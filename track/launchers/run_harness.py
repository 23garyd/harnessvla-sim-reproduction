"""Harness-condition rollout (experiment v2). One invocation = one rollout
of one frozen (suite, task, seed) cell via the rpent CLI with the
registry-v2 pins. Writes run_meta.json / result_row.json into an
append-only run dir; rpent's own artifacts land in <run_dir>/rpent/.

Billing: ANTHROPIC/OPENAI keys are stripped from the child env — the
claude_code planner bills the claude.ai subscription.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from track.analysis import disk_guard  # noqa: E402
from track.analysis.manifests import load_manifest  # noqa: E402
from track.launchers import direct_lib, harness_lib  # noqa: E402


def rpent_cmd(args, budgets, out_dir):
    return [str(REPO / ".venv/bin/rpent"), "--env", "libero",
            "--suite", args.suite, "--task", str(args.task_id),
            "--seed", str(args.seed),
            "--planner", "claude_code", "--model", "claude-opus-4-8",
            "--max-turns", str(budgets["max_turns"]),
            "--planner-timeout-s",
            str(harness_lib.PLANNER_SETTINGS["planner_timeout_s"]),
            # +20 settle margin over the guide's 1200-step budget (Day-3 bug)
            "--max-episode-steps", str(budgets["max_steps"] + 20),
            "--output-dir", str(out_dir)]


def child_env():
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
    env.update({
        "CUDA_VISIBLE_DEVICES": "0",
        "LIBERO_TYPE": "pro",
        "MUJOCO_GL": "egl",
        "PYOPENGL_PLATFORM": "egl",
        "PI05_CHECKPOINT_PATH":
            str(REPO / "checkpoints/rlinf-pi05-libero-130-fullshot-sft"),
        "SAM3_CHECKPOINT_PATH": str(REPO / "checkpoints/sam3/sam3.pt"),
    })
    return env


def sweep_strays(run_dir):
    """SDK tool runtime resolves relative paths against RPent root; preserve
    any fumbled writes into the run dir, never delete evidence."""
    stray = REPO / "RPent" / "artifacts"
    if stray.exists():
        dest = run_dir / "planner_strays"
        dest.mkdir(exist_ok=True)
        shutil.copytree(stray, dest, dirs_exist_ok=True)
        shutil.rmtree(stray)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--suite", required=True)
    p.add_argument("--task-id", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--manifest",
                   default=str(REPO / "track/manifests/harness_v2.json"))
    p.add_argument("--out-root", default=str(REPO / "artifacts/runs"))
    args = p.parse_args(argv)

    subprocess.run([str(REPO / "track/setup/pin_check.sh")], check=True)
    used, ok = disk_guard.check(REPO / "artifacts")
    if not ok:
        sys.exit(f"FATAL: artifacts disk budget exceeded (used={used})")
    manifest = load_manifest(args.manifest)
    direct_lib.select_cell(manifest, args.suite, args.task_id, args.seed,
                           condition=harness_lib.CONDITION)
    budgets = manifest["budgets"]

    rpent_commit = direct_lib.read_rpent_pin(REPO / "track/setup/pins.env")
    checkpoint_sha = direct_lib.read_checkpoint_sha(
        REPO / "track/setup/checkpoint.sha256sums")

    ts = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    run_dir = direct_lib.make_run_dir(
        Path(args.out_root), manifest["exp_version"], harness_lib.CONDITION,
        args.suite, args.task_id, args.seed, ts)
    meta = harness_lib.build_harness_run_meta(
        exp_version=manifest["exp_version"], suite=args.suite,
        task_id=args.task_id, seed=args.seed, budgets=budgets,
        rpent_commit=rpent_commit, checkpoint_sha256=checkpoint_sha,
        launch_command=" ".join(sys.argv))
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))

    rpent_out = run_dir / "rpent"
    validity, reason, evidence = "infra_failure", "exception", None
    outcome = harness_lib.empty_outcome()
    t0 = time.monotonic()
    log = open(run_dir / "launcher.log", "w")
    try:
        proc = subprocess.Popen(rpent_cmd(args, budgets, rpent_out),
                                stdout=log, stderr=subprocess.STDOUT,
                                env=child_env(), cwd=str(REPO),
                                start_new_session=True)
        wall_capped = False
        try:
            rc = proc.wait(timeout=budgets["max_wall_seconds"])
        except subprocess.TimeoutExpired:
            wall_capped = True
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
            proc.wait(timeout=30)
            rc = proc.returncode

        outcome = harness_lib.parse_harness_outcome(rpent_out)
        outcome["wall_s"] = round(time.monotonic() - t0, 1)  # launcher clock
        if wall_capped:
            validity, reason = "budget_exhausted", "wall_time"
        else:
            validity, reason = harness_lib.resolve_harness_outcome(
                outcome, budgets)
            if rc != 0 and not outcome["success"]:
                validity, reason = "infra_failure", f"rpent_exit_{rc}"
                evidence = (f"rpent exit {rc}; launcher.log and rpent/ logs "
                            f"retained in {run_dir}")
        if validity != "infra_failure":
            evidence = None
    except Exception:
        outcome["wall_s"] = round(time.monotonic() - t0, 1)
        validity, reason = "infra_failure", "exception"
        evidence = traceback.format_exc()[-2000:]
    finally:
        sweep_strays(run_dir)
        for pat in ("robots/libero/env_server.py",
                    "robots/libero/sam3_server.py",
                    "robots/libero/vla_server.py"):
            subprocess.run(["pkill", "-f", pat], check=False)
        log.close()
        row = harness_lib.build_harness_result_row(
            outcome=outcome, validity=validity, terminal_reason=reason,
            evidence=evidence)
        (run_dir / "result_row.json").write_text(json.dumps(row, indent=2))
        print(json.dumps({"run_dir": str(run_dir), **row}, indent=2))
    return 0 if validity != "infra_failure" else 1


if __name__ == "__main__":
    sys.exit(main())
