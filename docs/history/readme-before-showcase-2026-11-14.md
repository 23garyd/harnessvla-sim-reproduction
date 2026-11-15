# Technical Guide Before the Showcase Update

This historical README records the status and commands of its original environment. See the [current project overview](../../README.md). The editorial header is translated; the historical run instructions below are retained.

# HarnessVLA sim track (asus)

Additional technical evidence: [benchmarks, reproduction and archives](../../docs/evidence/dec-m5/README.md).

Additional technical evidence: [comparisons and demonstrations](../../docs/evidence/nov-m4/README.md).

See the [technical evidence index](../../docs/evidence/oct-m3/README.md) for current implementation entry points, artifacts and verification records.

Reproduction of HarnessVLA (arXiv:2607.08448, RPent) on LIBERO-Pro with a
frozen pi0.5 checkpoint. Runs on the RTX A6000 (GPU 0) only.

- **What/why/how:** `HANDOVER.md`, then
  `docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`
- **Architecture spec:** `docs/superpowers/specs/2026-07-26-sim-track-architecture-design.md`

## Quick start

Prerequisites: HF token at `~/huggingface.txt`, NVIDIA driver loaded
(GPU 0 = RTX A6000), system Python 3.10.

```bash
git clone <this-repo> && cd github_sow_harnessVLA
track/setup/setup.sh all            # GPU assert, RPent clone, venv, checkpoint
track/setup/pin_check.sh --record   # first-ever setup only, after reviewing the clone
track/setup/pin_check.sh            # every later session: verify pin + clean worktree
source track/setup/track_env.sh     # before any run or queue
```

After the Day-2 smoke tests pass: `track/setup/setup.sh freeze` to write
`track/setup/requirements.lock`.

## Development tests (no GPU needed)

```bash
python3 -m venv .venv-dev && .venv-dev/bin/pip install pytest
PYTHONPATH= .venv-dev/bin/python -m pytest track/tests -v
```

(the `PYTHONPATH=` prefix guards against ROS site-packages leaking into pytest on this machine)

## Layout

| Path | What |
|---|---|
| `track/launchers/` | Launcher wrappers; all planner calls go through `run_planner` (key strip) |
| `track/manifests/` | Frozen task/seed/condition queue manifests (JSON) |
| `track/analysis/` | Schemas, ledger builder, disk guard, manifest validator |
| `track/registry/` | Experiment registry, live risk log, deviation table |
| `track/setup/` | `setup.sh`, `track_env.sh`, `pin_check.sh`, pins, checksums |
| `RPent/` (gitignored) | Upstream clone, pinned — never edited |
| `checkpoints/` (gitignored) | pi0.5 download; checksums live in `track/setup/` |
| `artifacts/` (gitignored) | Run outputs, 200 GB guard, append-only |

## Standing rules

- Success is decided only by the benchmark predicate in `state_NN.json`.
- Seed 0 bootstraps memory and is never scored.
- Valid policy failures are never retried, deleted, or overwritten.
- `ANTHROPIC_API_KEY` is stripped from every planner subprocess
  (`track/launchers/planner_env.sh`) — planner work bills the claude.ai
  subscription only.
