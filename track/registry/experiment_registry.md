# Experiment registry

Every behavior-affecting configuration gets a version tag here before any run
uses it: planner model + settings, prompt hashes, baseline implementation,
ablation flags. Runs record their tag in `run_meta.json`. A version bump
invalidates affected paired cells; both conditions of those pairs are rerun.

| Version | Date | Planner model + settings | Prompt hashes | Baseline impl | Ablation flags | Notes |
|---|---|---|---|---|---|---|
| v0 | 2026-07-26 | none — scaffolding only, no runs | n/a | n/a | n/a | Track scaffolding built; first experiment version will be v1, frozen at Day 3 with the baseline decision |
| v1 | 2026-07-26 | none — direct condition has no planner | n/a (no planner prompts) | Minimal chunk-stream loop via vla_server (track/registry/baseline_design.md) | none | Core matrix frozen: 4 suites × t2 × s1–s5 (core_v1.json); budgets 600 steps / 1800 s; harness condition to be added at the Day-5 freeze |
| v2 | 2026-07-27 | claude_code / claude-opus-4-8, --max-turns 60, planner-timeout 1200 s, SDK defaults, ANTHROPIC/OPENAI keys stripped (subscription billing) | released prompts + guides pinned via RPENT_COMMIT 6e4ba18 (read-only) | direct arm carried forward from v1 unchanged; harness = released one-shot regime as-is | none | Day-5 protocol freeze (mentor-approved): harness cells added (harness_v2.json, seed 0 bootstrap_only + s1–s5); guide cell budget 1200 steps with env backstop 1220 (+20 settle margin); budget asymmetry vs direct 600 documented in deviation row 3 |

## Agent-authored change log

Log every agent-authored change to track code here, like any other code
change (plan section 2, "Claude Code + superpowers working model").

| Date | Change | Files | Reviewed by |
|---|---|---|---|
| 2026-07-26 | Initial track scaffolding (this repo structure, scripts, schemas, tests) | track/ | pending mentor review |
| 2026-07-26 | setup.sh Day-2 fixes: model-repo checkpoint, assets stage, lerobot git pin, hf-cache cleanup | track/setup/setup.sh | pending mentor review |
| 2026-07-26 | Day-2 smoke tests, env-manifest generator, setup notes, requirements freeze | track/smoke/, track/setup/{gen_env_manifest.sh,env_manifest.md,setup_notes.md,requirements.lock} | pending mentor review |
| 2026-07-27 | Day-4 harness prep: SAM3 stage (sam3.pt + pinned CLIP BPE vocab the wheel omits), SAM3_CHECKPOINT_PATH in track_env | track/setup/{setup.sh,track_env.sh,sam3.sha256sums}, track/tests/test_track_env.py | pending mentor review |
| 2026-07-27 | Day-4 annotated harness trace + audits (first harness rollout, object_swap t2 s0, success with retry) | track/traces/, track/setup/setup_notes.md | pending mentor review |
