# Temporal Depth Enrichment Core v0

Data: 2026-04-13

## Objetivo

- Adicionar profundidade temporal ao zones_master
- Melhorar a cobertura observada das features nos anos ja alinhados do tensor
- Nao aumenta, por si so, o numero de anos supervisionados de treino

## Fontes

- **SIDE stocks ET/UL**: `DS_SIDE_STOCKS_ET/UL_COM_2023_CSV_FR.zip`
  - nivel ZE2020 direto, TIME_PERIOD 2019-2020
  - medida: UNIT_LOC (ET) e LEGAL_UNIT (UL), atividade total (_T)

- **FLORES historico**: `TD_FLORES{ano}_NA17_TREF_NBETAB_CSV.zip`
  - nivel comunal, campo ET_TOT = total de estabelecimentos ativos
  - agregado para ZE2020 via mapeamento commune_to_ze2020_2026
  - anos: 2019, 2020, 2021

## Colunas Adicionadas

| coluna | cobertura (de 306) |
|---|---|
| `side_stocks_et_2019_total` | `306` |
| `side_stocks_ul_2019_total` | `306` |
| `side_stocks_et_2020_total` | `306` |
| `side_stocks_ul_2020_total` | `306` |
| `flores_et_total_2019` | `305` |
| `flores_et_total_2020` | `305` |
| `flores_et_total_2021` | `305` |

## Decisao

- `flores_et_total` e uma feature nova (distinta de `flores_presential_unit_loc_total`)
  e captura o estoque total de estabelecimentos FLORES por ano
- `side_stocks_et_total` e `side_stocks_ul_total` ganham cobertura observada em 2019 e 2020
  dentro da janela anual ja usada pelo tensor
- o proximo passo e atualizar build_panel_zones_v0.py e reconstruir o tensor STGNN
