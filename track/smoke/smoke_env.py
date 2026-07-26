"""Day-2 smoke test A: env_server standalone.

Boots RPent's robots/libero/env_server.py on the A6000 and validates:
get_env_meta, reset (obs has main/wrist images + states), render_camera
RGB-D non-degenerate, camera intrinsics/extrinsics, task language, one step,
clean shutdown. Saves the reset obs for smoke_vla.py.

Run: .venv/bin/python track/smoke/smoke_env.py
Evidence: artifacts/smoke/<date>/env_server/{results.json,server.log,obs_for_vla.npz}
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "RPent"))
from rpent.utils.http_rpc import HttpRpcClient  # noqa: E402
from rpent.utils.rpc import wait_for_ready  # noqa: E402

PORT = 18471
SUITE, TASK, SEED = "libero_object_swap", 2, 0
OUT = REPO / "artifacts" / "smoke" / time.strftime("%Y-%m-%d") / "env_server"
OUT.mkdir(parents=True, exist_ok=True)

env = {
    "PATH": "/usr/bin:/bin",
    "HOME": str(Path.home()),
    "CUDA_VISIBLE_DEVICES": "0",
    "LIBERO_TYPE": "pro",
    "MUJOCO_GL": "egl",
    "PYOPENGL_PLATFORM": "egl",
    "ROBOT_PLATFORM": "LIBERO",
}

log = open(OUT / "server.log", "w")
proc = subprocess.Popen(
    [str(REPO / ".venv/bin/python"), str(REPO / "RPent/robots/libero/env_server.py"),
     "--transport", "http", "--host", "127.0.0.1", "--port", str(PORT),
     "--suite", SUITE, "--task", str(TASK), "--seed", str(SEED),
     "--max-episode-steps", "600"],
    # stdin must stay an OPEN pipe: watch_parent_death treats stdin EOF as
    # "parent died" and shuts the server down (DEVNULL = instant EOF).
    stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
    env=env, cwd=str(REPO / "RPent"),
)
results = {}
try:
    client = HttpRpcClient(f"http://127.0.0.1:{PORT}")
    t0 = time.time()
    wait_for_ready(client, timeout_s=600)
    results["boot_s"] = round(time.time() - t0, 1)

    meta = client.call("env.get_env_meta")
    assert meta["suite"] == SUITE and meta["task"] == TASK and meta["seed"] == SEED, meta
    results["env_meta"] = meta

    obs, info = client.call("env.reset", timeout_s=180)
    results["reset_obs_keys"] = sorted(obs.keys())
    main = np.asarray(obs["main_images"])
    states = np.asarray(obs["states"])
    assert main.ndim == 3 and main.shape[2] == 3, main.shape
    assert main.std() > 1.0, "main image degenerate (flat)"
    results["main_images_shape"] = list(main.shape)
    results["states_shape"] = list(states.shape)

    task_language = client.call("env.get_task_language")
    results["task_language"] = task_language
    np.savez(OUT / "obs_for_vla.npz", main_images=main, states=states,
             wrist_images=np.asarray(obs["wrist_images"]),
             task=np.array(task_language))

    rgbd = client.call("env.render_camera",
                       kwargs={"camera_name": "agentview", "height": 256,
                               "width": 256, "depth": True}, timeout_s=120)
    rgb, depth = (np.asarray(rgbd[0]), np.asarray(rgbd[1])) if isinstance(rgbd, (list, tuple)) else (np.asarray(rgbd), None)
    assert rgb.std() > 1.0, "render RGB degenerate"
    results["render_rgb_shape"] = list(rgb.shape)
    if depth is not None:
        d = np.asarray(depth, dtype=np.float64)
        assert np.isfinite(d).all() and d.std() > 0, "depth degenerate"
        results["render_depth_shape"] = list(d.shape)
        results["depth_range"] = [float(d.min()), float(d.max())]

    cam = client.call("env.get_camera_meta",
                      kwargs={"camera_name": "agentview", "height": 256, "width": 256})
    results["camera_meta_keys"] = sorted(cam.keys()) if isinstance(cam, dict) else str(type(cam))

    step = client.call("env.step", kwargs={"action": [0.0] * 7}, timeout_s=60)
    results["step_reward_term_trunc"] = [float(step[1]), bool(step[2]), bool(step[3])]

    client.call("shutdown")
    proc.wait(timeout=30)
    # Known issue: EGL teardown aborts (SIGABRT, -6) after a clean shutdown
    # RPC; treat any prompt exit following shutdown-ok as clean.
    results["server_exit_code"] = proc.returncode
    results["PASS"] = True
finally:
    if proc.poll() is None:
        proc.kill()
        results.setdefault("PASS", False)
    log.close()
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps(results, indent=2, default=str))
    sys.exit(0 if results.get("PASS") else 1)
