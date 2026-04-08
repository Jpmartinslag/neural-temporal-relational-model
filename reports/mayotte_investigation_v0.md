# Investigacao Mayotte v0

Data: 2026-04-08

## Conclusao

A anomalia de `0601 / Mayotte` no `zones_master` nao vem de erro de merge da tabela `commune -> ZE2020`.
Ela vem de cobertura ausente ou diferente nas fontes locais usadas para os sinais derivados do RP e do Filosofi.

## Evidencia local

Tabela canonica:

- `ZE2020 = 0601`
- 17 comunas mapeadas
- codigos `97601` a `97617`

Cobertura observada nas tabelas interim:

- `rp_population_commune_2022.csv`: 0 comunas `976xx`
- `rp_emploi_lr_comp_commune_2022_v0.csv`: 0 comunas `976xx`
- `rp_emploi_lt_princ_commune_2022.csv`: 0 comunas `976xx`
- `filosofi_commune_2021.csv`: 0 comunas `976xx`
- `bpe_commune_2024.csv`: 17 comunas `976xx`
- `side_stocks_et_commune_2023.csv`: 17 comunas `976xx`
- `side_stocks_ul_commune_2023.csv`: 17 comunas `976xx`
- `flores_sphere_commune_2024.csv`: 17 comunas `976xx`

Leitura tecnica:

- o merge territorial esta correto
- a ausencia esta concentrada nas fontes RP e Filosofi usadas nesta versao
- para Mayotte, zeros seriam semanticamente falsos
- no `zones_master_annual_v0`, esses campos passaram a ficar vazios

## Fontes oficiais consultadas

1. Populations de reference 2022

URL:
https://www.insee.fr/fr/statistiques/8288323

Leitura:

- a pagina oficial informa que as populacoes 2022 estao disponiveis para todas as comunas da Franca, exceto Mayotte

Impacto:

- explica a ausencia de `population_2022_total` para `ZE2020 = 0601` nesta rodada

2. Dossier complet - Departement de Mayotte (976)

URL:
https://www.insee.fr/fr/statistiques/2011101?geo=DEP-976

Leitura:

- o dossier local de Mayotte mostra receitas/pobreza em 2017
- a secao de metodo informa que, para Filosofi, a difusao cobre Franca metropolitana, Martinica e Reuniao

Impacto:

- explica por que o `DS_FILOSOFI_CC_2021` local nao traz comunas `976xx`
- tambem sugere que Mayotte exigira tratamento dedicado se Filosofi for importante para o MVP

## Decisao aplicada no pipeline

No `zones_master_annual_v0`:

- `population_2022_total` para Mayotte ficou vazio
- `jobs_lt_2022_total` para Mayotte ficou vazio
- `active_15_64_2022_total` para Mayotte ficou vazio
- `employed_15_64_2022_total` para Mayotte ficou vazio
- `unemployed_15_64_2022_total` para Mayotte ficou vazio
- `unemployment_rate_est_2022` para Mayotte ficou vazio

## Proximo passo recomendado

Escolher explicitamente uma destas politicas para o MVP:

1. excluir Mayotte da versao anual canonica enquanto as fontes RP/Filosofi do recorte atual nao cobrirem o territorio
2. manter Mayotte no dataset, mas com `missingness` explicita e flags de cobertura por fonte
3. buscar uma fonte complementar dedicada para populacao, emprego e rendimento em Mayotte
