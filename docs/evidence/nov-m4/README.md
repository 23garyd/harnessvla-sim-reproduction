# HarnessVLA Simulation Comparison and Ablation Artifacts

Prepared on 2026-11-14. Ledgers and videos come from existing simulation experiments. This update performs offline statistics without a GPU and packages technical materials only.

| Work | Implementation | Artifacts |
|---|---|---|
| Paired conditions and termination statistics | [Comparison program](../../../track/analysis/compare.py), [ledger builder](../../../track/analysis/build_ledger.py) | [Existing ledger](../oct-m3/snapshot-2026-08-25/harnessvla_ledger_80_rollouts.csv), [offline analysis](paired-analysis.json) |
| Frozen-policy and harness execution | [harness](../../../track/launchers/harness_lib.py) | [Video directory](video/), [video index and hashes](video-index.csv) |
| Hidden-memory ablation and failure boundaries | [Ablation entry point](../../../track/launchers/run_ablation_hiddenmem.sh) | [Existing mechanism notes](../../../track/registry/day8_mechanism.md), [memory audit](../../../track/registry/memory_audit.md) |
| Analysis and environment gate checks | [Tests](../../../track/tests/) | [53-test output](verification/2026-11-14-tests.txt) |

Using the original comparison program, complete condition pairs and exclusion of infrastructure failures, the recovered ledger recomputes to direct 15/40 and harness 23/40. This is offline recomputation of the retained ledger, not new rollouts. Condition definitions, termination reasons, ablation contamination and quarantined rows remain subject to the original registry and audit notes.

The four clips illustrate regression, hidden-memory ablation, no-memory timeout and a longer clock budget. All are simulation footage, not evidence of physical B601 execution, wireless comparisons or completion of two industrial application demonstrations. Individual cases do not replace full paired statistics.

[implementation-commits.csv](implementation-commits.csv) maps code commits; [manifest.csv](manifest.csv) retains artifact hashes.
