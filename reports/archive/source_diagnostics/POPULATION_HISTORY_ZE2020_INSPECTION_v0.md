# Population History ZE2020 Inspection v0

Data: 2026-04-09

Arquivo gerado:

- [population_history_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/population_history_ze2020_v0.csv)

Qualidade:

- [population_history_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/population_history_ze2020_quality_v0.json)

## Resultado principal

A serie historica de populacao foi agregada com sucesso para `ZE2020`.

## Cobertura

- `306` zonas
- `37` colunas temporais
- unica zona sem `PMUN2023`: `0601 / Mayotte`

## Leitura metodologica

Esta base e uma das primeiras series temporais fortes ja colocadas no nivel final do projeto.

Ela e util porque:

1. ja esta em `ZE2020`
2. amplia o eixo temporal demografico de forma muito forte
3. ajuda a construir variaveis de tendencia territorial
4. aproxima o projeto de um painel temporal mais robusto

## Observacoes

- a agregacao usa a ponte `commune_to_ze2020_2026`
- a fonte de origem e `France hors Mayotte`
- a anomalia de Mayotte permanece coerente com o resto do projeto

## Proxima acao recomendada

1. decidir como incorporar essa serie ao `panel_zones`
2. construir features derivadas de tendencia demografica
3. manter a regra de nao imputar cobertura ausente de Mayotte
