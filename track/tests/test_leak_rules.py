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
