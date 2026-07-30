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

**[Superseded 2026-07-28: the Object-S 0/5 and the aggregate 9/20 in the
table above were artifacts of a planner-availability failure — see the
Day 7 entry and `day7_triage.md` §1–2 for the corrected matrix
(harness 11/20, Object-S 2/5).]**

## Day 7 — matrix correction & failure-taxonomy triage (2026-07-28)

- **Session-limit forensics**: the last 4 harness cells of the Day-6 queue
  (object_swap s2–s5) hit the claude.ai subscription session limit — s3–s5
  before turn 1 (0 steps, 0 VLA calls), s2 cut at turn 44. rpent exits 0 on
  planner exceptions, so all four were misclassified valid_failure. Fixed
  by stream-level classification (planner API error → infra_failure,
  commit 61c9524; SDK planner-timeout → budget_exhausted/planner_timeout,
  commit d214888; 107 tests green), rows regenerated from raw artifacts
  (originals preserved), cells re-run under the frozen infra-retry
  protocol (0 rate limits, raw-verified): s2 ✓ 21 turns, s5 ✓ 20 turns,
  s3/s4 genuine turn_budget failures. Risk log updated (≤15 harness
  cells per session window).
- **CORRECTED CORE MATRIX (40 scored; ledger 46 rows = 40 + 6 infra)**:

  | cell | direct | harness | paper anchor |
  |---|---|---|---|
  | libero_spatial_task_t2 (Spatial-T) | 0/5 | **5/5** | 42→94 — full amplitude |
  | libero_goal_swap_t2 (Goal-S) | 0/5 | **3/5** | 42→87 — clear gain |
  | libero_goal_task_t2 (Goal-T) | 1/5 | 1/5 | 45→87 — NO gain |
  | libero_object_swap_t2 (Object-S) | 4/5 | **2/5** | 78→90 — real regression, half the artifact's size |
  | **aggregate** | **5/20 (25%)** | **11/20 (55%)** | 50.0→82.4 — direction reproduced |

  Paired flips 9 rescued / 3 regressed / 2 both-pass / 6 both-fail, net +6.
  Object-S retry detail: s2 ✓ (21 turns, 411 s), s5 ✓ (20 turns, 396 s),
  s3/s4 genuine turn_budget failures.
- Failure-taxonomy table (primary label per scored harness failure):

  | cell/seed | primary | terminal | convergent at cut? |
  |---|---|---|---|
  | Goal-T s2 | empty_grasp | planner_timeout (1200 s, turn 58) | no |
  | Goal-T s3 | transport | turn_budget (env dead turn 54) | no |
  | Goal-T s4 | release | turn_budget (env dead turn 56) | no |
  | Goal-T s5 | release | turn_budget | **yes** (~4–6 turns short) |
  | Goal-S s3 | transport | valid_failure (honest finish, 47/60) | no |
  | Goal-S s4 | grounding | turn_budget | **yes** (2–4 turns short) |
  | Object-S s1 | release | turn_budget | partial |
  | Object-S s3/s4 (retries) | deferred to Day-9 | turn_budget | — |
- Failure taxonomy over the 9 scored harness failures (7 transcript-triaged
  via subagent analysis): release 3, transport 2, empty_grasp 1,
  grounding 1. Localization is NOT the weak link (one grounding failure in
  the whole matrix); analytic release/place geometry and post-drop grasp
  re-acquisition are.
