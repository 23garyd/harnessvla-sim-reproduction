"""Validation for the two track-added run records (spec section 3).

run_meta.json  - written at launch, immutable.
result_row.json - written at termination; the only input to the ledger.
Extra/unknown keys are intentionally permitted (forward compatibility).
"""
import math

VALIDITY_STATUSES = {
    "success",
    "valid_failure",
    "infra_failure",
    "timeout",
    "budget_exhausted",
}

_RUN_META_REQUIRED = {
    "exp_version": str,
    "condition": str,
    "task": str,
    "suite": str,
    "seed": int,
    "planner_model": str,
    "planner_settings": dict,
    "prompt_hashes": dict,
    "rpent_commit": str,
    "checkpoint_sha256": str,
    "budgets": dict,
    "launch_command": str,
}

_BUDGETS_REQUIRED = {
    "max_steps": int,
    "max_turns": int,
    "max_wall_seconds": int,
}

_RESULT_ROW_REQUIRED = {
    "success": bool,
    "terminal_reason": str,
    "validity": str,
    "counts": dict,
    "wall_seconds": (int, float),
}

_COUNTS_REQUIRED = {
    "steps": int,
    "turns": int,
    "vla_act_calls": int,
    "analytic_calls": int,
}


def _require(record, spec, where):
    if not isinstance(record, dict):
        raise ValueError(f"{where}: expected dict, got {type(record).__name__}")
    for key, typ in spec.items():
        if key not in record:
            raise ValueError(f"{where}: missing required key '{key}'")
        if not isinstance(record[key], typ) or (
            typ is int and isinstance(record[key], bool)
        ):
            raise ValueError(
                f"{where}: key '{key}' must be {typ}, "
                f"got {type(record[key]).__name__}"
            )


def validate_run_meta(meta):
    _require(meta, _RUN_META_REQUIRED, "run_meta")
    _require(meta["budgets"], _BUDGETS_REQUIRED, "run_meta.budgets")
    return meta


def validate_result_row(row):
    _require(row, _RESULT_ROW_REQUIRED, "result_row")
    _require(row["counts"], _COUNTS_REQUIRED, "result_row.counts")
    for key in _COUNTS_REQUIRED:
        if row["counts"][key] < 0:
            raise ValueError(
                f"result_row.counts: key '{key}' must be >= 0, "
                f"got {row['counts'][key]}"
            )
    ws = row["wall_seconds"]
    if isinstance(ws, bool) or not math.isfinite(ws) or ws < 0:
        raise ValueError(
            f"result_row: wall_seconds must be a finite number >= 0, got {ws!r}"
        )
    if row["validity"] not in VALIDITY_STATUSES:
        raise ValueError(
            f"result_row: unknown validity '{row['validity']}', "
            f"expected one of {sorted(VALIDITY_STATUSES)}"
        )
    if row["success"] != (row["validity"] == "success"):
        raise ValueError(
            "result_row: success flag inconsistent with validity "
            f"(success={row['success']}, validity='{row['validity']}')"
        )
    if row["validity"] == "infra_failure":
        evidence = row.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(
                "result_row: infra_failure requires non-empty 'evidence' "
                "(crash log, missing artifact, corrupted render, ...)"
            )
    return row
