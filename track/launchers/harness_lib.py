"""Harness-condition run records + outcome parsing (experiment v2).

Success comes ONLY from `libero_terminated` in states.json (cumulative
across entries). Planner self-reports (`finish.status`) are kept
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
            "analytic_calls": 0, "wall_s": 0.0, "planner_finish_status": None,
            "planner_api_error": None, "planner_timed_out": False}


def _scan_planner_stream(rpent_dir):
    """Scan the raw planner stream for terminal conditions the transcript
    does not record (both observed 2026-07-28):
    - backend-level errors (subscription session limit), surfaced as a
      synthetic AssistantMessage with error="rate_limit" -> api_error;
    - the SDK's planner_timeout_s expiry, a dedicated {"type": "timeout"}
      record -> timed_out.
    Bare {"type": "error"} records are NOT counted: rpent uses those for
    budget outcomes like max-turns."""
    out = {"api_error": None, "timed_out": False}
    for stream in sorted(rpent_dir.glob("*.stream.jsonl")):
        for line in stream.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (out["api_error"] is None
                    and rec.get("type") == "AssistantMessage"
                    and rec.get("error")):
                texts = [c.get("text", "") for c in rec.get("content") or []
                         if isinstance(c, dict)]
                out["api_error"] = \
                    f"{rec['error']}: {' '.join(texts).strip()}"[:500]
            elif rec.get("type") == "timeout":
                out["timed_out"] = True
    return out


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
    stream_scan = _scan_planner_stream(rpent_dir)
    return {
        # Cumulative like rlinf's success_once |= terminations: a transient
        # True scores even if a driver stepped past it (rpent halts on first
        # True today, so this is equivalent on all real artifacts).
        "success": any(bool(e.get("libero_terminated")) for e in states),
        "steps": steps,
        "turns": int(stats.get("turns_used", 0) or 0),
        "vla_act_calls": vla_calls,
        "analytic_calls": analytic_calls,
        "wall_s": float(stats.get("elapsed_s", 0.0) or 0.0),
        "planner_finish_status": (t.get("finish") or {}).get("status"),
        "planner_api_error": stream_scan["api_error"],
        "planner_timed_out": stream_scan["timed_out"],
    }


def resolve_harness_outcome(outcome, budgets):
    """Map a parsed outcome to (validity, terminal_reason). Predicate wins."""
    if outcome["success"]:
        return "success", "benchmark_predicate"
    # A planner backend error (rate limit, API failure) means the policy was
    # never fully exercised: budget/step readings are truncated artifacts of
    # the abort, so this outranks every non-success classification.
    if outcome.get("planner_api_error"):
        return "infra_failure", "planner_api_error"
    if outcome["turns"] >= budgets["max_turns"]:
        return "budget_exhausted", "turn_budget"
    if outcome["steps"] >= budgets["max_steps"]:
        return "budget_exhausted", "step_budget"
    if outcome["wall_s"] >= budgets["max_wall_seconds"]:
        return "budget_exhausted", "wall_time"
    # planner_timeout_s is a pinned v2 regime bound, so its expiry is a
    # budget outcome (the run stays scored), unlike a planner API error.
    if outcome.get("planner_timed_out"):
        return "budget_exhausted", "planner_timeout"
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
