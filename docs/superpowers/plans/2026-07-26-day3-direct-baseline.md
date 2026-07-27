# Day-3 Direct-Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the core task/seed matrix (experiment v1) and build the direct frozen-VLA baseline launcher — continuous pi0.5 rollout via vla_server, predicate-only scoring, one machine-readable result row per rollout — validated by two supervised rollouts.

**Architecture:** Pure, unit-testable logic (run-dir/record building, outcome resolution, freeze enforcement) lives in `track/launchers/direct_lib.py`, tested in `.venv-dev` with no GPU stack. The GPU driver `track/launchers/run_direct.py` spawns env_server per rollout, attaches to an already-running vla_server (`--vla-endpoint`; the model takes ~130 s to load, so it boots once per session), streams 5-step action chunks until the benchmark predicate fires or a budget trips, and writes `run_meta.json`/`result_row.json` per the Task-5/6 schemas so `build_ledger.py` consumes them unchanged.

**Tech Stack:** Python 3.10; `track.analysis.{schemas,manifests,disk_guard,build_ledger}` (already built); RPent's `HttpRpcClient`/`VLAClient`/`wait_for_ready`; pytest in `.venv-dev`.

**Session conventions (established Days 1–2):**
- Pytest: `PYTHONPATH= .venv-dev/bin/python -m pytest ...` (ROS pollution guard).
- Server subprocesses: stdin must stay an OPEN pipe (`watch_parent_death` shuts down on stdin EOF).
- Servers exit −6 (SIGABRT, EGL teardown) after a clean `shutdown` RPC — treat shutdown-ok + prompt exit as clean.
- Work directly on `main` was used for Day-2 records; Day-3 code goes on a branch `day3-direct-baseline`.

**Verified facts this plan builds on (Day-3 investigation, 2026-07-26):**
- Seed mapping: `init_state_id = first_id + (seed % trials)` (`RPent/robots/libero/env_server.py:90-92`); all four chosen cells have 50 init states and seeds 0–5 map to 6/6 distinct init-state vectors.
- The benchmark predicate surfaces as `terminated` from `env.chunk_step` (rlinf `LiberoEnv`: `success_once |= terminations`).
- `env.chunk_step(actions)` returns `(final_obs, reward, terminated[chunk], truncated[chunk], info)`.
- vla predict needs BOTH `main_images` and `wrist_images` plus 1-D `states` and `task_descriptions`.

---

### Task 1: `direct_lib.py` — records, outcome resolution, pins (pure logic)

**Files:**
- Create: `track/launchers/__init__.py` (empty — makes launchers importable)
- Create: `track/launchers/direct_lib.py`
- Test: `track/tests/test_direct_lib.py`

- [ ] **Step 1: Write the failing tests.** Create `track/tests/test_direct_lib.py`:

