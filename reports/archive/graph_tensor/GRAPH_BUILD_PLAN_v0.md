# Graph Build Plan v0

Data: 2026-04-09

Objetivo:

- registrar a regra do primeiro grafo `ZE2020`

## Regra do grafo inicial

- no = `zone d'emploi 2020`
- aresta = adjacencia geografica por contiguidade de fronteira
- exportacao inicial em lista de arestas direcionadas

## Justificativa

- e a forma mais defensavel de abrir o grafo sem inventar peso relacional
- continua compativel com extensao futura por mobilidade
- e suficiente para a fase pre-STGNN

## Artefatos esperados

- `graph_nodes_ze2020_v0.csv`
- `graph_edges_ze2020_v0.csv`
- `graph_ze2020_quality_v0.json`
