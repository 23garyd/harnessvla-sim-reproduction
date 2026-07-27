"""Direct frozen-VLA baseline rollout (experiment v1, condition "direct").

One invocation = one rollout of one frozen (suite, task, seed) cell:
spawn env_server, attach to a RUNNING vla_server (--vla-endpoint; pi0.5
takes ~130 s to load, boot it once per session), stream 5-step action
chunks conditioned on the full task instruction until the benchmark
predicate (`terminated`) fires or a budget trips. Writes run_meta.json,
result_row.json, first/last frames, and the env_server log into a unique
append-only run dir.

Boot the VLA server once:
  sleep infinity | .venv/bin/python RPent/robots/libero/vla_server.py \
      --transport http --host 127.0.0.1 --port 18473 > /tmp/vla_server.log 2>&1 &
  # (sleep infinity holds stdin open: watch_parent_death shuts down on EOF)

Then:
  .venv/bin/python track/launchers/run_direct.py \
      --suite libero_object_swap --task-id 2 --seed 1 \
      --vla-endpoint http://127.0.0.1:18473
"""
import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "RPent"))
sys.path.insert(0, str(REPO))

from rpent.utils.http_rpc import HttpRpcClient  # noqa: E402
from rpent.utils.rpc import wait_for_ready  # noqa: E402
from rpent.utils.vla_client import VLAClient  # noqa: E402

from track.analysis import disk_guard  # noqa: E402
from track.analysis.manifests import load_manifest  # noqa: E402
from track.launchers import direct_lib  # noqa: E402


def spawn_env_server(suite, task_id, seed, max_steps, port, log_path):
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(Path.home()),
        "CUDA_VISIBLE_DEVICES": "0",
        "LIBERO_TYPE": "pro",
        "MUJOCO_GL": "egl",
        "PYOPENGL_PLATFORM": "egl",
        "ROBOT_PLATFORM": "LIBERO",
    }
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [str(REPO / ".venv/bin/python"),
         str(REPO / "RPent/robots/libero/env_server.py"),
         "--transport", "http", "--host", "127.0.0.1", "--port", str(port),
         "--suite", suite, "--task", str(task_id), "--seed", str(seed),
         "--max-episode-steps", str(max_steps)],
        # stdin stays an OPEN pipe: watch_parent_death shuts down on EOF.
        stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
        env=env, cwd=str(REPO / "RPent"))
    return proc, log


def build_env_obs(obs, instruction):
    return {
        "main_images": np.asarray(obs["main_images"]),
        "wrist_images": np.asarray(obs["wrist_images"]),
        "states": np.asarray(obs["states"], dtype=np.float32),
        "task_descriptions": instruction,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--suite", required=True)
    p.add_argument("--task-id", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--manifest",
                   default=str(REPO / "track/manifests/core_v1.json"))
    p.add_argument("--vla-endpoint", required=True,
                   help="http://host:port of a running vla_server")
    p.add_argument("--env-port", type=int, default=18481)
    p.add_argument("--out-root", default=str(REPO / "artifacts/runs"))
    args = p.parse_args(argv)

    # Gates: pinned research code, disk budget, frozen cell.
    subprocess.run([str(REPO / "track/setup/pin_check.sh")], check=True)
    used, ok = disk_guard.check(REPO / "artifacts")
    if not ok:
        sys.exit(f"FATAL: artifacts disk budget exceeded (used={used})")
    manifest = load_manifest(args.manifest)
    direct_lib.select_cell(manifest, args.suite, args.task_id, args.seed,
                           condition=direct_lib.CONDITION)
    budgets = manifest["budgets"]

    # Pin/sha reads happen BEFORE run-dir creation: a failure here must not
    # leave an orphaned empty run dir behind.
    rpent_commit = direct_lib.read_rpent_pin(REPO / "track/setup/pins.env")
    checkpoint_sha = direct_lib.read_checkpoint_sha(
        REPO / "track/setup/checkpoint.sha256sums")

    ts = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    run_dir = direct_lib.make_run_dir(
        Path(args.out_root), manifest["exp_version"], direct_lib.CONDITION,
        args.suite, args.task_id, args.seed, ts)
    meta = direct_lib.build_run_meta(
        exp_version=manifest["exp_version"], suite=args.suite,
        task_id=args.task_id, seed=args.seed, budgets=budgets,
        rpent_commit=rpent_commit, checkpoint_sha256=checkpoint_sha,
        launch_command=" ".join(sys.argv))
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))

    proc = log = None
    steps = chunks = 0
    success = False
    validity, reason, evidence = "infra_failure", "exception", None
    t0 = time.monotonic()  # durations must survive a backward NTP step
    try:
        vla = VLAClient(HttpRpcClient(args.vla_endpoint))
        vla.healthz()

        # Env horizon gets +20 slack over the scoring budget: LiberoEnv's reset
        # burns 15 settle steps of robosuite's internal horizon counter, so an
        # equal horizon makes robosuite flag done at driver-step 585 and the
        # next chunk_step crashes ("executing action in terminated episode").
        # Scoring still stops at budgets["max_steps"] in our loop below.
        proc, log = spawn_env_server(args.suite, args.task_id, args.seed,
                                     budgets["max_steps"] + 20, args.env_port,
                                     run_dir / "env_server.log")
        env = HttpRpcClient(f"http://127.0.0.1:{args.env_port}")
        wait_for_ready(env, timeout_s=600)
        obs, _ = env.call("env.reset", timeout_s=180)
        instruction = env.call("env.get_task_language")
        direct_lib.save_png(obs["main_images"], run_dir / "frame_first.png")

        while (steps < budgets["max_steps"]
               and time.monotonic() - t0 < budgets["max_wall_seconds"]):
            actions, _ = vla.predict_action_batch(
                build_env_obs(obs, instruction), mode="eval")
            chunks += 1
            obs, _r, terminated, truncated, _i = env.call(
                "env.chunk_step",
                kwargs={"actions": np.asarray(actions).tolist()},
                timeout_s=120)
            term = np.atleast_1d(np.asarray(terminated)).astype(bool)
            trunc = np.atleast_1d(np.asarray(truncated)).astype(bool)
            if term.any():
                steps += int(np.argmax(term)) + 1
                success = True  # benchmark predicate — the only success source
                break
            steps += len(term)
            if trunc.any():
                break

        direct_lib.save_png(obs["main_images"], run_dir / "frame_last.png")
        validity, reason = direct_lib.resolve_outcome(
            success, steps, budgets["max_steps"],
            time.monotonic() - t0, budgets["max_wall_seconds"])
        evidence = None
    except Exception:
        success = False
        validity, reason = "infra_failure", "exception"
        evidence = traceback.format_exc()[-2000:]
    finally:
        if proc is not None:
            try:
                HttpRpcClient(f"http://127.0.0.1:{args.env_port}").call(
                    "shutdown", timeout_s=10)
            except Exception:
                pass
            try:
                proc.wait(timeout=30)  # -6 after clean shutdown is known-OK
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
        if log is not None:
            log.close()
        row = direct_lib.build_result_row(
            success=success, validity=validity, terminal_reason=reason,
            steps=steps, chunks=chunks,
            wall_s=round(time.monotonic() - t0, 1), evidence=evidence)
        (run_dir / "result_row.json").write_text(json.dumps(row, indent=2))
        print(json.dumps({"run_dir": str(run_dir), **row}, indent=2))
    return 0 if validity != "infra_failure" else 1


if __name__ == "__main__":
    sys.exit(main())
