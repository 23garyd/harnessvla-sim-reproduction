from .conftest import REPO

ENV = REPO / "track" / "setup" / "track_env.sh"


def test_track_env_exports(bash):
    r = bash(
        f'source "{ENV}" && '
        'echo "$CUDA_VISIBLE_DEVICES|$LIBERO_TYPE|$MUJOCO_GL|$PI05_CHECKPOINT_PATH'
        '|$SAM3_CHECKPOINT_PATH"'
    )
    assert r.returncode == 0, r.stderr
    cuda, libero, mujoco, ckpt, sam3 = r.stdout.strip().split("|")
    assert cuda == "0"
    assert libero == "pro"
    assert mujoco == "egl"
    assert ckpt == str(REPO / "checkpoints" / "rlinf-pi05-libero-130-fullshot-sft")
    assert sam3 == str(REPO / "checkpoints" / "sam3" / "sam3.pt")


def test_track_env_repo_derived_from_location(bash):
    # REPO must come from the file's own location, not the caller's cwd.
    r = bash(f'cd /tmp && source "{ENV}" && echo "$PI05_CHECKPOINT_PATH"')
    assert r.stdout.strip().startswith(str(REPO)), r.stdout


def test_track_env_fails_loudly_under_non_bash(bash):
    # dash has no BASH_SOURCE; without the guard it would silently set REPO=/.
    r = bash(f'sh -c \'. "{ENV}" && echo "$PI05_CHECKPOINT_PATH"\'')
    assert "FATAL" in r.stderr
    assert "//checkpoints" not in r.stdout
