from pathlib import Path

import pytest

from track.analysis import leak_rules

REPO = Path(__file__).resolve().parents[2]


def test_prompt_named_set_is_exactly_the_seven_released_names():
    assert leak_rules.PROMPT_NAMED == frozenset({
        "MEMORY", "README",
        "feedback_bowl_eef_y_offset", "feedback_failure_forensics",
        "feedback_pi0_pick_full_prompt", "feedback_scripted_pick_limits",
        "feedback_swap_perturbs_fixtures"})


def test_record_inventory_writes_both_kinds(tmp_path):
    res = tmp_path / "resources"
    (res / "libero" / "memory").mkdir(parents=True)
    (res / "libero" / "memory" / "MEMORY.md").write_text("index")
    (res / "libero" / "memory" / "tall_item_first_basket_placement.md").write_text("x")
    (res / "libero" / "results_object_pert").mkdir(parents=True)
    (res / "libero" / "results_object_pert" / "object_swap_t2_s0.json").write_text("{}")
    (res / "libero" / "results_object_pert" / "recipe_object_swap_t2_s0.jsonl").write_text("{}")

    out = tmp_path / "inventory.txt"
    n = leak_rules.record_inventory(resources_dir=res, out_path=out)

    assert n == 4
    inv = leak_rules.load_inventory(out)
    assert sorted(inv["memory"]) == ["MEMORY", "tall_item_first_basket_placement"]
    assert sorted(inv["tsm"]) == ["object_swap_t2_s0", "recipe_object_swap_t2_s0"]


def test_load_inventory_ignores_comments_and_blank_lines(tmp_path):
    p = tmp_path / "inv.txt"
    p.write_text("# a comment\n\nmemory foo\ntsm bar\n\n")
    inv = leak_rules.load_inventory(p)
    assert inv == {"memory": ["foo"], "tsm": ["bar"]}


def test_load_inventory_rejects_unknown_kind(tmp_path):
    p = tmp_path / "inv.txt"
    p.write_text("bogus foo\n")
    with pytest.raises(ValueError, match="unknown kind"):
        leak_rules.load_inventory(p)


def test_checked_in_inventory_has_the_measured_counts():
    inv = leak_rules.load_inventory()
    assert len(inv["memory"]) == 50
    assert len(inv["tsm"]) == 156


@pytest.mark.skipif(not (REPO / "RPent/resources/libero/memory").is_dir(),
                    reason="memory dir stashed or absent")
def test_checked_in_inventory_matches_the_live_release():
    """Drift guard: a new released note must be added to the inventory or the
    leak rules would silently stop covering it."""
    live = leak_rules.record_inventory(out_path=None)
    assert live == leak_rules.load_inventory()


def test_content_patterns_exclude_prompt_named_leaves():
    pats = set(leak_rules.content_patterns())
    # content-bearing: the planner cannot name this without reading
    assert "tall_item_first_basket_placement" in pats
    # prompt echo: the released guides name it
    for name in leak_rules.PROMPT_NAMED:
        assert name not in pats


def test_content_patterns_exclude_bare_paths():
    """The system prompt tells the planner to list_dir these, so their
    appearance is the condition WORKING, not a leak."""
    pats = set(leak_rules.content_patterns())
    assert "resources/libero/memory" not in pats
    assert "resources/libero/results_object_pert" not in pats


def test_content_patterns_count_is_43_memory_plus_156_tsm():
    assert len(leak_rules.content_patterns()) == 199


def test_content_patterns_include_the_stash_dir_when_given():
    pats = leak_rules.content_patterns(stash_dir="/tmp/tsm_ablation.XYZ")
    assert "/tmp/tsm_ablation.XYZ" in pats
    assert len(pats) == 200


def test_scan_text_positive_control_detects_a_leaf_name():
    hits = leak_rules.scan_text(
        "I read tall_item_first_basket_placement.md for the offsets",
        leak_rules.content_patterns())
    assert hits == ["tall_item_first_basket_placement"]


def test_scan_text_negative_control_ignores_prompt_echoes():
    """A transcript that only echoes what the prompt told it must be clean."""
    text = ("list_dir resources/libero/memory/ -> (empty)\n"
            "no matching task memory found; MEMORY.md absent\n"
            "consulted feedback_swap_perturbs_fixtures per the guide\n")
    assert leak_rules.scan_text(text, leak_rules.content_patterns()) == []


def test_scan_text_detects_tsm_reference_names():
    hits = leak_rules.scan_text("opened recipe_object_swap_t2_s0.jsonl",
                                leak_rules.content_patterns())
    assert hits == ["recipe_object_swap_t2_s0"]


