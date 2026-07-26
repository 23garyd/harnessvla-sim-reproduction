#!/usr/bin/env bash
# Regenerate track/setup/env_manifest.md (spec section 1). Run after any
# install change; commit the result.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
OUT="$REPO/track/setup/env_manifest.md"
PY="$REPO/.venv/bin/python"

{
    echo "# Environment manifest"
    echo
    echo "Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by \`track/setup/gen_env_manifest.sh\`."
    echo
    echo "## Host"
    echo "- OS: $(. /etc/os-release && echo "$PRETTY_NAME") ($(uname -r))"
    echo "- GPU 0: $(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader -i 0)"
    echo "- CUDA (driver): $(nvidia-smi | grep -o 'CUDA Version: [0-9.]*' | head -1)"
    echo "- Python: $("$PY" --version 2>&1)"
    echo
    echo "## Repos"
    echo "- track repo: $(git -C "$REPO" rev-parse HEAD)"
    echo "- RPent: $(git -C "$REPO/RPent" rev-parse HEAD) (https://github.com/RLinf/RPent, pinned in pins.env)"
    echo
    echo "## Key packages (full resolution: requirements.lock)"
    "$PY" -m pip list --format=freeze 2>/dev/null \
        | grep -iE '^(torch==|torchvision==|rlinf-|rpent|liberopro|robosuite|lerobot|mujoco==|jax)' \
        | sed 's/^/- /'
    echo "- lerobot origin: $("$PY" -c "
import json, importlib.metadata as m
p = [f for f in m.files('lerobot') if f.name == 'direct_url.json'][0]
d = json.loads(p.read_text())
print(d['url'] + '@' + d['vcs_info']['commit_id'])" 2>/dev/null || echo 'n/a')"
    echo
    echo "## Checkpoint"
    echo "- source: RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT (HF **model** repo; the internship plan's dataset URL is wrong)"
    echo "- local: checkpoints/rlinf-pi05-libero-130-fullshot-sft"
    echo "- sha256:"
    echo
    sed 's/^/    /' "$REPO/track/setup/checkpoint.sha256sums"
} > "$OUT"

echo "wrote $OUT"
