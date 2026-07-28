"""Manifest-driven batch runner (Day 6). Sequential, resume-without-
overwrite: cells with any non-infra row are done; infra rows retry with a
hard cap of 2 attempts (then exhausted -> triage). Every new row is verified
against raw artifacts before the queue proceeds. Never deletes anything.

Phase order per invocation: all direct cells (shared VLA server booted only
if needed, stopped before any harness launch — run_harness's pkill backstop
would kill it), then harness cells.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from track.analysis import build_ledger, disk_guard  # noqa: E402
from track.analysis.manifests import load_manifest, scored_cells  # noqa: E402

MAX_INFRA_ATTEMPTS = 2
VLA_PORT = 18473


def plan_pending(manifest, ledger_rows, max_infra_attempts=MAX_INFRA_ATTEMPTS,
                 manifest_path=None):
    """Return (pending, exhausted) cell dicts in manifest order. Each cell
    carries the manifest path it was planned from so run_cell launches the
    launcher against the SAME frozen manifest (Day-11 regression: the
    launchers' defaults are the core manifests)."""
    done, infra = set(), {}
    for r in ledger_rows:
        if r["exp_version"] != manifest["exp_version"]:
            continue
        key = (r["condition"], r["task"], int(r["seed"]))
        if r["validity"] == "infra_failure":
            infra[key] = infra.get(key, 0) + 1
        else:
            done.add(key)
    pending, exhausted = [], []
    for cond, suite, task, seed in scored_cells(manifest):
        cell_row = next(c for c in manifest["cells"]
                        if c["condition"] == cond and c["task"] == task)
        key = (cond, task, seed)
        item = {"condition": cond, "suite": suite,
                "task_id": cell_row["task_id"], "seed": seed}
        if manifest_path is not None:
            item["manifest"] = str(manifest_path)
        if key in done:
            continue
        if infra.get(key, 0) >= max_infra_attempts:
            exhausted.append(item)
        else:
            pending.append(item)
    return pending, exhausted


def verify_row(run_dir):
    """Summary-vs-raw check: the row must reproduce from raw artifacts."""
    run_dir = Path(run_dir)
    row = build_ledger.load_row(run_dir)  # schema + path cross-checks
    states_path = run_dir / "rpent" / "states.json"
    if row["condition"] == "harness" and states_path.exists():
        states = json.loads(states_path.read_text())
        # Cumulative, matching harness_lib.parse_harness_outcome exactly.
        raw = any(bool(e.get("libero_terminated")) for e in states)
        if bool(row["success"]) != raw:
            raise ValueError(
                f"{run_dir}: result_row success={row['success']} disagrees "
                f"with states.json libero_terminated={raw}")
    return row


def write_queue_record(queues_dir, manifests, planned, limit, ts=None):
    """Immutable record of what this queue intends to run."""
    queues_dir = Path(queues_dir)
    queues_dir.mkdir(parents=True, exist_ok=True)
    ts = ts or time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    path = queues_dir / f"queue_{ts}.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(
        {"manifests": [str(m) for m in manifests],
         "planned": planned, "limit": limit}, indent=2))
    return path


def start_shared_vla():
    """Boot one vla_server for direct cells. stdin stays an OPEN pipe."""
    log_path = REPO / "artifacts/queues" / f"vla_{int(time.monotonic())}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w")
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
    env.update({"CUDA_VISIBLE_DEVICES": "0",
                "PI05_CHECKPOINT_PATH":
                    str(REPO / "checkpoints/rlinf-pi05-libero-130-fullshot-sft")})
    proc = subprocess.Popen(
        [str(REPO / ".venv/bin/python"),
         str(REPO / "RPent/robots/libero/vla_server.py"),
         "--transport", "http", "--host", "127.0.0.1",
         "--port", str(VLA_PORT)],
        stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
        env=env, cwd=str(REPO / "RPent"))
    deadline = time.monotonic() + 400
    while time.monotonic() < deadline:
        if "RPC server listening" in log_path.read_text():
            return proc, f"http://127.0.0.1:{VLA_PORT}", log
        if proc.poll() is not None:
            break
        time.sleep(5)
    raise RuntimeError(f"shared vla_server did not come up; see {log_path}")


