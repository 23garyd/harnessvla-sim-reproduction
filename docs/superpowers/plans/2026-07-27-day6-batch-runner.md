# Day-6 Batch Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A manifest-driven batch runner over both frozen conditions with resume-without-overwrite, health/budget gates, a harness launcher + harness-condition run records, and summary-vs-raw validation — proven by a supervised pilot (the Day-6 gate).

**Architecture:** `harness_lib.py` owns harness records and outcome parsing from rpent's own artifacts (`states.json` last-entry `libero_terminated` is the only success source; planner self-reports never score). `run_harness.py` wraps the rpent CLI with the registry-v2 pins (key-strip, wall-cap kill of the process group, stray sweep, result_row always written). `batch_runner.py` plans pending cells from the derived ledger (skip valid rows; infra-only retry, cap 2), boots a shared VLA server only when direct cells are pending, dispatches launchers sequentially, and verifies every new row against raw artifacts before proceeding.

**Tech Stack:** Python 3.10 stdlib + existing `track.analysis.*` / `track.launchers.direct_lib`; pytest in `.venv-dev`.

**Session conventions:** pytest always `PYTHONPATH= .venv-dev/bin/python -m pytest ...`; stdin of any RPent server stays an OPEN pipe; servers may exit −6 after clean shutdown; the SDK resolves relative paths against RPent root → sweep `RPent/artifacts` after every harness run (preserve, never delete); work on branch `day6-batch-runner`.

**Verified artifact contract (Day-6 investigation):** rpent output dir contains `states.json` = list of per-command entries — last entry has `libero_terminated` (bool, authoritative predicate), each entry has `command.action` (None for the initial observe) and `result.steps_used`; `transcript_*.json` has `stats.turns_used`, `stats.elapsed_s`, `model`, and `finish.status` (diagnostic only). Registry-v2 pins: `--model claude-opus-4-8 --max-turns 60 --planner-timeout-s 1200 --max-episode-steps 1220` (= 1200 guide budget + 20 settle margin), wall cap 2400 s, keys stripped.

---

### Task 1: `manifests.py` — require `task_id` in cells

**Files:**
- Modify: `track/analysis/manifests.py` (cell validation loop)
- Modify: `track/tests/test_manifests.py` (fixture + new test)

- [ ] **Step 1: Write the failing test.** In `track/tests/test_manifests.py`, FIRST update the fixture — add `"task_id": 2, "task": "libero_goal_swap_t2"` keys to the cell in `valid_manifest()` so it reads:

```python
        "cells": [
            {"condition": "direct", "suite": "libero_goal_swap",
             "task": "libero_goal_swap_t2", "task_id": 2,
             "seeds": [
                 {"seed": 0, "bootstrap_only": True},
                 {"seed": 1, "bootstrap_only": False},
                 {"seed": 2, "bootstrap_only": False},
             ]},
        ],
```

Then APPEND:

```python
def test_missing_task_id_fails():
    m = valid_manifest()
    del m["cells"][0]["task_id"]
    with pytest.raises(ValueError, match="task_id"):
        manifests.validate_manifest(m)
```

- [ ] **Step 2: Run to verify it fails** (`PYTHONPATH= .venv-dev/bin/python -m pytest track/tests/test_manifests.py -v`): the new test FAILS (no task_id validation); the other 11 still pass with the enriched fixture.

- [ ] **Step 3: Implement.** In `track/analysis/manifests.py`, inside the per-cell loop, directly after the `condition/suite/task` str checks, insert:

```python
        if not isinstance(cell.get("task_id"), int) or isinstance(cell.get("task_id"), bool):
            raise ValueError(f"{where}: 'task_id' must be int")
```

- [ ] **Step 4: Run to verify.** File: 12 PASS. Full suite: 83 passed (both real manifests already carry task_id).

- [ ] **Step 5: Commit** `git add track/analysis/manifests.py track/tests/test_manifests.py && git commit -m "feat: manifests require task_id (matcher already consumes it)"`

---

### Task 2: `harness_lib.py` — harness records + outcome parsing

**Files:**
- Create: `track/launchers/harness_lib.py`
- Test: `track/tests/test_harness_lib.py`

- [ ] **Step 1: Write the failing tests.** Create `track/tests/test_harness_lib.py`:

