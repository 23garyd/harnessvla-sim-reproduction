import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


@pytest.fixture
def bash():
    """Run a bash snippet; returns CompletedProcess with .stdout/.stderr/.returncode."""

    def run(script, env=None, cwd=None):
        merged = dict(os.environ)
        merged.update(env or {})
        return subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env=merged,
            cwd=cwd,
        )

    return run