def stop_shared_vla(vla):
    proc, endpoint, log = vla
    try:
        req = urllib.request.Request(
            endpoint + "/call",
            data=json.dumps({"id": "q", "method": "shutdown",
                             "args": [], "kwargs": {}}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
    try:
        proc.wait(timeout=30)  # -6 after clean shutdown is known-OK
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


def newest_run_dir(runs_root, exp, condition, task, seed):
    d = Path(runs_root) / exp / condition / task / str(seed)
    dirs = sorted(p for p in d.iterdir() if p.is_dir()) if d.exists() else []
    if not dirs:
        raise ValueError(f"no run dir found under {d}")
    return dirs[-1]


def run_cell(cell, runs_root, vla_endpoint=None):
    from track.launchers.direct_lib import task_key
    if cell["condition"] == "direct":
        cmd = [str(REPO / ".venv/bin/python"),
               str(REPO / "track/launchers/run_direct.py"),
               "--suite", cell["suite"], "--task-id", str(cell["task_id"]),
               "--seed", str(cell["seed"]),
               "--vla-endpoint", vla_endpoint]
    else:
        cmd = [str(REPO / ".venv/bin/python"),
               str(REPO / "track/launchers/run_harness.py"),
               "--suite", cell["suite"], "--task-id", str(cell["task_id"]),
               "--seed", str(cell["seed"])]
    if cell.get("manifest"):
        cmd += ["--manifest", cell["manifest"]]
    print(f"=== {cell['condition']} {cell['suite']} t{cell['task_id']} "
          f"seed {cell['seed']} ===", flush=True)
    subprocess.run(cmd, check=False)
    run_dir = newest_run_dir(runs_root, exp_version_for(cell),
                             cell["condition"],
                             task_key(cell["suite"], cell["task_id"]),
                             cell["seed"])
    row = verify_row(run_dir)
    print(f"verified: validity={row['validity']} "
          f"reason={row['terminal_reason']}", flush=True)
    return row


_CELL_VERSIONS = {}


def exp_version_for(cell):
    return _CELL_VERSIONS[(cell["condition"], cell["suite"], cell["seed"])]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifests", nargs="+",
                   default=[str(REPO / "track/manifests/core_v1.json"),
                            str(REPO / "track/manifests/harness_v2.json")])
    p.add_argument("--runs-root", default=str(REPO / "artifacts/runs"))
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    subprocess.run([str(REPO / "track/setup/pin_check.sh")], check=True)
    rows, _, _ = build_ledger.build_ledger(args.runs_root)
    launched = 0
    record_written = False
    for mpath in args.manifests:
        manifest = load_manifest(mpath)
        pending, exhausted = plan_pending(manifest, rows, manifest_path=mpath)
        for cell in pending + exhausted:
            _CELL_VERSIONS[(cell["condition"], cell["suite"],
                            cell["seed"])] = manifest["exp_version"]
        for cell in exhausted:
            print(f"WARNING: exhausted (>= {MAX_INFRA_ATTEMPTS} infra "
                  f"attempts, needs triage): {cell}", flush=True)
        total = len(scored_cells(manifest))
        print(f"{Path(mpath).name}: {total} scored cells, "
              f"{total - len(pending) - len(exhausted)} already valid, "
              f"{len(pending)} pending, {len(exhausted)} exhausted",
              flush=True)
        if args.dry_run:
            for cell in pending:
                print(f"  pending: {cell}", flush=True)
            continue
        if pending and not record_written:
            path = write_queue_record(REPO / "artifacts/queues",
                                      args.manifests, pending, args.limit)
            print(f"queue record: {path}", flush=True)
            record_written = True
        direct_cells = [c for c in pending if c["condition"] == "direct"]
        harness_cells = [c for c in pending if c["condition"] != "direct"]
        vla = None
        try:
            if direct_cells and not (args.limit is not None
                                     and launched >= args.limit):
                vla = start_shared_vla()
                for cell in direct_cells:
                    if args.limit is not None and launched >= args.limit:
                        break
                    used, ok = disk_guard.check(REPO / "artifacts")
                    if not ok:
                        sys.exit(f"FATAL: disk budget exceeded "
                                 f"(used={used}); queue paused")
                    launched += 1
                    run_cell(cell, args.runs_root, vla_endpoint=vla[1])
        finally:
            if vla is not None:
                stop_shared_vla(vla)  # BEFORE any harness launch (pkill)
        for cell in harness_cells:
            if args.limit is not None and launched >= args.limit:
                break
            used, ok = disk_guard.check(REPO / "artifacts")
            if not ok:
                sys.exit(f"FATAL: disk budget exceeded (used={used}); "
                         f"queue paused")
            launched += 1
            run_cell(cell, args.runs_root)
    n, skipped0, incomplete = build_ledger.build_ledger(args.runs_root)
    build_ledger.write_csv(n, REPO / "artifacts/ledger.csv")
    print(f"queue done: {launched} launched this invocation; ledger "
          f"rebuilt ({len(n)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
