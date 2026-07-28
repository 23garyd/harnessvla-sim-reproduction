#!/usr/bin/env bash
# Day-8 predeclared hidden-memory ablation (registry v2-hiddenmem).
# Stashes the released TSM, runs the 5 Object-S harness cells with
# otherwise-identical v2 pins, restores memory by trap, verifies the pin.
# Artifacts are isolated under artifacts/ablation/ and never enter the
# core paired ledger.
#
# Attempt-1 lesson (2026-07-28): a plain stash under artifacts/ was
# DISCOVERED by the planner via repo-wide `find` and read back — the
# condition silently un-hid itself. The stash is therefore (a) a single
# opaque tar, (b) outside the repo in a 0700 mktemp dir, and (c) every
# finished run is tripwire-grepped for stash/memory references; any hit
# aborts the queue and marks the run invalid.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Defense-in-depth: run_harness strips billing keys itself, but every
# launcher that reaches the planner also goes through run_planner.
source "$REPO/track/launchers/planner_env.sh"
RES="$REPO/RPent/resources"
MANIFEST="$REPO/track/manifests/ablation_hiddenmem_v2.json"
OUT_ROOT="$REPO/artifacts/ablation/runs"
STASH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tsm_ablation.XXXXXXXX")"
STASH_TAR="$STASH_DIR/tsm.tar"
# libero/memory + the seed-0 reference are the condition itself; the HF
# download cache leaks the note FILENAMES via *.lock/*.metadata (attempt-2
# seed-4 lesson), so it goes into the stash too.
STASH_MEMBERS=(libero/memory libero/results_object_pert)
[ -d "$RES/.cache" ] && STASH_MEMBERS+=(.cache)

restore() {
    if [ -f "$STASH_TAR" ]; then
        tar -C "$RES" -xf "$STASH_TAR"
        rm -rf "$STASH_DIR"
        echo "restored stashed members: ${STASH_MEMBERS[*]}"
    fi
    bash "$REPO/track/setup/pin_check.sh"
}
trap restore EXIT TERM INT

tripwire() {
    # $1 = run dir. Any reference to the stash location or to a
    # memory-note filename in the planner-visible logs means the
    # hidden-memory condition failed: mark and abort.
    local hits
    hits=$(grep -rl -e "$STASH_DIR" -e "tall_item_first_basket_placement" \
        "$1/launcher.log" "$1/rpent/run.log" "$1"/rpent/*.stream.jsonl \
        2>/dev/null || true)
    if [ -n "$hits" ]; then
        echo "TRIPWIRE: hidden-memory condition violated in $1" >&2
        echo "$hits" >&2
        printf 'condition violated — see queue log\n' > "$1/INVALID"
        return 1
    fi
}

for d in libero/memory libero/results_object_pert; do
    [ -d "$RES/$d" ] || { echo "FATAL: $RES/$d missing before stash" >&2; exit 1; }
done
tar -C "$RES" -cf "$STASH_TAR" "${STASH_MEMBERS[@]}"
for d in "${STASH_MEMBERS[@]}"; do rm -rf "${RES:?}/$d"; done
echo "stashed -> opaque tar outside repo: ${STASH_MEMBERS[*]}"

# Block rpent's HF auto-resync of the stashed memory dataset for the
# children of this shell; planner keys are stripped by run_harness itself.
export HF_HUB_OFFLINE=1

if [ $# -gt 0 ]; then SEEDS=("$@"); else SEEDS=(1 2 3 4 5); fi
for seed in "${SEEDS[@]}"; do
    echo "=== ablation hidden-memory libero_object_swap t2 seed $seed ==="
    PYTHONPATH= run_planner "$REPO/.venv/bin/python" \
        -m track.launchers.run_harness \
        --suite libero_object_swap --task-id 2 --seed "$seed" \
        --manifest "$MANIFEST" --out-root "$OUT_ROOT" || \
        echo "WARNING: seed $seed exited infra (row retained); continuing"
    latest="$(ls -td "$OUT_ROOT/v2-hiddenmem/harness/libero_object_swap_t2/$seed"/2* | head -1)"
    tripwire "$latest"
done

PYTHONPATH= "$REPO/.venv/bin/python" -m track.analysis.build_ledger \
    --runs-root "$OUT_ROOT" --out "$REPO/artifacts/ablation/ledger.csv"
echo "ablation queue done"
