# New Downloads Gap Review v0

Data: 2026-04-10

Objetivo:

- verificar se os novos datasets baixados fecham as lacunas de profundidade temporal e cobertura funcional do projeto

## Conclusao curta

Os novos downloads ajudam, mas **nao fecham ainda as lacunas principais de profundidade temporal** que bloqueiam um modelo com grafo anual forte.

## O que realmente ajuda agora

### 1. `DS_POPULATIONS_REFERENCE_2023_CSV_FR.zip`

Ajuda porque:

- traz um ponto mais recente de populacao de referencia
- pode reforcar o eixo demografico anual

Limite:

- ainda precisamos verificar alinhamento exato com o pipeline atual e nivel geografico efetivo

### 2. `DS_POPULATIONS_HISTORIQUES_CSV_FR.zip`

Ajuda porque:

- reforca o eixo demografico longo
- provavelmente duplica ou sistematiza parte do que ja haviamos obtido via `base-pop-historiques-1876-2023.xlsx`

Leitura:

- util
- mas nao resolve sozinho a falta de profundidade no bloco economico e de emprego

### 3. `DS_RP_SERIE_HISTORIQUE_2022_CSV_FR.zip`

Ajuda porque:

- traz serie longa em nivel `COM`
- o cabecalho observado mostra medidas como `POP`, `BRTH`, `DEATH` e `DWELLINGS`
- a amostra lida cobre `1968 -> 2022`

Leitura:

- e um reforco real do eixo temporal do `RP`
- pode virar fonte complementar importante para features demograficas e residenciais
- mas nao substitui a necessidade de `RP 2021` para alinhar diretamente o bloco principal do painel anual

## O que enriquece o projeto, mas nao fecha a lacuna central

### BPE tematico 2024

- `DS_BPE_EDUCATION_2024_CSV_FR.zip`
- `DS_BPE_SPORT_CULTURE_2024_CSV_FR.zip`

Leitura:

- enriquecem o retrato tematico de `2024`
- nao ampliam profundidade temporal

### Filosofi tematico 2021

- `DS_FILOSOFI_AGE_TP_NIVVIE_2021_CSV_FR.zip`
- `DS_FILOSOFI_LOG_TP_NIVVIE_2021_CSV_FR.zip`
- `DS_FILOSOFI_MEN_TP_NIVVIE_2021_CSV_FR.zip`

Leitura:

- enriquecem o bloco de renda e nivel de vida em `2021`
- continuam no mesmo ano
- nao fecham a lacuna de profundidade

### RP 2022 adicional

- `DS_RP_ACTIVITE_PRINC_2022_CSV_FR.zip`
- `DS_RP_EDUCATION_2022_CSV_FR.zip`
- `DS_RP_EMPLOI_LR_PRINC_2022_CSV_FR.zip`
- `DS_RP_FAMILLE_COMP_2022_CSV_FR.zip`
- `DS_RP_LOGEMENT_COMPL_2022_CSV_FR.zip`
- `DS_RP_LOGEMENT_PRINC_2022_CSV_FR.zip`
- `DS_RP_MENAGES_COMP_2022_CSV_FR.zip`
- `DS_RP_MENAGES_PRINC_2022_CSV_FR.zip`
- `DS_RP_MIGRES_PRINC_2022_CSV_FR.zip`
- `DS_RP_POPULATION_COMP_2022_CSV_FR.zip`
- `DS_RP_SERIE_HISTORIQUE_2022_CSV_FR.zip`

Leitura:

- ampliam muito a cobertura tematica do `RP 2022`
- isso e excelente para futuras features
- mas continua faltando `RP 2021` para aprofundar a serie anual do bloco principal

### SIDE adicional 2022-2024

- `DS_SIDE_CREA_EI_2024_CSV_FR.zip`
- `DS_SIDE_CREA_ENT_DEP_REG_NAT_CJ_2024_CSV_FR.zip`
- `DS_SIDE_EQDEMO_A10_2022_CSV_FR.zip`
- `DS_SIDE_EQDEMO_A21_2022_CSV_FR.zip`
- `DS_SIDE_STOCKS_A21_2023_CSV_FR.zip`
- `DS_SIDE_STOCKS_EI_2023_CSV_FR.zip`

Leitura:

- ajudam a enriquecer a semantica do bloco economico
- mas nao substituem a necessidade de `SIDE 2021` e possivelmente `SIDE 2020`

Complemento importante:

- `DS_SIDE_EQDEMO_A21_2022_CSV_FR.zip` mostrou serie `2014 -> 2022`, mas na amostra observada apenas para `FRANCE` e `REG`
- `DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip` mostrou serie mensal, mas na amostra observada apenas para `FRANCE`, `REG` e `DEP`

Conclusao:

- esses datasets sao uteis para contexto macro e validacao externa
- eles nao fecham a lacuna comunal que precisamos para agregar coerentemente em `ZE2020`

## O que continua faltando

As lacunas principais continuam sendo:

1. `RP 2021`
2. `SIDE 2021`
3. `BPE 2023`
4. `BPE 2021`
5. `BPE 2020`
6. `Filosofi 2020`
7. `Flores 2023`

## Anomalia encontrada

O arquivo:

- `DS_SIDE_CREA_DEP_REG_NAT_2024_CSV_FR.zip`

apareceu como **corrompido ou nao-zip valido** na inspeção `unzip -l`.

## Decisao pratica

Os novos downloads:

- **melhoram bastante a largura tematica**
- **melhoram parcialmente o eixo demografico e historico do `RP`**
- mas **nao resolvem ainda a profundidade temporal critica** para um Graph WaveNet anual forte
