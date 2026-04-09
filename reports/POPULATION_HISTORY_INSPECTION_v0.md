# Population History Inspection v0

Data: 2026-04-08

Arquivo analisado:

- [base-pop-historiques-1876-2023.xlsx](/home/jpdark/Downloads/project_recomm/dataset/base-pop-historiques-1876-2023.xlsx)

## Resultado principal

Esta base e muito valiosa para o projeto.
Ela traz uma serie historica comunal longa, oficial e harmonizada em geografia estavel.

## Tabela extraida

- [population_history_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/population_history/population_history_communes_v0.csv)
- [population_history_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/population_history_quality_v0.json)

## Caracteristicas

Cobertura:

- `34877` linhas

Escala:

- comunal

Champ:

- `France hors Mayotte`

Geografia:

- `01/01/2025`

Publicacao:

- `décembre 2025`

## Variaveis temporais

Anos recentes anuais:

- `PMUN2023`
- `PMUN2022`
- `PMUN2021`
- `PMUN2020`
- `PMUN2019`
- `PMUN2018`
- `PMUN2017`
- `PMUN2016`
- `PMUN2015`
- `PMUN2014`
- `PMUN2013`
- `PMUN2012`
- `PMUN2011`
- `PMUN2010`
- `PMUN2009`
- `PMUN2008`
- `PMUN2007`
- `PMUN2006`

Anos historicos de recensement:

- `PSDC1999`
- `PSDC1990`
- `PSDC1982`
- `PSDC1975`
- `PSDC1968`
- `PSDC1962`
- `PTOT1954`
- `PTOT1936`
- `PTOT1931`
- `PTOT1926`
- `PTOT1921`
- `PTOT1911`
- `PTOT1906`
- `PTOT1901`
- `PTOT1896`
- `PTOT1891`
- `PTOT1886`
- `PTOT1881`
- `PTOT1876`

## Leitura metodologica

Esta base muda o projeto em tres sentidos:

1. fornece um eixo temporal demografico muito mais longo
2. permite construir sinais de tendencia demografica sem depender apenas de 2022
3. reforca a ideia de ampliar a janela temporal usando apenas dados oficiais confiaveis

## Limitacoes

- `France hors Mayotte`
- a serie nao resolve sozinha as demais familias economicas
- para STGNN final ainda precisamos ampliar o tempo em SIDE, BPE, FLORES e outras fontes

## Uso recomendado

Usar como:

- base estrutural temporal demografica
- suporte a features de tendencia
- apoio a definicao de janelas temporais modelaveis

## Proxima acao recomendada

1. construir uma agregacao inicial desta serie para `ZE2020`
2. depois comparar com o `zones_master_v0`
3. decidir se a populacao historica entra no `panel_zones` ampliado
