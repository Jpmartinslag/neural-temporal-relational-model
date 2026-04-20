# Sprint 1 Roadmap

Data: 2026-04-08
Escopo do sprint:

1. inventario formal dos datasets
2. padronizacao dos arquivos brutos
3. dicionario de variaveis
4. tabela canonica `commune -> zone d'emploi 2020`
5. agregacao inicial para `zone d'emploi`
6. primeiro `zones_master` anual
7. relatorio de qualidade dos dados

## Ja entregue

### 1. Inventario formal dos datasets

Artefato:

- [dataset_inventory.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/dataset_inventory.csv)

Status:

- concluido

Conteudo atual:

- 30 arquivos registrados
- datasets INSEE principais
- arquivos territoriais de suporte
- URL de API ou fonte oficial quando conhecida
- status local de disponibilidade validada

### 2. Padronizacao inicial dos arquivos brutos

Status:

- concluido em nivel minimo de fundacao
- ampliado com primeira camada tabular `interim`

O que foi feito:

- validacao estrutural dos `.zip`
- separacao entre acervo principal e complemento territorial
- normalizacao da localizacao dos arquivos territoriais em `data/raw/territorial`
- extracao controlada das planilhas territoriais para `data/interim/territorial_xlsx`

Limitacao atual:

- ainda nao cobrimos todas as fontes do acervo
- a camada `interim` atual cobre apenas as fontes usadas no `zones_master_v1`

Artefatos `interim` ja gerados:

- [rp_population_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_population_commune_2022.csv)
- [side_stocks_et_commune_2023.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/side_stocks_et_commune_2023.csv)
- [side_stocks_ul_commune_2023.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/side_stocks_ul_commune_2023.csv)
- [bpe_commune_2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/bpe_commune_2024.csv)
- [rp_emploi_lr_comp_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_comp_commune_2022.csv)
- [rp_emploi_lt_princ_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lt_princ_commune_2022.csv)
- [filosofi_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/filosofi_commune_2021.csv)
- [flores_sphere_commune_2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/flores_sphere_commune_2024.csv)

### 3. Dicionario de variaveis

Artefato:

- [variable_dictionary_seed.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/variable_dictionary_seed.csv)

Status:

- concluido em versao seed

Conteudo atual:

- 35 variaveis identificadas a partir dos `metadata.csv`
- codigo da variavel
- rotulo em frances
- primeiro dataset em que a variavel apareceu

Limitacao atual:

- ainda nao ha semantica harmonizada por uso analitico
- ainda faltam categorias derivadas como `target_candidate`, `structural_feature`, `mobility_feature`, `quality_flag`

### 4. Tabela canonica `commune -> zone d'emploi 2020`

Artefato:

- [commune_to_ze2020_2026.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/mappings/commune_to_ze2020_2026.csv)

Status:

- concluido

Conteudo atual:

- 34.875 linhas
- 306 `zone d'emploi`
- geografia de referencia: 01/01/2026
- colunas:
  - `CODGEO`
  - `LIBGEO`
  - `ZE2020`
  - `LIBZE2020`
  - `ZE_PARTIE_REG`
  - `DEP`
  - `REG`

Observacao:

- esta tabela foi extraida da aba `Composition_communale` do arquivo oficial `ZE2020_au_01-01-2026.xlsx`

### 5. Agregacao inicial para `zone d'emploi`

Status:

- concluido em versao minima

O que foi agregado:

- populacao total 2022
- estoque de estabelecimentos 2023
- estoque de unidades legais 2023
- total de equipamentos BPE 2024

### 6. Primeiro `zones_master` anual

Artefato:

- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)

Status:

- concluido em `v0`

Conteudo atual:

- 306 linhas
- 1 linha por `zone d'emploi`
- colunas atuais:
  - `ze2020`
  - `libze2020`
  - `reg`
  - `population_2022_total`
  - `side_stocks_et_2023_total`
  - `side_stocks_ul_2023_total`
  - `bpe_facilities_2024_total`
  - `side_stocks_et_per_1000_pop_2023`
  - `bpe_facilities_per_1000_pop_2024`

### 7. Relatorio de qualidade dos dados

Artefato:

- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

Status:

- concluido em `v0`

Resumo:

- 30 arquivos inventariados
- 35 variaveis no dicionario seed
- 34.875 linhas na ponte `commune -> ZE2020`
- 306 zonas no `zones_master_annual_v0`
- cobertura:
  - populacao: 305 zonas com valor
  - SIDE ET: 306 zonas com valor
  - SIDE UL: 306 zonas com valor
  - BPE: 306 zonas com valor

## Avanco adicional desta rodada

### `zones_master_annual_v1`

Status atual:

- versao historica removida do estado ativo do repositorio
- substituida operacionalmente pela versao canonica `v0` do repositorio limpo

Status:

- concluido em versao `v1`

Novos sinais incorporados:

- `jobs_lt_2022_total`
- `jobs_lt_per_1000_pop_2022`
- `flores_presential_unit_loc_2024_total`
- `flores_productive_unit_loc_2024_total`
- `filosofi_s_hh_tax_weighted_proxy_2021`
- `filosofi_s_dir_tax_di_weighted_proxy_2021`

Cobertura observada:

- 306 zonas no arquivo
- 305 zonas com `jobs_lt_2022_total`
- 297 zonas com proxy FILOSOFI
- 306 zonas com cobertura FLORES por esfera economica

