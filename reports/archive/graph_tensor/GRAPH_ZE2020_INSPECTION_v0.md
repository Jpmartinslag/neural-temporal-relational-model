# Graph ZE2020 Inspection v0

Data: 2026-04-09

Artefatos:

- [build_ze2020_graph_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_ze2020_graph_v0.py)
- [graph_nodes_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_v0.csv)
- [graph_edges_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_v0.csv)
- [graph_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_ze2020_quality_v0.json)

## Regra aplicada

- adjacencia geografica por contiguidade de fronteira com `touches()`
- exportacao de arestas direcionadas

## Resultado estrutural

- `306` nos
- `1552` arestas direcionadas
- `776` arestas nao direcionadas
- `2` nos isolados
- `8` componentes conectados

## Nos isolados

- `0103 / Marie-Galante`
- `0601 / Mayotte`

## Leitura metodologica

- os componentes desconectados nao indicam erro por si so
- a fragmentacao e coerente com ilhas e territorios ultramarinos
- o grafo inicial continua valido como estrutura geografica

## Consequencia pratica

- o grafo pode entrar como base do bloco pre-STGNN
- a presenca de componentes desconectados deve ficar explicita
- mobilidade ou arestas funcionais futuras poderao reduzir esse isolamento
