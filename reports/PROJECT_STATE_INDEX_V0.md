# Project State Index v0

Data: 2026-04-16

Objetivo:

- servir como porta de entrada do projeto
- reduzir confusao causada pela quantidade de artefatos
- indicar quais arquivos olhar primeiro em cada etapa

## Pergunta Do Projeto

Construir uma base territorial, temporal e auditavel para recomendacoes economicas em zonas de emprego francesas.

No estado atual, o projeto ainda nao esta na camada final de recomendacao.

O foco atual e consolidar um grafo territorial dinamico anual e validar se existe um backbone preditivo defensavel antes de avançar para modelos grafo-temporais e depois para decisao multiagente.

## Estado Atual Em Uma Linha

Temos target oficial `SIDE`, painel anual `ZE2020`, grafo geografico, grafo de mobilidade, tensores extended separados por `forecast`/`nowcast`/`diagnostic`, baselines causais e auditoria de candidatos locais; ainda nao temos arquitetura final nem camada decisional.

## Leitura Atual Obrigatoria

Arquivos de entrada para entender o estado atual:

- [BASELINE_PHASE_CLOSURE_DECISION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BASELINE_PHASE_CLOSURE_DECISION_V0.md)
- [PROJECT_CONSISTENCY_AUDIT_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_CONSISTENCY_AUDIT_V0.md)
- [EXTENDED_CORE_VERIFICATION_SUMMARY_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/EXTENDED_CORE_VERIFICATION_SUMMARY_V0.md)
- [LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md)
- [RAW_EXTERNAL_INVENTORY_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RAW_EXTERNAL_INVENTORY_V0.md)
- [canonical_artifacts_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/canonical_artifacts_v0.csv)

Resumo operacional:

- artefato canonico de target: `target_side_establishments_annual_core_v0.csv`
- benchmark atual a bater: `ridge_lag_only = 7.66%` WMAPE e `persistence = 7.68%`
- decisao atual: nao iniciar `STGNN` ainda; testar primeiro modelos residuais e correcao de persistencia com validacao causal
- tensor forecast-safe atual: `stgnn_tensor_package_extended_forecast_core_v1.npz`
- tensor nowcast atual: `stgnn_tensor_package_extended_nowcast_q1_core_v1.npz`
- tensor diagnostico atual: `stgnn_tensor_package_extended_diagnostic_core_v1.npz`
- candidatos locais: SITADEL mensal/anual, REI e Energia permanecem fora do tensor canonico
- correcao importante: `adjacency_mobility` dos tensores extended agora tem shape correto `280 x 280`
- resultado `REI` residual foi invalidado temporariamente por risco de vintage/publication lag e dupla contagem `P31/P33/P34` em 2024
- melhor novo experimento fixo sem `REI`: residual `RidgeCV` log com `engineered_target`, WMAPE medio `6.62%`
- melhor regra experimental de ativacao sem `REI`: aceleracao nacional absoluta + residual `SITADEL only`, WMAPE medio `5.49%` (`min_prior_years=1`), rebaixada para diagnostico de stress-test por threshold fragil calibrado em `2021`
- fallback por `persistence` foi testado nas regras de ativacao; nao resolve a robustez porque reduz o dano em `2022`, mas colapsa em `2021` com WMAPE `14.32%`
- diagnostico LOYO da regra de ativacao falhou no criterio de estabilidade: range de threshold `0.0917` contra limite metodologico `0.05`
- regra de ativacao melhora os 3 grupos de volume no agregado, mas piora contra persistencia em `2022` e `2023`; nao e baseline operacional
- referencias operacionais atuais: `ridge_lag_only` como benchmark principal e `persistence` como baseline conservador
- dumps linha-a-linha de predicao residual sao regeneraveis e ficam fora do Git; metricas, diagnosticos agregados e scripts ficam versionados

## O Que Esta Fechado

### 1. Organizacao Dos Dados Brutos

Status: fechado para a etapa atual.

