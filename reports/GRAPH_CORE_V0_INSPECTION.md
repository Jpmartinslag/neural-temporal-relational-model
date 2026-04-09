# Graph Core v0 Inspection

Data: 2026-04-09

Artefatos:

- [build_ze2020_graph_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_ze2020_graph_core_v0.py)
- [graph_nodes_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_core_v0.csv)
- [graph_edges_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_core_v0.csv)
- [graph_excluded_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_excluded_ze2020_core_v0.csv)
- [graph_ze2020_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_ze2020_core_quality_v0.json)

## Regra aplicada

- manter apenas a maior componente conectada do grafo geografico `ZE2020`

## Resultado

- `280` nos no `core_v0`
- `1486` arestas direcionadas
- `26` nos excluidos do MVP

## O que saiu do `core_v0`

- Corse
- Guadeloupe
- Martinique
- Guyane
- La Réunion
- Mayotte

## Leitura metodologica

- o `core_v0` passa a representar a Francia continental
- os territorios excluidos nao sao descartados do projeto
- eles apenas deixam de contaminar o primeiro ciclo do MVP
