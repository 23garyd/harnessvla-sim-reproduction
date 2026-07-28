import json

import pytest

from track.analysis import build_ledger
from track.launchers import direct_lib, harness_lib


def write_rpent_dir(tmp_path, *, terminated=True, finish_status="success",
                    turns=23, elapsed=264.3, with_states=True,
                    stream_records=None):
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
    if stream_records is not None:
        (d / "claude_x.txt.stream.jsonl").write_text(
            "\n".join(json.dumps(r) for r in stream_records) + "\n")
    return d


# Shapes taken verbatim from the 2026-07-28 rate-limited object_swap runs.
RATE_LIMIT_RECORD = {
    "type": "AssistantMessage",
    "content": [{"text": "You've hit your session limit · resets 3:10am"}],
    "model": "<synthetic>", "error": "rate_limit",
}
MAX_TURNS_ERROR_RECORD = {
    "type": "error",
    "message": ("Exception: Claude Code returned an error result: "
                "Reached maximum number of turns (60)"),
}


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


def test_parse_detects_planner_api_error(tmp_path):
    # A synthetic AssistantMessage carrying an error field means the planner
    # backend failed (e.g. subscription session limit) — not a policy result.
    d = write_rpent_dir(tmp_path, terminated=False, turns=1,
                        stream_records=[RATE_LIMIT_RECORD])
    o = harness_lib.parse_harness_outcome(d)
    assert o["planner_api_error"] is not None
    assert "rate_limit" in o["planner_api_error"]


def test_parse_no_stream_means_no_api_error(tmp_path):
    d = write_rpent_dir(tmp_path)
    o = harness_lib.parse_harness_outcome(d)
    assert o["planner_api_error"] is None


def test_parse_max_turns_error_is_not_api_error(tmp_path):
    # rpent surfaces max-turns exhaustion as a bare {"type": "error"} record;
    # that is a budget outcome, not a planner API failure.
    d = write_rpent_dir(tmp_path, terminated=False, turns=60,
                        stream_records=[MAX_TURNS_ERROR_RECORD])
    o = harness_lib.parse_harness_outcome(d)
    assert o["planner_api_error"] is None


def test_resolve_planner_api_error_is_infra():
    o = {"success": False, "steps": 0, "turns": 1, "wall_s": 167.2,
         "planner_api_error": "rate_limit: You've hit your session limit"}
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("infra_failure", "planner_api_error")
    # An API error mid-run invalidates budget readings too (truncated stats).
    o["turns"] = 60
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("infra_failure", "planner_api_error")
    # But the benchmark predicate always wins.
    o["success"] = True
    assert harness_lib.resolve_harness_outcome(o, BUDGETS) == \
        ("success", "benchmark_predicate")


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


def test_predicate_is_cumulative(tmp_path):
    # A transient mid-episode True must count as success even if later
    # entries read False (rlinf success_once semantics).
    d = write_rpent_dir(tmp_path, terminated=False)
    states = json.loads((d / "states.json").read_text())
    states[2]["libero_terminated"] = True
    (d / "states.json").write_text(json.dumps(states))
    o = harness_lib.parse_harness_outcome(d)
    assert o["success"] is True
