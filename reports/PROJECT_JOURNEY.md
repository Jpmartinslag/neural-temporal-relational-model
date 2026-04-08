# Project Journey

Data de inicio do journal: 2026-04-08

Objetivo:

- registrar o que foi feito
- registrar decisoes tecnicas
- registrar anomalias confirmadas
- registrar o que falta fazer
- manter rastreabilidade do caminho ate o primeiro dataset pronto para modelagem

## Estado atual do projeto

Estamos no `Sprint 1`, focado em fundacao de dados:

1. inventario formal dos datasets
2. padronizacao inicial dos arquivos brutos
3. dicionario de variaveis
4. tabela canonica `commune -> zone d'emploi 2020`
5. agregacao inicial para `zone d'emploi`
6. primeiro `zones_master` anual
7. relatorio de qualidade

## Jornada

### 2026-04-08 - Catalogo inicial do acervo

O que foi feito:

- inventario dos arquivos locais do acervo INSEE
- verificacao de integridade dos `.zip`
- identificacao de arquivos corrompidos
- recuperacao de links oficiais INSEE para redownload
- enriquecimento do catalogo com descricoes reais e APIs Melodi quando disponiveis

Artefatos:

- [CATALOGO_INSEE_DATASETS.md](/home/jpdark/Downloads/project_recomm/dataset/CATALOGO_INSEE_DATASETS.md)

Decisoes:

- manter apenas arquivos validos no acervo ativo
- usar documentacao oficial INSEE e endpoints Melodi como fonte semantica principal
- tratar nomes locais e nomes oficiais do INSEE como equivalencias documentadas quando divergirem

### 2026-04-08 - Complemento territorial oficial

O que foi feito:

- montagem de `data/raw/territorial`
- substituicao de URLs antigas que retornavam `HTTP 500`
- download e validacao dos arquivos territoriais atuais

Arquivos principais:

- [fonds_ze2020_2026.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/territorial/fonds_ze2020_2026.zip)
- [ZE2020_au_01-01-2026.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/territorial/ZE2020_au_01-01-2026.zip)
- [table-appartenance-geo-communes-2020.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/territorial/table-appartenance-geo-communes-2020.zip)
- [cog_ensemble_2026_csv.zip](/home/jpdark/Downloads/project_recomm/dataset/data/raw/territorial/cog_ensemble_2026_csv.zip)

Decisoes:

- fixar `ZE2020` como geometria funcional de trabalho
- usar a referencia comunal de `01/01/2026` como base territorial canonica nesta fase

### 2026-04-08 - Fundacao do Sprint 1

O que foi feito:

- criacao das pastas `metadata`, `data/interim`, `data/processed` e `reports`
- criacao do inventario formal dos datasets
- criacao do dicionario seed de variaveis
- extracao da ponte `commune -> ZE2020`
- construcao do primeiro `zones_master_annual_v0`
- geracao do primeiro relatorio de qualidade

Artefatos:

- [dataset_inventory.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/dataset_inventory.csv)
- [variable_dictionary_seed.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/variable_dictionary_seed.csv)
- [commune_to_ze2020_2026.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/mappings/commune_to_ze2020_2026.csv)
- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

Decisoes:

- trabalhar primeiro com dados anuais
- priorizar reproducibilidade e consistencia territorial antes de qualquer modelagem
- aceitar fundacao minima antes de expandir cobertura de features

### 2026-04-08 - Expansao analitica do `zones_master`

O que foi feito:

- geracao de tabelas `interim` por fonte
- incorporacao de emprego no local de trabalho, FLORES e proxies FILOSOFI
- emissao de `zones_master_annual_v1`

Artefatos:

- [rp_population_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_population_commune_2022.csv)
- [side_stocks_et_commune_2023.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/side_stocks_et_commune_2023.csv)
- [side_stocks_ul_commune_2023.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/side_stocks_ul_commune_2023.csv)
- [bpe_commune_2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/bpe_commune_2024.csv)
- [rp_emploi_lr_comp_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_comp_commune_2022.csv)
- [rp_emploi_lt_princ_commune_2022.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lt_princ_commune_2022.csv)
- [filosofi_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/filosofi_commune_2021.csv)
- [flores_sphere_commune_2024.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/flores_sphere_commune_2024.csv)
- [zones_master_annual_v1.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v1.csv)
- [interim_tables_summary_v1.json](/home/jpdark/Downloads/project_recomm/dataset/reports/interim_tables_summary_v1.json)

Decisoes:

