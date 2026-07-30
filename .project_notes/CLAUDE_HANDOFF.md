# Claude handoff — HarnessVLA sim-reproduction track

Last updated: 2026-07-29 (end of plan Day 11)
Repo: `/home/demo/github_sow_harnessVLA` · remote `nuPylot/harnessvla-sim` (private)
HEAD: `16734c7` · tags `day2-install-smoke` → `day11-extension-matrix` (all pushed)

## 1. What this track is

Reproducing HarnessVLA (arXiv:2607.08448, RPent framework) on LIBERO-Pro:
does a **frozen** pi0.5 VLA become more useful when wrapped in a
memory-guided agent harness? Machine: asus / RTX A6000 (GPU 0).
Charter is **direction-not-magnitude** (paper-era planner unavailable).
Plan: `docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`.

## 2. Current status

**Days 1–11 complete.** Day-10 MVP frozen; Day-11 extension matrix
finished and pushed. 118 tests green. RPent pin clean. GPU idle.

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
`artifacts/ablation/ledger.csv` 5 rows. Artifacts 6.0 GB (cap 200 GB).

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
   Predeclared hidden-memory ablation on that cell: **5/5 vs 2/5**.
4. **Anchoring leaks evade grep audits** — the stale coordinate never
   enters an action; it biases estimator *selection* (`memory_audit.md` §7).
5. **Ablation-integrity findings**: shell-capable planners actively hunt
   for hidden memory (repo-wide `find`, read a stash back); HF cache
   `.lock`/`.metadata` leak strategy-bearing note filenames. Working
   countermeasure: opaque out-of-repo tar + `HF_HUB_OFFLINE=1` +
   per-seed leak tripwire.
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
- Git identity is now `23garyd` (+ `gh auth setup-git` credential
  helper). Commits before 2026-07-29 are authored `23garyd`.

## 5. Registry versions & manifests

| version | what |
|---|---|
| v1 | direct arm, 600-step benchmark horizon (`core_v1.json`) |
| v2 | harness arm, released one-shot regime: 1200-step guide budget, env backstop 1220, claude-opus-4-8, 60 turns, planner-timeout 1200 s, wall 2400 s (`harness_v2.json`) |
| v2-hiddenmem | predeclared Day-8 ablation, Object-S (`ablation_hiddenmem_v2.json`) |
| v3 | Day-11 extension, +4 suites completing the 4×2 family grid (`ext_v3_direct.json`, `ext_v3_harness.json`) |

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
  `planner_env.sh`, `run_ablation_hiddenmem.sh`
- Analysis: `track/analysis/{compare,build_ledger,schemas,manifests,disk_guard}.py`
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

# ablation (opaque stash + leak tripwire; optional seed args)
bash track/launchers/run_ablation_hiddenmem.sh [4 5]
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
5. Two **quarantined** ablation attempts kept as evidence, excluded from
   results: `artifacts/ablation/attempt1_condition_violated/`,
   `attempt2_seed4_condition_violated/`.
6. **History re-authored and republished (2026-07-29).** All 83 commits,
   all 9 tags (including the 4 annotated taggers) and the identity
   strings in this file were rewritten to `23garyd` via `git
   filter-repo` (`--mailmap` + `--replace-text`); the track was pushed
   to `github.com/23garyd/aspire-robot-stack` (private). The former
   `nuPylot/harnessvla-sim` remote is no longer configured locally —
   `garyd` is the only remote, and the two repos have diverged in both
   identity and history, so **which one is canonical is undecided**.
   Author/committer dates are unchanged and run provenance is
   unaffected (`run_meta.json` keys on `rpent_commit` +
   `checkpoint_sha256`, never this repo's SHAs), but **every commit SHA
   changed**, so the 10 in-repo SHA citations in `risk_log.md` (15, 18),
   `progress_log.md` (167, 168, 349, 350) and `day7_triage.md` (31, 34)
   are now dangling and still need remapping. Pre-rewrite history
   survives only in `/home/demo/harnessvla-prerewrite-20260729.bundle`
   (local, never pushed).
7. Upstream issue reports not yet filed (maintainer-gated path):
   reference absolutes act as confirmation anchors; `tall_item_first_
   basket_placement.md` bias note is **scene-inverted** for low-table
   Object-S; "do not cache absolutes" should extend to estimator
   selection; the two RPent robustness items.

## 10. Next steps

1. **Day 12 — memory ablation, paper zero-shot protocol.** Hide
   Task-Specific + Global Memory across the grid; **predeclare before
   results**: removing memory hurts *swap* cells more than
   *redirection* cells. Machinery exists and is hardened
   (`run_ablation_hiddenmem.sh`). Discriminating cells are goal/object/10
   **swap** vs goal/10 **task** — the two new short-horizon cells are at
   ceiling for both arms and will carry no signal. Add a pytest leakage
   check that greps planner transcripts for memory paths (plan asks for
   it explicitly).
2. **Day 13 — retry/staging ablation**: one `vla_act` attempt per contact
   phase, identical budgets/memory/checkpoint, plus a fairness audit note.
3. **Day 14 — planner variability/repeatability**: repeated runs on fixed
   cells; bounds the Object-S pilot-vs-matrix variance question and
   open issue #4.
4. **Days 15+** — fold extension + ablations into
   `reproduction_report.md`; keep `progress_log.md` per-day tables current.
