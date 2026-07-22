# France ZE2020 context-conditioned sector-relation gate

This package executes the pre-registered DEC-077/HERALD_48 diagnostic.

- Five Slurm tasks run seeds 42--46 independently.
- Each task evaluates years 2019--2025 and five ZE-disjoint folds.
- Outputs are isolated under
  `hpc_results/fr_ze2020_context_sector_relation_<RUN_ID>/seed_<SEED>/`.
- The submitter is a dry run unless `--confirm-submit` is supplied.
- The post-run audit aggregates the five seed outputs without promoting claims.

The gate tests transferable, context-conditioned lagged sector association. It
does not establish causal effects, a dynamic graph-neural model, or automated
territorial action.
