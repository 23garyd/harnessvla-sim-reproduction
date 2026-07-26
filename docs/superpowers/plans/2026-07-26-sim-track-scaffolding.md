# HarnessVLA Sim-Track Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the track scaffolding defined by `docs/superpowers/specs/2026-07-26-sim-track-architecture-design.md`: directory layout, env/setup/pin scripts, key-hygiene launcher lib, run-record schemas, ledger builder, disk guard, manifest validator, and registry files.

**Architecture:** A single git repo (`github_sow_harnessVLA`) is the unit of reproduction. Bash scripts under `track/setup/` handle environment/pinning; Python modules under `track/analysis/` validate run records and derive the ledger; everything is covered by pytest in `track/tests/` (bash scripts tested via subprocess). RPent, checkpoints, artifacts, and venvs are gitignored.

**Tech Stack:** Bash, Python 3.10 (stdlib only), pytest (in a gitignored `.venv-dev`).

**Conventions used throughout:**
- `REPO` = `/home/demo/github_sow_harnessVLA` (scripts derive it from their own location; tests override via the `TRACK_REPO` env var).
- Run all commands from the repo root.
- Test command: `PYTHONPATH= .venv-dev/bin/python -m pytest track/tests -v` (running via `python -m` puts the repo root on `sys.path`, so `track.analysis.*` imports resolve). The `PYTHONPATH=` prefix is required on this machine: the shell profile injects ROS Humble site-packages, whose `launch_testing` pytest plugin aborts collection. Apply the same prefix wherever a task step says to run pytest.

---

### Task 1: Repo skeleton, dev test venv, Python packages

**Files:**
- Create: `track/launchers/.gitkeep`, `track/manifests/.gitkeep`, `track/registry/.gitkeep`, `track/setup/.gitkeep`
- Create: `track/__init__.py`, `track/analysis/__init__.py`, `track/tests/__init__.py`, `track/tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create directories and package markers**

```bash
mkdir -p track/launchers track/manifests track/analysis track/registry track/setup track/tests
touch track/launchers/.gitkeep track/manifests/.gitkeep track/registry/.gitkeep track/setup/.gitkeep
touch track/__init__.py track/analysis/__init__.py track/tests/__init__.py
```

- [ ] **Step 2: Extend .gitignore**

Replace the contents of `.gitignore` with:

```gitignore
RPent/
checkpoints/
artifacts/
.venv/
.venv-dev/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Create the dev test venv**

```bash
python3 -m venv .venv-dev
.venv-dev/bin/pip install --quiet --upgrade pip
.venv-dev/bin/pip install --quiet pytest
.venv-dev/bin/python -m pytest --version
```

Expected: pytest version line prints (any pytest ≥ 7 is fine).

- [ ] **Step 4: Write `track/tests/conftest.py`**

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


@pytest.fixture
def bash():
    """Run a bash snippet; returns CompletedProcess with .stdout/.stderr/.returncode."""

    def run(script, env=None, cwd=None):
        merged = dict(os.environ)
        merged.update(env or {})
        return subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env=merged,
            cwd=cwd,
        )

    return run
```

- [ ] **Step 5: Verify pytest collects nothing but runs**

Run: `.venv-dev/bin/python -m pytest track/tests -v`
Expected: `no tests ran` (exit code 5 is fine at this stage).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: track skeleton, dev test venv, python package markers"
```

---

### Task 2: `track_env.sh` — canonical run environment

**Files:**
- Create: `track/setup/track_env.sh`
- Test: `track/tests/test_track_env.py`

- [ ] **Step 1: Write the failing test**

Create `track/tests/test_track_env.py`:

```python
from .conftest import REPO

ENV = REPO / "track" / "setup" / "track_env.sh"


def test_track_env_exports(bash):
    r = bash(
        f'source "{ENV}" && '
        'echo "$CUDA_VISIBLE_DEVICES|$LIBERO_TYPE|$MUJOCO_GL|$PI05_CHECKPOINT_PATH"'
    )
    assert r.returncode == 0, r.stderr
    cuda, libero, mujoco, ckpt = r.stdout.strip().split("|")
    assert cuda == "0"
    assert libero == "pro"
    assert mujoco == "egl"
    assert ckpt == str(REPO / "checkpoints" / "rlinf-pi05-libero-130-fullshot-sft")


def test_track_env_repo_derived_from_location(bash):
    # REPO must come from the file's own location, not the caller's cwd.
    r = bash(f'cd /tmp && source "{ENV}" && echo "$PI05_CHECKPOINT_PATH"')
    assert r.stdout.strip().startswith(str(REPO)), r.stdout


def test_track_env_fails_loudly_under_non_bash(bash):
    # dash has no BASH_SOURCE; without the guard it would silently set REPO=/.
    r = bash(f'sh -c \'. "{ENV}" && echo "$PI05_CHECKPOINT_PATH"\'')
    assert "FATAL" in r.stderr
    assert "//checkpoints" not in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv-dev/bin/python -m pytest track/tests/test_track_env.py -v`
Expected: FAIL (file `track_env.sh` does not exist; `source` returns non-zero).

- [ ] **Step 3: Write `track/setup/track_env.sh`**

```bash
#!/usr/bin/env bash
# Canonical environment for every HarnessVLA sim-track run and queue.
# Source this file from bash; do not execute it. No run may depend on shell
# state beyond what is set here.
[ -n "${BASH_VERSION:-}" ] || { echo "FATAL: track_env.sh must be sourced by bash" >&2; return 1 2>/dev/null || exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # derived, never hardcoded

export CUDA_VISIBLE_DEVICES=0            # A6000 only; TITAN X never used
export PI05_CHECKPOINT_PATH="$REPO/checkpoints/rlinf-pi05-libero-130-fullshot-sft"
export LIBERO_TYPE=pro
export MUJOCO_GL=egl
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv-dev/bin/python -m pytest track/tests/test_track_env.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add track/setup/track_env.sh track/tests/test_track_env.py
git commit -m "feat: canonical track_env.sh sourced by all launchers and queues"
```

---

### Task 3: `pins.env` + `pin_check.sh` — RPent pin verify/record

**Files:**
- Create: `track/setup/pins.env`
- Create: `track/setup/pin_check.sh`
- Test: `track/tests/test_pin_check.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_pin_check.py`:

```python
import shutil
import subprocess

from .conftest import REPO

PIN = REPO / "track" / "setup" / "pin_check.sh"


def git(*args, cwd):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )


def make_track_repo(tmp_path):
    """Fake track repo: track/setup/{pin_check.sh,pins.env} + RPent git clone."""
    setup = tmp_path / "track" / "setup"
    setup.mkdir(parents=True)
    shutil.copy(PIN, setup / "pin_check.sh")
    (setup / "pins.env").write_text("RPENT_COMMIT=\n")
    rpent = tmp_path / "RPent"
    rpent.mkdir()
    git("init", cwd=rpent)
    (rpent / "a.txt").write_text("one\n")
    git("add", "-A", cwd=rpent)
    git("commit", "-m", "c1", cwd=rpent)
    return tmp_path


def run_pin(bash, root, *args):
    argv = " ".join(args)
    return bash(f'"{root}/track/setup/pin_check.sh" {argv}',
                env={"TRACK_REPO": str(root)})


def test_check_fails_when_pin_unset(bash, tmp_path):
    root = make_track_repo(tmp_path)
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "RPENT_COMMIT unset" in r.stderr


def test_record_then_check_ok(bash, tmp_path):
    root = make_track_repo(tmp_path)
    assert run_pin(bash, root, "--record").returncode == 0
    r = run_pin(bash, root)
    assert r.returncode == 0, r.stderr
    assert "pin check OK" in r.stdout


def test_record_refuses_dirty_worktree(bash, tmp_path):
    root = make_track_repo(tmp_path)
    (root / "RPent" / "a.txt").write_text("edited\n")
    r = run_pin(bash, root, "--record")
    assert r.returncode != 0
    assert "dirty" in r.stderr


def test_check_fails_on_drift(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    (root / "RPent" / "b.txt").write_text("two\n")
    git("add", "-A", cwd=root / "RPent")
    git("commit", "-m", "c2", cwd=root / "RPent")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "!=" in r.stderr


def test_check_fails_on_unrecorded_modification(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    (root / "RPent" / "a.txt").write_text("silent edit\n")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "unrecorded" in r.stderr


def test_check_fails_when_rpent_missing(bash, tmp_path):
    root = make_track_repo(tmp_path)
    shutil.rmtree(root / "RPent")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "not a git clone" in r.stderr


def test_unknown_argument_fails(bash, tmp_path):
    root = make_track_repo(tmp_path)
    r = run_pin(bash, root, "--recrod")
    assert r.returncode == 64
    assert "usage:" in r.stderr


def test_pins_env_is_parsed_not_executed(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    marker = root / "pwned"
    pins = root / "track" / "setup" / "pins.env"
    pins.write_text(f'touch "{marker}"\n' + pins.read_text())
    r = run_pin(bash, root)
    assert not marker.exists()
    assert r.returncode == 0, r.stderr


def test_malformed_pin_fails(bash, tmp_path):
    root = make_track_repo(tmp_path)
    pins = root / "track" / "setup" / "pins.env"
    pins.write_text("RPENT_COMMIT=not-a-sha\n")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "malformed" in r.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_pin_check.py -v`
Expected: FAIL/ERROR on all 9 (pin_check.sh missing → `shutil.copy` FileNotFoundError).

- [ ] **Step 3: Write `track/setup/pins.env`**

```bash
# Pinned upstream commits. Written by pin_check.sh --record; hand-edits are
# a behavior-affecting change and require an experiment-registry entry.
RPENT_COMMIT=
```

- [ ] **Step 4: Write `track/setup/pin_check.sh`**

```bash
#!/usr/bin/env bash
# Verify (default) or record (--record) the RPent pin.
# Fails loudly on: missing clone, unset pin, HEAD drift, dirty worktree,
# malformed pins.env, unknown arguments.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PINS="$REPO/track/setup/pins.env"
RPENT="$REPO/RPent"

usage() { echo "usage: pin_check.sh [--record]" >&2; exit 64; }
case "${1:-}" in ""|--record) ;; *) usage ;; esac

[ -d "$RPENT/.git" ] || { echo "FATAL: $RPENT is not a git clone; run track/setup/setup.sh rpent" >&2; exit 1; }

dirty="$(git -C "$RPENT" status --porcelain)"

if [ "${1:-}" = "--record" ]; then
    [ -z "$dirty" ] || { echo "FATAL: refusing to record pin with dirty RPent worktree:" >&2; echo "$dirty" >&2; exit 1; }
    head="$(git -C "$RPENT" rev-parse HEAD)"
    printf '# Pinned upstream commits. Written by pin_check.sh --record; hand-edits are\n# a behavior-affecting change and require an experiment-registry entry.\nRPENT_COMMIT=%s\n' "$head" > "$PINS.tmp"
    mv "$PINS.tmp" "$PINS"
    echo "recorded RPENT_COMMIT=$head"
    exit 0
fi

# Parse, never source: pins.env content must not run as code.
RPENT_COMMIT="$(grep -E '^RPENT_COMMIT=' "$PINS" | tail -1 | cut -d= -f2 || true)"
[ -n "$RPENT_COMMIT" ] || { echo "FATAL: RPENT_COMMIT unset in pins.env; run pin_check.sh --record after review" >&2; exit 1; }
echo "$RPENT_COMMIT" | grep -qE '^[0-9a-f]{7,40}$' || { echo "FATAL: RPENT_COMMIT malformed in pins.env: '$RPENT_COMMIT'" >&2; exit 1; }
head="$(git -C "$RPENT" rev-parse HEAD)"
[ "$head" = "$RPENT_COMMIT" ] || { echo "FATAL: RPent HEAD $head != pinned $RPENT_COMMIT" >&2; exit 1; }
[ -z "$dirty" ] || { echo "FATAL: RPent worktree has unrecorded modifications:" >&2; echo "$dirty" >&2; exit 1; }
echo "pin check OK: RPent at $RPENT_COMMIT, worktree clean"
```

Then: `chmod +x track/setup/pin_check.sh`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_pin_check.py -v`
Expected: 9 PASS

- [ ] **Step 6: Commit**

```bash
git add track/setup/pins.env track/setup/pin_check.sh track/tests/test_pin_check.py
git commit -m "feat: RPent pin record/verify with dirty-worktree detection"
```

---

### Task 4: `planner_env.sh` — key-hygiene launcher lib + repo-wide hygiene test

**Files:**
- Create: `track/launchers/planner_env.sh`
- Test: `track/tests/test_key_hygiene.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_key_hygiene.py`:

```python
from .conftest import REPO

LAUNCHERS = REPO / "track" / "launchers"
LIB = LAUNCHERS / "planner_env.sh"