Observacao:

- o resumo auxiliar `interim_tables_summary_v1.json` tambem foi removido do estado ativo

## Falta fazer neste sprint

### A. Fechar a padronizacao tabular por fonte

Objetivo:

- transformar os principais datasets em tabelas limpas e previsiveis em `data/interim/`

Prioridade:

- alta

Fontes-alvo:

- `DS_RP_POPULATION_PRINC_2022`
- `DS_SIDE_STOCKS_ET_COM_2023`
- `DS_SIDE_STOCKS_UL_COM_2023`
- `DS_BPE_2024`
- `DS_FILOSOFI_CC_2021`
- `DS_FLORES_*`

### B. Evoluir o dicionario de variaveis

Objetivo:

- adicionar classificacao funcional das variaveis

Campos recomendados para a proxima versao:

- `domain`
- `unit`
- `aggregation_rule`
- `temporal_nature`
- `role_in_mvp`

### C. Enriquecer o `zones_master`

Objetivo:

- incorporar sinais estruturais adicionais

Entradas candidatas:

- FILOSOFI
- FLORES
- RP emploi
- RP navettes

### D. Investigar a lacuna de populacao em 1 zona

Objetivo:

- identificar qual `zone d'emploi` ficou sem populacao no `v0`
- verificar se o problema e:
  - cobertura territorial
  - codigo COG
  - especificidade ultramarina
- ausencia real de observacao

Status atual:

- parcialmente investigado

Achado:

- a zona `0601 / Mayotte` existe na tabela `commune -> ZE2020`
- os codigos comunais `976xx` nao aparecem nas bases locais `DS_RP_POPULATION_PRINC_2022`, `DS_RP_EMPLOI_LR_COMP_2022` e `DS_RP_EMPLOI_LT_PRINC_2022`
- isso indica ausencia de cobertura nessas bases locais, e nao erro de merge

### E. Revisar a escolha do indicador de desemprego

Objetivo:

- evitar interpretar como dado economico real um zero que veio de ausencia estrutural de linhas

Achado atual:

- `DS_RP_EMPLOI_LR_COMP_2022` tem linhas `EMPSTA_ENQ = 2` para `2011` e `2016`
- nao tem linhas `EMPSTA_ENQ = 2` para `2022` em `COM` sob a regra de extracao atual
- portanto, `unemployment_rate_proxy_2022` nao deve ser tratado como indicador confiavel nesta versao

### E. Preparar a versao anual canonica do MVP

Objetivo:

- transformar o `zones_master_annual_v0` em um `zones_master_annual_v1`

Requisitos minimos:

- sem duplicatas
- nomes de colunas estabilizados
- regras de agregacao documentadas
- dicionario ligado as colunas finais

## Fora do sprint por enquanto

- painel mensal
- `panel_zones`
- grafo espacial
- forecasting
- decisao multicriterio
- agentes
- orquestracao

## Criterio de encerramento do Sprint 1

O Sprint 1 pode ser considerado fechado quando existirem:

1. inventario formal estavel
2. dicionario de variaveis minimamente enriquecido
3. tabela canonica `commune -> ZE2020`
4. `zones_master_annual_v1`
5. relatorio de qualidade com anomalias explicitas

## Revisao desta rodada

### Indicador de desemprego revisado

Artefatos canonicos:

- [rp_emploi_lr_comp_commune_2022_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_comp_commune_2022_v0.csv)
- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

Decisao:

- o indicador antigo `unemployment_rate_proxy_2022` foi descartado
- a versao `v0` passa a usar:
  - `active_15_64_2022_total`
  - `employed_15_64_2022_total`
  - `unemployed_15_64_2022_total = active - employed`
  - `unemployment_rate_est_2022 = unemployed / active`

Justificativa:

- em `DS_RP_EMPLOI_LR_COMP_2022`, a categoria `EMPSTA_ENQ = 2` nao esta disponivel como linha comunal direta em `2022`
- porem, `EMPSTA_ENQ = 1T2` e `EMPSTA_ENQ = 1` existem para 34.747 comunas no recorte aplicado
- por isso, a estimativa por diferenca e mais defensavel do que gravar zero

Cobertura:

- 34.774 comunas com cobertura parcial ou total no recorte LR
- 34.747 comunas com `ativos` e `ocupados` simultaneamente
- 305 zonas com cobertura agregada

### Investigacao Mayotte

Artefato:

- [mayotte_investigation_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/archive/source_diagnostics/mayotte_investigation_v0.md)

Conclusao operacional:

- a anomalia de `0601 / Mayotte` nao e erro de merge
- ela decorre da ausencia de cobertura nas fontes RP e Filosofi usadas nesta versao
- no `zones_master_annual_v0`, os campos RP derivados de Mayotte passaram a ficar vazios, nao zero

### Flags de cobertura e anomalia

Artefatos:

- [add_coverage_flags_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/add_coverage_flags_v0.py)
- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

O que entrou no schema:

- flags de cobertura por fonte
- `source_coverage_count`
- `source_coverage_ratio`
- `is_structural_anomaly`
- `anomaly_reason`
- `is_training_eligible_v0`

Resultado:

- 305 zonas elegiveis no recorte inicial de treino
- 1 zona anomala estrutural
- Mayotte explicitamente fora do treino inicial
