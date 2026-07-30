"""Leakage audit over the real ablation artifacts.

The hidden-memory condition is only valid if no planner-visible transcript
references hidden memory CONTENT. This audits every ablation run on disk
using the same rules as the queue-time tripwire (track.analysis.leak_rules),
and pins both directions with real data: the two quarantined attempts MUST
trip, and the accepted runs MUST NOT.
"""
import csv
from pathlib import Path

import pytest

from track.analysis import leak_rules

REPO = Path(__file__).resolve().parents[2]
ABLATION = REPO / "artifacts" / "ablation"
ACCEPTED_RUNS = ABLATION / "runs"
QUARANTINED = (
    ABLATION / "attempt1_condition_violated",
    ABLATION / "attempt2_seed4_condition_violated",
    # Found by this very audit on 2026-07-29: two originally-ACCEPTED
    # v2-hiddenmem rows whose transcripts carry Global Memory note names
    # leaked through the HF cache. See its INVALID.md.
    ABLATION / "audit_quarantine_hfcache_seeds1_2",
)


def run_dirs(root):
    """A run dir is any directory containing launcher.log."""
    if not root.is_dir():
        return []
    return sorted(p.parent for p in root.rglob("launcher.log"))


def ledger_versions():
    path = ABLATION / "ledger.csv"
    if not path.is_file():
        return set()
    with open(path) as fh:
        return {row["exp_version"] for row in csv.DictReader(fh)}


def test_accepted_ablation_runs_are_leak_free():
    """The condition held for every run that counts toward results."""
    offenders = {}
    for run in run_dirs(ACCEPTED_RUNS):
        hits = leak_rules.scan_run_dir(run)
        if hits:
            offenders[str(run.relative_to(REPO))] = hits
    assert not offenders, f"hidden-memory condition violated: {offenders}"


def test_audit_actually_scanned_something():
    """No-silent-skip guard: a passing audit that scanned zero files would be
    meaningless. If the ablation ledger has rows, run dirs must exist."""
    if not ledger_versions():
        pytest.skip("no ablation ledger yet")
    assert run_dirs(ACCEPTED_RUNS), (
        "ablation ledger has rows but no run dirs were found to scan")


def test_v4_rows_have_run_dirs_to_audit():
    """Once v4 rows land, they must be present on disk and leak-free."""
    if "v4" not in ledger_versions():
        pytest.skip("v4 not queued yet")
    v4_runs = run_dirs(ACCEPTED_RUNS / "v4")
    assert v4_runs, "v4 rows in the ledger but no v4 run dirs on disk"
    for run in v4_runs:
        assert leak_rules.scan_run_dir(run) == [], f"v4 leak in {run}"


@pytest.mark.parametrize("quarantine", QUARANTINED, ids=lambda p: p.name)
def test_quarantined_attempts_still_trip_the_rules(quarantine):
    """Real-data positive control. Attempt 1 is the run where the planner
    found the in-repo stash with a repo-wide `find` and read the notes back;
    attempt 2 leaked note filenames through the HF cache. If a rules change
    ever stops flagging these, the rules have regressed."""
    if not quarantine.is_dir():
        pytest.skip(f"{quarantine.name} not present")
    runs = run_dirs(quarantine)
    assert runs, f"{quarantine.name} has no run dirs"
    assert any(leak_rules.scan_run_dir(r) for r in runs), (
        f"{quarantine.name} is a known condition violation but the leak "
        "rules no longer detect it")


def test_quarantined_runs_are_not_under_the_accepted_tree():
    """Structural guard: quarantined evidence must never be scanned as
    accepted results, or a violation would enter the result set."""
    accepted = {str(p) for p in run_dirs(ACCEPTED_RUNS)}
    for quarantine in QUARANTINED:
        for run in run_dirs(quarantine):
            assert str(run) not in accepted