```python
import json

import pytest

from track.analysis import build_ledger
from track.launchers import direct_lib, harness_lib


def write_rpent_dir(tmp_path, *, terminated=True, finish_status="success",
                    turns=23, elapsed=264.3, with_states=True):
    d = tmp_path / "rpent"
    d.mkdir(parents=True, exist_ok=True)
    if with_states:
        states = [
            {"command": None, "result": {"steps_used": 0},
             "libero_terminated": False},
            {"command": {"action": "move_to"}, "result": {"steps_used": 12},
             "libero_terminated": False},
            {"command": {"action": "pi0_pick"}, "result": {"steps_used": 20},
             "libero_terminated": False},
            {"command": {"action": "move_to"}, "result": {"steps_used": 7},
             "libero_terminated": False},
            {"command": {"action": "release"}, "result": {"steps_used": 8},
             "libero_terminated": terminated},
        ]
        (d / "states.json").write_text(json.dumps(states))
    (d / "transcript_x.json").write_text(json.dumps({
        "stats": {"turns_used": turns, "elapsed_s": elapsed},
        "finish": {"status": finish_status},
        "model": "claude-opus-4-8",
    }))
    return d


BUDGETS = {"max_steps": 1200, "max_turns": 60, "max_wall_seconds": 2400}


def test_parse_outcome(tmp_path):
    d = write_rpent_dir(tmp_path)
    o = harness_lib.parse_harness_outcome(d)
    assert o["success"] is True
    assert o["steps"] == 47
    assert o["turns"] == 23
    assert o["vla_act_calls"] == 1     # pi0_pick
    assert o["analytic_calls"] == 3    # move_to x2 + release; initial None ignored
    assert o["wall_s"] == 264.3


def test_planner_selfreport_never_scores(tmp_path):
    # finish.status says success but the predicate never fired -> not success.
    d = write_rpent_dir(tmp_path, terminated=False, finish_status="success")
    o = harness_lib.parse_harness_outcome(d)
    assert o["success"] is False
    assert o["planner_finish_status"] == "success"


def test_parse_missing_states_raises(tmp_path):
    d = write_rpent_dir(tmp_path, with_states=False)
    with pytest.raises(ValueError, match="states.json"):
        harness_lib.parse_harness_outcome(d)


def test_parse_empty_states_raises(tmp_path):
    d = write_rpent_dir(tmp_path)
    (d / "states.json").write_text("[]")
    with pytest.raises(ValueError, match="empty or malformed"):
        harness_lib.parse_harness_outcome(d)


def test_resolve_mapping():
    o = {"success": True, "steps": 100, "turns": 10, "wall_s": 300.0}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("success", "benchmark_predicate")
    o = {"success": False, "steps": 100, "turns": 60, "wall_s": 300.0}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("budget_exhausted", "turn_budget")
    o = {"success": False, "steps": 1200, "turns": 10, "wall_s": 300.0}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("budget_exhausted", "step_budget")
    o = {"success": False, "steps": 100, "turns": 10, "wall_s": 2400.0}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("budget_exhausted", "wall_time")
    o = {"success": False, "steps": 100, "turns": 10, "wall_s": 300.0}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("valid_failure", "planner_finished_without_predicate")


def test_infra_row_from_empty_outcome():
    row = harness_lib.build_harness_result_row(
        outcome=harness_lib.empty_outcome(), validity="infra_failure",
        terminal_reason="exception", evidence="Traceback ...")
    assert row["validity"] == "infra_failure"
    assert row["counts"]["turns"] == 0


def test_meta_and_row_survive_ledger(tmp_path):
    run_dir = direct_lib.make_run_dir(tmp_path, "v2", "harness",
                                      "libero_goal_swap", 2, 3,
                                      "20260727T120000")
    meta = harness_lib.build_harness_run_meta(
        exp_version="v2", suite="libero_goal_swap", task_id=2, seed=3,
        budgets=BUDGETS, rpent_commit="6e4ba1805a459d74ad53569e833bae7ae2c59985",
        checkpoint_sha256="4d9089c9", launch_command="run_harness.py ...")
    (run_dir / "run_meta.json").write_text(json.dumps(meta))
    d = write_rpent_dir(run_dir)
    o = harness_lib.parse_harness_outcome(d)
    v, r = harness_lib.resolve_harness_outcome(o, BUDGETS)
    row = harness_lib.build_harness_result_row(outcome=o, validity=v,
                                               terminal_reason=r)
    (run_dir / "result_row.json").write_text(json.dumps(row))
    rows, _, _ = build_ledger.build_ledger(tmp_path)
    assert len(rows) == 1
    assert rows[0]["condition"] == "harness"
    assert rows[0]["turns"] == 23
    assert rows[0]["planner_model"] == harness_lib.PLANNER_MODEL
```

