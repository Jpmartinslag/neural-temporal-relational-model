# SIDE Communal Creations Inspection v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- verificar se os arquivos oficiais `SIDE` comunais de criacoes servem para auditar o target proxy atual
- agregar criacoes oficiais de comuna para `ZE2020`
- comparar os totais oficiais `SIDE` com o target proxy derivado atualmente

## Artefatos

- comunal oficial: `data/interim/tables/side_communal_creations_official_2012_2024_v0.csv`
- agregado `ZE2020`: `data/processed/side_communal_creations_ze2020_official_2012_2024_v0.csv`
- comparacao target proxy vs SIDE: `data/processed/target_proxy_vs_side_official_ze2020_2012_2024_v0.csv`
- inventario: `metadata/side_communal_creations_inventory_v0.csv`
- qualidade: `reports/side_communal_creations_inspection_quality_v0.json`

## Fontes Inspecionadas

### enterprise

- arquivo: `data/raw/business_demography/side/DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip`
- linhas vistas: `27180400`
- linhas selecionadas comuna-total: `453375`
- pares comuna-ano: `453375`
- anos: `[2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]`

### establishment

- arquivo: `data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip`
- linhas vistas: `27180400`
- linhas selecionadas comuna-total: `453375`
- pares comuna-ano: `453375`
- anos: `[2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]`

## Comparacao Com Target Proxy Atual

- anos sobrepostos: `[2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]`
- linhas sobrepostas: `3640`
- correlacao proxy vs SIDE empresas: `0.9546`
- correlacao proxy vs SIDE estabelecimentos: `0.9559`
- mediana ratio proxy/SIDE empresas: `1.9510`
- mediana ratio proxy/SIDE estabelecimentos: `1.7363`

## Totais Anuais

| Ano | Target proxy | SIDE empresas | SIDE estabelecimentos | Proxy/Empresas | Proxy/Estab. |
|---:|---:|---:|---:|---:|---:|
| 2012 | 938652 | 542967 | 615957 | 1.729 | 1.524 |
| 2013 | 926659 | 543622 | 602496 | 1.705 | 1.538 |
| 2014 | 946383 | 560305 | 621698 | 1.689 | 1.522 |
| 2015 | 925209 | 543084 | 608599 | 1.704 | 1.520 |
| 2016 | 982554 | 581286 | 649871 | 1.690 | 1.512 |
| 2017 | 1044797 | 633888 | 702642 | 1.648 | 1.487 |
| 2018 | 1147713 | 723196 | 795205 | 1.587 | 1.443 |
| 2019 | 1309092 | 836677 | 915980 | 1.565 | 1.429 |
| 2020 | 1328703 | 870951 | 948339 | 1.526 | 1.401 |
| 2021 | 1561417 | 1013787 | 1106794 | 1.540 | 1.411 |
| 2022 | 1571317 | 1021744 | 1119168 | 1.538 | 1.404 |
| 2023 | 1547360 | 1010891 | 1103907 | 1.531 | 1.402 |
| 2024 | 1606905 | 1071065 | 1219089 | 1.500 | 1.318 |

## Leitura

- os arquivos `SIDE` comunais sao utilizaveis para auditoria oficial do target
- eles cobrem `2012-2024` em nivel comunal e agregam para `ZE2020`
- o target proxy atual e sistematicamente maior que os totais oficiais `SIDE`
- a correlacao alta indicara se o proxy preserva ranking/dinamica espacial, mesmo com diferenca de nivel

## Decisao

- usar `SIDE` comunal oficial como auditoria prioritaria do target
- nao usar `SIDE` comunal como feature comum para prever o mesmo target sem controles de vazamento
- promover `SIDE` estabelecimentos oficiais como candidato principal de target formal
- manter `SIDE` empresas como alvo alternativo para sensibilidade
- manter o proxy atual como serie auxiliar/auditoria, pois ele preserva ranking e dinamica mas esta inflado em nivel

Relatorio de decisao:

- `reports/archive/2026_04_22_top_level_cleanup/TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md`
