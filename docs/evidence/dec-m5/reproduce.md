# Technical notes on reproduction and archiving

Compilation date: 2026-11-14. This directory prepares the December technical delivery; it does not indicate December acceptance or completion of all final work.

Checked-out source commit: `05ad169a0bea541b1c7a36fafe3b0012a4866bc3`. [archive-manifest.csv](archive-manifest.csv) provides a fixed GitHub link, byte count, and SHA-256 for each code file and existing attachment. The archive covers all tracked files in that source commit; it excludes the newly created dec-m5 directory itself, whose integrity is recorded separately in [manifest.csv](manifest.csv) to avoid circular hashing.

```bash
git clone https://github.com/23garyd/harnessvla-sim-reproduction.git
cd harnessvla-sim-reproduction
git checkout 05ad169a0bea541b1c7a36fafe3b0012a4866bc3
```

Paths in the archive CSV are relative to the repository root. Verify each file with SHA-256 after download/checkout; Git attributes in the evidence directories protect file bytes. The repository remains private, and access uses existing authorization.

[Test commands and actual output from the existing environment](../nov-m4/verification/2026-11-14-tests.txt) establish only that the specified hardware-free software subset runs. Prepare the full software dependencies, GPU, vendor SDK, models, and raw data separately using the [repository instructions](../../../README.md) and the original environment pinning files.

The work completed here consists of checking out code from the existing private source and verifying attachments and the software subset; it does not constitute a clean-machine rebuild of the entire system or verification that a third party can independently launch real experiments. Do not run physical robot entry points directly on unmeasured/uncalibrated machines; the current software checks do not require powering on the robot arm.

[setup.sh](../../../track/setup/setup.sh) and [pin_check.sh](../../../track/setup/pin_check.sh) are the original GPU environment entry points. Only software checks without a GPU were run here; RPent, pi0.5 weights, and the full artifacts directory are external dependencies and cannot be replaced by a few videos or ledgers.
