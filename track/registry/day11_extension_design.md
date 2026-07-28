# Day-11: extension design, decision & hard budget

## 1. Extension-question decision (from measured MVP bottlenecks)

Plan options: (a) broader task families, (b) stronger ablation,
(c) repeatability. **Chosen: (a) broader task coverage.** Rationale:

- (b) is structurally covered: Day 12 IS the memory ablation proper
  (paper zero-shot protocol), and the Day-8/9 single-cell ablation
  already built and hardened the condition machinery (opaque stash,
  leak tripwire). What Day 12 lacks is CELLS — which (a) supplies.
- (c) is structurally covered by Day 14 (planner variability).
- The MVP's sharpest open questions are cell-shaped: does the Goal-T
  no-gain (pi0 place-reflex) generalize to other redirection cells?
  Does the anchoring regression generalize to other swap cells with
  released references? Both need the missing family cells.

## 2. Extension matrix (registry v3)

+4 suites at t2 (uniform with the core), giving the complete 4×2 grid:

| family | redirection (task) | swap |
|---|---|---|
| Spatial | spatial_task t2 (core) | **spatial_swap t2 (NEW)** |
| Goal | goal_task t2 (core) | goal_swap t2 (core) |
| Object | **object_task t2 (NEW)** | object_swap t2 (core) |
| LIBERO-10 | **10_task t2 (NEW)** | **10_swap t2 (NEW)** |

8 tasks total (plan max), 5 held-out seeds each, seed 0 bootstrap-only —
a balanced 4v4 redirection/swap design that directly serves Day-12's
predeclared asymmetry hypothesis (memory removal should hurt swap cells
more than redirection cells). All 4 new cells have released seed-0
references (`results_*_pert/*_t2_s0.json` + recipes), so the harness
condition is exercised exactly as released. Core v1/v2 cells are frozen
and are NOT re-run; v3 rows are additive.

## 3. Budget forecast (from measured v1/v2 ledger data) and HARD CAP

Measured: direct 96 s mean driver time (~4 min/run with env boot,
≈0 MB/run); harness 786 s mean launcher-clock incl. boot (success 414 s,
failure 1242 s), 99 MB/run. LIBERO-10 is long-horizon → budget at the
failure-weighted mean, not the median.

| item | count | est. | basis |
|---|---|---|---|
| direct scored | 20 | ~1.3 h | 4 min/run |
| harness bootstrap (s0 pilots) | 4 | ~1.3 h | ~20 min/run |
| harness scored | 20 | ~5.5 h | 16 min/run (failure-weighted; LIBERO-10 uplift) |
| infra-retry headroom | ≤8 | ~2 h | retry cap 2 |
| **total compute** | ≤52 launches | **~8–10 h** | fits 2 evening windows |
| planner windows | 24 harness runs | **2 windows ≤12 each** | session-limit rule (risk log) |
| disk | ~24 harness + 20 direct | **~2.5 GB** (→ ~6 GB total) | 99 MB/harness run |

**Hard extension budget (freeze):** ≤52 rollout launches, ≤10 h compute,
≤12 harness cells per session window, ≤5 GB new artifacts. If LIBERO-10
pilots reveal per-run costs >1.5× the estimate, drop the LIBERO-10
family to one cell (10_swap, the Day-12-relevant one) rather than
exceed the cap — decision pre-registered here.

## 4. Pilot protocol (today, attended)

Per new suite: 1 direct pilot on s1 (scored — a valid pilot IS the
first matrix row, as on Day 3) + 1 harness pilot on s0 (bootstrap,
never scored). Repair only family-specific infra; any repair is a
launcher/setup change logged in the registry change log, never a
protocol change. Gate: every added family has one valid direct and one
valid harness pilot.

## 5. Known family-specific risks (watch in pilots)

- LIBERO-10: long-horizon → 600-step direct horizon may bind harder
  than in short tasks (benchmark default kept for uniformity; if a
  pilot shows wall-to-wall step exhaustion with partial progress, that
  is a scored budget_exhausted, not infra); harness 60-turn cap likely
  tighter here (record, don't retune).
- Env step-accounting death (day7_triage §4) more likely at long
  horizons — rows stay scored (turn_budget) per the frozen protocol.
- object_task language redirection may trigger the same pi0
  place-reflex chain as goal_task — that is the scientific point of
  adding it, not a defect.
