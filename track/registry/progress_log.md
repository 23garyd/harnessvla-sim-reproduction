# Progress log (day-by-day)

One entry per internship-plan day. "Day N" refers to the sim plan's day
numbering (docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx);
calendar dates differ because several plan-days were completed per session.
Detailed evidence lives in the files each entry points to.

## Day 1 — paper/code map & track setup (2026-07-26)

- Track home created and split from the ASPIRE folder (HANDOVER.md); private
  repo `nuPylot/harnessvla-sim` created and pushed.
- Architecture designed and frozen: spec
  (`docs/superpowers/specs/2026-07-26-sim-track-architecture-design.md`) —
  planner = claude_code on subscription (key stripped), 200 GB artifact cap,
  single-tree layout with pinned, never-edited RPent.
- Scaffolding built via 12 reviewed tasks: setup/pin/env scripts, key-hygiene
  lib, run-record schemas, ledger builder, disk guard, manifest validator,
  registry docs, README; 64 tests green.
- Gate: mentor can trace claim→code (registry + spec + plan committed). ✅

## Day 2 — environment install & component smoke tests (2026-07-26, tag `day2-install-smoke`)

- `setup.sh all` on the A6000: RPent pinned at `6e4ba18`, venv (10 GB stack),
  pi0.5 checkpoint (20 GB, sha256 recorded), LIBERO-PRO assets (865 files).
- 4 stack bugs found & fixed into setup.sh: wrong checkpoint repo URL in the
  plan (model repo, different casing), LIBERO assets missing from wheel,
  openpi's lerobot pin invisible to pip (uv-only sources table), HF download
  cache polluting checksums.
- Smoke tests PASS: env_server (reset/render/RGB-D/camera meta/step) and
  vla_server (pi0.5 load ~130 s, action chunk (5,7) validated).
- `requirements.lock` + `env_manifest.md` frozen. Evidence:
  `track/setup/setup_notes.md` (Day-2 sections), `track/smoke/`.
- Gate: reset/render, pi0.5 inference, one safe action from the documented
  environment. ✅

## Day 3 — core freeze & direct baseline (2026-07-27, tag `day3-baseline-frozen`)

- Core matrix frozen (`track/manifests/core_v1.json`, registry v1): 4 cells
  by anchor numbers (spatial_task, goal_task, goal_swap, object_swap; t2;
  s1–s5), seed distinctness verified + committed
  (`core_v1_seed_check.txt`).
- Direct baseline built (design option b, `track/registry/baseline_design.md`):
  `run_direct.py` + `direct_lib.py` (15 tests; suite 79 green).
- Real bug found by live validation: LiberoEnv reset burns 15 settle steps of
  robosuite's horizon → deterministic crash at step 585; fixed with +20 env
  horizon slack (scoring cap unchanged at 600). 2 infra rows retained.
- Gate rollouts: object_swap s1 success (143 steps), spatial_task s1
  budget_exhausted (600). ✅
- Evening queue (attended): 8/8 valid → 10/20 direct cells scored, direction
  matches the paper's anchors (Object-S 3/3, Spatial-T 0/3, Goal-T 1/2,
  Goal-S 0/2; aggregate 4/10 vs paper direct 50.0%). Evidence:
  `track/setup/setup_notes.md` (Day-3 sections), `artifacts/ledger.csv`.

## Day 4 — first harness execution (2026-07-27)

- SAM3 perception stage added to setup.sh (sam3.pt sha-pinned + the CLIP BPE
  vocab the pip wheel omits — 4th missing-package-data bug).
- Released seed-0 assets studied (auto-synced from `RLinf/RPent-memory`):
  recipe skeleton + spatial literals extracted as audit references.
- First harness rollout (rpent, claude_code planner claude-opus-4-8,
  key-stripped subscription billing): object_swap t2 s0 SOLVED in 437 s /
  33 turns with live re-grounding, bounded pi0_pick, failed-release retry,
  empty-grasp recovery with analytic fallback, staged transport, recipe write.
- Annotated trace + 4 audits committed
  (`track/traces/day4_object_swap_t2_s0_annotated.md`): vocabulary ✅ (note:
  plan's `vla_act` = repo's `pi0_pick`), zero resets ✅, no coordinate replay
  ✅, benchmark-predicate terminal ✅.
- Gate: trace visibly contains planner staging AND retry around the same
  frozen pi0.5. ✅
- Evening queue: direct matrix COMPLETED 20/20 (5/20 aggregate; Object-S 4/5,
  hard cells at/near floor — ordering matches anchors) + 3 harness pilots on
  held-out seeds (2/3 success; s2 proved re-grounding on a shifted basket;
  s1 failure = recurring release-from-height mode, retained as anti-example).
  Pin gate caught planner-stray contamination of RPent (10 rollouts refused
  until triaged); queue scripts now sweep strays into run dirs.
- Open for Day 5: step-cap regime decision (guides use one-shot 1200 vs our
  600), planner pin, harness manifest as registry v2, and the
  release-below-rim memory-improvement hypothesis from the pilot failure.

