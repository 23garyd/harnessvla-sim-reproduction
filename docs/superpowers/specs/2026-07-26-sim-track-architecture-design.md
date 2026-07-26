# HarnessVLA sim-track architecture — design spec

**Date:** 2026-07-26
**Machine:** asus (RTX A6000 48 GB = GPU 0; TITAN X unused)
**Scope:** Track-level architecture for the HarnessVLA simulation-reproduction track
(arXiv:2607.08448, RPent on LIBERO-Pro) — directory layout, environment, run/artifact
conventions, budgets, and overnight-queue policy. This spec organizes the track; the
per-day experimental work is defined by
`docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx` and is out of scope here.

## Decisions made during brainstorming

| Decision | Choice |
|---|---|
| Planner backend for scored runs | `claude_code` via the claude.ai subscription; `ANTHROPIC_API_KEY` stripped from every planner subprocess env |
| Version control | This folder becomes a git repo, pushed to a new **private** GitHub repo under the nuPylot org |
| Artifact disk budget | 200 GB hard cap under `artifacts/`, enforced by the batch runner |
| Layout approach | Approach A: single track tree; RPent nested but gitignored (alternatives considered: sibling dirs, working inside an RPent fork — rejected for fresh-start friction and asset-hygiene risk respectively) |

## 1. Directory layout and repositories

```
github_sow_harnessVLA/            # git repo → private GitHub (nuPylot)
├── HANDOVER.md
├── docs/                         # .docx plans + superpowers/specs/
├── track/                        # everything this track writes
│   ├── launchers/                # thin wrappers around rpent CLI + direct baseline
│   ├── manifests/                # frozen task/seed/condition manifests (yaml/json)
│   ├── analysis/                 # compare.py, build_ledger.py, trace annotators, hygiene tests
│   ├── registry/                 # experiment_registry.md, risk_log.md, deviation table
│   └── setup/                    # setup.sh, track_env.sh, env-manifest generator, pin_check.sh, checkpoint SHA256SUMS
├── RPent/                        # gitignored — upstream clone, pinned commit
├── checkpoints/                  # gitignored — pi0.5 download (checksums committed in track/setup/)
├── artifacts/                    # gitignored — all run outputs, 200 GB guard
│   └── runs/<exp_version>/<condition>/<task>/<seed>/<timestamp>/
└── .gitignore                    # RPent/, checkpoints/, artifacts/, .venv/
```

Rules:

- **RPent is pinned, never edited.** Its commit hash and its pyproject-pinned fork
  commits (RLinf/OpenPI/LIBERO-PRO) are recorded in `track/setup/env_manifest.md`.
  `pin_check.sh` fails loudly if RPent's HEAD or working tree drifts. Any
  behavior-affecting change to released assets (prompts, memories, primitives) requires
  mentor sign-off and lands as a recorded patch file in the track repo, never a silent
  edit.
- **The track repo is the unit of reproduction.** Day-16 fresh start = clone repo →
  `track/setup/setup.sh` → it clones RPent at the pinned commit, builds the venv,
  fetches and checksums the checkpoint.
- **Artifacts are append-only.** Run directories are unique
  (`exp_version/condition/task/seed/timestamp`) and never overwritten; resume logic
  skips cells that already have a valid `result_row.json`.

## 2. Environment, GPU pinning, and key hygiene

- **Python env:** one dedicated venv at `.venv/` (gitignored), built by `setup.sh`
  from system Python 3.10 — not conda, so the Day-16 fresh-start test carries no hidden
  conda state. Install via `pip install -e "RPent[full]"` keeping the pyproject-pinned
  forks (never upgrade robosuite or the LIBERO forks). After Day-2 smoke tests pass,
  freeze the resolved package set to `track/setup/requirements.lock`.
- **Canonical env file** `track/setup/track_env.sh`, sourced by every launcher and
  every overnight queue:

  ```bash
  export CUDA_VISIBLE_DEVICES=0            # A6000 only; TITAN X never used
  export PI05_CHECKPOINT_PATH=$REPO/checkpoints/rlinf-pi05-libero-130-fullshot-sft
  export LIBERO_TYPE=pro
  export MUJOCO_GL=egl
  ```

- **Key hygiene (billing policy made structural):** every launcher invokes the planner
  subprocess with `env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY`, so the `claude_code`
  planner can only bill the claude.ai subscription and can never silently pick up
  `~/anthropic-api.txt`. A pytest in `track/analysis/` asserts the strip is present in
  launcher code, and the Day-2 smoke test verifies the planner subprocess env is clean.
  The HF token (`~/huggingface.txt`) is used once by `setup.sh` for the checkpoint
  download and never exported into run environments.
