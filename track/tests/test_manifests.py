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
                "task_id": 2,
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


def test_missing_task_id_fails():
    m = valid_manifest()
    del m["cells"][0]["task_id"]
    with pytest.raises(ValueError, match="task_id"):
        manifests.validate_manifest(m)