Arquivos principais:

- [RAW_DOWNLOAD_ORGANIZATION_2026_04_12_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RAW_DOWNLOAD_ORGANIZATION_2026_04_12_V0.md)
- [raw_download_organization_2026_04_12_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/raw_download_organization_2026_04_12_v0.csv)
- [organize_raw_downloads_v0.py](/home/jpdark/Downloads/project_recomm/dataset/src/data/organize_raw_downloads_v0.py)

Leitura:

- `data/raw/` e fonte bruta local e nao entra nos commits principais
- os arquivos brutos foram organizados e duplicados byte-identicos foram removidos

### 2. Painel Territorial Anual

Status: fechado em `core_v0`; estendido em `extended_panel_core_v0` para os baselines causais atuais.

Arquivos principais:

- [zones_master_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/zones_master_annual_core_v0.csv)
- [panel_zones_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/panel_zones_core_v0.csv)
- [PANEL_ZONES_DESIGN.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PANEL_ZONES_DESIGN.md)
- [panel_zones_quality_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/panel_zones_quality_v0.json)

Leitura:

- unidade territorial principal: `ZE2020`
- periodo efetivo de features: `2019-2024`
- painel extended atual: `2018-2024`, `280` zonas, target oficial `SIDE`

### 3. Grafos Territoriais

Status: fechado para grafos observados iniciais.

Arquivos principais:

- [graph_nodes_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_nodes_ze2020_core_v0.csv)
- [graph_edges_ze2020_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_edges_ze2020_core_v0.csv)
- [graph_adjacency_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_adjacency_core_v0.csv)
- [mobility_adjacency_raw_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_raw_core_v0.csv)
- [mobility_adjacency_row_normalized_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/mobility_adjacency_row_normalized_core_v0.csv)
- [GRAPH_CORE_V0_INSPECTION.md](/home/jpdark/Downloads/project_recomm/dataset/reports/GRAPH_CORE_V0_INSPECTION.md)
- [MOBILITY_GRAPH_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/MOBILITY_GRAPH_CORE_V0.md)
- [MOBILITY_SPATIAL_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/MOBILITY_SPATIAL_BASELINE_CORE_V0.md)

Leitura:

- grafo geografico: adjacencia espacial entre zonas `ZE2020`
- grafo de mobilidade: fluxos domicilio-trabalho entre zonas `ZE2020`
- ambos estao disponiveis para experimentos futuros
- media simples dos vizinhos nao supera persistencia local em nenhum dos dois grafos
- ainda nao ha grafo adaptativo aprendido

### 4. Target Proxy

Status: fechado para experimentos iniciais, mas rebaixado para alvo auxiliar apos auditoria `SIDE`.

Arquivos principais:

- [target_proxy_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_proxy_annual_core_v0.csv)
- [graph_model_target_panel_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/graph_model_target_panel_core_v0.csv)
- [BASELINE_ANNUAL_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BASELINE_ANNUAL_TARGET_CORE_V0.md)
- [TARGET_PROXY_CANDIDATE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_PROXY_CANDIDATE_CORE_V0.md)

Leitura:

- target atual: proxy anual de criacao de estabelecimentos
- target nao e ground truth final de recomendacao economica
- auditoria `SIDE` mostrou alta correlacao com fonte oficial, mas inflacao sistematica de nivel
- candidato principal de target formal passa a ser `SIDE` estabelecimentos oficiais agregados por `ZE2020`
- proxy atual deve ficar como comparacao auxiliar/auditoria

Auditoria:

- [SIDE_COMMUNAL_CREATIONS_INSPECTION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_COMMUNAL_CREATIONS_INSPECTION_V0.md)
- [TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md)

### 5. Pacote Tensorial Grafo-Temporal

Status: pacote antigo mantido para rastreabilidade; pacote extended atual separado por forecast/nowcast/diagnostic.

Arquivos principais:

