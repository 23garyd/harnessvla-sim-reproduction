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


def _tree_fingerprint(root):
    """(relative path, bytes) for every file under root, order-independent."""
    return sorted((str(p.relative_to(root)), p.read_bytes())
                  for p in root.rglob("*") if p.is_file())


def test_self_check_stashes_then_restores_via_the_trap(bash, tmp_path):
    """REGRESSION (2026-07-29): the first v4 pilot left the released assets
    stashed because the EXIT trap's restore() referenced main()'s *local*
    variables, so under `set -u` it died on `stash_tar: unbound variable`
    before extracting. pin_check cannot catch it -- RPent/resources/ is
    gitignored -- so only an end-to-end stash+restore check can.
    """
    res = fake_resources(tmp_path)
    (res / "libero" / "memory" / "leaf.md").write_text("content that must survive")
    (res / "libero" / "results_object_pert" / "object_swap_t2_s0.json").write_text("{}")
    before = _tree_fingerprint(res)

    r = bash(f'bash {SCRIPT} --self-check',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})

    assert r.returncode == 0, f"self-check failed: {r.stdout}\n{r.stderr}"
    assert "stashed -> opaque tar" in r.stdout
    assert "self-check: stash hid every member" in r.stdout
    assert "restored stashed members (verified present)" in r.stdout, \
        "restore did not run or did not verify"
    assert "unbound variable" not in r.stderr
    assert _tree_fingerprint(res) == before, "resources not restored bit-identically"


def test_self_check_leaves_no_stash_dir_behind(bash, tmp_path):
    """Uses an isolated TMPDIR: globbing the real /tmp would couple this test
    to unrelated leftovers on the machine."""
    res = fake_resources(tmp_path)
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()
    r = bash(f'bash {SCRIPT} --self-check',
             env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res),
                  "TMPDIR": str(tmpdir)})
    assert r.returncode == 0, r.stderr
    assert not list(tmpdir.glob("tsm_ablation.*")), "stash dir not cleaned up"


def test_restore_reports_fatal_and_keeps_the_stash_if_extraction_is_incomplete(
        bash, tmp_path):
    """If restore cannot put everything back it must say so loudly and RETAIN
    the stash, because a silent failure leaves every later run memory-free."""
    res = fake_resources(tmp_path)
    stash = tmp_path / "stash"
    stash.mkdir()
    (stash / "members.txt").write_text("libero/memory\nlibero/never_in_the_tar\n")
    # a tar that restores only one of the two declared members
    r0 = bash(f'tar -C {res} -cf {stash}/stash.tar libero/memory',
              env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r0.returncode == 0, r0.stderr
    r = bash(
        f'source {SCRIPT}; STASH_DIR={stash}; STASH_TAR={stash}/stash.tar; '
        f'MEMBERS_FILE={stash}/members.txt; restore',
        env={"TRACK_REPO": str(REPO), "TRACK_RES": str(res)})
    assert r.returncode != 0
    assert "NOT fully restored" in r.stderr
    assert (stash / "stash.tar").is_file(), "stash must be retained for manual recovery"
