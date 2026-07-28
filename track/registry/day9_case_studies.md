# Day-9: matched case studies & cross-perturbation synthesis

Scope: the 3 direct✓→harness✗ pairs (Goal-T s2; Object-S s1, s3), the
Object-S s3/s4 with-memory retry transcripts (deferred from Day 7), and
the cross-perturbation synthesis. Method: adversarial re-examination of
the Day-8 mechanism claim against raw artifacts (states.json stream
telemetry, run.log, depth-map ground truth, released reference files).
One major correction is issued (§2). No new rollouts; no retuning.

## 1. Headline: the Day-8 mechanism claim is CORRECTED

Day-8 concluded (predeclared H1) that the released memory's
carry-height release rule ("release at carry_z≈0.30; do not descend")
causes the Object-S regression. The **ablation outcome stands**
(hidden-memory 5/5 vs with-memory 2/5) but the **causal path was
wrong**. Three datapoints falsify the z-mechanism:

1. The seed-0 reference itself succeeded releasing at **z=0.367** —
   higher than the failing releases (0.331/0.332/0.334).
2. Hidden-memory s3 succeeded releasing at **z=0.28 carry height,
   without descending** — obeying the rule as written.
3. Release-position ground truth (rim band from same-seed depth maps):

| run | release xy @ z | true basket center | Δx | outcome |
|---|---|---|---|---|
| with-mem s3 | (0.072, 0.216) @ 0.331 | (−0.010, 0.246) | **+0.082** | bounce-out |
| with-mem s4 | (0.076, 0.234) @ 0.332 | (−0.002, 0.247) | **+0.078** | roll-out |
| hidden-mem s3 | (−0.005, 0.238) @ 0.28 | (−0.010, 0.246) | +0.005 | success |
| hidden-mem s4 | (0.000, 0.245) @ 0.21 | (−0.002, 0.247) | +0.002 | success |
| reference s0 | (0.086, 0.237) @ 0.367 | ≈(0.076, ·) s0 scene | ~0 | success |

Basket half-width ≈ 0.075 m: the with-memory releases were **outside
the basket footprint in x**. The 0.05 m z difference is second-order.

**Corrected mechanism — reference-coordinate anchoring.** The seed-0
recipe ships an absolute basket coordinate (0.076, 0.231) valid only
for seed 0's scene. In seeds 3/4 the basket sits at x≈−0.01/0.00, and
the oblique agentview + SAM3 "woven basket" centroid (which lands on
the front outer wall) produce a +x-biased estimate alongside an
accurate region `center_xyz`. Both with-memory planners **selected the
biased estimate because it matched the cached s0 absolute**:

- s4, run.log:53: "basket interior center ~(0.07, 0.23) (robust region
  median matches s0's (0.076, 0.231))" — while its own `center_xyz`
  read +0.005.
- s3 discarded its own region readouts of x=−0.011/−0.070 in favor of
  outlier pixels near +0.06, matching the reference.
- s1 (Day-5 audit, now unified): its carry binding was "chosen matching
  the seed-0 winning release pose" — same anchor, −y flavor.

The hidden-memory planners, with no reference to anchor on, read the
region center → x≈0.00 → 5/5. **The memory hurts this cell not through
its z rule but by turning a released reference trajectory into a
confirmation anchor for ambiguous perception.**

**Audit-methodology consequence**: this leak evades the Day-5
coordinate-leakage grep — the stale absolute never appears in an
executed action; it biases which fresh measurement gets believed.
"Structural prior with live re-grounding" can silently degrade into
"reference-confirmed mis-grounding" exactly when perception is
ambiguous. Addendum added to `memory_audit.md`.

## 2. Case study A — Object-S bounce-outs (with-memory s1, s3, s4)

Shared chain (all three): correct grasp via bounded pi0_pick (1 call)
→ carry to an s0-anchored basket estimate → `release` lands on/outside
the +x rim (s1: +y overshoot) → bottle bounces/rolls out horizontal →
re-grasp of a low horizontal cylinder is the hardest state in the
primitive vocabulary → 37–44 turns of recovery → turn_budget.

Recovery quality varied (evidence the planner, not the plan, differs):
s1 solved the horizontal re-grasp (3 z-calibration cycles) and was one
placement short at cap; s3 achieved one lift then lost it to a
transport slip (grip 0.0006 mid-`move_to`), ending on a well-founded
cap grasp; s4 never re-grasped — its `pi0_pick` #2 tipped and displaced
the basket (the exact hazard `tall_item...` line 33 warns about, turn
28) and it thrashed the same pitched-straddle close (3× grip ≈0.0015)
without measuring the fingertip offset.