- manter `zones_master` versionado
- deixar sinais ainda experimentais explicitamente marcados como `proxy`
- nao avancar para STGNN antes de fechar cobertura, missingness e target

### 2026-04-08 - Revisao do indicador de desemprego

Problema identificado:

- a versao `v1` usava `unemployment_rate_proxy_2022`
- a categoria comunal direta `EMPSTA_ENQ = 2` nao estava disponivel em `2022` no recorte aplicado
- isso fazia o indicador tender a zero artificial

O que foi feito:

- revisao da fonte `DS_RP_EMPLOI_LR_COMP_2022`
- reconstrucao da tabela comunal de emprego com `ativos` e `ocupados`
- substituicao da taxa anterior por uma estimativa defensavel
- emissao de `zones_master_annual_v2`

Nova regra:

- `unemployed_15_64_2022_total = active_15_64_2022_total - employed_15_64_2022_total`
- `unemployment_rate_est_2022 = unemployed / active`

Artefatos:

- [build_zones_master_v2.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_zones_master_v2.py)
- [rp_emploi_lr_comp_commune_2022_v2.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_comp_commune_2022_v2.csv)
- [zones_master_annual_v2.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v2.csv)
- [data_quality_report_v1.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v1.json)

Decisoes:

- descartar `unemployment_rate_proxy_2022`
- manter apenas o indicador estimado documentado
- preferir `missing` a `zero` quando a cobertura estrutural nao existir

### 2026-04-08 - Investigacao Mayotte

Problema identificado:

- `ZE2020 = 0601 / Mayotte` aparecia com lacunas em populacao e emprego

O que foi feito:

- verificacao da ponte territorial
- contagem de cobertura `976xx` nas tabelas `interim`
- confronto com a documentacao oficial do INSEE

Artefato:

- [mayotte_investigation_v1.md](/home/jpdark/Downloads/project_recomm/dataset/reports/mayotte_investigation_v1.md)

Conclusao:

- a anomalia nao e erro de merge
- as fontes RP e Filosofi usadas nesta rodada nao cobrem `976xx`
- `SIDE`, `BPE` e `FLORES` cobrem Mayotte

Decisao:

- Mayotte sera isolada como anomalia
- os campos sem cobertura estrutural ficam vazios, nao zero
- a zona nao deve contaminar o treino enquanto a politica de uso nao for formalizada

## Estado de limpeza para modelagem

Ja resolvido:

- inventario inicial
- integridade local do acervo principal
- geografia canonica `commune -> ZE2020`
- primeira versao anual analitica
- revisao do indicador de desemprego
- isolamento de Mayotte como anomalia

Ainda falta para STGNN:

1. consolidar a versao canonica final do `zones_master`
2. enriquecer o dicionario com semantica analitica e regra de agregacao
3. construir `panel_zones`
4. definir `target`
5. gerar mascaras de missingness
6. normalizar features
7. construir o grafo espacial inicial
8. montar tensores de treino, validacao e teste

## Regra de manutencao deste journal

A partir desta rodada:

- toda decisao tecnica relevante entra aqui
- todo artefato novo entra aqui
- toda anomalia confirmada entra aqui
- todo proximo passo acordado entra aqui

### 2026-04-08 - Governanca de versao e foco da Fase 1

O que foi feito:

- definicao de uma politica local de versionamento
- criacao de um `.gitignore` voltado ao projeto de dados
- formalizacao de um roadmap curto da Fase 1

Artefatos:

- [.gitignore](/home/jpdark/Downloads/project_recomm/dataset/.gitignore)
- [VERSIONING_POLICY.md](/home/jpdark/Downloads/project_recomm/dataset/reports/VERSIONING_POLICY.md)
- [PHASE1_GRAPH_ROADMAP.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PHASE1_GRAPH_ROADMAP.md)

Decisoes:

- o repositorio deve versionar scripts, metadata, reports e artefatos analiticos leves
- arquivos brutos pesados ficam fora do git
- a Fase 1 fica explicitamente orientada a construcao do grafo territorial inicial
- tarefas fora do caminho critico do grafo devem ser adiadas

### 2026-04-08 - Inicializacao do repositorio Git

O que foi feito:

- inicializacao do repositorio local com `git init`
- preparacao do diretorio para conexao com o remoto oficial do projeto

Repositorio remoto:

- https://github.com/Jpmartinslag/territorial-recommender-stgnn-mas.git

Decisoes:

- usar `main` como branch principal
- manter commits pequenos por decisao metodologica
- tratar `PROJECT_JOURNEY.md` como memoria tecnica viva do repositorio
