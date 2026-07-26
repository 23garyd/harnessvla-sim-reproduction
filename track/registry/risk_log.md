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
