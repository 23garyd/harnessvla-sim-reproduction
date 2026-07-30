# Day-12: memory ablation — design & predeclaration (registry v4)

**Frozen 2026-07-29, BEFORE any v4 rollout.** This commit is the Day-12
acceptance gate: the predicted asymmetry in §3 is written down while the
result set is still empty. Nothing in §3 may be edited after the first
v4 row lands; a changed hypothesis requires a new registry version.

Environment at freeze: RPent pin `6e4ba18` clean, 118 tests green,
core v1/v2 and extension v3 frozen (80 scored rollouts, 40 pairs).

## 1. The condition (paper Table 5 zero-shot)

The paper's zero-shot condition is: no Task-Specific Memory or Global
Memory retrieval for the target setting, everything else held. Mapped
onto the released RPent assets:

| released asset | role | v4 |
|---|---|---|
| `resources/libero/memory/` (50 notes + `MEMORY.md` index) | Global Memory | **hidden** |
| `resources/libero/results_{spatial,goal,object,10}_pert/` (seed-0 references + recipes) | Task-Specific Memory | **hidden, all four** |
| `resources/.cache/` (HF download cache) | leaks note *filenames* via `.lock`/`.metadata` | **hidden** |

All four TSM directories are hidden, not just the family under test, so
cross-family recipe transfer is blocked and every cell sees an identical
condition.

Mechanism (inherited from the hardened Day-8 path): one opaque tar in a
0700 `mktemp` dir outside the repo, `HF_HUB_OFFLINE=1` to block rpent's
HF re-sync, trap-restore on EXIT/TERM/INT, `pin_check` after restore.
`resources/` is gitignored in RPent, so stashing does not dirty the
worktree and `run_harness`'s `pin_check` still passes mid-ablation.

**Held identical to v2/v3** — the only intended difference is memory
access: system prompt and guides verbatim (including the instruction to
`list_dir resources/libero/memory/`), primitives, frozen pi0.5
checkpoint, `claude_code/claude-opus-4-8`, budgets 1200/60/2400,
`libero_terminated` scoring, seed set.

**No seed-0 bootstrap.** Bootstrapping would manufacture the memory
being ablated; its absence *is* the zero-shot condition. Seeds 1–5 only.

**Per-seed clean slate** (new; Day-8 lacked it): after each run, any
planner-created file under the hidden paths is moved into that run's
artifacts as evidence and the path restored to absent, so run *k* cannot
inherit run *k−1*'s notes. `pin_check` cannot catch this because
`resources/` is gitignored, so the check is explicit.

## 2. Cells and pairing

Baseline = the frozen with-memory rows, reused, never re-run. v2 and v3
carry identical budgets (1200/60/2400), pins, and planner model, so
pairing across them is legitimate.

| side | cell | baseline (with memory) | source |
|---|---|---|---|
| redirection (T) | `libero_spatial_task` t2 | 5/5 | v2 |
| redirection (T) | `libero_object_task` t2 | 5/5 | v3 |
| swap (S) | `libero_spatial_swap` t2 | 5/5 | v3 |
| swap (S) | `libero_goal_swap` t2 | 3/5 | v2 |
| | **T side** | **10/10** | |
| | **S side** | **8/10** | |

Selected for **headroom**, not for family symmetry. An ablation that
predicts a *drop* can only be measured where the with-memory arm has
successes to lose, so cells at 3/5–5/5 are the highest-power detectors
and cells at floor are uninformative. This inverts the Day-11 note that
the two ceiling cells "carry no signal" — true for detecting a *gain*,
backwards for detecting *harm*.

Excluded, pre-registered with reasons:

| cell | with memory | why excluded |
|---|---|---|
| `libero_goal_task` t2 | 1/5 | floor — cannot fall |
| `libero_10_task` t3 | 0/5 | floor — cannot fall |
| `libero_10_swap` t2 | 2/5 | near-floor, and stresses the pinned 1200 s planner timeout |
| `libero_object_swap` t2 | 2/5 | already ablated on Day 8 (see §3) |

