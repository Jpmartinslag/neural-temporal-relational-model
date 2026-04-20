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
- emissao de um `zones_master` revisado que passa a ser o `v0` canonico do repositorio limpo

Nova regra:

- `unemployed_15_64_2022_total = active_15_64_2022_total - employed_15_64_2022_total`
- `unemployment_rate_est_2022 = unemployed / active`

Artefatos:

- [build_zones_master_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_zones_master_v0.py)
- [rp_emploi_lr_comp_commune_2022_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rp_emploi_lr_comp_commune_2022_v0.csv)
- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

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

- [mayotte_investigation_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/mayotte_investigation_v0.md)

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
- [PROJECT_EXPLANATIONS.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_EXPLANATIONS.md)

Decisoes:

- o repositorio deve versionar scripts, metadata, reports e artefatos analiticos leves
- arquivos brutos pesados ficam fora do git
- a Fase 1 fica explicitamente orientada a construcao do grafo territorial inicial
- tarefas fora do caminho critico do grafo devem ser adiadas
- o projeto passa a manter tres trilhas permanentes de memoria: `git`, `PROJECT_JOURNEY.md` e `PROJECT_EXPLANATIONS.md`

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

### 2026-04-08 - Limpeza do repositorio para estado canonico

O que foi feito:

- remocao de artefatos intermediarios que ja nao fazem parte do pipeline ativo
- consolidacao do repositorio em torno da versao canonica atual

Artefatos removidos do estado ativo:

- `data/interim/tables/rp_emploi_lr_comp_commune_2022.csv`
- `data/processed/zones_master_annual_v0.csv`
- `data/processed/zones_master_annual_v1.csv`
- `reports/data_quality_report_v0.json`
- `reports/interim_tables_summary_v1.json`

Artefatos canonicos mantidos:

- `data/interim/tables/rp_emploi_lr_comp_commune_2022_v0.csv`
- `data/processed/zones_master_annual_v0.csv`
- `reports/data_quality_report_v0.json`

Decisoes:

- o repositorio deve refletir apenas o pipeline vivo
- versoes antigas ficam preservadas no historico do `git`, nao como arquivos ativos
- o conjunto atual de referencia para a Fase 1 passa a ser o `v0`

### 2026-04-08 - Flags de cobertura e anomalia no `zones_master_v0`

O que foi feito:

- adicao de flags de cobertura por fonte no `zones_master`
- adicao de contagem e razao de cobertura por zona
- adicao de flag de anomalia estrutural
- adicao de flag de elegibilidade inicial para treino

Artefatos:

- [add_coverage_flags_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/add_coverage_flags_v0.py)
- [zones_master_annual_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_v0.csv)
- [data_quality_report_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/data_quality_report_v0.json)

Novas colunas principais:

- `has_population_2022`
- `has_active_lr_2022`
- `has_jobs_lt_2022`
- `has_side_stocks_et_2023`
- `has_side_stocks_ul_2023`
- `has_bpe_2024`
- `has_flores_2024`
- `has_filosofi_2021`
- `source_coverage_count`
- `source_coverage_ratio`
- `is_structural_anomaly`
- `anomaly_reason`
- `is_training_eligible_v0`

Resultado:

- 305 zonas elegiveis para o recorte inicial de treino
- 1 anomalia estrutural confirmada
- Mayotte marcada com `is_structural_anomaly = 1`

Decisoes:

- FILOSOFI nao entra como criterio obrigatorio de elegibilidade inicial
- a elegibilidade inicial de treino usa o nucleo: populacao, ativos, empregos LT, SIDE, BPE e FLORES
- Mayotte permanece no dataset, mas fora do treino inicial

### 2026-04-08 - Construcao do `panel_zones_v0`

O que foi feito:

- definicao da janela temporal inicial `2021-2024`
- criacao do painel minimo em formato `zone-year`
- registro explicito da regra temporal de cada feature
- geracao do relatorio de qualidade do painel

Artefatos:

- [build_panel_zones_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_panel_zones_v0.py)
- [panel_zones_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/panel_zones_v0.csv)
- [panel_feature_registry_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/panel_feature_registry_v0.csv)
- [panel_zones_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/panel_zones_quality_v0.json)
- [PANEL_ZONES_DESIGN.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PANEL_ZONES_DESIGN.md)

Resultado:

- 1.224 linhas no painel
- 306 zonas
- 4 anos
- 305 zonas com cobertura observada em `2022`
- 306 zonas com cobertura observada em `2023` e `2024`
- 297 zonas com observacao em `2021` por conta do FILOSOFI

Decisoes:

- nenhuma feature foi projetada para anos em que nao foi observada
- o painel `v0` e explicito, auditavel e ainda nao e um painel denso final para STGNN
- Mayotte permanece no painel, mas segue fora do recorte inicial de treino

### 2026-04-08 - Matriz inicial de cobertura temporal e guia de coleta

O que foi feito:

- consolidacao da visao por familia de fonte
- registro dos anos ja presentes localmente
- formalizacao de onde procurar a expansao temporal oficial

Artefatos:

- [source_time_coverage_matrix_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/source_time_coverage_matrix_v0.csv)
- [DATA_COLLECTION_GUIDE.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DATA_COLLECTION_GUIDE.md)

Decisoes:

- a janela temporal alvo passa a ser a maior janela confiavel oficialmente publicada ate o ano atual
- cada familia sera expandida apenas ate o ultimo ano oficial disponivel
- a coleta adicional passa a seguir a ordem de prioridade por familia e por utilidade no projeto

### 2026-04-08 - Triagem de downloads externos ao fluxo principal

O que foi feito:

- revisao dos arquivos baixados manualmente fora do acervo principal
- classificacao entre pipeline, apoio e contexto institucional

Artefato:

- [DOWNLOAD_INBOX_REVIEW_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DOWNLOAD_INBOX_REVIEW_v0.md)

Achados principais:

- apareceu um shapefile potencialmente relevante da `FRR`
- apareceram planilhas `ZRR` relevantes para contexto de politica territorial
- apareceu uma serie historica longa de populacao
- apareceram tabelas FILOSOFI detalhadas que podem enriquecer muito o bloco de renda

Decisao:

- esses downloads entram agora no radar de integracao controlada
- a entrada no pipeline sera feita por prioridade e por utilidade metodologica

### 2026-04-08 - Inspecao da camada FRR baixada

O que foi feito:

- inspecao estrutural do arquivo `dataset-1775678390572.zip`
- verificacao de geometria, projecao, campos e cobertura territorial

Artefato:

- [FRR_LAYER_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FRR_LAYER_INSPECTION_v0.md)

Achado principal:

- a camada `N_FRR_026` e comunal, mas cobre apenas o departamento `26`
- portanto, nao e uma camada nacional pronta para integrar ao pipeline

Decisao:

- manter como referencia de schema e prova de fonte
- nao integrar ao pipeline ativo enquanto nao localizarmos a cobertura nacional

### 2026-04-08 - Extracao e inspecao das tabelas ZRR

O que foi feito:

- conversao dos `.xls` de `ZRR`
- extracao para CSV canonico do projeto
- verificacao de cobertura historica e de cobertura comunal `COG 2021`

Artefatos:

- [extract_zrr_tables_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_zrr_tables_v0.py)
- [zrr_historique_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zrr_historique_communes_v0.csv)
- [zrr_cog2021_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zrr_cog2021_communes_v0.csv)
- [zrr_tables_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zrr_tables_quality_v0.json)
- [ZRR_TABLES_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ZRR_TABLES_INSPECTION_v0.md)

Achado principal:

- `ZRR` entra como camada comunal muito forte de politica territorial
- ha historico institucional utilisavel e uma tabela alinhada ao `COG 2021`

Decisao:

- manter `ZRR` no pipeline ampliado de politica territorial
- usaremos `ZRR` como referencia enquanto buscamos a cobertura nacional de `FRR`

### 2026-04-08 - Verificacao de alinhamento com o projeto original

O que foi feito:

- releitura dos documentos de projeto para verificar o papel de `ZRR` e das outras restricoes territoriais

Achado principal:

- o projeto original ja previa um bloco de politica territorial com `QPV/ZRR`
- em versoes posteriores, o desenho tambem incorpora `FRR/FRR+` e `ZAN`
- isso confirma que a coleta atual de `ZRR/FRR` esta no caminho metodologico correto

Decisao:

- consolidar um bloco futuro de `policy layers`
- tratar `ZRR`, `FRR/FRR+`, `QPV` e `ZAN` como familia propria no acervo e na documentacao

### 2026-04-08 - Extracao da serie historica de populacao

O que foi feito:

- inspecao da base historica de populacao
- extracao para CSV comunal canônico
- validacao de cobertura temporal e geografica

Artefatos:

- [extract_population_history_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_population_history_v0.py)
- [population_history_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/population_history/population_history_communes_v0.csv)
- [population_history_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/population_history_quality_v0.json)
- [POPULATION_HISTORY_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/POPULATION_HISTORY_INSPECTION_v0.md)

Achado principal:

- a base traz uma serie comunal longa e harmonizada em geografia `01/01/2025`
- ela amplia fortemente o eixo temporal demografico do projeto

Decisao:

- manter a base como fonte estrutural temporal de alta prioridade
- usar esta serie para preparar a futura expansao temporal do painel

### 2026-04-09 - Agregacao da serie historica de populacao para ZE2020

O que foi feito:

- agregacao da base comunal de populacao historica para `zone d'emploi`
- geracao de uma serie temporal demografica diretamente no nivel final do projeto

Artefatos:

- [build_population_history_ze2020_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_population_history_ze2020_v0.py)
- [population_history_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/population_history_ze2020_v0.csv)
- [population_history_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/population_history_ze2020_quality_v0.json)
- [POPULATION_HISTORY_ZE2020_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/POPULATION_HISTORY_ZE2020_INSPECTION_v0.md)

Resultado:

- `306` zonas
- `37` colunas temporais
- apenas `0601 / Mayotte` sem cobertura recente

Decisao:

- esta serie entra como eixo temporal demografico estruturante
- o proximo debate passa a ser como incorpora-la ao `panel_zones` sem perder clareza metodologica

### 2026-04-09 - Formalizacao da familia `policy_layers`

O que foi feito:

- criacao do desenho formal da familia `policy_layers`
- definicao do schema comunal canonico
- normalizacao inicial da camada `ZRR`

Artefatos:

- [build_policy_commune_status_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_policy_commune_status_v0.py)
- [policy_commune_status_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/policy_commune_status_v0.csv)
- [policy_layers_registry_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/policy_layers_registry_v0.csv)
- [policy_commune_status_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/policy_commune_status_quality_v0.json)
- [POLICY_LAYERS_DESIGN.md](/home/jpdark/Downloads/project_recomm/dataset/reports/POLICY_LAYERS_DESIGN.md)

Decisao:

- `policy_layers` passa a ser familia explicita do projeto
- `ZRR` entra como primeiro membro normalizado
- `FRR/FRR+`, `QPV` e `ZAN` permanecem como alvos seguintes da mesma familia

### 2026-04-09 - Organizacao dos downloads brutos de politica

O que foi feito:

- reorganizacao dos downloads de politica em subpastas dedicadas
- retirada desses arquivos do topo do repositorio
- preparacao da atualizacao do inventario

Artefatos:

- [POLICY_DOWNLOAD_ORGANIZATION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/POLICY_DOWNLOAD_ORGANIZATION_v0.md)
- [update_policy_inventory_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/update_policy_inventory_v0.py)

Decisao:

- `data/raw/policy` passa a ser a raiz unica dos brutos institucionais
- a organizacao por `zrr`, `frr`, `qpv`, `zan` e `legal` fica oficial no projeto

### 2026-04-09 - Organizacao dos brutos de registro empresarial

O que foi feito:

- criacao de uma area dedicada para arquivos `SIRENE`
- remocao desses brutos do topo do repositorio

Artefatos:

- [RAW_DOWNLOAD_ORGANIZATION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RAW_DOWNLOAD_ORGANIZATION_v0.md)
- [update_business_registry_inventory_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/update_business_registry_inventory_v0.py)

Decisao:

- `data/raw/business_registry/sirene` passa a ser a raiz desses brutos
- o topo do repositorio continua reservado ao pipeline vivo e ao acervo principal

### 2026-04-09 - Posicionamento do OCS GE Artificialisation

O que foi decidido:

- `OCS GE Artificialisation` foi reconhecido como fonte importante para o projeto
- ele tem forte alinhamento com `ZAN` e com a camada de politica/conformidade

Decisao metodologica:

- a fonte fica registrada como importante
- mas nao entra no caminho critico imediato desta rodada
- primeiro vamos estruturar `QPV` e `ZAN` com os arquivos ja baixados
- `OCS GE Artificialisation` entra como expansao posterior qualificada da familia `policy_layers`

### 2026-04-09 - Convencao de nomes do repositorio

O que foi feito:

- formalizacao de uma convencao de nomes para scripts, datasets, relatorios e documentos vivos
- alinhamento do script de integracao do `QPV` ao padrao definido

Artefatos:

- [NAMING_CONVENTIONS_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/NAMING_CONVENTIONS_v0.md)
- [integrate_qpv_policy_commune_status_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_qpv_policy_commune_status_v0.py)

Decisao:

- arquivos tecnicos novos passam a seguir padrao explicito de nomenclatura
- scripts Python devem combinar verbo, objeto, escopo e versao

### 2026-04-09 - Integracao do `QPV` na familia `policy_layers`

O que foi feito:

- extracao das tabelas `QPV`
- integracao de `QPV 2024` no schema canônico `policy_commune_status_v0`
- ativacao formal de `QPV` no registro da familia

Artefatos:

