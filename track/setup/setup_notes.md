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

## Day-5/6 pick-ups (from the Day-3 final review)

- Day 5 (harness freeze): add seed-0 `bootstrap_only: true` entries + harness
  cells in a new registry version; make `direct_lib.select_cell`
  condition-aware (it currently matches on suite+task_id only); record any
  strict-regime step-cap delta in the deviation table.
- Day 6 (batch runner): append `RpcError.server_traceback` to infra-row
  evidence and capture a per-run vla_server log slice (row-level evidence is
  currently thin for RPC-side failures); ledger aggregation must filter
  infra_failure and dedupe multi-attempt cells (object_swap_t2/1 now has an
  infra row AND a success row — both retained by design); implement the
  infra-only retry policy (cap 2); note build_ledger's "scored rows" print
  wording includes infra rows (fix when next touched); steps can overshoot
  max_steps by up to chunk-1 if a future cap isn't divisible by 5.
