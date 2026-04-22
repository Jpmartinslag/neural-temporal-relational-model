# Future Dataset Candidates v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- registrar datasets locais e fontes externas ja identificadas que podem ser uteis depois
- evitar integrar datasets fora de hora
- separar candidatos por papel metodologico, granularidade e risco

Arquivo estruturado:

- [future_dataset_candidates_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/future_dataset_candidates_v0.csv)

## Regra Geral

Nem todo dataset baixado deve entrar no painel agora.

Para entrar no `core_v0`, a fonte precisa respeitar pelo menos uma destas funcoes:

- feature anual por `ZE2020` ou agregavel com seguranca para `ZE2020`
- target ou validacao de target
- contexto politico ou ambiental com interpretacao clara
- contexto macro superior, desde que marcado como nao local

Se a fonte nao e territorial por `ZE2020`, ela deve ser tratada como contexto, nao como sinal local direto.

## Candidatos Locais Mais Importantes

### 1. SIRENE Historico E Geolocalizacao

Status: local disponivel.

Arquivos:

- `StockEtablissementHistorique_utf8.zip`
- `StockEtablissement_utf8.parquet`
- `StockUniteLegale_utf8.parquet`
- `GeolocalisationEtablissement_Sirene_pour_etudes_statistiques_utf8.parquet`

Uso futuro:

- auditar e melhorar o target proxy
- derivar dinamicas de estabelecimentos
- enriquecer estrutura empresarial local

Risco:

- arquivos grandes
- historico de endereco pode nao refletir exatamente a localizacao no momento da criacao

Prioridade: alta.

### 2. SIDE Criacoes Comunais 2024

Status: local disponivel.

Arquivos:

- `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip`
- `DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip`
- `TAB_SIDE_CREA_ENT_COM_2024_XLSX.zip`
- `TAB_SIDE_CREA_ETAB_COM_2024_XLSX.zip`

Uso futuro:

- validar ou substituir parte do target proxy
- criar features de criacao empresarial em nivel local

Risco:

- pode vazar target se usado como feature para prever o mesmo fenomeno
- precisa confirmar anos, geografia e medidas antes de integrar

Prioridade: muito alta, mas exige cuidado.

### 3. SIDE Agregado DEP/REG/NAT Por Forma Legal

Status: local disponivel.

Arquivo principal:

- `DS_SIDE_CREA_ENT_DEP_REG_NAT_CJ_2024_CSV_FR.zip`

Conteudo observado:

- `GEO`
- `GEO_OBJECT`
- `SIDE_MEASURE`
- `LEGAL_FORM`
- `FREQ`
- `TIME_PERIOD`
- `OBS_VALUE`

Uso futuro:

- contexto departamental/regional/nacional por forma legal
- explicar mudancas agregadas de estrutura juridica das criacoes

Risco:

- nao e `ZE2020`
- nao deve ser usado como variavel local direta

Prioridade: media.

### 4. FLORES Historico 2017-2023

Status: local disponivel.

Arquivos:

- `TD_FLORES2017_*`
- `TD_FLORES2018_*`
- `TD_FLORES2019_*`
- `TD_FLORES2020_*`
- `TD_FLORES2021_*`
- `DS_FLORES_2022_CSV_FR.zip`
- `DS_FLORES_2023_CSV_FR.zip`

Uso futuro:

- aumentar profundidade anual de emprego e estabelecimentos
- criar features por setor e esfera economica

Risco:

- formatos historicos diferentes
- harmonizacao geografica precisa ser checada

Prioridade: alta depois dos baselines atuais.

### 5. RP Estendido

Status: local disponivel.

Arquivos:

- `DS_RP_ACTIVITE_PRINC_2022_CSV_FR.zip`
- `DS_RP_EDUCATION_2022_CSV_FR.zip`
- `DS_RP_LOGEMENT_*_2022`
- `DS_RP_FAMILLE_*_2022`
- `DS_RP_MENAGES_*_2022`
- `DS_RP_MIGRES_PRINC_2022_CSV_FR.zip`
- `DS_RP_NAVETTES_PRINC_2022_CSV_FR.zip`
- bases `RP 2021` em `data/raw/temporal_depth/rp/`

Uso futuro:

- educacao
- habitacao
- familias e domicilios
- migracao
- mobilidade casa-trabalho
- profundidade 2021 para algumas camadas

Risco:

- muitas variaveis
- risco de inflar features sem ganho preditivo

Prioridade: alta, mas seletiva.

### 6. Filosofi Estendido

