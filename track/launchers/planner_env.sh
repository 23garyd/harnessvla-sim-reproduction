#!/usr/bin/env bash
# Source this from every launcher. run_planner strips billing keys so the
# claude_code planner bills only the claude.ai subscription and can never
# silently pick up ~/anthropic-api.txt (billing policy, HANDOVER.md).
[ -n "${BASH_VERSION:-}" ] || { echo "FATAL: planner_env.sh must be sourced by bash" >&2; return 1 2>/dev/null || exit 1; }
run_planner() {
    env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY "$@"
}
