# Technical recommendations for simulation evaluation and evidence management

Basis: [paired analysis implementation](../../../track/analysis/compare.py), [original memory audit](../../../track/registry/memory_audit.md), and [current ledger recomputation](../nov-m4/paired-analysis.json).

- Compare only complete pairs, and record infrastructure failures, exhausted time budgets, and task failures separately. Wall-clock columns with different startup overheads cannot directly serve as performance comparisons.
- Keep memory conditions, caches, and quarantined rows in separate namespaces; condition changes based on a frozen policy must be traceable to the same task, seed, and model.
- Cite individual simulation cases and aggregate results separately; simulation results do not establish performance for physical robots, wireless links, or industrial deployment.

Further engineering work: provide downloadable archives of the large run directories; complete third-party reproduction after pinning RPent, verifying models, and fixing dependencies; maintain separate experiment records for real links and robot scenarios. The current offline ledger recomputation is not a rerun of the GPU benchmark.
