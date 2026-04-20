# Data Collection Guide

Data: 2026-04-08

Objetivo:

- dizer onde procurar os dados oficiais que faltam
- orientar a expansao temporal do acervo sem perder qualidade metodologica

## Regra adotada

A janela temporal alvo do projeto nao sera definida por uma data arbitraria.
Ela sera definida pela maior cobertura confiavel oficialmente publicada pelo governo, ate o ano atual.

Isso significa:

- cada fonte entra apenas ate o ultimo ano oficial disponivel
- nao vamos inventar anos inexistentes
- nao vamos assumir disponibilidade de `2026` se a fonte ainda nao a publicou

## Onde procurar por familia

### 1. Catalogo principal do INSEE

Ponto de entrada principal:

- https://catalogue-donnees.insee.fr/fr/catalogue/recherche

Uso:

- procurar datasets por prefixo `DS_`
- localizar anos disponiveis
- confirmar nome oficial e pagina fonte

Pesquisar por:

- `DS_RP_`
- `DS_FILOSOFI_`
- `DS_BPE_`
- `DS_FLORES_`
- `DS_SIDE_`
- `DS_BTS_`

### 2. API Melodi do INSEE

Ponto de entrada:

- https://api.insee.fr/melodi/data

Uso:

- confirmar existencia oficial de datasets
- recuperar titulo oficial
- localizar identificadores coerentes por familia

### 3. Paginas estatisticas do INSEE

Uso:

- encontrar arquivos vinculados a uma publicacao especifica
- confirmar ultimo ano publicado
- validar notas metodologicas

Buscar nas paginas do INSEE quando o dataset nao estiver claro no catalogo.

### 4. Referencias territoriais oficiais

Para `ZE2020`, `COG` e tabelas de pertencimento:

- https://www.insee.fr/fr/information/2114819
- https://www.insee.fr/fr/information/6800675

Uso:

- mapping comunal
- geometrias
- suporte ao grafo

### 5. Politicas ZRR / FRR

Para contexto institucional e possiveis labels:

- https://www.service-public.fr
- https://www.legifrance.gouv.fr
- https://www.data.gouv.fr

Uso:

- localizar textos oficiais
- localizar zonagens e listas territoriais
- documentar mudancas de regime

## Como continuar a coleta

Para cada familia de dados:

1. identificar o ultimo ano oficial disponivel
2. identificar a serie historica ainda publicada
3. verificar se a granularidade comunal existe
4. baixar apenas os anos que ampliam a janela de forma util
5. registrar no inventario e no journal

## Ordem recomendada de busca adicional

1. `DS_SIDE_*`
2. `DS_RP_*`
3. `DS_BPE_*`
4. `DS_FLORES_*`
5. `DS_FILOSOFI_*`
6. politicas `ZRR/FRR`

## Arquivo de apoio

A matriz de cobertura atual esta em:

- [source_time_coverage_matrix_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/source_time_coverage_matrix_v0.csv)
