# Selected provenance — main benchmark (280 territories)

Minimal set of committed artefacts needed to verify the headline numbers in
[`docs/RESULTS_AND_LIMITATIONS.md`](../../../docs/RESULTS_AND_LIMITATIONS.md) that come from the
280-territory main benchmark. Named after the scientific protocol, not the legacy internal
experiment identifier (see `docs/EXPERIMENT_PROVENANCE.md`, "Naming").

- `benchmark_summary.json` — the final, frozen per-method/per-width summary table. Copy of the
  primary worktree's `hpc_results/herald93/benchmark_summary_v2.json` (v2 = post-correction,
  after commit `36ede89` fixed the frozen-scorer defect); byte-identical, checksum in
  `manifest.json`.
- `tasks/` — all 70 per-(method, scenario, seed, width) task records that
  `benchmark_summary.json` aggregates. Copy of `hpc_results/herald93/tasks_v2/`.
- `manifest.json` — path, checksum, size, scientific role, commit, and protocol for every file
  here, plus what was deliberately **not** selected (the pre-correction v1 summary, and the
  pre-fix `tasks_frozen_scorer/` run) and why.

**Not versioned here, and not needed to verify these numbers:** `hpc_results/herald94/`,
`herald95/`, `herald96/` — already committed in full by an earlier commit (`ce1a3c8`); the
temporal-representation-gain and oracle numbers in `docs/RESULTS_AND_LIMITATIONS.md` are read
directly from those, read-only, by `tests/test_selected_benchmark_provenance.py`.

## Reconstruction test

```bash
python3 -m pytest tests/test_selected_benchmark_provenance.py -v
```

Recomputes best forecast skill, edge AUPRC vs. prevalence, the with-mechanism/no-mechanism
comparison, the temporal-representation gain range, both protocols' oracle values, and the
all-pairs AUPRC-at-prevalence result directly from these files (and from the already-committed
`herald94`/`95`/`96` artefacts), and fails if any of them no longer matches
`docs/RESULTS_AND_LIMITATIONS.md`.
