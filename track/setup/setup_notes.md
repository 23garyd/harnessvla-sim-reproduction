# Day-2 setup notes (2026-07-26)

Install + component smoke tests on asus (RTX A6000). Everything below was hit
during the first real `setup.sh all` + smoke run; fixes are in `setup.sh` so a
fresh start does not repeat them.

## Issues found and fixed

1. **Checkpoint URL in the internship plan is wrong.** The pi0.5 checkpoint is
   the HF **model** repo `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT` (public,
   ungated); the plan's `datasets/rlinf-pi05-libero-130-fullshot-sft` URL 404s
   on both repo-type and casing. Fixed in `setup.sh`; noted in HANDOVER.md and
   `track/registry/protocol_deviations.md` context.
2. **LIBERO-PRO simulator assets are not in the pip wheel.** Without them,
   `env.reset` dies on a missing scene XML. `setup.sh assets` (part of `all`)
   now runs `liberopro-download-assets --skip-existing` (865 files, RPent
   README step 2).
3. **openpi's lerobot pin is invisible to pip.** `rlinf-openpi` declares a bare
   `lerobot` dependency (its real pin, git rev `0cf8648`, sits in a uv-only
   `[tool.uv.sources]` table). pip resolved lerobot 0.3.3, which lacks the
   `lerobot.common` namespace openpi imports → vla_server crashed on boot.
   Do NOT `pip install lerobot==<old>` naively — it downgrades torch to 2.2
   and breaks the pinned stack (had to re-resolve with `RPent[full]`).
   `make_venv` now installs the pinned git rev with `--no-deps`.

## Known issues (open, tracked)

- **SIGABRT on teardown:** both env_server and vla_server exit `-6` after a
  clean `shutdown` RPC (EGL/CUDA context teardown abort). Functionally clean —
  shutdown RPC returns ok and the process exits promptly. The Day-6 batch
  runner must treat "shutdown RPC ok + prompt exit" as clean regardless of the
  negative exit code.
- **stdin-EOF kills the servers:** `watch_parent_death` treats stdin EOF as
  "parent died". Any launcher must keep an OPEN pipe on the server's stdin
  (never `/dev/null`), or the server shuts down milliseconds after binding.
