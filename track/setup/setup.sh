#!/usr/bin/env bash
# One-command bootstrap (spec section 1): clone repo -> setup.sh -> it clones
# RPent at the pinned commit, builds the venv, fetches + checksums the
# checkpoint. Subcommands allow re-running any stage alone.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck disable=SC1091
source "$REPO/track/setup/setup_lib.sh"

PINS="$REPO/track/setup/pins.env"
RPENT_URL="https://github.com/RLinf/RPent"
CKPT_REPO="RLinf/rlinf-pi05-libero-130-fullshot-sft"
CKPT_DIR="$REPO/checkpoints/rlinf-pi05-libero-130-fullshot-sft"
SUMS="$REPO/track/setup/checkpoint.sha256sums"

clone_rpent() {
    [ -d "$REPO/RPent/.git" ] || git clone "$RPENT_URL" "$REPO/RPent"
    local pin
    pin="$(read_pin "$PINS")"
    if [ -n "$pin" ]; then
        git -C "$REPO/RPent" checkout --quiet "$pin"
        echo "RPent at pinned $pin"
    else
        echo "WARNING: RPENT_COMMIT unset; review the clone, then run" >&2
        echo "         track/setup/pin_check.sh --record" >&2
    fi
}

make_venv() {
    [ -d "$REPO/.venv" ] || python3 -m venv "$REPO/.venv"
    "$REPO/.venv/bin/pip" install --upgrade pip
    # Keep the pyproject-pinned RLinf/OpenPI/LIBERO-PRO forks; never
    # upgrade robosuite or the LIBERO forks (plan + spec section 2).
    "$REPO/.venv/bin/pip" install -e "$REPO/RPent[full]"
}

fetch_checkpoint() {
    mkdir -p "$REPO/checkpoints"
    if [ ! -d "$CKPT_DIR" ]; then
        [ -f "$HOME/huggingface.txt" ] || { echo "FATAL: HF token file missing at $HOME/huggingface.txt" >&2; return 1; }
        # Download to a temp dir and mv into place atomically so an interrupted
        # download can never be mistaken for a complete checkpoint (and then
        # TOFU-recorded as checksum truth by verify_checkpoint).
        rm -rf "$CKPT_DIR.partial"
        # HF token is read here once and scoped to this command only;
        # it is never exported into run environments (spec section 2).
        HF_TOKEN="$(cat "$HOME/huggingface.txt")" \
            "$REPO/.venv/bin/huggingface-cli" download "$CKPT_REPO" \
            --repo-type dataset --local-dir "$CKPT_DIR.partial"
        mv "$CKPT_DIR.partial" "$CKPT_DIR"
    fi
    verify_checkpoint "$CKPT_DIR" "$SUMS"
}

freeze_requirements() {
    # Run once, after the Day-2 smoke tests pass (spec section 2).
    "$REPO/.venv/bin/pip" freeze > "$REPO/track/setup/requirements.lock"
    echo "froze $REPO/track/setup/requirements.lock"
}

case "${1:-all}" in
    check)      assert_gpu; "$REPO/track/setup/pin_check.sh" ;;
    rpent)      clone_rpent ;;
    venv)       make_venv ;;
    checkpoint) fetch_checkpoint ;;
    freeze)     freeze_requirements ;;
    all)        assert_gpu; clone_rpent; make_venv; fetch_checkpoint ;;
    *) echo "usage: setup.sh [check|rpent|venv|checkpoint|freeze|all]" >&2; exit 64 ;;
esac
