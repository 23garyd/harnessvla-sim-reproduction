"""Queue-manifest loading and validation (spec sections 3-4).

A queue is a frozen manifest plus a pinned experiment version - nothing
else. Manifests mark seed 0 bootstrap_only; scored seeds are never 0.
"""
import json
from pathlib import Path

_BUDGETS_REQUIRED = {"max_steps": int, "max_turns": int, "max_wall_seconds": int}
_CAPS_REQUIRED = {"max_rollouts": int, "max_tokens_per_rollout": int}


def _require(record, spec, where):
    if not isinstance(record, dict):
        raise ValueError(f"{where}: expected dict, got {type(record).__name__}")
    for key, typ in spec.items():
        if key not in record:
            raise ValueError(f"{where}: missing required key '{key}'")
        if not isinstance(record[key], typ) or isinstance(record[key], bool):
            raise ValueError(f"{where}: key '{key}' must be {typ.__name__}")


def validate_manifest(manifest):
    for key in ("exp_version", "budgets", "caps", "cells"):
        if key not in manifest:
            raise ValueError(f"manifest: missing required key '{key}'")
    if not isinstance(manifest["exp_version"], str):
        raise ValueError("manifest: 'exp_version' must be str")
    _require(manifest["budgets"], _BUDGETS_REQUIRED, "manifest.budgets")
    _require(manifest["caps"], _CAPS_REQUIRED, "manifest.caps")
    if not isinstance(manifest["cells"], list) or not manifest["cells"]:
        raise ValueError("manifest: 'cells' must be a non-empty list")
    seen_cells = set()
    for i, cell in enumerate(manifest["cells"]):
        where = f"manifest.cells[{i}]"
        for key in ("condition", "suite", "task"):
            if key not in cell:
                raise ValueError(f"{where}: missing required key '{key}'")
            if not isinstance(cell[key], str):
                raise ValueError(f"{where}: key '{key}' must be str")
        if not isinstance(cell.get("task_id"), int) or isinstance(cell.get("task_id"), bool):
            raise ValueError(f"{where}: 'task_id' must be int")
        if not isinstance(cell.get("seeds"), list) or not cell["seeds"]:
            raise ValueError(f"{where}: 'seeds' must be a non-empty list")
        cell_id = (cell["condition"], cell["suite"], cell["task"])
        if cell_id in seen_cells:
            raise ValueError(f"{where}: duplicate cell {cell_id}")
        seen_cells.add(cell_id)
        seen_seeds = set()
        for entry in cell["seeds"]:
            if "seed" not in entry or "bootstrap_only" not in entry:
                raise ValueError(
                    f"{where}: each seed entry needs 'seed' and 'bootstrap_only'")
            if not isinstance(entry["seed"], int) or isinstance(entry["seed"], bool):
                raise ValueError(f"{where}: 'seed' must be int")
            if not isinstance(entry["bootstrap_only"], bool):
                raise ValueError(f"{where}: 'bootstrap_only' must be bool")
            if entry["seed"] in seen_seeds:
                raise ValueError(f"{where}: duplicate seed {entry['seed']}")
            seen_seeds.add(entry["seed"])
            if entry["seed"] == 0 and not entry["bootstrap_only"]:
                raise ValueError(
                    f"{where}: seed 0 bootstraps memory only and must be "
                    "bootstrap_only (it is never scored)")
    return manifest


def scored_cells(manifest):
    """Expand to (condition, suite, task, seed) tuples, bootstrap seeds excluded."""
    validate_manifest(manifest)
    out = []
    for cell in manifest["cells"]:
        for entry in cell["seeds"]:
            if not entry["bootstrap_only"]:
                out.append((cell["condition"], cell["suite"],
                            cell["task"], entry["seed"]))
    return out


def load_manifest(path):
    return validate_manifest(json.loads(Path(path).read_text()))


def main(argv=None):
    """Print `suite task_id seed` lines for a manifest's scored cells.

    The ablation launcher consumes this instead of parsing JSON in bash, so
    cell expansion goes through validate_manifest() exactly once.
    """
    import argparse

    p = argparse.ArgumentParser(description=main.__doc__)
    p.add_argument("--plan", required=True, metavar="MANIFEST")
    p.add_argument("--condition", default=None,
                   help="only print cells with this condition")
    args = p.parse_args(argv)

    manifest = load_manifest(args.plan)
    task_ids = {(c["condition"], c["suite"], c["task"]): c["task_id"]
                for c in manifest["cells"]}
    for condition, suite, task, seed in scored_cells(manifest):
        if args.condition and condition != args.condition:
            continue
        print(f"{suite} {task_ids[(condition, suite, task)]} {seed}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
