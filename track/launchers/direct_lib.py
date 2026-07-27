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


def select_cell(manifest, suite, task_id, seed, condition=CONDITION):
    """Freeze enforcement: refuse any (condition, suite, task, seed) not
    scored in the frozen manifest. Bootstrap-only seeds are never scored."""
    for cell in manifest["cells"]:
        if (cell["condition"] == condition and cell["suite"] == suite
                and cell.get("task_id") == task_id):
            for entry in cell["seeds"]:
                if entry["seed"] == seed:
                    if entry["bootstrap_only"]:
                        raise ValueError(
                            f"seed {seed} is bootstrap_only in the frozen "
                            f"manifest and is never scored")
                    return cell
            raise ValueError(
                f"seed {seed} not in the frozen manifest for {suite} t{task_id}")
    raise ValueError(
        f"cell ({condition}, {suite}, t{task_id}) not in the frozen manifest")


def save_png(arr, path):
    """Save an HxWx3 uint8 array as PNG (lazy imports: GPU-venv only)."""
    import numpy as np
    from PIL import Image
    Image.fromarray(np.asarray(arr).astype("uint8")).save(path)
