import os
import stat

from .conftest import REPO

LIB = REPO / "track" / "setup" / "setup_lib.sh"
SETUP = REPO / "track" / "setup" / "setup.sh"


def fake_nvidia_smi(tmp_path, name):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    smi = bindir / "nvidia-smi"
    smi.write_text(f'#!/usr/bin/env bash\necho "{name}"\n')
    smi.chmod(smi.stat().st_mode | stat.S_IEXEC)
    return f"{bindir}:{os.environ['PATH']}"


def test_scripts_parse():
    import subprocess
    for script in (LIB, SETUP):
        r = subprocess.run(["bash", "-n", str(script)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{script}: {r.stderr}"


def test_assert_gpu_accepts_a6000(bash, tmp_path):
    path = fake_nvidia_smi(tmp_path, "NVIDIA RTX A6000")
    r = bash(f'source "{LIB}" && assert_gpu', env={"PATH": path})
    assert r.returncode == 0, r.stderr
    assert "GPU0 OK" in r.stdout


def test_assert_gpu_rejects_titan_x(bash, tmp_path):
    path = fake_nvidia_smi(tmp_path, "NVIDIA TITAN X (Pascal)")
    r = bash(f'source "{LIB}" && assert_gpu', env={"PATH": path})
    assert r.returncode != 0
    assert "expected RTX A6000" in r.stderr


def test_verify_checkpoint_record_then_check(bash, tmp_path):
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    (ckpt / "weights.bin").write_bytes(b"pi05" * 100)
    sums = tmp_path / "checkpoint.sha256sums"

    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode == 0, r.stderr
    assert "recorded" in r.stdout
    assert sums.exists()

    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode == 0, r.stderr
    assert "checksum OK" in r.stdout


def test_verify_checkpoint_detects_corruption(bash, tmp_path):
    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()
    (ckpt / "weights.bin").write_bytes(b"pi05" * 100)
    sums = tmp_path / "checkpoint.sha256sums"
    bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    (ckpt / "weights.bin").write_bytes(b"corrupted")
    r = bash(f'source "{LIB}" && verify_checkpoint "{ckpt}" "{sums}"')
    assert r.returncode != 0


def test_setup_usage_on_bad_subcommand(bash):
    r = bash(f'"{SETUP}" frobnicate')
    assert r.returncode == 64
    assert "usage:" in r.stderr
