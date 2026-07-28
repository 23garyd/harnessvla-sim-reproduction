# Day-7 triage: corrected core matrix + failure taxonomy

Scope: forensic triage of the Day-6 paired core matrix from raw artifacts
(states.json, run.log, transcript_*.json, stream jsonl, env_server.log),
per the internship plan's Day-7 charter. No retuning on evaluation seeds:
every scored row below is either the original Day-6 run or a
protocol-sanctioned infra retry; all findings route to
limitations/deviation text and predeclared-ablation candidates only.

## 1. The Object-S "collapse" was a planner-availability artifact

The Day-6 evening table showed object_swap harness 0/5 against direct 4/5 —
an apparent inversion on the strong cell. Raw-stream forensics
(`claude_*.txt.stream.jsonl`) showed the last 4 harness cells of the
19-cell queue hit the claude.ai subscription **session limit** ("You've
hit your session limit · resets 3:10am (America/Los_Angeles)"):

- s3, s4, s5: rate-limited **before turn 1** — 0 env steps, 0 VLA calls,
  ~160 s wall (server boot only). The policy was never exercised.
- s2: rate-limited **mid-run at turn 44** (after 340 steps, 5 pi0 calls).
- s1: clean — a genuine 60-turn budget exhaustion (the only scored Day-6
  failure in the cell).

rpent exits 0 on planner exceptions, so the launcher's `rc != 0` infra
check never fired and all four rows were misclassified
`valid_failure/planner_finished_without_predicate`. Fixes (TDD, suite
101 → 107 green):

- `harness_lib` now scans the raw planner stream: a synthetic
  `AssistantMessage` with an `error` field (e.g. `rate_limit`) →
  `infra_failure/planner_api_error` (commit 2c49ac0); a `{"type":
  "timeout"}` record (SDK `planner_timeout_s` expiry) →
  `budget_exhausted/planner_timeout`, which stays scored because
  1200 s is a pinned v2 regime bound (commit c9e00e5). Bare
  `{"type": "error"}` records (max-turns) are deliberately not matched.
- The 4 object_swap rows were regenerated from raw artifacts (originals
  preserved as `result_row.json.orig`) and the cells re-run under the
  frozen infra-retry protocol (attempt 2 of 2, batch runner, raw-verified,
  zero rate-limit signatures). goal_task s2's row was likewise
  regenerated (`planner_timeout`; success flag unchanged).
- Risk log updated; scheduling rule: ≤ ~15 harness cells per session
  window, split larger queues.

Retry results: s2 SUCCESS (21 turns, 411 s), s5 SUCCESS (20 turns,
396 s), s3 and s4 genuine turn-budget failures — consistent with the
pre-freeze pilots (2/3) under identical pins.

## 2. Corrected core matrix (40 scored rollouts, ledger 46 rows = 40 + 6 infra)

| cell | direct | harness | paper anchor |
|---|---|---|---|
| libero_spatial_task_t2 (Spatial-T) | 0/5 | **5/5** | 42→94 — full amplitude |
| libero_goal_swap_t2 (Goal-S) | 0/5 | **3/5** | 42→87 — clear gain |
| libero_goal_task_t2 (Goal-T) | 1/5 | 1/5 | 45→87 — NO gain (see §4) |
| libero_object_swap_t2 (Object-S) | 4/5 | **2/5** | 78→90 — regression, real but half the artifact's size (see §5) |
| **aggregate** | **5/20 (25%)** | **11/20 (55%)** | 50.0→82.4 — direction reproduced |

Paired flips: 9 direct✗→harness✓ (all 5 Spatial-T; Goal-S s1,s2,s5;
Goal-T s1), 3 direct✓→harness✗ (Goal-T s2; Object-S s1,s3), 2 both-pass
(Object-S s2,s5), 6 both-fail. Net +6.

## 3. Failure taxonomy (9 scored harness failures)

Labels: grounding | staging | empty_grasp | transport | release |
timeout_planning | timeout_execution | false_success. Primary label =
the causally decisive error; terminal label = what the budget row says.

| cell/seed | primary | chain | terminal | forward progress at cut? |
|---|---|---|---|---|
| Goal-T s2 | empty_grasp | pi0 place-reflex drop → 33-turn re-grasp loop (7/8 grasps empty) | planner_timeout (1200 s, turn 58) | no — same loop, needed strategy change |
| Goal-T s3 | transport | neck-grip slip mid-carry → wedged bottle → env death | turn_budget | no — env dead since turn 54 |
| Goal-T s4 | release | tilted release toppled out of bowl → re-grasp loop → env death | turn_budget | no — env dead since turn 56; was 1 primitive from success at turn 22 |
| Goal-T s5 | release | horizontal bottle draped bowl rim (In-predicate needs upright) | turn_budget | **yes** — holding bottle 7 cm from bowl, ~4–6 turns short |
| Goal-S s3 | transport | body-grasp on smooth glass slipped ×2 on 0.26 m lift → unrecoverable wedge | valid_failure (finish at 47/60) | no — honest, well-founded stop |
| Goal-S s4 | grounding | unbounded z_min region query → wrong (tilted-slat) surface → mis-sited release → wrist-yaw re-grasp loop | turn_budget | **yes** — verified grasp over the true site, 2–4 turns short |
| Object-S s1 | release | ballistic release at carry z=0.334 bounced bottle out → 37-turn horizontal re-grasp (solved!) → rim-straddle release #2 | turn_budget | partial — one placement short, but in a memory-flagged unrecoverable state |
| Object-S s3 (retry) | turn_budget row; transcript triage deferred to Day-9 case studies | — | turn_budget | — |
| Object-S s4 (retry) | turn_budget row; transcript triage deferred to Day-9 case studies | — | turn_budget | — |

Counts by primary label (7 triaged): release 3, transport 2,
empty_grasp 1, grounding 1. Zero grounding failures outside Goal-S s4 —
SAM3 + back_project localization agreed with references in every run;
the paper's "semantic re-grounding" mechanism is not the weak link.
The weak links are (a) release/place geometry executed analytically and
(b) grasp retention/re-acquisition after a drop.

## 4. Goal-T: one causal chain, not four failures

All four failures are the same chain at different stopping points
(task: "put the wine bottle in the bowl", flipped predicate
In(bottle, akita_black_bowl_1)):

1. **pi0_pick executes the memorized base-task pick-AND-place.** 16
   pi0_pick calls across the cell produced 5 real lifts; in 4 of 5 the
   policy's trained place behavior re-opened the gripper and dumped the
   bottle ~15–25 cm from the bowl — exactly the perturbation's intended
   trap (the seed-0 reference's `expected_baseline_behavior` predicts
   this verbatim for the raw policy; the harness inherits it through its
   grasp primitive). Planners' mitigation (truncating max_chunks to
   8–13) produced peak_lift≈0 no-ops instead. **There is no reliable
   grab-and-hold mode of pi0_pick in this cell.**