- [stgnn_tensor_package_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/stgnn_tensor_package_core_v0.npz)
- [stgnn_tensor_sample_index_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_sample_index_core_v0.csv)
- [stgnn_tensor_feature_registry_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_feature_registry_core_v0.csv)
- [target_side_establishments_annual_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/processed/target_side_establishments_annual_core_v0.csv)
- [stgnn_tensor_package_side_target_core_v0.npz](/home/jpdark/Downloads/project_recomm/dataset/data/processed/stgnn_tensor_package_side_target_core_v0.npz)
- [stgnn_tensor_sample_index_side_target_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_sample_index_side_target_core_v0.csv)
- [stgnn_tensor_feature_registry_side_target_core_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/stgnn_tensor_feature_registry_side_target_core_v0.csv)
- [STGNN_TENSOR_PACKAGE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_TENSOR_PACKAGE_CORE_V0.md)
- [STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md)
- [STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md)

Leitura:

- `X`: `[6, 280, 23]`
- `Y`: `[6, 280]`
- `A`: `[280, 280]`
- `Mask`: `[6, 280, 23]`
- `0` em `x_scaled_imputed` significa media do treino apos padronizacao
- `x_mask` e obrigatoria para diferenciar imputacao de observacao real
- a frequencia dinamica observada hoje e anual, porque as fontes oficiais principais nao oferecem granularidade mensal consistente
- pacote `SIDE`: `X=[5, 280, 23]`, `Y=[5, 280]`, targets `2020-2024`, sem `forecast_holdout`
- pacote `extended_forecast_core`: `X=[7, 280, 28]`, `Y=[7, 280]`, `A_geo=[280, 280]`, `A_mobility=[280, 280]`
- pacote `extended_nowcast_q1_core`: `X=[7, 280, 29]`, `Y=[7, 280]`, adiciona apenas sinal Q1 do ano corrente
- pacote `extended_diagnostic_core`: `X=[7, 280, 32]`, inclui sinais intra-ano posteriores apenas para auditoria

## O Que Esta Em Teste

### 6. Baselines

Status: em teste, agora reexecutado tambem com target oficial `SIDE`.

Arquivos principais:

- [BASELINE_ANNUAL_EVALUATION_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/BASELINE_ANNUAL_EVALUATION_V0.md)
- [baseline_annual_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/baseline_annual_metrics_core_v0.json)
- [SPATIAL_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SPATIAL_BASELINE_CORE_V0.md)
- [spatial_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/spatial_baseline_metrics_core_v0.json)
- [AUTOREGRESSIVE_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/AUTOREGRESSIVE_BASELINE_CORE_V0.md)
- [autoregressive_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/autoregressive_baseline_metrics_core_v0.json)
- [FEATURE_AUGMENTED_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_AUGMENTED_BASELINE_CORE_V0.md)
- [feature_augmented_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/feature_augmented_baseline_metrics_core_v0.json)
- [SIDE_TARGET_BASELINES_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_TARGET_BASELINES_CORE_V0.md)
- [side_target_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/side_target_baseline_metrics_core_v0.json)
- [FEATURE_AUGMENTED_BASELINE_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_AUGMENTED_BASELINE_SIDE_TARGET_CORE_V0.md)
- [feature_augmented_baseline_side_target_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/feature_augmented_baseline_side_target_metrics_core_v0.json)
- [FEATURE_TEMPORAL_AVAILABILITY_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FEATURE_TEMPORAL_AVAILABILITY_CORE_V0.md)
- [LONG_HISTORY_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/LONG_HISTORY_SIDE_TARGET_CORE_V0.md)
- [long_history_side_target_baseline_metrics_core_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/long_history_side_target_baseline_metrics_core_v0.json)
- [RICH_VS_LONG_SIDE_TARGET_COMPARISON_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RICH_VS_LONG_SIDE_TARGET_COMPARISON_CORE_V0.md)
- [CONTROLLED_HYBRID_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/CONTROLLED_HYBRID_SIDE_TARGET_CORE_V0.md)
- [ZONE_GROUP_ERROR_DIAGNOSTICS_SIDE_TARGET_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/ZONE_GROUP_ERROR_DIAGNOSTICS_SIDE_TARGET_CORE_V0.md)
- [SEGMENTED_SIDE_TARGET_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SEGMENTED_SIDE_TARGET_BASELINE_CORE_V0.md)
- [SIDE_MODEL_DECISION_MATRIX_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_MODEL_DECISION_MATRIX_CORE_V0.md)
- [SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md)
- [SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md)
- [TEMPORAL_REGIME_SIDE_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/TEMPORAL_REGIME_SIDE_BASELINE_CORE_V0.md)
- [RESIDUAL_BASELINE_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RESIDUAL_BASELINE_CORE_V0.md)
- [RESIDUAL_BASELINE_DIAGNOSTICS_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RESIDUAL_BASELINE_DIAGNOSTICS_CORE_V0.md)
- [RESIDUAL_ACTIVATION_RULES_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/RESIDUAL_ACTIVATION_RULES_CORE_V0.md)

