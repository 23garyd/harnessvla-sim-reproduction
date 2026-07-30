# Day-5 memory audit: released TSM as a structural prior on new seeds

Scope: does the released Task-Specific Memory (`resources/libero/memory/MEMORY.md`,
`tall_item_first_basket_placement.md`, `feedback_staged_held_object_transport.md`)
act as a structural prior with live re-grounding, or does it leak stale
coordinates, when applied to unseen seeds of `object_swap_t2`?

**Sources used**: the released reference dir
`RPent/resources/libero/results_object_pert/{object_swap_t2_s0.json,recipe_object_swap_t2_s0.jsonl}`
was present on disk throughout (not stashed) and read directly — the
`planner_strays`/HF-cache fallbacks were not needed for the reference itself.
The `planner_strays` copy at `artifacts/harness/day4_object_swap_t2_s0_r2/` turned
out to be load-bearing for a different reason: it is a *separate* Day-4-evening
rerun of s0 (own recipe + json, different literals) that hit a release-height
failure and self-corrected in-episode — used in section 5. New-seed evidence:
`artifacts/harness/day4_eve_object_swap_t2_{s2,s3,s1}/` (`run.log`,
`transcript_*.json`, `recipe_*.jsonl`, `planner_strays/.../*.json`).

## 1. Skeleton alignment

| | reset | pre-grasp move_to | pi0_pick | carry move_to | release | after release |
|---|---|---|---|---|---|---|
| released s0 | yes | 1 | 1 | 1 | 1 | — (clean) |
| s2 (success) | implicit | 1 | 1 | 1 (+1 refine back_project, no extra move) | 1 | — (clean, 4-line recipe) |
| s3 (success) | implicit | 1 | 1 | 1 | 1 | — (clean, 4-line recipe) |
| s1 (failure) | implicit | 1 | 1 (+`set_gripper` firm) | 1 | 1 | **diverges**: re-`move_to`, re-`pi0_pick`, 3x recovery `move_to`, re-`pi0_pick`, `move_pose`×4 (17 lines total) |

**Verdict**: all four runs share the identical core primitive skeleton —
*approach → pi0_pick → carry → release* — with only cosmetic variation
(s1 inserts a `set_gripper` firming step, s2 inserts one mid-carry
`back_project` refinement, no run repeats `reset`). s1's recipe is 3-4x
longer only because the skeleton's tail (`release`) failed and the agent
improvised an unscripted recovery cascade (`move_pose` appears nowhere in the
released memory or in s2/s3) — the divergence starts strictly *after* the
shared skeleton, not within it. This supports "same structural skeleton,
different spatial bindings," not "memorized trajectory."

## 2. Spatial re-binding evidence

| | pre-grasp xyz | delta vs released [-0.185,-0.088] | carry/basket xyz | delta vs released [0.076,0.231] | binding source |
|---|---|---|---|---|---|
| released s0 | [-0.185,-0.088,0.20] | — | [0.076,0.231,0.35] | — | agentview back_project (body px) + SAM3 basket, score 0.80 |
| s2 | [-0.183,-0.098,0.2] | (+0.002,-0.010) | refined interior center **[-0.015,0.275]**→ waypoint [0,0.29,0.33] | (-0.091,+0.044) | `segment` "the woven basket" (run.log:67, score 0.789) then 4x `back_project` on rim corners (run.log:79-95) → footprint x∈[-0.08,0.05], y∈[0.20,0.35] |
| s3 | [-0.18,-0.09,0.2] | (+0.005,-0.002) | [0.01,0.235,0.3] | (-0.066,+0.004) | 3x `back_project` on bottle body (run.log:60-65) + 3x on basket opening (run.log:79-84) → interior center ~(0.0,0.235) |
| s1 | [-0.1835,-0.0796,0.21] | (+0.0015,+0.0084) | [0.085,0.242,0.35] | (+0.009,+0.011) | `segment` "salad dressing"/"basket" (run.log:54-56, SAM3 0.781) for the pre-grasp only — **carry pose was not independently re-grounded this seed**, chosen "matching the seed-0 winning release pose" per its own strategy_notes |