- [ ] **Step 2: Run to verify collection ERROR** (module missing).

- [ ] **Step 3: Write `track/launchers/harness_lib.py`:**

```python
"""Harness-condition run records + outcome parsing (experiment v2).

Success comes ONLY from the last states.json entry's `libero_terminated`
(the benchmark predicate). Planner self-reports (`finish.status`) are kept
as diagnostics and never score. All records go through
track.analysis.schemas so build_ledger consumes harness run dirs unchanged.
"""
import json
from pathlib import Path

from track.analysis.schemas import validate_result_row, validate_run_meta
from track.launchers.direct_lib import task_key

CONDITION = "harness"
PLANNER_MODEL = "claude_code/claude-opus-4-8"
PLANNER_SETTINGS = {
    "max_turns": 60,
    "planner_timeout_s": 1200,
    "max_episode_steps": 1220,
    "sdk": "claude_agent_sdk defaults",
    "billing": "subscription (ANTHROPIC/OPENAI keys stripped)",
}
VLA_PRIMITIVES = {"pi0_pick", "pi0_doubled"}


def build_harness_run_meta(*, exp_version, suite, task_id, seed, budgets,
                           rpent_commit, checkpoint_sha256, launch_command):
    return validate_run_meta({
        "exp_version": exp_version,
        "condition": CONDITION,
        "task": task_key(suite, task_id),
        "suite": suite,
        "seed": seed,
        "planner_model": PLANNER_MODEL,
        "planner_settings": dict(PLANNER_SETTINGS),
        "prompt_hashes": {
            "released_assets": f"pinned via RPENT_COMMIT {rpent_commit}"},
        "rpent_commit": rpent_commit,
        "checkpoint_sha256": checkpoint_sha256,
        "budgets": dict(budgets),
        "launch_command": launch_command,
    })


def empty_outcome():
    """Outcome shell for infra rows when no artifacts exist."""
    return {"success": False, "steps": 0, "turns": 0, "vla_act_calls": 0,
            "analytic_calls": 0, "wall_s": 0.0, "planner_finish_status": None}


def parse_harness_outcome(rpent_dir):
    """Parse one rpent output dir into an outcome dict. Raises ValueError
    (naming the offending path) on missing/corrupt artifacts."""
    rpent_dir = Path(rpent_dir)
    states_path = rpent_dir / "states.json"
    if not states_path.exists():
        raise ValueError(f"{states_path}: missing states.json")
    states = json.loads(states_path.read_text())
    if not isinstance(states, list) or not states:
        raise ValueError(f"{states_path}: empty or malformed")
    steps = vla_calls = analytic_calls = 0
    for entry in states:
        result = entry.get("result")
        if isinstance(result, dict):
            steps += int(result.get("steps_used", 0) or 0)
        cmd = entry.get("command")
        action = cmd.get("action") if isinstance(cmd, dict) else None
        if action in VLA_PRIMITIVES:
            vla_calls += 1
        elif action is not None:
            analytic_calls += 1
    transcripts = sorted(rpent_dir.glob("transcript_*.json"))
    if not transcripts:
        raise ValueError(f"{rpent_dir}: no transcript_*.json")
    t = json.loads(transcripts[0].read_text())
    stats = t.get("stats") or {}
    return {
        "success": bool(states[-1].get("libero_terminated")),
        "steps": steps,
        "turns": int(stats.get("turns_used", 0) or 0),
        "vla_act_calls": vla_calls,
        "analytic_calls": analytic_calls,
        "wall_s": float(stats.get("elapsed_s", 0.0) or 0.0),
        "planner_finish_status": (t.get("finish") or {}).get("status"),
    }


def resolve_harness_outcome(outcome, budgets):
    """Map a parsed outcome to (validity, terminal_reason). Predicate wins."""
    if outcome["success"]:
        return "success", "benchmark_predicate"
    if outcome["turns"] >= budgets["max_turns"]:
        return "budget_exhausted", "turn_budget"
    if outcome["steps"] >= budgets["max_steps"]:
        return "budget_exhausted", "step_budget"
    if outcome["wall_s"] >= budgets["max_wall_seconds"]:
        return "budget_exhausted", "wall_time"
    return "valid_failure", "planner_finished_without_predicate"


def build_harness_result_row(*, outcome, validity, terminal_reason,
                             evidence=None):
    row = {
        "success": bool(outcome["success"]) and validity == "success",
        "terminal_reason": terminal_reason,
        "validity": validity,
        "counts": {"steps": outcome["steps"], "turns": outcome["turns"],
                   "vla_act_calls": outcome["vla_act_calls"],
                   "analytic_calls": outcome["analytic_calls"]},
        "wall_seconds": round(float(outcome["wall_s"]), 1),
    }
    if outcome.get("planner_finish_status") is not None:
        row["planner_finish_status"] = outcome["planner_finish_status"]
    if evidence is not None:
        row["evidence"] = evidence
    return validate_result_row(row)
```