- [extract_qpv_tables_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_qpv_tables_v0.py)
- [integrate_qpv_policy_commune_status_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_qpv_policy_commune_status_v0.py)
- [qpv_2024_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/qpv_2024_communes_v0.csv)
- [qpv_correspondance_2024_2015_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/qpv_correspondance_2024_2015_v0.csv)
- [policy_commune_status_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/policy_commune_status_v0.csv)
- [policy_layers_registry_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/policy_layers_registry_v0.csv)
- [policy_commune_status_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/policy_commune_status_quality_v0.json)
- [QPV_TABLES_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/QPV_TABLES_INSPECTION_v0.md)

Resultado:

- `1584` linhas `QPV` adicionadas
- `823` comunas distintas cobertas
- `policy_layers` agora tem `ZRR` e `QPV` ativos

Decisao:

- `QPV` passa a integrar o bloco institucional ativo do projeto
- o proximo membro a estruturar continua sendo `ZAN`

### 2026-04-09 - Abertura da camada quantitativa `ZAN`

O que foi feito:

- extracao canônica da tabela comunal `conso2009-2024-resultats-com.csv`
- criacao de uma camada interim quantitativa para `ZAN`
- atualizacao do registro da familia para indicar carga quantitativa parcial

Artefatos:

- [extract_zan_consumption_communes_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_zan_consumption_communes_v0.py)
- [zan_consumption_communes_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/policy/zan_consumption_communes_v0.csv)
- [zan_consumption_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zan_consumption_quality_v0.json)
- [ZAN_CONSUMPTION_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ZAN_CONSUMPTION_INSPECTION_v0.md)
- [policy_layers_registry_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/policy_layers_registry_v0.csv)

Resultado:

- `34905` linhas comunais
- `138` colunas
- `ZAN` passa a ter camada interim ativa

Decisao:

- `ZAN` entra primeiro como tabela quantitativa
- a traducao para status, regras de conformidade e agregacao `ZE2020` fica para a proxima rodada

### 2026-04-09 - Agregacao da camada quantitativa `ZAN` para `ZE2020`

O que foi feito:

- agregacao de metricas aditivas de `ZAN` para `zone d'emploi`
- criacao de derivados simples por populacao e por superficie

Artefatos:

- [build_zan_consumption_ze2020_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_zan_consumption_ze2020_v0.py)
- [zan_consumption_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zan_consumption_ze2020_v0.csv)
- [zan_consumption_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/zan_consumption_ze2020_quality_v0.json)
- [ZAN_CONSUMPTION_ZE2020_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ZAN_CONSUMPTION_ZE2020_INSPECTION_v0.md)

Resultado:

- `305` zonas cobertas
- `34837` comunas mapeadas
- `68` comunas fora do mapeamento atual desta camada

Decisao:

- `ZAN` ja pode entrar no raciocinio territorial em nivel `ZE2020`
- as `68` comunas nao mapeadas parecem refletir diferencas de `COG` ou alteracoes comunais difusas
- a proxima etapa sera definir sinais de conformidade para agentes e depois tratar esse ajuste residual de correspondencia

### 2026-04-09 - Revisao de consistencia do pipeline atual

O que foi feito:

- auditoria cruzada entre `zones_master`, `panel_zones`, `population_history_ze2020`, `zan_consumption_ze2020` e `policy_layers`
- correcao da leitura `QPV`
- saneamento do historico `ZRR`
- reconstrucao sequencial de `policy_commune_status_v0`

Artefatos:

- [CONSISTENCY_REVIEW_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/CONSISTENCY_REVIEW_v0.md)
- [consistency_review_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/consistency_review_v0.json)
- [extract_qpv_tables_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/extract_qpv_tables_v0.py)
- [sanitize_zrr_historical_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/sanitize_zrr_historical_v0.py)

Resultado:

- datasets canônicos principais estao coerentes
- `policy_commune_status_v0.csv` voltou a `433235` linhas validas
- `QPV` ficou com `1373` linhas comunais limpas
- a unica ausencia territorial recorrente segue sendo `0601 / Mayotte`

Decisao:

- podemos seguir para visualizacao diagnostica sem carregar incoerencia estrutural grave
- antes do grafo, ainda permanecem como passivos conhecidos:
  - `QPV` multi-comuna
  - reproducao bruta `ZRR`
  - traducao de `ZAN` para sinais de agente

### 2026-04-09 - Visualizacao diagnostica inicial

O que foi feito:

- geracao de um primeiro pacote de visualizacao diagnostica
- inspecao da cobertura do `zones_master`
- inspecao da densidade anual do `panel_zones`
- inspecao inicial dos extremos da camada `ZAN`

Artefatos:

- [DIAGNOSTICS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DIAGNOSTICS_V0.md)
- [diagnostics_summary_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_summary_v0.json)
- [coverage_count_hist_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/coverage_count_hist_v0.png)
- [zones_master_distributions_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/zones_master_distributions_v0.png)
- [panel_observed_feature_count_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/panel_observed_feature_count_v0.png)
- [zan_top_intensity_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/diagnostics_v0/zan_top_intensity_v0.png)

Decisao:

- o dataset ja esta suficientemente visivel para passarmos ao primeiro grafo espacial

### 2026-04-09 - Revisao de prontidao antes do grafo

O que foi feito:

- revisao metodologica do passo seguinte
- explicitação do problema de ausencia de `ground truth`
- definicao do papel real do primeiro grafo no projeto

Artefatos:

- [PRE_GRAPH_READINESS_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PRE_GRAPH_READINESS_v0.md)
- [EVALUATION_WITHOUT_GROUND_TRUTH_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/EVALUATION_WITHOUT_GROUND_TRUTH_v0.md)

Decisao:

- o primeiro grafo sera tratado como infraestrutura metodologica
- nao como validacao do sistema final
- o projeto pode avancar para o grafo desde que essa limitacao continue explicita

### 2026-04-09 - Formalizacao da base de dependencias do ambiente

O que foi feito:

- criacao de um arquivo inicial de dependencias Python
- registro da stack geoespacial como parte oficial do projeto

Artefatos:

- [requirements.txt](/home/jpdark/Downloads/project_recomm/dataset/requirements.txt)
- [ENVIRONMENT_SETUP_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ENVIRONMENT_SETUP_v0.md)

Decisao:

- a etapa do grafo depende formalmente de uma stack geoespacial
- essa dependencia deixa de ser implicita e passa a ser registrada no projeto

### 2026-04-09 - Construcao do primeiro grafo `ZE2020`

O que foi feito:

- instalacao da stack geoespacial em `.venv`
- leitura da geometria oficial `ZE2020`
- construcao do primeiro grafo por adjacencia geografica
- validacao de nos, arestas, componentes e isolados

Artefatos:

- [build_ze2020_graph_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_ze2020_graph_v0.py)
- [graph_nodes_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_v0.csv)
- [graph_edges_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_v0.csv)
- [graph_ze2020_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_ze2020_quality_v0.json)
- [GRAPH_ZE2020_INSPECTION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_ZE2020_INSPECTION_v0.md)

Resultado:

- `306` nos
- `1552` arestas direcionadas
- `776` arestas nao direcionadas
- `8` componentes conectados
- `2` nos isolados: `Marie-Galante` e `Mayotte`

Decisao:

- o primeiro grafo estrutural do projeto esta pronto
- desconexoes ultramarinas passam a ser tratadas como propriedade territorial do grafo, nao como erro

### 2026-04-09 - Visualizacao inicial do grafo

O que foi feito:

- geracao de mapas do fundo `ZE2020`
- geracao de mapa por componentes conectados
- destaque visual dos nos isolados

Artefatos:

- [GRAPH_VISUALS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_VISUALS_V0.md)
- [ze2020_boundaries_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_visuals_v0/ze2020_boundaries_v0.png)
- [ze2020_graph_components_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_visuals_v0/ze2020_graph_components_v0.png)
- [ze2020_isolated_nodes_v0.png](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_visuals_v0/ze2020_isolated_nodes_v0.png)

Decisao:

- o grafo agora tambem esta visivel, nao apenas tabulado

### 2026-04-09 - Visualizacao interativa do grafo

O que foi feito:

- geracao de um HTML interativo para o grafo `ZE2020`

Artefatos:

- [ze2020_graph_interactive_v0.html](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_visuals_v0/ze2020_graph_interactive_v0.html)
- [build_graph_visuals_html_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_graph_visuals_html_v0.py)

Decisao:

- a visualizacao principal do grafo passa a ser o HTML interativo

### 2026-04-09 - Recorte `core_v0` do grafo

O que foi feito:

- filtragem do grafo completo para manter apenas a maior componente conectada
- exclusao formal de Corse e territorios ultramarinos do MVP

Artefatos:

- [GRAPH_SCOPE_DECISION_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_SCOPE_DECISION_v0.md)
- [GRAPH_CORE_V0_INSPECTION.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_CORE_V0_INSPECTION.md)
- [graph_nodes_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_core_v0.csv)
- [graph_edges_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_core_v0.csv)
- [graph_excluded_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_excluded_ze2020_core_v0.csv)

Decisao:

- o MVP passa a trabalhar com o `graph_core_v0`
- Corse e ultramarinos ficam documentados como excluidos temporarios

### 2026-04-09 - Alinhamento dos datasets ao `core_v0`

O que foi feito:

- filtragem dos datasets processados para o mesmo universo territorial do `graph_core_v0`
- geracao de uma visualizacao HTML exclusiva da Francia continental

Artefatos:

- [CORE_DATASETS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/CORE_DATASETS_V0.md)
- [zones_master_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_core_v0.csv)
- [panel_zones_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/panel_zones_core_v0.csv)
- [population_history_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/population_history_ze2020_core_v0.csv)
- [zan_consumption_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zan_consumption_ze2020_core_v0.csv)
- [GRAPH_CORE_VISUALS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_CORE_VISUALS_V0.md)
- [ze2020_graph_core_interactive_v0.html](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_visuals_v0/ze2020_graph_core_interactive_v0.html)

Decisao:

- o universo territorial ativo do MVP passa a ser o `core_v0`
- os proximos blocos devem usar esse recorte de forma consistente

### 2026-04-09 - Pacote pre-STGNN do `core_v0`

O que foi feito:

- criacao do pacote estrutural pre-STGNN
- geracao do indice de nos
- geracao do `edge_index`
- consolidacao do painel com features dinamicas, contexto estatico e masks

Artefatos:

- [PRE_STGNN_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PRE_STGNN_CORE_V0.md)
- [graph_node_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_node_index_core_v0.csv)
- [graph_edge_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edge_index_core_v0.csv)
- [pre_stgnn_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/pre_stgnn_dataset_core_v0.csv)
- [pre_stgnn_feature_masks_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/pre_stgnn_feature_masks_core_v0.csv)
- [pre_stgnn_feature_registry_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/pre_stgnn_feature_registry_core_v0.csv)
- [pre_stgnn_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/pre_stgnn_core_quality_v0.json)

Resultado:

- `280` nos
- `1486` arestas direcionadas
- `1120` linhas no dataset temporal
- `16` features dinamicas
- `6` features estaticas de contexto

Decisao:

- o pacote estrutural do pre-STGNN esta pronto
- o proximo congelamento necessario e o target inicial do forecasting

### 2026-04-09 - Formalizacao da logica de auditabilidade

O que foi feito:

- registro formal da justificativa metodologica para separar `STGNN`, decisao, agentes e orquestrador

Artefato:

- [AUDITABILITY_RATIONALE_v0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/AUDITABILITY_RATIONALE_v0.md)

Decisao:

- a arquitetura modular fica explicitamente reconhecida como estrategia de auditoria e validacao, nao apenas de implementacao

### 2026-04-09 - Revisao de prontidao do target inicial

O que foi feito:

- verificacao das bases locais de criacao de empresas
- comparacao entre o target previsto no plano e a oferta real do acervo atual

Artefato:

- [TARGET_READINESS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_READINESS_V0.md)

Decisao:

- o target do projeto permanece conceitualmente definido
- mas sua implementacao ainda nao deve ser forçada com o acervo atual

### 2026-04-09 - Abertura das opcoes de derivacao do target

O que foi feito:

- inspecao dos brutos `SIRENE` para avaliar se o target pode ser derivado localmente
- comparacao entre o estoque atual de estabelecimentos e o historico de periodos

Artefato:

- [TARGET_DERIVATION_OPTIONS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_DERIVATION_OPTIONS_V0.md)

Decisao:

- `SIRENE StockEtablissement` abre um caminho viavel para um target proxy mensal por `commune`
- esse caminho tem caveat territorial porque a comuna observada e a do estoque atual
- o projeto passa a distinguir explicitamente `target oficial alvo` de `target proxy candidato`

### 2026-04-09 - Construcao do primeiro target proxy canonico

O que foi feito:

- derivacao do primeiro target proxy mensal por `ZE2020 core_v0` a partir de `SIRENE StockEtablissement`
- limpeza temporal para manter apenas a janela plausivel `2000 -> 2026`

Artefatos:

- [build_target_proxy_candidate_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_target_proxy_candidate_core_v0.py)
- [target_proxy_candidate_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_candidate_core_v0.csv)
- [target_proxy_candidate_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/target_proxy_candidate_core_quality_v0.json)
- [TARGET_PROXY_CANDIDATE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_PROXY_CANDIDATE_CORE_V0.md)

Decisao:

- o projeto passa a ter um target proxy canônico utilizável para baseline tecnico
- o caveat territorial continua explicito
- o target oficial da pesquisa continua conceitualmente superior ao proxy

### 2026-04-09 - Alinhamento anual do target para baseline

O que foi feito:

- agregacao do target proxy mensal para frequencia anual
- construcao de um dataset de baseline com `features_t -> target_t+1`

Artefatos:

- [build_baseline_annual_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_baseline_annual_target_core_v0.py)
- [target_proxy_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_annual_core_v0.csv)
- [baseline_annual_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/baseline_annual_dataset_core_v0.csv)
- [baseline_annual_target_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/baseline_annual_target_core_quality_v0.json)
- [BASELINE_ANNUAL_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BASELINE_ANNUAL_TARGET_CORE_V0.md)

Decisao:

