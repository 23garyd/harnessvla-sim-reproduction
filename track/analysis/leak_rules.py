"""Shared leak rules for the memory-ablation conditions (v2-hiddenmem, v4).

Single source of truth for what counts as evidence that hidden memory was
READ during an ablation run. Consumed by BOTH the queue-time tripwire in
track/launchers/run_ablation_memory.sh and the audit in
track/tests/test_ablation_leakage.py, so the two can never diverge.

Rule for what becomes a pattern: only strings the planner could not produce
without having read hidden content. The released system prompt
(RPent/robots/libero/prompts/system.py:393-414) instructs the planner to
`list_dir resources/libero/memory/`, so the BARE paths — and the note names
that appear in the released prompts/guides — are prompt echoes, not leaks,
and are deliberately excluded. See day12_ablation_design.md section 5.

Patterns come from the checked-in inventory rather than the live directory,
because during an ablation the live directory is stashed.
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESOURCES_DIR = REPO / "RPent" / "resources"
INVENTORY_PATH = REPO / "track" / "registry" / "memory_inventory.txt"

# Names the RELEASED prompts/guides mention. The planner can echo these
# without having read anything, so they are recorded in the inventory for
# completeness but never become patterns.
PROMPT_NAMED = frozenset({
    "MEMORY",
    "README",
    "feedback_bowl_eef_y_offset",
    "feedback_failure_forensics",
    "feedback_pi0_pick_full_prompt",
    "feedback_scripted_pick_limits",
    "feedback_swap_perturbs_fixtures",
})

# Planner-visible artifacts inside a run dir. Day-8's tripwire checked only
# launcher.log, rpent/run.log and *.stream.jsonl; transcript_*.json and
# claude_*.txt also carry tool output, so they are included.
TRANSCRIPT_GLOBS = (
    "launcher.log",
    "rpent/run.log",
    "rpent/*.stream.jsonl",
    "rpent/*.txt",
    "rpent/transcript_*.json",
)

_KINDS = ("memory", "tsm")


def record_inventory(resources_dir=RESOURCES_DIR, out_path=INVENTORY_PATH):
    """Scan the live release and record memory + TSM basenames.

    Returns the number of names recorded. With out_path=None nothing is
    written and the inventory dict is returned instead (used by the drift
    test).
    """
    resources_dir = Path(resources_dir)
    memory = sorted(p.stem for p in
                    (resources_dir / "libero" / "memory").glob("*.md"))
    tsm = sorted({p.stem for d in
                  sorted((resources_dir / "libero").glob("results_*_pert"))
                  for p in d.iterdir() if p.is_file()})
    if out_path is None:
        return {"memory": memory, "tsm": tsm}

    lines = [
        "# Memory-content inventory for the ablation leak rules.",
        "# Regenerate with: PYTHONPATH= .venv/bin/python -m "
        "track.analysis.leak_rules --record",
        "# Format: <kind> <basename>",
        "#   memory = Global Memory leaf (resources/libero/memory/*.md)",
        "#   tsm    = Task-Specific Memory reference "
        "(resources/libero/results_*_pert/*)",
        "# Names in leak_rules.PROMPT_NAMED are recorded here but excluded",
        "# from patterns: the released prompts/guides name them, so their",
        "# appearance in a transcript is a prompt echo, not a leak.",
    ]
    lines += [f"memory {n}" for n in memory]
    lines += [f"tsm {n}" for n in tsm]
    Path(out_path).write_text("\n".join(lines) + "\n")
    return len(memory) + len(tsm)


def load_inventory(path=INVENTORY_PATH):
    inv = {kind: [] for kind in _KINDS}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"inventory: malformed line {line!r}")
        kind, name = parts
        if kind not in inv:
            raise ValueError(f"inventory: unknown kind {kind!r} in {line!r}")
        inv[kind].append(name)
    return inv