- `pip check` reports pre-existing, unrelated conflicts (protobuf vs
  google-api-core/tensorboard/swanlab; lerobot's own historic bounds). Present
  since the initial `RPent[full]` resolve; harmless for this stack.

## Smoke-test results (2026-07-26, evidence under artifacts/smoke/2026-07-26/)

- `track/smoke/smoke_env.py`: PASS — boot 3.5 s; reset obs has
  `main_images (256,256,3)`, `wrist_images`, `states (8,)`; agentview RGB-D
  render non-degenerate (depth finite, near/far in camera meta); intrinsics +
  extrinsics present; task language returned; one `env.step` ok.
- `track/smoke/smoke_vla.py`: PASS — pi0.5 loads onto the A6000 in ~130–140 s;
  first inference 1.9 s, second 0.5 s; action chunk shape (5, 7), finite,
  |a|max ≈ 1.02. The `pi05_libero` config needs BOTH main and wrist views.

## Timing reference (for budget calibration)

- env_server boot: ~4 s; reset: seconds; render 256²: <1 s
- vla_server boot incl. model load: ~130–140 s (budget queue restarts accordingly)
- vla inference: ~0.5 s warm (~2 s first call)

## Day-3 gate (2026-07-26)

Two supervised `run_direct.py` rollouts, both exit 0 / non-`infra_failure`,
gating the direct frozen-VLA baseline (`track/manifests/core_v1.json`, HEAD
`0543d1d`). vla_server boot: `RPC server listening` at ~120 s (model ready in
110.6 s) — booting it requires `source track/setup/track_env.sh` first
(exports `PI05_CHECKPOINT_PATH`; the Task-6 plan snippet now says so
explicitly).

**Retained infra failures (evidence, not part of the gate):** the first
attempt at this gate hit an env-horizon bug — `LiberoEnv.reset` burns 15
zero-action settle steps of robosuite's internal horizon counter, so a
`--max-episode-steps` equal to the 600-step scoring budget made robosuite
flag `done` at driver-step 585 while the wire's `truncated` flag stayed
`False`; the next `env.chunk_step` call then crashed with `ValueError:
executing action in terminated episode`. Both cells failed identically
(585 steps, 118 chunks, ~110 s) — reproducible, not a flake. Fixed in
`696c12a` (env horizon = `max_steps + 20`; scoring budget unchanged at 600).
Per protocol these `infra_failure` rows are retained with evidence rather
than deleted; they remain in `artifacts/ledger.csv` (4 rows total: 2
`infra_failure` + the 2 gating rows below):
- `libero_object_swap_t2` seed 1, run `20260727T043506`: infra_failure/exception, 585 steps, 111.0 s
- `libero_spatial_task_t2` seed 1, run `20260727T043737`: infra_failure/exception, 585 steps, 110.3 s

**Gating rollouts (post-fix, HEAD `0543d1d`):**

| suite | seed | validity | terminal_reason | steps | wall_seconds | run dir |
|---|---|---|---|---|---|---|
| libero_object_swap_t2 | 1 | success | benchmark_predicate | 143 | 38.6 | `artifacts/runs/v1/direct/libero_object_swap_t2/1/20260727T044536` |
| libero_spatial_task_t2 | 1 | budget_exhausted | step_budget | 600 | 110.8 | `artifacts/runs/v1/direct/libero_spatial_task_t2/1/20260727T044619` |

Frame evidence (`frame_first.png`/`frame_last.png` in each run dir):
- object_swap (success): first frame shows a wire basket + several canned/
  bottled objects on a table with the gripper raised open; last frame shows
  the gripper descended, closed, and positioned directly at the basket —
  consistent with the benchmark predicate firing on a successful place.
- spatial_task (budget_exhausted): first frame shows three bowls, a plate, a
  box, and a drawer unit with the gripper raised; last frame shows the
  gripper lowered near two bowls that are now adjacent, but no object reaches
  a distinct goal location by step 600 — consistent with a genuine
  (non-infra) failure to trigger the predicate within budget.

Ledger rebuilt via `python -m track.analysis.build_ledger --runs-root
artifacts/runs --out artifacts/ledger.csv`: 4 rows (2 gating + 2 retained
infra_failure), 0 seed-0 excluded, 0 incomplete. vla_server shut down cleanly
via the plan's `pkill` line after the audit; GPU 0 (A6000) confirmed back to
idle (15 MiB).

## Day-3 evening direct queue (2026-07-27, attended)

The plan's Day-3 unattended slot (4 core cells x 2 further held-out seeds),
run attended after the supervised pilot passed. 8/8 rollouts valid, 0
infra_failure, ~11 min wall including one VLA boot. Direct-baseline ledger now
holds 10 scored rollouts (+ the 2 retained pre-fix infra rows):

| cell | scored seeds | successes | anchor (paper direct) |
|---|---|---|---|
| libero_object_swap_t2 (Object-S) | s1,s2,s3 | 3/3 | 78% — already-strong cell, matches |
| libero_spatial_task_t2 (Spatial-T) | s1,s2,s3 | 0/3 | 42% — weakest direct cell, matches |
| libero_goal_task_t2 (Goal-T) | s1,s2 | 1/2 | 45% |
| libero_goal_swap_t2 (Goal-S) | s1,s2 | 0/2 | 42% |

Aggregate 4/10 (small-n; the paper's overall direct rate is 50.0%). Direction
is consistent with the anchor table; no conclusions drawn until the matrix is
complete and paired with harness runs. Remaining direct cells for the core
matrix: seeds s4,s5 for object_swap/spatial_task and s3,s4,s5 for
goal_task/goal_swap (10 rollouts).

## Day-4 evening queue (2026-07-27, attended)

**Direct matrix COMPLETE (20/20 scored, ledger 22 rows incl. 2 retained infra):**

| cell | successes | paper anchor (direct) |
|---|---|---|
| libero_object_swap_t2 (Object-S) | 4/5 | 78% — matches closely |
| libero_spatial_task_t2 (Spatial-T) | 0/5 | 42% (single-task cell runs below the 10-task cell average) |
| libero_goal_task_t2 (Goal-T) | 1/5 | 45% |
| libero_goal_swap_t2 (Goal-S) | 0/5 | 42% |
| **aggregate** | **5/20 (25%)** | paper overall direct 50.0% |

Ordering matches the anchors (Object-S >> rest). Our hard cells run below the
paper's cell averages — expected with one fixed task (t2) per cell vs the
paper's 10; direction is what the core matrix tests.

**Harness pilots (object_swap t2, held-out seeds s1–s3; PRE-FREEZE exploratory
— planner claude-opus-4-8, 60-turn cap, settings not yet pinned; these do not
count as scored matrix rows):**

| seed | outcome | wall | note |
|---|---|---|---|
| s1 | failure (993 s) | correct grasp+carry; release-from-height rolled the tall bottle off the rim (same failure mode as the seed-0 first attempt) and no recovery within budget. Direct SUCCEEDED on this seed — retained as an honest anti-example |
| s2 | success (264 s) | basket at (-0.015, 0.275) — genuinely different from the Day-4 s0 rerun's live-grounded (0.077, 0.245) (the released s0 carry literal is [0.076, 0.231]); localized live, first-try placement |
| s3 | success (254 s) | single attempt, no reset |

Mechanism evidence on novel scenes: re-grounding confirmed (s2's shifted
basket). Failure lesson for Day-5 memory work: the release-from-carry-height
failure mode recurs — the seed-0 recipe's lesson ("descend below rim before
release") is in the Day-4 run's OWN written recipe but the released memory
does not carry it yet; a candidate Task-Specific-Memory improvement to test.

**Ops finding:** the SDK tool runtime resolves relative paths against RPent's
root; fumbled planner writes land in `RPent/artifacts/` and dirty the pinned
worktree — the pin gate correctly refused 10 direct rollouts until triaged.
Queue scripts now sweep `RPent/artifacts` into each run dir
(`planner_strays/`) after every harness rollout; preserved, never deleted.
The Day-6 batch runner must include this sweep.

## Day-5 memory validation + protocol freeze (2026-07-27)

**Memory audit** (`track/registry/memory_audit.md`): released Task-Specific
Memory confirmed as a structural prior — all four runs (released s0, pilots
s1–s3) share the approach→pi0_pick→carry→release skeleton with re-derived
spatial bindings; coordinate-leakage grep clean in s2/s3 (s1 has one literal
in reasoning prose only, never executed); s2 re-grounded a genuinely shifted
basket. Honest caveats: s1 copied its carry binding instead of re-measuring
(root cause of its failure), and the "descend below rim before release"
lesson — already self-discovered in the Day-4 s0 run — is absent from the
released notes (candidate TSM addition; hypothesis only, not applied).

**No-memory diagnostic**: object_swap t2 s2 with memory stashed
(HF_HUB_OFFLINE=1, dirs restored by trap; pin clean afterwards) → SUCCESS in
223 s. Mechanically validates the hidden-memory condition (nothing readable,
no leaks); scientifically consistent with the paper — Object-S is the cell
where the frozen VLA is already strong; the predicted swap-cell asymmetry is
Day-12's full ablation.

**Protocol freeze (mentor-approved, registry v2):** harness condition added on
the same 4 cells/seeds (`track/manifests/harness_v2.json`, seed 0
bootstrap_only + s1–s5); released one-shot regime as-is — guide cell budget
1200 steps, env backstop `--max-episode-steps 1220`; planner pinned
claude_code/claude-opus-4-8, 60 turns, planner-timeout 1200 s, keys
stripped; wall cap 2400 s. Budget
asymmetry vs direct (600) documented as deviation row 3. Direct rows scored
under v1 carry forward as the paired direct arm (nothing behavior-affecting
changed for that condition).

**Day-5 gate:** one harness rollout valid end to end ✅ (four now), memory
used without coordinate replay ✅ (audit), scoring rules frozen ✅ (v2). PASSED.

## Day-5/6 pick-ups (from the Day-3 final review)

- Day 5 (harness freeze): add seed-0 `bootstrap_only: true` entries + harness
  cells in a new registry version; make `direct_lib.select_cell`
  condition-aware (it currently matches on suite+task_id only); record any
  strict-regime step-cap delta in the deviation table.
- Day 6 (batch runner): OWNS harness budget enforcement — pass the pinned
  `--max-episode-steps 1220` / `--max-turns 60` / `--planner-timeout-s 1200`
  flags on every scored harness launch, enforce the 2400 s wall cap, and write
  harness `run_meta`/`result_row` records (needs a harness-condition variant
  of `build_run_meta`/`build_result_row` — the current ones hardcode
  condition="direct", turns=0, planner_model="none"). Also: require `task_id`
  in `validate_manifest`'s cell schema (matcher already consumes it;
  test fixtures need updating alongside).
- Day 6 (batch runner): append `RpcError.server_traceback` to infra-row
  evidence and capture a per-run vla_server log slice (row-level evidence is
  currently thin for RPC-side failures); ledger aggregation must filter
  infra_failure and dedupe multi-attempt cells (object_swap_t2/1 now has an
  infra row AND a success row — both retained by design); implement the
  infra-only retry policy (cap 2); note build_ledger's "scored rows" print
  wording includes infra rows (fix when next touched); steps can overshoot
  max_steps by up to chunk-1 if a future cap isn't divisible by 5.

## Day-4 gate (2026-07-27)

**Rollout:** `libero_object_swap` task 2, seed 0 ("Pick the salad dressing and
place it in the basket") — harness-mode rollout via the full Claude-planner
loop (not the direct frozen-VLA baseline). Outcome **success**,
`libero_terminated: true`, wall time 437.0 s (SDK-reported) / 439.8 s
(harness-reported). Planner: `claude-opus-4-8` via the `claude_code` backend
(Claude Agent SDK), invoked under the team's key-stripped Claude subscription
billing (no metered API key), with an advisory **$10 SDK budget cap** per
episode (`run.log`: "budget=$10.0") — advisory in that the harness logs/warns
against it but subscription billing means there is no hard metered cutoff.
33/60 planner turns used, 51 tool calls. Run dir (gitignored):
`artifacts/harness/day4_object_swap_t2_s0_r2/`.

**Day-4 gate statement:** "the trace visibly contains planner staging AND
retry around the same frozen pi0.5" — **PASSED**. Cite
`track/traces/day4_object_swap_t2_s0_annotated.md`: staging is visible at
turns 9, 13, 18, 23, 26, 28, 30 (`move_to`/`set_gripper` legs sequencing the
approach → grasp-verify → carry → descend → release skeleton); retry is
visible at turns 15-20 (failed-release recovery: the tall bottle tipped over
the basket rim on the first `release`, the planner re-localized the fallen
object and re-staged a second grasp) and again at turns 20-26 (an empty
`pi0_pick` grasp on the same frozen Pi0.5 checkpoint was diagnosed from
wrist-camera evidence and recovered with an analytic `set_gripper` fallback,
never a policy swap or reset). Both recoveries happened around the *same*
frozen `pi0.5` policy invoked via `pi0_pick` in turns 11 and 20 — no
retraining, no reset (0 reset invocations, confirmed in the trace's Audit 2).

**SAM3 BPE wheel bug (already fixed):** the `sam3` pip wheel omits its
repo-root `assets/` directory, but the packaged text encoder hardcodes
`<site-packages>/assets/bpe_simple_vocab_16e6.txt.gz` (the canonical CLIP BPE
vocab) and fails to load without it. Fixed in `track/setup/setup.sh`
(`fetch_sam3`, one line): fetch the vocab file from
`https://github.com/openai/CLIP/raw/main/clip/bpe_simple_vocab_16e6.txt.gz`
into that path and verify its sha256
(`924691ac288e54409236115652ad4aa250f48203de50a9e4722a6ecd48d6804a`) before
letting `sam3_server` start.

**Pointers:** run dir `artifacts/harness/day4_object_swap_t2_s0_r2/`; trace +
audits `track/traces/day4_object_swap_t2_s0_annotated.md`.
