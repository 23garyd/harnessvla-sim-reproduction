from .conftest import REPO

LAUNCHERS = REPO / "track" / "launchers"
LIB = LAUNCHERS / "planner_env.sh"


def test_run_planner_strips_billing_keys(bash):
    r = bash(
        f'source "{LIB}" && '
        'ANTHROPIC_API_KEY=leak1 OPENAI_API_KEY=leak2 '
        'run_planner bash -c '
        '\'echo "${ANTHROPIC_API_KEY:-UNSET}:${OPENAI_API_KEY:-UNSET}"\''
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "UNSET:UNSET"


def test_run_planner_passes_through_other_env(bash):
    r = bash(
        f'source "{LIB}" && '
        "LIBERO_TYPE=pro run_planner bash -c 'echo $LIBERO_TYPE'"
    )
    assert r.stdout.strip() == "pro"


def test_every_launcher_uses_run_planner():
    """Any launcher that invokes rpent or a claude CLI must go through
    run_planner (the env -u strip). Guards future launchers."""
    offenders = []
    for sh in LAUNCHERS.glob("*.sh"):
        if sh.name == "planner_env.sh":
            continue
        text = sh.read_text()
        if ("rpent" in text or "claude" in text) and "run_planner" not in text:
            offenders.append(sh.name)
    assert offenders == []
