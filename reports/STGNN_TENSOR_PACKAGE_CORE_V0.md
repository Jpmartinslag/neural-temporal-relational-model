# STGNN Tensor Package Core v0

Data: 2026-04-12

Objetivo:

- criar uma camada tensorial auditavel antes da escolha da arquitetura `STGNN`
- preservar valores brutos, mascaras de observacao e normalizacao sem vazamento temporal

## Artefatos

- tensor: `data/processed/stgnn_tensor_package_core_v0.npz`
- indice de amostras: `metadata/stgnn_tensor_sample_index_core_v0.csv`
- registro de features: `metadata/stgnn_tensor_feature_registry_core_v0.csv`
- qualidade: `reports/stgnn_tensor_package_core_quality_v0.json`

## Estrutura

- nos: `280`
- features: `23`
- horizonte: `1` ano
- amostras anuais: `6`
- splits: `{'forecast_holdout': 1, 'test': 1, 'train': 3, 'validation': 1}`
- `x_raw`: `[6, 280, 23]`
- `x_scaled_imputed`: `[6, 280, 23]`
- `x_mask`: `[6, 280, 23]`
- `y_raw`: `[6, 280]`
- adjacencia: `[280, 280]`

## Decisoes

- a normalizacao usa apenas amostras de treino
- em `x_scaled_imputed`, `0` significa media do treino depois da padronizacao
- valores ausentes tambem sao imputados como `0` somente depois da normalizacao
- por isso, `x_mask` e obrigatoria para separar valor observado proximo da media de valor imputado
- a mascara `x_mask` preserva quais valores eram originalmente observados
- a adjacencia normalizada inclui self-loop para uso por modelos com passagem de mensagem
- `h = 1` e tratado como primeira configuracao de atribuicao temporal, nao como prova causal

## Limite

- missingness bruto das features nas amostras: `0.493`
- features sem observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`
- o split de treino ainda possui poucas amostras anuais
- qualquer `STGNN` treinado nesta versao deve ser tratado como experimento exploratorio

## Proxima etapa

- construir baselines fortes usando este pacote tensorial
- comparar persistencia, autoregressivo tabular e baseline espacial por media de vizinhos antes de treinar um `STGNN`

Baseline espacial minimo:

- `y_hat_i(t+1) = sum_j A_norm[i,j] * y_j(t)`
- variante robusta: `alpha * y_i(t) + (1 - alpha) * sum_j A_norm[i,j] * y_j(t)`
- esse baseline testa se a vizinhanca tem sinal antes de aprender pesos neurais no grafo
