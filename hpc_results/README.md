# HPC job outputs

Committed raw outputs from completed cluster runs. This is a compute archive, not the
project's main structure — start from [`../docs/RESULTS_AND_LIMITATIONS.md`](../docs/RESULTS_AND_LIMITATIONS.md)
for what these artefacts actually support, not from browsing this folder.

```text
hpc_results/
├── herald94/   # temporal representation + composite-signal results (11-24% gain range)
├── herald95/   # relational-scale oracle ladder
├── herald96/   # residual/multirelational diagnostic, all-pairs recovery test
└── phase7_nl_gemeente_proxy/   # NL gemeente proxy Phase 7 output — blocked for relation labels
```

Mirrored into git by commit `ce1a3c8`, specifically so that every figure and audit line in
`reports/final_visual_evidence/` is reproducible from the repository alone (protected — do not
regenerate; see `../docs/EXPERIMENT_PROVENANCE.md` §11).

## The main benchmark's raw output is not mirrored here

`hpc_results/herald93/` (the 280-territory main-benchmark run) is **not** committed in full —
only the minimal subset needed to verify its reported numbers, versioned separately at
[`../results/selected/main_benchmark/`](../results/selected/main_benchmark/) with its own
manifest and checksums. See `../docs/EXPERIMENT_PROVENANCE.md` §4/§11 for why the full raw
directory was not mirrored the way `herald94-96` were.

## What was archived out of this branch

`hpc_results/herald_semi_total_253_geo2025/` (pre-Q7 V6/Semi run), `imported_from_vm_20260501/`
(provenance not independently re-verified), `final_model_comparison_20260429/` (pre-Q7, partial),
and `herald_v6_observed2025_20260430_142920/` were archived, not deleted — recoverable via git
history and the external cleanup archive. Full HPC/results classification, job by job, against
its decision-log entry: `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md`.

## What belongs in git, and what doesn't

Keep only if small and useful: a README, an aggregated metrics JSON/CSV, a small final summary.
Never commit per-seed prediction CSVs, `.npz` internals, `.out`/`.err` logs, or raw transfer
archives — those stay on the cluster or in a local, gitignored cache. Anything a dashboard or a
report figure needs should be exported to `reports/metrics/` or `reports/dashboards/`, not read
from here directly.
