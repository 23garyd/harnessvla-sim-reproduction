"""Day-8 paired comparison over the ledger (experiment v1 direct vs v2
harness).

Rules frozen at the Day-5 protocol freeze:
- success is the ledger's predicate-derived 1/0; infra_failure rows are
  excluded (they are documented attempts, not scored outcomes);
- aggregation is over COMPLETE (task, seed) pairs only — a seed missing
  either condition is reported under `unpaired`, never averaged over;
- intervals are Wilson score intervals (z=1.96), chosen over normal
  approximation because cell n=5 and several k are 0 or n.
"""
import argparse
import csv
import math

Z = 1.96


def wilson_interval(k, n, z=Z):
    """Wilson score interval for k successes in n trials."""
    if n <= 0:
        raise ValueError(f"n must be > 0, got {n}")
    if not 0 <= k <= n:
        raise ValueError(f"k must be in [0, {n}], got {k}")
    z2 = z * z
    center = (k + z2 / 2) / (n + z2)
    half = (z / (n + z2)) * math.sqrt(k * (n - k) / n + z2 / 4)
    return (max(0.0, center - half), min(1.0, center + half))


def paired_table(rows):
    """Build the paired comparison from ledger rows (list of dicts with
    condition/task/seed/success/validity). Returns cells, aggregate,
    paired flip counts, and the unpaired outcomes that were excluded."""
    scored = {}
    for r in rows:
        if r["validity"] == "infra_failure":
            continue
        key = (r["task"], r["seed"], r["condition"])
        if key in scored:
            raise ValueError(f"duplicate scored row for {key}")
        scored[key] = int(r["success"])

    pairs, unpaired = {}, []
    for (task, seed, cond) in sorted(scored):
        other = "harness" if cond == "direct" else "direct"
        if (task, seed, other) in scored:
            if cond == "direct":
                pairs[(task, seed)] = (scored[(task, seed, "direct")],
                                       scored[(task, seed, "harness")])
        else:
            unpaired.append((task, seed, cond))

    def summarize(outcomes):
        k, n = sum(outcomes), len(outcomes)
        return {"k": k, "n": n, "wilson": wilson_interval(k, n)}

    cells = {}
    for (task, _seed), (d, h) in pairs.items():
        cells.setdefault(task, {"direct": [], "harness": []})
        cells[task]["direct"].append(d)
        cells[task]["harness"].append(h)
    cells = {task: {cond: summarize(v[cond]) for cond in ("direct", "harness")}
             for task, v in sorted(cells.items())}

    flips = {"rescued": 0, "regressed": 0, "both_pass": 0, "both_fail": 0}
    for d, h in pairs.values():
        flips[{(0, 1): "rescued", (1, 0): "regressed",
               (1, 1): "both_pass", (0, 0): "both_fail"}[(d, h)]] += 1

    aggregate = {cond: summarize([p[i] for p in pairs.values()])
                 for i, cond in enumerate(("direct", "harness"))}
    return {"cells": cells, "aggregate": aggregate, "flips": flips,
            "unpaired": unpaired}


def _fmt(s):
    lo, hi = s["wilson"]
    return f"{s['k']}/{s['n']} [{lo:.2f}, {hi:.2f}]"


def render_markdown(table):
    lines = [
        "| cell | direct k/n [Wilson 95%] | harness k/n [Wilson 95%] |",
        "|---|---|---|",
    ]
    for task, cell in table["cells"].items():
        lines.append(f"| {task} | {_fmt(cell['direct'])} "
                     f"| {_fmt(cell['harness'])} |")
    agg = table["aggregate"]
    lines.append(f"| **aggregate (complete pairs)** "
                 f"| {_fmt(agg['direct'])} | {_fmt(agg['harness'])} |")
    f = table["flips"]
    lines.append("")
    lines.append(f"Paired flips: {f['rescued']} rescued (direct fail, "
                 f"harness pass), {f['regressed']} regressed, "
                 f"{f['both_pass']} both-pass, {f['both_fail']} both-fail.")
    if table["unpaired"]:
        lines.append("")
        lines.append(f"Excluded as unpaired (never averaged over): "
                     f"{table['unpaired']}")
    lines.append("")
    lines.append("Wall-clock columns are NOT compared: harness "
                 "wall_seconds is launcher-clock and includes ~3-4 min "
                 "server boot, unlike direct.")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ledger", default="artifacts/ledger.csv")
    args = p.parse_args()
    with open(args.ledger) as f:
        rows = list(csv.DictReader(f))
    print(render_markdown(paired_table(rows)))


if __name__ == "__main__":
    main()