Leitura:

- persistencia local e forte
- baseline espacial simples ficou muito pior que persistencia
- a validacao escolheu `alpha = 1.0`, ou seja, peso zero para media dos vizinhos
- baseline autoregressivo interno tambem nao superou persistencia na validacao
- media movel de 3 anos melhorou levemente no teste, mas perdeu na validacao
- baseline com features externas piorou fortemente fora do treino
- no alvo oficial `SIDE`, persistencia tem WMAPE `3.566` na validacao e `9.470` no teste
- no alvo oficial `SIDE`, o ridge autoregressivo melhora no teste, mas perde na validacao
- no alvo oficial `SIDE`, features externas continuam muito piores que persistencia
- pacote longo `SIDE` aumenta amostras anuais para `8`, com `train=5`, `validation=1`, `test=2`
- no pacote longo, persistencia ainda vence a validacao com WMAPE `3.369`
- comparacao rico vs longo confirma que o proximo passo deve ser um baseline hibrido controlado, nao arquitetura complexa
- baseline hibrido controlado tambem nao supera persistencia na validacao
- diagnostico por grupos mostra que grandes zonas urbanas concentram os maiores erros absolutos
- zonas pequenas tem WMAPE mais alto, mas impacto agregado menor
- baseline segmentado por tamanho+volatilidade melhora a persistencia no pacote longo: validacao WMAPE `3.259` vs. `3.369`; teste WMAPE `6.564` vs. `6.664`
- no teste do pacote longo, ridge autoregressivo ainda e melhor: WMAPE `6.406`
- matriz de decisao escolhe `segmented_by_size_volatility_group` como candidato da proxima etapa, com persistencia como referencia conservadora
- `rich_lags_only` tem melhor teste numerico, mas vem de janela curta diferente e nao decide o baseline principal
- backtest rolante corrige a leitura: segmentacao nao supera persistencia em media de teste rolante
- no backtest rolante, ridge autoregressivo tem melhor WMAPE medio de teste (`7.554`) contra persistencia (`7.680`), mas ainda e instavel por fold
- diagnostico de instabilidade mostra que ridge ajuda em anos de aceleracao agregada forte (`2021`, `2024`) e piora em anos estaveis ou levemente negativos (`2022`, `2023`)
- regra simples de regime usando crescimento agregado ja observado falhou: WMAPE medio de teste `9.143`, pior que ridge (`7.554`) e persistencia (`7.680`)
- oracle nao utilizavel mostra teto diagnostico WMAPE `4.302`, ou seja, escolher corretamente o regime teria valor, mas falta sinal antecipador
- leitura atual: a dinamica local e forte; features externas amplas e rasas ainda nao adicionam sinal robusto sobre `y(t+1)=y(t)`
- nenhuma regra simples e estavel o suficiente para justificar salto imediato para STGNN
- baseline extended atual: `ridge_lag_only` WMAPE medio `7.66%`; persistencia WMAPE medio `7.68%`
- grafo de mobilidade supera geografia marginalmente em modelo linear, mas nao supera `ridge_lag_only`
- SITADEL mensal melhora sobre SITADEL anual bruto, mas ainda nao supera o baseline temporal
- baseline residual sem `REI` tem melhor resultado fixo WMAPE medio `6.62%`, mas vem de engenharia do historico do proprio target, nao de fonte externa local
- selecao causal conservadora do baseline residual sem `REI` tem WMAPE medio `9.47%`; portanto nao e operacionalmente aceitavel
- diagnostico residual sem `REI`: ganho existe no agregado, mas Paris responde por `54.4%` da reducao total de erro absoluto
- regra experimental de ativacao sem `REI` com aceleracao nacional absoluta e residual `SITADEL only` chega a WMAPE medio `5.49%`, mas usa apenas um ano previo para calibrar threshold
- `residual_baseline_predictions_core_v0.csv` e `residual_activation_rules_predictions_core_v0.csv` sao grandes e regeneraveis; nao sao artefatos canonicos

