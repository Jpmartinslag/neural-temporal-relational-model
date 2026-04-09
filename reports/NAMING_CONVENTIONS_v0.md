# Naming Conventions

Data: 2026-04-09

Objetivo:

- manter nomes previsiveis no repositorio
- reduzir ambiguidade entre script, dado, relatorio e documento vivo
- facilitar leitura, busca e manutencao do pipeline

## Regra geral

- nomes tecnicos ficam em `snake_case`
- nomes de artefatos versionados terminam em `_vN` quando houver versao canonica
- evitar abreviacoes novas sem necessidade
- o nome deve explicitar a acao ou o conteudo principal

## Scripts Python

Padrao:

- `verbo_objeto_escopo_vN.py`

Verbos permitidos na pratica:

- `build`
- `extract`
- `integrate`
- `update`
- `validate`

Exemplos:

- `build_zones_master_v0.py`
- `extract_qpv_tables_v0.py`
- `integrate_qpv_policy_commune_status_v0.py`

## CSV e JSON

Padrao:

- `objeto_escopo_vN.csv`
- `objeto_escopo_vN.json`

Exemplos:

- `policy_commune_status_v0.csv`
- `population_history_ze2020_v0.csv`
- `policy_commune_status_quality_v0.json`

## Relatorios Markdown

Dois grupos:

- documentos vivos do projeto em maiusculas:
  - `PROJECT_JOURNEY.md`
  - `PROJECT_EXPLANATIONS.md`
  - `PHASE1_GRAPH_ROADMAP.md`
- relatorios tecnicos versionados:
  - `TOPIC_ACTION_vN.md`
  - `TOPIC_DESIGN.md` quando forem documentos de desenho ainda nao versionados por iteracao

Exemplos:

- `ZRR_TABLES_INSPECTION_v0.md`
- `POLICY_DOWNLOAD_ORGANIZATION_v0.md`
- `PANEL_ZONES_DESIGN.md`

## Regra operacional

- arquivos novos devem nascer ja no padrao
- arquivos antigos so devem ser renomeados quando houver ganho real de consistencia
- nomes entram no journal e nas explicacoes quando a mudanca afetar o fluxo do projeto
