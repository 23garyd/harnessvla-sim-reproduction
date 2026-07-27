"""Verify the frozen manifest's seeds map to distinct LIBERO init states.

Mirrors env_server.py's mapping (rid = first_id + seed % trials) and checks
that seed 0 and every scored seed select pairwise-distinct init-state vectors.
Run with the stack venv; writes a committable report next to the manifest.

Run: .venv/bin/python track/smoke/verify_seed_mapping.py [manifest.json]
Exit: 0 all distinct, 1 any collision.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from liberopro.liberopro.benchmark import get_benchmark  # noqa: E402


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    manifest_path = Path(args[0]) if args else REPO / "track/manifests/core_v1.json"
    manifest = json.loads(manifest_path.read_text())
    report_path = manifest_path.with_name(manifest_path.stem + "_seed_check.txt")

    lines = [f"Seed-mapping verification for {manifest_path.name}",
             "rule: rid = first_id + (seed % trials)  (env_server.py:90-92)", ""]
    ok = True
    for cell in manifest["cells"]:
        suite_name, task_id = cell["suite"], cell["task_id"]
        seeds = [0] + sorted(e["seed"] for e in cell["seeds"]
                             if not e["bootstrap_only"])
        suite = get_benchmark(suite_name)()
        states = np.asarray(suite.get_task_init_states(task_id))
        trials = len(states)
        rids = [s % trials for s in seeds]
        sel = states[rids]
        unique = len({tuple(r) for r in sel.round(10).tolist()})
        cell_ok = unique == len(seeds)
        ok &= cell_ok
        lines.append(
            f"{suite_name} t{task_id}: trials={trials} seeds={seeds} "
            f"rids={rids} distinct_states={unique}/{len(seeds)} "
            f"{'OK' if cell_ok else 'COLLISION'}")
        lines.append(f"    language: {suite.get_task(task_id).language}")
    lines.append("")
    lines.append("RESULT: " + ("all distinct" if ok else "COLLISION FOUND"))
    report = "\n".join(lines) + "\n"
    report_path.write_text(report)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
