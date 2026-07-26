import pytest

from track.analysis import schemas


def valid_meta():
    return {
        "exp_version": "v1",
        "condition": "direct",
        "task": "task_a",
        "suite": "libero_goal_task",
        "seed": 1,
        "planner_model": "claude_code/claude-fable-5",
        "planner_settings": {"max_turns": 40},
        "prompt_hashes": {"system.py": "abc123"},
        "rpent_commit": "deadbeef",
        "checkpoint_sha256": "cafe01",
        "budgets": {"max_steps": 400, "max_turns": 40, "max_wall_seconds": 1800},
        "launch_command": "rpent --env libero ...",
    }


def valid_row():
    return {
        "success": True,
        "terminal_reason": "benchmark_predicate",
        "validity": "success",
        "counts": {"steps": 120, "turns": 9, "vla_act_calls": 2, "analytic_calls": 6},
        "wall_seconds": 301.5,
    }


def test_valid_meta_passes():
    schemas.validate_run_meta(valid_meta())


def test_meta_missing_key_fails():
    m = valid_meta()
    del m["rpent_commit"]
    with pytest.raises(ValueError, match="rpent_commit"):
        schemas.validate_run_meta(m)


def test_meta_missing_budget_key_fails():
    m = valid_meta()
    del m["budgets"]["max_turns"]
    with pytest.raises(ValueError, match="max_turns"):
        schemas.validate_run_meta(m)


def test_meta_wrong_type_fails():
    m = valid_meta()
    m["seed"] = "1"
    with pytest.raises(ValueError, match="seed"):
        schemas.validate_run_meta(m)


def test_valid_row_passes():
    schemas.validate_result_row(valid_row())


def test_unknown_validity_fails():
    r = valid_row()
    r["validity"] = "kinda_worked"
    with pytest.raises(ValueError, match="validity"):
        schemas.validate_result_row(r)


def test_success_flag_must_match_validity():
    r = valid_row()
    r["validity"] = "timeout"        # success is still True -> inconsistent
    with pytest.raises(ValueError, match="success"):
        schemas.validate_result_row(r)


def test_infra_failure_requires_evidence():
    r = valid_row()
    r["success"] = False
    r["validity"] = "infra_failure"
    with pytest.raises(ValueError, match="evidence"):
        schemas.validate_result_row(r)
    r["evidence"] = "env_server crashed: see server.log line 812"
    schemas.validate_result_row(r)


def test_missing_count_fails():
    r = valid_row()
    del r["counts"]["vla_act_calls"]
    with pytest.raises(ValueError, match="vla_act_calls"):
        schemas.validate_result_row(r)


def test_valid_failure_row_passes():
    r = valid_row()
    r["success"] = False
    r["validity"] = "valid_failure"
    schemas.validate_result_row(r)


def test_budget_exhausted_row_passes():
    r = valid_row()
    r["success"] = False
    r["validity"] = "budget_exhausted"
    r["terminal_reason"] = "step_budget"
    schemas.validate_result_row(r)


def test_result_row_wrong_type_fails():
    r = valid_row()
    r["success"] = "yes"
    with pytest.raises(ValueError, match="success"):
        schemas.validate_result_row(r)


def test_negative_count_fails():
    r = valid_row()
    r["counts"]["steps"] = -5
    with pytest.raises(ValueError, match="steps"):
        schemas.validate_result_row(r)


def test_non_finite_wall_seconds_fails():
    r = valid_row()
    r["wall_seconds"] = float("nan")
    with pytest.raises(ValueError, match="wall_seconds"):
        schemas.validate_result_row(r)
    r["wall_seconds"] = -1.0
    with pytest.raises(ValueError, match="wall_seconds"):
        schemas.validate_result_row(r)


def test_extra_keys_allowed():
    m = valid_meta()
    m["notes"] = "anything"
    schemas.validate_run_meta(m)
    r = valid_row()
    r["evidence"] = "harmless on non-infra rows"
    schemas.validate_result_row(r)
