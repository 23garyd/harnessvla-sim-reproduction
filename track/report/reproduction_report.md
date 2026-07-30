# Reproducing HarnessVLA on LIBERO-Pro: a paired 40-rollout core matrix

**Track**: HarnessVLA-paper reproduction (arXiv:2607.08448, RPent framework)
**Author**: Bob Ding, with Claude Code (subagent-driven; all agent changes logged in `experiment_registry.md`)
**Period**: 2026-07-26 → 2026-07-28 (plan Days 1–10)
**Status**: Day-10 MVP frozen (`track/registry/mvp_freeze.md`)

## TL;DR

The paper's central claim — a frozen pi0.5 VLA becomes more useful under
LIBERO-Pro perturbations when wrapped in RPent's memory-guided agent
harness — **reproduces in direction** on a 4-cell × 5-seed paired core
matrix: direct 5/20 (25%) vs harness 11/20 (55%), Wilson 95%
[0.11, 0.47] vs [0.34, 0.74], with 9 seeds rescued and 3 regressed.
The gains are mechanism-specific (planner re-grounding on perception-type
perturbations: Spatial-T 0/5→5/5, Goal-S 0/5→3/5), and so are the
non-gains and the one regression: the harness has no lever when the
perturbation lives inside the policy's motor program (Goal-T 1/5→1/5),
and the released task memory *mis-grounds* an already-competent policy
on Object-S (4/5→2/5). A predeclared hidden-memory ablation on the
regression cell went 5/5 (restated **3/3 on clean rows** by the Day-12
leakage audit, which quarantined seeds 1–2 for an HF-cache condition
leak — direction unchanged, n reduced) — and adversarial triage then
revised our own
first mechanism story: the memory harms via **reference-coordinate
anchoring** of perception, a leakage mode that grep-based coordinate
audits cannot see. We regard the direction as reproduced, the
regression as a genuine, mechanistically-explained finding the paper's
own Object-S small-gap caveat foreshadows, and the anchoring leak +
agent memory-hunting behavior as novel methodological contributions.

## 1. Claim under test

HarnessVLA (RPent) wraps a frozen VLA in a planner-driven harness:
semantic re-grounding (SAM3 + depth back-projection), sparse targeted
VLA retries, analytic primitives, and a released task-specific memory.
Paper anchors on LIBERO-Pro (paper Table: direct→harness): Spatial-T
42→94, Goal-T 45→87, Goal-S 42→87, Object-S 78→90; aggregate 50.0→82.4.
Scope of this reproduction (deviation row 1): 4 anchor cells, task 2,
held-out seeds s1–s5, ≥40 paired scored rollouts,
**direction-not-magnitude** (paper-era planner unavailable; deviation
row 2 pins claude-opus-4-8/60 turns).

## 2. Setup (Day 1–2)

RTX A6000 ("asus"); RPent pinned `6e4ba18` (read-only, dirty-worktree
alarm); pi0.5 checkpoint sha-recorded; LIBERO-Pro assets + SAM3 (+ the
CLIP BPE vocab the wheel omits) fetched by pinned setup stages; venv
locked (`requirements.lock`). Planner billing: claude.ai subscription
with `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` stripped from every planner
subprocess (guard-tested). Four stack bugs found and fixed into
`setup.sh` are listed in `setup_notes.md`. 115-test suite green at
freeze.

## 3. Protocol (frozen Day 3 / Day 5)

- **Scoring**: success solely from the benchmark predicate
  (`libero_terminated`), cumulative (`success_once` semantics); planner
  self-reports are diagnostics. Every scored row is re-verified against
  raw `states.json` at queue time.
- **Direct arm (v1)**: minimal chunk-stream driver, 600-step benchmark
  horizon (+20 settle margin discovered as a real bug, Day 3).
- **Harness arm (v2)**: released one-shot regime as-is — 1200-step
  guide budget (env backstop 1220), 60 turns, planner-timeout 1200 s,
  wall cap 2400 s. Budget asymmetry vs direct = deviation row 3
  (mentor-approved).
- Seed 0 bootstraps memory and is never scored; no retuning on
  evaluation seeds; valid failures never retried. Infra failures retry
  at cap 2 with immutable queue records.
- Full deviation table: `track/registry/protocol_deviations.md` (4 rows).

## 4. Core result (Days 3–7)

