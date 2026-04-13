# Project Recomm Dataset

Base territorial e temporal para recomendacao economica em zonas de emprego francesas (`ZE2020`).

Este repositorio ainda nao contem a arquitetura final. O estado atual consolida dados, grafos, targets oficiais e baselines auditaveis para decidir quando faz sentido avancar para modelos grafo-temporais.

## Entrada Principal

Leia primeiro:

- `reports/PROJECT_STATE_INDEX_V0.md`
- `reports/PROJECT_JOURNEY.md`
- `metadata/canonical_artifacts_v0.csv`

## Artefatos Canonicos Atuais

- Unidade territorial: `data/processed/graph_nodes_ze2020_core_v0.csv`
- Grafo geografico: `data/processed/graph_adjacency_core_v0.csv`
- Grafo de mobilidade: `data/processed/mobility_adjacency_row_normalized_core_v0.csv`
- Target principal: `data/processed/target_side_establishments_annual_core_v0.csv`
- Dataset longo do target SIDE: `data/processed/long_history_side_target_dataset_core_v0.csv`
- Baseline de referencia: persistencia local
- Desafiante atual: ridge autoregressivo, condicionado por regime temporal

## Regra De Higiene

- `data/raw/` nao deve entrar no Git.
- Arquivos brutos, downloads, caches, scans e saidas exploratorias devem ficar fora do fluxo principal.
- Novos artefatos so devem ser criados se aparecerem em `metadata/canonical_artifacts_v0.csv` ou forem marcados como diagnostico temporario.
- Antes de criar nova arquitetura, atualizar o indice do projeto e justificar qual baseline ela precisa superar.

## Estado Metodologico Atual

- Persistencia continua sendo o baseline conservador obrigatorio.
- Ridge ajuda em anos de aceleracao agregada forte, mas falha em anos estaveis.
- Segmentacao por perfil de zona foi promissora em uma janela fixa, mas nao se sustentou no backtest rolante.
- Grafos geografico e de mobilidade existem, mas media simples de vizinhos falhou; qualquer uso futuro de grafo precisa ser mais seletivo.
