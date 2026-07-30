# Claude handoff — HarnessVLA sim-reproduction track

Last updated: 2026-07-29 (Day-12 machinery complete; queue not yet run)
Repo: `/home/demo/github_sow_harnessVLA` · canonical remote `garyd` →
`github.com/23garyd/harnessvla-robot-stack` (private). The old
`nuPylot/harnessvla-sim` is NOT configured here and holds the pre-rewrite
history (see §9.6). Tags `day2-install-smoke` → `day11-extension-matrix`.
Work in progress on branch `day12-memory-ablation` (unmerged, unpushed).

## 1. What this track is

Reproducing HarnessVLA (arXiv:2607.08448, RPent framework) on LIBERO-Pro:
does a **frozen** pi0.5 VLA become more useful when wrapped in a
memory-guided agent harness? Machine: asus / RTX A6000 (GPU 0).
Charter is **direction-not-magnitude** (paper-era planner unavailable).
Plan: `docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`.

## 2. Current status

**Days 1–11 complete. Day-12 machinery complete; the v4 queue has NOT
been run** (no GPU work today). 162 tests green (+1 skipped: the v4
leakage audit, which activates when v4 rows exist). RPent pin clean.
GPU idle.

Day-12 so far: predeclaration frozen and committed BEFORE any rollout
(gate commit `e6c253d`) — **do not rewrite history past it, the gate is
a timestamp claim**. Machinery built TDD on branch
`day12-memory-ablation`. The new leakage audit then found that 2 of the
5 ACCEPTED Day-8 ablation rows had the condition broken; they are
quarantined and the Day-8 result is restated 5/5 → **3/3 on clean
rows** across all 9 citing documents (§9.5).

Headline — **combined 8-cell matrix, 80 scored rollouts (40 pairs)**:

| cell | direct | harness | note |
|---|---|---|---|
| libero_spatial_task_t2 | 0/5 | **5/5** | core; full-amplitude rescue |
| libero_goal_swap_t2 | 0/5 | **3/5** | core |
| libero_goal_task_t2 | 1/5 | 1/5 | core; no gain (pi0 place reflex) |
| libero_object_swap_t2 | 4/5 | **2/5** | core; REGRESSION (anchoring) |
| libero_object_task_t2 | 5/5 | 5/5 | ext; both at ceiling |
| libero_spatial_swap_t2 | 5/5 | 5/5 | ext; both at ceiling |
| libero_10_task_t3 | 0/5 | 0/5 | ext; wall for both arms |
| libero_10_swap_t2 | 0/5 | **2/5** | ext; long-horizon rescue |
| **aggregate** | **15/40 [0.24,0.53]** | **23/40 [0.42,0.71]** | Wilson 95% |

Paired flips: 11 rescued / 3 regressed / 12 both-pass / 14 both-fail.
Ledger: `artifacts/ledger.csv` 87 rows (80 scored + 7 infra);
`artifacts/ablation/ledger.csv` 3 rows (was 5; see §9.5). Artifacts 6.0 GB (cap 200 GB).

## 3. Key findings so far

1. **Direction reproduced.** Gains concentrate where the perturbation
   breaks *perception* (spatial relocation, fixture swap); the harness
   has no lever where the perturbation lives inside the policy's motor
   program (goal_task: `pi0_pick` re-enacts the memorized base-task
   pick-AND-place, dumping the object; no grab-and-hold mode exists).
2. **Division of labor is visible in artifacts**: 10 of 11 core harness
   successes fired the predicate during an *analytic* primitive; median
   **1 pi0 call per success** vs direct's 120-chunk budget.
3. **Object-S regression mechanism = reference-coordinate anchoring**
   (Day-9 correction of the Day-8 story). Failing releases were
   +0.078–0.082 m off-center in x — outside the basket footprint —
   because planners chose the +x-biased perception estimate *because it
   matched the cached seed-0 absolute* (0.076, 0.231). Release **x**,
   not z, is the failure variable (s0 succeeded from z=0.367).
   Predeclared hidden-memory ablation on that cell: **3/3 vs 1/3** on
   clean rows (originally 5/5 vs 2/5; seeds 1–2 quarantined 2026-07-29
   by the Day-12 leakage audit for an HF-cache condition leak —
   direction unchanged, n reduced 5→3, mechanism unaffected).