## 3. PREDECLARATION (written before results)

**H1:** Δ_S > Δ_T, where Δ = (with-memory success rate) − (no-memory
success rate), pooled per side over 10 seed-paired rollouts each.
**H0:** Δ_S ≤ Δ_T.

Paper basis for the direction (plan §2, zero-shot vs few-shot Goal):
Goal-T 79.0 vs 87.0 = **−8.0 pt**; Goal-S 31.0 vs 87.0 = **−56.0 pt**.
Removing memory should cost swap cells far more than redirection cells.

**Decision rule.** Confirmed if Δ_S > Δ_T in point estimate. Reported
with Wilson 95% CIs per side and per cell, plus paired flip counts
(kept / lost / gained). Declared now, before results: **n = 10 per side
cannot reach significance** — per the direction-not-magnitude charter the
verdict is directional only, and a Δ_S > Δ_T that falls inside
overlapping CIs will be reported as *directionally consistent, not
established*.

**Headroom disclosure.** The T side starts at 10/10 and the S side at
8/10, so the redirection side has *more* room to fall. The design is
therefore biased **against** H1, and a confirmed Δ_S > Δ_T cannot be a
ceiling artifact.

**Family-composition caveat.** The paper's asymmetry evidence is
Goal-family. Headroom forces our T side onto Spatial/Object and leaves
only one Goal cell (goal_swap, S side), so a null result is ambiguous
between "the asymmetry does not reproduce" and "it is Goal-specific".
Recorded now, not after the fact.

**Pre-existing counterexample.** The Day-8 ablation of `object_swap`
(v2-hiddenmem, family-scoped stash) scored **5/5 without memory vs 2/5
with it** — memory was net *harmful* on that swap cell, via
reference-coordinate anchoring (`day9_case_studies.md`). If that
mechanism generalizes, Δ_S may come out **negative**, contradicting H1.
That result is reported alongside but **not pooled** into v4: different
`exp_version`, and its stash hid only the object family's TSM.

## 4. Machinery

Generalize, do not fork. `run_ablation_hiddenmem.sh` hardcodes the cell,
2 stash members and 2 tripwire patterns; it becomes
`run_ablation_memory.sh`, reading cells from `--manifest` (default
`ablation_zeroshot_v4.json`) and keeping the proven per-seed loop over
`run_harness` — deliberately *not* `batch_runner`, so the tripwire can
abort **live** between seeds instead of discovering a leak after a whole
planner window has burned. Adds resume-skip and `--limit` for window
slicing; ends in `build_ledger` as today. `run_ablation_hiddenmem.sh`
remains as a thin wrapper pinning the v2-hiddenmem manifest so the Day-8
command still reproduces.

Artifacts land in `artifacts/ablation/runs/v4/...` and never enter the
core paired ledger; `artifacts/ablation/ledger.csv` gains the v4 rows
alongside the 5 v2-hiddenmem rows.

## 5. Leak audit

`track/analysis/leak_rules.py` is the single source of truth, consumed by
**both** the shell tripwire and pytest so queue-time and test-time rules
cannot diverge.

Content-bearing patterns (a hit means memory content was obtained):
the stash path; the **43** memory leaf basenames *not* named in the
released prompts; concrete `results_*_pert` reference and recipe
basenames (prompts name only the generic `recipe_` / `recipe_tag`).

Deliberately **not** patterns, because `prompts/system.py:393-414`
instructs the planner to `list_dir` them — their appearance is a prompt
echo and is the condition *working*: the bare paths
`resources/libero/memory` and `resources/libero/results_*_pert`, and the
7 basenames named in the released prompts/guides (`MEMORY`, `README`,
`feedback_bowl_eef_y_offset`, `feedback_failure_forensics`,
`feedback_pi0_pick_full_prompt`, `feedback_scripted_pick_limits`,
`feedback_swap_perturbs_fixtures`).

