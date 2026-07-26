#!/usr/bin/env bash
# Verify (default) or record (--record) the RPent pin.
# Fails loudly on: missing clone, unset pin, HEAD drift, dirty worktree,
# malformed pins.env, unknown arguments.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PINS="$REPO/track/setup/pins.env"
RPENT="$REPO/RPent"

usage() { echo "usage: pin_check.sh [--record]" >&2; exit 64; }
case "${1:-}" in ""|--record) ;; *) usage ;; esac

[ -d "$RPENT/.git" ] || { echo "FATAL: $RPENT is not a git clone; run track/setup/setup.sh rpent" >&2; exit 1; }

dirty="$(git -C "$RPENT" status --porcelain)"

if [ "${1:-}" = "--record" ]; then
    [ -z "$dirty" ] || { echo "FATAL: refusing to record pin with dirty RPent worktree:" >&2; echo "$dirty" >&2; exit 1; }
    head="$(git -C "$RPENT" rev-parse HEAD)"
    printf '# Pinned upstream commits. Written by pin_check.sh --record; hand-edits are\n# a behavior-affecting change and require an experiment-registry entry.\nRPENT_COMMIT=%s\n' "$head" > "$PINS.tmp"
    mv "$PINS.tmp" "$PINS"
    echo "recorded RPENT_COMMIT=$head"
    exit 0
fi

# Parse, never source: pins.env content must not run as code.
RPENT_COMMIT="$(grep -E '^RPENT_COMMIT=' "$PINS" | tail -1 | cut -d= -f2 || true)"
[ -n "$RPENT_COMMIT" ] || { echo "FATAL: RPENT_COMMIT unset in pins.env; run pin_check.sh --record after review" >&2; exit 1; }
echo "$RPENT_COMMIT" | grep -qE '^[0-9a-f]{7,40}$' || { echo "FATAL: RPENT_COMMIT malformed in pins.env: '$RPENT_COMMIT'" >&2; exit 1; }
head="$(git -C "$RPENT" rev-parse HEAD)"
[ "$head" = "$RPENT_COMMIT" ] || { echo "FATAL: RPent HEAD $head != pinned $RPENT_COMMIT" >&2; exit 1; }
[ -z "$dirty" ] || { echo "FATAL: RPent worktree has unrecorded modifications:" >&2; echo "$dirty" >&2; exit 1; }
echo "pin check OK: RPent at $RPENT_COMMIT, worktree clean"