2. **A dropped bottle is horizontal, low, and reach-limited** (wedged
   against cabinet/rack/handles): 9 scripted set_gripper closes across
   the cell closed on air; descents stalled 3–5 cm short at OSC reach
   limits. This loop is the top turn sink (33/33/31 turns in s2/s3/s4).
3. **The predicate needs an upright bottle**; both releases that reached
   the bowl failed on geometry (toppled out; draped across rim). No seed
   ever restored an upright carry after a drop.

Turn-budget verdict: the earlier "cap bound on 3/5" read was too
generous. Genuinely convergent at the cap: s5 only (plus Goal-S s4).
s2/s3/s4 needed a strategy change or a live env, not more turns. Why
seed 1 succeeded: its single pi0_pick held (final_gripper 0.0149 — the
only non-reopening lift in the cell) and it released upright — i.e. the
cell's harness success is gated on pi0's stochastic place-reflex, not on
planning quality.

**Env-death sub-finding (s3, s4):** both runs killed their env mid-run
with `ValueError: executing action in terminated episode`
(robosuite base.py:379 → worker death → broken pipe on every later
call) at harness-counted steps 654/804 despite `--max-episode-steps
1220` — the states.json `steps_used` sum under-counts actual sim steps,
so the robosuite horizon expires before the harness budget nominally
does. Each planner then burned 5–7 turns probing a dead env. The
released memory itself warns about this mode and recommends 5000+ for
long sessions; our v2 freeze pinned 1220 (deviation row 3 territory).
Recorded as a limitation + Day-8 note; NOT changed mid-matrix.

## 5. Object-S: the released memory's release rule is the regression mechanism

