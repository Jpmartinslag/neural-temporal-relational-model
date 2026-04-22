# STGNN Tensor Package SIDE Target Core v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- reconstruir o pacote tensorial usando target oficial `SIDE` estabelecimentos
- manter a mesma camada de features e grafo do `core_v0` para comparacao metodologica

## Artefatos

- tensor: `data/processed/stgnn_tensor_package_side_target_core_v0.npz`
- indice de amostras: `metadata/stgnn_tensor_sample_index_side_target_core_v0.csv`
- registro de features: `metadata/stgnn_tensor_feature_registry_side_target_core_v0.csv`
- qualidade: `reports/stgnn_tensor_package_side_target_core_quality_v0.json`

## Estrutura

- target: `side_establishment_creations_official`
- nos: `280`
- features: `25`
- horizonte: `1` ano
- amostras anuais: `5`
- splits: `{'test': 1, 'train': 3, 'validation': 1}`
- anos de feature alinhados: `[2019, 2020, 2021, 2022, 2023]`
- anos de target alinhados: `[2020, 2021, 2022, 2023, 2024]`
- `x_raw`: `[5, 280, 25]`
- `y_raw`: `[5, 280]`

## Decisoes

- a normalizacao continua ajustada apenas no treino
- `0` em `x_scaled_imputed` continua significando media do treino depois da padronizacao
- `x_mask` continua obrigatoria para distinguir dado observado de imputacao
- este pacote nao escolhe arquitetura; ele apenas troca o alvo para a fonte oficial `SIDE`

## Limites

- missingness bruto das features nas amostras: `0.432`
- features sem observacao no treino: `['flores_presential_unit_loc_total', 'flores_productive_unit_loc_total']`
- os baselines devem ser reexecutados antes de qualquer modelo complexo
