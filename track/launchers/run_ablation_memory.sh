#!/usr/bin/env bash
# Generalized memory-ablation condition wrapper.
#
# Default condition is registry v4 = the paper's Table 5 zero-shot protocol:
# hide Global Memory (resources/libero/memory), ALL FOUR Task-Specific Memory
# dirs (resources/libero/results_*_pert) and the HF download cache, then run
# the manifest's harness cells with otherwise-identical v2/v3 pins. Also
# drives the Day-8 v2-hiddenmem manifest via run_ablation_hiddenmem.sh.
#
# Hardening (see track/registry/day12_ablation_design.md sections 1 and 5):
#   - the stash is ONE opaque tar in a 0700 mktemp dir OUTSIDE the repo,
#     because a plain in-repo stash was located by the planner's repo-wide
#     `find` and read back (Day-8 attempt 1)
#   - HF_HUB_OFFLINE=1 blocks rpent's HF re-sync of the stashed dataset, and
#     the HF cache is stashed too because *.lock/*.metadata leak note
#     FILENAMES (Day-8 attempt 2 — and the Day-12 audit found this same leak
#     had contaminated 2 ACCEPTED Day-8 rows, so it is not theoretical)
#   - every finished run is leak-scanned by track.analysis.leak_rules, the
#     same module test_ablation_leakage.py uses; any hit quarantines the run
#     and aborts the queue
#   - per-seed clean slate: anything the planner creates under a hidden path
#     is moved into the run dir as evidence and the path restored to absent,
#     so run k cannot inherit run k-1's notes. pin_check cannot catch this
#     because RPent/resources/ is gitignored.
#
# Functions are defined unconditionally; main runs only on execution, so
# tests can source this file.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RES="${TRACK_RES:-$REPO/RPent/resources}"
PY="${TRACK_PY:-$REPO/.venv/bin/python}"
DEFAULT_MANIFEST="$REPO/track/manifests/ablation_zeroshot_v4.json"
OUT_ROOT="${OUT_ROOT:-$REPO/artifacts/ablation/runs}"
QUARANTINE="${QUARANTINE:-$REPO/artifacts/ablation/quarantine}"

usage() {
    echo "usage: run_ablation_memory.sh [--manifest FILE] [--limit N]" \
         "[--dry-run] [--self-check]" >&2
    exit 64
}

# Stash state is SCRIPT-SCOPE, never local to main(). The EXIT trap runs after
# main()'s frame is gone, so locals are invisible there and `set -u` kills the
# restore before it extracts — which is exactly what happened on the first v4
# pilot (2026-07-29): the queue finished, the trap died on `stash_tar: unbound
# variable`, and the released assets were left stashed. pin_check does NOT
# catch this because RPent/resources/ is gitignored.
STASH_DIR=""
STASH_TAR=""
MEMBERS_FILE=""

restore() {
    local rc=$?
    if [ -n "${STASH_TAR:-}" ] && [ -f "${STASH_TAR:-}" ]; then
        tar -C "$RES" -xf "$STASH_TAR"
        # Self-verify: every stashed member must be back on disk. A silent
        # restore failure leaves the repo memory-free, which would invisibly
        # contaminate every LATER run, ablation or not.
        local member missing=0
        while read -r member; do
            [ -n "$member" ] || continue
            [ -e "$RES/$member" ] || { echo "FATAL: restore left '$member' missing" >&2; missing=1; }
        done < "$MEMBERS_FILE"
        if [ "$missing" = 1 ]; then
            echo "FATAL: released assets NOT fully restored. Stash retained at" \
                 "$STASH_DIR — extract it manually before any further run:" >&2
            echo "  tar -C $RES -xf $STASH_TAR && rm -rf $STASH_DIR" >&2
            echo "DELETE the stash afterwards: a stale tar under \$TMPDIR is a" \
                 "readable copy of the hidden memory that a LATER ablation's" \
                 "planner could find, and the tripwire only knows its own" \
                 "current stash path." >&2
            return 1
        fi
        rm -rf "$STASH_DIR"
        echo "restored stashed members (verified present)"
    fi
    bash "$REPO/track/setup/pin_check.sh"
    return $rc
}

do_stash() {
    STASH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tsm_ablation.XXXXXXXX")"
    chmod 700 "$STASH_DIR"
    STASH_TAR="$STASH_DIR/stash.tar"
    MEMBERS_FILE="$STASH_DIR/members.txt"
    [ -d "$RES/libero/memory" ] || {
        echo "FATAL: $RES/libero/memory missing before stash" >&2; exit 1; }
    stash_members > "$MEMBERS_FILE"
    tar -C "$RES" -cf "$STASH_TAR" -T "$MEMBERS_FILE"
    local member
    while read -r member; do
        [ -n "$member" ] && rm -rf "${RES:?}/$member"
    done < "$MEMBERS_FILE"
    echo "stashed -> opaque tar outside repo:"
    sed 's/^/  /' "$MEMBERS_FILE"
}

