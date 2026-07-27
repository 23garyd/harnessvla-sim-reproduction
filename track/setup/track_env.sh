#!/usr/bin/env bash
# Canonical environment for every HarnessVLA sim-track run and queue.
# Source this file from bash; do not execute it. No run may depend on shell state
# beyond what is set here.
[ -n "${BASH_VERSION:-}" ] || { echo "FATAL: track_env.sh must be sourced by bash" >&2; return 1 2>/dev/null || exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # derived, never hardcoded

export CUDA_VISIBLE_DEVICES=0            # A6000 only; TITAN X never used
export PI05_CHECKPOINT_PATH="$REPO/checkpoints/rlinf-pi05-libero-130-fullshot-sft"
export SAM3_CHECKPOINT_PATH="$REPO/checkpoints/sam3/sam3.pt"
export LIBERO_TYPE=pro
export MUJOCO_GL=egl
