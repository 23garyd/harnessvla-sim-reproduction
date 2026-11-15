# HarnessVLA Simulation Implementation and Historical Evidence Index

Prepared on 2026-11-14. Implementation baseline: `cc653453f0bb6384a442007a1b0b411de827010b`.
This update packages existing simulation artifacts, with no new rollouts. Simulation video is not presented as B601 hardware footage.

| Feature | Implementation | Auditable artifacts |
|---|---|---|
| Frozen-policy and harness comparison runs | [direct](../../../track/launchers/run_direct.py), [harness](../../../track/launchers/run_harness.py) | [Experiment registry snapshot](snapshot-2026-08-25/harnessvla_experiment_registry.md) |
| Paired ledger and statistical analysis | [Ledger builder](../../../track/analysis/build_ledger.py), [comparison analysis](../../../track/analysis/compare.py) | [Historical ledger CSV](snapshot-2026-08-25/harnessvla_ledger_80_rollouts.csv), [technical progress record](snapshot-2026-08-25/harnessvla_progress_log.md) |
| Simulation execution example | [Harness implementation](../../../track/launchers/harness_lib.py) | [Simulation video](video/A_harness_success_spatial_task.mp4) |

Files in `snapshot-2026-08-25/` are byte-identical to the existing technical evidence pack. The video originally illustrated a simulated spatial task. Reusing it in multiple monthly materials does not create a new experiment or establish physical B601 execution, safety refusal or link degradation.

Although the ledger filename contains `80_rollouts`, its contents include base, extended and ablation records. Statistics require filtering by the registry version, conditions, pairing and termination reasons; the filename does not imply that every record belongs to one experiment. Large original per-rollout directories are not included here, and machine paths in the CSV are not externally downloadable URLs.

The [2026-11-14 test output](verification/2026-11-14-tests.txt) records 36 passing analysis and harness unit tests, not a new GPU simulation run.

This repository and the ASPIRE simulation repository are cited separately and report separate results.

[manifest.csv](manifest.csv) records byte counts, SHA-256 and provenance for the artifacts in this directory.

[implementation-commits.csv](implementation-commits.csv) maps each feature to its implementation files, the historical commits that last changed them, code links at the full baseline, and artifact paths. Historical implementation commits remain separate from evidence-packaging commits so documentation work is not presented as new implementation.