Final cell result: direct 4/5 vs harness 2/5 — a real regression, half
the size of the artifact, and now mechanistically explained (s1 fully
triaged; s3/s4 retries deferred to Day-9 case studies):

- The harness is architecturally forbidden from letting pi0 place
  (released `feedback_no_pi0_end_to_end.md`: "Pi0 may ONLY be used for
  the gripper grasp"), so placement is an **analytic ballistic release
  at carry height** — prescribed by the released MEMORY.md calibration
  ("Release at the carry height; do not descend inside the basket
  footprint", carry_z=0.30) and matching the seed-0 winning recipe.
- On s1 that ~0.20 m free-fall of a top-heavy bottle bounced it off the
  rim and out (post-release localization: 10 cm past basket center,
  horizontal, rolling). The planner then *solved* the horizontal
  re-grasp the Day-4 pilot couldn't (3 z-calibration cycles, caught the
  belly at z=0.031) and delivered the bottle back over the basket — but
  spent 37/60 turns doing it and mis-executed release #2 (rim straddle).
- Direct pi0.5 on the same seed lowers into the cavity and opens
  progressively as one learned pick-and-place: success in 143 steps.

**Reusable finding:** the released TSM's carry_z release rule for tall
bottles is not seed-robust, and it converts clean grasps into
unrecoverable episodes precisely on the cell where the frozen policy is
already strong. This sharpens the Day-5 memory-audit caveat (the
"descend below rim before release" lesson exists only in a stray Day-4
recipe, never in the released notes) and is the candidate mechanism for
the paper's own small Object-S gap (78→90 vs 42→94 elsewhere).
Candidate predeclared ablation (Day 12): hidden-memory on Object-S
(does removing the carry_z rule help?). Candidate upstream issue:
propose the below-rim descent note via the maintainer-gated memory
contribution path documented upstream.

## 6. Goal-S failures (both-fail pairs, cell 3/5)

- s3 (`transport`): correct grounding, two verified grasps; a 0.036–0.039
  body grasp on smooth glass slipped both times during the 0.26 m
  vertical lift; the bottle wedged under the rack slats with the
  fingertips walled 0.05 m above it. The planner exhausted all three
  access primitives, quantified the clearance deficit, and finished
  honestly with 13 turns left. The three successes all avoided this:
  s1/s2 clamped the thin neck (form closure), s5 carried horizontally.
- s4 (`grounding→release→turn_budget`): the only localization failure in
  the matrix — an unbounded `z_min` region back_project returned the
  tilted front slats (z≈1.17) instead of the true predicate surface
  (z=1.127); the resulting mis-sited release cost 28 recovery turns
  (15 of them on a wrist-yaw misdiagnosis); at turn 60 it had a verified
  grasp positioned over the correct site, 2–4 turns from a release.

## 7. Upstream RPent update review (2026-07-28, `6e4ba18` → `c01b9cf`)

User-flagged repo update reviewed by fetch+diff (worktree untouched, pin
intact). Four commits: two operational fixes (parent-watch made opt-in —
the exact Day-2 stdin/EOF bug we worked around; fail-fast when a server
crashes before ready), two docs commits. `resources/` (released memory)
unchanged; `pro_hybrid_guide.md` changed only in CLI examples (`--env
libero`, model example → claude-opus-4-8 — both already our v2 pins).
**Nothing affects scoring, prompts, memory, or the regime → stay pinned
at `6e4ba18` for the core matrix.** Pin bump to `c01b9cf` is a recorded
candidate for the extension matrix only (queue robustness). Neither the
step-accounting env death (§4) nor the carry_z release rule (§5) is
fixed upstream — both are candidate upstream issue reports.

## 8. Disposition

- Matrix frozen and corrected; Day-10 core requirement (≥40 paired
  scored rollouts) met with a clean ledger (40 scored + 6 documented
  infra rows).
- To Day 8 (compare.py): use validity != infra_failure rows only; report
  Wilson intervals; note harness wall_seconds includes ~3–4 min server
  boot; terminal_reason vocabulary now includes planner_timeout.
- To Day 9 (case studies): the 3 direct✓→harness✗ pairs (Goal-T s2,
  Object-S s1, Object-S s3) + Object-S s3/s4 retry transcripts.
- To the report's limitations: 60-turn cap (2 of 9 failures plausibly
  convergent at cut), env step-accounting mismatch, planner-availability
  operational risk, released-memory release-rule brittleness.