```python
import json

import pytest

from track.analysis import build_ledger
from track.launchers import direct_lib


def test_task_key():
    assert direct_lib.task_key("libero_goal_swap", 2) == "libero_goal_swap_t2"


def test_make_run_dir_five_levels(tmp_path):
    d = direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                "libero_goal_swap", 2, 3, "20260726T120000")
    assert d == (tmp_path / "v1" / "direct" / "libero_goal_swap_t2"
                 / "3" / "20260726T120000")
    assert d.is_dir()
    with pytest.raises(FileExistsError):
        direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                "libero_goal_swap", 2, 3, "20260726T120000")


def test_resolve_outcome_mapping():
    assert direct_lib.resolve_outcome(True, 42, 600, 100.0, 1800) == \
        ("success", "benchmark_predicate")
    assert direct_lib.resolve_outcome(False, 600, 600, 100.0, 1800) == \
        ("budget_exhausted", "step_budget")
    assert direct_lib.resolve_outcome(False, 42, 600, 1801.0, 1800) == \
        ("budget_exhausted", "wall_time")
    assert direct_lib.resolve_outcome(False, 42, 600, 100.0, 1800) == \
        ("valid_failure", "env_truncated")


def test_build_result_row_validates():
    row = direct_lib.build_result_row(
        success=False, validity="valid_failure", terminal_reason="env_truncated",
        steps=42, chunks=9, wall_s=100.5)
    assert row["counts"] == {"steps": 42, "turns": 0,
                             "vla_act_calls": 9, "analytic_calls": 0}


def test_build_result_row_infra_needs_evidence():
    with pytest.raises(ValueError, match="evidence"):
        direct_lib.build_result_row(
            success=False, validity="infra_failure", terminal_reason="exception",
            steps=0, chunks=0, wall_s=1.0)
    row = direct_lib.build_result_row(
        success=False, validity="infra_failure", terminal_reason="exception",
        steps=0, chunks=0, wall_s=1.0, evidence="Traceback ...")
    assert row["evidence"] == "Traceback ..."


def test_read_rpent_pin(tmp_path):
    pins = tmp_path / "pins.env"
    pins.write_text("# comment\nRPENT_COMMIT=6e4ba1805a459d74ad53569e833bae7ae2c59985\n")
    assert direct_lib.read_rpent_pin(pins).startswith("6e4ba18")
    pins.write_text("RPENT_COMMIT=\n")
    with pytest.raises(ValueError, match="RPENT_COMMIT"):
        direct_lib.read_rpent_pin(pins)


def test_read_checkpoint_sha(tmp_path):
    sums = tmp_path / "checkpoint.sha256sums"
    sums.write_text(
        "aaaa  ./.gitattributes\n"
        "4d9089c941793f170b625c2ed0ac7a3aa09b6f103e52dbbc82e67301529d6683  ./model.safetensors\n")
    assert direct_lib.read_checkpoint_sha(sums).startswith("4d9089c9")
    sums.write_text("aaaa  ./other.bin\n")
    with pytest.raises(ValueError, match="model.safetensors"):
        direct_lib.read_checkpoint_sha(sums)


def test_build_run_meta_ledger_round_trip(tmp_path):
    """A run dir written with direct_lib must survive build_ledger unchanged."""
    run_dir = direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                      "libero_goal_swap", 2, 3, "20260726T120000")
    meta = direct_lib.build_run_meta(
        exp_version="v1", suite="libero_goal_swap", task_id=2, seed=3,
        budgets={"max_steps": 600, "max_turns": 0, "max_wall_seconds": 1800},
        rpent_commit="6e4ba1805a459d74ad53569e833bae7ae2c59985",
        checkpoint_sha256="4d9089c9", launch_command="run_direct.py ...")
    (run_dir / "run_meta.json").write_text(json.dumps(meta))
    row = direct_lib.build_result_row(
        success=True, validity="success", terminal_reason="benchmark_predicate",
        steps=42, chunks=9, wall_s=100.5)
    (run_dir / "result_row.json").write_text(json.dumps(row))
    rows, skipped0, incomplete = build_ledger.build_ledger(tmp_path)
    assert len(rows) == 1 and skipped0 == 0 and incomplete == 0
    assert rows[0]["task"] == "libero_goal_swap_t2"
    assert rows[0]["seed"] == 3
    assert rows[0]["condition"] == "direct"
    assert rows[0]["vla_act_calls"] == 9
```

- [ ] **Step 2: Run tests to verify they fail.**
Run: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests/test_direct_lib.py -v`
Expected: collection ERROR — no module `track.launchers.direct_lib`.

- [ ] **Step 3: Write `track/launchers/__init__.py`** (empty file) **and `track/launchers/direct_lib.py`:**

```python
"""Pure logic for the direct frozen-VLA baseline launcher (experiment v1).

Everything here is unit-testable without the GPU stack. The driver
(run_direct.py) owns servers and the rollout loop; this module owns records,
paths, pins, and freeze enforcement. Records go through
track.analysis.schemas so build_ledger.py consumes run dirs unchanged.
"""
import re
from pathlib import Path

from track.analysis.schemas import validate_result_row, validate_run_meta

CONDITION = "direct"


def task_key(suite, task_id):
    """Path/ledger task identifier — unique across suites by construction."""
    return f"{suite}_t{task_id}"


def make_run_dir(root, exp_version, condition, suite, task_id, seed, ts):
    """Create the 5-level run dir (append-only: refuses to overwrite)."""
    d = Path(root) / exp_version / condition / task_key(suite, task_id) / str(seed) / ts
    d.mkdir(parents=True, exist_ok=False)
    return d