- [ ] **Step 4: Run to verify.** File: 7 PASS. Full suite: 90 passed.
- [ ] **Step 5: Commit** `git add track/launchers/harness_lib.py track/tests/test_harness_lib.py && git commit -m "feat: harness_lib - v2 records, predicate-only outcome parsing"`

---

### Task 3: `run_harness.py` — the harness rollout driver

**Files:**
- Create: `track/launchers/run_harness.py`

No pytest (GPU/planner driver; parsing/records tested in Task 2; live validation in Task 6). Gate: py_compile.

- [ ] **Step 1: Write `track/launchers/run_harness.py`:**

```python
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
```

CAUTION (encode as written): the pkill backstop kills ANY libero server —
the batch runner must never leave a shared direct-condition VLA server up
across a harness launch (Task 4 sequences direct phase → stop shared VLA →
harness phase).

- [ ] **Step 2: Gates.** `PYTHONPATH= .venv-dev/bin/python -m py_compile track/launchers/run_harness.py && echo COMPILE-OK`; full suite still 90.
- [ ] **Step 3: Commit** `git add track/launchers/run_harness.py && git commit -m "feat: run_harness - v2-pinned rpent wrapper with wall-cap kill and stray sweep"`

---

### Task 4: `batch_runner.py` — manifest-driven queue with resume

**Files:**
- Create: `track/launchers/batch_runner.py`
- Test: `track/tests/test_batch_runner.py`

- [ ] **Step 1: Write the failing tests.** Create `track/tests/test_batch_runner.py`:

