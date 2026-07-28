"""Derive ledger.csv from artifacts/runs/. The ledger is never hand-edited;
any reported number must reproduce from a clean rebuild (spec section 3).

Run-directory contract: <runs_root>/<exp_version>/<condition>/<task>/<seed>/<ts>/
containing run_meta.json (launch, immutable) and result_row.json (termination).
Seed-0 rows are bootstrap-only and are never scored.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from track.analysis.schemas import validate_result_row, validate_run_meta

LEDGER_COLUMNS = [
    "exp_version", "condition", "suite", "task", "seed", "run_id",
    "success", "validity", "terminal_reason",
    "steps", "turns", "vla_act_calls", "analytic_calls", "wall_seconds",
    "planner_model", "rpent_commit", "checkpoint_sha256", "run_dir",
]


def iter_run_dirs(runs_root):
    """Yield every directory that contains a run_meta.json."""
    for meta_path in sorted(Path(runs_root).glob("*/*/*/*/*/run_meta.json")):
        yield meta_path.parent


def load_row(run_dir):
    meta = validate_run_meta(
        json.loads((run_dir / "run_meta.json").read_text()))
    result = validate_result_row(
        json.loads((run_dir / "result_row.json").read_text()))
    path_ids = tuple(run_dir.parts[-5:-1])
    meta_ids = (meta["exp_version"], meta["condition"], meta["task"], str(meta["seed"]))
    if path_ids != meta_ids:
        raise ValueError(
            f"path (exp_version, condition, task, seed)={path_ids} "
            f"disagrees with run_meta {meta_ids}"
        )
    return {
        "exp_version": meta["exp_version"],
        "condition": meta["condition"],
        "suite": meta["suite"],
        "task": meta["task"],
        "seed": meta["seed"],
        "run_id": run_dir.name,
        "success": result["success"],
        "validity": result["validity"],
        "terminal_reason": result["terminal_reason"],
        "steps": result["counts"]["steps"],
        "turns": result["counts"]["turns"],
        "vla_act_calls": result["counts"]["vla_act_calls"],
        "analytic_calls": result["counts"]["analytic_calls"],
        "wall_seconds": result["wall_seconds"],
        "planner_model": meta["planner_model"],
        "rpent_commit": meta["rpent_commit"],
        "checkpoint_sha256": meta["checkpoint_sha256"],
        "run_dir": str(run_dir),
    }


def build_ledger(runs_root):
    """Return (rows, skipped_seed0, incomplete). Raises on any invalid record."""
    rows, skipped_seed0, incomplete = [], 0, 0
    for run_dir in iter_run_dirs(runs_root):
        if not (run_dir / "result_row.json").exists():
            incomplete += 1
            continue
        try:
            row = load_row(run_dir)
        except ValueError as e:
            raise ValueError(f"{run_dir}: {e}") from e
        if row["seed"] == 0:
            skipped_seed0 += 1
            continue
        rows.append(row)
    rows.sort(key=lambda r: (r["exp_version"], r["condition"], r["suite"],
                             r["task"], r["seed"], r["run_id"]))
    return rows, skipped_seed0, incomplete


def write_csv(rows, out_path):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        writer.writeheader()
        for row in rows:
            # success as 1/0: bool("False") is True, a trap for CSV consumers
            writer.writerow({**row, "success": int(row["success"])})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="artifacts/runs")
    parser.add_argument("--out", default="artifacts/ledger.csv")
    args = parser.parse_args(argv)
    rows, skipped_seed0, incomplete = build_ledger(args.runs_root)
    write_csv(rows, args.out)
    infra = sum(1 for r in rows if r["validity"] == "infra_failure")
    print(f"ledger: {len(rows)} rows ({len(rows) - infra} scored, "
          f"{infra} infra_failure) -> {args.out} "
          f"(excluded: {skipped_seed0} seed-0 bootstrap, "
          f"{incomplete} incomplete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
