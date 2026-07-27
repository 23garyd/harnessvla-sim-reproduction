import json

import pytest

from track.analysis import build_ledger
from track.launchers import direct_lib


def test_task_key():
    assert direct_lib.task_key("libero_goal_swap", 2) == "libero_goal_swap_t2"


def test_make_run_dir_five_levels(tmp_path):
    d = direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                "libero_goal_swap", 2, 3, "20260726T120000")
    assert d == (tmp_path / "v1" / "direct" / "libero_goal_swap_t2"
                 / "3" / "20260726T120000")
    assert d.is_dir()
    with pytest.raises(FileExistsError):
        direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                "libero_goal_swap", 2, 3, "20260726T120000")


def test_resolve_outcome_mapping():
    assert direct_lib.resolve_outcome(True, 42, 600, 100.0, 1800) == \
        ("success", "benchmark_predicate")
    assert direct_lib.resolve_outcome(False, 600, 600, 100.0, 1800) == \
        ("budget_exhausted", "step_budget")
    assert direct_lib.resolve_outcome(False, 42, 600, 1801.0, 1800) == \
        ("budget_exhausted", "wall_time")
    assert direct_lib.resolve_outcome(False, 42, 600, 100.0, 1800) == \
        ("valid_failure", "env_truncated")


def test_build_result_row_validates():
    row = direct_lib.build_result_row(
        success=False, validity="valid_failure", terminal_reason="env_truncated",
        steps=42, chunks=9, wall_s=100.5)
    assert row["counts"] == {"steps": 42, "turns": 0,
                             "vla_act_calls": 9, "analytic_calls": 0}


def test_build_result_row_infra_needs_evidence():
    with pytest.raises(ValueError, match="evidence"):
        direct_lib.build_result_row(
            success=False, validity="infra_failure", terminal_reason="exception",
            steps=0, chunks=0, wall_s=1.0)
    row = direct_lib.build_result_row(
        success=False, validity="infra_failure", terminal_reason="exception",
        steps=0, chunks=0, wall_s=1.0, evidence="Traceback ...")
    assert row["evidence"] == "Traceback ..."


def test_read_rpent_pin(tmp_path):
    pins = tmp_path / "pins.env"
    pins.write_text("# comment\nRPENT_COMMIT=6e4ba1805a459d74ad53569e833bae7ae2c59985\n")
    assert direct_lib.read_rpent_pin(pins).startswith("6e4ba18")
    pins.write_text("RPENT_COMMIT=\n")
    with pytest.raises(ValueError, match="RPENT_COMMIT"):
        direct_lib.read_rpent_pin(pins)


def test_read_checkpoint_sha(tmp_path):
    sums = tmp_path / "checkpoint.sha256sums"
    sums.write_text(
        "aaaa  ./.gitattributes\n"
        "4d9089c941793f170b625c2ed0ac7a3aa09b6f103e52dbbc82e67301529d6683  ./model.safetensors\n")
    assert direct_lib.read_checkpoint_sha(sums).startswith("4d9089c9")
    sums.write_text("aaaa  ./other.bin\n")
    with pytest.raises(ValueError, match="model.safetensors"):
        direct_lib.read_checkpoint_sha(sums)


def test_build_run_meta_ledger_round_trip(tmp_path):
    """A run dir written with direct_lib must survive build_ledger unchanged."""
    run_dir = direct_lib.make_run_dir(tmp_path, "v1", "direct",
                                      "libero_goal_swap", 2, 3, "20260726T120000")
    meta = direct_lib.build_run_meta(
        exp_version="v1", suite="libero_goal_swap", task_id=2, seed=3,
        budgets={"max_steps": 600, "max_turns": 0, "max_wall_seconds": 1800},
        rpent_commit="6e4ba1805a459d74ad53569e833bae7ae2c59985",
        checkpoint_sha256="4d9089c9", launch_command="run_direct.py ...")
    (run_dir / "run_meta.json").write_text(json.dumps(meta))
    row = direct_lib.build_result_row(
        success=True, validity="success", terminal_reason="benchmark_predicate",
        steps=42, chunks=9, wall_s=100.5)
    (run_dir / "result_row.json").write_text(json.dumps(row))
    rows, skipped0, incomplete = build_ledger.build_ledger(tmp_path)
    assert len(rows) == 1 and skipped0 == 0 and incomplete == 0
    assert rows[0]["task"] == "libero_goal_swap_t2"
    assert rows[0]["seed"] == 3
    assert rows[0]["condition"] == "direct"
    assert rows[0]["vla_act_calls"] == 9


def valid_cell_manifest():
    return {
        "exp_version": "v1",
        "budgets": {"max_steps": 600, "max_turns": 0, "max_wall_seconds": 1800},
        "caps": {"max_rollouts": 24, "max_tokens_per_rollout": 0},
        "cells": [
            {"condition": "direct", "suite": "libero_goal_swap",
             "task": "libero_goal_swap_t2", "task_id": 2,
             "seeds": [{"seed": 0, "bootstrap_only": True},
                       {"seed": 1, "bootstrap_only": False}]},
        ],
    }


def test_select_cell_ok():
    cell = direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 1)
    assert cell["task"] == "libero_goal_swap_t2"


def test_select_cell_rejects_bootstrap_seed():
    with pytest.raises(ValueError, match="bootstrap_only"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 0)


def test_select_cell_rejects_unfrozen_seed():
    with pytest.raises(ValueError, match="not in the frozen manifest"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_goal_swap", 2, 9)


def test_select_cell_rejects_unknown_cell():
    with pytest.raises(ValueError, match="not in the frozen manifest"):
        direct_lib.select_cell(valid_cell_manifest(), "libero_spatial_task", 2, 1)


def test_resolve_outcome_success_wins_over_caps():
    # Predicate fired on the exact step the cap was reached: success wins.
    assert direct_lib.resolve_outcome(True, 600, 600, 1800.0, 1800) == \
        ("success", "benchmark_predicate")


def test_resolve_outcome_wall_boundary_exact():
    assert direct_lib.resolve_outcome(False, 42, 600, 1800.0, 1800) == \
        ("budget_exhausted", "wall_time")


def test_core_v1_manifest_frozen():
    from track.analysis.manifests import load_manifest
    from track.tests.conftest import REPO
    m = load_manifest(REPO / "track" / "manifests" / "core_v1.json")
    assert m["exp_version"] == "v1"
    assert m["budgets"] == {"max_steps": 600, "max_turns": 0,
                            "max_wall_seconds": 1800}
    suites = sorted(c["suite"] for c in m["cells"])
    assert suites == ["libero_goal_swap", "libero_goal_task",
                      "libero_object_swap", "libero_spatial_task"]
    from track.analysis.manifests import scored_cells
    cells = scored_cells(m)
    assert len(cells) == 20  # 4 suites x seeds 1-5
    assert all(seed in (1, 2, 3, 4, 5) for _, _, _, seed in cells)
    for c in m["cells"]:
        assert c["task"] == direct_lib.task_key(c["suite"], c["task_id"])