- **GPU sanity:** `setup.sh` asserts GPU 0 reports "RTX A6000" before anything runs.

## 3. Run conventions, result schema, and the experiment registry

Every rollout produces one run directory containing RPent's raw REPL artifacts
(`command.json`, `state_NN.json`, `log_NN.json`, RGB-D frames, video) plus two
track-added files:

- **`run_meta.json`** — written at launch, immutable: experiment version, condition,
  task, suite, seed, planner model ID + settings, prompt hashes, RPent commit,
  checkpoint checksum, budgets (steps/turns/time), and the launch command.
- **`result_row.json`** — written at termination: success (decided **only** by the
  benchmark completion predicate in `state_NN.json` — never vla_act stop predicates or
  planner self-reports), terminal reason, step/turn/vla_act/analytic-primitive counts,
  wall time, and a validity status from the fixed vocabulary
  `{success, valid_failure, infra_failure, timeout, budget_exhausted}`.

Conventions:

- **The ledger is derived, never hand-edited.** `track/analysis/build_ledger.py`
  regenerates `ledger.csv` by scanning `artifacts/runs/`; any reported number must
  reproduce from a clean ledger rebuild. Valid policy failures stay in the denominator.
  `infra_failure` status requires cited evidence (crash log, missing artifact,
  corrupted render) recorded in the row.
- **Experiment versioning:** `track/registry/experiment_registry.md` assigns a version
  tag (`v1`, `v2`, …) to every behavior-affecting configuration — planner
  model/settings, prompt hashes, baseline implementation, ablation flags. Runs record
  their version in `run_meta.json`. A version bump invalidates affected paired cells;
  both conditions of those pairs are rerun. The registry also logs every agent-authored
  change, per the plan's audit rule.
- **Seed convention, encoded not remembered:** manifests mark seed 0
  `bootstrap_only: true`; the ledger builder refuses to score any seed-0 row, and the
  manifest-freeze step verifies s1–s5 map to LIBERO init states distinct from seed 0.

## 4. Budgets and the overnight-queue policy

Budgets are enforced by the batch runner, not by convention:

- **Disk:** guard trips at 200 GB total under `artifacts/`, checked before each rollout
  starts; the queue pauses, never deletes.
- **Planner spend:** with the `claude_code` planner billing the subscription, the cap is
  expressed as per-rollout **turn and token caps** plus a **per-queue rollout cap**,
  frozen per experiment version in the manifest and calibrated from the Day-4/5
  supervised pilots.
- **Time/steps:** every rollout gets hard step, wall-time, and turn budgets from its
  manifest; exceeding one terminates the rollout as `budget_exhausted`, which is a
  scored failure, not a rerun candidate.

Overnight queues (the plan's operating rule, made mechanical):

- A queue is a **frozen manifest** (task/seed/condition cells) plus a pinned experiment
  version — nothing else. No queue runs before its supervised pilot passed the same day.
- The runner provides: unique output dirs, resume-without-overwrite, health checks
  (env_server/vla_server liveness, GPU visibility), timeout enforcement with
  process-tree cleanup, and the disk guard.
- **Retry policy is predeclared:** only rows classified `infra_failure` with cited
  evidence are re-queued, capped at 2 attempts. `valid_failure` rows are never retried
  and never overwritten.
- Queues run in a `tmux` session with `track_env.sh` sourced; morning triage starts
  from `build_ledger.py` output, not the queue's own logs.
- The plan's `/loop 30m` triage check may pause a queue on a tripped guard but never
  deletes artifacts or changes configs.

## Out of scope

- The experimental protocol itself (tasks, seeds, conditions, ablations, gates) — owned
  by the internship plan document.
- The B601/ACT track. If ACT training later runs on this machine it gets its own
  folder and spec; nothing in this layout reserves space for it.
- Creation of the GitHub remote is an implementation step (repo under nuPylot, private).

## Success criteria

1. Day-16 fresh-start test passes from this repo alone: clone → `setup.sh` → one valid
   paired rollout, with no undocumented steps.
2. `pin_check.sh` and the key-hygiene pytest pass throughout the track; RPent and the
   released assets show zero unrecorded modifications.
3. Every number in any report reproduces from `build_ledger.py` over `artifacts/runs/`.
4. No overnight queue ever exceeds its disk, turn/token, or rollout caps, and no valid
   policy failure is ever retried or overwritten.