```python
import json

import pytest

from track.launchers import batch_runner, direct_lib, harness_lib


def manifest():
    return {
        "exp_version": "v2",
        "budgets": {"max_steps": 1200, "max_turns": 60,
                    "max_wall_seconds": 2400},
        "caps": {"max_rollouts": 24, "max_tokens_per_rollout": 0},
        "cells": [
            {"condition": "harness", "suite": "libero_goal_swap",
             "task": "libero_goal_swap_t2", "task_id": 2,
             "seeds": [{"seed": 0, "bootstrap_only": True},
                       {"seed": 1, "bootstrap_only": False},
                       {"seed": 2, "bootstrap_only": False}]},
        ],
    }


def row(seed, validity, exp="v2", condition="harness",
        task="libero_goal_swap_t2"):
    return {"exp_version": exp, "condition": condition, "task": task,
            "seed": seed, "validity": validity}


def test_plan_pending_all_missing():
    pending, exhausted = batch_runner.plan_pending(manifest(), [])
    assert [c["seed"] for c in pending] == [1, 2]
    assert all(c["condition"] == "harness" and c["task_id"] == 2
               for c in pending)
    assert exhausted == []


def test_plan_pending_skips_valid_rows():
    rows = [row(1, "success")]
    pending, _ = batch_runner.plan_pending(manifest(), rows)
    assert [c["seed"] for c in pending] == [2]
    rows = [row(1, "valid_failure")]  # scored failure also counts as done
    pending, _ = batch_runner.plan_pending(manifest(), rows)
    assert [c["seed"] for c in pending] == [2]


def test_plan_pending_retries_single_infra():
    rows = [row(1, "infra_failure")]
    pending, exhausted = batch_runner.plan_pending(manifest(), rows)
    assert [c["seed"] for c in pending] == [1, 2]
    assert exhausted == []


def test_plan_pending_exhausts_after_two_infra():
    rows = [row(1, "infra_failure"), row(1, "infra_failure")]
    pending, exhausted = batch_runner.plan_pending(manifest(), rows)
    assert [c["seed"] for c in pending] == [2]
    assert [c["seed"] for c in exhausted] == [1]


def test_plan_pending_ignores_other_versions_and_conditions():
    rows = [row(1, "success", exp="v1"),
            row(2, "success", condition="direct")]
    pending, _ = batch_runner.plan_pending(manifest(), rows)
    assert [c["seed"] for c in pending] == [1, 2]


def make_run(tmp_path, terminated=True, row_success=True):
    run_dir = direct_lib.make_run_dir(tmp_path, "v2", "harness",
                                      "libero_goal_swap", 2, 1,
                                      "20260727T120000")
    meta = harness_lib.build_harness_run_meta(
        exp_version="v2", suite="libero_goal_swap", task_id=2, seed=1,
        budgets={"max_steps": 1200, "max_turns": 60,
                 "max_wall_seconds": 2400},
        rpent_commit="6e4ba1805a459d74ad53569e833bae7ae2c59985",
        checkpoint_sha256="4d9089c9", launch_command="x")
    (run_dir / "run_meta.json").write_text(json.dumps(meta))
    rpent = run_dir / "rpent"
    rpent.mkdir()
    (rpent / "states.json").write_text(json.dumps(
        [{"command": {"action": "release"}, "result": {"steps_used": 5},
          "libero_terminated": terminated}]))
    (rpent / "transcript_x.json").write_text(json.dumps(
        {"stats": {"turns_used": 9, "elapsed_s": 100.0},
         "finish": {"status": "success"}}))
    o = harness_lib.parse_harness_outcome(rpent)
    o["success"] = row_success
    v, r = ("success", "benchmark_predicate") if row_success else \
        ("valid_failure", "planner_finished_without_predicate")
    result = harness_lib.build_harness_result_row(
        outcome=o, validity=v, terminal_reason=r)
    (run_dir / "result_row.json").write_text(json.dumps(result))
    return run_dir


def test_verify_row_ok(tmp_path):
    run_dir = make_run(tmp_path, terminated=True, row_success=True)
    batch_runner.verify_row(run_dir)  # no raise


def test_verify_row_detects_mismatch(tmp_path):
    # row claims success but states.json predicate never fired
    run_dir = make_run(tmp_path, terminated=False, row_success=True)
    with pytest.raises(ValueError, match="disagrees with states.json"):
        batch_runner.verify_row(run_dir)


def test_queue_record_written(tmp_path):
    pending = [{"condition": "harness", "suite": "libero_goal_swap",
                "task_id": 2, "seed": 1}]
    path = batch_runner.write_queue_record(
        tmp_path, ["m1.json"], pending, limit=5, ts="20260727T120000")
    rec = json.loads(path.read_text())
    assert rec["planned"] == pending
    assert rec["limit"] == 5
    with pytest.raises(FileExistsError):
        batch_runner.write_queue_record(
            tmp_path, ["m1.json"], pending, limit=5, ts="20260727T120000")
```

- [ ] **Step 2: Run to verify collection ERROR** (module missing).

- [ ] **Step 3: Write `track/launchers/batch_runner.py`:**

```python
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


def plan_pending(manifest, ledger_rows, max_infra_attempts=MAX_INFRA_ATTEMPTS):
    """Return (pending, exhausted) cell dicts in manifest order."""
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
        raw = bool(states[-1].get("libero_terminated")) if states else False
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
        pending, exhausted = plan_pending(manifest, rows)
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
```

- [ ] **Step 4: Run to verify.** File: 8 PASS. Full suite: 98 passed. py_compile batch_runner.
- [ ] **Step 5: Commit** `git add track/launchers/batch_runner.py track/tests/test_batch_runner.py && git commit -m "feat: batch runner - resume without overwrite, infra retry cap, raw verification"`

---

### Task 5: `build_ledger.py` print wording (scored vs infra)