4. **Anchoring leaks evade grep audits** — the stale coordinate never
   enters an action; it biases estimator *selection* (`memory_audit.md` §7).
5. **Ablation-integrity findings**: shell-capable planners actively hunt
   for hidden memory (repo-wide `find`, read a stash back); HF cache
   `.lock`/`.metadata` leak strategy-bearing note filenames. Working
   countermeasure: opaque out-of-repo tar + `HF_HUB_OFFLINE=1` +
   per-seed leak tripwire. **A narrow tripwire is worse than none you
   trust**: the Day-8 version grepped ONE hardcoded note name over 3 of
   5 artifact globs and passed 2 contaminated rows into the results,
   found only by the Day-12 audit (`leak_rules.py`: 199 patterns,
   condition-scoped, shared by tripwire and pytest).
6. Perturbation difficulty is **highly task-instance dependent** — both
   new short-horizon cells are at ceiling for both arms.

## 4. Standing decisions / invariants (do not violate)

- **Billing**: planner runs on the claude.ai subscription. Strip
  `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` from every planner subprocess
  (`run_planner` in `track/launchers/planner_env.sh`; guard-tested).
  `~/anthropic-api.txt`, `~/openai.txt` exist — never let them leak in.
  `~/huggingface.txt` only for scoped downloads.
- **RPent is read-only, pinned `6e4ba1805a459d74ad53569e833bae7ae2c59985`**;
  `track/setup/pin_check.sh` gates every launch. Upstream moved to
  `c01b9cf` (2 operational fixes + docs, released assets untouched) —
  **reviewed and deliberately NOT taken** for the core; candidate for
  extension only (`day7_triage.md` §7).
- **Scoring**: success only from the benchmark predicate
  (`libero_terminated`), cumulative. Planner self-reports never score.
  Every scored row is raw-verified.
- Seed 0 bootstraps memory and is **never scored**. Valid failures are
  never retried/deleted. Infra failures retry at cap 2. No retuning on
  evaluation seeds. Frozen core (v1/v2) is never re-run.
- **Planner session-limit rule**: ≤12 harness cells per session window;
  space windows ~3 h apart (learned the hard way, see §6).
- Git identity is `23garyd <76086658+23garyd@users.noreply.github.com>`
  (repo-local and global). The whole history was re-authored to it on
  2026-07-29 — see §9.6. Canonical remote is `garyd` →
  `github.com/23garyd/harnessvla-robot-stack` (private); push there.

## 5. Registry versions & manifests

| version | what |
|---|---|
| v1 | direct arm, 600-step benchmark horizon (`core_v1.json`) |
| v2 | harness arm, released one-shot regime: 1200-step guide budget, env backstop 1220, claude-opus-4-8, 60 turns, planner-timeout 1200 s, wall 2400 s (`harness_v2.json`) |
| v2-hiddenmem | predeclared Day-8 ablation, Object-S (`ablation_hiddenmem_v2.json`) |
| v3 | Day-11 extension, +4 suites completing the 4×2 family grid (`ext_v3_direct.json`, `ext_v3_harness.json`) |
| v4 | Day-12 memory ablation, paper Table-5 zero-shot: Global Memory + all four TSM dirs + HF cache hidden, harness only, 4 headroom cells × s1–s5, **no seed-0 bootstrap** (`ablation_zeroshot_v4.json`) — designed and predeclared, NOT yet queued |

Deviations (4 rows) in `track/registry/protocol_deviations.md`:
scale, planner pin, direct-600-vs-harness-1200 budget asymmetry,
`vla_act`→`pi0_pick` naming.

## 6. Bugs found & fixed (all committed)

Stack/setup: wrong checkpoint repo URL in the plan; LIBERO-PRO assets
missing from wheel; lerobot pin invisible to pip (uv-only sources);
HF cache polluting checksums; SAM3 wheel omits the CLIP BPE vocab;
**LIBERO-Pro ships an empty init-state file for `10_task` t2** (5th
missing-package-data bug → cell moved t2→t3).