def resolve_outcome(success, steps, max_steps, wall_s, max_wall_s):
    """Map loop end-state to (validity, terminal_reason). Predicate-only:
    success comes solely from the benchmark `terminated` signal."""
    if success:
        return "success", "benchmark_predicate"
    if steps >= max_steps:
        return "budget_exhausted", "step_budget"
    if wall_s >= max_wall_s:
        return "budget_exhausted", "wall_time"
    return "valid_failure", "env_truncated"


def build_run_meta(*, exp_version, suite, task_id, seed, budgets,
                   rpent_commit, checkpoint_sha256, launch_command):
    return validate_run_meta({
        "exp_version": exp_version,
        "condition": CONDITION,
        "task": task_key(suite, task_id),
        "suite": suite,
        "seed": seed,
        "planner_model": "none (direct frozen-VLA baseline)",
        "planner_settings": {},
        "prompt_hashes": {},
        "rpent_commit": rpent_commit,
        "checkpoint_sha256": checkpoint_sha256,
        "budgets": dict(budgets),
        "launch_command": launch_command,
    })


def build_result_row(*, success, validity, terminal_reason, steps, chunks,
                     wall_s, evidence=None):
    row = {
        "success": success,
        "terminal_reason": terminal_reason,
        "validity": validity,
        "counts": {"steps": steps, "turns": 0,
                   "vla_act_calls": chunks, "analytic_calls": 0},
        "wall_seconds": wall_s,
    }
    if evidence is not None:
        row["evidence"] = evidence
    return validate_result_row(row)


def read_rpent_pin(pins_file):
    """Parse (never source) pins.env — same rule as pin_check.sh."""
    text = Path(pins_file).read_text()
    m = re.findall(r"^RPENT_COMMIT=([0-9a-f]{7,40})$", text, flags=re.M)
    if not m:
        raise ValueError(f"{pins_file}: RPENT_COMMIT unset or malformed")
    return m[-1]


def read_checkpoint_sha(sums_file):
    """sha256 of model.safetensors — the checkpoint identity for run_meta."""
    for line in Path(sums_file).read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].endswith("model.safetensors"):
            return parts[0]
    raise ValueError(f"{sums_file}: no model.safetensors line")


def select_cell(manifest, suite, task_id, seed):
    """Freeze enforcement: refuse any (suite, task, seed) not scored in the
    frozen manifest. Bootstrap-only seeds are never scored."""
    for cell in manifest["cells"]:
        if cell["suite"] == suite and cell.get("task_id") == task_id:
            for entry in cell["seeds"]:
                if entry["seed"] == seed:
                    if entry["bootstrap_only"]:
                        raise ValueError(
                            f"seed {seed} is bootstrap_only in the frozen "
                            f"manifest and is never scored")
                    return cell
            raise ValueError(
                f"seed {seed} not in the frozen manifest for {suite} t{task_id}")
    raise ValueError(f"cell ({suite}, t{task_id}) not in the frozen manifest")


def save_png(arr, path):
    """Save an HxWx3 uint8 array as PNG (lazy imports: GPU-venv only)."""
    import numpy as np
    from PIL import Image
    Image.fromarray(np.asarray(arr).astype("uint8")).save(path)
```

- [ ] **Step 4: Run tests to verify they pass** (select_cell is tested in Task 2; the 8 tests above must pass).
Run: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests/test_direct_lib.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add track/launchers/__init__.py track/launchers/direct_lib.py track/tests/test_direct_lib.py
git commit -m "feat: direct_lib - run records, outcome resolution, pins, freeze enforcement"
```

---

### Task 2: Freeze the core matrix — `core_v1.json` + select_cell tests

**Files:**
- Create: `track/manifests/core_v1.json`
- Modify: `track/tests/test_direct_lib.py` (append tests)
- Delete: `track/manifests/.gitkeep`

