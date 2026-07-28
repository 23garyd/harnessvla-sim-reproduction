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


def test_main_print_separates_scored_and_infra(tmp_path, capsys):
    write_run(tmp_path, seed=1, ts="20260727T000001")
    write_run(tmp_path, seed=2, ts="20260727T000002", success=False,
              validity="infra_failure", evidence="server crash: log ...")
    out = tmp_path / "ledger.csv"
    build_ledger.main(["--runs-root", str(tmp_path), "--out", str(out)])
    text = capsys.readouterr().out
    assert "2 rows (1 scored, 1 infra_failure)" in text
