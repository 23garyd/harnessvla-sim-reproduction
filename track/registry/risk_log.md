# Risk log (live)

The full risk table with early warnings, required responses, and decision
days lives in the internship plan
(`docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`, section 8).
This file tracks risks as they materialize during execution, plus risks
pre-empted by a recorded decision. Status vocabulary: open | monitoring |
mitigated | closed | preempted.

| Date | Risk (plan §8 row or new) | What happened | Response taken | Status |
|---|---|---|---|---|
| 2026-07-26 | Checkpoint/GPU incompatibility | Pre-empted: track moved to asus (RTX A6000, sm_86) because the pinned forks lack Blackwell sm_120 kernels for the robot PC's RTX 5090 | Layout pins CUDA_VISIBLE_DEVICES=0 (A6000); setup.sh asserts the GPU name | preempted |
| 2026-07-26 | Checkpoint download failure (plan §8: stack installation) | Plan's HF URL 404s — checkpoint is the **model** repo `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT`, not a dataset | setup.sh corrected + HANDOVER note; downloaded, sha256 recorded | closed |
| 2026-07-26 | Missing simulator assets | LIBERO-PRO assets absent from the pip wheel; env.reset crashed on missing scene XML | `setup.sh assets` stage added (`liberopro-download-assets`, 865 files) | closed |
| 2026-07-26 | Stack installation failure (plan §8 row 1) | rlinf-openpi's lerobot pin lives in a uv-only `[tool.uv.sources]` table pip ignores → lerobot 0.3.3 resolved, vla_server crashed on import; naive `lerobot==0.1.0` downgrade dragged torch to 2.2.2 breaking the pinned stack | Stack restored via `RPent[full]` re-resolve; make_venv installs the fork-pinned lerobot git rev `0cf8648` with `--no-deps`; details in setup_notes.md | closed |
| 2026-07-26 | Server teardown SIGABRT | env_server and vla_server exit −6 after a clean `shutdown` RPC (EGL/CUDA teardown abort); functionally clean | Recorded in setup_notes.md; Day-6 batch runner must treat shutdown-ok + prompt exit as clean | monitoring |
| 2026-07-28 | Ablation-condition integrity (NEW): hidden-memory stash discovered by the planner | Day-8 ablation attempt 1: with `resources/libero/memory` missing, the planner ran a repo-wide Bash `find`, located the stash under `artifacts/ablation/stash/`, and read the memory notes + seed-0 reference from there — silently un-hiding the condition (seed 1 "success" contaminated; behavioral finding: the agent actively hunts for its memory) | Queue stopped at seed 2; memory restored, pin clean; attempt-1 runs quarantined (`artifacts/ablation/attempt1_condition_violated/INVALID.md`); script hardened — opaque tar stash outside the repo + post-run leak tripwire that aborts the queue on any stash/memory-filename reference | mitigated |
| 2026-07-28 | Planner availability (plan §8: planner model drift/access; NEW facet: subscription session limit) | The 2026-07-28 matrix queue exhausted the claude.ai session limit on its last 4 cells (object_swap harness s2 cut at turn 44; s3–s5 got "You've hit your session limit · resets 3:10am" before turn 1). rpent exits 0 on planner exceptions, so the rows were misclassified valid_failure and the cell read 0/5 — a fake "harness hurts the strong cell" inversion | Classifier fixed (planner stream AssistantMessage.error → infra_failure/planner_api_error, commit 2c49ac0); 4 rows reclassified from raw artifacts (originals preserved); cells re-queued under the infra-retry protocol. Scheduling rule going forward: budget ≤ ~15 harness cells per session window, or split queues across windows; check `claude` availability before an attended queue | mitigated |
