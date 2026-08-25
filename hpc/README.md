# HPC job scripts

SLURM scripts for the Mésocentre cluster. None was (re)launched by the repository-cleanup
branch — every job directory here holds the *scripts*, and `hpc_results/` (siblings, not
duplicates) holds the *committed outputs* of runs already completed.

```text
hpc/
├── herald90/ … herald96/        # the known-truth synthetic benchmark stage — herald93 is the
│                                 # main-benchmark driver for the canonical model, see below
├── france_ze2020/, france_ze2020_dynamic_graph/, france_ze2020_relation_objective/,
│   france_ze2020_context_sector_relation/, france_ze2020_top3_entry{,_lift}/
│                                 # the France ZE2020 single-signal relation-gate chain,
│                                 # closed — see ../docs/EXPERIMENT_PROVENANCE.md §7
├── phase4/                       # pre-lettered, pre-Q7 international harmonization search
├── phase5/                       # fixed-L2 residual corrector, closed (NOT_SUPPORTED)
├── phase6_dynamic_dual_graph/    # P6 dual graph, closed (DUAL_GRAPH_S1_FAIL)
├── phase7_sector_precedence/     # sector→sector precedence graph (descriptive evidence layer)
├── phase9_synthetic_generalization/, phase10_synthetic_lagged/
│                                 # earlier synthetic-benchmark iterations, superseded by herald93-98
├── audit/, forecast/, validation/  # standalone audit/forecast/validation runners, mixed vintage
└── tools/                        # cluster transfer/setup helpers
```

`hpc/regime/`, `hpc/archive/`, and `hpc/research/` — the pre-Q7 regime-search, legacy-run, and
V7-research-battery script groups — were archived out of this branch (not deleted; recoverable
via git history and the external cleanup archive). See
[`../docs/EXPERIMENT_PROVENANCE.md`](../docs/EXPERIMENT_PROVENANCE.md) §7-9 for exactly which
scripts moved and why, and for the real (but itself historical) dependency `hpc/phase4/`,
`hpc/validation/`, `hpc/audit/`, and `hpc/forecast/` still have on the four `train_herald_*`
files kept in `src/modeles/`.

## The canonical model's job

`hpc/herald93/run_model_benchmark.py` is the driver behind every main-benchmark number in
[`../docs/RESULTS_AND_LIMITATIONS.md`](../docs/RESULTS_AND_LIMITATIONS.md). The minimal
provenance needed to verify those numbers — the frozen summary and every per-task record — is
versioned at [`../results/selected/main_benchmark/`](../results/selected/main_benchmark/), not
copied here; see that folder's own manifest for what was selected and why, and
`../tests/test_selected_benchmark_provenance.py` for the reconstruction it backs. Run it
locally, at a small scale, through the neutral entrypoint:

```bash
./scripts/run_model_smoke.sh
```

Full job-index and machine-readable registry: `HPC_PHASE_INDEX.md`, `hpc_phase_registry.json`.
Every job's classification (active, historical, closed, superseded) against its decision-log
entry: `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md`.

## Conventions

- Every job writes to a uniquely dated `OUT_ROOT`; no script overwrites a previous run's output.
- Raw outputs stay in `hpc_results/`; only small, versioned summaries move to `reports/`.
- A phase name alone does not tell you whether a job is active — check it against the decision
  log (`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`) or the HPC/results map above before
  citing a number from it.
