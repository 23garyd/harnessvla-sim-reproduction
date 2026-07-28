# Day-10 MVP freeze (2026-07-28)

The Day-10 core deliverable is frozen at this state. Nothing below may
be re-run, re-scored, or overwritten; extensions (Days 11+) go to new
registry versions and new artifact namespaces.

## Frozen deliverables

| item | value |
|---|---|
| Core ledger | `artifacts/ledger.csv`, 46 data rows (40 scored + 6 infra), sha256 `88450c6b9daa4bafacf8294121b52c2db55b6de4bbee241eecb6a792f4bed905` |
| Ablation ledger | `artifacts/ablation/ledger.csv`, 5 scored rows, sha256 `9aa679f5757a1e416ad3e97dc2b025bd03ea27f88dccf7b84c0e70820365a308` |
| Raw run artifacts | `artifacts/runs/` (v1 direct, v2 harness) + `artifacts/ablation/` (v2-hiddenmem + 2 quarantined condition-violated attempts); 3.4 GB total under the 200 GB cap |
| RPent pin | `6e4ba1805a459d74ad53569e833bae7ae2c59985` (worktree clean at freeze; upstream c01b9cf reviewed and deliberately NOT taken — day7_triage.md §7) |
| Checkpoint | pi0.5 `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT`, sha256 recorded in `track/setup/checkpoint.sha256sums` |
| Planner pin | claude_code / claude-opus-4-8, 60 turns, planner-timeout 1200 s, keys stripped (subscription billing) |
| Test suite | 115 tests green at freeze |
| Report | `track/report/reproduction_report.md` |

## Frozen headline numbers

Core paired matrix (40 scored rollouts, complete pairs only, Wilson 95%):
direct **5/20 [0.11, 0.47]** vs harness **11/20 [0.34, 0.74]**;
paired flips 9 rescued / 3 regressed / 2 both-pass / 6 both-fail.
Per-cell: Spatial-T 0/5→5/5, Goal-S 0/5→3/5, Goal-T 1/5→1/5,
Object-S 4/5→2/5. Predeclared hidden-memory ablation (Object-S):
5/5 vs 2/5 with memory; mechanism = reference-coordinate anchoring
(Day-9 correction).

## Provenance chain (mentor trace: claim → code → artifacts)

1. Claim + design: `docs/superpowers/specs/2026-07-26-sim-track-architecture-design.md`
2. Protocol: `track/registry/experiment_registry.md` (v1/v2/v2-hiddenmem)
   + `track/manifests/*.json` + `track/registry/protocol_deviations.md`
3. Execution: `track/launchers/` + `track/setup/` (pins, checksums)
4. Scoring: predicate-only, cumulative (`track/launchers/harness_lib.py`,
   `run_direct.py`); every scored row raw-verified
5. Analysis: `track/analysis/compare.py` + `build_ledger.py`
6. Findings: `track/registry/{day7_triage,day8_mechanism,day9_case_studies,memory_audit}.md`
7. Daily trace with results: `track/registry/progress_log.md`
