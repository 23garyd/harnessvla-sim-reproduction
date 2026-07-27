# Protocol-deviation table

Deviations from the paper's protocol (Appendix C) and the plan's design
reference. Every row must state what differs and why; reports cite this table.

| # | Item | Paper protocol | This track | Why | Recorded |
|---|---|---|---|---|---|
| 1 | Evaluation scale | 8 cells, 80 tasks, seeds s1–s10, 800 scored rollouts per condition | Core: 4 tasks, seeds s1–s5, ≥40 paired scored rollouts; extension up to ~240 | 20-day internship compute/time budget (plan section 2) | 2026-07-26 |
| 2 | Planner model | Paper-era Claude Code / Codex versions | claude_code planner via claude.ai subscription; pinned claude-opus-4-8, 60 turns (registry v2) | Paper-era planner versions unavailable; direction-not-magnitude comparison (plan risk "planner model drift") | 2026-07-27 |
| 3 | Step budgets across conditions | Baseline = continuous pi-RLinf under benchmark defaults; harness under its own released regime | Direct scored at 600 (benchmark horizon); harness scored under the released 1200-step one-shot guide budget (env backstop 1220) | Released guides reused unmodified (read-only rule); mentor-approved at the Day-5 freeze | 2026-07-27 |
| 4 | VLA primitive naming | Plan's nominal vocabulary names the VLA primitive `vla_act` | Repo registers `pi0_pick` (used) and `pi0_doubled` (unused) | Upstream naming; mapping documented in the Day-4 trace audits | 2026-07-27 |