s2 is the star case: it re-grounds the basket from scratch every seed and
finds it has genuinely moved to interior center ≈(-0.015, 0.275) — a ~9 cm x
/ ~4 cm y shift from the released carry point — and adjusts, landing inside
(`held_bottle_xy_at_release: [0.02, 0.30]`, confirmed by a post-hoc
back_project before release). s3 similarly re-grounds and finds a smaller
but real shift. **s1 is the counter-example**: its pre-grasp binding is
correctly re-grounded (SAM3 identity match), but its carry binding is copied
near the released literal rather than re-derived from this seed's own
basket segmentation — and this seed's actual basket center (`basket_center_
world_xyz` in its final_state: [0.086, 0.189, 0.03]) is ~5 cm in -y from the
copied carry target, so the "same as s0" release lands over the back rim.

## 3. Coordinate-leakage grep

Grepped every pilot's `transcript_*.json` + `recipe_*.jsonl` for the four
released literals `-0.185`, `0.231`, `-0.107`, `-0.237`:

- **s2**: 0 hits (all four literals). Clean.
- **s3**: 0 hits (all four literals). Clean.
- **s1**: 0 hits for `0.231`, `-0.107`, `-0.237`. **1 hit for `-0.185`**, but
  only as prose in the reasoning turn, not inside any executed tool call:
  > "Salad dressing found at score 0.781, world (-0.1835, -0.0796) — this
  > matches the seed-0 reference's salad_dressing position (-0.185, -0.088)
  > almost exactly, confirming correct identity."

  This is a citation used to *verify* the fresh SAM3/back_project result
  against the reference, not a copy-paste into an action — the actual
  `move_to` a few lines later uses the freshly measured -0.1835,-0.0796, not
  -0.185,-0.088. As predicted, raw released coordinates do not leak into
  executed actions in any of the three pilots; the one textual match is
  reasoning-visible cross-checking, and it is confined to the pre-grasp
  literal, never the carry/basket literal that mattered for the failure.

## 4. Memory-note usage

| | MEMORY.md | tall_item_first_basket_placement.md | feedback_staged_held_object_transport.md | visible behavior tied to a note |
|---|---|---|---|---|
| s2 | read (13851B) | read (9336B) | read (2367B) | quotes the plan verbatim: *"grasp with a small pi0 chunk budget, verify, carry to basket in split waypoints at carry_z, release"* — then executes exactly that (verified_hold check, split carry+refine, release) |
| s3 | read (13851B) | read (9336B) | read (2367B) | same grasp→verify→carry→release staging; `pick_result.verified_hold: true` before committing to the carry move, matching the "staged held-object transport" pattern |
| s1 | read (13851B) | read (9336B) | read (2367B) | same grasp-verification pattern followed (gripper-opening check against "seed-0's held-bottle signature") — but the notes contain no rim-clearance guidance, and none was applied (see §5) |

All three also read the released `object_swap_t2_s0.json` (and s2 additionally
read the released recipe `.jsonl`) as a citation reference, separate from the
three memory notes.

## 5. Failure analysis (s1)

Reconstructed sequence (run.log line numbers):
1. `segment` finds salad_dressing (SAM3 0.781) and basket (run.log:54-56) — identity correct, matches seed-0.
2. `move_to` pre-grasp [-0.1835,-0.0796,0.21] (run.log:61); `pi0_pick` → clean grasp, gripper 0.037 (run.log:66).
3. `set_gripper` firms grip; `move_to` carry [0.085,0.242,0.35] (run.log:81) — copied near the released carry pose rather than re-grounded to this seed's basket (see §2).
4. `release` at high z=0.35 (run.log:86) → predicate does not fire. Re-segmentation locates the bottle at (0.213,0.268,z=0.034), ~13cm from basket center — it rolled off the +x/back rim.
5. Recovery cascade (unscripted, not in memory or released recipe): re-`move_to` over the fallen bottle stalls near the IK reach edge; re-`pi0_pick` misses (bottle already toppled to lying); two more `pi0_pick` attempts on the horizontal cylinder fail to close (no side-grasp primitive); four `move_pose` attempts to scripted-pinch the lying body top out at x=0.274 but the arm can only reach that x at z≥0.12, above the bottle's z≈0.03 body — unrecoverable. Honest failure reported (`libero_terminated: false`).

**Release-from-height mode**: the proximate cause is releasing a tall,
held-off-center bottle from carry height (z=0.35) over the basket rim
instead of descending to seat its base below the rim first. This is the
*identical failure mode* hit by the Day-4-evening rerun of seed 0 preserved
at `artifacts/harness/day4_object_swap_t2_s0_r2/` (its own
`object_swap_t2_s0.json`/`recipe_object_swap_t2_s0.jsonl`, distinct from the
released reference): that run also released high, the bottle "tipped over
the front rim and rolled out," and the agent then self-corrected *within
that same episode* by re-grasping and this time carrying to z=0.30 then
explicitly descending to z≈0.22-0.23 ("DESCENDED to seat the bottle base
below the rim before releasing", per the transcript) before releasing
successfully. That corrective lesson —
descend below rim before release for tall/off-center holds — exists only in
that ad hoc stray run's own recipe, not in either released memory note
(`tall_item_first_basket_placement.md`,
`feedback_staged_held_object_transport.md`) that s1 actually consulted.
**Candidate TSM improvement (hypothesis only, not applied)**: add a
"descend to seat below rim before release" rule to
`tall_item_first_basket_placement.md`.

## 6. Verdict

The released memory does function as the paper claims for the *skeleton*
and the *grasp-verification* portion of behavior: every pilot — including
the failure — read the same three notes, reproduced the identical
approach→pick→carry→release primitive order, staged a hold-verification
step before committing to the carry, and (per §3) never copy-pasted stale
coordinates into an executed action; s2 and s3 both independently
re-measured the basket via fresh SAM3/back_project calls and adjusted for a
real ~5-9cm shift, which is exactly "structural prior + live re-grounding."
But the pattern is not uniformly robust: s1 shows that re-grounding can be
skipped selectively (the pre-grasp binding was fresh, the carry binding
was not, "matching the seed-0 winning release pose" instead of measuring
this seed's basket), and the memory notes are silent on the one failure
mode (high release over a rim) that a prior Day-4 run had already
discovered and fixed ad hoc but never fed back into the released notes —
so the released TSM is a real, working structural prior with genuine live
re-grounding on the happy path, but it is incomplete as a *safety* prior and
provides no protection against partial (rather than absent) re-grounding.

## 7. Day-9 addendum: anchoring leak — a coordinate-leakage mode the §3 grep cannot see

The Day-9 case studies (`day9_case_studies.md` §1–2) found a leakage
mode this audit's §3 methodology (grep released literals in executed
actions) is blind to: **reference-coordinate anchoring of estimator
selection**. With-memory Object-S planners on seeds 3/4 never pasted
the s0 basket absolute (0.076, 0.231) into a command — instead, faced
with two conflicting fresh measurements (accurate region `center_xyz`
≈ 0.00 vs +x-biased `median_xyz`/SAM3 front-wall centroid ≈ +0.066),
both chose the biased one BECAUSE it matched the cached reference
("robust region median matches s0's (0.076, 0.231)", s4 run.log:53),
releasing outside the basket footprint. s1's copied carry binding (§2)
is the same mechanism. Consequence for §6's verdict: "live
re-grounding" held at the level of issuing fresh perception calls, but
the reference can still capture the *interpretation* of those calls
when the readout is ambiguous. Any future leakage audit must check
estimate-selection reasoning against the tool outputs, not just action
parameters against released literals.

## 8. Day-12 addendum: the leak rules, and why the Day-8 tripwire missed two runs

The Day-8 tripwire grepped for **one** hardcoded note name
(`tall_item_first_basket_placement`) across **three** of the five
planner-visible artifact globs. That is why two contaminated runs entered
the accepted results and were only found on Day 12 (see `risk_log.md`
2026-07-29 and `day8_mechanism.md` §4 Day-12 correction). A narrow
tripwire that passes is more dangerous than no tripwire, because it is
read as evidence the condition held.

`track/analysis/leak_rules.py` replaces it, and is the single source of
truth for both the queue-time tripwire and `test_ablation_leakage.py`:

- **199 content-bearing patterns** from a checked-in inventory
  (`memory_inventory.txt`, 206 names): the 43 Global Memory leaf names
  *not* mentioned in the released prompts/guides, plus all 156
  `results_*_pert` reference and recipe basenames.
- **Excluded, deliberately.** The bare paths `resources/libero/memory` and
  `resources/libero/results_*_pert`, and the 7 leaf names the released
  assets mention (`MEMORY`, `README`, `feedback_bowl_eef_y_offset`,
  `feedback_failure_forensics`, `feedback_pi0_pick_full_prompt`,
  `feedback_scripted_pick_limits`, `feedback_swap_perturbs_fixtures`).
  `prompts/system.py:393-414` instructs the planner to `list_dir` the
  memory directory and to record which notes it read, so those strings
  appear in every run: flagging them would make the tripwire fire always
  and mean nothing. Their appearance is the condition *working*.
- **All five artifact globs** are scanned: `launcher.log`, `rpent/run.log`,
  `rpent/*.stream.jsonl`, `rpent/*.txt`, `rpent/transcript_*.json`.
- **Condition-scoped.** A name is evidence only if that run's own
  condition hid it, read from its `run_meta.json` `exp_version`
  (v2-hiddenmem = memory + object family; v4 = memory + all four).
  Unknown or missing versions fall back to the strictest set — fail closed.
- **Inventory is checked in, not derived from the live tree**, so the audit
  works while memory is stashed and after it is restored. A drift test
  fails if the release gains a note the inventory lacks.
- **All three quarantined sets are pinned as regression controls**: if a
  future rules change stops detecting them, a test fails.

The §3 grep and §7 anchoring caveat still stand: this catches *content
acquisition*, not the anchoring leak, where a stale coordinate never
enters an action and instead biases estimator selection.