### 6.1 Candidatos Locais Recentes

Status: testados, nao canonicos.

Arquivos principais:

- [LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md)
- [local_candidate_feature_metrics_v0.json](/home/jpdark/Downloads/project_recomm/dataset/reports/local_candidate_feature_metrics_v0.json)
- [sitadel_monthly_derived_annual_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/sitadel_monthly_derived_annual_ze2020_v0.csv)
- [energy_consumption_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/energy_consumption_ze2020_v0.csv)
- [rei_cfe_ze2020_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/data/interim/tables/rei_cfe_ze2020_v0.csv)

Leitura:

- SITADEL mensal `log1p` e promissor, mas nao canonico
- melhor variante SITADEL mensal: `ridge_sitadel_monthly_q1_nowcast_log = 7.89%`
- melhor variante forecast-safe mensal: `ridge_sitadel_monthly_lag_log = 7.93%`
- Energia e REI ainda nao trouxeram ganho nas formas testadas
- conclusao correta: candidatos locais ainda nao provaram ganho linear causal, nao que sejam irrelevantes

### 7. Inventario De Datasets Futuros

Status: registrado, nao integrado.

Arquivos principais:

- [FUTURE_DATASET_CANDIDATES_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FUTURE_DATASET_CANDIDATES_V0.md)
- [future_dataset_candidates_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/future_dataset_candidates_v0.csv)

Leitura:

- ha varias fontes locais uteis para fases futuras, mas nem todas pertencem ao `core_v0`
- `SIDE` comunal de criacoes e prioridade alta para validacao do target proxy
- `FLORES` historico, `RP` estendido e `Filosofi` estendido sao bons candidatos para melhorar features
- `DS_ICA` e `DS_COMPTES_REGIONAUX` ficam como contexto macro futuro, nao como dados locais diretos

## O Que Ainda Nao Esta Implementado

### 8. Modelos Grafo-Temporais

Status: nao implementado.

Decisao atual:

- nao escolher arquitetura ainda
- testar primeiro baselines fortes
- reconstruir os baselines com target oficial `SIDE` antes de qualquer arquitetura complexa
- grafos geografico e de mobilidade ja foram testados com vizinhos simples e nao superaram persistencia
- proximo uso de grafo deve ser mais seletivo: pesos economicos, atencao, ou grafo adaptativo
- `STGNN` permanece como familia candidata, nao como objetivo obrigatorio
- a decisao operacional atual e priorizar baselines residuais e `shrinkage` sobre persistencia antes de qualquer modelo grafo-temporal

### 9. Grafo Dinamico Mais Rico

Status: conceitual.

Estado atual:

- implementados grafo geografico estatico e grafo de mobilidade observado
- nenhum dos dois ainda e dinamico no tempo
- nenhum grafo adaptativo foi aprendido

