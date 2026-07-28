#!/usr/bin/env bash
# Day-8 predeclared hidden-memory ablation (registry v2-hiddenmem).
# Stashes the released TSM, runs the 5 Object-S harness cells with
# otherwise-identical v2 pins, restores memory by trap, verifies the pin.
# Artifacts are isolated under artifacts/ablation/ and never enter the
# core paired ledger.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Defense-in-depth: run_harness strips billing keys itself, but every
# launcher that reaches the planner also goes through run_planner.
source "$REPO/track/launchers/planner_env.sh"
RES="$REPO/RPent/resources/libero"
STASH="$REPO/artifacts/ablation/stash"
MANIFEST="$REPO/track/manifests/ablation_hiddenmem_v2.json"
OUT_ROOT="$REPO/artifacts/ablation/runs"

restore() {
    for d in memory results_object_pert; do
        if [ -d "$STASH/$d" ]; then
            mv "$STASH/$d" "$RES/$d"
            echo "restored: $RES/$d"
        fi
    done
    bash "$REPO/track/setup/pin_check.sh"
}
trap restore EXIT

mkdir -p "$STASH" "$OUT_ROOT"
for d in memory results_object_pert; do
    [ -d "$RES/$d" ] || { echo "FATAL: $RES/$d missing before stash" >&2; exit 1; }
    [ -e "$STASH/$d" ] && { echo "FATAL: stale stash $STASH/$d" >&2; exit 1; }
    mv "$RES/$d" "$STASH/$d"
    echo "stashed: $d"
done

# Block rpent's HF auto-resync of the stashed memory dataset for the
# children of this shell; planner keys are stripped by run_harness itself.
export HF_HUB_OFFLINE=1

for seed in 1 2 3 4 5; do
    echo "=== ablation hidden-memory libero_object_swap t2 seed $seed ==="
    PYTHONPATH= run_planner "$REPO/.venv/bin/python" \
        -m track.launchers.run_harness \
        --suite libero_object_swap --task-id 2 --seed "$seed" \
        --manifest "$MANIFEST" --out-root "$OUT_ROOT" || \
        echo "WARNING: seed $seed exited infra (row retained); continuing"
done

PYTHONPATH= "$REPO/.venv/bin/python" -m track.analysis.build_ledger \
    --runs-root "$OUT_ROOT" --out "$REPO/artifacts/ablation/ledger.csv"
echo "ablation queue done"
