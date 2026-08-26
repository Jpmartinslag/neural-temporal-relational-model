# Source code

Model, baselines, data pipelines, analysis, and dashboard generation.

```text
src/
├── data/           # ingestion + panel/graph builders (data/france_ze2020/, data/european_panel/, data/synthetic/)
├── modeles/        # models, baselines, training/evaluation (modeles/france_ze2020/, modeles/synthetic/, modeles/real_world/)
├── analyse/        # narrow-purpose statistical analysis and gate selection
└── visualisation/  # dashboard HTML generation
```

`modeles/` keeps its French spelling — not renamed to `models/` — because doing so would touch
imports across roughly 180 tracked files for no functional gain; see
[`../docs/EXPERIMENT_PROVENANCE.md`](../docs/EXPERIMENT_PROVENANCE.md) §6.

## The canonical model

The Neural Temporal–Relational Model's implementation is
`src/modeles/france_ze2020/herald93_benchmark.py`, driven by
`hpc/herald93/run_model_benchmark.py` and its generator,
`src/data/synthetic/generate_france_multisignal_v92.py`. Every component (temporal encoder,
relational scorer, candidate-support handling, loss, no-mechanism control, widths, seeds) is
confirmed against the description in `../docs/PROJECT_OVERVIEW.md` and audited line-by-line in
`../docs/EXPERIMENT_PROVENANCE.md` §2 — not chosen for having the highest version number.

Run it through the neutral public entrypoint, not by importing the module directly:

```bash
./scripts/run_temporal_relational_model.py --smoke
```

`HERALD` is this project's legacy internal experiment identifier, not its public name — see
`../docs/EXPERIMENT_PROVENANCE.md` §1. It survives in filenames and module paths because
renaming ~200 files under active test coverage this close to delivery was judged higher-risk
than valuable; it does not appear as the project's name in any of the 6 public documents.

## Historical and closed code

Several files here predate the current model or belong to a branch the decision log closed —
kept for provenance, not imported by the canonical model, and not part of the active pipeline:

- `train_herald_{v3,v4,v5,v6,v7}.py`, `train_herald_semi_v1.py`,
  `train_dynamic_stgnn_models_v1.py`, `build_dynamic_stgnn_feature_panel_v1.py`,
  `integrate_side_2025_for_herald_v6.py`, `herald_regime_modes.py` — the pre-Q7 France
  architecture search.
- `train_dual_graph_experiment.py`, `dual_graph_models.py`, `run_dual_graph_{pilot,smoke}.py` —
  the P6 dynamic dual graph, closed (`DUAL_GRAPH_S1_FAIL`).
- `graph_temporal_models.py`, `graph_temporal_train.py`, `run_e0_smoke_nl{,_v2}.py`,
  `run_s0_fr_smoke.py`, `run_s1_fr_local.py` — the graph-temporal (GConvGRU/EvolveGCN-H)
  branch, closed (`S1_FR_FAIL`).
- `phase5/` — the fixed-L2 residual corrector, closed (`NOT_SUPPORTED`).
- `run_ardeco_ridge_fr.py` — closed exploration.
- `train_herald_v6.py`, `train_herald_v7.py`, `train_herald_semi_v2.py`,
  `train_herald_regime_experiment.py` specifically: none of the four participates in, is
  imported by, or is tested alongside the canonical model above. They are still under active
  edit in the primary worktree as of this pass and were left untouched — see
  `../docs/EXPERIMENT_PROVENANCE.md` §10 for the full dependency audit, including the real (but
  itself historical) callers in `hpc/phase4/`, `hpc/validation/`, `hpc/audit/`, `hpc/forecast/`.

Full classification of every module (active, historical, closed, research-track):
`reports/canonical/HERALD_10_CODE_PATH_MAP.md`.

## Active research track, not yet a validated result

`modeles/synthetic/`, `modeles/real_world/`, and `data/synthetic/` (beyond the France
multisignal generator above) hold the relation-learning research line behind the known-truth
benchmark. Read their results, and what they do and do not demonstrate, in
[`../docs/RESULTS_AND_LIMITATIONS.md`](../docs/RESULTS_AND_LIMITATIONS.md) — not from a source
file's docstring alone.