- o primeiro treino coerente do projeto deve nascer como baseline anual
- o STGNN mensal fica para uma etapa posterior, quando as features temporais tambem estiverem densas nessa frequencia

### 2026-04-09 - Primeira avaliacao baseline anual sem grafo

O que foi feito:

- avaliacao de dois baselines anuais no `core_v0`
- `persistence`
- `ridge_linear`

Artefatos:

- [evaluate_baseline_annual_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_baseline_annual_core_v0.py)
- [baseline_annual_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/baseline_annual_predictions_core_v0.csv)
- [baseline_annual_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/baseline_annual_metrics_core_v0.json)
- [BASELINE_ANNUAL_EVALUATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BASELINE_ANNUAL_EVALUATION_V0.md)

Decisao:

- `persistence` passa a ser o benchmark minimo oficial do projeto
- a regressao linear simples nao superou esse benchmark
- o proximo salto de valor esperado fica corretamente deslocado para o modelo com grafo

### 2026-04-09 - Prontidao para o commit da base concreta

O que foi feito:

- consolidacao do escopo da fundacao que deve ser congelada antes da modelagem com grafo

Artefato:

- [FOUNDATION_COMMIT_READINESS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FOUNDATION_COMMIT_READINESS_V0.md)
- [FOUNDATION_COMMIT_SCOPE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FOUNDATION_COMMIT_SCOPE_V0.md)

Decisao:

- o proximo commit importante do projeto deve congelar grafo, datasets core, target proxy e baseline anual
- a etapa seguinte passa a ser explicitamente a modelagem com grafo
- `data/raw/` fica fora desse commit

### 2026-04-09 - Preparacao do pacote anual para modelo com grafo

O que foi feito:

- construcao do pacote anual de modelagem com grafo no `core_v0`
- organizacao de features, targets e adjacencia em artefatos dedicados

Artefatos:

- [build_graph_model_annual_package_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_graph_model_annual_package_core_v0.py)
- [graph_model_feature_panel_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_model_feature_panel_core_v0.csv)
- [graph_model_target_panel_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_model_target_panel_core_v0.csv)
- [graph_adjacency_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_adjacency_core_v0.csv)
- [graph_model_annual_package_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/graph_model_annual_package_core_quality_v0.json)
- [GRAPH_MODEL_ANNUAL_PACKAGE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_MODEL_ANNUAL_PACKAGE_CORE_V0.md)

Decisao:

- o pacote anual com grafo esta estruturalmente pronto
- mas a profundidade temporal observada ainda e curta para um Graph WaveNet anual forte
- a decisao de treinar o modelo com grafo precisa reconhecer esse limite explicitamente

### 2026-04-09 - Plano de aprofundamento temporal das features

O que foi feito:

- traducao do problema de profundidade temporal em uma ordem concreta de coleta

Artefatos:

- [TEMPORAL_DEPTH_EXPANSION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_DEPTH_EXPANSION_V0.md)
- [temporal_depth_priorities_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/temporal_depth_priorities_v0.csv)
- [DOWNLOAD_PRIORITY_AND_API_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DOWNLOAD_PRIORITY_AND_API_V0.md)

Decisao:

- antes do Graph WaveNet principal, a prioridade de coleta passa a ser `RP 2021`, `SIDE 2020-2021`, `BPE 2023/2021/2020`, `Filosofi 2020` e `Flores 2023`
- a verificacao de API passa a ser feita junto com a lista de coleta

### 2026-04-10 - Revisao dos novos downloads para lacunas temporais

O que foi feito:

- verificacao dos novos datasets baixados
- comparacao deles com as lacunas de profundidade temporal ja identificadas

Artefato:

- [NEW_DOWNLOADS_GAP_REVIEW_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/NEW_DOWNLOADS_GAP_REVIEW_V0.md)

Decisao:

- os novos downloads ampliam largura tematica e reforcam o eixo demografico
- mas as lacunas principais continuam sendo `RP 2021`, `SIDE 2021`, `BPE 2023/2021/2020`, `Filosofi 2020` e `Flores 2023`
- `DS_SIDE_CREA_DEP_REG_NAT_2024_CSV_FR.zip` foi identificado como arquivo invalido

Complemento da verificacao:

- `DS_RP_SERIE_HISTORIQUE_2022_CSV_FR.zip` foi confirmado como serie longa comunal e passa a ser considerado reforco real do eixo temporal do `RP`
- `DS_SIDE_EQDEMO_A21_2022_CSV_FR.zip` e `DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip` foram verificados como series agregadas acima de comuna, entao nao fecham a lacuna do painel anual em `ZE2020`

### 2026-04-10 - Download oficial de RP 2021 e Filosofi 2020

O que foi feito:

- download dos arquivos oficiais confirmados para `RP 2021`
- download dos arquivos oficiais confirmados para `Filosofi 2020`
- validacao de integridade por `unzip -t`

Artefato:

- [TEMPORAL_DEPTH_DOWNLOADS_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_DEPTH_DOWNLOADS_V0.md)

Decisao:

- `RP 2021` e `Filosofi 2020` deixam de ser lacunas abertas
- as principais lacunas restantes passam a ser `SIDE 2021`, `BPE 2023/2021/2020` e `Flores 2023`

### 2026-04-10 - Integracao de RP 2021 e Filosofi 2020 no pipeline

O que foi feito:

- extracao comunal de `RP 2021`
- extracao comunal de `Filosofi 2020`
- integracao dessas camadas no `zones_master_annual_v0`
- reconstrucao de `panel_zones`, `core views`, `pre_stgnn`, `baseline annual` e `graph annual package`

Artefatos:

- [integrate_temporal_depth_rp_filosofi_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_temporal_depth_rp_filosofi_v0.py)
- [TEMPORAL_DEPTH_INTEGRATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_DEPTH_INTEGRATION_V0.md)
- [temporal_depth_integration_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/temporal_depth_integration_quality_v0.json)

Decisao:

- o painel anual passa a cobrir `2020-2024`
- `pre_stgnn_core_v0` passa de `1120` para `1400` linhas
- o baseline anual passa a usar treino `2020-2022`, validacao `2023` e teste `2024`
- as lacunas centrais restantes ficam concentradas em `SIDE 2021`, `BPE 2023/2021/2020` e `Flores 2023`

### 2026-04-10 - Busca de links exatos em data.gouv

O que foi feito:

- busca orientada em `data.gouv.fr` para fechar links baixaveis diretos
- cruzamento com o que ainda faltava em `SIDE`, `BPE` e `FLORES`

Artefato:

- [DATAGOUV_LINK_SEARCH_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DATAGOUV_LINK_SEARCH_V0.md)

Decisao:

- `data.gouv` passa a ser rota valida para baixar `SIDE 2021` por meio dos datasets multi-anuais `A10`
- `data.gouv` fecha tambem um caminho direto para `FLORES 2023` em `A17`
- `data.gouv` fecha um caminho direto para `BPE 2023`
- `BPE 2021` e `BPE 2020` continuam abertos

### 2026-04-10 - Correcao da leitura dos links do data.gouv

O que foi feito:

- validacao pela API oficial do `data.gouv` dos recursos publicados para `SIDE`, `FLORES` e `BPE`
- revisao da interpretacao inicial dos anos cobertos pelos links brutos
- correcao do relatorio de busca para evitar fechar lacunas com falsa precisao

Artefato:

- [DATAGOUV_LINK_SEARCH_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/DATAGOUV_LINK_SEARCH_V0.md)

Decisao:

- `BPE 2023` permanece como lacuna efetivamente fechada por `data.gouv`
- `SIDE 2021` continua aberto, porque o recurso bruto hoje exposto aponta para `2022`
- `FLORES 2023` continua aberto, porque o recurso bruto hoje exposto aponta para `2024`
- `BPE 2021` e `BPE 2020` continuam abertos

### 2026-04-10 - Inspecao do recurso baixado como BPE 2023

O que foi feito:

- download do recurso zip oficial a partir do `data.gouv`
- validacao tecnica do arquivo comprimido
- leitura amostral do shapefile e do csv associados ao mesmo recurso

Artefato:

- [BPE_TEMPORAL_MISMATCH_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BPE_TEMPORAL_MISMATCH_V0.md)

Decisao:

- o download do recurso foi bem-sucedido
- a integracao ao pipeline foi suspensa
- o motivo e que o conteudo observado traz `Millésime = 2024` / `an = 2024`, apesar de a rota ter sido tratada inicialmente como `BPE 2023`
- `BPE 2023` volta a ficar em observacao metodologica

### 2026-04-10 - Busca ampliada em fontes oficiais alem do data.gouv

O que foi feito:

- ampliacao da busca para paginas oficiais do `Insee` e para o `catalogue-donnees.insee.fr`
- verificacao do que as paginas publicas realmente prometem em `BPE 2021` e `BPE 2020`
- consolidacao da diferenca entre existencia oficial da base e fechamento do link bruto utilizavel

Artefato:

- [OFFICIAL_SOURCE_SEARCH_V1.md](/home/jpdark/Downloads/project_recomm/dataset/reports/OFFICIAL_SOURCE_SEARCH_V1.md)

Decisao:

- `BPE 2021` e `BPE 2020` passam a ter status de existencia oficial confirmada
- `SIDE 2021` e `FLORES 2023` passam a ter status de familia oficial confirmada, mas recurso anual alvo ainda nao fechado
- a estrategia de busca fica mais precisa: nao basta achar um portal oficial, e preciso fechar o ano certo e o formato certo

Complemento:

- a propria pagina oficial do `Insee` para `BPE 2021` afirma que os arquivos do telechargement da base estao disponiveis em `csv`
- isso reforca que o problema restante em `BPE 2021` nao e ausencia de diffusion, mas isolamento do endpoint bruto correto

### 2026-04-10 - Integracao de BPE 2021 ao pipeline

O que foi feito:

- validacao do arquivo `bpe21-ensemble-csv.zip`
- confirmacao de que o conteudo traz `AN = 2021`, `DEPCOM` e `NB_EQUIP`
- agregacao comunal e por `ZE2020`
- injecao de `BPE 2021` no `zones_master`
- rebuild sequencial do painel, visoes core, pre-STGNN, baseline anual e pacote do modelo com grafo

Artefatos:

- [integrate_bpe_2021_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_bpe_2021_v0.py)
- [bpe_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/bpe_commune_2021.csv)
- [BPE_2021_INTEGRATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BPE_2021_INTEGRATION_V0.md)

Decisao:

- `BPE 2021` deixa de ser lacuna aberta
- `BPE 2023` continua suspenso por mismatch temporal
- `BPE 2020` continua aberto

### 2026-04-10 - Verificacao dos novos downloads de FLORES

O que foi feito:

- inspecao dos novos arquivos `FLORES` baixados localmente
- verificacao do pacote nacional `DS_FLORES_2023_CSV_FR.zip`
- verificacao dos arquivos detalhados `A17` para `2021` e `2020`

Artefato:

- [FLORES_DOWNLOAD_VERIFICATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FLORES_DOWNLOAD_VERIFICATION_V0.md)

Decisao:

- `FLORES 2023` deixa de ser lacuna aberta
- `FLORES 2021` tambem passa a estar fechado em formato detalhado `A17`
- `FLORES 2020` fica parcialmente fechado

### 2026-04-09 - Criacao do workflow de scan completo do repositorio

O que foi feito:

- criacao de um script unificado para varrer o repositorio inteiro
- definicao do bundle padrao de saida para analise posterior

Artefatos:

- [scan_full_repository_v0.sh](/home/jpdark/Downloads/project_recomm/dataset/src/data/scan_full_repository_v0.sh)
- [SCAN_WORKFLOW_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SCAN_WORKFLOW_V0.md)

Decisao:

- o scan completo passa a ser uma ferramenta oficial de inspeção do projeto
- o resultado esperado do scan sera interpretado depois como insumo de governanca e auditoria

### 2026-04-09 - Revisao do scan completo do repositorio

O que foi feito:

- leitura dos artefatos centrais produzidos pelo scan
- consolidacao dos achados tecnicos de integridade e ambiente

Artefato:

- [SCAN_REVIEW_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SCAN_REVIEW_V0.md)

Decisao:

- o acervo foi confirmado como estruturalmente saudavel
- `SIRENE` permanece como principal candidato para derivacao do target proxy
- o suporte a `parquet` foi fechado com `pyarrow` e o schema leve dos arquivos `SIRENE` foi confirmado

### 2026-04-11 - Integracao de SIDE 2021 e BPE 2023

O que foi feito:

- validacao dos arquivos `SIDE` multi-ano `2014-2023`
- extracao de `TIME_PERIOD = 2021` em nivel comunal
- validacao do arquivo `BPE23.zip` com `AN = 2023`
- agregacao de `SIDE 2021` e `BPE 2023` para `ZE2020`
- reconstrução dos datasets `core_v0`, `pre_stgnn`, pacote anual com grafo e baseline anual

Artefatos:

- [integrate_side_2021_bpe_2023_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/integrate_side_2021_bpe_2023_v0.py)
- [side_stocks_commune_2021.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/side_stocks_commune_2021.csv)
- [bpe_commune_2023.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/bpe_commune_2023.csv)
- [SIDE_2021_BPE_2023_INTEGRATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_2021_BPE_2023_INTEGRATION_V0.md)

Decisao:

- `SIDE 2021` passa a estar fechado via arquivos multi-ano `SIDE 2023`
- `BPE 2023` passa a estar fechado via `BPE23.zip`
- `BPE 2020` permanece como unica lacuna principal de profundidade temporal

### 2026-04-11 - Busca dura por BPE 2020 Ensemble

O que foi feito:

- busca paralela com agentes por fontes oficiais e institucionais fora da pagina dinamica do Insee
- consulta ao historico do catalogo `DoReMIFaSol`
- teste do link historico oficial
- consulta ao `Internet Archive`
- download e validacao do candidato `data.gouv.fr`

Artefato:

- [BPE_2020_HARD_SEARCH_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BPE_2020_HARD_SEARCH_V0.md)

Decisao:

- o identificador historico correto foi confirmado: `bpe20_ensemble_csv.zip`
- a URL historica atual retorna `404`
- o candidato `data.gouv.fr` foi rejeitado porque contem apenas anos `2011` e `2012`
- `BPE 2020` segue como lacuna aberta, nao por falta de nome correto, mas por ausencia de arquivo vivo validado

### 2026-04-12 - Camada tensorial antes da arquitetura STGNN

O que foi feito:

- revisao da prontidao real antes da escolha de arquitetura `STGNN`
- criacao do pacote tensorial auditavel `stgnn_tensor_package_core_v0`
- preservacao de valores brutos, mascaras, adjacencia e normalizacao sem vazamento temporal

Artefatos:

- [build_stgnn_tensor_package_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_stgnn_tensor_package_core_v0.py)
- [stgnn_tensor_package_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/stgnn_tensor_package_core_v0.npz)
- [stgnn_tensor_sample_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_sample_index_core_v0.csv)
- [stgnn_tensor_feature_registry_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_feature_registry_core_v0.csv)
- [STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md)
- [STGNN_TENSOR_PACKAGE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_TENSOR_PACKAGE_CORE_V0.md)

Decisao:

- a arquitetura `STGNN` ainda nao foi escolhida
- o projeto passa primeiro por baselines fortes usando o pacote tensorial
- `FLORES` foi identificado como sem observacao no treino nesta versao, entao nao deve ser interpretado como sinal causal nos primeiros experimentos
- `0` no tensor padronizado passa a ser definido como media do treino, com `x_mask` obrigatoria para separar imputacao de observacao real
- o primeiro baseline espacial sera a media dos vizinhos via adjacencia normalizada, antes de qualquer modelo neural com grafo

### 2026-04-12 - Baseline espacial antes do STGNN

O que foi feito:

- implementacao do baseline espacial minimo sobre o pacote tensorial
- comparacao entre persistencia local, media espacial dos vizinhos e mistura validada por `alpha`

Artefatos:

- [evaluate_spatial_baseline_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_spatial_baseline_core_v0.py)
- [spatial_baseline_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/spatial_baseline_predictions_core_v0.csv)
- [spatial_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/spatial_baseline_metrics_core_v0.json)
- [SPATIAL_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SPATIAL_BASELINE_CORE_V0.md)

Decisao:

- a media espacial dos vizinhos nao superou a persistencia local
- a validacao escolheu `alpha = 1.0`, equivalente a peso zero para o componente espacial simples
- o grafo espacial estatico ainda nao deve ser tratado como sinal preditivo confirmado
- qualquer `STGNN` futuro precisa superar esse piso antes de ser interpretado

### 2026-04-13 - Baseline autoregressivo intra-zona

O que foi feito:

- implementacao de um baseline autoregressivo usando apenas historico anual da propria zona
- comparacao entre persistencia, extrapolacao por delta, media movel de 3 anos e regressao ridge autoregressiva
- atualizacao do indice do projeto para explicitar que o alvo atual e um grafo territorial dinamico anual, nao uma arquitetura nomeada

Artefatos:

- [evaluate_autoregressive_baseline_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_autoregressive_baseline_core_v0.py)
- [autoregressive_baseline_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/autoregressive_baseline_predictions_core_v0.csv)
- [autoregressive_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/autoregressive_baseline_metrics_core_v0.json)
- [AUTOREGRESSIVE_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/AUTOREGRESSIVE_BASELINE_CORE_V0.md)
- [PROJECT_STATE_INDEX_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_STATE_INDEX_V0.md)

Decisao:

- a persistencia local continua sendo o baseline mais forte na validacao
- a media movel de 3 anos melhora levemente no teste, mas nao na validacao
- a regressao autoregressiva nao superou a persistencia
- o proximo teste deve verificar se features externas adicionam sinal sobre a persistencia local

### 2026-04-13 - Baseline com features externas

O que foi feito:

- teste de regressao ridge com features externas do painel e mascaras de observacao
- exclusao das features sem observacao no treino
- comparacao contra persistencia local

Artefatos:

- [evaluate_feature_augmented_baseline_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_feature_augmented_baseline_core_v0.py)
- [feature_augmented_baseline_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/feature_augmented_baseline_predictions_core_v0.csv)
- [feature_augmented_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/feature_augmented_baseline_metrics_core_v0.json)
- [FEATURE_AUGMENTED_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_AUGMENTED_BASELINE_CORE_V0.md)

Decisao:

- as features externas atuais nao superaram a persistencia
- o modelo com `y(t)` mais features melhorou treino, mas piorou validacao e teste
- isso indica sobreajuste e pouca profundidade/sinal das features atuais
- antes de arquitetura, o proximo passo deve auditar melhor o target e inspecionar `SIDE` comunal de criacoes

### 2026-04-13 - Auditoria do target com SIDE comunal oficial

O que foi feito:

- inspecao dos arquivos oficiais `SIDE` comunais de criacoes de empresas e estabelecimentos
- selecao das linhas comunais totais anuais
- agregacao de `COM` para `ZE2020`
- comparacao com o target proxy anual atual

Artefatos:

- [inspect_side_communal_creations_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/inspect_side_communal_creations_v0.py)
- [side_communal_creations_ze2020_official_2012_2024_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/side_communal_creations_ze2020_official_2012_2024_v0.csv)
- [target_proxy_vs_side_official_ze2020_2012_2024_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_vs_side_official_ze2020_2012_2024_v0.csv)
- [SIDE_COMMUNAL_CREATIONS_INSPECTION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_COMMUNAL_CREATIONS_INSPECTION_V0.md)
- [TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md)

Decisao:

- o `SIDE` comunal oficial cobre `2012-2024` e e adequado para auditar ou substituir o target proxy
- o proxy atual tem alta correlacao com `SIDE`, mas esta inflado em nivel
- `SIDE` estabelecimentos passa a ser o candidato principal para target formal
- `SIDE` empresas fica como alvo de sensibilidade
- o proxy atual deve permanecer como serie auxiliar/auditoria, nao como ground truth final

Proximo passo:

- reconstruir um pacote alternativo com target oficial `SIDE`
- repetir persistencia, baselines autoregressivos, espaciais e com features antes de qualquer arquitetura complexa

### 2026-04-13 - Rebuild com target oficial SIDE

O que foi feito:

- criacao do painel de target oficial `SIDE` estabelecimentos por `ZE2020`
- criacao de novo pacote tensorial usando o mesmo painel de features, mas com alvo oficial
- reexecucao dos baselines de persistencia, autoregressivo e espacial
- reexecucao do baseline com features externas sobre o target oficial

Artefatos:

- [build_side_target_panel_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_side_target_panel_core_v0.py)
- [target_side_establishments_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_side_establishments_annual_core_v0.csv)
- [TARGET_SIDE_ESTABLISHMENTS_ANNUAL_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_SIDE_ESTABLISHMENTS_ANNUAL_CORE_V0.md)
- [build_stgnn_tensor_package_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_stgnn_tensor_package_side_target_core_v0.py)
- [stgnn_tensor_package_side_target_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/stgnn_tensor_package_side_target_core_v0.npz)
- [STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md)
- [evaluate_side_target_baselines_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_side_target_baselines_core_v0.py)
- [SIDE_TARGET_BASELINES_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_TARGET_BASELINES_CORE_V0.md)
- [evaluate_feature_augmented_baseline_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_feature_augmented_baseline_side_target_core_v0.py)
- [FEATURE_AUGMENTED_BASELINE_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_AUGMENTED_BASELINE_SIDE_TARGET_CORE_V0.md)

Decisao:

- o alvo oficial `SIDE` substitui o proxy como candidato principal de modelagem
- a persistencia local continua sendo o baseline principal a ser batido
- a media dos vizinhos geografica continua sem ganho, com `alpha = 1.0`
- o baseline com features externas piora fortemente contra persistencia
- nao ha justificativa tecnica para arquitetura complexa nesta etapa sem melhorar profundidade temporal, selecao de features ou construcao do grafo

### 2026-04-13 - Auditoria de selecao de features Phase 1

Motivacao:

- os baselines com features externas pioraram contra persistencia
- antes de qualquer experimento com grafo ou STGNN, e necessario saber quais features tem sinal real no treino
- a selecao deve usar apenas o split de treino, com mascara de observacao, para evitar decisao contaminada pelo futuro

O que foi feito:

- calculo de taxa de observacao por feature e por ano no treino
- calculo de correlacao de Pearson com o target usando apenas celulas observadas no treino
- classificacao de cada feature em: `include`, `include_flagged`, `exclude`
- producao de recomendacao auditavel para o subconjunto Phase 1

Artefatos:

- [evaluate_feature_selection_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_feature_selection_core_v0.py)
- [feature_selection_audit_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/feature_selection_audit_core_v0.csv)
- [feature_selection_audit_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/feature_selection_audit_core_quality_v0.json)
- [FEATURE_SELECTION_AUDIT_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_SELECTION_AUDIT_CORE_V0.md)

Resultados principais:

- `flores_presential_unit_loc_total` e `flores_productive_unit_loc_total`: excluidas — `train_obs_rate = 0.0`, sem observacao real no treino
- `13` features sinalizadas com `train_obs_rate = 0.33`: apenas o ano de feature `2021` tem observacao no treino
- `8` features incluidas diretamente: `filosofi` (2 anos de treino observados) e `6` features estaticas
- top correlacoes com target: `side_stocks_ul_total` (`0.998`), `side_stocks_et_total` (`0.998`), `jobs_lt_total` (`0.994`)

Achado estrutural:

- a esparsidade das features de alto sinal nao e um problema de qualidade de dado
- e um problema de cobertura temporal: `RP 2022` e `SIDE stocks 2021` so cobrem o ano de feature `2021`
- os anos de feature `2019` e `2020` ficam praticamente vazios de sinal dinamico
- isso valida diretamente a necessidade de extensao temporal como proximo passo estrategico

Alerta metodologico:

- `side_stocks_et_total` e `side_stocks_ul_total` tem correlacao `0.998` com o target `SIDE` de criacoes
- isso e esperado (estoque de estabelecimentos prediz volume de criacoes), mas cria risco de colinearidade
- qualquer modelo que use essas features precisa documentar explicitamente que o ganho pode ser trivial (predicao por escala, nao por dinamica)
- isso nao e vazamento temporal, mas e um risco de interpretacao que deve aparecer na tese

Decisao:

- `FLORES` excluido dos experimentos Phase 1 formalmente
- features dinamicas esparsas incluidas com sinalizacao, nao excluidas, porque tem sinal real quando observadas
- o subconjunto efetivo Phase 1 passa a ser `21` features (23 - 2 FLORES)
- a sparsidade confirma que extensao temporal e a proxima alavanca de melhoria mais direta
- proximo passo tecnico: construir grafo de mobilidade a partir de fluxos domicilio-trabalho RP 2021, que ja esta disponivel localmente

### 2026-04-13 - Grafo de mobilidade e baseline espacial comparativo

Motivacao:

- o baseline espacial com grafo geografico escolheu `alpha = 1.0` (ignorar vizinhos) em todos os experimentos anteriores
- a hipotese era que a adjacencia geografica captura a unidade errada de relacao economica
- fluxos domicilio-trabalho capturam interdependencia funcional real entre zonas
- a fonte `base-flux-mobilite-domicile-lieu-travail-2021` estava disponivel localmente com pares origem-destino em nivel comunal

O que foi feito:

- construcao do grafo de mobilidade ZE2020 a partir de pares (CODGEO=residencia, DCLT=trabalho) do RP 2021
- agregacao de fluxos comunais para ZE2020 via mapeamento `commune_to_ze2020_2026`
- geracao de tres variantes de adjacencia: dirigida bruta, simetrica, normalizada por linha com self-loop
- baseline espacial comparativo com target oficial SIDE: persistencia vs. vizinhos-geo vs. vizinhos-mobilidade
- selecao de alpha em validacao para cada grafo

Artefatos:

- [build_mobility_graph_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_mobility_graph_core_v0.py)
- [mobility_graph_edges_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_edges_core_v0.csv)
- [mobility_adjacency_raw_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_raw_core_v0.csv)
- [mobility_adjacency_row_normalized_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_row_normalized_core_v0.csv)
- [mobility_graph_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_graph_core_v0.npz)
- [MOBILITY_GRAPH_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/MOBILITY_GRAPH_CORE_V0.md)
- [evaluate_mobility_spatial_baseline_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_mobility_spatial_baseline_core_v0.py)
- [mobility_spatial_baseline_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_spatial_baseline_predictions_core_v0.csv)
- [MOBILITY_SPATIAL_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/MOBILITY_SPATIAL_BASELINE_CORE_V0.md)
- [mobility_spatial_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/mobility_spatial_baseline_metrics_core_v0.json)

Resultados do grafo de mobilidade:

- `27.571` pares inter-zona com fluxo (vs. `1.486` arestas no grafo geografico)
- grau medio de saida: `98.5` zonas conectadas por trabalhadores
- cobertura de fluxo no core: `17.1%` do total nacional

Resultados do baseline comparativo:

- persistencia (validacao): WMAPE = `3.566`
- media de vizinhos geograficos (validacao): WMAPE = `89.559`
- media de vizinhos de mobilidade (validacao): WMAPE = `255.938`
- ambos os grafos escolheram `alpha = 1.0` na validacao

Leitura estrutural:

- o grafo de mobilidade e muito mais denso que o geografico (grau medio `98` vs. ~`10`)
- isso faz a media ponderada colapsar para algo proximo da media nacional
- predicao pela media de ~100 zonas vizinhas e essencialmente predicao macroeconomica, nao local
- isso explica o WMAPE altissimo da media de vizinhos de mobilidade (`256` vs. `89` do geografico)

Decisao:

- o grafo de mobilidade nao agrega sinal preditivo com media simples de vizinhos
- a falha nao e do dado de mobilidade, e da operacao de suavizacao espacial com grafo denso
- um STGNN pode usar o grafo de mobilidade de forma diferente (passagem de mensagem seletiva, atencao, etc.)
- porem, antes de qualquer STGNN, a conclusao de baseline se fortalece:
  *nenhum grafo simples — geografico ou de mobilidade — supera persistencia local com os dados atuais*
- isso nao invalida o uso do grafo: ele pode capturar relacoes que so aparecem com profundidade temporal adequada
- a alavanca prioritaria passa a ser extensao temporal das features (FLORES historico, SIDE stocks 2019-2020)
- o grafo de mobilidade fica como alternativa disponivel para experimentos STGNN futuros

### 2026-04-13 - Extensao temporal das features (SIDE stocks 2019-2020 + FLORES historico 2019-2021)

O que foi feito:

- adicionadas 7 novas colunas ao `zones_master_annual_v0.csv`:
  `side_stocks_et_2019_total`, `side_stocks_ul_2019_total`,
  `side_stocks_et_2020_total`, `side_stocks_ul_2020_total`,
  `flores_et_total_2019`, `flores_et_total_2020`, `flores_et_total_2021`
- atualizado `build_panel_zones_v0.py`: FEATURE_SPECS expandido para mapear os novos anos
- adicionado `flores_et_total` como nova feature dinamica em `build_pre_stgnn_core_v0.py` e `build_graph_model_annual_package_core_v0.py`
- reconstruida a cadeia completa: panel → core views → pre_stgnn → tensor package

Fontes usadas:

- SIDE ET 2019-2020: `DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip` (nivel ZE2020 direto, sem agregar)
- SIDE UL 2019-2020: `DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip` (nivel ZE2020 direto)
- FLORES 2019-2021: `TD_FLORES{ano}_NA17_TREF_NBETAB_CSV.zip` (nivel comunal, `ET_TOT`, mapeado para ZE2020)

Artefatos:

- [enrich_zones_master_temporal_depth_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/enrich_zones_master_temporal_depth_core_v0.py)
- [temporal_depth_enrichment_core_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/temporal_depth_enrichment_core_quality_v0.json)
- [TEMPORAL_DEPTH_ENRICHMENT_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_DEPTH_ENRICHMENT_CORE_V0.md)

Resultado na auditoria de features (tensor STGNN SIDE target, re-executado):

| feature | train_obs antes | train_obs depois | corr target |
|---|---|---|---|
| `side_stocks_et_total` | 0.33 | **1.00** | 0.998 |
| `side_stocks_ul_total` | 0.33 | **1.00** | 0.998 |
| `flores_et_total` | n/a (nova) | **1.00** | 0.937 |

- `flores_presential_unit_loc_total` e `flores_productive_unit_loc_total` permanecem excluidas (2024 only, nao disponivel para anos de treino)
- tensor atual: `25 features`, `5 amostras anuais`, `train=3, val=1, test=1`
- baselines de persistencia e grafos nao mudam (nao usam features)

Decisao:

- as tres features de maior cobertura e correlacao estao agora completamente observadas no treino
- isso elimina o problema critico de `side_stocks_et_total` com `train_obs=0.33` (apenas 1 ano de treino com SIDE)
- o tensor esta pronto para primeiros experimentos de modelos com features
- o proximo passo e um ridge/linear baseline usando as features do tensor para verificar se o ganho sobre persistencia aparece quando se usam as features diretamente

### 2026-04-13 - Revisao bibliografica: WMGCN como base metodologica

Paper lido: **"Predicting Economic Growth by Region Embedding: A Multigraph Convolutional Network Approach"** (Hui et al., CIKM 2020, 27 citacoes)

DOI: 10.1145/3340531.3411882

O que o paper faz:

- Aprende embeddings de ZIP code areas para representar o crescimento economico setorial
- Constroi um multigrafo com 3 tipos de arestas: distrito escolar, condado, conexoes aereas
- Usa 4 GCNs separados por categoria de feature (demografica, social, economica, habitacao)
- Integracao por soma ponderada com apenas 4 pesos trenaveis — principio de Occam's Razor explicitamente invocado
- Dados: US Census Bureau ACS (governamental, aberto) — equivalente estrutural ao INSEE/SIDE

Alinhamento direto com a nossa arquitetura:

| elemento WMGCN | equivalente no projeto |
|---|---|
| multigrafo (escola, condado, voos) | grafo geografico + grafo de mobilidade (Stage 2) |
| features ACS por categoria | features INSEE por dominio (labour, economic, income, services) |
| embeddings regionais h_i | saida do STGNN para os agentes |
| dados governamentais abertos | INSEE, SIDE, FLORES, BPE |
| Occam's Razor — frugalidade | titulo da tese "recommandation territoriale frugale" |

O que o WMGCN NAO tem (lacuna que a tese preenche):

- Sem dimensao temporal — o target e crescimento estatico 2011-2016
- Sem backbone STGNN — nao ha previsao de serie temporal no grafo
- Sem camada de agentes — nao ha orquestracao decisional
- Sem multi-step forecasting — nao ha horizonte temporal futuro

Avanco sobre o WMGCN na literatura (citacoes relevantes, 2022-2023):

- "Learning Economic Indicators by Aggregating Multi-Level Geospatial Information" (2022, 19 cit) — avanca na agregacao geografica multi-nivel mas sem dimensao temporal
- "Heterogeneous Region Embedding with Prompt Learning" (2023, 42 cit) — adiciona prompt learning mas ainda sem STGNN
- "HUGAT — Heterogeneous Urban Graph Attention Network" (2022, 16 cit) — adiciona atencao mas sem agentes
- Survey STGNN para urban computing (2023, 435 cit) — posiciona o problema no panorama espaço-temporal mas sem orchestracao agente

Conclusao da revisao:

Nenhum paper combina: (1) embedding regional multigrafo + (2) backbone STGNN temporal + (3) camada de agentes analiticos orquestrados. A lacuna esta confirmada e e exatamente o que a tese propoe. O WMGCN serve como referencia metodologica para o Stage 2 (GRAPH HYBRID) e justifica o design do multigrafo geografico + mobilidade ja construido.

Acao no documento da tese:

- A citacao Wu2019 (Graph WaveNet) no `.tex` pode ser complementada ou substituida por Hui2020 (WMGCN) como referencia para a construcao do multigrafo no Stage 2
- O STGNN no Stage 3 e a extensao temporal natural dos embeddings do WMGCN

### 2026-04-13 - Inventario temporal e pacote longo SIDE

O que foi feito:

- criada auditoria de disponibilidade temporal das features atuais
- preservadas explicitamente as adicoes recentes: `SIDE stocks`, `FLORES historico` e `SIDE creations`
- separado o problema em dois pacotes:
  - pacote rico: mais features, janela `2019-2023 -> 2020-2024`
  - pacote longo: mais anos supervisionados, usando historico oficial `SIDE`
- criado baseline longo com 5 lags do target `SIDE`

Artefatos:

- [audit_feature_temporal_availability_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/audit_feature_temporal_availability_core_v0.py)
- [FEATURE_TEMPORAL_AVAILABILITY_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_TEMPORAL_AVAILABILITY_CORE_V0.md)
- [feature_temporal_availability_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/feature_temporal_availability_core_v0.csv)
- [supervised_year_availability_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/supervised_year_availability_core_v0.csv)
- [build_long_history_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_long_history_side_target_core_v0.py)
- [long_history_side_target_dataset_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/long_history_side_target_dataset_core_v0.csv)
- [LONG_HISTORY_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/LONG_HISTORY_SIDE_TARGET_CORE_V0.md)

Resultado:

- pacote rico atual: `5` amostras anuais, `train=3`, `validation=1`, `test=1`
- pacote longo SIDE: `8` amostras anuais, `train=5`, `validation=1`, `test=2`
- no pacote longo, persistencia continua vencendo na validacao: WMAPE `3.369`
- ridge autoregressivo melhora no treino/teste, mas perde para persistencia na validacao
- media dos vizinhos geograficos continua muito pior, com `alpha=1.0`

Decisao:

- nao descartar as features adicionadas; elas permanecem no pacote rico
- nao fundir pacote rico e pacote longo sem nome explicito
- usar o pacote longo para testar memoria temporal do alvo
- usar o pacote rico para testar covariaveis e arquitetura com mais contexto

### 2026-04-13 - Comparacao pacote rico vs pacote longo SIDE

O que foi feito:

- consolidada comparacao entre baselines do pacote rico, pacote rico com features e pacote longo
- criado registro unico de metricas por pacote/modelo/split
- identificadas features candidatas para um hibrido controlado

Artefatos:

- [compare_rich_vs_long_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/compare_rich_vs_long_side_target_core_v0.py)
- [RICH_VS_LONG_SIDE_TARGET_COMPARISON_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RICH_VS_LONG_SIDE_TARGET_COMPARISON_CORE_V0.md)
- [rich_vs_long_side_target_comparison_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/rich_vs_long_side_target_comparison_core_v0.csv)

Resultado:

- pacote rico temporal: persistencia vence na validacao, ridge vence no teste
- pacote rico com todas as features: persistencia continua vencendo; features externas amplas pioram muito
- pacote longo SIDE: persistencia vence na validacao, ridge melhora no teste

Decisao:

- proximo baseline deve ser hibrido e controlado
- base temporal: lags oficiais `SIDE`
- features candidatas: `side_stocks_et_total`, `side_stocks_ul_total`, `flores_et_total`
- manter `side_creations_et_total` rotulado como historico do target

### 2026-04-13 - Baseline hibrido controlado

O que foi feito:

- testado baseline hibrido com poucos grupos de features
- base comum: 5 lags oficiais `SIDE` e taxas recentes de crescimento
- grupos testados:
  - `lags_only`
  - `lags_plus_side_stocks`
  - `lags_plus_side_stocks_flores`

Artefatos:

- [evaluate_controlled_hybrid_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_controlled_hybrid_side_target_core_v0.py)
- [CONTROLLED_HYBRID_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/CONTROLLED_HYBRID_SIDE_TARGET_CORE_V0.md)
- [controlled_hybrid_side_target_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/controlled_hybrid_side_target_metrics_core_v0.json)

Resultado:

- persistencia continua vencendo na validacao: WMAPE `3.566`
- `lags_only`: validacao WMAPE `7.302`, teste WMAPE `3.326`
- `lags_plus_side_stocks`: validacao WMAPE `9.971`, teste WMAPE `3.497`
- `lags_plus_side_stocks_flores`: validacao WMAPE `10.716`, teste WMAPE `6.506`

Decisao:

- o hibrido controlado ainda nao supera persistencia em validacao
- `SIDE stocks` e `FLORES` nao devem ser tratados como ganho preditivo confirmado nesta janela
- proximo ganho provavel nao vira de mais features tabulares rasas, mas de melhor grafo de mobilidade ou validacao por grupos de zonas

### 2026-04-13 - Diagnostico de erro por grupos de zonas

O que foi feito:

- criado diagnostico dos erros por tamanho e volatilidade das zonas `ZE2020`
- comparados pacotes `rich_temporal`, `long_history` e `controlled_hybrid`
- identificado onde a persistencia falha no teste do pacote longo

Artefatos:

- [evaluate_zone_group_errors_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_zone_group_errors_side_target_core_v0.py)
- [ZONE_GROUP_ERROR_DIAGNOSTICS_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ZONE_GROUP_ERROR_DIAGNOSTICS_SIDE_TARGET_CORE_V0.md)
- [zone_group_error_metrics_side_target_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/zone_group_error_metrics_side_target_core_v0.csv)
- [zone_error_profile_side_target_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/zone_error_profile_side_target_core_v0.csv)

Resultado:

- no teste do pacote longo, zonas pequenas tem WMAPE mais alto: `8.550`
- zonas grandes concentram os maiores erros absolutos: Paris, Marseille, Lyon, Bordeaux e Toulouse
- por volatilidade, nao ha uma separacao extrema; o problema principal combina escala urbana e choques locais
- persistencia continua forte globalmente, mas esconde perfis territoriais diferentes

Decisao:

- antes de STGNN, testar baseline segmentado por perfil de zona
- nao tratar erro medio global como criterio suficiente
- manter grafos geografico e de mobilidade como estruturas disponiveis, mas nao usar media simples de vizinhos como solucao

### 2026-04-13 - Baseline segmentado por perfil de zona

O que foi feito:

- criado baseline segmentado usando perfis calculados apenas com historico ate `2021`
- grupos usados: tamanho, volatilidade e tamanho+volatilidade
- para cada grupo, o modelo foi escolhido na validacao entre persistencia, delta, media movel, ridge autoregressivo e blend espacial

Artefatos:

- [evaluate_segmented_side_target_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_segmented_side_target_core_v0.py)
- [SEGMENTED_SIDE_TARGET_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SEGMENTED_SIDE_TARGET_BASELINE_CORE_V0.md)
- [segmented_side_target_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/segmented_side_target_predictions_core_v0.csv)
- [segmented_zone_profile_side_target_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/segmented_zone_profile_side_target_core_v0.csv)

Resultado:

- persistencia longa: validacao WMAPE `3.369`, teste WMAPE `6.664`
- segmentado por tamanho+volatilidade: validacao WMAPE `3.259`, teste WMAPE `6.564`
- ridge autoregressivo: validacao WMAPE `4.850`, teste WMAPE `6.406`

Decisao:

- segmentacao e o primeiro ganho metodologico limpo sobre persistencia na validacao
- o ganho ainda e pequeno, entao nao substitui sozinho o baseline principal
- o ridge vence no teste, mas perde na validacao; deve ser tratado como candidato, nao como modelo final
- proximo passo: criar uma matriz de decisao simples entre persistencia, ridge e segmentacao antes de qualquer STGNN

### 2026-04-13 - Matriz de decisao dos baselines SIDE

O que foi feito:

