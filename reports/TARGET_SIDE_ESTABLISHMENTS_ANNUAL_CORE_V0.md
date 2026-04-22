# Target SIDE Establishments Annual Core v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- criar um target anual oficial baseado em `SIDE` estabelecimentos
- preservar `SIDE` empresas como alvo alternativo de sensibilidade
- manter o target proxy antigo apenas como auditoria/comparacao

## Artefatos

- fonte agregada: `data/processed/side_communal_creations_ze2020_official_2012_2024_v0.csv`
- target: `data/processed/target_side_establishments_annual_core_v0.csv`
- qualidade: `reports/target_side_establishments_annual_core_quality_v0.json`

## Estrutura

- nos `ZE2020`: `280`
- anos: `2012-2024`
- linhas: `3640`
- coluna principal: `side_establishment_creations_official`
- coluna de sensibilidade: `side_enterprise_creations_official`

## Decisao

- o alvo principal formal passa a ser `side_establishment_creations_official`
- `side_enterprise_creations_official` deve ser usado para teste de sensibilidade
- o proxy anterior nao deve ser interpretado como ground truth final

## Totais Anuais

| Ano | SIDE estabelecimentos | SIDE empresas |
|---:|---:|---:|
| 2012 | 615957 | 542967 |
| 2013 | 602496 | 543622 |
| 2014 | 621698 | 560305 |
| 2015 | 608599 | 543084 |
| 2016 | 649871 | 581286 |
| 2017 | 702642 | 633888 |
| 2018 | 795205 | 723196 |
| 2019 | 915980 | 836677 |
| 2020 | 948339 | 870951 |
| 2021 | 1106794 | 1013787 |
| 2022 | 1119168 | 1021744 |
| 2023 | 1103907 | 1010891 |
| 2024 | 1219089 | 1071065 |
