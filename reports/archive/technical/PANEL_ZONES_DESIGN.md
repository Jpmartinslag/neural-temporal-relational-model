# Panel Zones Design

Data: 2026-04-08

Objetivo:

- definir a primeira estrutura temporal do projeto sem criar series artificiais

## Janela temporal inicial

- `2021`
- `2022`
- `2023`
- `2024`

## Unidade do painel

- uma linha por `zone d'emploi` e por `year`

Chaves:

- `ze2020`
- `year`

## Regra central

Nenhuma feature e projetada artificialmente para anos onde a fonte nao foi observada.

Isto significa:

- FILOSOFI fica em `2021`
- RP populacao e emprego ficam em `2022`
- SIDE fica em `2023`
- BPE e FLORES ficam em `2024`

## Motivacao da escolha

- evita misturar tempo de forma silenciosa
- preserva rastreabilidade metodologica
- permite construir o painel minimo sem inventar valores
- deixa clara a necessidade futura de alinhamento temporal ou imputacao controlada

## Consequencia pratica

O `panel_zones_v0` nao e ainda um painel denso pronto para STGNN final.
Ele e um painel minimo, explicito e auditavel.

Seu papel nesta fase e:

- estabilizar o formato `zone-year`
- explicitar cobertura temporal por feature
- preparar o caminho para o grafo e para o dataset pre-STGNN

## Flags importantes

- `has_any_feature_value`
- `observed_feature_count`
- `is_source_year_row`
- `is_training_eligible_panel_v0`

## Proximo passo depois do painel

1. revisar quais features entram no recorte inicial do grafo
2. extrair geometrias `ZE2020`
3. gerar a adjacencia espacial inicial
