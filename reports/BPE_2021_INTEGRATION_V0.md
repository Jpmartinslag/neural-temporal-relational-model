# BPE 2021 Integration v0

Data: 2026-04-10

Objetivo:

- verificar se o novo download de `BPE 2021` fecha uma lacuna real do painel anual
- integrar a camada ao pipeline apenas se o conteudo confirmar `2021`

## Arquivo validado

- [bpe21-ensemble-csv.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/temporal_depth/bpe/bpe21-ensemble-csv.zip)

Resultado da validacao:

- zip integro
- arquivo principal: `bpe21_ensemble.csv`
- coluna temporal confirmada no conteudo: `AN = 2021`
- coluna comunal confirmada: `DEPCOM`
- medida confirmada: `NB_EQUIP`

## Integracao realizada

Script:

- [integrate_bpe_2021_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_bpe_2021_v0.py)

Interim:

- [bpe_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/bpe_commune_2021.csv)

Campos adicionados ao `zones_master`:

- `bpe_facilities_2021_total`
- `bpe_facilities_per_1000_pop_2021`

## Cobertura

No universo completo:

- `1,002,987` linhas selecionadas da base
- `34,859` comunas com cobertura `BPE 2021`
- `306` zonas com cobertura `BPE 2021`

No `core_v0`:

- `280` zonas com `bpe_facilities_2021_total`
- `280` zonas com `bpe_facilities_per_1000_pop_2021`

## Efeito no painel

O painel `2021` ficou mais forte:

- `280` linhas do `core_v0` em `2021` passaram a ter `BPE`
- a media de `observed_feature_count` em `2021` no `core_v0` subiu para `11.0`

## Leitura metodologica

- este download fecha de fato a lacuna `BPE 2021`
- ele e muito mais confiavel para integracao do que o recurso baixado como `BPE 2023`, que apresentou mismatch temporal
- `BPE 2020` continua aberto

## Conclusao pratica

Com este download, o projeto ganhou profundidade real no eixo de servicos/acessibilidade:

- `2021`: `BPE` presente
- `2024`: `BPE` presente

Assim, a lacuna dessa familia fica reduzida para:

- `BPE 2020`
- `BPE 2023`, ainda em observacao por problema temporal do recurso encontrado
