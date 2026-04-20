# Target Proxy Candidate Core v0

Data: 2026-04-09

Objetivo:

- construir um primeiro target proxy mensal por `zone d'emploi` a partir do `SIRENE StockEtablissement`

## Definicao

- cada linha conta uma criacao de estabelecimento
- a data usada e `dateCreationEtablissement`
- a localizacao usada e `codeCommuneEtablissement` observado no estoque atual
- a agregacao final e `commune -> ZE2020 core_v0`

## Caveat metodologico

- este target e um **proxy**
- a comuna observada e a do estoque atual, nao necessariamente a comuna exata do momento da criacao historica

## Regra de limpeza temporal

- anos mantidos: `2000 -> 2026`
- datas impossiveis ou muito improvaveis foram excluidas do artefato canonico
- isso removeu valores como `0002-02`, `1024-01`, `2054-08` e `5015-04`

## Cobertura final

- linhas escaneadas no `SIRENE`: `43116645`
- linhas com data e comuna validas: `39099279`
- linhas dentro do mapeamento `core_v0`: `33268077`
- comunas core observadas: `34386`
- zonas core observadas apos limpeza: `280`
- meses observados apos limpeza: `324`
- janela observada apos limpeza: `2000-01 -> 2026-12`
- linhas agregadas excluidas por ano fora da janela: `131912`
- contagem excluida por ano fora da janela: `6934525`

## Leitura

- o target proxy ficou denso o suficiente para baseline tecnico
- todas as `280` zonas do `core_v0` aparecem no recorte limpo
- o principal limite continua sendo territorial, nao temporal

## Meses com maior contagem observada

- `2024-01`: `213580` criacoes
- `2025-01`: `210942` criacoes
- `2022-01`: `206917` criacoes
- `2023-01`: `206208` criacoes
- `2021-01`: `196205` criacoes
- `2026-01`: `173112` criacoes
- `2020-01`: `169863` criacoes
- `2019-01`: `164106` criacoes
- `2025-09`: `156715` criacoes
- `2024-09`: `156326` criacoes
