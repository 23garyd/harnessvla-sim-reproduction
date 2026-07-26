# Protocol-deviation table

Deviations from the paper's protocol (Appendix C) and the plan's design
reference. Every row must state what differs and why; reports cite this table.

| # | Item | Paper protocol | This track | Why | Recorded |
|---|---|---|---|---|---|
| 1 | Evaluation scale | 8 cells, 80 tasks, seeds s1–s10, 800 scored rollouts per condition | Core: 4 tasks, seeds s1–s5, ≥40 paired scored rollouts; extension up to ~240 | 20-day internship compute/time budget (plan section 2) | 2026-07-26 |
| 2 | Planner model | Paper-era Claude Code / Codex versions | claude_code planner via claude.ai subscription, current CLI model; exact model ID + settings pinned per experiment version at Day 3 | Paper-era planner versions unavailable; direction-not-magnitude comparison (plan risk "planner model drift") | 2026-07-26 |
