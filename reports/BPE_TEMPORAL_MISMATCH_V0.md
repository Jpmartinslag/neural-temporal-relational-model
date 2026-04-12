# BPE Temporal Mismatch v0

Data: 2026-04-10

Objetivo:

- verificar se o recurso fechado como `BPE 2023` em `data.gouv` poderia entrar no pipeline temporal

## O que foi baixado

Arquivo:

- [DS_BPE_2023_CSV_FR.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/temporal_depth/bpe/DS_BPE_2023_CSV_FR.zip)

Origem:

- pagina: https://www.data.gouv.fr/datasets/base-permanente-des-equipements-2
- recurso zip: https://www.data.gouv.fr/api/1/datasets/r/abfc35ff-8305-43f0-a553-3b549673c002
- recurso csv: https://www.data.gouv.fr/api/1/datasets/r/dcdcf8fb-acaf-4260-b455-b25e0c7ee003

## Resultado da inspecao

- o zip e valido
- o recurso contem um shapefile `bpe23-nettoye.*`
- a amostra do conteudo do csv e do shapefile mostra `Millésime = 2024`
- a amostra lida no shapefile tambem apresenta `an = 2024`

## Leitura metodologica

- o portal e o nome do recurso sugerem `BPE 2023`
- o conteudo observado sugere fortemente `BPE 2024`
- portanto, integrar esse recurso como `2023` neste momento seria arriscado

## Decisao

- nao integrar o recurso ao pipeline temporal como `BPE 2023`
- manter a lacuna `BPE 2023` em observacao ate encontrar um recurso cujo conteudo confirme o ano correto

## Pistas oficiais adicionais

Na pagina oficial do Insee para `BPE 2021` e `BPE 2020`, o HTML confirma a existencia de documentacao especifica desses anos:

- `BPE21_ensemble_dessin_fichier.pdf`
- `BPE21_ensemble_dictionnaire_variables.pdf`
- `BPE21_table_passage.csv`
- `contenu_bpe20_ensemble.pdf`
- `BPE20_table_passage.csv`

Isso confirma que a familia oficial desses anos existe, mesmo que o link bruto de dados ainda nao tenha sido isolado nesta rodada.
