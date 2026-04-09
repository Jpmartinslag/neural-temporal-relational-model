# Diagnostics v0

Data: 2026-04-09

Objetivo:

- visualizar rapidamente o estado dos dados canônicos antes da etapa do grafo
- enxergar cobertura, distribuicao e sinais extremos

Artefatos:

- [diagnostics_summary_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_summary_v0.json)
- [coverage_count_hist_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/coverage_count_hist_v0.png)
- [zones_master_distributions_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/zones_master_distributions_v0.png)
- [panel_observed_feature_count_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/panel_observed_feature_count_v0.png)
- [zan_top_intensity_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/zan_top_intensity_v0.png)

## Resumo

- `zones_master`: `306` linhas
- `panel_zones`: `1224` linhas
- `zan_consumption_ze2020`: `305` linhas
- `305` zonas elegiveis para treino

## Cobertura

Distribuicao de `source_coverage_count`:

- `8`: `297` zonas
- `7`: `8` zonas
- `4`: `1` zona

Leitura:

- a cobertura do `zones_master` esta forte para quase todo o territorio
- a zona com cobertura `4` e a anomalia estrutural ja conhecida

## Painel

Media de `observed_feature_count` por ano:

- `2021`: `1.94`
- `2022`: `6.98`
- `2023`: `3.00`
- `2024`: `4.00`

Leitura:

- `2022` continua sendo o ano mais denso para o nucleo RP
- o painel ainda e ralo, mas coerente com as janelas reais das fontes

## ZAN

Top 5 por `zan_artif_per_pop21`:

- `9406 / Porto-Vecchio`
- `2818 / Vire Normandie`
- `9405 / Ghisonaccia`
- `7510 / Dax`
- `2811 / Honfleur Pont-Audemer`

Leitura:

- a camada `ZAN` ja consegue destacar contrastes territoriais reais
- esses sinais ainda sao apenas diagnosticos, nao regras de agente

## Decisao

- o estado atual ja permite avancar para o primeiro grafo espacial `ZE2020`
- as visualizacoes confirmam que a base esta suficientemente estruturada para essa proxima etapa