Status: local disponivel.

Arquivos:

- `DS_FILOSOFI_AGE_TP_NIVVIE_2021_CSV_FR.zip`
- `DS_FILOSOFI_LOG_TP_NIVVIE_2021_CSV_FR.zip`
- `DS_FILOSOFI_MEN_TP_NIVVIE_2021_CSV_FR.zip`
- `indic-struct-distrib-revenu-2020-*`

Uso futuro:

- pobreza e renda por idade, moradia e domicilios
- vulnerabilidade socioeconomica
- possivel camada de equidade para agentes futuros

Risco:

- supressao estatistica
- missingness territorial

Prioridade: alta.

### 7. BPE Harmonizado E Especializado

Status: local disponivel.

Arquivos:

- `ds_bpe_evolution_com_2019_2024_geo_2025.zip`
- `DS_BPE_EDUCATION_2024_CSV_FR.zip`
- `DS_BPE_SPORT_CULTURE_2024_CSV_FR.zip`
- `DS_BPE_2024_CSV_FR.zip`
- `BPE24.zip`

Uso futuro:

- servicos, equipamentos, educacao, esporte e cultura
- reforco de acessibilidade e amenidades
- aguardar a tabela INSEE prometida de contagem/presenca `2015-2025`

Risco:

- comparabilidade entre milessimos BPE
- camada 2019-2024 ja e mais defensavel que vintages brutos antigos

Prioridade: alta para a versao oficial `2015-2025`, media para especializadas 2024.

### 8. Politicas Publicas E Ambiente

Status: local disponivel.

Familias:

- `ZRR`
- `FRR`
- `QPV`
- `ZAN`
- `OCS GE Artificialisation`
- `PNB Action 7`

Uso futuro:

- restricoes e elegibilidade
- contexto de politica publica
- camadas de decisao/agentes
- variaveis ambientais e de uso do solo

Risco:

- algumas camadas sao geoespaciais grandes
- validade temporal e definicao legal precisam ser preservadas
- nao devem virar target economico por acidente

Prioridade: alta para camada decisional, media para backbone preditivo atual.

### 9. Salarios Privados BTS

Status: local disponivel.

Arquivos:

- `DS_BTS_SAL_EQTP_SEX_AGE_2023_CSV_FR.zip`
- `DS_BTS_SAL_EQTP_SEX_PCS_2023_CSV_FR.zip`

Uso futuro:

- qualidade do emprego
- estrutura salarial
- contexto economico local

Risco:

- um ano principal
- escopo privado

Prioridade: media.

### 10. Populacao Historica Longa

Status: local disponivel.

Arquivos:

- `base-pop-historiques-1876-2023.xlsx`
- `DS_POPULATIONS_HISTORIQUES_CSV_FR.zip`
- `DS_POPULATIONS_REFERENCE_2023_CSV_FR.zip`

Uso futuro:

- tendencias demograficas longas
- features estaticas de trajetoria

Risco:

- mudancas de COG
- harmonizacao historica

Prioridade: media-alta.

## Fontes Futuras Registradas, Mas Ainda Nao Baixadas

### DS_ICA

Fonte:

- <https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ICA>

Uso futuro:

- indices mensais de atividade e chiffre d'affaires
- contexto macro-setorial intra-anual

Restricao:

- nao e territorial por `ZE2020`
- precisa ser combinado com composicao setorial local para virar proxy territorial

Status: registrar, nao integrar agora.

### DS_COMPTES_REGIONAUX

Fonte:

- <https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_COMPTES_REGIONAUX>

Uso futuro:

- PIB regional
- valor agregado por ramo
- renda e contas regionais dos domicilios

Restricao:

- regional, nao `ZE2020`
- deve ser contexto macro, nao sinal local direto

Status: registrar, nao integrar agora.

## Prioridade Recomendada

Proxima ordem razoavel, depois dos baselines atuais:

1. inspecionar `SIDE` comunal de criacoes para validar target proxy
2. testar baseline com features externas locais ja integradas
3. expandir `FLORES` historico para melhorar profundidade anual
4. integrar `RP` e `Filosofi` estendidos de forma seletiva
5. deixar `DS_ICA` e `DS_COMPTES_REGIONAUX` para fase macro-contextual

## Regra De Uso

Antes de integrar qualquer candidato:

- confirmar granularidade
- confirmar anos reais no conteudo
- confirmar se e feature, target, contexto ou restricao
- checar risco de vazamento temporal
- registrar a decisao neste arquivo ou no indice do projeto