- criada matriz de decisao auditavel entre persistencia, ridge, segmentacao e baseline rico de lags
- definida persistencia como baseline conservador obrigatorio
- definida margem minima de `0.050` ponto de WMAPE na validacao para candidato forte
- documentada a restricao de comparabilidade entre pacote longo e pacote rico

Artefatos:

- [build_side_model_decision_matrix_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_side_model_decision_matrix_core_v0.py)
- [SIDE_MODEL_DECISION_MATRIX_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_MODEL_DECISION_MATRIX_CORE_V0.md)
- [side_model_decision_matrix_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/side_model_decision_matrix_core_v0.csv)

Resultado:

- candidato recomendado: `segmented_by_size_volatility_group`
- melhor validacao: `segmented_by_size_volatility_group`, WMAPE `3.259`
- melhor teste numerico: `rich_lags_only`, WMAPE `3.326`, mas em janela curta diferente
- persistencia permanece baseline conservador e referencia obrigatoria

Decisao:

- nao avancar para STGNN ainda
- proximo passo metodologico: backtest temporal adicional da regra segmentada
- se a regra segmentada permanecer estavel, ela vira baseline forte para comparar contra modelos grafo-temporais

### 2026-04-13 - Backtest rolante da regra segmentada

O que foi feito:

- testada validacao temporal rolante
- regra escolhida no ano de validacao e aplicada ao ano seguinte
- folds de validacao: `2020`, `2021`, `2022`, `2023`
- candidatos por fold: persistencia, delta, media movel, ridge autoregressivo e blend espacial

Artefatos:

- [backtest_segmented_side_decision_rule_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/backtest_segmented_side_decision_rule_core_v0.py)
- [SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md)
- [segmented_decision_rule_backtest_metrics_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/segmented_decision_rule_backtest_metrics_core_v0.csv)
- [segmented_decision_rule_backtest_predictions_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/segmented_decision_rule_backtest_predictions_core_v0.csv)

Resultado:

- melhor WMAPE medio no teste rolante: `ridge_autoregressive`, WMAPE `7.554`
- persistencia no teste rolante: WMAPE medio `7.680`
- segmentacao tamanho+volatilidade no teste rolante: WMAPE medio `8.704`
- a regra segmentada melhora a validacao media, mas nao generaliza bem para o ano seguinte

Decisao:

- a matriz de decisao fixa foi util, mas nao e suficiente
- segmentacao nao deve ser promovida a baseline principal
- persistencia continua baseline conservador
- ridge autoregressivo vira desafiante principal, mas precisa de diagnostico de instabilidade por fold antes de qualquer STGNN

### 2026-04-13 - Diagnostico da instabilidade por fold

O que foi feito:

- comparados folds de teste do backtest rolante
- calculado crescimento agregado real contra `y_lag_0`
- identificado quando ridge melhora ou piora contra persistencia
- listadas piores zonas por erro absoluto da persistencia

Artefatos:

- [diagnose_backtest_instability_side_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/diagnose_backtest_instability_side_core_v0.py)
- [SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md)
- [side_backtest_fold_instability_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/side_backtest_fold_instability_core_v0.csv)
- [side_backtest_group_instability_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/side_backtest_group_instability_core_v0.csv)
- [side_backtest_worst_zones_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/side_backtest_worst_zones_core_v0.csv)

Resultado:

- fold `2020 -> 2021`: crescimento agregado `+16.7%`; ridge reduz WMAPE de `14.317` para `8.358`
- fold `2021 -> 2022`: crescimento agregado `+1.1%`; persistencia vence, ridge piora para `8.338`
- fold `2022 -> 2023`: crescimento agregado `-1.4%`; persistencia vence, ridge piora para `10.406`
- fold `2023 -> 2024`: crescimento agregado `+10.4%`; ridge reduz WMAPE de `9.470` para `3.113`

Decisao:

- o problema principal nao e apenas tipo de zona; e regime temporal agregado
- ridge ajuda quando ha aceleracao agregada forte
- persistencia domina quando o proximo ano e estavel ou negativo
- proximo baseline deve ser uma regra de regime temporal entre persistencia e ridge

### 2026-04-13 - Regra simples de regime temporal

O que foi feito:

- testada regra entre persistencia e ridge usando apenas crescimento agregado ja observado no ano de feature
- threshold escolhido na validacao de cada fold
- incluido `oracle_regime_not_usable` apenas como teto diagnostico

Artefatos:

- [evaluate_temporal_regime_side_baseline_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/evaluate_temporal_regime_side_baseline_core_v0.py)
- [TEMPORAL_REGIME_SIDE_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_REGIME_SIDE_BASELINE_CORE_V0.md)
- [temporal_regime_side_baseline_metrics_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/temporal_regime_side_baseline_metrics_core_v0.csv)

Resultado:

- regra temporal simples: WMAPE medio de teste `9.143`
- persistencia: WMAPE medio de teste `7.680`
- ridge: WMAPE medio de teste `7.554`
- oracle nao utilizavel: WMAPE medio de teste `4.302`

Decisao:

- a regra com crescimento observado nao e suficiente
- o oracle mostra que escolher o regime correto teria grande valor
- falta um sinal antecipador externo de regime; sem isso, o modelo so descobre o choque tarde demais
- proximo passo deve ser auditar sinais candidatos de regime, como `DS_ICA`, contas regionais ou outros indicadores macro/setoriais

### 2026-04-13 - Consolidacao e higiene dos artefatos

O que foi feito:

- removidos caches e saidas locais ignoradas que nao fazem parte do fluxo versionado
- criada entrada principal do projeto em `README.md`
- criado registro canonico de artefatos em `metadata/canonical_artifacts_v0.csv`
- atualizado o indice do projeto para apontar apenas os arquivos que devem ser lidos primeiro
- reforcado `.gitignore` para evitar retorno de `graphify-out` e `reports/scan_archives`

Decisao:

- nao mover dados processados ainda, porque varios scripts antigos escrevem caminhos historicos
- separar agora o que e canonico do que e diagnostico
- uma migracao fisica de pastas so deve ser feita em etapa propria, com atualizacao dos scripts e validacao

### 2026-04-13 - Refinamento Metodologico e Mitigacao de Vazamento

Motivacao:

- a auditoria inicial apresentava vazamento contemporaneo (nowcast) no sinal de regime
- bugs estatisticos no perfil setorial invalidavam os relatorios de qualidade
- a correlacao pooled global era enganosa e escondia a fraqueza do sinal intra-ano

O que foi feito:

- correcao do bug no script de perfil setorial (pesos agora restritos a [0,1])
- alteracao do `regime_leading_signal` para modo **forecast**: utiliza apenas o 1º trimestre (Jan-Mar) para prever o ano fechado
- reconstrucao do Painel Estendido e do Pacote Tensorial com o sinal refinado
- reexecucao dos baselines Ridge no pacote de 11 anos de treino

Artefatos Corrigidos:

- [build_zone_sectoral_profile_core_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_zone_sectoral_profile_core_v0.py)
- [build_leading_regime_signal_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/build_leading_regime_signal_v0.py)
- [stgnn_tensor_package_extended_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/stgnn_tensor_package_extended_core_v0.npz)

Veredito Tecnico Seguro:

- O sinal setorial-mensal e um candidato a indicador de regime, mas a evidencia atual ainda e dominada por tendencia temporal comum.
- O pacote `extended` aumenta a profundidade temporal para 11 anos reais, mas o Ridge linear ainda nao supera a persistencia (Val: 8.2% vs 3.5%).
- A falha do modelo linear em converter o sinal de regime em ganho preditivo intra-ano valida a necessidade de investigar arquiteturas nao-lineares (STGNN) e mecanismos de atencao espacial.

Decisao:

- Decisao historica superada por auditorias posteriores.
- Naquele momento, `STGNN` parecia um proximo experimento logico.
- Apos os testes locais, engenharia de features e selecao causal, a decisao atual mudou: nao iniciar `STGNN` ainda.
- Manter este bloco apenas como rastreabilidade da evolucao metodologica.

### 2026-04-14 - Saneamento do Extended Core e benchmark exploratorio

O que foi feito:
- Correção de múltiplos vazamentos (escala, estrutural e temporal) no `extended core`.
- Remoção da injeção de regime no tensor original SIDE, restaurando sua reprodutibilidade canônica.
- Criação de perfis setoriais dinâmicos (Target T usa Perfil T-1) a partir de históricos FLORES (2017-2021) para evitar vazamento estrutural.
- Remoção da população contemporânea, utilizando apenas `pop_lag_1` e `pop_lag_2`.
- Implementação de um backtest rolante rigoroso (2018-2024), escalonando e imputando dados estritamente dentro de cada fold.
- Construcao e integracao de um grafo economico de mobilidade (Censo RP 2021) superando marginalmente o grafo geografico linear.
- Download massivo de novos datasets externos para investigação de variação local: Energia (SDES), Construção (SITADEL) e Fiscalidade (REI).

Artefatos:
- `stgnn_tensor_package_side_target_core_v0.npz` (restaurado)
- `stgnn_tensor_package_extended_forecast_core_v1.npz` (forecast-safe)
- `stgnn_tensor_package_extended_nowcast_q1_core_v1.npz` (forecast-safe + choque Q1)
- `stgnn_tensor_package_extended_diagnostic_core_v1.npz` (diagnostico, nao usar como forecast)
- `metadata/extended_core_feature_classification_v0.csv`
- `reports/EXTENDED_CORE_VERIFICATION_SUMMARY_V0.md`

Decisão:
- A previsão de volume bruto provou ser superior à previsão de taxa de criação (WMAPE 7.66% vs >80%).
- O benchmark linear a ser batido foi consolidado em 7.66% (`ridge_lag_only`), empatando virtualmente com a persistência (7.68%).
- O STGNN passa a ser formalmente um experimento exploratorio para testar valor nao-linear das novas features. Nao ha ainda evidencia de necessidade do STGNN.
- Início da exploração de variáveis de calor local (Energia, SITADEL, REI) para dar ao modelo sensores físicos de crise e expansão.


### 2026-04-14 - Inicio da fase "Calor Local" com dados SITADEL

Motivacao:
- Responder a lacuna estrutural do "Extended Core" em relacao a "ondas locais".
- Modelos lineares baseados apenas em historico nao captam bem choques em anos anomalos (ex. 2020-2022).
- Os novos datasets externos serao usados como proxies de "intenção de expansao fisica" (SITADEL) e "peso imobiliario estrutural" (REI).

O que foi feito:
- Escrita e execucao do script de extracao e agregacao `build_sitadel_surface_ze2020_v0.py`.
- Lida a tabela de permissoes de construcao "Locais Nao Residenciais" da base SITADEL a nivel comunal.
- Agregadas as metragens quadradas (SDP_AUT e SDP_COM) por ano e por Zone d'Emploi (ZE2020).

Artefatos:
- `src/data/build_sitadel_surface_ze2020_v0.py`
- `data/interim/tables/sitadel_surface_ze2020_v0.csv`
- `reports/sitadel_surface_quality_v0.json`

Decisao:
- O indicador de metragem aprovada (`sitadel_surface_autorisee_lag_1`) e iniciada (`sitadel_surface_commencee_lag_1`) sera tratado como proxy local defasada de expansao fisica. No primeiro teste linear, SITADEL nao superou o baseline temporal; por isso fica como feature exploratoria, nao como evidencia conclusiva.

### 2026-04-15 - Protocolo conservador para REI e Energia

Motivacao:
- Evitar adicionar novas fontes diretamente ao tensor principal sem demonstrar ganho incremental.
- Tratar REI e Energia como fontes candidatas de "calor local", sempre defasadas em `T-1`.
- Manter a comparacao contra `ridge_lag_only` como filtro metodologico minimo.

O que foi feito:
- Criado `src/data/build_rei_cfe_ze2020_v0.py` para extrair proxies CFE do REI comunal e agregar por ZE2020.
- Criado `src/data/build_energy_consumption_ze2020_v0.py` para extrair consumo eletrico/gas nao residencial na malha IRIS e agregar por ZE2020.
- Criado `src/data/evaluate_local_candidate_features_v0.py` para testar fontes candidatas como lags contra o baseline temporal.
- Executada avaliacao leve com SITADEL ja processado.

Resultado atual:
- `ridge_lag_only`: WMAPE medio `7.66%`.
- `persistence`: WMAPE medio `7.68%`.
- `ridge_sitadel_only`: WMAPE medio `8.43%`.

Decisao:
- SITADEL permanece como feature candidata, nao como evidencia de ganho.
- REI e Energia devem ser processados e avaliados pelo mesmo protocolo antes de entrar em qualquer tensor canonico.

### 2026-04-16 - Auditoria incremental de REI e Energia

Motivacao:
- Verificar se as novas fontes de "calor local" realmente melhoram o baseline temporal.
- Evitar inflar o tensor com variaveis plausiveis, mas sem ganho preditivo demonstrado.

O que foi feito:
- Corrigido o leitor REI para lidar com CSV em encoding `cp1252/latin1`.
- Processado REI CFE para `2023-2024`, agregado por ZE2020.
- Processada Energia SDES eletricidade/gas nao residencial na malha IRIS para `2018-2024`, agregada por ZE2020.
- Reexecutada avaliacao incremental de candidatos locais.

Artefatos:
- `data/interim/tables/rei_cfe_ze2020_v0.csv`
- `data/interim/tables/energy_consumption_ze2020_v0.csv`
- `reports/rei_cfe_quality_v0.json`
- `reports/energy_consumption_quality_v0.json`
- `reports/local_candidate_feature_metrics_v0.json`
- `reports/LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md`

Resultado:
- `ridge_lag_only`: WMAPE medio `7.66%`.
- `ridge_rei_only`: WMAPE medio `7.66%`, sem ganho real por cobertura temporal curta.
- `persistence`: WMAPE medio `7.68%`.
- `ridge_sitadel_only`: WMAPE medio `8.43%`.
- `ridge_energy_only`: WMAPE medio `8.66%`.
- `ridge_local_all`: WMAPE medio `8.84%`.