Patterns derive from a checked-in `track/registry/memory_inventory.txt`
(recorded via `--record`), not the live directory — so the audit works
post-restore *and* while memory is stashed, with a drift test asserting
the inventory matches the live directory whenever memory is present.

`track/tests/test_ablation_leakage.py` (plan deliverable): scans every
ablation run's planner-visible transcripts (`launcher.log`,
`rpent/run.log`, `rpent/*.stream.jsonl`, strategy notes); **positive
control** — a synthetic transcript containing a known leaf name must be
flagged; **negative control** — a prompt-echo-only transcript must not
be; **no-silent-skip guard** — asserts run dirs were actually found when
v4 rows exist in the ablation ledger.

A violated run is quarantined under `artifacts/ablation/quarantine/`,
excluded from results, and retried at infra cap 2 — a condition
violation is an infra failure, not a valid failure.

## 6. Hard budget (freeze)

Measured harness cost: 786 s mean launcher clock (success 414 s,
failure 1242 s), 99 MB/run. Budgeted at the failure-weighted mean since
no-memory runs should skew toward the tail (more turns re-deriving what
memory supplied).

| item | count | est. |
|---|---|---|
| harness no-memory scored | 20 | ~5.5 h |
| infra/quarantine retry headroom | ≤6 | ~1.5 h |
| **total** | **≤26 launches** | **≤7 h** |

Caps: **≤26 launches, ≤7 h compute, ≤12 harness cells per planner
window (2 windows ≥3 h apart), ≤3 GB new artifacts** (6.0 → ~8 GB
against the 200 GB cap). Pre-registered fallback: if a quarantine burns
a window, drop to the two highest-power cells (`spatial_swap` vs
`spatial_task` — same family, both 5/5) rather than exceed the caps.

## 7. Deliverables & gate

This document (predeclaration committed before results) ·
`ablation_zeroshot_v4.json` · `run_ablation_memory.sh` ·
`leak_rules.py` + `memory_inventory.txt` ·
`test_ablation_leakage.py` (118 → ~126 tests) ·
`memory_audit.md` §8 leakage-audit note ·
`experiment_registry.md` v4 row · `risk_log.md` entries ·
`progress_log.md` Day-12 entry **with the result table**.

Plan gate: *"the only intended difference is access to bootstrapped
harness memory, and the predicted swap-versus-redirection asymmetry is
written down before results arrive."* §1 establishes the first, §3 the
second.

No new `protocol_deviations.md` row: hiding both memory types **is** the
paper's zero-shot protocol, and the 4-cell scale is already covered by
the existing scale-deviation row.

## 8. Sequence

1. Commit this design + predeclaration ← **the gate**
2. Build machinery TDD; full suite green (118 + the new leakage tests)
3. Attended pilot: 1 cell / 1 seed, verify condition + tripwire fire correctly
4. Queue 2 planner windows (≤12 cells each, ≥3 h apart)
5. Analyze Δ_S vs Δ_T with CIs and flip counts; raw-verify every row
6. `progress_log.md` Day-12 entry with the result table

## 9. Known risks

- **Planner memory-hunting** (Day-8 attempt-1 behavioral finding): the
  planner actively searches for hidden memory. Countermeasure is the
  opaque out-of-repo stash + per-seed tripwire; residual risk is a
  channel we have not enumerated, which is why the tripwire aborts the
  queue rather than merely annotating.
- **Anchoring may dominate on swap cells** (Day-9 mechanism), pushing Δ_S
  negative. That is a result, not a defect — see §3.
- **Turn-cap confound**: no-memory runs may spend turns re-deriving
  calibration and hit the 60-turn cap, so some no-memory failures will be
  `turn_budget` rather than task failure. Reported as a distinct
  terminal-reason breakdown, not folded silently into the success rate.
- **Long-horizon timeout** is avoided by construction — no LIBERO-10 cell
  is in the v4 set.
