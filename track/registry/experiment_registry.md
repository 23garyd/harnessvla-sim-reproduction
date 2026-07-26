# Experiment registry

Every behavior-affecting configuration gets a version tag here before any run
uses it: planner model + settings, prompt hashes, baseline implementation,
ablation flags. Runs record their tag in `run_meta.json`. A version bump
invalidates affected paired cells; both conditions of those pairs are rerun.

| Version | Date | Planner model + settings | Prompt hashes | Baseline impl | Ablation flags | Notes |
|---|---|---|---|---|---|---|
| v0 | 2026-07-26 | none — scaffolding only, no runs | n/a | n/a | n/a | Track scaffolding built; first experiment version will be v1, frozen at Day 3 with the baseline decision |

## Agent-authored change log

Log every agent-authored change to track code here, like any other code
change (plan section 2, "Claude Code + superpowers working model").

| Date | Change | Files | Reviewed by |
|---|---|---|---|
| 2026-07-26 | Initial track scaffolding (this repo structure, scripts, schemas, tests) | track/ | pending mentor review |
| 2026-07-26 | setup.sh Day-2 fixes: model-repo checkpoint, assets stage, lerobot git pin, hf-cache cleanup | track/setup/setup.sh | pending mentor review |
| 2026-07-26 | Day-2 smoke tests, env-manifest generator, setup notes, requirements freeze | track/smoke/, track/setup/{gen_env_manifest.sh,env_manifest.md,setup_notes.md,requirements.lock} | pending mentor review |
