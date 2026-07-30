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
