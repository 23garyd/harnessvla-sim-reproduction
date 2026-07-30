# Day-12 Memory Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and test the machinery for the registry-v4 zero-shot memory ablation — a manifest, a generalized condition launcher, and a leak-rule module shared by the queue-time tripwire and a pytest audit — so the only intended difference between v4 and v2/v3 is access to bootstrapped harness memory.

**Architecture:** `leak_rules.py` is the single source of truth for what counts as evidence that hidden memory was *read*; both `run_ablation_memory.sh` (queue-time, aborts live) and `test_ablation_leakage.py` (audit-time) consume it, so the rules cannot diverge. Patterns derive from a checked-in inventory (`memory_inventory.txt`) rather than the live directory, so the audit works while memory is stashed and after it is restored. `run_ablation_memory.sh` generalizes the Day-8 script: cells come from a manifest instead of being hardcoded, functions are sourceable for testing, and a per-seed clean-slate step prevents run *k* inheriting run *k−1*'s notes.

**Tech Stack:** Python 3.10 stdlib + existing `track.analysis.*`; bash; pytest.

**Spec:** `track/registry/day12_ablation_design.md` (approved, gate commit `e6c253d`). Read §1, §4 and §5 before starting.

**Session conventions:**
- pytest is ALWAYS `PYTHONPATH= .venv/bin/python -m pytest ...` — the bare `PYTHONPATH=` prefix is required or ROS Humble's `launch_testing` plugin aborts collection.
- Baseline is **118 tests green**; `bash track/setup/pin_check.sh` must stay clean.
- `RPent/` is read-only and pinned `6e4ba18`. Never edit it. `RPent/resources/` is gitignored, which is why stashing does not dirty the worktree.
- Canonical remote is `garyd` → `github.com/23garyd/harnessvla-robot-stack`. Push there, not to `origin` (which is not configured).
- Do NOT run any rollout as part of this plan. This plan builds and tests machinery only; the pilot and queue are Day-12 steps 3–4, after review.

**Verified facts this plan depends on (measured 2026-07-29, do not re-derive):**
- `RPent/resources/libero/memory/` holds **50** `*.md` files, of which **7** are named in the released prompts/guides (`MEMORY`, `README`, `feedback_bowl_eef_y_offset`, `feedback_failure_forensics`, `feedback_pi0_pick_full_prompt`, `feedback_scripted_pick_limits`, `feedback_swap_perturbs_fixtures`) → **43** content-bearing leaf names.
- `RPent/resources/libero/results_{spatial,goal,object,10}_pert/` hold **39 + 40 + 40 + 37 = 156** files. **None** of their basenames appear in the released prompts/guides, so all 156 are content-bearing.
- Total patterns = 43 + 156 = **199**, plus the runtime stash path.
- The released system prompt (`RPent/robots/libero/prompts/system.py:393-414`) tells the planner to `list_dir resources/libero/memory/`. The BARE paths are therefore prompt echoes and must NOT be patterns.
- Real-data controls: `artifacts/ablation/attempt1_condition_violated/` has **7** files containing `tall_item_first_basket_placement`; `attempt2_seed4_condition_violated/` has **2**; the clean `artifacts/ablation/runs/v2-hiddenmem/` runs have **0**.
- Planner-visible artifacts per run: `launcher.log`, `rpent/run.log`, `rpent/*.stream.jsonl`, `rpent/*.txt`, `rpent/transcript_*.json`. Day-8's tripwire scanned only the first three.

---

## File Structure

| file | responsibility |
|---|---|
| `track/analysis/leak_rules.py` (create) | Sole definition of leak patterns; inventory record/load; run-dir scanning; CLI used by the shell |
| `track/registry/memory_inventory.txt` (create) | Checked-in inventory of memory + TSM basenames, so scanning works while memory is stashed |
| `track/analysis/manifests.py` (modify) | Add a `--plan` CLI so the shell gets cell expansion from validated Python, not `jq` |
| `track/manifests/ablation_zeroshot_v4.json` (create) | The 4 v4 cells × seeds 1–5, harness only, no seed 0 |
| `track/launchers/run_ablation_memory.sh` (create) | Generalized condition wrapper: stash → run manifest cells → per-seed hygiene + tripwire → restore |
| `track/launchers/run_ablation_hiddenmem.sh` (rewrite) | Thin wrapper pinning the v2-hiddenmem manifest, so the Day-8 command still reproduces |
| `track/tests/test_leak_rules.py` (create) | Unit tests for pattern construction and scanning, with synthetic controls |
| `track/tests/test_ablation_leakage.py` (create) | The plan-mandated audit: scans real ablation runs, with real-data positive/negative controls and a no-silent-skip guard |
| `track/tests/test_ablation_memory_launcher.py` (create) | Sources the shell script and tests its functions against a fake resources tree |
| `track/tests/test_manifests.py` (modify) | Assert the v4 manifest loads and scores 20 cells with no seed 0 |

---

### Task 1: `manifests.py` — a `--plan` CLI for the shell

The launcher must not parse JSON with `jq`/`sed`; it should get cells from the same validated Python the tests use.