Cell choice (anchors from the internship plan, section 2): three large-gap cells
(Spatial-T 42→94, Goal-T 45→87, Goal-S 42→87) and one honest small-gap cell
(Object-S 78→90); 3 families; 2×T + 2×S. Task id fixed at 2 for every suite
(predeclared rule — matches the RPent README canonical example; no
outcome-based selection). Seeds s1–s5 verified distinct from seed 0 (Day-3
verification; re-runnable via Task 3's tool).

- [ ] **Step 1: Write the failing tests.** Append to `track/tests/test_direct_lib.py`:

```python
def valid_cell_manifest():
    return {
        "exp_version": "v1",
        "budgets": {"max_steps": 600, "max_turns": 0, "max_wall_seconds": 1800},
        "caps": {"max_rollouts": 24, "max_tokens_per_rollout": 0},
        "cells": [
            {"condition": "direct", "suite": "libero_goal_swap",
             "task": "libero_goal_swap_t2", "task_id": 2,
             "seeds": [{"seed": 0, "bootstrap_only": True},
                       {"seed": 1, "bootstrap_only": False}]},
        ],
    }


def test_select_cell_ok():
    cell = direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 1)
    assert cell["task"] == "libero_goal_swap_t2"


def test_select_cell_rejects_bootstrap_seed():
    with pytest.raises(ValueError, match="bootstrap_only"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 0)


def test_select_cell_rejects_unfrozen_seed():
    with pytest.raises(ValueError, match="not in the frozen manifest"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 9)


def test_select_cell_rejects_unknown_cell():
    with pytest.raises(ValueError, match="not in the frozen manifest"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_spatial_task", 2, 1)


def test_resolve_outcome_success_wins_over_caps():
    # Predicate fired on the exact step the cap was reached: success wins.
    assert direct_lib.resolve_outcome(True, 600, 600, 1800.0, 1800) == \
        ("success", "benchmark_predicate")


def test_resolve_outcome_wall_boundary_exact():
    assert direct_lib.resolve_outcome(False, 42, 600, 1800.0, 1800) == \
        ("budget_exhausted", "wall_time")


def test_core_v1_manifest_frozen():
    from track.analysis.manifests import load_manifest
    from track.tests.conftest import REPO
    m = load_manifest(REPO / "track" / "manifests" / "core_v1.json")
    assert m["exp_version"] == "v1"
    assert m["budgets"] == {"max_steps": 600, "max_turns": 0,
                            "max_wall_seconds": 1800}
    suites = sorted(c["suite"] for c in m["cells"])
    assert suites == ["libero_goal_swap", "libero_goal_task",
                      "libero_object_swap", "libero_spatial_task"]
    from track.analysis.manifests import scored_cells
    cells = scored_cells(m)
    assert len(cells) == 20  # 4 suites x seeds 1-5
    assert all(seed in (1, 2, 3, 4, 5) for _, _, _, seed in cells)
    for c in m["cells"]:
        assert c["task"] == direct_lib.task_key(c["suite"], c["task_id"])
```

- [ ] **Step 2: Run to verify the manifest test fails** (select_cell tests pass already — they exercise Task 1 code):
Run: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests/test_direct_lib.py -v`
Expected: `test_core_v1_manifest_frozen` FAILS (file missing); other 14 PASS.

- [ ] **Step 3: Write `track/manifests/core_v1.json`:**

```json
{
  "exp_version": "v1",
  "frozen": "2026-07-26 (Day 3); seed distinctness verified via track/smoke/verify_seed_mapping.py",
  "budgets": {"max_steps": 600, "max_turns": 0, "max_wall_seconds": 1800},
  "caps": {"max_rollouts": 24, "max_tokens_per_rollout": 0},
  "cells": [
    {"condition": "direct", "suite": "libero_spatial_task",
     "task": "libero_spatial_task_t2", "task_id": 2,
     "anchor": "Spatial-T large gap (paper 42->94)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "direct", "suite": "libero_goal_task",
     "task": "libero_goal_task_t2", "task_id": 2,
     "anchor": "Goal-T large gap (paper 45->87)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "direct", "suite": "libero_goal_swap",
     "task": "libero_goal_swap_t2", "task_id": 2,
     "anchor": "Goal-S large gap (paper 42->87)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "direct", "suite": "libero_object_swap",
     "task": "libero_object_swap_t2", "task_id": 2,
     "anchor": "Object-S small gap, honest hard case (paper 78->90)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]}
  ]
}
```

Note: this manifest freezes the DIRECT condition only. Harness cells reuse the
same task/seed list and are added at the Day-5 protocol freeze (a
behavior-affecting change → new registry version).

- [ ] **Step 4: Run tests to verify they pass.**
Run: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests/test_direct_lib.py -v`
Expected: 15 PASS

- [ ] **Step 5: Remove placeholder and commit**

```bash
git rm --quiet track/manifests/.gitkeep
git add track/manifests/core_v1.json track/tests/test_direct_lib.py
git commit -m "feat: freeze core matrix v1 - 4 cells x seeds s1-s5, direct condition"
```

---

### Task 3: `verify_seed_mapping.py` — re-runnable freeze verification

**Files:**
- Create: `track/smoke/verify_seed_mapping.py`
- Create (generated): `track/manifests/core_v1_seed_check.txt`

No pytest (needs the GPU-stack venv's liberopro). Mirrors
`env_server.py:90-92` (`rid = first_id + seed % trials`).

- [ ] **Step 1: Write `track/smoke/verify_seed_mapping.py`:**

```python
"""Verify the frozen manifest's seeds map to distinct LIBERO init states.

Mirrors env_server.py's mapping (rid = first_id + seed % trials) and checks
that seed 0 and every scored seed select pairwise-distinct init-state vectors.
Run with the stack venv; writes a committable report next to the manifest.

Run: .venv/bin/python track/smoke/verify_seed_mapping.py [manifest.json]
Exit: 0 all distinct, 1 any collision.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from liberopro.liberopro.benchmark import get_benchmark  # noqa: E402


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    manifest_path = Path(args[0]) if args else REPO / "track/manifests/core_v1.json"
    manifest = json.loads(manifest_path.read_text())
    report_path = manifest_path.with_name(manifest_path.stem + "_seed_check.txt")

    lines = [f"Seed-mapping verification for {manifest_path.name}",
             "rule: rid = first_id + (seed % trials)  (env_server.py:90-92)", ""]
    ok = True
    for cell in manifest["cells"]:
        suite_name, task_id = cell["suite"], cell["task_id"]
        seeds = [0] + sorted(e["seed"] for e in cell["seeds"]
                             if not e["bootstrap_only"])
        suite = get_benchmark(suite_name)()
        states = np.asarray(suite.get_task_init_states(task_id))
        trials = len(states)
        rids = [s % trials for s in seeds]
        sel = states[rids]
        unique = len({tuple(r) for r in sel.round(10).tolist()})
        cell_ok = unique == len(seeds)
        ok &= cell_ok
        lines.append(
            f"{suite_name} t{task_id}: trials={trials} seeds={seeds} "
            f"rids={rids} distinct_states={unique}/{len(seeds)} "
            f"{'OK' if cell_ok else 'COLLISION'}")
        lines.append(f"    language: {suite.get_task(task_id).language}")
    lines.append("")
    lines.append("RESULT: " + ("all distinct" if ok else "COLLISION FOUND"))
    report = "\n".join(lines) + "\n"
    report_path.write_text(report)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it and check the report.**

```bash
.venv/bin/python track/smoke/verify_seed_mapping.py
```

Expected: prints 4 cells, each `distinct_states=6/6 OK`, `RESULT: all distinct`, exit 0. Report written to `track/manifests/core_v1_seed_check.txt`.

- [ ] **Step 3: Commit (report included — it is the freeze evidence)**

```bash
git add track/smoke/verify_seed_mapping.py track/manifests/core_v1_seed_check.txt
git commit -m "feat: seed-mapping verifier + committed core_v1 seed-check evidence"
```

---

### Task 4: `run_direct.py` — the rollout driver

**Files:**
- Create: `track/launchers/run_direct.py`

No pytest (GPU/server driver; pure parts already tested in Task 1; validated
end-to-end in Task 6). Syntax gate: `py_compile`.

- [ ] **Step 1: Write `track/launchers/run_direct.py`:**

```python
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
    direct_lib.select_cell(manifest, args.suite, args.task_id, args.seed)
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
```

- [ ] **Step 2: Syntax + import gate (dev venv can compile; imports need stack venv):**

```bash
PYTHONPATH= .venv-dev/bin/python -m py_compile track/launchers/run_direct.py && echo COMPILE-OK
.venv/bin/python -c "import ast, pathlib; ast.parse(pathlib.Path('track/launchers/run_direct.py').read_text()); print('AST-OK')"
```

Expected: `COMPILE-OK`, `AST-OK`.

- [ ] **Step 3: Full dev suite still green:**
Run: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests -q`
Expected: 79 passed (64 prior + 15 direct_lib).

- [ ] **Step 4: Commit**

```bash
git add track/launchers/run_direct.py
git commit -m "feat: run_direct - direct baseline rollout driver with budget gates"
```

---

### Task 5: Baseline design note + registry v1 freeze

**Files:**
- Create: `track/registry/baseline_design.md`
- Modify: `track/registry/experiment_registry.md` (append v1 row)

- [ ] **Step 1: Write `track/registry/baseline_design.md`:**

```markdown
# Direct-baseline design (frozen Day 3, 2026-07-26)

Per the internship plan's design-reference decision, the paper's baseline is a
continuous end-to-end pi-RLinf rollout. Of the two sanctioned implementations
we freeze **(b): a minimal loop streaming vla_server action chunks conditioned
on the full task instruction until the benchmark predicate fires or the step
cap is hit** (`track/launchers/run_direct.py`). Rationale: (a) the RLinf eval
pipeline is a training-repo artifact with its own runner/logging conventions;
(b) reuses exactly the smoke-tested servers and gives us schema-native
run_meta/result_row artifacts with full budget control.

## Frozen parameters (experiment v1)

| Item | Value | Shared with harness? |
|---|---|---|
| Checkpoint | RLinf-Pi05-LIBERO-130-fullshot-SFT, sha256 4d9089c9... (model.safetensors) | identical (frozen, never fine-tuned) |
| Cameras | env defaults: agentview `main_images` 256x256 + wrist 256x256, both fed to pi0.5 | identical (env_server init_params) |
| Action chunking | model-native 5-step chunks (`pi05_libero`, action_dim 7); every chunk executed in full unless the predicate fires mid-chunk | identical model config |
| Step cap | 600 env steps scored by the driver; the env's internal horizon runs at 620 (+20 slack because LiberoEnv's reset burns 15 settle steps of robosuite's horizon counter — see run_direct.py; discovered Day 3 when equal horizons crashed at step 585) | shared where shared: harness scored runs use the strict regime; any step-cap difference is recorded at the Day-5 freeze |
| Wall cap | 1800 s per rollout | same for harness |
| Instruction | full `env.get_task_language()` string every predict call | harness composes its own vla_act prompts (by design) |
| Scoring | success iff `terminated` (benchmark predicate) fires before budgets; vla stop-predicates/self-reports never score | identical rule |

## Core matrix (frozen in track/manifests/core_v1.json)

4 cells x seeds s1-s5, task id 2 per suite (predeclared, matches the RPent
README example; no outcome-based selection): libero_spatial_task (Spatial-T,
paper 42->94), libero_goal_task (Goal-T, 45->87), libero_goal_swap (Goal-S,
42->87), libero_object_swap (Object-S, 78->90, honest hard case). Seed
distinctness evidence: track/manifests/core_v1_seed_check.txt.

## Validity mapping (schemas vocabulary)

- predicate fired -> success / "benchmark_predicate"
- step cap -> budget_exhausted / "step_budget" (scored failure)
- wall cap -> budget_exhausted / "wall_time" (scored failure)
- env truncated early -> valid_failure / "env_truncated"
- launcher exception -> infra_failure + traceback evidence (never scored, rerun candidate)
```

- [ ] **Step 2: Append the v1 row to `track/registry/experiment_registry.md`** (after the v0 row):

```markdown
| v1 | 2026-07-26 | none — direct condition has no planner | n/a (no planner prompts) | Minimal chunk-stream loop via vla_server (track/registry/baseline_design.md) | none | Core matrix frozen: 4 suites × t2 × s1–s5 (core_v1.json); budgets 600 steps / 1800 s; harness condition to be added at the Day-5 freeze |
```

- [ ] **Step 3: Commit**

```bash
git add track/registry/baseline_design.md track/registry/experiment_registry.md
git commit -m "docs: freeze baseline design (b) + experiment v1 registry row"
```

---

### Task 6: Two supervised validation rollouts (Day-3 gate)

No new files (evidence lands in gitignored `artifacts/runs/`). The Day-3 gate:
**at least two valid direct rollouts finish with trustworthy success/failure
labels and retained evidence.** Policy failures are fine; only
`infra_failure` fails the gate.

- [ ] **Step 1: Boot the VLA server once (background, stdin held open):**

```bash
cd /home/demo/github_sow_harnessVLA
source track/setup/track_env.sh   # provides PI05_CHECKPOINT_PATH
sleep infinity | .venv/bin/python RPent/robots/libero/vla_server.py \
    --transport http --host 127.0.0.1 --port 18473 \
    > artifacts/smoke/vla_server_day3.log 2>&1 &
```

Wait until `grep "RPC server listening" artifacts/smoke/vla_server_day3.log`
succeeds (~130 s — model load blocks the listener).

- [ ] **Step 2: Rollout 1 — the smoke-tested cell:**

```bash
.venv/bin/python track/launchers/run_direct.py \
    --suite libero_object_swap --task-id 2 --seed 1 \
    --vla-endpoint http://127.0.0.1:18473
```

Expected: JSON result row printed; exit 0; `validity` ∈ {success,
valid_failure, budget_exhausted}. A 600-step budget_exhausted run takes
~120 chunks ≈ 3–6 min.

- [ ] **Step 3: Rollout 2 — a different family and perturbation:**

```bash
.venv/bin/python track/launchers/run_direct.py \
    --suite libero_spatial_task --task-id 2 --seed 1 \
    --vla-endpoint http://127.0.0.1:18473
```

Expected: same shape of output, exit 0.

- [ ] **Step 4: Ledger + evidence audit:**

```bash
.venv/bin/python -m track.analysis.build_ledger \
    --runs-root artifacts/runs --out artifacts/ledger.csv
cat artifacts/ledger.csv
ls artifacts/runs/v1/direct/*/1/*/
```

Expected: `ledger: 2 scored rows` (0 seed-0, 0 incomplete); each run dir has
`run_meta.json`, `result_row.json`, `frame_first.png`, `frame_last.png`,
`env_server.log`. Open both frame pairs and confirm the scene moved
(trustworthy-label spot check: a `success` row should show the object at its
goal; a failure row should not).

- [ ] **Step 5: Shut the VLA server down and record the gate:**

```bash
pkill -f "vla_server.py --transport http --host 127.0.0.1 --port 18473" || true
```

Append the gate evidence to `track/setup/setup_notes.md` under a new
`## Day-3 gate (2026-07-26)` heading: the two ledger rows (validity, steps,
wall_seconds) and the run-dir paths.

- [ ] **Step 6: Commit + push**

```bash
git add track/setup/setup_notes.md
git commit -m "docs: Day-3 gate evidence - two valid supervised direct rollouts"
```

---

### Task 7: Wrap-up — merge and tag

- [ ] **Step 1:** Full dev suite: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests -q` → 79 passed.
- [ ] **Step 2:** `git checkout main && git merge day3-direct-baseline --no-edit && git push origin main`
- [ ] **Step 3:** Tag: `git tag -a day3-baseline-frozen -m "Day 3: core matrix v1 frozen, direct baseline validated (2 supervised rollouts)" && git push origin day3-baseline-frozen`

---

## Explicitly deferred (do NOT build now)

- **Overnight direct queue** (4 tasks × 2 seeds) — the internship plan schedules it after this gate; needs a supervised pilot sign-off first (mentor gate).
- **Batch runner** (manifest-driven, resume, health checks) — Day 6; `run_direct.py` deliberately stays single-rollout.
- **Harness condition cells + strict-regime budgets** — Day-5 protocol freeze (new registry version).
- **vla_server port/lifecycle management** — the Day-6 runner owns it; today it is booted manually once per session.
