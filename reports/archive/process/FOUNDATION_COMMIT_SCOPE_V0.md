# Foundation Commit Scope v0

Data: 2026-04-09

Objetivo:

- definir exatamente o que entra e o que fica fora do commit que congela a base concreta do projeto

## Commit purpose

This commit marks the end of the data foundation phase and the start of the graph-modeling phase.

## Recommended commit message

`freeze core data foundation target proxy and annual baseline`

## Include in commit

### Code

- `src/data/*.py`
- `src/data/scan_full_repository_v0.sh`
- `requirements.txt`
- `.gitignore`

### Metadata

- `metadata/dataset_inventory.csv`
- `metadata/panel_feature_registry_v0.csv`
- `metadata/policy_layers_registry_v0.csv`
- `metadata/pre_stgnn_feature_registry_core_v0.csv`
- `metadata/source_time_coverage_matrix_v0.csv`
- `metadata/variable_dictionary_seed.csv`

### Interim data actually used by the pipeline

- `data/interim/mappings/`
- `data/interim/tables/`
- `data/interim/policy/`
- `data/interim/population_history/`

### Processed canonical artifacts

- `data/processed/graph_*`
- `data/processed/panel_zones*`
- `data/processed/population_history_ze2020*`
- `data/processed/pre_stgnn_*`
- `data/processed/target_proxy_*`
- `data/processed/baseline_annual_*`
- `data/processed/zan_consumption_ze2020*`
- `data/processed/zones_master_annual_core_v0.csv`
- `data/processed/zones_master_annual_v0.csv`

### Reports and project memory

- `reports/`

## Exclude from commit

### Raw source archives and bulky source downloads

- `data/raw/`
- top-level source archives already covered by raw inventory rules

### Local environment and temporary artifacts

- `.venv/`
- `scan_output/`
- `scan_output_bundle.tar.gz`

## Rationale

- raw downloads remain reproducible inputs, not foundation artifacts
- the commit should freeze the usable analytical layer, not the whole acquisition cache
- this keeps the repository smaller and the transition to modeling cleaner

## Practical staging rule

Stage everything from the live pipeline, but do **not** stage `data/raw/`, `.venv/`, or scan outputs.