Opcoes futuras:

- adicionar grafo adaptativo aprendido
- manter grafo espacial apenas como contexto/auditoria
- manter grafo de mobilidade como visao complementar, nao como media simples de vizinhos
- inferir dinamica intra-anual ou mensal apenas como produto futuro de modelo, nao como dado observado hoje

Fonte futura registrada:

- `DS_ICA` - Indicateur d'activité et de chiffre d'affaires
- URL: `https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_ICA`
- cobertura temporal informada: `1999-01` a `2026-01`
- periodicidade: mensal
- papel futuro: covariavel macro-setorial/conjuntural
- restricao: nao e territorial por `ZE2020`, entao nao deve ser integrada diretamente como feature territorial observada
- uso correto futuro: mapear choques setoriais mensais para zonas usando composicao economica local

Fonte futura registrada:

- `DS_COMPTES_REGIONAUX` - Comptes régionaux annuels
- URL: `https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_COMPTES_REGIONAUX`
- cobertura temporal informada: `1990` a `2024`
- periodicidade: anual
- papel futuro: contexto macro-regional anual
- conteudo: PIB regional, valor agregado por ramo, contas regionais dos domicilios
- restricao: dado regional, nao `ZE2020`
- uso correto futuro: anexar contexto macro da regiao a cada zona via pertencimento regional, sem interpretar como sinal local especifico da zona

### 10. Camada Multiagente / Decisional

Status: conceitual.

Estado atual:

- ainda nao implementada

Definicao operacional provisoria:

- agente nao precisa ser `LLM`
- agentes analiticos podem ser modulos especializados com entrada, saida e criterio proprio
- `LLM`, se usado, deve atuar como orquestrador/interface explicavel, nao como motor quantitativo principal

## Arquivos Que Devem Ser Lidos Primeiro

Para entender o projeto rapidamente, ler nesta ordem:

1. [README.md](/home/jpdark/Downloads/project_recomm/dataset/README.md)
2. [canonical_artifacts_v0.csv](/home/jpdark/Downloads/project_recomm/dataset/metadata/canonical_artifacts_v0.csv)
3. [PROJECT_STATE_INDEX_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_STATE_INDEX_V0.md)
4. [PROJECT_JOURNEY.md](/home/jpdark/Downloads/project_recomm/dataset/reports/PROJECT_JOURNEY.md)
5. [SIDE_MODEL_DECISION_MATRIX_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_MODEL_DECISION_MATRIX_CORE_V0.md)
6. [SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SEGMENTED_DECISION_RULE_BACKTEST_CORE_V0.md)
7. [SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/SIDE_BACKTEST_INSTABILITY_DIAGNOSTIC_CORE_V0.md)
8. [FUTURE_DATASET_CANDIDATES_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/FUTURE_DATASET_CANDIDATES_V0.md)
9. [EXTENDED_CORE_VERIFICATION_PLAN_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/EXTENDED_CORE_VERIFICATION_PLAN_V0.md)

## Proximo Passo

Implementar e auditar a proxima rodada de baselines residuais antes de qualquer modelo grafo-temporal.

Objetivo:

- manter persistencia local como baseline principal
- prever apenas a correcao de persistencia, nao o volume inteiro
- testar residual absoluto, residual log e correcao com `shrinkage` causal
- avaliar erro por perfil de zona e por ano, nao apenas media global
- usar grafos apenas depois que baselines residuais estiverem fechados

Artefatos esperados:

- avaliacao residual sobre `SIDE`: persistencia vs. residual Ridge/Huber/ElasticNet
- pesos de `shrinkage` escolhidos apenas por historico anterior
- criterio minimo para decidir se grafos ou `STGNN` merecem novo experimento

## Regra De Higiene

Antes de criar novos artefatos, verificar este indice.

Se um novo arquivo nao se encaixar em uma etapa clara, ele nao deve ser criado ainda.