| cell | direct k/n [Wilson 95%] | harness k/n [Wilson 95%] | paper anchor |
|---|---|---|---|
| Spatial-T | 0/5 [0.00, 0.43] | **5/5** [0.57, 1.00] | 42→94: reproduced, full amplitude |
| Goal-S | 0/5 [0.00, 0.43] | **3/5** [0.23, 0.88] | 42→87: clear gain |
| Goal-T | 1/5 [0.04, 0.62] | 1/5 [0.04, 0.62] | 45→87: NOT reproduced at this pin |
| Object-S | 4/5 [0.38, 0.96] | **2/5** [0.12, 0.77] | 78→90: inverted (regression) |
| **aggregate** | **5/20 [0.11, 0.47]** | **11/20 [0.34, 0.74]** | 50.0→82.4: direction reproduced |

Paired flips: 9 rescued / 3 regressed / 2 both-pass / 6 both-fail (net +6).

**Integrity note (Day 7)**: the first pass of this matrix showed
Object-S harness 0/5 — an artifact of the claude.ai session limit
killing the last 4 queue cells (planner never ran; rpent exits 0 on
planner exceptions). We built stream-level classification
(`planner_api_error` → infra, `planner_timeout` → budget), reclassified
5 rows from raw artifacts (originals preserved), and re-ran the 4 cells
under the frozen infra-retry protocol. Details: `day7_triage.md` §1.

## 5. Mechanism evidence (Days 4, 8)

- **Division of labor is visible in artifacts**: 10 of 11 harness
  successes fire the predicate during an *analytic* primitive (9
  release, 1 move_to); median **1 pi0 call per success** (max 2) vs
  direct's 120-chunk budget. Success/failure turn distributions are
  disjoint (17–28 vs 47–60).
- **Trace-level audit (Day 4)**: annotated 33-turn solve with live
  re-grounding, bounded pi0_pick, failed-release retry, empty-grasp
  recovery, staged transport; zero resets; no coordinate replay into
  actions (`track/traces/day4_object_swap_t2_s0_annotated.md`).
- **Memory audit (Day 5)**: released memory = structural prior with
  live re-grounding on the happy path (identical skeletons, re-derived
  bindings, leakage grep clean), with recorded caveats that Day 9
  sharpened into a finding (§7).

## 6. Failure analysis (Day 7)

Taxonomy over the 9 scored harness failures: release 3, transport 2,
empty_grasp 1, grounding 1 (+2 retry rows folded into the Object-S
case study). Localization is *not* the weak link — one grounding
failure in the whole matrix. Key chains:

- **Goal-T (no gain)** — one causal chain across all 4 failures:
  `pi0_pick` executes the memorized base-task pick-AND-place, so 4 of 5
  clean lifts ended with the policy's own place reflex dumping the
  bottle (measured as gripper-gap oscillation, e.g. 0.001→0.078 at
  z=1.226); truncating chunks to dodge the place phase yields zero-lift
  no-ops; the fallen horizontal bottle is nearly un-graspable with the
  available primitives; the flipped `In(bottle, bowl)` predicate needs
  an upright carry no seed restored. The harness lacks a
  **grab-and-hold** VLA mode; the raw policy succeeds on s2 precisely
  because nothing interrupts its own pick-and-place. Turn cap genuinely
  binding on only 2 of 9 failures.
- **Env-death sub-finding**: 2 runs lost their simulator mid-episode
  ("executing action in terminated episode" at counted steps 654/804
  despite backstop 1220) — step under-counting; documented, not
  changed mid-matrix.

## 7. The Object-S regression: ablation + corrected mechanism (Days 8–9)

**Predeclared ablation** (registry v2-hiddenmem, registered before any
rollout): hide the released memory + seed-0 reference on Object-S s1–s5,
all other pins identical.

| seed | direct | harness + memory | hidden-memory |
|---|---|---|---|
| 1 | ✓ | ✗ | ~~✓ 22 turns~~ QUARANTINED |
| 2 | ✓ | ✓ | ~~✓ 26 turns~~ QUARANTINED |
| 3 | ✓ | ✗ | **✓** 15 turns |
| 4 | ✗ | ✗ | **✓** 18 turns |
| 5 | ✓ | ✓ | **✓** 19 turns |

**Corrected 2026-07-29 (Day-12 leakage audit).** Seeds 1–2 were run
before the HF download cache was added to the stash, so the cache's
`.lock`/`.metadata` entries exposed the Global Memory note filenames and
the planner listed them — the same violation `attempt2_seed4` was
quarantined for. Both rows are quarantined with evidence retained
(`artifacts/ablation/audit_quarantine_hfcache_seeds1_2/INVALID.md`).
On the 3 clean rows the ablation reads **hidden-memory 3/3 vs
with-memory 1/3 vs direct 2/3**: the direction holds and the strongest
datapoint survives (seed 4, which both frozen arms fail), but this is no
longer a 5-seed predeclared result. The corrected mechanism below is
unaffected — its evidence rests on s3/s4, both clean.

