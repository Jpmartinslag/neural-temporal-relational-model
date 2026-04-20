# Download Inbox Review v0

Data: 2026-04-08

Objetivo:

- revisar os arquivos baixados fora do fluxo principal
- decidir o que entra no pipeline
- decidir o que fica como fonte de contexto ou apoio

## Arquivos revisados

### 1. [base-flux-mobilite-domicile-lieu-travail-2022_xlsx.zip](/home/jpdark/Downloads/project_recomm/dataset/base-flux-mobilite-domicile-lieu-travail-2022_xlsx.zip)

Conteudo:

- `base-excel-flux-mobilite-domicile-lieu-travail-2022.xlsx`

Leitura:

- potencialmente util para mobilidade e navettes
- pode complementar ou validar o `DS_RP_NAVETTES_PRINC_2022`

Decisao atual:

- manter para revisao
- prioridade media

### 2. [base-pop-historiques-1876-2023.xlsx](/home/jpdark/Downloads/project_recomm/dataset/base-pop-historiques-1876-2023.xlsx)

Leitura:

- serie historica longa de populacao
- forte candidata para ampliar o eixo temporal demografico

Decisao atual:

- manter para integracao futura
- prioridade alta

### 3. [BPE24.zip](/home/jpdark/Downloads/project_recomm/dataset/BPE24.zip)

Conteudo:

- `BPE24.csv`

Leitura:

- parece duplicata funcional da base BPE 2024 ja presente no acervo principal

Decisao atual:

- manter fora do pipeline principal por enquanto
- usar apenas se precisarmos comparar cobertura ou formato com `DS_BPE_2024`

### 4. [dataset-1775678390572.zip](/home/jpdark/Downloads/project_recomm/dataset/dataset-1775678390572.zip)

Conteudo:

- shapefile `N_FRR_026.*`
- XML de metadados

Leitura:

- este e o achado mais importante desta rodada
- parece ser um dataset geografico da `FRR`
- forte candidato para contexto institucional e possivel label territorial

Decisao atual:

- manter
- prioridade alta
- revisar com detalhe na proxima rodada

### 5. [diffusion-zonages-historique-zrr-2019.xls](/home/jpdark/Downloads/project_recomm/dataset/diffusion-zonages-historique-zrr-2019.xls)

Leitura:

- historico de ZRR
- relevante para contexto de politica territorial

Decisao atual:

- manter
- prioridade alta

### 6. [diffusion-zonages-zrr-cog2021.xls](/home/jpdark/Downloads/project_recomm/dataset/diffusion-zonages-zrr-cog2021.xls)

Leitura:

- zonage ZRR alinhado ao COG 2021
- relevante para vinculo entre politica e geografia

Decisao atual:

- manter
- prioridade alta

### 7. [indic-struct-distrib-revenu-2021-COMMUNES_XLSX.zip](/home/jpdark/Downloads/project_recomm/dataset/indic-struct-distrib-revenu-2021-COMMUNES_XLSX.zip)

Leitura:

- conjunto detalhado FILOSOFI 2021 em nivel comunal
- pode enriquecer muito o bloco de renda

Decisao atual:

- manter
- prioridade alta

### 8. [indic-struct-distrib-revenu-2021-ETUDES_XLSX.zip](/home/jpdark/Downloads/project_recomm/dataset/indic-struct-distrib-revenu-2021-ETUDES_XLSX.zip)

Leitura:

- inclui tabelas prontas em `ZE2020`
- util para validacao da agregacao comunal e possivel atalho analitico

Decisao atual:

- manter
- prioridade alta

### 9. [indic-struct-distrib-revenu-2021-SUPRA_XLSX.zip](/home/jpdark/Downloads/project_recomm/dataset/indic-struct-distrib-revenu-2021-SUPRA_XLSX.zip)

Leitura:

- agregados supra-comunais
- util mais para validacao e comparacao do que para pipeline central

Decisao atual:

- manter
- prioridade media

### 10. [joe_20240620_0144_0051.pdf](/home/jpdark/Downloads/project_recomm/dataset/joe_20240620_0144_0051.pdf)

Leitura:

- documento juridico ou normativo
- provavelmente ligado a publicacao da `FRR`

Decisao atual:

- manter como documento de contexto institucional
- nao entra no pipeline de dados

## Classificacao geral

Entram no radar direto do pipeline:

- `base-pop-historiques-1876-2023.xlsx`
- `dataset-1775678390572.zip`
- `diffusion-zonages-historique-zrr-2019.xls`
- `diffusion-zonages-zrr-cog2021.xls`
- `indic-struct-distrib-revenu-2021-COMMUNES_XLSX.zip`
- `indic-struct-distrib-revenu-2021-ETUDES_XLSX.zip`

Ficam como apoio ou validacao:

- `base-flux-mobilite-domicile-lieu-travail-2022_xlsx.zip`
- `indic-struct-distrib-revenu-2021-SUPRA_XLSX.zip`
- `BPE24.zip`

Ficam como contexto institucional:

- `joe_20240620_0144_0051.pdf`

## Proxima acao recomendada

1. abrir e interpretar o shapefile `FRR`
2. extrair e entender as tabelas `ZRR`
3. revisar a serie historica de populacao
4. decidir o que vira fonte ativa do painel e do grafo
