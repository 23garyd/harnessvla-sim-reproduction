# Direct-baseline design (frozen Day 3, 2026-07-26)

Per the internship plan's design-reference decision, the paper's baseline is a
continuous end-to-end pi-RLinf rollout. Of the two sanctioned implementations
we freeze **(b): a minimal loop streaming vla_server action chunks conditioned
on the full task instruction until the benchmark predicate fires or the step
cap is hit** (`track/launchers/run_direct.py`). Rationale: (a) the RLinf eval
pipeline is a training-repo artifact with its own runner/logging conventions;
(b) reuses exactly the smoke-tested servers and gives us schema-native
run_meta/result_row artifacts with full budget control.

## Frozen parameters (experiment v1)

| Item | Value | Shared with harness? |
|---|---|---|
| Checkpoint | RLinf-Pi05-LIBERO-130-fullshot-SFT, sha256 4d9089c9... (model.safetensors) | identical (frozen, never fine-tuned) |
| Cameras | env defaults: agentview `main_images` 256x256 + wrist 256x256, both fed to pi0.5 | identical (env_server init_params) |
| Action chunking | model-native 5-step chunks (`pi05_libero`, action_dim 7); every chunk executed in full unless the predicate fires mid-chunk | identical model config |
| Step cap | 600 env steps (benchmark horizon) | shared where shared: harness scored runs use the strict regime; any step-cap difference is recorded at the Day-5 freeze |
| Wall cap | 1800 s per rollout | same for harness |
| Instruction | full `env.get_task_language()` string every predict call | harness composes its own vla_act prompts (by design) |
| Scoring | success iff `terminated` (benchmark predicate) fires before budgets; vla stop-predicates/self-reports never score | identical rule |

## Core matrix (frozen in track/manifests/core_v1.json)

4 cells x seeds s1-s5, task id 2 per suite (predeclared, matches the RPent
README example; no outcome-based selection): libero_spatial_task (Spatial-T,
paper 42->94), libero_goal_task (Goal-T, 45->87), libero_goal_swap (Goal-S,
42->87), libero_object_swap (Object-S, 78->90, honest hard case). Seed
distinctness evidence: track/manifests/core_v1_seed_check.txt.

## Validity mapping (schemas vocabulary)

- predicate fired -> success / "benchmark_predicate"
- step cap -> budget_exhausted / "step_budget" (scored failure)
- wall cap -> budget_exhausted / "wall_time" (scored failure)
- env truncated early -> valid_failure / "env_truncated"
- launcher exception -> infra_failure + traceback evidence (never scored, rerun candidate)