stash_members() {
    # One member path per line, relative to RES. MUST be captured before the
    # stash: afterwards the results_*_pert glob matches nothing, so recomputing
    # it later would silently shrink the list and break restore AND hygiene.
    local members=(libero/memory) d
    for d in "$RES"/libero/results_*_pert; do
        [ -d "$d" ] && members+=("libero/$(basename "$d")")
    done
    [ -d "$RES/.cache" ] && members+=(.cache)
    printf '%s\n' "${members[@]}"
}

plan_cells() {
    # "suite task_id seed" lines for $1's harness cells, via validated Python.
    ( cd "$REPO" && PYTHONPATH= "$PY" -m track.analysis.manifests \
        --plan "$1" --condition harness )
}

exp_version_of() {
    ( cd "$REPO" && PYTHONPATH= "$PY" -c \
        'import json,sys; print(json.load(open(sys.argv[1]))["exp_version"])' "$1" )
}

hygiene_after_seed() {
    # $1 = run dir, $2 = members file. Preserve planner-created files as
    # evidence, then restore the hidden paths to absent for the next seed.
    local run_dir="$1" members_file="$2" member dest
    while read -r member; do
        [ -n "$member" ] || continue
        [ -e "$RES/$member" ] || continue
        dest="$run_dir/planner_created_memory/$member"
        mkdir -p "$(dirname "$dest")"
        mv "$RES/$member" "$dest"
        echo "HYGIENE: planner created '$member' -> $dest"
    done < "$members_file"
}

tripwire() {
    # $1 = run dir, $2 = stash dir. Shares its rule set with
    # test_ablation_leakage.py through track.analysis.leak_rules.
    if ! ( cd "$REPO" && PYTHONPATH= "$PY" -m track.analysis.leak_rules \
            --scan "$1" --stash "$2" ); then
        mkdir -p "$QUARANTINE"
        printf 'condition violated — leak_rules flagged hidden-memory content\n' \
            > "$1/INVALID"
        mv "$1" "$QUARANTINE/$(basename "$(dirname "$1")")_$(basename "$1")"
        echo "TRIPWIRE: quarantined and aborting queue" >&2
        return 1
    fi
}

main() {
    local manifest="$DEFAULT_MANIFEST" limit=0 dry_run=0 self_check=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --manifest)   [ $# -ge 2 ] || usage; manifest="$2"; shift 2 ;;
            --limit)      [ $# -ge 2 ] || usage; limit="$2"; shift 2 ;;
            --dry-run)    dry_run=1; shift ;;
            --self-check) self_check=1; shift ;;
            *) usage ;;
        esac
    done

    if [ "$self_check" = 1 ]; then
        # Exercise the REAL stash + trap-restore path with no rollout. Run this
        # before burning a planner window: it is what would have caught the
        # 2026-07-29 unbound-variable restore failure.
        trap restore EXIT TERM INT
        do_stash
        local member hidden=1
        while read -r member; do
            [ -n "$member" ] || continue
            [ -e "$RES/$member" ] && { echo "FATAL: '$member' still present after stash" >&2; hidden=0; }
        done < "$MEMBERS_FILE"
        [ "$hidden" = 1 ] || return 1
        echo "self-check: stash hid every member; restoring via the EXIT trap"
        return 0
    fi

    local cells
    cells="$(plan_cells "$manifest")"
    if [ "$limit" -gt 0 ]; then
        cells="$(printf '%s\n' "$cells" | head -n "$limit")"
    fi

    if [ "$dry_run" = 1 ]; then
        echo "manifest: $manifest (exp_version $(exp_version_of "$manifest"))"
        echo "would hide:"
        stash_members | sed 's/^/  /'
        echo "would run:"
        printf '%s\n' "$cells"
        return 0
    fi

    # Defense in depth: run_harness strips billing keys itself, but every
    # launcher reaching the planner also goes through run_planner.
    source "$REPO/track/launchers/planner_env.sh"

    local exp
    exp="$(exp_version_of "$manifest")"
    trap restore EXIT TERM INT
    do_stash

    # Block rpent's HF auto-resync of the stashed memory dataset.
    export HF_HUB_OFFLINE=1

    local suite task_id seed run_parent latest
    while read -r suite task_id seed; do
        [ -n "$suite" ] || continue
        run_parent="$OUT_ROOT/$exp/harness/${suite}_t${task_id}/$seed"
        if compgen -G "$run_parent/2*/result_row.json" > /dev/null; then
            echo "=== skip (already has a row): $suite t$task_id s$seed ==="
            continue
        fi
        echo "=== ablation $exp $suite t$task_id seed $seed ==="
        PYTHONPATH= run_planner "$PY" -m track.launchers.run_harness \
            --suite "$suite" --task-id "$task_id" --seed "$seed" \
            --manifest "$manifest" --out-root "$OUT_ROOT" || \
            echo "WARNING: seed $seed exited infra (row retained); continuing"
        latest="$(ls -td "$run_parent"/2* | head -1)"
        tripwire "$latest" "$STASH_DIR"
        hygiene_after_seed "$latest" "$MEMBERS_FILE"
    done <<< "$cells"

    ( cd "$REPO" && PYTHONPATH= "$PY" -m track.analysis.build_ledger \
        --runs-root "$OUT_ROOT" \
        --out "$REPO/artifacts/ablation/ledger.csv" )
    echo "ablation queue done"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
