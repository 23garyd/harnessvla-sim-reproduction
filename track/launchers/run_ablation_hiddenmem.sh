#!/usr/bin/env bash
# Day-8 predeclared hidden-memory ablation (registry v2-hiddenmem).
#
# Kept as the documented Day-8 entry point; the condition logic now lives in
# run_ablation_memory.sh, which this pins to the v2-hiddenmem manifest.
#
# IMPORTANT — this wrapper no longer reproduces the ORIGINAL v2-hiddenmem
# condition, it reproduces a strictly STRONGER one. The 2026-07-28 runs hid
# Global Memory + the object TSM only (and, for seeds 1-2, not even the HF
# cache). run_ablation_memory.sh's stash_members is generic, so a run today
# hides Global Memory + ALL FOUR TSM dirs + the HF cache.
#
# Consequences, do not paper over them:
#   - rows produced now are NOT poolable with the 3 clean historical
#     v2-hiddenmem rows; they are a different condition wearing the same
#     exp_version. Restoring the quarantined seeds 1-2 to get back to n=5
#     therefore requires a NEW exp_version, not a re-run under this wrapper.
#   - leak_rules.CONDITION_HIDDEN_TSM maps v2-hiddenmem to the object family
#     only, which is correct for auditing the HISTORICAL rows but would
#     under-check a run made today. Add the new version to that table.
# See day12_ablation_design.md §3 and day8_mechanism.md §4.
#
# BEHAVIOUR CHANGE: the old script took bare seed arguments
# (`run_ablation_hiddenmem.sh 4 5`). Seeds now come from the manifest and
# slicing is `--limit N`. Any arguments are forwarded, so --dry-run works.
set -euo pipefail
REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
exec bash "$REPO/track/launchers/run_ablation_memory.sh" \
    --manifest "$REPO/track/manifests/ablation_hiddenmem_v2.json" "$@"