Runtime: `stdin=DEVNULL` triggered `watch_parent_death` instant
shutdown (use `stdin=PIPE`); 15 reset settle steps consume robosuite's
horizon (env horizon = budget + 20); `pkill -f` self-match killed the
shell twice; SDK relative paths dirty RPent (`sweep_strays`).

Classification (Day 7): planner API errors (subscription session limit)
were mis-scored as valid failures — rpent exits 0 on planner
exceptions. Now: stream `AssistantMessage.error` →
`infra_failure/planner_api_error`; `{"type":"timeout"}` →
`budget_exhausted/planner_timeout`. 5 rows regenerated from raw
artifacts (originals kept as `result_row.json.orig`).

Day 11: `batch_runner` never passed each cell's source manifest to the
launchers (core worked only because its cells matched the launchers'
defaults) → cells now carry `manifest`; tests added.

## 7. Key files

- Report: `track/report/reproduction_report.md`
- Freeze + provenance chain: `track/registry/mvp_freeze.md`
- Findings: `track/registry/{day7_triage,day8_mechanism,day9_case_studies,day11_extension_design,memory_audit,baseline_design}.md`
- Registry/risks: `track/registry/{experiment_registry,risk_log,protocol_deviations,progress_log}.md`
  (`progress_log.md` carries **per-day result tables** — keep it that way)
- Launchers: `track/launchers/{run_direct,run_harness,batch_runner,direct_lib,harness_lib}.py`,
  `planner_env.sh`, `run_ablation_memory.sh` (+ `run_ablation_hiddenmem.sh`,
  now a thin wrapper — read its header, it hides MORE than the original
  v2-hiddenmem condition did)
- Analysis: `track/analysis/{compare,build_ledger,schemas,manifests,disk_guard,leak_rules}.py`
  (`leak_rules.py` = the ONE definition of a memory leak, shared by the
  queue tripwire and `test_ablation_leakage.py`; inventory in
  `track/registry/memory_inventory.txt`)
- Setup: `track/setup/{setup.sh,track_env.sh,pin_check.sh,pins.env,*.sha256sums,setup_notes.md}`
- Trace: `track/traces/day4_object_swap_t2_s0_annotated.md`

## 8. Commands that matter

```bash
source track/setup/track_env.sh          # every session, before any run
bash track/setup/pin_check.sh            # verify RPent pin + clean worktree
PYTHONPATH= .venv/bin/python -m pytest track/tests/ -q      # 118 tests
#   NOTE: the PYTHONPATH= prefix is REQUIRED (ROS Humble pollution)

# queue (resume-safe, raw-verifies every row; --dry-run to plan only)
PYTHONPATH= .venv/bin/python -m track.launchers.batch_runner \
  --manifests track/manifests/ext_v3_direct.json track/manifests/ext_v3_harness.json [--limit N]

# analysis
PYTHONPATH= .venv/bin/python -m track.analysis.compare --ledger artifacts/ledger.csv
PYTHONPATH= .venv/bin/python -m track.analysis.build_ledger --runs-root artifacts/runs --out artifacts/ledger.csv

# ablation — ALWAYS --dry-run first (verifies cells + what gets hidden,
# stashes nothing). v4 defaults; --limit N slices a planner window.
bash track/launchers/run_ablation_memory.sh --dry-run
bash track/launchers/run_ablation_memory.sh [--limit 12]
bash track/launchers/run_ablation_hiddenmem.sh --dry-run   # Day-8 manifest

# leak audit (same rules as the queue tripwire)
PYTHONPATH= .venv/bin/python -m track.analysis.leak_rules --scan <run_dir>
PYTHONPATH= .venv/bin/python -m track.analysis.leak_rules --record  # refresh inventory
```

## 9. Unresolved / open issues

1. **Env step-accounting mismatch**: 2 core runs died mid-episode with
   `executing action in terminated episode` at counted steps 654/804
   despite `--max-episode-steps 1220` — `states_used` under-counts real
   sim steps. Documented as a limitation; **not** changed mid-matrix.
2. **LIBERO-10 pressures the 1200 s planner timeout** (2 ext rows) —
   regime limitation to report, not retune.
