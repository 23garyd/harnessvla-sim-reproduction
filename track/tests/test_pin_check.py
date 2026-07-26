import shutil
import subprocess

from .conftest import REPO

PIN = REPO / "track" / "setup" / "pin_check.sh"


def git(*args, cwd):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )


def make_track_repo(tmp_path):
    """Fake track repo: track/setup/{pin_check.sh,pins.env} + RPent git clone."""
    setup = tmp_path / "track" / "setup"
    setup.mkdir(parents=True)
    shutil.copy(PIN, setup / "pin_check.sh")
    (setup / "pins.env").write_text("RPENT_COMMIT=\n")
    rpent = tmp_path / "RPent"
    rpent.mkdir()
    git("init", cwd=rpent)
    (rpent / "a.txt").write_text("one\n")
    git("add", "-A", cwd=rpent)
    git("commit", "-m", "c1", cwd=rpent)
    return tmp_path


def run_pin(bash, root, *args):
    argv = " ".join(args)
    return bash(f'"{root}/track/setup/pin_check.sh" {argv}',
                env={"TRACK_REPO": str(root)})


def test_check_fails_when_pin_unset(bash, tmp_path):
    root = make_track_repo(tmp_path)
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "RPENT_COMMIT unset" in r.stderr


def test_record_then_check_ok(bash, tmp_path):
    root = make_track_repo(tmp_path)
    assert run_pin(bash, root, "--record").returncode == 0
    r = run_pin(bash, root)
    assert r.returncode == 0, r.stderr
    assert "pin check OK" in r.stdout


def test_record_refuses_dirty_worktree(bash, tmp_path):
    root = make_track_repo(tmp_path)
    (root / "RPent" / "a.txt").write_text("edited\n")
    r = run_pin(bash, root, "--record")
    assert r.returncode != 0
    assert "dirty" in r.stderr


def test_check_fails_on_drift(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    (root / "RPent" / "b.txt").write_text("two\n")
    git("add", "-A", cwd=root / "RPent")
    git("commit", "-m", "c2", cwd=root / "RPent")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "!=" in r.stderr


def test_check_fails_on_unrecorded_modification(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    (root / "RPent" / "a.txt").write_text("silent edit\n")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "unrecorded" in r.stderr


def test_check_fails_when_rpent_missing(bash, tmp_path):
    root = make_track_repo(tmp_path)
    shutil.rmtree(root / "RPent")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "not a git clone" in r.stderr


def test_unknown_argument_fails(bash, tmp_path):
    root = make_track_repo(tmp_path)
    r = run_pin(bash, root, "--recrod")
    assert r.returncode == 64
    assert "usage:" in r.stderr


def test_pins_env_is_parsed_not_executed(bash, tmp_path):
    root = make_track_repo(tmp_path)
    run_pin(bash, root, "--record")
    marker = root / "pwned"
    pins = root / "track" / "setup" / "pins.env"
    pins.write_text(f'touch "{marker}"\n' + pins.read_text())
    r = run_pin(bash, root)
    assert not marker.exists()
    assert r.returncode == 0, r.stderr


def test_malformed_pin_fails(bash, tmp_path):
    root = make_track_repo(tmp_path)
    pins = root / "track" / "setup" / "pins.env"
    pins.write_text("RPENT_COMMIT=not-a-sha\n")
    r = run_pin(bash, root)
    assert r.returncode != 0
    assert "malformed" in r.stderr
