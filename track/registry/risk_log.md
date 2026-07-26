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