3. **Direct arm records no trajectories** (by Day-3 design), so raw-policy
   placement behavior is not measurable. Optional fix: deterministic
   instrumented replay (pins + seed mapping make it exact).
4. **Goal-T non-reproduction may be pin-sensitive** — 2 of 9 core
   failures were plausibly convergent at the 60-turn cap. Day-14
   repeatability work should bound this.
5. **Three** quarantined ablation sets kept as evidence, excluded from
   results: `artifacts/ablation/attempt1_condition_violated/`,
   `attempt2_seed4_condition_violated/`, and (added 2026-07-29 by the
   Day-12 audit) `audit_quarantine_hfcache_seeds1_2/` — two originally
   ACCEPTED rows. Re-running those 2 seeds under the hardened condition
   to restore n=5 is a legitimate open option; not done.
6. **History re-authored and republished (2026-07-29).** All 83 commits,
   all 9 tags (including the 4 annotated taggers) and the identity
   strings in this file were rewritten to `23garyd` via `git
   filter-repo` (`--mailmap` + `--replace-text`); the track was pushed
   to `github.com/23garyd/harnessvla-robot-stack` (private), which is
   now **canonical**. The former `nuPylot/harnessvla-sim` remote is no
   longer configured locally — `garyd` is the only remote — so that
   mentor-facing repo still holds the pre-rewrite history and will
   diverge from this one until someone reconciles them.
   Author/committer dates are unchanged and run provenance is
   unaffected (`run_meta.json` keys on `rpent_commit` +
   `checkpoint_sha256`, never this repo's SHAs), but **every commit SHA
   changed**. The 5 affected in-repo commit citations were remapped:
   `2c49ac0`→`61c9524` (`risk_log.md` 18, `progress_log.md` 167,
   `day7_triage.md` 31) and `c9e00e5`→`d214888` (`progress_log.md` 168,
   `day7_triage.md` 34). NOT affected, despite looking like SHAs:
   `0cf8648` is the pinned lerobot fork rev, and `88450c6b…4bed905` /
   `9aa679f5…365a308` are ledger **sha256** checksums. Pre-rewrite
   history survives only in
   `/home/demo/harnessvla-prerewrite-20260729.bundle` (local, unpushed).
7. Upstream issue reports not yet filed (maintainer-gated path):
   reference absolutes act as confirmation anchors; `tall_item_first_
   basket_placement.md` bias note is **scene-inverted** for low-table
   Object-S; "do not cache absolutes" should extend to estimator
   selection; the two RPent robustness items.

## 10. Next steps

1. **Day 12 — remaining steps (design + machinery DONE).** Predeclaration
   frozen at `e6c253d`; manifest, launcher, leak rules and the leakage
   pytest are built and green on branch `day12-memory-ablation`. Left to do:
   (a) merge the branch and push; (b) **attended pilot, 1 cell / 1 seed** —
   verify the condition holds and that the tripwire + per-seed hygiene fire
   correctly; (c) queue the remaining 19 cells in **2 planner windows ≤12
   each, ≥3 h apart**; (d) analyse Δ_S vs Δ_T with Wilson CIs and paired
   flip counts, raw-verifying every row; (e) `progress_log.md` Day-12 result
   table. Note the Day-11 handoff claim that the ceiling cells "carry no
   signal" was **superseded** — for a drop-detecting ablation they are the
   highest-power cells and floor cells are the useless ones
   (`day12_ablation_design.md` §2).
   The Δ analysis needs a small `compare.py` addition for the paired
   per-side statistic; its shape depends on the terminal-reason mix in real
   v4 rows, so it is deliberately unwritten (see the plan's self-review).
2. **Day 13 — retry/staging ablation**: one `vla_act` attempt per contact
   phase, identical budgets/memory/checkpoint, plus a fairness audit note.
3. **Day 14 — planner variability/repeatability**: repeated runs on fixed
   cells; bounds the Object-S pilot-vs-matrix variance question and
   open issue #4.
4. **Days 15+** — fold extension + ablations into
   `reproduction_report.md`; keep `progress_log.md` per-day tables current.
