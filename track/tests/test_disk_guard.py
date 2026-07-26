from track.analysis import disk_guard


def test_usage_bytes_sums_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    (tmp_path / "sub" / "b.bin").write_bytes(b"y" * 500)
    assert disk_guard.usage_bytes(tmp_path) == 1500


def test_usage_bytes_missing_dir_is_zero(tmp_path):
    assert disk_guard.usage_bytes(tmp_path / "nope") == 0


def test_check_under_cap(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 100)
    used, ok = disk_guard.check(tmp_path, cap_bytes=200)
    assert used == 100 and ok is True


def test_check_over_cap(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 300)
    used, ok = disk_guard.check(tmp_path, cap_bytes=200)
    assert used == 300 and ok is False


def test_default_cap_is_200_gb():
    assert disk_guard.DEFAULT_CAP_BYTES == 200 * 1024**3


def test_main_exit_codes(tmp_path, capsys):
    (tmp_path / "a.bin").write_bytes(b"x" * 300)
    assert disk_guard.main(["--path", str(tmp_path), "--cap-bytes", "1000"]) == 0
    assert disk_guard.main(["--path", str(tmp_path), "--cap-bytes", "200"]) == 1
    out = capsys.readouterr().out
    assert "OVER" in out and "OK" in out
