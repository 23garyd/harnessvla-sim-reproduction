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
(v2-hiddenmem, family-scoped stash) scored **3/3 without memory vs 1/3
with it on the same seeds** — memory was net *harmful* on that swap
cell, via reference-coordinate anchoring (`day9_case_studies.md`). If
that mechanism generalizes, Δ_S may come out **negative**,
contradicting H1. That result is reported alongside but **not pooled**
into v4: different `exp_version`, and its stash hid only the object
family's TSM.

> **Amended 2026-07-29, before any v4 rollout.** This paragraph
> originally cited the Day-8 result as 5/5 vs 2/5. Building the §5
> leakage audit revealed that Day-8 seeds 1–2 ran before the HF cache
> was stashed and their transcripts carry the leaked Global Memory note
> filenames; both rows are now quarantined and the figures above are the
> clean-row restatement. **H1, H0 and the decision rule are unchanged** —
> only this counterexample's n. Amending it is legitimate because the v4
> result set is still empty; the §3 freeze binds from the first v4 row.
> See `day8_mechanism.md` §4 Day-12 correction.

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
alongside the 3 clean v2-hiddenmem rows.

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

---

## 10. RESULTS (appended 2026-07-30 — §3 is frozen and untouched)

20/20 v4 rows, all raw-verified against `states.json`, zero leaks across all
20 runs, zero infra failures, zero tripwire aborts, teardown verified
bit-identical (619 files) after both windows.

| cell | side | with memory | no memory | Δ | per-seed (s1→s5) |
|---|---|---|---|---|---|
| spatial_task t2 | T | 5/5 | 5/5 | +0.00 | == == == == == |
| object_task t2 | T | 5/5 | 5/5 | +0.00 | == == == == == |
| spatial_swap t2 | S | 5/5 | 5/5 | +0.00 | == == == == == |
| goal_swap t2 | S | 3/5 | **2/5** | — | LO LO .. GA == |

| side | with memory | no memory | Wilson 95% (no-mem) | Δ |
|---|---|---|---|---|
| **T** (redirection) | 10/10 | 10/10 | [0.72, 1.00] | **+0.00** |
| **S** (swap) | 8/10 | 7/10 | [0.40, 0.89] | **+0.10** |

Paired flips: 16 both-pass, 1 both-fail, **2 lost** (memory helped), **1
gained** (memory hurt). All four flips are in `goal_swap`.

### Verdict against the predeclared decision rule

Δ_S = +0.10 > Δ_T = +0.00, so H1 is **confirmed on the point estimate**. Per
§3's pre-committed language, because the side CIs overlap heavily
([0.49,0.94] vs [0.40,0.89]) this is reported as **directionally consistent,
not established**. The whole effect is **one net seed**.

### The mechanism is a budget effect, not a grounding failure

This is the load-bearing caveat, and §9's pre-registered confound
materialising — via the 1200 s planner timeout rather than the 60-turn cap
we anticipated:

| arm | terminal reasons (these 4 cells) |
|---|---|
| with memory | 18 `benchmark_predicate`, 1 `planner_finished_without_predicate`, 1 `turn_budget` |
| no memory | 17 `benchmark_predicate`, **3 `planner_timeout`** |

**All three no-memory failures are `planner_timeout`** on `goal_swap`, at
46/51/49 turns with 2 pi0 calls each — i.e. *below* the 60-turn cap and still
working when the pinned 1200 s wall-clock cut them off. They are
`budget_exhausted`, not task failures. Under the frozen protocol they score
as failures (1200 s is a pinned v2 regime bound, not retuned mid-experiment),
and that is how they are counted above.

So the honest mechanism claim is **not** "without memory the planner cannot
re-ground a swapped fixture". It is: **without memory the planner must
re-derive calibration, which costs wall-clock, and on `goal_swap` that cost
exceeds a pinned budget.** Memory's measured value here is *deliberation
time*, not capability. Whether the paper's re-grounding mechanism exists at
this pin is **untested** — a longer planner timeout would likely convert
these three rows, and that experiment has not been run.

### What did NOT reproduce

The paper's predicted asymmetry is a **−56 pt** swap-cell collapse against
**−8 pt** for redirection. Measured: **−10 pt vs 0 pt**. The direction
matches; the magnitude does not, by a factor of ~5. Three of the four cells
show *zero* effect from removing Global Memory **and** all four TSM
directories — `spatial_swap`, a swap cell with a released seed-0 reference,
was 5/5 either way.

### Concordant prior

Day-8's `object_swap` ablation (3/3 without memory vs 1/3 with, clean rows)
remains the one cell where memory was net *harmful*, via reference-coordinate
anchoring. The single `GAINED` flip here (`goal_swap` s4: fails with memory,
succeeds without) is the same sign and worth a Day-13 look.

### Cost check

No exploration penalty on successes: no-memory 20–51 turns (median 26) vs
with-memory 16–40 (median 23), same median of 1 pi0 call. The penalty is
concentrated in the failures, which is exactly the timeout story.

---

## 11. FOLLOW-UP PREDECLARATION — the timeout confound (v5-longtimeout)

**Frozen 2026-07-30, BEFORE any v5 rollout.** §3 and §10 are unchanged and
remain frozen; this is a separate diagnostic arm, never pooled into the v4
result.

### Why

Every v4 no-memory failure came back `planner_timeout` — `goal_swap` s1/s2/s3
at 46/51/49 turns with 2 pi0 calls each, i.e. **below** the 60-turn cap and
still working when the pinned 1200 s planner wall-clock cut them off. Those 3
rows are the *entire* Δ_S = +0.10 signal. So the v4 result cannot presently
distinguish:

- **budget effect** — memory buys deliberation time, and without it the
  planner exceeds a pinned clock; or
- **capability effect** — memory enables re-grounding a swapped fixture, as
  the paper claims.

§10 reports the budget reading as the honest one. This arm tests it.

### Condition

Re-run exactly those 3 seeds with the planner timeout **doubled to 2400 s**
(wall cap raised 2400 → 3600 s to stay above it). Everything else identical to
v4: same zero-shot stash (Global Memory + all four TSM dirs + HF cache), same
60-turn cap, same 1200-step budget, same checkpoint, same planner model, same
seeds. **The planner wall-clock is the only change** — enforced by a test
asserting v5's budgets differ from v4's in that key alone, and by
`planner_timeout_s()` defaulting to the pinned 1200 s so v1–v4 stay
bit-reproducible.

### Predeclared three-way readout

| outcome | reading |
|---|---|
| **H_budget** — ≥1 of 3 converts to success, or failures move off `planner_timeout` | the 1200 s bound was binding; v4's swap-side signal is substantially a clock artifact and §10's budget reading is confirmed |
| **H_capability** — all 3 fail again, terminal reasons NOT `planner_timeout` (`turn_budget` / `valid_failure`) | the memory-free planner genuinely cannot solve these seeds; v4's signal reflects capability, and the paper's mechanism gains support |
| **H_unbounded** — all 3 still `planner_timeout` at 2400 s | deliberation cost is large and unbounded at this pin; report as a regime limitation and **do not retune further** |

Whatever the outcome, **the v4 numbers in §10 stand exactly as reported**.
This arm changes their *interpretation*, not their values. n=3 — the readout
is qualitative and directional, and no CI is claimed.
