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
# NOTE: the internship plan cites huggingface.co/datasets/RLinf/rlinf-pi05-
# libero-130-fullshot-sft, but the checkpoint actually lives in a MODEL repo
# with this casing (verified 2026-07-26; the dataset URL 404s).
CKPT_REPO="RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT"
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
    # rlinf-openpi's real lerobot pin lives in a uv-only [tool.uv.sources]
    # table that pip ignores, so pip resolves a lerobot without the
    # lerobot.common namespace openpi imports (found Day 2). Install the
    # fork-pinned git rev; --no-deps so it cannot downgrade torch.
    GIT_LFS_SKIP_SMUDGE=1 "$REPO/.venv/bin/pip" install --no-deps \
        "lerobot @ git+https://github.com/huggingface/lerobot@0cf864870cf29f4738d3ade893e6fd13fbd7cdb5"
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
            --repo-type model --local-dir "$CKPT_DIR.partial"
        # Drop huggingface-cli's resume cache: its volatile lock/metadata files
        # must not end up in the recorded checksums.
        rm -rf "$CKPT_DIR.partial/.cache"
        mv "$CKPT_DIR.partial" "$CKPT_DIR"
    fi
    verify_checkpoint "$CKPT_DIR" "$SUMS"
}

fetch_sim_assets() {
    # LIBERO-PRO simulator assets are not shipped in the pip wheel — without
    # them env reset dies on missing scene XMLs (RPent README step 2).
    # Idempotent via --skip-existing.
    "$REPO/.venv/bin/liberopro-download-assets" --skip-existing
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
    assets)     fetch_sim_assets ;;
    checkpoint) fetch_checkpoint ;;
    freeze)     freeze_requirements ;;
    all)        assert_gpu; clone_rpent; make_venv; fetch_sim_assets; fetch_checkpoint ;;
    *) echo "usage: setup.sh [check|rpent|venv|assets|checkpoint|freeze|all]" >&2; exit 64 ;;
esac
