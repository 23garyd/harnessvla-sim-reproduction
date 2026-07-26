"""Day-2 smoke test B: vla_server standalone.

Boots RPent's robots/libero/vla_server.py (loads the frozen pi0.5 checkpoint
onto the A6000), runs two inferences on the obs saved by smoke_env.py, and
validates the returned action chunk (finite, non-zero, [chunk, 7]).

Run smoke_env.py first (same day), then: .venv/bin/python track/smoke/smoke_vla.py
Evidence: artifacts/smoke/<date>/vla_server/{results.json,server.log,action_chunk.npy}
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
from rpent.utils.vla_client import VLAClient  # noqa: E402

PORT = 18473
DAY = time.strftime("%Y-%m-%d")
OUT = REPO / "artifacts" / "smoke" / DAY / "vla_server"
OUT.mkdir(parents=True, exist_ok=True)
ENV_OUT = REPO / "artifacts" / "smoke" / DAY / "env_server"

env = {
    "PATH": "/usr/bin:/bin",
    "HOME": str(Path.home()),
    "CUDA_VISIBLE_DEVICES": "0",
    "PI05_CHECKPOINT_PATH": str(REPO / "checkpoints" / "rlinf-pi05-libero-130-fullshot-sft"),
}

log = open(OUT / "server.log", "w")
proc = subprocess.Popen(
    [str(REPO / ".venv/bin/python"), str(REPO / "RPent/robots/libero/vla_server.py"),
     "--transport", "http", "--host", "127.0.0.1", "--port", str(PORT)],
    # stdin must stay an OPEN pipe: watch_parent_death treats stdin EOF as
    # "parent died" and shuts the server down (DEVNULL = instant EOF).
    stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
    env=env, cwd=str(REPO / "RPent"),
)
results = {}
try:
    client = HttpRpcClient(f"http://127.0.0.1:{PORT}")
    t0 = time.time()
    wait_for_ready(client, timeout_s=900)  # model load blocks the listener
    results["boot_and_model_load_s"] = round(time.time() - t0, 1)

    vla = VLAClient(client)
    results["healthz"] = vla.healthz()

    saved = np.load(ENV_OUT / "obs_for_vla.npz")
    env_obs = {
        "main_images": saved["main_images"],
        "wrist_images": saved["wrist_images"],  # pi05_libero needs 2 views
        "states": saved["states"].astype(np.float32),
        "task_descriptions": str(saved["task"]),
    }
    t1 = time.time()
    actions, info = vla.predict_action_batch(env_obs, mode="eval")
    results["first_inference_s"] = round(time.time() - t1, 2)
    actions = np.asarray(actions)
    assert actions.ndim == 2 and actions.shape[1] == 7, actions.shape
    assert np.isfinite(actions).all(), "non-finite actions"
    assert float(np.abs(actions).max()) > 0, "all-zero action chunk"
    results["action_chunk_shape"] = list(actions.shape)
    results["action_abs_max"] = float(np.abs(actions).max())
    np.save(OUT / "action_chunk.npy", actions)

    t2 = time.time()
    actions2, _ = vla.predict_action_batch(env_obs, mode="eval")
    results["second_inference_s"] = round(time.time() - t2, 2)

    client.call("shutdown")
    proc.wait(timeout=60)
    # Known issue: SIGABRT (-6) on teardown after clean shutdown RPC.
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