Additional memory-quality defects surfaced: the prescribed +0.03 m y
compensation was dropped by both s3/s4; the `tall_item...` line 53
centroid-bias note is **scene-inverted** for this cell (says −x bias;
actual bias here is +x — following it worsens the error).

## 3. Case study B — Goal-T s2: direct ✓ (106 steps) vs harness ✗ (planner_timeout)

- Direct: predicate fired on the **1st action of chunk 22** (106 steps,
  31.6 s) — the policy was mid-stream; no discrete release act exists
  in its interface.
- Harness: the gripper-gap telemetry shows pi0's place-reflex
  numerically: gap 0.0186 → **0.0782 at z=0.9966** (drop #1) → re-close
  0.0084/0.0011 → **0.0778 at z=1.2260** (drop #2 at height). 8 grasp
  attempts total, 1 held briefly; 33 turns re-acquiring; SDK
  planner-timeout at turn 58.
- Architectural reading: the harness needs a **grab-and-hold** VLA mode
  it does not have — `pi0_pick` truncated early yields zero-lift
  no-ops, run long it executes the memorized base-task place. The raw
  policy succeeds *because* nothing interrupts its pick-and-place; the
  harness fails *because* its grasp primitive contains a place it
  cannot use and cannot fully suppress. This is the perturbation the
  paper's Goal-T anchor (45→87) claims to fix; our planner pin does not
  reproduce that fix at 60 turns.

## 4. Case study C — evidence limits on the direct side (recorded honestly)

The direct driver persists **no trajectories** (by Day-3 design: 5
files/run — meta, row, 2 frames, boot log). Therefore "raw pi0.5
descends and progressively opens at placement" is **not measurable**
from our artifacts; additionally the benchmark predicates (`In`/`On`)
contain **no gripper-open term** and all 3 paired direct successes
fired **mid-chunk** — success while still gripped is possible. What is
proven: the policy brought the object into container contact/
containment (predicate semantics) with the arm low over the container
at predicate time (terminal frames, qualitative); the discrete-release
comparison stands on the harness-side numbers alone. Optional
extension (not scheduled): deterministic instrumented replay of the 3
direct runs (pins + seed mapping make this exact) to recover eef-z /
gripper profiles.

## 5. Cross-perturbation synthesis

| cell | perturbation | direct | harness | what the pairing shows |
|---|---|---|---|---|
| Spatial-T | objects relocated (init-state) | 0/5 | **5/5** | pure re-grounding deficit: policy cannot find relocated targets; planner re-perceives → full rescue; median success 24 turns, 1 pi0 call |
| Goal-S | goal fixture swapped/relocated | 0/5 | **3/5** | re-grounding rescue where grasp survives; residual failures are physical (glass slip ×2) and one perception-bounding error |
| Goal-T | goal predicate flipped vs memorized behavior | 1/5 | 1/5 | the perturbation lives INSIDE the policy's motor program (place reflex); planner cannot rescue what its grasp primitive re-enacts; no grab-and-hold mode |
| Object-S | target object identity swapped | 4/5 | **2/5** | policy already competent; memory's reference coordinates anchor perception off-target → regression |

Synthesis: **the harness converts perception problems into wins and
inherits (or amplifies) motor-program and memory-quality problems.**
Where the frozen policy's failure is "can't find / can't parse the
scene" (Spatial-T, Goal-S), planner re-grounding is worth +8 cells.
Where the failure mode is the policy's own trained behavior (Goal-T)
the harness has no lever, and where the policy needed no help
(Object-S) the released memory's stale anchors actively mis-ground it.
This sharpens the paper's claim: the memory-guided agent's gains are
real and mechanism-specific, and its costs are equally
mechanism-specific — both live at the perception/grounding seam.

## 6. Dispositions

- Day-8 H1 status: outcome CONFIRMED (5/5 vs 2/5), mechanism REVISED
  (coordinate anchoring, not carry-height). Correction noted in
  `day8_mechanism.md` §4 and the registry ablation row.
- `memory_audit.md`: addendum §7 (anchoring leak evades the grep audit).
- Candidate upstream memory issues (maintainer-gated path): (a) scene
  absolutes in reference recipes act as confirmation anchors — consider
  shipping references with coordinates masked or flagged per-scene; (b)
  `tall_item...` line 53 bias note is scene-inverted for low-table
  Object-S scenes; (c) line 47's "do not cache absolutes" needs to
  extend to estimator selection, not just action reuse.
- To the report's limitations: direct-arm trajectory non-observability;
  Goal-T turn-cap interaction; single-cell scope of the ablation.
