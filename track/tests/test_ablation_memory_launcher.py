"""Unit tests for the ablation launcher's pieces.

The script guards its main flow behind a BASH_SOURCE check, so these tests
source it and exercise individual functions against a fake resources tree.
No rollout is launched.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "track" / "launchers" / "run_ablation_memory.sh"
HIDDENMEM = REPO / "track" / "launchers" / "run_ablation_hiddenmem.sh"


def fake_resources(tmp_path):
    res = tmp_path / "resources"
    for sub in ("libero/memory", "libero/results_object_pert",
                "libero/results_goal_pert", ".cache"):
        (res / sub).mkdir(parents=True)
    (res / "libero" / "memory" / "MEMORY.md").write_text("index")
    return res


def test_script_is_executable_and_sourceable_without_running(bash, tmp_path):
    """Sourcing must define functions without stashing anything."""
    res = fake_resources(tmp_path)
    r = bash(f'source {SCRIPT}; echo SOURCED-OK; ls {res}/libero',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "SOURCED-OK" in r.stdout
    assert "memory" in r.stdout


def test_stash_members_lists_memory_all_tsm_dirs_and_cache(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'source {SCRIPT}; stash_members',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    members = r.stdout.split()
    assert members[0] == "libero/memory"
    assert "libero/results_object_pert" in members
    assert "libero/results_goal_pert" in members
    assert ".cache" in members


def test_plan_cells_reads_the_v4_manifest(bash, tmp_path):
    res = fake_resources(tmp_path)
    manifest = REPO / "track" / "manifests" / "ablation_zeroshot_v4.json"
    r = bash(f'source {SCRIPT}; plan_cells {manifest}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    lines = [l for l in r.stdout.strip().split("\n") if l]
    assert len(lines) == 20
    assert "libero_spatial_task 2 1" in lines
    assert not any(l.endswith(" 0") for l in lines)   # no seed 0


def test_hygiene_moves_planner_created_files_into_the_run_dir(bash, tmp_path):
    """Per-seed clean slate: run k must not inherit run k-1's notes."""
    res = fake_resources(tmp_path)
    members = tmp_path / "members.txt"
    members.write_text("libero/memory\n")
    (res / "libero" / "memory" / "note_the_planner_wrote.md").write_text("x")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    r = bash(f'source {SCRIPT}; hygiene_after_seed {run_dir} {members}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert not (res / "libero" / "memory").exists(), "path not restored to absent"
    moved = run_dir / "planner_created_memory" / "libero" / "memory"
    assert (moved / "note_the_planner_wrote.md").is_file(), "evidence not preserved"


def test_hygiene_is_a_noop_when_nothing_was_created(bash, tmp_path):
    res = fake_resources(tmp_path)
    members = tmp_path / "members.txt"
    members.write_text("libero/results_spatial_pert\n")   # never existed
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    r = bash(f'source {SCRIPT}; hygiene_after_seed {run_dir} {members}',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert not (run_dir / "planner_created_memory").exists()


def test_dry_run_prints_the_plan_and_stashes_nothing(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --dry-run',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "libero_spatial_task 2 1" in r.stdout
    assert "libero/memory" in r.stdout          # reports what WOULD be hidden
    assert (res / "libero" / "memory" / "MEMORY.md").is_file(), "dry run stashed!"


def test_dry_run_limit_truncates_the_plan(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --dry-run --limit 3',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    cells = [l for l in r.stdout.split("\n") if l.startswith("libero_")]
    assert len(cells) == 3


def test_rejects_unknown_argument(bash, tmp_path):
    res = fake_resources(tmp_path)
    r = bash(f'bash {SCRIPT} --bogus',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 64
    assert "usage" in r.stderr


def test_day8_wrapper_delegates_with_the_v2_hiddenmem_manifest(bash, tmp_path):
    """The Day-8 entry point documented in the handoff must still work."""
    res = fake_resources(tmp_path)
    r = bash(f'bash {HIDDENMEM} --dry-run',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode == 0, r.stderr
    assert "v2-hiddenmem" in r.stdout
    cells = [l for l in r.stdout.split("\n") if l.startswith("libero_")]
    assert len(cells) == 5
    assert all(c.startswith("libero_object_swap 2 ") for c in cells)
