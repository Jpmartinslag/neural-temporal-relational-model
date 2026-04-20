# Scan Review v0

Data: 2026-04-09

Objetivo:

- consolidar os achados principais do scan completo do repositorio

## Resultado geral

O scan foi concluido com sucesso e confirmou que o acervo principal esta estruturalmente saudavel.

## O que ficou confirmado

- os arquivos `.zip` inspecionados passaram no teste de integridade
- o acervo principal `DS_*`, `SIRENE`, `policy` e `territorial` foi percorrido
- o bundle final do scan foi gerado

## Principais achados

### 1. Integridade dos zips

Nao apareceu corrupcao em:

- datasets principais do INSEE
- `SIRENE`
- `QPV`
- `ZAN`
- arquivos territoriais

### 2. Tamanho e peso do acervo

Os maiores arquivos do projeto hoje sao:

- `SIRENE StockEtablissement`
- `SIRENE Geolocalisation`
- `SIRENE StockEtablissementHistorique`
- `SIRENE StockUniteLegale`
- `PNB Action7`

Leitura:

- o caminho mais promissor para um target proxy continua vindo de `SIRENE`

### 3. Parquet

O suporte a `parquet` foi concluido com `pyarrow`, e o schema leve por metadados confirmou:

- `GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet`
  - `37256819` linhas
  - `19` colunas
- `StockEtablissement_utf8.parquet`
  - `43116645` linhas
  - `54` colunas
- `StockUniteLegale_utf8.parquet`
  - `29453574` linhas
  - `35` colunas

Leitura:

- os `parquet` de `SIRENE` estao validos
- o formato `parquet` passa a ser uma rota forte para exploracao futura com melhor desempenho que os `zip` CSV

### 4. Excel

O scan de `xlsx` funcionou para:

- [base-pop-historiques-1876-2023.xlsx](/home/jpdark/Downloads/project_recomm/dataset/base-pop-historiques-1876-2023.xlsx)
- [liste-1514qp2015.xlsx](/home/jpdark/Downloads/project_recomm/dataset/data/raw/policy/qpv/liste-1514qp2015.xlsx)

Mas falhou para:

- [ZE2020_au_01-01-2026.xlsx](/home/jpdark/Downloads/project_recomm/dataset/data/interim/territorial_xlsx/ZE2020_au_01-01-2026.xlsx)
- [table-appartenance-geo-communes-2020.xlsx](/home/jpdark/Downloads/project_recomm/dataset/data/interim/territorial_xlsx/table-appartenance-geo-communes-2020.xlsx)

Leitura:

- esses dois arquivos parecem ter XML interno nao totalmente compativel com `openpyxl`
- isso nao invalida o projeto, porque o pipeline atual nao depende deles como fonte tabular ativa

## Conclusao pratica

O scan reforca tres pontos:

1. o acervo esta bem organizado e sem nova corrupcao zip
2. `SIRENE` continua sendo o bloco mais importante para o proximo target proxy
3. o scan agora ja descreve tambem os `parquet` centrais do projeto
