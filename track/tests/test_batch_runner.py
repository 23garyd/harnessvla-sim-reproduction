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


def test_verify_row_uses_cumulative_predicate(tmp_path):
    # Row scored success from a transient mid-episode True; verify must agree.
    run_dir = make_run(tmp_path, terminated=False, row_success=True)
    states_path = run_dir / "rpent" / "states.json"
    states = json.loads(states_path.read_text())
    states.append({"command": {"action": "move_to"},
                   "result": {"steps_used": 3}, "libero_terminated": False})
    states[0]["libero_terminated"] = True
    states_path.write_text(json.dumps(states))
    batch_runner.verify_row(run_dir)  # must NOT raise