## Day 5 — memory validation & Week-1 protocol freeze (2026-07-27)

- Memory audit (`track/registry/memory_audit.md`): released TSM = structural
  prior with live re-grounding confirmed (identical skeleton, re-derived
  bindings, leakage grep clean); honest caveats recorded (s1's copied carry
  binding; the below-rim lesson missing from released notes — candidate TSM
  addition, not applied).
- No-memory diagnostic: hidden-memory condition works leak-free; object_swap
  s2 succeeded without memory (223 s) — consistent with Object-S being the
  strong cell; swap-asymmetry test deferred to the Day-12 ablation proper.
- Protocol frozen as registry v2 (mentor-approved): harness cells added
  (harness_v2.json; seed-0 bootstrap entries), released one-shot regime as-is
  (1200 guide budget, env backstop 1220), planner pinned
  claude-opus-4-8/60 turns; budget asymmetry vs direct 600 = deviation row 3;
  v1 direct rows carry forward as the paired arm. select_cell made
  condition-aware (82 tests green).
- Gate: harness rollout valid end-to-end ✅, memory without coordinate
  replay ✅, scoring rules frozen ✅. PASSED — cleared for the Day-6–10
  paired matrix.

## Day 6 — batch runner & first paired point (2026-07-27, tag `day6-batch-runner`)

- Built via 7 reviewed tasks (suite 82 → 101 green): task_id schema parity;
  `harness_lib` (v2 records; predicate-only CUMULATIVE scoring — review
  hardened last-entry reading into rlinf's success_once semantics);
  `run_harness` (v2-pinned rpent wrapper: key strip, wall-cap process-group
  kill, stray sweep, result_row always written); `batch_runner`
  (resume-without-overwrite, infra retry cap 2, immutable queue records,
  shared-VLA phase ordering, raw verification of every new row); ledger
  print now separates scored from infra rows.
- Day-6 gate PASSED live: core_v1 dry-run honored all 20 direct rows (0
  re-runs); one live harness cell verified against raw artifacts; stopped
  batch resumed with 19 pending and exactly one run dir (no overwrite);
  row success == raw predicate.
- The pilot is the first paired core-matrix point and it landed on the
  starkest cell: **harness SUCCESS on libero_spatial_task t2 s1 (446 s,
  1 vla_act + 9 analytic, 24 turns) where direct went 0/5.**
- Matrix-run watch items (from the final review; fix before any UNATTENDED
  queue): (1) after a verify_row "disagrees" crash, triage that run dir
  before re-invoking — a blind restart would count the bad row as done;
  (2) every `verified:` line must pair with a fresh timestamp dir (an
  early-crash retry could re-verify the previous attempt); (3) invoke the
  matrix with the single harness manifest so the queue record captures the
  full plan.
- Remaining: 19 scored harness cells (~2.5–4 h attended, planner spend on
  the subscription) → then Day 7 triage + Day 8 compare.py. Note for
  compare.py: harness wall_seconds includes ~3–4 min server boot (launcher
  clock) — not like-for-like with direct wall columns.

## Day 6 evening — PAIRED CORE MATRIX COMPLETE (2026-07-28, attended)

19/19 harness cells launched, raw-verified, 0 infra failures; ledger 42 rows
(40 scored = the Day-10 "≥40 paired scored rollouts" core requirement, met).

| cell | direct | harness | paper anchor |
|---|---|---|---|
| libero_spatial_task_t2 (Spatial-T) | 0/5 | **5/5** | 42→94 — reproduced at full amplitude |
| libero_goal_swap_t2 (Goal-S) | 0/5 | **3/5** | 42→87 — clear gain |
| libero_goal_task_t2 (Goal-T) | 1/5 | 1/5 | 45→87 — NO gain; turn budget (60) bound on 3/5 seeds |
| libero_object_swap_t2 (Object-S) | 4/5 | **0/5** | 78→90 — INVERTED: harness hurt the strong cell |
| **aggregate** | **5/20 (25%)** | **9/20 (45%)** | 50.0→82.4 — direction reproduced |

Paired flips: 9 cells direct✗→harness✓, 5 cells direct✓→harness✗, 6 both-fail.
Net +4 with strong per-cell structure: the harness closes the hardest cells
(Spatial-T, Goal-S) and DAMAGES the cell where the frozen VLA was already
strong — a sharper version of the paper's own Object-S small-gap caveat.

Day-7 triage priorities: (1) Object-S harness collapse — 0/5 scored vs 2/3 in
the pre-freeze pilots under identical pins (planner variance? regime text?
examine transcripts + finish summaries); (2) Goal-T turn-budget pressure —
was 60 turns the binding constraint (3/5 turn_budget rows say yes); (3) the
5 direct✓→harness✗ pairs as case studies. NO retuning on eval seeds — the
matrix is frozen; findings go to the deviation/limitations sections and, if
warranted, a predeclared ablation.
