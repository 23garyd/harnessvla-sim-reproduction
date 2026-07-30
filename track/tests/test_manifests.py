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


def test_ablation_hiddenmem_manifest_loads_and_scores_5_cells():
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1]
         / "manifests" / "ablation_hiddenmem_v2.json")
    m = manifests.load_manifest(p)
    assert m["exp_version"] == "v2-hiddenmem"
    assert m["budgets"] == {"max_steps": 1200, "max_turns": 60,
                            "max_wall_seconds": 2400}
    cells = manifests.scored_cells(m)
    assert len(cells) == 5
    assert all(c[:3] == ("harness", "libero_object_swap",
                         "libero_object_swap_t2") for c in cells)
    assert sorted(c[3] for c in cells) == [1, 2, 3, 4, 5]


def test_ext_v3_manifests_load_and_form_4x2_grid():
    from pathlib import Path
    mdir = Path(__file__).resolve().parents[1] / "manifests"
    md = manifests.load_manifest(mdir / "ext_v3_direct.json")
    mh = manifests.load_manifest(mdir / "ext_v3_harness.json")
    assert md["exp_version"] == mh["exp_version"] == "v3"
    assert md["budgets"]["max_steps"] == 600
    assert mh["budgets"]["max_steps"] == 1200
    d_cells = manifests.scored_cells(md)
    h_cells = manifests.scored_cells(mh)
    suites = {"libero_object_task", "libero_spatial_swap",
              "libero_10_task", "libero_10_swap"}
    assert {c[1] for c in d_cells} == {c[1] for c in h_cells} == suites
    assert len(d_cells) == len(h_cells) == 20  # 4 suites x s1-s5
    # every harness cell carries a seed-0 bootstrap entry
    for cell in mh["cells"]:
        assert any(e["seed"] == 0 and e["bootstrap_only"]
                   for e in cell["seeds"])


def test_plan_cli_prints_suite_taskid_seed(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest()))
    rc = manifests.main(["--plan", str(p), "--condition", "direct"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == "libero_goal_task 2 1\nlibero_goal_task 2 2\n"


def test_plan_cli_condition_filter_excludes_other_conditions(tmp_path, capsys):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest()))
    rc = manifests.main(["--plan", str(p), "--condition", "harness"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_ablation_zeroshot_v4_manifest_is_the_predeclared_design():
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1]
         / "manifests" / "ablation_zeroshot_v4.json")
    m = manifests.load_manifest(p)
    assert m["exp_version"] == "v4"
    # identical to v2/v3 so the ONLY difference is memory access
    assert m["budgets"] == {"max_steps": 1200, "max_turns": 60,
                            "max_wall_seconds": 2400}
    cells = manifests.scored_cells(m)
    assert len(cells) == 20                      # 4 cells x seeds 1-5
    assert all(c[0] == "harness" for c in cells)
    assert {c[1] for c in cells} == {
        "libero_spatial_task", "libero_object_task",
        "libero_spatial_swap", "libero_goal_swap"}
    # zero-shot: NO seed-0 bootstrap anywhere, since bootstrapping would
    # manufacture the memory being ablated
    for cell in m["cells"]:
        assert all(e["seed"] != 0 for e in cell["seeds"])
    assert sorted({c[3] for c in cells}) == [1, 2, 3, 4, 5]
    # the excluded floor cells must not sneak in
    assert not {c[1] for c in cells} & {
        "libero_goal_task", "libero_10_task", "libero_10_swap",
        "libero_object_swap"}