def test_run_planner_strips_billing_keys(bash):
    r = bash(
        f'source "{LIB}" && '
        'ANTHROPIC_API_KEY=leak1 OPENAI_API_KEY=leak2 '
        'run_planner bash -c '
        '\'echo "${ANTHROPIC_API_KEY:-UNSET}:${OPENAI_API_KEY:-UNSET}"\''
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "UNSET:UNSET"


def test_run_planner_passes_through_other_env(bash):
    r = bash(
        f'source "{LIB}" && '
        "LIBERO_TYPE=pro run_planner bash -c 'echo $LIBERO_TYPE'"
    )
    assert r.stdout.strip() == "pro"


def test_every_launcher_uses_run_planner():
    """Any launcher that invokes rpent or a claude CLI must go through
    run_planner (the env -u strip). Guards future launchers."""
    offenders = []
    for sh in LAUNCHERS.glob("*.sh"):
        if sh.name == "planner_env.sh":
            continue
        text = sh.read_text()
        if ("rpent" in text or "claude" in text) and "run_planner" not in text:
            offenders.append(sh.name)
    assert offenders == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_key_hygiene.py -v`
Expected: first two FAIL (planner_env.sh missing); third PASSES vacuously (no launchers yet) — that is expected.

- [ ] **Step 3: Write `track/launchers/planner_env.sh`**

```bash
#!/usr/bin/env bash
# Source this from every launcher. run_planner strips billing keys so the
# claude_code planner bills only the claude.ai subscription and can never
# silently pick up ~/anthropic-api.txt (billing policy, HANDOVER.md).
[ -n "${BASH_VERSION:-}" ] || { echo "FATAL: planner_env.sh must be sourced by bash" >&2; return 1 2>/dev/null || exit 1; }
run_planner() {
    env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY "$@"
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_key_hygiene.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add track/launchers/planner_env.sh track/tests/test_key_hygiene.py
git commit -m "feat: run_planner key-strip lib + repo-wide launcher hygiene test"
```

---

### Task 5: `schemas.py` — run_meta / result_row validation

**Files:**
- Create: `track/analysis/schemas.py`
- Test: `track/tests/test_schemas.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_schemas.py`:

```python
import pytest

from track.analysis import schemas


def valid_meta():
    return {
        "exp_version": "v1",
        "condition": "direct",
        "task": "task_a",
        "suite": "libero_goal_task",
        "seed": 1,
        "planner_model": "claude_code/claude-fable-5",
        "planner_settings": {"max_turns": 40},
        "prompt_hashes": {"system.py": "abc123"},
        "rpent_commit": "deadbeef",
        "checkpoint_sha256": "cafe01",
        "budgets": {"max_steps": 400, "max_turns": 40, "max_wall_seconds": 1800},
        "launch_command": "rpent --env libero ...",
    }


def valid_row():
    return {
        "success": True,
        "terminal_reason": "benchmark_predicate",
        "validity": "success",
        "counts": {"steps": 120, "turns": 9, "vla_act_calls": 2, "analytic_calls": 6},
        "wall_seconds": 301.5,
    }


def test_valid_meta_passes():
    schemas.validate_run_meta(valid_meta())


def test_meta_missing_key_fails():
    m = valid_meta()
    del m["rpent_commit"]
    with pytest.raises(ValueError, match="rpent_commit"):
        schemas.validate_run_meta(m)


def test_meta_missing_budget_key_fails():
    m = valid_meta()
    del m["budgets"]["max_turns"]
    with pytest.raises(ValueError, match="max_turns"):
        schemas.validate_run_meta(m)


def test_meta_wrong_type_fails():
    m = valid_meta()
    m["seed"] = "1"
    with pytest.raises(ValueError, match="seed"):
        schemas.validate_run_meta(m)


def test_valid_row_passes():
    schemas.validate_result_row(valid_row())


def test_unknown_validity_fails():
    r = valid_row()
    r["validity"] = "kinda_worked"
    with pytest.raises(ValueError, match="validity"):
        schemas.validate_result_row(r)


def test_success_flag_must_match_validity():
    r = valid_row()
    r["validity"] = "timeout"        # success is still True -> inconsistent
    with pytest.raises(ValueError, match="success"):
        schemas.validate_result_row(r)


def test_infra_failure_requires_evidence():
    r = valid_row()
    r["success"] = False
    r["validity"] = "infra_failure"
    with pytest.raises(ValueError, match="evidence"):
        schemas.validate_result_row(r)
    r["evidence"] = "env_server crashed: see server.log line 812"
    schemas.validate_result_row(r)


def test_missing_count_fails():
    r = valid_row()
    del r["counts"]["vla_act_calls"]
    with pytest.raises(ValueError, match="vla_act_calls"):
        schemas.validate_result_row(r)


def test_valid_failure_row_passes():
    r = valid_row()
    r["success"] = False
    r["validity"] = "valid_failure"
    schemas.validate_result_row(r)


def test_budget_exhausted_row_passes():
    r = valid_row()
    r["success"] = False
    r["validity"] = "budget_exhausted"
    r["terminal_reason"] = "step_budget"
    schemas.validate_result_row(r)


def test_result_row_wrong_type_fails():
    r = valid_row()
    r["success"] = "yes"
    with pytest.raises(ValueError, match="success"):
        schemas.validate_result_row(r)


def test_negative_count_fails():
    r = valid_row()
    r["counts"]["steps"] = -5
    with pytest.raises(ValueError, match="steps"):
        schemas.validate_result_row(r)


def test_non_finite_wall_seconds_fails():
    r = valid_row()
    r["wall_seconds"] = float("nan")
    with pytest.raises(ValueError, match="wall_seconds"):
        schemas.validate_result_row(r)
    r["wall_seconds"] = -1.0
    with pytest.raises(ValueError, match="wall_seconds"):
        schemas.validate_result_row(r)


def test_extra_keys_allowed():
    m = valid_meta()
    m["notes"] = "anything"
    schemas.validate_run_meta(m)
    r = valid_row()
    r["evidence"] = "harmless on non-infra rows"
    schemas.validate_result_row(r)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_schemas.py -v`
Expected: ERROR — `ModuleNotFoundError: track.analysis.schemas`.

- [ ] **Step 3: Write `track/analysis/schemas.py`**

```python
"""Validation for the two track-added run records (spec section 3).

run_meta.json  - written at launch, immutable.
result_row.json - written at termination; the only input to the ledger.
Extra/unknown keys are intentionally permitted (forward compatibility).
"""
import math

VALIDITY_STATUSES = {
    "success",
    "valid_failure",
    "infra_failure",
    "timeout",
    "budget_exhausted",
}

_RUN_META_REQUIRED = {
    "exp_version": str,
    "condition": str,
    "task": str,
    "suite": str,
    "seed": int,
    "planner_model": str,
    "planner_settings": dict,
    "prompt_hashes": dict,
    "rpent_commit": str,
    "checkpoint_sha256": str,
    "budgets": dict,
    "launch_command": str,
}

_BUDGETS_REQUIRED = {
    "max_steps": int,
    "max_turns": int,
    "max_wall_seconds": int,
}

_RESULT_ROW_REQUIRED = {
    "success": bool,
    "terminal_reason": str,
    "validity": str,
    "counts": dict,
    "wall_seconds": (int, float),
}

_COUNTS_REQUIRED = {
    "steps": int,
    "turns": int,
    "vla_act_calls": int,
    "analytic_calls": int,
}


def _require(record, spec, where):
    if not isinstance(record, dict):
        raise ValueError(f"{where}: expected dict, got {type(record).__name__}")
    for key, typ in spec.items():
        if key not in record:
            raise ValueError(f"{where}: missing required key '{key}'")
        if not isinstance(record[key], typ) or (
            typ is int and isinstance(record[key], bool)
        ):
            raise ValueError(
                f"{where}: key '{key}' must be {typ}, "
                f"got {type(record[key]).__name__}"
            )


def validate_run_meta(meta):
    _require(meta, _RUN_META_REQUIRED, "run_meta")
    _require(meta["budgets"], _BUDGETS_REQUIRED, "run_meta.budgets")
    return meta


def validate_result_row(row):
    _require(row, _RESULT_ROW_REQUIRED, "result_row")
    _require(row["counts"], _COUNTS_REQUIRED, "result_row.counts")
    for key in _COUNTS_REQUIRED:
        if row["counts"][key] < 0:
            raise ValueError(
                f"result_row.counts: key '{key}' must be >= 0, "
                f"got {row['counts'][key]}"
            )
    ws = row["wall_seconds"]
    if isinstance(ws, bool) or not math.isfinite(ws) or ws < 0:
        raise ValueError(
            f"result_row: wall_seconds must be a finite number >= 0, got {ws!r}"
        )
    if row["validity"] not in VALIDITY_STATUSES:
        raise ValueError(
            f"result_row: unknown validity '{row['validity']}', "
            f"expected one of {sorted(VALIDITY_STATUSES)}"
        )
    if row["success"] != (row["validity"] == "success"):
        raise ValueError(
            "result_row: success flag inconsistent with validity "
            f"(success={row['success']}, validity='{row['validity']}')"
        )
    if row["validity"] == "infra_failure":
        evidence = row.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(
                "result_row: infra_failure requires non-empty 'evidence' "
                "(crash log, missing artifact, corrupted render, ...)"
            )
    return row
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_schemas.py -v`
Expected: 15 PASS

- [ ] **Step 5: Commit**

```bash
git add track/analysis/schemas.py track/tests/test_schemas.py
git commit -m "feat: run_meta/result_row schemas with validity vocabulary"
```

---

### Task 6: `build_ledger.py` — derived ledger, seed-0 exclusion

**Files:**
- Create: `track/analysis/build_ledger.py`
- Test: `track/tests/test_build_ledger.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_build_ledger.py`:

```python
import csv
import json

import pytest

from track.analysis import build_ledger


def write_run(root, *, exp="v1", cond="direct", task="task_a",
              suite="libero_goal_task", seed=1, ts="20260726T000000",
              success=True, validity="success", evidence=None,
              with_result=True):
    d = root / exp / cond / task / str(seed) / ts
    d.mkdir(parents=True)
    meta = {
        "exp_version": exp, "condition": cond, "task": task, "suite": suite,
        "seed": seed,
        "planner_model": "claude_code/claude-fable-5",
        "planner_settings": {"max_turns": 40},
        "prompt_hashes": {"system.py": "abc123"},
        "rpent_commit": "deadbeef", "checkpoint_sha256": "cafe01",
        "budgets": {"max_steps": 400, "max_turns": 40, "max_wall_seconds": 1800},
        "launch_command": "rpent ...",
    }
    (d / "run_meta.json").write_text(json.dumps(meta))
    if with_result:
        row = {
            "success": success, "terminal_reason": "benchmark_predicate",
            "validity": validity,
            "counts": {"steps": 120, "turns": 9, "vla_act_calls": 2,
                       "analytic_calls": 6},
            "wall_seconds": 301.5,
        }
        if evidence is not None:
            row["evidence"] = evidence
        (d / "result_row.json").write_text(json.dumps(row))
    return d


def test_valid_run_appears_in_ledger(tmp_path):
    write_run(tmp_path)
    rows, skipped_seed0, incomplete = build_ledger.build_ledger(tmp_path)
    assert len(rows) == 1
    assert skipped_seed0 == 0 and incomplete == 0
    assert rows[0]["task"] == "task_a"
    assert rows[0]["success"] is True
    assert rows[0]["run_id"] == "20260726T000000"


def test_seed_zero_never_scored(tmp_path):
    write_run(tmp_path, seed=0, ts="20260726T000001")
    write_run(tmp_path, seed=1, ts="20260726T000002")
    rows, skipped_seed0, _ = build_ledger.build_ledger(tmp_path)
    assert [r["seed"] for r in rows] == [1]
    assert skipped_seed0 == 1


def test_incomplete_run_skipped_and_counted(tmp_path):
    write_run(tmp_path, with_result=False)
    rows, _, incomplete = build_ledger.build_ledger(tmp_path)
    assert rows == [] and incomplete == 1


def test_invalid_row_raises(tmp_path):
    write_run(tmp_path, success=False, validity="infra_failure")  # no evidence
    with pytest.raises(ValueError, match="evidence"):
        build_ledger.build_ledger(tmp_path)


def test_write_csv_round_trip(tmp_path):
    write_run(tmp_path)
    rows, _, _ = build_ledger.build_ledger(tmp_path)
    out = tmp_path / "ledger.csv"
    build_ledger.write_csv(rows, out)
    with open(out) as f:
        got = list(csv.DictReader(f))
    assert len(got) == 1
    assert got[0]["validity"] == "success"
    assert got[0]["steps"] == "120"


def test_rows_sorted_deterministically(tmp_path):
    write_run(tmp_path, task="task_b", ts="20260726T000003")
    write_run(tmp_path, task="task_a", ts="20260726T000004")
    rows, _, _ = build_ledger.build_ledger(tmp_path)
    assert [r["task"] for r in rows] == ["task_a", "task_b"]


def test_meta_path_mismatch_raises(tmp_path):
    d = write_run(tmp_path, seed=1)
    meta = json.loads((d / "run_meta.json").read_text())
    meta["seed"] = 2
    (d / "run_meta.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError) as exc:
        build_ledger.build_ledger(tmp_path)
    assert "disagrees" in str(exc.value)


def test_validation_error_names_run_dir(tmp_path):
    d = write_run(tmp_path, success=False, validity="infra_failure")
    with pytest.raises(ValueError) as exc:
        build_ledger.build_ledger(tmp_path)
    assert str(d) in str(exc.value)
    assert "evidence" in str(exc.value)


def test_malformed_json_names_run_dir(tmp_path):
    d = write_run(tmp_path)
    (d / "run_meta.json").write_text("{not json")
    with pytest.raises(ValueError) as exc:
        build_ledger.build_ledger(tmp_path)
    assert str(d) in str(exc.value)


def test_success_written_as_int(tmp_path):
    write_run(tmp_path, success=False, validity="valid_failure")
    rows, _, _ = build_ledger.build_ledger(tmp_path)
    out = tmp_path / "ledger.csv"
    build_ledger.write_csv(rows, out)
    with open(out) as f:
        got = list(csv.DictReader(f))
    assert got[0]["success"] == "0"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_build_ledger.py -v`
Expected: ERROR — `ModuleNotFoundError: track.analysis.build_ledger`.

- [ ] **Step 3: Write `track/analysis/build_ledger.py`**

```python
"""Derive ledger.csv from artifacts/runs/. The ledger is never hand-edited;
any reported number must reproduce from a clean rebuild (spec section 3).

Run-directory contract: <runs_root>/<exp_version>/<condition>/<task>/<seed>/<ts>/
containing run_meta.json (launch, immutable) and result_row.json (termination).
Seed-0 rows are bootstrap-only and are never scored.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from track.analysis.schemas import validate_result_row, validate_run_meta

LEDGER_COLUMNS = [
    "exp_version", "condition", "suite", "task", "seed", "run_id",
    "success", "validity", "terminal_reason",
    "steps", "turns", "vla_act_calls", "analytic_calls", "wall_seconds",
    "planner_model", "rpent_commit", "checkpoint_sha256", "run_dir",
]


def iter_run_dirs(runs_root):
    """Yield every directory that contains a run_meta.json."""
    for meta_path in sorted(Path(runs_root).glob("*/*/*/*/*/run_meta.json")):
        yield meta_path.parent


def load_row(run_dir):
    meta = validate_run_meta(
        json.loads((run_dir / "run_meta.json").read_text()))
    result = validate_result_row(
        json.loads((run_dir / "result_row.json").read_text()))
    path_ids = tuple(run_dir.parts[-5:-1])
    meta_ids = (meta["exp_version"], meta["condition"], meta["task"], str(meta["seed"]))
    if path_ids != meta_ids:
        raise ValueError(
            f"path (exp_version, condition, task, seed)={path_ids} "
            f"disagrees with run_meta {meta_ids}"
        )
    return {
        "exp_version": meta["exp_version"],
        "condition": meta["condition"],
        "suite": meta["suite"],
        "task": meta["task"],
        "seed": meta["seed"],
        "run_id": run_dir.name,
        "success": result["success"],
        "validity": result["validity"],
        "terminal_reason": result["terminal_reason"],
        "steps": result["counts"]["steps"],
        "turns": result["counts"]["turns"],
        "vla_act_calls": result["counts"]["vla_act_calls"],
        "analytic_calls": result["counts"]["analytic_calls"],
        "wall_seconds": result["wall_seconds"],
        "planner_model": meta["planner_model"],
        "rpent_commit": meta["rpent_commit"],
        "checkpoint_sha256": meta["checkpoint_sha256"],
        "run_dir": str(run_dir),
    }


def build_ledger(runs_root):
    """Return (rows, skipped_seed0, incomplete). Raises on any invalid record."""
    rows, skipped_seed0, incomplete = [], 0, 0
    for run_dir in iter_run_dirs(runs_root):
        if not (run_dir / "result_row.json").exists():
            incomplete += 1
            continue
        try:
            row = load_row(run_dir)
        except ValueError as e:
            raise ValueError(f"{run_dir}: {e}") from e
        if row["seed"] == 0:
            skipped_seed0 += 1
            continue
        rows.append(row)
    rows.sort(key=lambda r: (r["exp_version"], r["condition"], r["suite"],
                             r["task"], r["seed"], r["run_id"]))
    return rows, skipped_seed0, incomplete


def write_csv(rows, out_path):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        writer.writeheader()
        for row in rows:
            # success as 1/0: bool("False") is True, a trap for CSV consumers
            writer.writerow({**row, "success": int(row["success"])})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="artifacts/runs")
    parser.add_argument("--out", default="artifacts/ledger.csv")
    args = parser.parse_args(argv)
    rows, skipped_seed0, incomplete = build_ledger(args.runs_root)
    write_csv(rows, args.out)
    print(f"ledger: {len(rows)} scored rows -> {args.out} "
          f"(excluded: {skipped_seed0} seed-0 bootstrap, "
          f"{incomplete} incomplete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_build_ledger.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add track/analysis/build_ledger.py track/tests/test_build_ledger.py
git commit -m "feat: derived ledger builder with seed-0 exclusion and validation"
```

---

### Task 7: `disk_guard.py` — 200 GB artifacts cap

**Files:**
- Create: `track/analysis/disk_guard.py`
- Test: `track/tests/test_disk_guard.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_disk_guard.py`:

```python
from track.analysis import disk_guard


def test_usage_bytes_sums_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    (tmp_path / "sub" / "b.bin").write_bytes(b"y" * 500)
    assert disk_guard.usage_bytes(tmp_path) == 1500


def test_usage_bytes_missing_dir_is_zero(tmp_path):
    assert disk_guard.usage_bytes(tmp_path / "nope") == 0


def test_check_under_cap(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 100)
    used, ok = disk_guard.check(tmp_path, cap_bytes=200)
    assert used == 100 and ok is True


def test_check_over_cap(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 300)
    used, ok = disk_guard.check(tmp_path, cap_bytes=200)
    assert used == 300 and ok is False


def test_default_cap_is_200_gb():
    assert disk_guard.DEFAULT_CAP_BYTES == 200 * 1024**3


def test_main_exit_codes(tmp_path, capsys):
    (tmp_path / "a.bin").write_bytes(b"x" * 300)
    assert disk_guard.main(["--path", str(tmp_path), "--cap-bytes", "1000"]) == 0
    assert disk_guard.main(["--path", str(tmp_path), "--cap-bytes", "200"]) == 1
    out = capsys.readouterr().out
    assert "OVER" in out and "OK" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_disk_guard.py -v`
Expected: ERROR — `ModuleNotFoundError: track.analysis.disk_guard`.

- [ ] **Step 3: Write `track/analysis/disk_guard.py`**

```python
"""Artifacts disk guard (spec section 4): 200 GB hard cap under artifacts/.
The batch runner calls this before each rollout; on OVER it pauses the
queue. It never deletes anything."""
import argparse
import os
import sys

DEFAULT_CAP_BYTES = 200 * 1024**3  # 200 GB


def usage_bytes(root):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            try:
                total += os.stat(os.path.join(dirpath, name)).st_size
            except OSError:
                continue  # file vanished mid-scan
    return total


def check(root, cap_bytes=DEFAULT_CAP_BYTES):
    used = usage_bytes(root)
    return used, used <= cap_bytes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="artifacts")
    parser.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP_BYTES)
    args = parser.parse_args(argv)
    used, ok = check(args.path, args.cap_bytes)
    print(f"disk_guard: used={used} cap={args.cap_bytes} "
          f"status={'OK' if ok else 'OVER'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_disk_guard.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add track/analysis/disk_guard.py track/tests/test_disk_guard.py
git commit -m "feat: artifacts disk guard with 200GB default cap"
```

---

### Task 8: `manifests.py` — queue-manifest validation, seed-0 bootstrap rule

**Files:**
- Create: `track/analysis/manifests.py`
- Test: `track/tests/test_manifests.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_manifests.py`:

```python
import json

import pytest

from track.analysis import manifests


def valid_manifest():
    return {
        "exp_version": "v1",
        "budgets": {"max_steps": 400, "max_turns": 40, "max_wall_seconds": 1800},
        "caps": {"max_rollouts": 40, "max_tokens_per_rollout": 200000},
        "cells": [
            {
                "condition": "direct",
                "suite": "libero_goal_task",
                "task": "task_a",
                "seeds": [
                    {"seed": 0, "bootstrap_only": True},
                    {"seed": 1, "bootstrap_only": False},
                    {"seed": 2, "bootstrap_only": False},
                ],
            }
        ],
    }


def test_valid_manifest_passes():
    manifests.validate_manifest(valid_manifest())


def test_seed_zero_must_be_bootstrap_only():
    m = valid_manifest()
    m["cells"][0]["seeds"][0]["bootstrap_only"] = False
    with pytest.raises(ValueError, match="seed 0"):
        manifests.validate_manifest(m)


def test_missing_caps_fails():
    m = valid_manifest()
    del m["caps"]["max_rollouts"]
    with pytest.raises(ValueError, match="max_rollouts"):
        manifests.validate_manifest(m)


def test_missing_budget_fails():
    m = valid_manifest()
    del m["budgets"]["max_wall_seconds"]
    with pytest.raises(ValueError, match="max_wall_seconds"):
        manifests.validate_manifest(m)


def test_scored_cells_excludes_bootstrap():
    cells = manifests.scored_cells(valid_manifest())
    assert cells == [
        ("direct", "libero_goal_task", "task_a", 1),
        ("direct", "libero_goal_task", "task_a", 2),
    ]


def test_load_manifest_from_json(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest()))
    m = manifests.load_manifest(p)
    assert m["exp_version"] == "v1"


def test_non_bool_bootstrap_only_fails():
    m = valid_manifest()
    m["cells"][0]["seeds"][1]["bootstrap_only"] = "no"
    with pytest.raises(ValueError, match="bootstrap_only"):
        manifests.validate_manifest(m)


def test_duplicate_seed_fails():
    m = valid_manifest()
    m["cells"][0]["seeds"].append({"seed": 1, "bootstrap_only": False})
    with pytest.raises(ValueError, match="duplicate seed"):
        manifests.validate_manifest(m)


def test_duplicate_cell_fails():
    m = valid_manifest()
    m["cells"].append(dict(m["cells"][0]))
    with pytest.raises(ValueError, match="duplicate cell"):
        manifests.validate_manifest(m)


def test_non_str_cell_field_fails():
    m = valid_manifest()
    m["cells"][0]["condition"] = 123
    with pytest.raises(ValueError, match="condition"):
        manifests.validate_manifest(m)


def test_empty_seeds_fails():
    m = valid_manifest()
    m["cells"][0]["seeds"] = []
    with pytest.raises(ValueError, match="seeds"):
        manifests.validate_manifest(m)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_manifests.py -v`
Expected: ERROR — `ModuleNotFoundError: track.analysis.manifests`.

- [ ] **Step 3: Write `track/analysis/manifests.py`**

```python
"""Queue-manifest loading and validation (spec sections 3-4).

A queue is a frozen manifest plus a pinned experiment version - nothing
else. Manifests mark seed 0 bootstrap_only; scored seeds are never 0.
"""
import json
from pathlib import Path

_BUDGETS_REQUIRED = {"max_steps": int, "max_turns": int, "max_wall_seconds": int}
_CAPS_REQUIRED = {"max_rollouts": int, "max_tokens_per_rollout": int}


def _require(record, spec, where):
    if not isinstance(record, dict):
        raise ValueError(f"{where}: expected dict, got {type(record).__name__}")
    for key, typ in spec.items():
        if key not in record:
            raise ValueError(f"{where}: missing required key '{key}'")
        if not isinstance(record[key], typ) or isinstance(record[key], bool):
            raise ValueError(f"{where}: key '{key}' must be {typ.__name__}")


def validate_manifest(manifest):
    for key in ("exp_version", "budgets", "caps", "cells"):
        if key not in manifest:
            raise ValueError(f"manifest: missing required key '{key}'")
    if not isinstance(manifest["exp_version"], str):
        raise ValueError("manifest: 'exp_version' must be str")
    _require(manifest["budgets"], _BUDGETS_REQUIRED, "manifest.budgets")
    _require(manifest["caps"], _CAPS_REQUIRED, "manifest.caps")
    if not isinstance(manifest["cells"], list) or not manifest["cells"]:
        raise ValueError("manifest: 'cells' must be a non-empty list")
    seen_cells = set()
    for i, cell in enumerate(manifest["cells"]):
        where = f"manifest.cells[{i}]"
        for key in ("condition", "suite", "task"):
            if key not in cell:
                raise ValueError(f"{where}: missing required key '{key}'")
            if not isinstance(cell[key], str):
                raise ValueError(f"{where}: key '{key}' must be str")
        if not isinstance(cell.get("seeds"), list) or not cell["seeds"]:
            raise ValueError(f"{where}: 'seeds' must be a non-empty list")
        cell_id = (cell["condition"], cell["suite"], cell["task"])
        if cell_id in seen_cells:
            raise ValueError(f"{where}: duplicate cell {cell_id}")
        seen_cells.add(cell_id)
        seen_seeds = set()
        for entry in cell["seeds"]:
            if "seed" not in entry or "bootstrap_only" not in entry:
                raise ValueError(
                    f"{where}: each seed entry needs 'seed' and 'bootstrap_only'")
            if not isinstance(entry["seed"], int) or isinstance(entry["seed"], bool):
                raise ValueError(f"{where}: 'seed' must be int")
            if not isinstance(entry["bootstrap_only"], bool):
                raise ValueError(f"{where}: 'bootstrap_only' must be bool")
            if entry["seed"] in seen_seeds:
                raise ValueError(f"{where}: duplicate seed {entry['seed']}")
            seen_seeds.add(entry["seed"])
            if entry["seed"] == 0 and not entry["bootstrap_only"]:
                raise ValueError(
                    f"{where}: seed 0 bootstraps memory only and must be "
                    "bootstrap_only (it is never scored)")
    return manifest


def scored_cells(manifest):
    """Expand to (condition, suite, task, seed) tuples, bootstrap seeds excluded."""
    validate_manifest(manifest)
    out = []
    for cell in manifest["cells"]:
        for entry in cell["seeds"]:
            if not entry["bootstrap_only"]:
                out.append((cell["condition"], cell["suite"],
                            cell["task"], entry["seed"]))
    return out


def load_manifest(path):
    return validate_manifest(json.loads(Path(path).read_text()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_manifests.py -v`
Expected: 11 PASS

- [ ] **Step 5: Commit**

```bash
git add track/analysis/manifests.py track/tests/test_manifests.py
git commit -m "feat: queue-manifest validator with seed-0 bootstrap rule"
```

---

### Task 9: `setup_lib.sh` + `setup.sh` — environment bootstrap

**Files:**
- Create: `track/setup/setup_lib.sh`
- Create: `track/setup/setup.sh`
- Test: `track/tests/test_setup.py`

- [ ] **Step 1: Write the failing tests**

Create `track/tests/test_setup.py`:

```python
import os
import stat

from .conftest import REPO

LIB = REPO / "track" / "setup" / "setup_lib.sh"
SETUP = REPO / "track" / "setup" / "setup.sh"


def fake_nvidia_smi(tmp_path, name):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    smi = bindir / "nvidia-smi"
    smi.write_text(f'#!/usr/bin/env bash\necho "{name}"\n')
    smi.chmod(smi.stat().st_mode | stat.S_IEXEC)
    return f"{bindir}:{os.environ['PATH']}"


def test_scripts_parse():
    import subprocess
    for script in (LIB, SETUP):
        r = subprocess.run(["bash", "-n", str(script)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{script}: {r.stderr}"


def test_assert_gpu_accepts_a6000(bash, tmp_path):
    path = fake_nvidia_smi(tmp_path, "NVIDIA RTX A6000")
    r = bash(f'source "{LIB}" && assert_gpu', env={"PATH": path})
    assert r.returncode == 0, r.stderr
    assert "GPU0 OK" in r.stdout


def test_assert_gpu_rejects_titan_x(bash, tmp_path):
    path = fake_nvidia_smi(tmp_path, "NVIDIA TITAN X (Pascal)")
    r = bash(f'source "{LIB}" && assert_gpu', env={"PATH": path})
    assert r.returncode != 0
    assert "expected RTX A6000" in r.stderr


def test_verify_checkpoint_record_then_check(bash, tmp_path):
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    (ckpt / "weights.bin").write_bytes(b"pi05" * 100)
    sums = tmp_path / "checkpoint.sha256sums"

    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode == 0, r.stderr
    assert "recorded" in r.stdout
    assert sums.exists()

    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode == 0, r.stderr
    assert "checksum OK" in r.stdout


def test_verify_checkpoint_detects_corruption(bash, tmp_path):
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    (ckpt / "weights.bin").write_bytes(b"pi05" * 100)
    sums = tmp_path / "checkpoint.sha256sums"
    bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    (ckpt / "weights.bin").write_bytes(b"corrupted")
    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode != 0


def test_setup_usage_on_bad_subcommand(bash):
    r = bash(f'"{SETUP}" frobnicate')
    assert r.returncode == 64
    assert "usage:" in r.stderr


def test_assert_gpu_fails_without_nvidia_smi(bash, tmp_path):
    empty = tmp_path / "bin"
    empty.mkdir()
    r = bash(f'export PATH="{empty}"; source "{LIB}" && assert_gpu')
    assert r.returncode != 0
    assert "nvidia-smi not found" in r.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-dev/bin/python -m pytest track/tests/test_setup.py -v`
Expected: FAIL/ERROR on all 6 (scripts missing).

- [ ] **Step 3: Write `track/setup/setup_lib.sh`**

```bash
#!/usr/bin/env bash
# Pure functions used by setup.sh; kept separate so tests can source them.

# Fail unless GPU 0 is the RTX A6000 (spec section 2: a driver
# re-enumeration must never silently move work to the TITAN X).
assert_gpu() {
    command -v nvidia-smi >/dev/null || { echo "FATAL: nvidia-smi not found (driver not loaded?)" >&2; return 1; }
    local name
    name="$(nvidia-smi --query-gpu=name --format=csv,noheader -i 0)"
    case "$name" in
        *"RTX A6000"*) echo "GPU0 OK: $name" ;;
        *) echo "FATAL: GPU 0 is '$name', expected RTX A6000" >&2; return 1 ;;
    esac
}

# verify_checkpoint <ckpt_dir> <sums_file>
# First run records checksums (trust-on-first-use: upstream publishes no
# sums); later runs verify against them.
verify_checkpoint() {
    local ckpt_dir="$1" sums_file="$2"
    if [ -f "$sums_file" ]; then
        (cd "$ckpt_dir" && sha256sum --check --quiet "$sums_file") \
            && echo "checkpoint checksum OK: $ckpt_dir"
    else
        (cd "$ckpt_dir" && find . -type f -print0 | sort -z | xargs -0 sha256sum) \
            > "$sums_file"
        echo "recorded new checksums to $sums_file"
    fi
}

# read_pin <pins_file>
# Parse, never source: pins.env content must not run as code.
# Twin of the inline parse in pin_check.sh (kept standalone as the audit gate).
read_pin() {
    grep -E '^RPENT_COMMIT=' "$1" | tail -1 | cut -d= -f2 || true
}
```

- [ ] **Step 4: Write `track/setup/setup.sh`**

```bash
#!/usr/bin/env bash
# One-command bootstrap (spec section 1): clone repo -> setup.sh -> it clones
# RPent at the pinned commit, builds the venv, fetches + checksums the
# checkpoint. Subcommands allow re-running any stage alone.
set -euo pipefail

REPO="${TRACK_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck disable=SC1091
source "$REPO/track/setup/setup_lib.sh"

PINS="$REPO/track/setup/pins.env"
RPENT_URL="https://github.com/RLinf/RPent"
CKPT_REPO="RLinf/rlinf-pi05-libero-130-fullshot-sft"
CKPT_DIR="$REPO/checkpoints/rlinf-pi05-libero-130-fullshot-sft"
SUMS="$REPO/track/setup/checkpoint.sha256sums"

clone_rpent() {
    [ -d "$REPO/RPent/.git" ] || git clone "$RPENT_URL" "$REPO/RPent"
    local pin
    pin="$(read_pin "$PINS")"
    if [ -n "$pin" ]; then
        git -C "$REPO/RPent" checkout --quiet "$pin"
        echo "RPent at pinned $pin"
    else
        echo "WARNING: RPENT_COMMIT unset; review the clone, then run" >&2
        echo "         track/setup/pin_check.sh --record" >&2
    fi
}

make_venv() {
    [ -d "$REPO/.venv" ] || python3 -m venv "$REPO/.venv"
    "$REPO/.venv/bin/pip" install --upgrade pip
    # Keep the pyproject-pinned RLinf/OpenPI/LIBERO-PRO forks; never
    # upgrade robosuite or the LIBERO forks (plan + spec section 2).
    "$REPO/.venv/bin/pip" install -e "$REPO/RPent[full]"
}

fetch_checkpoint() {
    mkdir -p "$REPO/checkpoints"
    if [ ! -d "$CKPT_DIR" ]; then
        [ -f "$HOME/huggingface.txt" ] || { echo "FATAL: HF token file missing at $HOME/huggingface.txt" >&2; return 1; }
        # Download to a temp dir and mv into place atomically so an interrupted
        # download can never be mistaken for a complete checkpoint (and then
        # TOFU-recorded as checksum truth by verify_checkpoint).
        rm -rf "$CKPT_DIR.partial"
        # HF token is read here once and scoped to this command only;
        # it is never exported into run environments (spec section 2).
        HF_TOKEN="$(cat "$HOME/huggingface.txt")" \
            "$REPO/.venv/bin/huggingface-cli" download "$CKPT_REPO" \
            --repo-type dataset --local-dir "$CKPT_DIR.partial"
        mv "$CKPT_DIR.partial" "$CKPT_DIR"
    fi
    verify_checkpoint "$CKPT_DIR" "$SUMS"
}

freeze_requirements() {
    # Run once, after the Day-2 smoke tests pass (spec section 2).
    "$REPO/.venv/bin/pip" freeze > "$REPO/track/setup/requirements.lock"
    echo "froze $REPO/track/setup/requirements.lock"
}

case "${1:-all}" in
    check)      assert_gpu; "$REPO/track/setup/pin_check.sh" ;;
    rpent)      clone_rpent ;;
    venv)       make_venv ;;
    checkpoint) fetch_checkpoint ;;
    freeze)     freeze_requirements ;;
    all)        assert_gpu; clone_rpent; make_venv; fetch_checkpoint ;;
    *) echo "usage: setup.sh [check|rpent|venv|checkpoint|freeze|all]" >&2; exit 64 ;;
esac
```

Then: `chmod +x track/setup/setup.sh` (setup_lib.sh stays 644 — it is sourced, never executed, matching the track_env.sh convention)

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv-dev/bin/python -m pytest track/tests/test_setup.py -v`
Expected: 7 PASS

Note: `setup.sh all` is NOT run by this plan — it needs the GPU, network, and ~hours of downloads, and belongs to Day 2 of the internship plan. The tests cover its parseable structure and the pure functions.

- [ ] **Step 6: Commit**

```bash
git add track/setup/setup_lib.sh track/setup/setup.sh track/tests/test_setup.py
git commit -m "feat: setup.sh bootstrap with GPU assert and checkpoint checksums"
```

---

### Task 10: Registry seed files

**Files:**
- Create: `track/registry/experiment_registry.md`
- Create: `track/registry/risk_log.md`
- Create: `track/registry/protocol_deviations.md`
- Delete: `track/registry/.gitkeep`

- [ ] **Step 1: Write `track/registry/experiment_registry.md`**

```markdown
# Experiment registry

Every behavior-affecting configuration gets a version tag here before any run
uses it: planner model + settings, prompt hashes, baseline implementation,
ablation flags. Runs record their tag in `run_meta.json`. A version bump
invalidates affected paired cells; both conditions of those pairs are rerun.

| Version | Date | Planner model + settings | Prompt hashes | Baseline impl | Ablation flags | Notes |
|---|---|---|---|---|---|---|
| v0 | 2026-07-26 | none — scaffolding only, no runs | n/a | n/a | n/a | Track scaffolding built; first experiment version will be v1, frozen at Day 3 with the baseline decision |

## Agent-authored change log

Log every agent-authored change to track code here, like any other code
change (plan section 2, "Claude Code + superpowers working model").

| Date | Change | Files | Reviewed by |
|---|---|---|---|
| 2026-07-26 | Initial track scaffolding (this repo structure, scripts, schemas, tests) | track/ | pending mentor review |
```

- [ ] **Step 2: Write `track/registry/risk_log.md`**

```markdown
# Risk log (live)

The full risk table with early warnings, required responses, and decision
days lives in the internship plan
(`docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`, section 8).
This file tracks only risks as they actually materialize.

| Date | Risk (plan §8 row or new) | What happened | Response taken | Status |
|---|---|---|---|---|
| 2026-07-26 | Checkpoint/GPU incompatibility | Pre-empted: track moved to asus (RTX A6000, sm_86) because the pinned forks lack Blackwell sm_120 kernels for the robot PC's RTX 5090 | Layout pins CUDA_VISIBLE_DEVICES=0 (A6000); setup.sh asserts the GPU name | closed |
```

- [ ] **Step 3: Write `track/registry/protocol_deviations.md`**

```markdown
# Protocol-deviation table

Deviations from the paper's protocol (Appendix C) and the plan's design
reference. Every row must state what differs and why; reports cite this table.

| # | Item | Paper protocol | This track | Why | Recorded |
|---|---|---|---|---|---|
| 1 | Evaluation scale | 8 cells, 80 tasks, seeds s1–s10, 800 scored rollouts per condition | Core: 4 tasks, seeds s1–s5, ≥40 paired scored rollouts; extension up to ~240 | 20-day internship compute/time budget (plan section 2) | 2026-07-26 |
| 2 | Planner model | Paper-era Claude Code / Codex versions | claude_code planner via claude.ai subscription, current CLI model; exact model ID + settings pinned per experiment version at Day 3 | Paper-era planner versions unavailable; direction-not-magnitude comparison (plan risk "planner model drift") | 2026-07-26 |
```

- [ ] **Step 4: Remove the placeholder and commit**

```bash
git rm --quiet track/registry/.gitkeep
git add track/registry/
git commit -m "docs: seed experiment registry, live risk log, deviation table"
```

---

### Task 11: README quick start

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# HarnessVLA sim track (asus)

Reproduction of HarnessVLA (arXiv:2607.08448, RPent) on LIBERO-Pro with a
frozen pi0.5 checkpoint. Runs on the RTX A6000 (GPU 0) only.

- **What/why/how:** `HANDOVER.md`, then
  `docs/HarnessVLA_Simulation_Reproduction_Internship_Plan.docx`
- **Architecture spec:** `docs/superpowers/specs/2026-07-26-sim-track-architecture-design.md`

## Quick start

```bash
git clone <this-repo> && cd github_sow_harnessVLA
track/setup/setup.sh all            # GPU assert, RPent clone, venv, checkpoint
track/setup/pin_check.sh --record   # first time only, after reviewing the clone
source track/setup/track_env.sh     # before any run or queue
```

After the Day-2 smoke tests pass: `track/setup/setup.sh freeze` to write
`track/setup/requirements.lock`.

## Development tests (no GPU needed)

```bash
python3 -m venv .venv-dev && .venv-dev/bin/pip install pytest
.venv-dev/bin/python -m pytest track/tests -v
```

## Layout

| Path | What |
|---|---|
| `track/launchers/` | Launcher wrappers; all planner calls go through `run_planner` (key strip) |
| `track/manifests/` | Frozen task/seed/condition queue manifests (JSON) |
| `track/analysis/` | Schemas, ledger builder, disk guard, manifest validator |
| `track/registry/` | Experiment registry, live risk log, deviation table |
| `track/setup/` | `setup.sh`, `track_env.sh`, `pin_check.sh`, pins, checksums |
| `RPent/` (gitignored) | Upstream clone, pinned — never edited |
| `checkpoints/` (gitignored) | pi0.5 download; checksums live in `track/setup/` |
| `artifacts/` (gitignored) | Run outputs, 200 GB guard, append-only |

## Standing rules

- Success is decided only by the benchmark predicate in `state_NN.json`.
- Seed 0 bootstraps memory and is never scored.
- Valid policy failures are never retried, deleted, or overwritten.
- `ANTHROPIC_API_KEY` is stripped from every planner subprocess
  (`track/launchers/planner_env.sh`) — planner work bills the claude.ai
  subscription only.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start, layout, standing rules"
```

---

### Task 12: Full-suite verification

- [ ] **Step 1: Run the entire test suite**

Run: `.venv-dev/bin/python -m pytest track/tests -v`
Expected: **64 PASS** (3 track_env + 9 pin_check + 3 key_hygiene + 15 schemas + 10 ledger + 6 disk_guard + 11 manifests + 7 setup). Zero failures, zero errors.

- [ ] **Step 2: Run the shell scripts through bash -n once more**

```bash
bash -n track/setup/track_env.sh track/setup/setup.sh track/setup/setup_lib.sh \
        track/setup/pin_check.sh track/launchers/planner_env.sh && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`

- [ ] **Step 3: Verify clean git state and history**

Run: `git status --short` → empty. `git log --oneline` → one commit per task above, plus the two pre-existing spec commits.

- [ ] **Step 4: Final commit if anything is outstanding**

```bash
git add -A && git diff --cached --quiet || git commit -m "chore: scaffolding verification cleanup"
```

---

## Explicitly deferred (do NOT build now)

- **GitHub remote creation and push** — needs the private repo created under the nuPylot org first; do this at the next session with `gh repo create` or the web UI, then `git remote add origin … && git push -u origin main`.
- **Running `setup.sh all`** — Day 2 of the internship plan (network + GPU + hours of download).
- **The batch runner and overnight-queue tooling** — Day 6 of the internship plan; it consumes `manifests.py`, `disk_guard.py`, and `schemas.py` built here.
- **Actual launchers (direct baseline, harness)** — Day 3–4 of the internship plan; they must source `planner_env.sh` and `track_env.sh`, which the hygiene test enforces.
```
