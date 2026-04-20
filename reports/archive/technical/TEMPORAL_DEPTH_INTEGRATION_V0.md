# Temporal Depth Integration v0

Data: 2026-04-10

Objetivo:

- integrar `RP 2021` e `Filosofi 2020` no pipeline vivo

## Artefatos interim produzidos

- [rp_population_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_population_commune_2021.csv)
- [rp_emploi_lr_commune_2021_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_commune_2021_v0.csv)
- [filosofi_commune_2020.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/filosofi_commune_2020.csv)

## Efeito sobre o dataset principal

- `zones_master_annual_v0.csv` recebeu colunas `2021` para populacao e emprego
- `zones_master_annual_v0.csv` recebeu colunas `2020` para proxies Filosofi

## Cobertura observada

- zonas com populacao 2021: `305`
- zonas com emprego 2021: `305`
- zonas com Filosofi 2020: `297`

## Nota metodologica

- os proxies `Filosofi 2020` foram agregados por media ponderada pelo numero de menages (`NBMEN20`)
- `Mayotte` permanece vazia nessas colunas, coerente com a cobertura oficial
