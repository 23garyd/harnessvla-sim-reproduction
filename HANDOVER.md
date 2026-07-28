# HarnessVLA track — handover (written 2026-07-26, on the robot PC; this folder lives on asus)

This folder is the dedicated home for the **HarnessVLA-paper track** (arXiv:2607.08448,
RPent). It was split on 2026-07-26 from the ASPIRE SOW folder on the robot PC
(`github_sow_2026_7`, the machine with the B601 arm + RTX 5090) so the two paths
can't mix. **This track runs on asus**; the ASPIRE/B601 real-robot track stays on
the robot PC.

## Why asus

The sim plan's own risk table flags Blackwell **sm_120** kernel incompatibility in
the pinned RLinf/OpenPI/LIBERO-PRO forks — that's the robot PC's RTX 5090. asus was
checked 2026-07-26 via `nvidia-smi`: **NVIDIA RTX A6000 (Ampere, sm_86) + TITAN X
(Pascal)**. Note: the A6000 is *not* an "RTX 6000 Ada", but sm_86 is well supported
by the pinned forks, so the rationale holds. Use the A6000; the TITAN X is too old
for this stack.

## Where the track stands (2026-07-28: Day-10 MVP FROZEN)

**The sim-reproduction core is complete and frozen.** Days 1–10 of the
sim plan executed 2026-07-26 → 07-28: environment installed and pinned,
40 paired scored rollouts (4 anchor cells × s1–s5, direct vs harness),
predeclared hidden-memory ablation, failure taxonomy, and the
reproduction report. Headline: direct 5/20 vs harness 11/20 (direction
reproduced); Goal-T gain not reproduced at our planner pin; Object-S
regressed 4/5→2/5 with a measured mechanism (reference-coordinate
anchoring; hidden-memory ablation 5/5). Start here:

- Report: `track/report/reproduction_report.md`
- Frozen state + provenance chain: `track/registry/mvp_freeze.md`
- Day-by-day trace with full results: `track/registry/progress_log.md`
- Repo: github.com/nuPylot/harnessvla-sim, tags through `day10-mvp-freeze`

Remaining plan-days (11–20) are extensions: more cells/seeds, the
swap-asymmetry memory ablation proper (Day 12), possible RPent pin bump
to c01b9cf (reviewed, not taken — day7_triage.md §7), robot-PC B602
path. Nothing in the frozen core may be re-run or re-scored.

*(Original 2026-07-26 status preserved below for history.)*

**Planning only — nothing built.** The two internship plans (prepared 22 Jul 2026)
are in `docs/`. No RPent, pi0.5, LeRobot, or ACT code exists yet for this track on
either PC.

Relationship to the ASPIRE track (decided 2026-07-26 after comparing the SOW docs
against the built work): both SOW plans are HarnessVLA-based, but the delivered
development work reproduces **ASPIRE** (LLM-written programs + trace-guided repair)
— a different paper sharing the same harness thesis. Decision: the SOW milestone
containers are treated as filled by the ASPIRE work (sim reproduction complete with
honest results; B601 software complete, live runs pending). **This track is the
higher-risk learned-policy path**, pursued independently on this machine.

## The two sub-plans (docs/)

1. `HarnessVLA_Simulation_Reproduction_Internship_Plan.docx` — reproduce HarnessVLA
   with released RPent + frozen pi0.5 on LIBERO-Pro. Day-10 core: 4 tasks × 5
   held-out seeds × {direct VLA, full harness} ≥ 40 paired rollouts + 1 ablation.
   **Runs entirely on asus.**
2. `B601_Harness_VLA_Internship_Plan.docx` — frozen ACT grasp primitive on the real
   B601-RS inside an observe/stage/grasp/verify/retry/memory loop. **The arm, CAN
   adapter, and D405 are on the robot PC** — ACT *training* can run here on the
   A6000, but data collection and all robot execution happen on the robot PC
   (or the arm must be physically moved — open decision, not yet made).

## Bench artifacts: single source of truth (safety-relevant)

Calibration, limits, and camera state belong to the **bench**, not to either paper.
Source of truth: robot PC, `~/github_sow_2026_7/aspire_robot_engine` (branch
`b601_live`, remote https://github.com/nuPylot/aspire_demo.git):
`robot_b601/hand_eye.json` (still an identity placeholder until the M3b live
calibration), `robot_b601/b601_rs_limits.json`, plus the M3a–M3b bring-up scripts.
Consume these by **pinned commit + hash**, never by copy-paste — a stale calibration
that moves a real arm is a safety problem.

## Next plan

**Sim track (start here, Days 1–3 of the sim plan):**
1. Clone RPent; `pip install -e ".[full]"` keeping the pyproject-pinned
   RLinf/OpenPI/LIBERO-PRO forks (do NOT upgrade robosuite or the forks).
2. Download the frozen checkpoint `RLinf/RLinf-Pi05-LIBERO-130-fullshot-SFT`
   (correction 2026-07-26: it is a HF *model* repo with this casing — the plan's
   `datasets/rlinf-pi05-libero-130-fullshot-sft` URL 404s); record checksum; set
   `PI05_CHECKPOINT_PATH`, `LIBERO_TYPE=pro`, `MUJOCO_GL=egl`.
3. Smoke-test `robots/libero/env_server.py` and `vla_server.py` independently on the
   A6000 (reset, render, one pi0.5 inference, one action chunk, clean shutdown).
4. Freeze 4 tasks (≥2 families, both T and S perturbations) + seeds s1–s5 (verify
   no init-state collision with seed 0), freeze the direct-baseline implementation,
   then run the Day-10 core matrix.

**B601/ACT track (intern, later):** Week 1 of its plan is substantially the
already-built ASPIRE M3a–M3b — run/validate those on the robot PC's bench first;
the genuinely new work is dataset collection + ACT training (Weeks 2–3). Its own
fallback for ACT < 70% ("analytic grasp") is exactly ASPIRE M3c, already built.

## Billing policy (inherited from the ASPIRE track, keep it)

Claude CLI work bills to the claude.ai subscription — strip `ANTHROPIC_API_KEY`
from any planner subprocess env (`env -u ANTHROPIC_API_KEY ...`). Note
`~/anthropic-api.txt` exists in this home dir — do not let the RPent planner
silently pick up an API key.
