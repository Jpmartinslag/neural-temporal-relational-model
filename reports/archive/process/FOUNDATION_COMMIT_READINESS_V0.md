# Foundation Commit Readiness v0

Data: 2026-04-09

Objetivo:

- fechar o escopo do commit que congela a base concreta do projeto antes da etapa do modelo com grafo

## O que ja esta suficientemente concreto

### 1. Fundacao territorial

- [commune_to_ze2020_2026.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/mappings/commune_to_ze2020_2026.csv)
- [graph_nodes_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_core_v0.csv)
- [graph_edges_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_core_v0.csv)
- [graph_node_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_node_index_core_v0.csv)
- [graph_edge_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edge_index_core_v0.csv)

### 2. Datasets canônicos do MVP

- [zones_master_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_core_v0.csv)
- [panel_zones_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/panel_zones_core_v0.csv)
- [population_history_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/population_history_ze2020_core_v0.csv)
- [zan_consumption_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zan_consumption_ze2020_core_v0.csv)
- [pre_stgnn_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/pre_stgnn_dataset_core_v0.csv)

### 3. Policy layers

- [policy_commune_status_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/policy_commune_status_v0.csv)
- `ZRR`, `QPV` e `ZAN` ja estao em formato ativo

### 4. Target e baseline

- [target_proxy_candidate_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_candidate_core_v0.csv)
- [target_proxy_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_annual_core_v0.csv)
- [baseline_annual_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/baseline_annual_dataset_core_v0.csv)
- [baseline_annual_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/baseline_annual_predictions_core_v0.csv)

### 5. Evidencia metodologica

- [TARGET_PROXY_CANDIDATE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_PROXY_CANDIDATE_CORE_V0.md)
- [BASELINE_ANNUAL_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/archive/benchmarks/BASELINE_ANNUAL_TARGET_CORE_V0.md)
- [BASELINE_ANNUAL_EVALUATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/archive/benchmarks/BASELINE_ANNUAL_EVALUATION_V0.md)
- [CONSISTENCY_REVIEW_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/CONSISTENCY_REVIEW_v0.md)
- [SCAN_REVIEW_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/archive/process/SCAN_REVIEW_V0.md)

## O que o commit deve representar

Este commit deve marcar:

- fim da fase de base analitica concreta
- inicio da fase de modelagem
- benchmark minimo oficial fixado como `persistence`

Mensagem recomendada:

- `freeze core data foundation target proxy and annual baseline`

## O que nao deve entrar no commit

- `.venv`
- `scan_output`
- bundles temporarios
- artefatos redundantes fora do fluxo vivo
- `data/raw/`

## Leitura final

O projeto ja tem base suficiente para:

1. iniciar o primeiro modelo com grafo anual
2. comparar contra `persistence`
3. manter a trilha metodologica auditavel