Decisao:
- Nao adicionar REI, Energia ou SITADEL ao tensor canonico neste momento.
- Manter as fontes como familias candidatas para ablacoees e possiveis transformacoes.
- Para REI, proximo passo util seria converter anos XLSX historicos antes de nova conclusao.
- Para Energia, proximo passo util seria testar variacoes ano-a-ano e nao apenas niveis defasados.

### 2026-04-16 - Inventario bruto externo e fila de prioridade

Motivacao:
- Afirmar que uma familia de dados "nao ajuda" seria incorreto enquanto arquivos grandes ainda nao foram processados.
- Separar conclusoes sobre subconjuntos ja testados de potencial ainda nao explorado.

O que foi feito:
- Criado `src/data/build_raw_external_inventory_v0.py`.
- Gerado inventario completo dos arquivos em `data/raw/external`.
- Classificados arquivos por familia, tamanho, status de processamento e prioridade.
- Identificados arquivos ainda nao processados que podem mudar a avaliacao metodologica.

Artefatos:
- `metadata/raw_external_inventory_v0.csv`
- `reports/RAW_EXTERNAL_INVENTORY_V0.md`

Resultado:
- Total inventariado: `72` arquivos.
- Volume bruto externo: `7702.78 MB`.
- Processado integralmente: SITADEL anual comunal.
- Processado parcialmente: Energia IRIS 2018-2024 e REI 2023-2024.
- Pendente de alta prioridade: SITADEL mensal comunal `3.35 GB`, REI historico `2018-2022`, Energia historica `2008-2017`.

Decisao:
- As conclusoes negativas atuais valem somente para subconjuntos processados e em forma bruta defasada.
- Proxima etapa deve atacar primeiro `SITADEL mensal comunal`, depois `Energia historica 2008-2017`, depois `REI historico convertido`.

### 2026-04-16 - Preparacao do processamento SITADEL mensal

Motivacao:
- O arquivo SITADEL mensal comunal tem `3.35 GB` e cerca de `62M` linhas.
- Rodar esse processamento dentro do agente queimaria contexto sem necessidade.
- A forma correta e deixar um script reprodutivel e o usuario executar localmente.

O que foi feito:
- Criado `src/data/build_sitadel_monthly_ze2020_v0.py`.
- O script le o CSV em chunks, filtra `Ensemble des locaux non-residentiels`, agrega por `ZE2020`, ano e mes.
- O script tambem gera derivacoes anuais `total`, `q1` e `h1` para separar uso forecast e nowcast.

Artefatos esperados apos execucao:
- `data/interim/tables/sitadel_monthly_surface_ze2020_v0.csv`
- `data/interim/tables/sitadel_monthly_derived_annual_ze2020_v0.csv`
- `reports/sitadel_monthly_surface_quality_v0.json`

Decisao:
- Nao incluir SITADEL mensal no tensor canonico antes de avaliar `T-1`, `Q1 nowcast`, transformacoes log/YoY e ablacoees contra `ridge_lag_only`.

### 2026-04-16 - Avaliacao incremental do SITADEL mensal

Motivacao:
- Verificar se a granularidade mensal resolve a fraqueza do SITADEL anual bruto.
- Separar corretamente previsao pura (`T-1`) de nowcast (`Q1/H1` do proprio ano).

O que foi feito:
- Integrado `sitadel_monthly_derived_annual_ze2020_v0.csv` ao avaliador de candidatos locais.
- Testados sinais mensais em forma bruta e `log1p`.
- Mantida a regra de escala/imputacao por fold, sem usar futuro.

Resultado:
- `ridge_lag_only`: WMAPE medio `7.66%`.
- `persistence`: WMAPE medio `7.68%`.
- Melhor variante SITADEL mensal: `ridge_sitadel_monthly_q1_nowcast_log`, WMAPE medio `7.89%`.
- Melhor variante forecast-safe: `ridge_sitadel_monthly_lag_log`, WMAPE medio `7.93%`.

Decisao:
- SITADEL mensal melhora a leitura em relacao ao SITADEL anual bruto, especialmente com `log1p`.
- Ainda nao bate o baseline temporal, portanto fica como familia experimental, nao canonica.
- A conclusao defensavel e: `SITADEL mensal e promissor, mas ainda nao provou ganho linear causal sobre o baseline temporal`.

### 2026-04-16 - Auditoria de consistencia antes de commit

Motivacao:
- Reduzir ambiguidades geradas por muitos artefatos.
- Separar explicitamente arquivos canonicos, candidatos e diagnosticos.
- Corrigir qualquer incoerencia tecnica antes de consolidar commit.

O que foi feito:
- Criado `reports/PROJECT_CONSISTENCY_AUDIT_V0.md`.
- Atualizado `metadata/canonical_artifacts_v0.csv` com tensors extended, candidatos locais e relatorios atuais.
- Atualizado `reports/PROJECT_STATE_INDEX_V0.md` para refletir target oficial `SIDE`, tensores extended e candidatos locais.
- Corrigido `src/data/build_stgnn_tensor_package_extended_v1.py`.

Correcao importante:
- `adjacency_mobility` nos tensors extended estava sendo carregada com uma coluna extra do CSV.
- Shape anterior: `280 x 281`.
- Shape corrigido: `280 x 280`.
- O script agora falha explicitamente se `A_geo` ou `A_mobility` nao tiverem shape esperado.

Decisao:
- O projeto esta consistente para consolidar a fase atual em commit.
- STGNN continua como experimento futuro, nao como obrigacao imediata.
- Antes de nova arquitetura, o benchmark a bater permanece `ridge_lag_only = 7.66%` e `persistence = 7.68%`.

### 2026-04-16 - Conversao REI historico e reteste local

Motivacao:
- Fechar a lacuna REI `2018-2022`, que estava presa em XLSX.
- Testar se proxies fiscais CFE com cobertura mais longa superam o baseline temporal.

O que foi feito:
- Criado `src/data/convert_rei_xlsx_to_csv_v0.py`.
- Convertidos localmente os anos REI `2018-2022` usando `python-calamine`.
- Atualizado `src/data/build_rei_cfe_ze2020_v0.py` para normalizar schemas diferentes:
  - `2018`: colunas curtas `P11`, `P13`, `P14`, `P31_*`, `P33_*`, `P34_*`.
  - `2019-2022`: colunas longas `CFE - ...`.
  - `2023-2024`: CSVs diretos dos ZIPs.
- Agregado REI CFE por `ZE2020` para `2018-2024`.
- Reexecutada avaliacao de candidatos locais.

Resultado:
- `ridge_lag_only`: WMAPE medio `7.66%`.
- `persistence`: WMAPE medio `7.68%`.
- `ridge_rei_only`: WMAPE medio `7.77%`.
- `ridge_local_all`: WMAPE medio `7.91%`.
- REI melhora 2023, mas piora 2022 e 2024.

Decisao:
- REI historico e metodologicamente utilizavel como candidato.
- Ainda nao entra no tensor canonico porque nao supera o baseline temporal em media.
- Leitura correta: REI parece sinal local sensivel a regime, nao preditor linear estavel.
- CSVs convertidos em `data/interim/tables/rei_converted_csv_v0/` sao intermediarios grandes e reprodutiveis; ficam ignorados no Git.

### 2026-04-16 - Integracao historica de energia SDES

Motivacao:
- Testar a hipotese de que consumo de energia nao-residencial representa atividade economica local.
- Aumentar profundidade temporal dos candidatos locais antes de decidir qualquer inclusao no tensor canonico.

O que foi feito:
- Atualizado `src/data/build_energy_consumption_ze2020_v0.py`.
- Integrados arquivos historicos SDES `2008-2017` de eletricidade, gas, calor e frio.
- Mantida a integracao dos arquivos `2018-2024` de eletricidade e gas.
- Para os historicos, escolhido um unico nivel territorial por combustivel/ano (`IRIS` quando disponivel, senao `Commune`) para evitar dupla contagem.
- Agregadas as variaveis para `ZE2020`.

Resultado:
- Cobertura de energia: `2008-2024`.
- `306` zonas com pelo menos algum dado energetico.
- Variaveis finais:
  - consumo nao-residencial de eletricidade
  - consumo nao-residencial de gas
  - consumo nao-residencial de calor/frio
  - pontos de entrega nao-residenciais correspondentes
- Primeiros anos sao esparsos, especialmente eletricidade `2008-2010` e gas `2008-2009`.

Reteste:
- `ridge_local_all`: WMAPE medio `7.65%`.
- `ridge_lag_only`: WMAPE medio `7.66%`.
- `persistence`: WMAPE medio `7.68%`.
- `ridge_energy_log`: WMAPE medio `7.99%`.
- `ridge_energy_only`: WMAPE medio `8.01%`.
- Selecao causal de modelo usando apenas anos anteriores: WMAPE medio `9.95%`.

Decisao:
- A hipotese economica e plausivel e recebeu o primeiro sinal quantitativo positivo no modelo combinado.
- O ganho medio ainda e muito pequeno e instavel por ano.
- A selecao causal piora, entao ainda nao sabemos escolher esse ganho sem olhar o futuro.
- Energia fica como familia candidata para modelos locais/nao-lineares e ablation studies.
- Nao entra no tensor canonico enquanto nao houver estabilidade superior ao baseline temporal.

### 2026-04-17 - Primeiro passe de engenharia conservadora de features locais

Motivacao:
- Testar a proposta de substituir niveis absolutos por dinamicas mais invariantes a escala.
- Manter apenas features `forecast-safe`: valores ate `T` para prever `T+1`.
- Evitar denominadores potencialmente arriscados, como estoque contemporaneo ainda nao auditado como fonte historica segura.

O que foi feito:
- Atualizado `src/data/evaluate_local_candidate_features_v0.py`.
- Adicionadas features autoregressivas do alvo oficial SIDE:
  - `target_side_log_diff_1y`
  - `target_side_log_diff_2y`
  - `target_side_roll_mean_3y_log`
  - `target_side_acceleration`
- Adicionadas features de energia:
  - log-diff `1y` e `2y`
  - volatilidade `3y`
  - share eletricidade/gas
  - log-diff de pontos de entrega
- Adicionadas features REI:
  - log-diff de base, produto e artigos CFE
  - volatilidade `3y` da base CFE
- Adicionadas features SITADEL:
  - media movel `2y` log de superficie autorizada/começada
  - volatilidade `3y` de superficie autorizada/começada

Resultado:
- Melhor resultado geral continua `ridge_local_all`: WMAPE medio `7.65%`.
- `ridge_lag_only`: WMAPE medio `7.66%`.
- Melhor familia engenheirada: `ridge_engineered_sitadel`, WMAPE medio `7.97%`.
- `ridge_engineered_energy`: WMAPE medio `8.04%`.
- `ridge_engineered_target`: WMAPE medio `8.77%`.
- `ridge_engineered_rei`: WMAPE medio `15.35%`.
- `ridge_engineered_all`: WMAPE medio `16.89%`.
- Selecao causal com modelos engenheirados: WMAPE medio `10.44%`.

Decisao:
- A proposta do Gemini e metodologicamente correta como direcao, mas este primeiro passe nao melhorou o baseline.
- As features engenheiradas ficam como diagnostico experimental, nao canonico.
- Proximo passo metodologico deve focar estabilidade/seleção conservadora, nao adicionar mais features cegamente.

### 2026-04-16 - Plano de Engenharia de Features Locais

Motivacao:
- As features locais candidatas (SITADEL, Energia, REI) estao causando instabilidade devido ao uso de niveis absolutos e lags simples.
- Necessidade de focar em transformacoes invariantes a escala, dinamicas estruturais e prevencao estrita de data leakage.

O que foi feito:
- Criado o plano detalhado em `reports/archive/diagnostics/LOCAL_FEATURE_ENGINEERING_PLAN_v0.md`.
- Definidas as transformacoes metodologicamente validas: diferenca logaritmica (momentum), medias moveis, intensidade por estabelecimento, volatidade historica e proxy estrutural de mix de energia.
- Elaborada tabela compacta com as top 10 features a serem testadas para prevencao de vazamento temporal.
- Sugerido novo protocolo de validacao cruzada rolante com imputacao e padronizacao restritas por fold.

Decisao:
- Substituir variaveis brutas pelas formulacoes baseadas em razoes estruturais, momentum e suavizacao temporal (`log_diff`, `roll_mean`, etc.).
- Isolar explicitamente `sitadel_q1_nowcast` do loop de predicao `forecast`.
- Este plano foi implementado em primeiro passe em `2026-04-17` e nao superou o baseline temporal.
- O plano fica como registro de experimento concluido/diagnostico, nao como plano ativo.

### 2026-04-17 - Correcao de direcao atual antes de modelos grafo-temporais

Motivacao:
- Alguns registros anteriores no journal sugeriam que `STGNN` seria o proximo passo obrigatorio.
- Experimentos posteriores mostraram que o ganho de features locais ainda e marginal e instavel.
- Para evitar inferencia errada por agentes externos, a decisao atual precisa ficar explicita.

Decisao atual:
- Nao iniciar `STGNN` ainda.
- `STGNN` permanece como familia candidata futura, nao como objetivo imediato.
- O proximo passo pratico e testar modelos residuais: prever a correcao sobre persistencia.
- Baselines residuais devem usar validacao causal, escolha de `shrinkage` sem olhar o ano de teste e comparacao por ano/perfil de zona.
- Criterio minimo para retomar grafo/STGNN: residual ou baseline tabular precisa demonstrar ganho robusto e explicavel sobre `ridge_lag_only` e persistencia.

### 2026-04-17 - Primeiro baseline residual com shrinkage

Motivacao:
- A persistencia local e muito forte, entao prever o volume completo e menos eficiente do que prever a correcao sobre persistencia.
- O objetivo era testar residual absoluto/log e `lambda` de shrinkage sem mudar o tensor canonico.