**Files:**
- Modify: `track/analysis/build_ledger.py` (main's print)
- Modify: `track/tests/test_build_ledger.py` (append one test)

- [ ] **Step 1: Failing test.** Append to `track/tests/test_build_ledger.py`:

```python
def test_main_print_separates_scored_and_infra(tmp_path, capsys):
    write_run(tmp_path, seed=1, ts="20260727T000001")
    write_run(tmp_path, seed=2, ts="20260727T000002", success=False,
              validity="infra_failure", evidence="server crash: log ...")
    out = tmp_path / "ledger.csv"
    build_ledger.main(["--runs-root", str(tmp_path), "--out", str(out)])
    text = capsys.readouterr().out
    assert "2 rows (1 scored, 1 infra_failure)" in text
```

- [ ] **Step 2: Verify it fails** (current wording says "2 scored rows").
- [ ] **Step 3: Implement.** In `build_ledger.main`, replace the print with:

```python
    infra = sum(1 for r in rows if r["validity"] == "infra_failure")
    print(f"ledger: {len(rows)} rows ({len(rows) - infra} scored, "
          f"{infra} infra_failure) -> {args.out} "
          f"(excluded: {skipped_seed0} seed-0 bootstrap, "
          f"{incomplete} incomplete)")
```

- [ ] **Step 4: Verify.** Ledger file: 11 PASS. Full suite: 99 passed.
- [ ] **Step 5: Commit** `git add track/analysis/build_ledger.py track/tests/test_build_ledger.py && git commit -m "fix: ledger print separates scored from infra rows"`

---

### Task 6: Supervised pilot — the Day-6 gate (LIVE, needs GPU + planner)

Gate: **a stopped batch resumes without overwriting evidence, and summaries
match raw outcomes for every pilot trial.**

- [ ] **Step 1: Resume proof over existing evidence (no spend):**

```bash
PYTHONPATH= .venv/bin/python track/launchers/batch_runner.py \
    --manifests track/manifests/core_v1.json --dry-run
```

Expected: `core_v1.json: 20 scored cells, 20 already valid, 0 pending, 0 exhausted` — the completed direct arm is honored, nothing re-runs.

- [ ] **Step 2: One live harness cell (limit-stopped batch):**

```bash
PYTHONPATH= .venv/bin/python track/launchers/batch_runner.py \
    --manifests track/manifests/harness_v2.json --limit 1
```

Expected: queue record written; first pending cell (manifest order → `libero_spatial_task` t2 s1 — harness on the weakest direct cell) launches via run_harness; on completion the runner prints `verified: validity=...`; ledger rebuilt. Any validity except infra_failure is a pass for the gate (exit 0). Takes ~10–20 min (servers boot ~4 min + planner episode).

- [ ] **Step 3: Resume-after-stop proof (no spend):**

```bash
PYTHONPATH= .venv/bin/python track/launchers/batch_runner.py \
    --manifests track/manifests/harness_v2.json --dry-run
```

Expected: `19 pending` (the Step-2 cell now `already valid`, NOT re-listed) — the limit-stopped batch resumed and skipped completed work. Also confirm no overwrite: `ls artifacts/runs/v2/harness/libero_spatial_task_t2/1/` shows exactly ONE timestamp dir.

- [ ] **Step 4: Summary-vs-raw audit of the pilot row:** print the row and re-derive from raw:

```bash
cat artifacts/runs/v2/harness/libero_spatial_task_t2/1/*/result_row.json
.venv/bin/python -c "
import json, glob
d = sorted(glob.glob('artifacts/runs/v2/harness/libero_spatial_task_t2/1/*/rpent/states.json'))[-1]
print('raw predicate:', json.load(open(d))[-1].get('libero_terminated'))"
```

Expected: row `success` equals the raw predicate (the runner already verified this — this is the human-visible double check).

- [ ] **Step 5: Record the gate.** Append `## Day-6 gate (2026-07-27)` to `track/setup/setup_notes.md`: Step-1/3 outputs (resume + skip counts), the pilot row (cell, validity, reason, steps/turns/wall), the no-overwrite listing, and the raw-vs-row agreement. Commit: `git add track/setup/setup_notes.md && git commit -m "docs: Day-6 gate evidence - resume without overwrite + raw-verified pilot"`

---

### Task 7: Wrap-up

- [ ] **Step 1:** Full dev suite → 99 passed; `git status --porcelain` clean.
- [ ] **Step 2:** Merge + push: `git checkout main && git merge day6-batch-runner --no-edit && git push origin main && git branch -d day6-batch-runner`
- [ ] **Step 3:** Tag: `git tag -a day6-batch-runner -m "Day 6: manifest-driven batch runner, gate passed (resume without overwrite, raw-verified rows)" && git push origin day6-batch-runner`
- [ ] **Step 4:** Append the Day-6 entry to `track/registry/progress_log.md` + registry change-log row; commit + push.

---

## Explicitly deferred (do NOT build now)

- **The full 20-cell harness matrix queue** — runs after the gate, on the coordinator/mentor's go (planner spend ~20 rollouts).
- **compare.py / Wilson intervals** — Day 8 per the internship plan.
- **`/loop 30m` queue triage automation** — manual triage is fine while queues are attended.
- **Parallel/multi-GPU dispatch** — sequential is the frozen protocol for now.
- **Direct-runner infra-evidence enrichment (RpcError.server_traceback, vla-log slice)** — the direct arm is complete; enrich `run_direct.py` only if direct reruns are ever needed (recorded pick-up stays open).
