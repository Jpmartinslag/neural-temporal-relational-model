# FLORES Download Verification v0

Data: 2026-04-10

Objetivo:

- verificar se os novos downloads locais de `FLORES` fecham lacunas temporais do projeto

## Arquivos validados

### Pacote 2023

- [DS_FLORES_2023_CSV_FR.zip](/home/jpdark/Downloads/project_recomm/dataset/DS_FLORES_2023_CSV_FR.zip)

Conteudo observado:

- `DS_FLORES_A17_2023_CSV_FR.zip`
- `DS_FLORES_A38_2023_CSV_FR.zip`
- `DS_FLORES_A5_2023_CSV_FR.zip`
- `DS_FLORES_A88_2023_CSV_FR.zip`
- `DS_FLORES_ECONOMIC_SPHERE_2023_CSV_FR.zip`
- `DS_FLORES_PE_2023_CSV_FR.zip`

Leitura:

- o pacote `2023` esta correto e e diretamente util ao pipeline
- ele fecha a lacuna `FLORES 2023`
- o subpacote `ECONOMIC_SPHERE_2023` e particularmente valioso porque conversa diretamente com a logica atual do `zones_master`

### Tabelas detalhadas 2021

- [TD_FLORES2021_NA17_TREF_NBETAB_csv.zip](/home/jpdark/Downloads/project_recomm/dataset/TD_FLORES2021_NA17_TREF_NBETAB_csv.zip)
- [TD_FLORES2021_NA17_TREF_NBSAL_csv.zip](/home/jpdark/Downloads/project_recomm/dataset/TD_FLORES2021_NA17_TREF_NBSAL_csv.zip)

Conteudo observado:

- geografia comunal via `CODGEO`
- etablissements por `A17`
- postes salaries por `A17`

Leitura:

- esses downloads fecham uma camada temporal rica de `FLORES 2021`
- eles sao uteis para reforcar profundidade temporal, mesmo que nao sejam exatamente o mesmo recorte de `ECONOMIC_SPHERE`

### Tabelas detalhadas 2020

- [TD_FLORES2020_NA17_TREF_NBSAL_CSV.zip](/home/jpdark/Downloads/project_recomm/dataset/TD_FLORES2020_NA17_TREF_NBSAL_CSV.zip)

Conteudo observado:

- geografia comunal via `CODGEO`
- postes salaries por `A17`

Leitura:

- essa camada fecha parcialmente `FLORES 2020`
- para `2020`, ainda convem verificar se voce tambem tem o par de `NBETAB` correspondente

## Conclusao pratica

Com esses downloads, a situacao de `FLORES` melhora muito:

- `FLORES 2023`: fechado
- `FLORES 2021`: fechado em formato detalhado `A17`
- `FLORES 2020`: parcialmente fechado, ao menos no bloco `NBSAL`

## Lacunas que continuam fora desta verificacao

- `SIDE 2021`
- `BPE 2020`
- `BPE 2023` com ano confiavel