def test_scan_run_dir_reports_file_and_pattern(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("clean\n")
    (run / "rpent" / "run.log").write_text(
        "cat tall_item_first_basket_placement.md\n")
    (run / "rpent" / "transcript_x.json").write_text(
        '{"note": "recipe_object_swap_t2_s0"}')
    hits = leak_rules.scan_run_dir(run)
    assert ("rpent/run.log", "tall_item_first_basket_placement") in hits
    assert ("rpent/transcript_x.json", "recipe_object_swap_t2_s0") in hits
    assert not any(f == "launcher.log" for f, _ in hits)


def test_scan_run_dir_clean_dir_returns_no_hits(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("no matching task memory found\n")
    assert leak_rules.scan_run_dir(run) == []


def test_scan_run_dir_survives_undecodable_bytes(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_bytes(
        b"\xff\xfe binary junk tall_item_first_basket_placement\n")
    hits = leak_rules.scan_run_dir(run)
    assert hits == [("rpent/run.log", "tall_item_first_basket_placement")]


def test_cli_scan_exits_1_and_names_the_hit(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_text("tall_item_first_basket_placement")
    rc = leak_rules.main(["--scan", str(run)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "LEAK" in err
    assert "tall_item_first_basket_placement" in err


def test_cli_scan_exits_0_on_clean_run(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "launcher.log").write_text("no matching task memory found")
    rc = leak_rules.main(["--scan", str(run)])
    assert rc == 0
    assert "clean" in capsys.readouterr().out


def test_cli_scan_detects_the_stash_path(tmp_path, capsys):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_text("find /tmp/tsm_ablation.AbCd -type f")
    rc = leak_rules.main(["--scan", str(run), "--stash", "/tmp/tsm_ablation.AbCd"])
    assert rc == 1
    assert "/tmp/tsm_ablation.AbCd" in capsys.readouterr().err


def test_cli_record_writes_the_inventory(tmp_path, capsys):
    out = tmp_path / "inv.txt"
    rc = leak_rules.main(["--record", "--out", str(out)])
    assert rc == 0
    assert len(leak_rules.load_inventory(out)["memory"]) == 50


def test_tsm_family_parses_recipe_prefix_and_the_10_family():
    assert leak_rules._tsm_family("object_swap_t2_s0") == "object"
    assert leak_rules._tsm_family("recipe_object_swap_t2_s0") == "object"
    assert leak_rules._tsm_family("10_task_t7_s0") == "10"
    assert leak_rules._tsm_family("recipe_10_task_t7_s0") == "10"
    assert leak_rules._tsm_family("spatial_swap_t2_s0") == "spatial"


def test_patterns_scoped_to_v2_hiddenmem_cover_only_the_object_family():
    """v2-hiddenmem stashed memory + results_object_pert ONLY. The other three
    families were legitimately present, so their names are not leak evidence."""
    pats = set(leak_rules.content_patterns(exp_version="v2-hiddenmem"))
    assert "tall_item_first_basket_placement" in pats      # memory: hidden
    assert "object_swap_t2_s0" in pats                     # object TSM: hidden
    assert "recipe_object_swap_t2_s0" in pats
    assert "10_task_t7_s0" not in pats                     # not hidden
    assert "goal_swap_t2_s0" not in pats
    assert "recipe_spatial_swap_t2_s0" not in pats


def test_patterns_scoped_to_v4_cover_every_family():
    pats = set(leak_rules.content_patterns(exp_version="v4"))
    assert len(pats) == 199
    for name in ("object_swap_t2_s0", "10_task_t7_s0", "goal_swap_t2_s0",
                 "recipe_spatial_swap_t2_s0", "tall_item_first_basket_placement"):
        assert name in pats


def test_unknown_exp_version_falls_back_to_the_strictest_rule_set():
    """Fail closed: an unrecognised condition must not silently narrow the
    audit."""
    assert (leak_rules.content_patterns(exp_version="v99-unknown")
            == leak_rules.content_patterns(exp_version="v4"))


def test_scan_run_dir_reads_exp_version_from_run_meta(tmp_path):
    import json
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "run_meta.json").write_text(json.dumps({"exp_version": "v2-hiddenmem"}))
    # a non-hidden family under v2-hiddenmem: must NOT be flagged
    (run / "rpent" / "run.log").write_text("read 10_task_t7_s0.json")
    assert leak_rules.scan_run_dir(run) == []
    # a hidden family under v2-hiddenmem: MUST be flagged
    (run / "rpent" / "run.log").write_text("read object_swap_t2_s0.json")
    assert leak_rules.scan_run_dir(run) == [("rpent/run.log", "object_swap_t2_s0")]


def test_scan_run_dir_without_run_meta_uses_strictest(tmp_path):
    run = tmp_path / "20260729T120000"
    (run / "rpent").mkdir(parents=True)
    (run / "rpent" / "run.log").write_text("read 10_task_t7_s0.json")
    assert leak_rules.scan_run_dir(run) == [("rpent/run.log", "10_task_t7_s0")]