O que foi feito:
- Criado `src/data/evaluate_residual_baselines_core_v0.py`.
- Testados `RidgeCV`, `HuberRegressor` e `ElasticNetCV`.
- Testados residual absoluto e residual log.
- Testados `lambda = 0.0, 0.1, 0.25, 0.5, 0.75, 1.0`.
- Gerados:
  - `reports/residual_baseline_metrics_core_v0.json`
  - `data/processed/residual_baseline_predictions_core_v0.csv`
  - `reports/archive/diagnostics/RESIDUAL_BASELINE_CORE_V0.md`

Resultado:
- Resultado inicialmente observado: `HuberRegressor`, residual absoluto, `local_all`, `lambda=0.5`, WMAPE medio `5.17%`.
- Este resultado foi depois superado pela ablation `REI only`.
- Selecao causal ingenua falhou: `12.21%` WMAPE.
- Selecao causal conservadora foi reavaliada apos ablations e ficou em `7.02%` WMAPE.

Decisao:
- Baseline residual passa a ser o caminho pratico mais promissor.
- Ainda e experimento, nao conclusao final.
- Proxima auditoria deve verificar erro por zona/perfil e se o ganho vem de `local_all` real ou de algum subconjunto especifico.

### 2026-04-17 - Diagnostico por zona do baseline residual

Motivacao:
- Verificar se o ganho residual e amplo ou concentrado em poucas zonas grandes.
- Avaliar se o novo baseline melhora apenas WMAPE global ou tambem grupos de volume/volatilidade.

O que foi feito:
- Criado `src/data/diagnose_residual_baseline_core_v0.py`.
- Gerados:
  - `data/processed/residual_baseline_zone_diagnostics_core_v0.csv`
  - `reports/archive/diagnostics/residual_baseline_diagnostics_core_v0.json`
  - `reports/archive/diagnostics/RESIDUAL_BASELINE_DIAGNOSTICS_CORE_V0.md`
- Grupos de volume e volatilidade foram definidos usando historico ate `2020`, sem olhar anos de teste.

Resultado inicial (`local_all`, antes da ablation):
- Modelo fixo residual melhora `2021` e `2024`, mas piora contra persistencia em `2022` e `2023`.
- O ganho por contagem e amplo: `269` zonas melhoram e `11` pioram.
- O ganho por magnitude e concentrado: Paris representa `29.0%` da reducao total de erro absoluto; top 10 zonas representam `46.4%`.
- O modelo melhora todos os grupos de volume e volatilidade no agregado.

Decisao:
- O residual e forte como benchmark experimental, mas ainda nao deve ser tratado como modelo final.
- Proximo passo executado depois: ablation de `local_all` para identificar se o ganho vem de SITADEL, REI, energia ou interacao entre fontes.

### 2026-04-17 - Regras de ativacao do residual

Motivacao:
- O residual fixo melhora anos de choque/aceleracao, mas piora contra persistencia em anos estaveis.
- Precisamos de uma regra forecast-safe para escolher entre modelo estavel e residual antes de observar o ano de teste.

O que foi feito:
- Criado `src/data/evaluate_residual_activation_rules_core_v0.py`.
- Testados gatilhos:
  - aceleracao nacional absoluta
  - `regime_signal_lag_1`
  - volatilidade local historica `3y`
  - crescimento local absoluto
- O lado estavel da regra usa `ridge_level_lag_only`.
- O lado residual usa `HuberRegressor`, residual absoluto, `local_all`, `lambda=0.5`.

Resultado inicial (`local_all`, antes da ablation):
- Melhor regra numerica: `national_acceleration_abs`, `min_prior_years=1`.
- WMAPE medio: `4.86%`.
- Pior ano: `6.51%`.
- Variante mais conservadora `min_prior_years=2`: WMAPE medio `6.03%`, mas com erro alto em `2022` por default para `ridge_level`.

Decisao:
- Gatilho de aceleracao nacional e a melhor familia atual para ativar residual.
- `min_prior_years=1` e forte, mas fragil por usar so um ano anterior para calibrar.
- `min_prior_years=2` e mais defensavel, mas ainda tem problema no ano inicial.
- Proximo passo executado depois: testar variantes de default inicial e ablation de `local_all` antes de promover qualquer regra operacional.

### 2026-04-17 - Ablation residual e reavaliacao das regras de ativacao

Motivacao:
- O resultado `local_all` podia estar escondendo qual fonte realmente explicava o ganho.
- Era necessario comparar `REI`, SITADEL e energia separadamente antes de promover qualquer baseline.

O que foi feito:
- `src/data/evaluate_residual_baselines_core_v0.py` passou a testar ablations:
  - `sitadel_only`
  - `energy_only`
  - `rei_only`
  - `sitadel_energy`
  - `sitadel_rei`
  - `rei_energy`
  - `local_all`
- `src/data/evaluate_residual_activation_rules_core_v0.py` passou a comparar residual sides:
  - `REI only`
  - `local_all`
  - `SITADEL+REI`
  - `REI+energy`
- Tambem foram comparados defaults estaveis `ridge_level_lag_only` e `persistence`.

Resultado:
- Melhor residual fixo: `HuberRegressor`, residual absoluto, `REI only`, `lambda=0.5`.
- WMAPE medio fixo: `5.02%`; pior ano: `6.33%`.
- `local_all` ficou abaixo: WMAPE medio `5.17%`.
- Melhor regra de ativacao: `ridge_level_lag_only` como lado estavel, `SITADEL+REI` como lado residual e gatilho `national_acceleration_abs`.
- WMAPE medio da regra: `4.83%`; pior ano: `6.51%`.

Decisao:
- `REI` e a principal fonte candidata para explicar a correcao residual.
- A regra de ativacao e numericamente forte, mas ainda fragil porque `min_prior_years=1` calibra threshold com pouco historico.
- Proximo passo metodologico: auditar temporalidade/vintage do `REI` e evitar qualquer afirmacao de resultado final.
- `STGNN` continua adiado.

### 2026-04-17 - Banimento temporario do REI nos residuais

Motivacao:
- Auditoria externa apontou dois problemas metodologicos no uso de `REI`:
  - risco de publication lag/vintage fiscal ao usar registros definitivos `t` para prever `t+1`
  - dupla contagem em 2024 quando `P31/P33/P34` agregados aparecem junto com subcomponentes `P31_*`, `P33_*`, `P34_*`

O que foi feito:
- Corrigido `src/data/build_rei_cfe_ze2020_v0.py` para preferir `P31`, `P33`, `P34` quando o agregado existe, evitando somar agregado + componentes.
- Removidos grupos `REI` do avaliador residual candidato:
  - `rei_only`
  - `sitadel_rei`
  - `rei_energy`
  - `engineered_rei`
- Reexecutados:
  - `src/data/evaluate_residual_baselines_core_v0.py`
  - `src/data/diagnose_residual_baseline_core_v0.py`
  - `src/data/evaluate_residual_activation_rules_core_v0.py`

Resultado sem `REI`:
- Melhor residual fixo: `RidgeCV`, residual log, `engineered_target`, `lambda=0.5`.
- WMAPE medio fixo: `6.62%`; pior ano: `9.28%`.
- Selecao causal conservadora piorou para `9.47%`.
- Melhor regra de ativacao sem `REI`: `national_acceleration_abs` com lado residual `SITADEL only`.
- WMAPE medio da regra: `5.49%`; pior ano: `6.51%`.

Decisao:
- O resultado forte com `REI` (`5.02%` fixo; `4.83%` ativado) fica invalidado temporariamente.
- O baseline residual sem `REI` ainda e util como diagnostico, mas nao deve ser promovido como operacional.
- `REI` permanece apenas como fonte candidata sob quarentena metodologica ate prova de disponibilidade temporal e correcao de vintage.
- `STGNN` continua adiado.

### 2026-04-17 - Teste de fallback nas regras de ativacao sem REI

Motivacao:
- Auditoria externa sugeriu trocar o fallback inicial de `ridge_level_lag_only` por `persistence` nas regras mais conservadoras (`min_prior_years=2`).
- A hipotese era reduzir o erro de `2022`, onde `persistence` e muito melhor que o ridge estavel.

O que foi feito:
- `src/data/evaluate_residual_activation_rules_core_v0.py` passou a testar dois modos de fallback:
  - `stable`: usa o modelo estavel configurado
  - `persistence`: usa persistencia quando nao ha historico suficiente para calibrar o gatilho
- Reexecutado `src/data/evaluate_residual_activation_rules_core_v0.py`.
- Atualizados:
  - `reports/archive/diagnostics/residual_activation_rules_metrics_core_v0.json`
  - `reports/archive/diagnostics/RESIDUAL_ACTIVATION_RULES_CORE_V0.md`

Resultado:
- Melhor regra numerica continua sendo `national_acceleration_abs`, `ridge_level_lag_only` como lado estavel, `SITADEL only` como lado residual, `min_prior_years=1`.
- WMAPE medio: `5.49%`; pior ano: `6.51%`.
- Fallback por `persistence` nao virou solucao robusta: melhora a intuicao para anos estaveis, mas falha fortemente em `2021`, onde persistencia tem WMAPE `14.32%`.

Decisao:
- O fallback por persistencia fica registrado como experimento testado e rejeitado como baseline operacional.
- A regra `5.49%` permanece diagnostica: mostra que SITADEL pode ajudar em anos de choque se houver gatilho seguro, mas ainda depende de `min_prior_years=1` e threshold fragil.
- Proximo passo deve focar em diagnostico/robustez do gatilho antes de qualquer arquitetura complexa.

### 2026-04-17 - Auditoria metodologica do gatilho no-REI

Motivacao:
- Auditoria externa revisou a regra no-REI de melhor WMAPE (`5.49%`) e apontou risco de overfit por threshold.
- O objetivo foi separar ganho preditivo real de simples escape de anos em que `ridge_level_lag_only` falha.

Conclusao metodologica:
- A regra `national_acceleration_abs`, `min_prior_years=1`, nao e robusta como seletor operacional.
- O threshold usado apos `2021` fica estaticamente ancorado em `0.11655188465700994`, sugerindo memorizacao do choque pos-COVID.
- O comportamento economico e problemático: ativa residual em `2022`/`2023`, anos em que persistencia era forte, e nao ativa em `2024`, ano de choque/desaceleracao.
- O ganho numerico vem em parte de evitar falhas do ridge estavel, nao necessariamente de capturar sinal estrutural robusto.

Decisao:
- Rebaixar formalmente a regra `5.49%` para diagnostico de stress-test.
- O relatorio de ativacao passa a exigir trace de threshold por ano.
- Nao promover regra de ativacao, residual no-REI ou STGNN enquanto nao houver diagnostico de robustez por ano, zona e volume.

### 2026-04-20 - Diagnostico LOYO e estratificacao da regra de ativacao

Motivacao:
- A regra de ativacao no-REI tinha bom WMAPE medio (`5.49%`), mas suspeita de threshold overfitado.
- Era necessario testar estabilidade temporal e verificar se o ganho era amplo por volume territorial.

O que foi feito:
- Criado `src/data/diagnose_activation_rules_core_v0.py`.
- O diagnostico audita apenas predicoes ja geradas, sem treinar modelo novo.
- Saidas:
  - `reports/archive/diagnostics/activation_rule_diagnostics_core_v0.json`
  - `reports/ACTIVATION_RULE_DIAGNOSTICS_CORE_V0.md`
- Medidas adicionadas:
  - trace de threshold por ano
  - LOYO threshold audit
  - WMAPE por estrato de volume
  - reducao absoluta de erro vs. persistencia e vs. ridge estavel
  - zonas melhoradas/pioradas
  - risco de concentracao top-1/top-10

Resultado:
- LOYO falhou no criterio de estabilidade: range de threshold `0.0917`, acima do limite metodologico `0.05`.
- Estratificacao por volume foi positiva no agregado:
  - `bottom_50pct`: WMAPE regra `5.64` vs persistencia `8.95`
  - `middle_40pct`: WMAPE regra `6.32` vs persistencia `8.52`
  - `top_10pct`: WMAPE regra `4.89` vs persistencia `6.93`
- A regra ainda piora contra persistencia em `2022` e `2023`.
- Risco de concentracao esta no limite: top-1 representa `29.43%` do ganho positivo vs. persistencia.

Decisao:
- A regra de ativacao permanece rebaixada a diagnostico de stress-test.
- Ela mostra que residual com SITADEL pode ser util em anos de ruptura, mas o gatilho atual nao e robusto.
- Baselines operacionais atuais:
  - `ridge_lag_only` como benchmark principal
  - `persistence` como baseline conservador
- Nao avancar para arquitetura complexa com base nesse gatilho.

### 2026-04-20 - Fechamento da fase de baselines

Motivacao:
- Encerrar a etapa de data mining, limpeza, auditoria de target e validacao de baselines antes da limpeza/arquivamento do projeto.
- Evitar que resultados exploratorios fortes sejam confundidos com baselines operacionais.

O que foi feito:
- Criado `reports/BASELINE_PHASE_CLOSURE_DECISION_V0.md`.
- Adicionado o relatorio como leitura obrigatoria em `reports/PROJECT_STATE_INDEX_V0.md`.

Decisao congelada:
- Target operacional: `SIDE` official establishment creations agregadas para `ZE2020`.
- Benchmark principal: `ridge_lag_only`.
- Baseline conservador: `persistence`.
- `REI`: quarentena metodologica.
- SITADEL e energia: sinais diagnosticos, nao promovidos.
- Residual fixo no-REI: exploratorio.
- Regra de ativacao no-REI: stress-test diagnostic.
- STGNN: proxima familia experimental, nao conclusao.

Proximo passo:
- Limpeza e arquivamento dos artefatos.
- Depois, iniciar experimentos de modelagem do micro para o macro: temporal sem grafo, grafo estatico, mobilidade, e apenas entao modelos grafo-temporais.