**Files:**
- Modify: `track/analysis/manifests.py` (append at end of file)
- Test: `track/tests/test_manifests.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `track/tests/test_manifests.py`:

```python
def test_plan_cli_prints_suite_taskid_seed(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest()))
    rc = manifests.main(["--plan", str(p), "--condition", "direct"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == "libero_goal_task 2 1\nlibero_goal_task 2 2\n"


def test_plan_cli_condition_filter_excludes_other_conditions(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest()))
    rc = manifests.main(["--plan", str(p), "--condition", "harness"])
    assert rc == 0
    assert capsys.readouterr().out == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_manifests.py -q -k plan_cli`
Expected: FAIL — `AttributeError: module 'track.analysis.manifests' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Append to `track/analysis/manifests.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_manifests.py -q`
Expected: PASS, all manifest tests green

- [ ] **Step 5: Commit**

```bash
git add track/analysis/manifests.py track/tests/test_manifests.py
git commit -m "feat: manifests --plan CLI so the ablation launcher gets validated cell expansion"
```

---

### Task 2: the v4 manifest

**Files:**
- Create: `track/manifests/ablation_zeroshot_v4.json`
- Test: `track/tests/test_manifests.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `track/tests/test_manifests.py`:

```python
def test_ablation_zeroshot_v4_manifest_is_the_predeclared_design():
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1]
         / "manifests" / "ablation_zeroshot_v4.json")
    m = manifests.load_manifest(p)
    assert m["exp_version"] == "v4"
    # identical to v2/v3 so the ONLY difference is memory access
    assert m["budgets"] == {"max_steps": 1200, "max_turns": 60,
                            "max_wall_seconds": 2400}
    cells = manifests.scored_cells(m)
    assert len(cells) == 20                      # 4 cells x seeds 1-5
    assert all(c[0] == "harness" for c in cells)
    assert {c[1] for c in cells} == {
        "libero_spatial_task", "libero_object_task",
        "libero_spatial_swap", "libero_goal_swap"}
    # zero-shot: NO seed-0 bootstrap anywhere, since bootstrapping would
    # manufacture the memory being ablated
    for cell in m["cells"]:
        assert all(e["seed"] != 0 for e in cell["seeds"])
    assert sorted({c[3] for c in cells}) == [1, 2, 3, 4, 5]
    # the excluded floor cells must not sneak in
    assert not {c[1] for c in cells} & {
        "libero_goal_task", "libero_10_task", "libero_10_swap",
        "libero_object_swap"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_manifests.py -q -k zeroshot_v4`
Expected: FAIL — `FileNotFoundError: .../ablation_zeroshot_v4.json`

- [ ] **Step 3: Write the manifest**

Create `track/manifests/ablation_zeroshot_v4.json`:

```json
{
  "exp_version": "v4",
  "frozen": "2026-07-29 (Day 12, predeclared BEFORE any rollout — see track/registry/day12_ablation_design.md, gate commit e6c253d). Paper Table 5 zero-shot condition: Global Memory (resources/libero/memory) AND all four Task-Specific Memory dirs (resources/libero/results_*_pert) AND the HF download cache are hidden by run_ablation_memory.sh; prompt, guides, primitives, frozen pi0.5 checkpoint, planner model and budgets are identical to v2/v3, so the only intended difference is memory access. Seeds 1-5 with NO seed-0 bootstrap: its absence IS the zero-shot condition. PREDECLARED HYPOTHESIS H1: delta_S > delta_T where delta = (with-memory success rate) - (no-memory success rate) pooled per side over 10 seed-paired rollouts; H0: delta_S <= delta_T. Cells chosen for headroom, not family symmetry — the T side starts at 10/10 and the S side at 8/10, so the design is biased AGAINST H1. Day-8's object_swap ablation (5/5 without memory vs 2/5 with) is a known counterexample and is reported alongside but NOT pooled. Runs land in artifacts/ablation/runs/v4 and NEVER enter the core paired ledger.",
  "budgets": {"max_steps": 1200, "max_turns": 60, "max_wall_seconds": 2400},
  "caps": {"max_rollouts": 26, "max_tokens_per_rollout": 0},
  "cells": [
    {"condition": "harness", "suite": "libero_spatial_task",
     "task": "libero_spatial_task_t2", "task_id": 2,
     "anchor": "redirection side; with-memory baseline 5/5 (v2)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "harness", "suite": "libero_object_task",
     "task": "libero_object_task_t2", "task_id": 2,
     "anchor": "redirection side; with-memory baseline 5/5 (v3)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "harness", "suite": "libero_spatial_swap",
     "task": "libero_spatial_swap_t2", "task_id": 2,
     "anchor": "swap side; with-memory baseline 5/5 (v3)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]},
    {"condition": "harness", "suite": "libero_goal_swap",
     "task": "libero_goal_swap_t2", "task_id": 2,
     "anchor": "swap side; with-memory baseline 3/5 (v2)",
     "seeds": [{"seed": 1, "bootstrap_only": false},
               {"seed": 2, "bootstrap_only": false},
               {"seed": 3, "bootstrap_only": false},
               {"seed": 4, "bootstrap_only": false},
               {"seed": 5, "bootstrap_only": false}]}
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_manifests.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add track/manifests/ablation_zeroshot_v4.json track/tests/test_manifests.py
git commit -m "feat: registry-v4 zero-shot ablation manifest (4 headroom cells, seeds 1-5, no bootstrap)"
```

---

### Task 3: `leak_rules.py` — inventory record and load

The inventory is checked in so the audit still works when the memory directory is stashed (or restored, after the fact).

**Files:**
- Create: `track/analysis/leak_rules.py`
- Create: `track/registry/memory_inventory.txt` (generated, then committed)
- Test: `track/tests/test_leak_rules.py`

- [ ] **Step 1: Write the failing test**

Create `track/tests/test_leak_rules.py`:

```python
from pathlib import Path

import pytest

from track.analysis import leak_rules

REPO = Path(__file__).resolve().parents[2]


def test_prompt_named_set_is_exactly_the_seven_released_names():
    assert leak_rules.PROMPT_NAMED == frozenset({
        "MEMORY", "README",
        "feedback_bowl_eef_y_offset", "feedback_failure_forensics",
        "feedback_pi0_pick_full_prompt", "feedback_scripted_pick_limits",
        "feedback_swap_perturbs_fixtures"})


def test_record_inventory_writes_both_kinds(tmp_path):
    res = tmp_path / "resources"
    (res / "libero" / "memory").mkdir(parents=True)
    (res / "libero" / "memory" / "MEMORY.md").write_text("index")
    (res / "libero" / "memory" / "tall_item_first_basket_placement.md").write_text("x")
    (res / "libero" / "results_object_pert").mkdir(parents=True)
    (res / "libero" / "results_object_pert" / "object_swap_t2_s0.json").write_text("{}")
    (res / "libero" / "results_object_pert" / "recipe_object_swap_t2_s0.jsonl").write_text("{}")

    out = tmp_path / "inventory.txt"
    n = leak_rules.record_inventory(resources_dir=res, out_path=out)

    assert n == 4
    inv = leak_rules.load_inventory(out)
    assert sorted(inv["memory"]) == ["MEMORY", "tall_item_first_basket_placement"]
    assert sorted(inv["tsm"]) == ["object_swap_t2_s0", "recipe_object_swap_t2_s0"]


def test_load_inventory_ignores_comments_and_blank_lines(tmp_path):
    p = tmp_path / "inv.txt"
    p.write_text("# a comment\n\nmemory foo\ntsm bar\n\n")
    inv = leak_rules.load_inventory(p)
    assert inv == {"memory": ["foo"], "tsm": ["bar"]}


def test_load_inventory_rejects_unknown_kind(tmp_path):
    p = tmp_path / "inv.txt"
    p.write_text("bogus foo\n")
    with pytest.raises(ValueError, match="unknown kind"):
        leak_rules.load_inventory(p)


def test_checked_in_inventory_has_the_measured_counts():
    inv = leak_rules.load_inventory()
    assert len(inv["memory"]) == 50
    assert len(inv["tsm"]) == 156


@pytest.mark.skipif(not (REPO / "RPent/resources/libero/memory").is_dir(),
                    reason="memory dir stashed or absent")
def test_checked_in_inventory_matches_the_live_release():
    """Drift guard: a new released note must be added to the inventory or the
    leak rules would silently stop covering it."""
    live = leak_rules.record_inventory(out_path=None)
    assert live == leak_rules.load_inventory()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q`
Expected: FAIL — `ImportError: cannot import name 'leak_rules'`

- [ ] **Step 3: Write minimal implementation**

Create `track/analysis/leak_rules.py`:

```python
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
```

- [ ] **Step 4: Generate the inventory, then run the tests**

```bash
PYTHONPATH= .venv/bin/python -m track.analysis.leak_rules --record
```

This fails until Task 5 adds the CLI. Until then, generate it directly:

```bash
PYTHONPATH= .venv/bin/python -c "
from track.analysis import leak_rules
print(leak_rules.record_inventory(), 'names recorded')"
```

Expected: `206 names recorded` (50 memory + 156 tsm)

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add track/analysis/leak_rules.py track/registry/memory_inventory.txt track/tests/test_leak_rules.py
git commit -m "feat: leak_rules inventory of memory + TSM basenames, with a live-release drift guard"
```

---

### Task 4: `leak_rules.py` — pattern construction and scanning

**Files:**
- Modify: `track/analysis/leak_rules.py` (append)
- Test: `track/tests/test_leak_rules.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `track/tests/test_leak_rules.py`:

```python
def test_content_patterns_exclude_prompt_named_leaves():
    pats = set(leak_rules.content_patterns())
    # content-bearing: the planner cannot name this without reading
    assert "tall_item_first_basket_placement" in pats
    # prompt echo: the released guides name it
    for name in leak_rules.PROMPT_NAMED:
        assert name not in pats


def test_content_patterns_exclude_bare_paths():
    """The system prompt tells the planner to list_dir these, so their
    appearance is the condition WORKING, not a leak."""
    pats = set(leak_rules.content_patterns())
    assert "resources/libero/memory" not in pats
    assert "resources/libero/results_object_pert" not in pats


def test_content_patterns_count_is_43_memory_plus_156_tsm():
    assert len(leak_rules.content_patterns()) == 199


def test_content_patterns_include_the_stash_dir_when_given():
    pats = leak_rules.content_patterns(stash_dir="/tmp/tsm_ablation.XYZ")
    assert "/tmp/tsm_ablation.XYZ" in pats
    assert len(pats) == 200


def test_scan_text_positive_control_detects_a_leaf_name():
    hits = leak_rules.scan_text(
        "I read tall_item_first_basket_placement.md for the offsets",
        leak_rules.content_patterns())
    assert hits == ["tall_item_first_basket_placement"]


def test_scan_text_negative_control_ignores_prompt_echoes():
    """A transcript that only echoes what the prompt told it must be clean."""
    text = ("list_dir resources/libero/memory/ -> (empty)\n"
            "no matching task memory found; MEMORY.md absent\n"
            "consulted feedback_swap_perturbs_fixtures per the guide\n")
    assert leak_rules.scan_text(text, leak_rules.content_patterns()) == []


def test_scan_text_detects_tsm_reference_names():
    hits = leak_rules.scan_text("opened recipe_object_swap_t2_s0.jsonl",
                                leak_rules.content_patterns())
    assert hits == ["recipe_object_swap_t2_s0"]


def test_scan_run_dir_reports_file_and_pattern(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("clean\n")
    (run / "rpent" / "run.log").write_text(
        "cat tall_item_first_basket_placement.md\n")
    (run / "rpent" / "transcript_x.json").write_text(
        '{"note": "recipe_object_swap_t2_s0"}')
    hits = leak_rules.scan_run_dir(run)
    assert ("rpent/run.log", "tall_item_first_basket_placement") in hits
    assert ("rpent/transcript_x.json", "recipe_object_swap_t2_s0") in hits
    assert not any(f == "launcher.log" for f, _ in hits)


def test_scan_run_dir_clean_dir_returns_no_hits(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("no matching task memory found\n")
    assert leak_rules.scan_run_dir(run) == []


def test_scan_run_dir_survives_undecodable_bytes(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_bytes(
        b"\xff\xfe binary junk tall_item_first_basket_placement\n")
    hits = leak_rules.scan_run_dir(run)
    assert hits == [("rpent/run.log", "tall_item_first_basket_placement")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q -k "content_patterns or scan_"`
Expected: FAIL — `AttributeError: module ... has no attribute 'content_patterns'`

- [ ] **Step 3: Write minimal implementation**

Append to `track/analysis/leak_rules.py`:

```python
def content_patterns(inventory=None, stash_dir=None):
    """Literal strings whose presence proves hidden content was read.

    Excludes PROMPT_NAMED leaves and never includes bare directory paths:
    the released prompt instructs the planner to list those, so echoing them
    is expected behaviour under the ablation, not a leak.
    """
    inv = inventory if inventory is not None else load_inventory()
    pats = {n for n in inv["memory"] if n not in PROMPT_NAMED}
    pats |= set(inv["tsm"])
    if stash_dir:
        pats.add(str(stash_dir))
    return sorted(pats)


def _compile(patterns):
    # longest-first so a pattern that is a prefix of another cannot mask it
    ordered = sorted(patterns, key=len, reverse=True)
    return re.compile("|".join(re.escape(p) for p in ordered))


def scan_text(text, patterns):
    """Sorted distinct patterns found in text."""
    if not patterns:
        return []
    return sorted({m.group(0) for m in _compile(patterns).finditer(text)})


def scan_run_dir(run_dir, stash_dir=None, inventory=None):
    """Scan one run dir's planner-visible artifacts.

    Returns a sorted list of (path relative to run_dir, pattern) pairs.
    """
    run_dir = Path(run_dir)
    patterns = content_patterns(inventory, stash_dir)
    rx = _compile(patterns)
    hits = set()
    for glob in TRANSCRIPT_GLOBS:
        for path in sorted(run_dir.glob(glob)):
            if not path.is_file():
                continue
            text = path.read_text(errors="ignore")
            for match in rx.finditer(text):
                hits.add((str(path.relative_to(run_dir)), match.group(0)))
    return sorted(hits)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add track/analysis/leak_rules.py track/tests/test_leak_rules.py
git commit -m "feat: leak_rules pattern construction + run-dir scanning, with prompt-echo negative controls"
```

---

### Task 5: `leak_rules.py` — CLI consumed by the launcher

**Files:**
- Modify: `track/analysis/leak_rules.py` (append)
- Test: `track/tests/test_leak_rules.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `track/tests/test_leak_rules.py`:

```python
def test_cli_scan_exits_1_and_names_the_hit(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_text("tall_item_first_basket_placement")
    rc = leak_rules.main(["--scan", str(run)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "LEAK" in err
    assert "tall_item_first_basket_placement" in err


def test_cli_scan_exits_0_on_clean_run(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("no matching task memory found")
    rc = leak_rules.main(["--scan", str(run)])
    assert rc == 0
    assert "clean" in capsys.readouterr().out


def test_cli_scan_detects_the_stash_path(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_text("find /tmp/tsm_ablation.AbCd -type f")
    rc = leak_rules.main(["--scan", str(run), "--stash", "/tmp/tsm_ablation.AbCd"])
    assert rc == 1
    assert "/tmp/tsm_ablation.AbCd" in capsys.readouterr().err


def test_cli_record_writes_the_inventory(tmp_path, capsys):
    out = tmp_path / "inv.txt"
    rc = leak_rules.main(["--record", "--out", str(out)])
    assert rc == 0
    assert len(leak_rules.load_inventory(out)["memory"]) == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q -k cli`
Expected: FAIL — `AttributeError: module ... has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

Append to `track/analysis/leak_rules.py`:

```python
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scan", metavar="RUN_DIR",
                      help="audit one run dir; exit 1 on any leak")
    mode.add_argument("--record", action="store_true",
                      help="regenerate the checked-in inventory")
    p.add_argument("--stash", default=None,
                   help="stash dir path to also treat as a leak pattern")
    p.add_argument("--out", default=INVENTORY_PATH,
                   help="inventory path for --record")
    args = p.parse_args(argv)

    if args.record:
        n = record_inventory(out_path=args.out)
        print(f"recorded {n} names -> {args.out}")
        return 0

    hits = scan_run_dir(args.scan, stash_dir=args.stash)
    if hits:
        print(f"LEAK: hidden-memory content referenced in {args.scan}",
              file=sys.stderr)
        for path, pattern in hits:
            print(f"  {path}: {pattern}", file=sys.stderr)
        return 1
    print(f"leak audit clean: {args.scan}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_leak_rules.py -q`
Expected: PASS (20 tests)

Also verify the CLI by hand:

```bash
PYTHONPATH= .venv/bin/python -m track.analysis.leak_rules --record
```
Expected: `recorded 206 names -> .../memory_inventory.txt` and `git diff --exit-code track/registry/memory_inventory.txt` shows no change.

- [ ] **Step 5: Commit**

```bash
git add track/analysis/leak_rules.py track/tests/test_leak_rules.py
git commit -m "feat: leak_rules --scan/--record CLI (exit 1 on leak) for the tripwire"
```

---

### Task 6: `test_ablation_leakage.py` — the plan-mandated audit

The plan's Day-12 deliverable: *"add a pytest leakage check that greps planner transcripts for memory paths."* This is the highest-value test in the plan because it runs against **real** artifacts, including two historical violations.

**Files:**
- Create: `track/tests/test_ablation_leakage.py`

- [ ] **Step 1: Write the failing test**

Create `track/tests/test_ablation_leakage.py`:

```python
"""Leakage audit over the real ablation artifacts.

The hidden-memory condition is only valid if no planner-visible transcript
references hidden memory CONTENT. This audits every ablation run on disk
using the same rules as the queue-time tripwire (track.analysis.leak_rules),
and pins both directions with real data: the two quarantined attempts MUST
trip, and the accepted runs MUST NOT.
"""
import csv
from pathlib import Path

import pytest

from track.analysis import leak_rules

REPO = Path(__file__).resolve().parents[2]
ABLATION = REPO / "artifacts" / "ablation"
ACCEPTED_RUNS = ABLATION / "runs"
QUARANTINED = (
    ABLATION / "attempt1_condition_violated",
    ABLATION / "attempt2_seed4_condition_violated",
)


def run_dirs(root):
    """A run dir is any directory containing launcher.log."""
    if not root.is_dir():
        return []
    return sorted(p.parent for p in root.rglob("launcher.log"))


def ledger_versions():
    path = ABLATION / "ledger.csv"
    if not path.is_file():
        return set()
    with open(path) as fh:
        return {row["exp_version"] for row in csv.DictReader(fh)}


def test_accepted_ablation_runs_are_leak_free():
    """The condition held for every run that counts toward results."""
    offenders = {}
    for run in run_dirs(ACCEPTED_RUNS):
        hits = leak_rules.scan_run_dir(run)
        if hits:
            offenders[str(run.relative_to(REPO))] = hits
    assert not offenders, f"hidden-memory condition violated: {offenders}"


def test_audit_actually_scanned_something():
    """No-silent-skip guard: a passing audit that scanned zero files would be
    meaningless. If the ablation ledger has rows, run dirs must exist."""
    if not ledger_versions():
        pytest.skip("no ablation ledger yet")
    assert run_dirs(ACCEPTED_RUNS), (
        "ablation ledger has rows but no run dirs were found to scan")


def test_v4_rows_have_run_dirs_to_audit():
    """Once v4 rows land, they must be present on disk and leak-free."""
    if "v4" not in ledger_versions():
        pytest.skip("v4 not queued yet")
    v4_runs = run_dirs(ACCEPTED_RUNS / "v4")
    assert v4_runs, "v4 rows in the ledger but no v4 run dirs on disk"
    for run in v4_runs:
        assert leak_rules.scan_run_dir(run) == [], f"v4 leak in {run}"


@pytest.mark.parametrize("quarantine", QUARANTINED, ids=lambda p: p.name)
def test_quarantined_attempts_still_trip_the_rules(quarantine):
    """Real-data positive control. Attempt 1 is the run where the planner
    found the in-repo stash with a repo-wide `find` and read the notes back;
    attempt 2 leaked note filenames through the HF cache. If a rules change
    ever stops flagging these, the rules have regressed."""
    if not quarantine.is_dir():
        pytest.skip(f"{quarantine.name} not present")
    runs = run_dirs(quarantine)
    assert runs, f"{quarantine.name} has no run dirs"
    assert any(leak_rules.scan_run_dir(r) for r in runs), (
        f"{quarantine.name} is a known condition violation but the leak "
        "rules no longer detect it")


def test_quarantined_runs_are_not_under_the_accepted_tree():
    """Structural guard: quarantined evidence must never be scanned as
    accepted results, or a violation would enter the result set."""
    accepted = {str(p) for p in run_dirs(ACCEPTED_RUNS)}
    for quarantine in QUARANTINED:
        for run in run_dirs(quarantine):
            assert str(run) not in accepted
```

- [ ] **Step 2: Run the tests**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_ablation_leakage.py -q -v`

Expected: all PASS. Specifically `test_quarantined_attempts_still_trip_the_rules[attempt1_condition_violated]` must PASS by *finding* leaks (7 files reference `tall_item_first_basket_placement`), and `test_accepted_ablation_runs_are_leak_free` must PASS by finding none in the 5 accepted v2-hiddenmem runs.

If `test_accepted_ablation_runs_are_leak_free` FAILS, stop and report — that would mean a historical run previously believed clean is not, which is a finding, not a test bug. Do not weaken the rules to make it pass.

- [ ] **Step 3: Commit**

```bash
git add track/tests/test_ablation_leakage.py
git commit -m "test: leakage audit over real ablation artifacts, with both quarantined attempts as positive controls"
```

---

### Task 7: `run_ablation_memory.sh` — the generalized condition launcher

**Files:**
- Create: `track/launchers/run_ablation_memory.sh`
- Test: `track/tests/test_ablation_memory_launcher.py`

Design notes for the implementer:
- Functions are defined unconditionally; `main` runs only when the file is executed, so tests can `source` it and call functions in isolation.
- `stash_members` must be captured **before** stashing and persisted, because after the stash the `results_*_pert` glob matches nothing — recomputing it later would silently shrink the member list and break both restore and hygiene.
- Never delete planner-created files. Move them into the run dir as evidence.

- [ ] **Step 1: Write the failing test**

Create `track/tests/test_ablation_memory_launcher.py`:

```python
"""Unit tests for the ablation launcher's pieces.

The script guards its main flow behind a BASH_SOURCE check, so these tests
source it and exercise individual functions against a fake resources tree.
No rollout is launched.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "track" / "launchers" / "run_ablation_memory.sh"


def fake_resources(tmp_path):
    res = tmp_path / "resources"
    for sub in ("libero/memory", "libero/results_object_pert",
                "libero/results_goal_pert", ".cache"):
        (res / sub).mkdir(parents=True)
    (res / "libero" / "memory" / "MEMORY.md").write_text("index")
    return res


def test_script_is_executable_and_sourceable_without_running(bash, tmp_path):
    """Sourcing must define functions without stashing anything."""
    res = fake_resources(tmp_path)
    r = bash(f'source {SCRIPT}; echo SOURCED-OK; ls {res}/libero',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "SOURCED-OK" in r.stdout
    assert "memory" in r.stdout


def test_stash_members_lists_memory_all_tsm_dirs_and_cache(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'source {SCRIPT}; stash_members',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    members = r.stdout.split()
    assert members[0] == "libero/memory"
    assert "libero/results_object_pert" in members
    assert "libero/results_goal_pert" in members
    assert ".cache" in members


def test_plan_cells_reads_the_v4_manifest(bash, tmp_path):
    res = fake_resources(tmp_path)
    manifest = REPO / "track" / "manifests" / "ablation_zeroshot_v4.json"
    r = bash(f'source {SCRIPT}; plan_cells {manifest}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    lines = [l for l in r.stdout.strip().split("\n") if l]
    assert len(lines) == 20
    assert "libero_spatial_task 2 1" in lines
    assert not any(l.endswith(" 0") for l in lines)   # no seed 0


def test_hygiene_moves_planner_created_files_into_the_run_dir(bash, tmp_path):
    """Per-seed clean slate: run k must not inherit run k-1's notes."""
    res = fake_resources(tmp_path)
    members = tmp_path / "members.txt"
    members.write_text("libero/memory\n")
    (res / "libero" / "memory" / "note_the_planner_wrote.md").write_text("x")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    r = bash(f'source {SCRIPT}; hygiene_after_seed {run_dir} {members}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert not (res / "libero" / "memory").exists(), "path not restored to absent"
    moved = run_dir / "planner_created_memory" / "libero" / "memory"
    assert (moved / "note_the_planner_wrote.md").is_file(), "evidence not preserved"


def test_hygiene_is_a_noop_when_nothing_was_created(bash, tmp_path):
    res = fake_resources(tmp_path)
    members = tmp_path / "members.txt"
    members.write_text("libero/results_spatial_pert\n")   # never existed
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    r = bash(f'source {SCRIPT}; hygiene_after_seed {run_dir} {members}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert not (run_dir / "planner_created_memory").exists()


def test_dry_run_prints_the_plan_and_stashes_nothing(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --dry-run',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "libero_spatial_task 2 1" in r.stdout
    assert "libero/memory" in r.stdout          # reports what WOULD be hidden
    assert (res / "libero" / "memory" / "MEMORY.md").is_file(), "dry run stashed!"


def test_dry_run_limit_truncates_the_plan(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --dry-run --limit 3',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    cells = [l for l in r.stdout.split("\n") if l.startswith("libero_")]
    assert len(cells) == 3


def test_rejects_unknown_argument(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --bogus',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 64
    assert "usage" in r.stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_ablation_memory_launcher.py -q`
Expected: FAIL — script does not exist

- [ ] **Step 3: Write the launcher**

Create `track/launchers/run_ablation_memory.sh`:

```bash
#!/usr/bin/env bash
# Generalized memory-ablation condition wrapper.
#
# Default condition is registry v4 = the paper's Table 5 zero-shot protocol:
# hide Global Memory (resources/libero/memory), ALL FOUR Task-Specific Memory
# dirs (resources/libero/results_*_pert) and the HF download cache, then run
# the manifest's harness cells with otherwise-identical v2/v3 pins. Also
# drives the Day-8 v2-hiddenmem manifest via run_ablation_hiddenmem.sh.
#
# Hardening (see track/registry/day12_ablation_design.md sections 1 and 5):
#   - the stash is ONE opaque tar in a 0700 mktemp dir OUTSIDE the repo,
#     because a plain in-repo stash was located by the planner's repo-wide
#     `find` and read back (Day-8 attempt 1)
#   - HF_HUB_OFFLINE=1 blocks rpent's HF re-sync of the stashed dataset, and
#     the HF cache is stashed too because *.lock/*.metadata leak note
#     FILENAMES (Day-8 attempt 2)
#   - every finished run is leak-scanned by track.analysis.leak_rules, the
#     same module test_ablation_leakage.py uses; any hit quarantines the run
#     and aborts the queue
#   - per-seed clean slate: anything the planner creates under a hidden path
#     is moved into the run dir as evidence and the path restored to absent,
#     so run k cannot inherit run k-1's notes. pin_check cannot catch this
#     because RPent/resources/ is gitignored.
#
# Functions are defined unconditionally; main runs only on execution, so
# tests can source this file.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RES="${TRACK_RES:-$REPO/RPent/resources}"
PY="${TRACK_PY:-$REPO/.venv/bin/python}"
DEFAULT_MANIFEST="$REPO/track/manifests/ablation_zeroshot_v4.json"
OUT_ROOT="${OUT_ROOT:-$REPO/artifacts/ablation/runs}"
QUARANTINE="${QUARANTINE:-$REPO/artifacts/ablation/quarantine}"

usage() {
    echo "usage: run_ablation_memory.sh [--manifest FILE] [--limit N] [--dry-run]" >&2
    exit 64
}

stash_members() {
    # One member path per line, relative to RES. MUST be captured before the
    # stash: afterwards the results_*_pert glob matches nothing.
    local members=(libero/memory) d
    for d in "$RES"/libero/results_*_pert; do
        [ -d "$d" ] && members+=("libero/$(basename "$d")")
    done
    [ -d "$RES/.cache" ] && members+=(.cache)
    printf '%s\n' "${members[@]}"
}

plan_cells() {
    # "suite task_id seed" lines for $1's harness cells, via validated Python.
    PYTHONPATH= "$PY" -m track.analysis.manifests --plan "$1" --condition harness
}

exp_version_of() {
    PYTHONPATH= "$PY" -c "
import json,sys; print(json.load(open(sys.argv[1]))['exp_version'])" "$1"
}

hygiene_after_seed() {
    # $1 = run dir, $2 = members file. Preserve planner-created files as
    # evidence, then restore the hidden paths to absent for the next seed.
    local run_dir="$1" members_file="$2" member dest
    while read -r member; do
        [ -n "$member" ] || continue
        [ -e "$RES/$member" ] || continue
        dest="$run_dir/planner_created_memory/$member"
        mkdir -p "$(dirname "$dest")"
        mv "$RES/$member" "$dest"
        echo "HYGIENE: planner created '$member' -> $dest"
    done < "$members_file"
}

tripwire() {
    # $1 = run dir, $2 = stash dir. Shares its rule set with
    # test_ablation_leakage.py through track.analysis.leak_rules.
    if ! PYTHONPATH= "$PY" -m track.analysis.leak_rules \
            --scan "$1" --stash "$2"; then
        mkdir -p "$QUARANTINE"
        printf 'condition violated — leak_rules flagged hidden-memory content\n' \
            > "$1/INVALID"
        mv "$1" "$QUARANTINE/$(basename "$(dirname "$1")")_$(basename "$1")"
        echo "TRIPWIRE: quarantined and aborting queue" >&2
        return 1
    fi
}

main() {
    local manifest="$DEFAULT_MANIFEST" limit=0 dry_run=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --manifest) [ $# -ge 2 ] || usage; manifest="$2"; shift 2 ;;
            --limit)    [ $# -ge 2 ] || usage; limit="$2"; shift 2 ;;
            --dry-run)  dry_run=1; shift ;;
            *) usage ;;
        esac
    done

    local cells
    cells="$(plan_cells "$manifest")"
    if [ "$limit" -gt 0 ]; then
        cells="$(printf '%s\n' "$cells" | head -n "$limit")"
    fi

    if [ "$dry_run" = 1 ]; then
        echo "manifest: $manifest (exp_version $(exp_version_of "$manifest"))"
        echo "would hide:"
        stash_members | sed 's/^/  /'
        echo "would run:"
        printf '%s\n' "$cells"
        return 0
    fi

    # Defense in depth: run_harness strips billing keys itself, but every
    # launcher reaching the planner also goes through run_planner.
    source "$REPO/track/launchers/planner_env.sh"

    local exp stash_dir stash_tar members_file
    exp="$(exp_version_of "$manifest")"
    stash_dir="$(mktemp -d "${TMPDIR:-/tmp}/tsm_ablation.XXXXXXXX")"
    chmod 700 "$stash_dir"
    stash_tar="$stash_dir/stash.tar"
    members_file="$stash_dir/members.txt"

    restore() {
        if [ -f "$stash_tar" ]; then
            tar -C "$RES" -xf "$stash_tar"
            rm -rf "$stash_dir"
            echo "restored stashed members"
        fi
        bash "$REPO/track/setup/pin_check.sh"
    }
    trap restore EXIT TERM INT

    [ -d "$RES/libero/memory" ] || {
        echo "FATAL: $RES/libero/memory missing before stash" >&2; exit 1; }
    stash_members > "$members_file"
    tar -C "$RES" -cf "$stash_tar" -T "$members_file"
    while read -r member; do
        [ -n "$member" ] && rm -rf "${RES:?}/$member"
    done < "$members_file"
    echo "stashed -> opaque tar outside repo:"
    sed 's/^/  /' "$members_file"

    # Block rpent's HF auto-resync of the stashed memory dataset.
    export HF_HUB_OFFLINE=1

    local suite task_id seed run_parent latest
    while read -r suite task_id seed; do
        [ -n "$suite" ] || continue
        run_parent="$OUT_ROOT/$exp/harness/${suite}_t${task_id}/$seed"
        if compgen -G "$run_parent/2*/result_row.json" > /dev/null; then
            echo "=== skip (already has a row): $suite t$task_id s$seed ==="
            continue
        fi
        echo "=== ablation $exp $suite t$task_id seed $seed ==="
        PYTHONPATH= run_planner "$PY" -m track.launchers.run_harness \
            --suite "$suite" --task-id "$task_id" --seed "$seed" \
            --manifest "$manifest" --out-root "$OUT_ROOT" || \
            echo "WARNING: seed $seed exited infra (row retained); continuing"
        latest="$(ls -td "$run_parent"/2* | head -1)"
        tripwire "$latest" "$stash_dir"
        hygiene_after_seed "$latest" "$members_file"
    done <<< "$cells"

    PYTHONPATH= "$PY" -m track.analysis.build_ledger \
        --runs-root "$OUT_ROOT" \
        --out "$REPO/artifacts/ablation/ledger.csv"
    echo "ablation queue done"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
```

- [ ] **Step 4: Make executable and run the tests**

```bash
chmod +x track/launchers/run_ablation_memory.sh
PYTHONPATH= .venv/bin/python -m pytest track/tests/test_ablation_memory_launcher.py -q
```
Expected: PASS (8 tests)

Then confirm the real dry run against the real resources tree:

```bash
bash track/launchers/run_ablation_memory.sh --dry-run
```
Expected: `exp_version v4`, the member list including `libero/memory`, all four `results_*_pert` dirs and `.cache`, and 20 cells with no seed 0. Verify afterwards that `RPent/resources/libero/memory/MEMORY.md` still exists and `bash track/setup/pin_check.sh` is clean.

- [ ] **Step 5: Commit**

```bash
git add track/launchers/run_ablation_memory.sh track/tests/test_ablation_memory_launcher.py
git commit -m "feat: generalized run_ablation_memory.sh (manifest-driven, per-seed clean slate, shared tripwire)"
```

---

### Task 8: `run_ablation_hiddenmem.sh` becomes a thin wrapper

The Day-8 command in the handoff must keep reproducing.

**Files:**
- Rewrite: `track/launchers/run_ablation_hiddenmem.sh`
- Test: `track/tests/test_ablation_memory_launcher.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `track/tests/test_ablation_memory_launcher.py`:

```python
HIDDENMEM = REPO / "track" / "launchers" / "run_ablation_hiddenmem.sh"


def test_day8_wrapper_delegates_with_the_v2_hiddenmem_manifest(bash, tmp_path):
    """The Day-8 entry point documented in the handoff must still work."""
    res = fake_resources(tmp_path)
    r = bash(f'bash {HIDDENMEM} --dry-run',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "v2-hiddenmem" in r.stdout
    cells = [l for l in r.stdout.split("\n") if l.startswith("libero_")]
    assert len(cells) == 5
    assert all(c.startswith("libero_object_swap 2 ") for c in cells)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_ablation_memory_launcher.py -q -k day8_wrapper`
Expected: FAIL — the old script does not accept `--dry-run`

- [ ] **Step 3: Rewrite the wrapper**

Replace the entire contents of `track/launchers/run_ablation_hiddenmem.sh`:

```bash
#!/usr/bin/env bash
# Day-8 predeclared hidden-memory ablation (registry v2-hiddenmem).
#
# Kept as the documented Day-8 entry point; the condition logic now lives in
# run_ablation_memory.sh, which this pins to the v2-hiddenmem manifest.
# Note the v2-hiddenmem stash was family-scoped (object TSM only) whereas v4
# hides all four TSM dirs — see day12_ablation_design.md section 3 for why
# the two are reported separately and never pooled.
#
# Any extra arguments are forwarded, so `--dry-run` and `--limit N` work.
set -euo pipefail
REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
exec bash "$REPO/track/launchers/run_ablation_memory.sh" \
    --manifest "$REPO/track/manifests/ablation_hiddenmem_v2.json" "$@"
```

Note the behaviour change to record in the commit message: the old script
accepted bare seed arguments (`run_ablation_hiddenmem.sh 4 5`). Seeds now
come from the manifest, and slicing is `--limit N`.

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH= .venv/bin/python -m pytest track/tests/test_ablation_memory_launcher.py -q`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add track/launchers/run_ablation_hiddenmem.sh track/tests/test_ablation_memory_launcher.py
git commit -m "refactor: run_ablation_hiddenmem.sh delegates to run_ablation_memory.sh

Seeds now come from the manifest; the old bare-seed form is replaced by
--limit N. Day-8 reproduction path preserved and covered by a test."
```

---

### Task 9: registry rows, full suite, and handoff

**Files:**
- Modify: `track/registry/experiment_registry.md` (add the v4 row)
- Modify: `track/registry/risk_log.md` (add two rows)
- Modify: `track/registry/memory_audit.md` (add §8)
- Modify: `.project_notes/CLAUDE_HANDOFF.md` (§2 status, §5 registry table, §8 commands, §10 next steps)

- [ ] **Step 1: Add the v4 registry row**

Append a row to the table in `track/registry/experiment_registry.md` matching the existing column layout, recording: version `v4`, condition harness-only, the 4 cells, seeds 1–5, no bootstrap, budgets 1200/60/2400, planner `claude_code/claude-opus-4-8`, RPent pin `6e4ba18`, manifest `ablation_zeroshot_v4.json`, design/predeclaration commit `e6c253d`, artifacts root `artifacts/ablation/runs/v4`, and "never pooled with the core paired ledger".

- [ ] **Step 2: Add the risk rows**

Append to `track/registry/risk_log.md`:
- Row: *Ablation-condition integrity generalized to 4 cells* — mitigation: shared `leak_rules.py` consumed by both tripwire and pytest; both historical violations pinned as positive controls; per-seed clean slate; status `mitigated`.
- Row: *Turn-cap confound in the no-memory arm* — no-memory runs may spend turns re-deriving calibration and hit the 60-turn cap, so some failures will be `turn_budget` rather than task failure; mitigation: report the terminal-reason breakdown separately, never folded into the success rate; status `monitoring`.

- [ ] **Step 3: Add `memory_audit.md` §8**

Add a section documenting: the 199-pattern rule set and why bare paths and the 7 prompt-named leaves are excluded; that Day-8's tripwire scanned 3 of the 5 planner-visible artifact globs and v4 scans all 5; and that the inventory is checked in so the audit works while memory is stashed.

- [ ] **Step 4: Run the FULL suite and the pin check**

```bash
bash track/setup/pin_check.sh
PYTHONPATH= .venv/bin/python -m pytest track/tests/ -q
```
Expected: `pin check OK` and **all tests pass** — 118 baseline + ~34 new (20 leak_rules, 6 leakage audit, 9 launcher, 3 manifest) ≈ **152**. Record the actual number; do not assert a guessed count anywhere.

- [ ] **Step 5: Update the handoff**

In `.project_notes/CLAUDE_HANDOFF.md`: §2 to "Day-12 machinery built and tested, queue not yet run"; §5 registry table to add the v4 row; §8 to add
`bash track/launchers/run_ablation_memory.sh [--dry-run] [--limit N]`; §10 to
replace the Day-12 bullet with the remaining steps (pilot → 2 windows →
analysis).

- [ ] **Step 6: Commit and push**

```bash
git add track/registry/ .project_notes/CLAUDE_HANDOFF.md
git commit -m "docs: Day-12 registry rows, leakage-audit note, and handoff update"
git push garyd main
```

---

## Self-Review

**Spec coverage:**

| spec section | task |
|---|---|
| §1 condition (hide GM + all 4 TSM + HF cache) | Task 7 `stash_members` |
| §1 no seed-0 bootstrap | Task 2 (manifest assertion) |
| §1 per-seed clean slate | Task 7 `hygiene_after_seed` + 2 tests |
| §2 cells and pairing | Task 2 |
| §3 predeclaration | already committed `e6c253d`; echoed in the manifest's `frozen` field (Task 2) |
| §4 generalize not fork; live abort; resume-skip; `--limit` | Task 7, Task 8 |
| §5 shared rule module, 43+156 patterns, exclusions, controls, inventory drift | Tasks 3–6 |
| §5 quarantine + infra-retry classification | Task 7 `tripwire` |
| §6 hard budget | recorded in the manifest `caps.max_rollouts = 26` (Task 2); enforcement is the queue operator's, not code |
| §7 deliverables | Tasks 2–9 |
| §9 turn-cap confound | Task 9 risk row |

**Deliberately out of scope** (spec §8 steps 3–6, after review): the attended pilot, the two planner windows, and the Δ_S vs Δ_T analysis. The analysis will need a small addition to `compare.py` for the paired per-side statistic; that is a separate plan once real v4 rows exist, since its shape depends on the terminal-reason mix.

**Placeholder scan:** no TBD/TODO; every code step carries complete code; every command carries expected output.

**Type consistency:** `content_patterns(inventory=None, stash_dir=None)`, `scan_text(text, patterns)`, `scan_run_dir(run_dir, stash_dir=None, inventory=None)`, `record_inventory(resources_dir, out_path)`, `load_inventory(path)` are used with these exact signatures in Tasks 3–7 and in both shell call sites (`--scan`/`--stash`, `--record`/`--out`). Shell functions `stash_members`, `plan_cells`, `exp_version_of`, `hygiene_after_seed(run_dir, members_file)`, `tripwire(run_dir, stash_dir)` match their test call sites in Task 7.

**Known risk in this plan:** Task 7's `test_dry_run_*` tests set `TRACK_RES` to a fake tree but `plan_cells`/`exp_version_of` still use the real repo's `.venv` and manifests — intended, since only the resources tree needs faking. If `.venv` is missing, those tests fail with a clear interpreter error rather than a confusing assertion.
