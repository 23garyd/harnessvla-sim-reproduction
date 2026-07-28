import pytest

from track.analysis import compare


def row(condition, task, seed, success, validity="success"):
    if not success and validity == "success":
        validity = "valid_failure"
    return {"condition": condition, "task": task, "seed": str(seed),
            "success": str(int(success)), "validity": validity}


def paired_rows():
    rows = []
    # cell A: direct 1/2, harness 2/2
    for s, (d, h) in {1: (1, 1), 2: (0, 1)}.items():
        rows.append(row("direct", "cell_a", s, d))
        rows.append(row("harness", "cell_a", s, h))
    # cell B: direct 1/2, harness 0/2
    for s, (d, h) in {1: (1, 0), 2: (0, 0)}.items():
        rows.append(row("direct", "cell_b", s, d))
        rows.append(row("harness", "cell_b", s, h))
    return rows


def test_wilson_interval_known_values():
    # 0/5 and 5/5 against scipy-checked references (z=1.96)
    lo, hi = compare.wilson_interval(0, 5)
    assert lo == 0.0
    assert hi == pytest.approx(0.4345, abs=1e-3)
    lo, hi = compare.wilson_interval(5, 5)
    assert lo == pytest.approx(0.5655, abs=1e-3)
    assert hi == 1.0
    lo, hi = compare.wilson_interval(11, 20)
    assert lo == pytest.approx(0.3421, abs=1e-3)
    assert hi == pytest.approx(0.7418, abs=1e-3)


def test_wilson_interval_rejects_bad_counts():
    with pytest.raises(ValueError):
        compare.wilson_interval(3, 0)
    with pytest.raises(ValueError):
        compare.wilson_interval(6, 5)
    with pytest.raises(ValueError):
        compare.wilson_interval(-1, 5)


def test_infra_rows_are_excluded():
    rows = paired_rows()
    rows.append({"condition": "harness", "task": "cell_a", "seed": "3",
                 "success": "0", "validity": "infra_failure"})
    table = compare.paired_table(rows)
    assert table["cells"]["cell_a"]["harness"]["n"] == 2  # infra seed 3 dropped


def test_paired_table_counts_and_intervals():
    table = compare.paired_table(paired_rows())
    a = table["cells"]["cell_a"]
    assert a["direct"] == {"k": 1, "n": 2,
                           "wilson": pytest.approx(
                               compare.wilson_interval(1, 2))}
    assert a["harness"]["k"] == 2
    agg = table["aggregate"]
    assert agg["direct"] == {"k": 2, "n": 4,
                             "wilson": pytest.approx(
                                 compare.wilson_interval(2, 4))}
    assert agg["harness"]["k"] == 2
    assert table["flips"] == {"rescued": 1, "regressed": 1,
                              "both_pass": 1, "both_fail": 1}


def test_incomplete_pairs_are_excluded_and_reported():
    rows = paired_rows()
    # harness-only seed with no direct partner must not enter any aggregate
    rows.append(row("harness", "cell_a", 9, 1))
    table = compare.paired_table(rows)
    assert table["cells"]["cell_a"]["harness"]["n"] == 2
    assert table["aggregate"]["harness"]["n"] == 4
    assert table["unpaired"] == [("cell_a", "9", "harness")]


def test_duplicate_scored_rows_raise():
    rows = paired_rows()
    rows.append(row("direct", "cell_a", 1, 1))
    with pytest.raises(ValueError, match="duplicate"):
        compare.paired_table(rows)


def test_render_markdown_mentions_wall_clock_caveat():
    text = compare.render_markdown(compare.paired_table(paired_rows()))
    assert "cell_a" in text and "cell_b" in text
    assert "aggregate" in text
    # the harness launcher clock includes ~3-4 min server boot
    assert "server boot" in text
