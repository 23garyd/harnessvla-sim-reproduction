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