- Goal-T no-gain explained as ONE causal chain: pi0_pick executes the
  memorized base-task pick-AND-place (4 of 5 clean lifts ended with the
  policy's place reflex dumping the bottle), truncated-chunk mitigation
  yields no-op grasps, horizontal fallen bottle nearly un-graspable,
  flipped In(bottle,bowl) predicate needs an upright carry. Turn cap
  genuinely binding on only 2 of 9 failures (Goal-T s5, Goal-S s4).
  Env-death sub-finding: Goal-T s3/s4 killed their env ("executing action
  in terminated episode") at counted steps 654/804 despite backstop 1220 —
  step under-counting; recorded as limitation, not changed mid-matrix.
- Object-S regression mechanism found: the released memory's carry_z
  ballistic-release rule for tall bottles (+ the no-pi0-end-to-end
  constraint) replaces pi0's learned lower-into-cavity place with a
  ~0.2 m free-fall — not seed-robust; s1 bounced out, recovered the
  horizontal re-grasp, and ran out of turns one placement short while
  direct pi0.5 solved the seed in 143 steps. Sharpens the Day-5
  memory-audit caveat; candidate Day-12 ablation + upstream memory note.
- Upstream RPent update (user-flagged) reviewed by fetch+diff:
  `6e4ba18..c01b9cf` = 2 operational fixes (incl. the Day-2 parent-watch
  bug, independently fixed upstream) + docs; released assets and regime
  untouched → **pin unchanged**; bump recorded as extension-matrix
  candidate. Full triage: `track/registry/day7_triage.md`.
- Gate: every failure category attributed from raw artifacts, corrected
  matrix frozen, no eval-seed retuning. ✅ Next: Day 8 compare.py with
  Wilson intervals + mechanism metrics from existing traces.

## Day 8 — compare.py, mechanism metrics & hidden-memory ablation (2026-07-28)

- `track/analysis/compare.py` (TDD, 8 tests; suite 115 green): paired
  table with Wilson 95% intervals, complete-pairs-only aggregation,
  infra excluded, duplicate detection. Frozen output:

  | cell | direct k/n [Wilson 95%] | harness k/n [Wilson 95%] |
  |---|---|---|
  | libero_goal_swap_t2 | 0/5 [0.00, 0.43] | 3/5 [0.23, 0.88] |
  | libero_goal_task_t2 | 1/5 [0.04, 0.62] | 1/5 [0.04, 0.62] |
  | libero_object_swap_t2 | 4/5 [0.38, 0.96] | 2/5 [0.12, 0.77] |
  | libero_spatial_task_t2 | 0/5 [0.00, 0.43] | 5/5 [0.57, 1.00] |
  | **aggregate (complete pairs)** | **5/20 [0.11, 0.47]** | **11/20 [0.34, 0.74]** |

- Mechanism metrics from existing traces (`day8_mechanism.md`):
  **10 of 11 harness successes fire the predicate during an analytic
  primitive** (9 release, 1 move_to; 1 pi0_pick) — the paper's division
  of labor, visible in artifacts. VLA-invocation profile:

  | group | vla calls min/med/max | analytic calls | turns |
  |---|---|---|---|
  | harness success (n=11) | 1 / 1 / 2 | 3 / 7 / 9 | 17 / 21 / 28 |
  | harness failure (n=9) | 2 / 3 / 5 | 12 / 21 / 25 | 47 / 60 / 60 |
  | direct (n=20, chunk calls) | 22 / 120 / 120 | — | — |

- **Predeclared hidden-memory ablation (registry v2-hiddenmem,
  registered before any rollout): 5/5 — H1 confirmed.** *(Corrected
  2026-07-29: seeds 1–2 quarantined by the Day-12 leakage audit for an
  HF-cache condition leak → **3/3 on clean rows**; direction unchanged,
  n reduced 5→3. See the Day-12 entry and `day8_mechanism.md` §4.)* The released
  TSM's carry-height ballistic-release rule causes the Object-S
  regression; the memory-free planner descends to seat before release:

  | seed | direct | harness + memory | hidden-memory | terminal eef z |
  |---|---|---|---|---|
  | 1 | ✓ | ✗ (release z=0.334, bounced out) | ~~✓ 22 turns~~ QUARANTINED | 0.214 |
  | 2 | ✓ | ✓ | ~~✓ 26 turns~~ QUARANTINED | 0.187 |
  | 3 | ✓ | ✗ | **✓** 15 turns | 0.285 |
  | 4 | ✗ | ✗ | **✓** 18 turns | 0.219 |
  | 5 | ✓ | ✓ | **✓** 19 turns | 0.180 |

  Seed 4 — solved by NEITHER frozen arm — fell to the memory-free
  harness in 18 turns. Scope: one implicated cell; not a general
  "memory hurts" claim (the with-memory harness produced all 8 rescues
  on the hard cells).
- Ablation integrity (methodology findings, quarantined + tripwired):
  attempt 1 — the planner HUNTED for its hidden memory via repo-wide
  find and read the stash back; attempt 2 — HF download cache leaked
  note filenames via .lock/.metadata. Final protocol: opaque
  out-of-repo tar + HF_HUB_OFFLINE + per-seed leak tripwire. All
  violations quarantined with INVALID notes; risk log updated.
- Interruption note: one queue stop mid-seed-4 was an external task
  stop, NOT an API limit (no rate_limit signature; planner mid-tool-call)
  — trap restored memory, pin clean, seeds 4–5 resumed on request.
- Gate: comparison table + intervals frozen from the ledger, one
  predeclared ablation executed and scored against its hypothesis,
  mechanism metrics extracted without new rollouts. ✅ Next (Day 9):
  cross-perturbation case studies — the 3 direct✓→harness✗ pairs +
  Object-S s3/s4 with-memory retry transcripts.

## Day 9 — matched case studies, mechanism correction & synthesis (2026-07-28)

- **MAJOR CORRECTION (adversarial re-triage of Object-S s3/s4 retries):
  the Day-8 carry-height mechanism is falsified; the real mechanism is
  reference-coordinate ANCHORING.** The ablation outcome (5/5 vs 2/5;
  restated 3/3 vs 1/3 on clean rows by the Day-12 audit — the evidence
  below rests on s3/s4, both clean) stands; the causal path is revised. Falsifying evidence + ground
  truth (rim bands from same-seed depth maps; basket half-width 0.075):

  | run | release xy @ z | true center | Δx | outcome |
  |---|---|---|---|---|
  | with-mem s3 | (0.072, 0.216) @ 0.331 | (−0.010, 0.246) | **+0.082** | bounce-out |
  | with-mem s4 | (0.076, 0.234) @ 0.332 | (−0.002, 0.247) | **+0.078** | roll-out |
  | hidden-mem s3 | (−0.005, 0.238) @ 0.28 | (−0.010, 0.246) | +0.005 | success |
  | hidden-mem s4 | (0.000, 0.245) @ 0.21 | (−0.002, 0.247) | +0.002 | success |
  | reference s0 | (0.086, 0.237) @ **0.367** | ≈own center | ~0 | success |

  The failing releases were OUTSIDE the basket footprint in x; z is
  exonerated (s0 succeeded from 0.367; hidden-mem s3 from carry height
  0.28 without descending). Both with-memory planners chose the
  +x-biased perception estimate BECAUSE it matched the cached s0
  absolute ("robust region median matches s0's (0.076, 0.231)",
  s4 run.log:53) over the accurate center_xyz their own tools returned;
  s1's s0-copied carry binding (Day-5 audit) is the same mechanism.
- **Audit-methodology finding**: this anchoring leak evades the Day-5
  coordinate-leakage grep — the stale absolute never enters an action;
  it biases estimator SELECTION. memory_audit.md §7 addendum; future
  leakage audits must check estimate-selection reasoning against tool
  outputs.
- Case study Goal-T s2 (direct 106 steps ✓ vs harness planner_timeout
  ✗): pi0's place-reflex measured in gripper telemetry (gap 0.0186 →
  0.0782@z0.997 drop → re-close 0.0011 → 0.0778@z1.226 drop); the
  harness lacks a grab-and-hold VLA mode — truncated pi0_pick = 0-lift
  no-ops, full pi0_pick = memorized place. Direct succeeds because
  nothing interrupts the policy's own pick-and-place.
- Direct-arm evidence limits (recorded honestly): the Day-3 driver
  persists NO trajectories (5 files/run, by design); predicates
  (`In`/`On`) have no gripper-open term and all 3 paired direct
  successes fired MID-CHUNK — "policy descends then progressively
  opens" is NOT measurable from our artifacts. Optional extension
  listed: deterministic instrumented replay (pins + seed mapping make
  it exact).
- Cross-perturbation synthesis (full: day9_case_studies.md §5):

  | cell | perturbation | direct | harness | pairing shows |
  |---|---|---|---|---|
  | Spatial-T | objects relocated | 0/5 | **5/5** | pure re-grounding rescue |
  | Goal-S | fixture swapped | 0/5 | **3/5** | re-grounding rescue; residual physical failures |
  | Goal-T | predicate flipped | 1/5 | 1/5 | perturbation inside the policy's motor program — no harness lever |
  | Object-S | object swapped | 4/5 | **2/5** | stale memory anchors mis-ground a competent policy |

  **The harness converts perception problems into wins and inherits or
  amplifies motor-program and memory-quality problems — gains and
  costs both live at the grounding seam.**
- Memory-quality defects for upstream (maintainer-gated path):
  reference absolutes act as confirmation anchors; `tall_item...` bias
  note is scene-inverted for this cell; "do not cache absolutes" must
  extend to estimator selection.
- Gate: all 3 regression pairs explained from raw artifacts, mechanism
  claims adversarially cross-checked (one revised in writing), synthesis
  frozen. ✅ Next (Day 10): MVP freeze + report skeleton.

## Day 10 — MVP freeze & reproduction report (2026-07-28, tag `day10-mvp-freeze`)

- **MVP frozen** (`track/registry/mvp_freeze.md`): core ledger 46 rows
  (40 scored + 6 infra, sha256 `88450c6b…4bed905`), ablation ledger 5
  rows (sha256 `9aa679f5…365a308`), 3.4 GB raw artifacts, RPent pin
  `6e4ba18` clean, 115 tests green. Nothing in the core may be re-run
  or re-scored; extensions go to new registry versions.
- **Reproduction report written** (`track/report/reproduction_report.md`):
  claim → setup → frozen protocol → results → mechanism → failure
  analysis → ablation + Day-9 correction → synthesis → deviations/
  limitations (7) → artifact index → verdict. Frozen headline tables:

  | cell | direct [Wilson 95%] | harness [Wilson 95%] | paper anchor |
  |---|---|---|---|
  | Spatial-T | 0/5 [0.00, 0.43] | **5/5** [0.57, 1.00] | 42→94 reproduced |
  | Goal-S | 0/5 [0.00, 0.43] | **3/5** [0.23, 0.88] | 42→87 gain |
  | Goal-T | 1/5 [0.04, 0.62] | 1/5 [0.04, 0.62] | 45→87 NOT reproduced at pin |
  | Object-S | 4/5 [0.38, 0.96] | **2/5** [0.12, 0.77] | 78→90 inverted |
  | **aggregate** | **5/20 [0.11, 0.47]** | **11/20 [0.34, 0.74]** | direction reproduced |

  Verdict — reproduced: aggregate direction, Spatial-T full amplitude,
  sparse-VLA division of labor, structural-prior memory behavior. Not
  reproduced at this pin: Goal-T gain (no grab-and-hold VLA mode vs
  pi0's place reflex). New findings: reference-coordinate anchoring
  (grep-invisible memory leak), agent memory-hunting + 2 leak channels
  with working countermeasure, release-x (not z) as the basket-placement
  failure variable, scene-inverted memory guidance.
- HANDOVER.md updated to Day-10 state (entry points for mentor).
- Gate (plan Day-10): ≥40 paired scored rollouts ✅ (40), mentor can
  trace claim→code→artifacts ✅ (mvp_freeze.md provenance chain),
  report delivered ✅.

## Day 11 — extension design & 8-cell matrix complete (2026-07-28→29, tag `day11-extension-matrix`)

- Extension question chosen from measured bottlenecks: **broader task
  coverage** (ablation = Day 12's charter, repeatability = Day 14's).
  Registry v3: +4 suites completing the 4×2 family/perturbation grid
  (4 redirection vs 4 swap) for Day-12. Hard budget pre-registered from
  measured costs (≤52 launches, ≤10 h, ≤12 harness/session window,
  ≤5 GB) — actuals landed inside every cap.
- Family pilots found 2 real infra issues before the queue: (1)
  LIBERO-Pro ships a valid-but-EMPTY init-state file for 10_task t2
  (5th missing-package-data bug) → cell moved t2→t3 pre-queue,
  recorded; (2) batch_runner never passed each cell's source manifest
  to the launchers (core queue had worked only because its cells
  matched the launchers' defaults) → fixed with tests (118 green).
- Queue ran in 2 planner windows 3 h apart (session-limit rule): 28 +
  8 cells, all raw-verified, **0 infra failures, 0 rate-limit hits**.
- **EXTENSION RESULTS (40 new scored rollouts; ledger 87 rows)**:

  | cell | direct | harness | reading |
  |---|---|---|---|
  | libero_object_task_t2 (Object-T) | **5/5** | **5/5** | both arms at ceiling — perturbation harmless here |
  | libero_spatial_swap_t2 (Spatial-S) | **5/5** | **5/5** | both at ceiling — unlike Spatial-T where direct was 0/5 |
  | libero_10_task_t3 (Long-T) | 0/5 | 0/5 | wall for both: direct all step_budget; harness 2× planner_timeout + 3× planner finished w/o predicate |
  | libero_10_swap_t2 (Long-S) | 0/5 | **2/5** | harness rescues 2 long-horizon seeds (s3, s4); rest turn_budget/finished |

- **COMBINED 8-CELL MATRIX (80 scored rollouts, 40 pairs)**:

  | | direct | harness |
  |---|---|---|
  | aggregate | **15/40 [0.24, 0.53]** | **23/40 [0.42, 0.71]** |

  Paired flips: 11 rescued / 3 regressed / 12 both-pass / 14 both-fail
  (net +8). Direction unchanged with doubled n; the regressed set is
  still confined to the two core cells (Object-S anchoring, Goal-T s2).
- Observations for Days 12–14: (a) perturbation difficulty is heavily
  task-instance-dependent (both new short-horizon cells are at ceiling
  for BOTH arms — they will carry no signal in the Day-12 ablation;
  the asymmetry test's discriminating cells are goal/object/10 swap vs
  goal/10 task); (b) LIBERO-10 stresses the pinned 1200 s planner
  timeout (2 rows) — a regime limitation to report, not retune;
  (c) direct-vs-harness gap on the extension is +2 cells only — the
  harness's value concentrates where perception breaks, replicating
  the core synthesis.
- Gate: every added family piloted in both conditions ✅, queue inside
  the hard budget ✅, all rows raw-verified ✅.

## Day 12 — memory-ablation machinery, and an integrity finding in already-published results (2026-07-29)

- **Design + PREDECLARATION frozen and committed BEFORE any rollout**
  (`day12_ablation_design.md`, gate commit `e6c253d`): paper Table-5
  zero-shot condition (hide Global Memory + all four TSM dirs + the HF
  cache), 4 cells chosen for **headroom** rather than family symmetry,
  seeds 1–5 with no seed-0 bootstrap.
  H1: Δ_S > Δ_T; H0: Δ_S ≤ Δ_T, Δ = with-memory − no-memory success rate
  pooled per side over 10 seed-paired rollouts. Disclosed up front: the T
  side starts at 10/10 vs the S side's 8/10, so the design is biased
  AGAINST H1; n=10/side cannot reach significance; the paper's asymmetry
  evidence is Goal-family while headroom forces our T side onto
  Spatial/Object.
- Machinery built TDD (branch `day12-memory-ablation`): `manifests --plan`
  CLI, `ablation_zeroshot_v4.json`, `leak_rules.py` + a checked-in
  206-name `memory_inventory.txt`, and `test_ablation_leakage.py`.
- **FINDING — 2 of the 5 ACCEPTED Day-8 ablation rows had the condition
  broken.** The new audit, run against real artifacts, split them cleanly:

  | run | hits on content that run HID | hits on non-hidden families | verdict |
  |---|---|---|---|
  | seed 1 `20260728T161724` | **35** | 0 | quarantined |
  | seed 2 `20260728T162346` | **36** | 30 | quarantined |
  | seed 3 `20260728T163128` | 0 | 10 | clean |
  | seed 4 `20260728T200048` | 0 | 9 | clean |
  | seed 5 `20260728T200704` | 0 | 21 | clean |

  Mechanism: the HF download cache exposed the Global Memory note
  filenames as `.lock`/`.metadata` entries and the planner listed them —
  verbatim from seed 1's stream, `=== memory dir ===\ncan_and_small_
  package_basket_placement.md.lock…`. Same failure mode as the already
  quarantined `attempt2_seed4`; seeds 1–2 predate the `.cache` stash fix,
  seeds 4–5 were re-run after it. **Root cause of the MISS:** the Day-8
  tripwire grepped for ONE hardcoded note name (absent from these two
  runs) across 3 of the 5 planner-visible artifact globs.
- **Consequence: the Day-8 result is restated 5/5 → 3/3 on clean rows**
  (vs with-memory 1/3 and direct 2/3 on those seeds). Direction unchanged
  and the strongest datapoint survives — seed 4, failed by both frozen
  arms, is clean — but the status drops from a 5-seed predeclared result
  to 3 concordant rows. The Day-9 anchoring mechanism is unaffected (its
  evidence is s3/s4, both clean). Rows quarantined with evidence retained
  in `artifacts/ablation/audit_quarantine_hfcache_seeds1_2/INVALID.md`;
  ablation ledger rebuilt 5 → 3 rows; corrected in all 8 citing documents.
- Second fix from the same audit: the rules are now **condition-scoped**
  per the run's own recorded `exp_version`, failing closed on unknown
  versions. Without this, v2-hiddenmem runs were mis-flagged for reading
  the three TSM families its family-scoped stash legitimately left in place.
- No rollout run; no GPU work. Queue is Day-12 steps 3–4, after review.
- **Attended pilot (1 cell / 1 seed) — the condition works, and the pilot
  earned its keep by finding a teardown bug no unit test could.**
  `libero_spatial_task` t2 s1 under v4: **success**, predicate fired at
  states.json entry 10 during an *analytic* `release`, 27 turns, **1 pi0
  call**, 9 analytic calls, 420 s. Raw-verified against `states.json`; leak
  audit clean under the full 199-pattern v4 rule set; per-seed hygiene a
  no-op (the planner created nothing under a hidden path). Ledger: 4 rows
  (3 clean v2-hiddenmem + this one). With memory this cell/seed also
  succeeded, so the seed contributes 0 to Δ_T — **one row is not a result**;
  19 cells remain.
- **INCIDENT: the queue exited leaving the released assets stashed.** The
  EXIT trap's `restore()` referenced `main()`'s locals, so it died on
  `stash_tar: unbound variable` before extracting. `pin_check` said "clean"
  the whole time — it is structurally blind here, because
  `RPent/resources/` is gitignored. Restored from the retained tar and
  verified bit-identical (619 files, content hash). Fixed: script-scope
  stash state, a self-verifying `restore()` that retains the stash and
  prints recovery steps on failure, a `--self-check` mode that exercises the
  real stash+trap path without a rollout, and 3 regression tests. Also
  removed a stale stash dir from /tmp — a readable copy of hidden memory is
  itself a leak channel for a *later* run, whose tripwire only knows its own
  stash path. 166 tests green (the v4 leakage audit is no longer skipped now
  that v4 rows exist).
- Lesson for the remaining windows: run `--self-check` before each one, and
  do not trust `pin_check` as evidence the condition was torn down.