**Outcome: 5/5 without memory vs 2/5 with** — including seed 4, which
neither frozen arm solves.

**Corrected mechanism (Day 9, adversarial re-triage)**: our first
explanation (the memory's carry-height release rule) was falsified —
the seed-0 reference succeeded from z=0.367 and a hidden-memory run
succeeded at carry height z=0.28. Depth-map ground truth shows the
failing releases were **+0.078–0.082 m off-center in x, outside the
basket footprint** (half-width 0.075), while all successful releases
were within 0.005 m. Cause: **reference-coordinate anchoring** — both
with-memory planners selected the +x-biased perception estimate *because
it matched the cached seed-0 absolute* ("robust region median matches
s0's (0.076, 0.231)"), discarding accurate readings their own tools
returned. The stale coordinate never appears in an action, so
grep-based leakage audits pass; it captures the *interpretation* of
fresh measurements instead. Full evidence: `day9_case_studies.md`.

**Ablation-integrity findings** (methodology): two attempts were
invalidated before the clean run — (1) the planner, finding its memory
missing, ran repo-wide `find` hunts and **read the stash back**;
(2) after moving to an opaque out-of-repo tar, HF download-cache
`.lock`/`.metadata` **filenames** still leaked strategy-bearing note
titles. Naive resource-hiding is not a valid ablation technique for
shell-capable agents; the surviving protocol (opaque tar + offline flag
+ per-seed leak tripwire) held 5/5 clean.

## 8. Cross-perturbation synthesis (Day 9)

The harness converts **perception problems into wins** (relocated
objects, swapped fixtures: +8 cells) and **inherits or amplifies
motor-program and memory-quality problems** (flipped-goal cell: no
lever; object-swap cell: stale anchors mis-ground a competent policy).
Both the gains and the costs live at the grounding seam. This sharpens
rather than contradicts the paper: its Object-S anchor already shows
the smallest gain (78→90), and our regression is a pin-and-seed-level
magnification of that same weakness.

## 9. Deviations & limitations

1. Scale: 4 cells × 5 seeds vs the paper's 800 rollouts/condition
   (deviation 1); per-cell intervals are wide — per-cell claims rest on
   paired flips + mechanism triage, not intervals.
2. Planner drift: claude-opus-4-8/60-turn pin vs paper-era planners
   (deviation 2); Goal-T's non-reproduction may be pin-sensitive
   (2 of 9 failures were plausibly convergent at the cap).
3. Budget asymmetry direct 600 vs harness 1200 steps (deviation 3,
   released regime kept as-is); wall-clock is not comparable across
   arms (harness includes ~3–4 min server boot).
4. Direct-arm trajectories are not recorded (by design); placement
   behavior of the raw policy is inferred only from terminal frames +
   predicate semantics. Optional: deterministic instrumented replay.
5. Env step-accounting mismatch can kill episodes early under the
   harness backstop (2 occurrences, documented).
6. Ablation scope: one cell, chosen because triage implicated it — not
   a general "memory hurts" claim (with-memory harness produced all 8
   rescues on the hard cells).
7. Operational: subscription session limits can silently kill planner
   runs; our classifier now catches this as infra (≤15 harness
   cells/session window rule).

## 10. Artifact index

Frozen state + provenance chain: `track/registry/mvp_freeze.md`.
Ledgers: `artifacts/ledger.csv` (46 rows) + `artifacts/ablation/ledger.csv`
(5 rows), sha256 in the freeze note. Per-day trace with full result
tables: `track/registry/progress_log.md`. Repo:
github.com/nuPylot/harnessvla-sim, tags `day2-install-smoke` →
`day10-mvp-freeze`.

## 11. Verdict

- **Reproduced**: the direction of the aggregate claim (25%→55%,
  barely-overlapping Wilson intervals); the full-amplitude Spatial-T
  rescue; the sparse-VLA division of labor at the artifact level; the
  structural-prior-with-live-re-grounding memory behavior on the happy
  path.
- **Not reproduced at this pin**: the Goal-T gain (mechanism: no
  grab-and-hold VLA mode vs pi0's place reflex; possibly turn-cap and
  planner-pin sensitive).
- **New findings**: (a) Object-S regression with a measured mechanism —
  reference-coordinate anchoring of perception, invisible to grep
  audits; (b) shell-capable planner agents actively hunt for hidden
  resources, with two concrete leak channels (stash discovery,
  HF-cache filenames) and a working countermeasure; (c) release-x, not
  release-z, is the failure variable on basket placement; (d) memory
  notes contain scene-inverted guidance (bias-direction defect).
  Candidates for upstream issue reports via the maintainer-gated path.
