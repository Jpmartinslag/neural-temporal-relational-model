# Mobility Spatial Baseline Core v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-13

Objetivo:

- testar se o grafo de mobilidade agrega sinal preditivo sobre persistencia
- comparar diretamente com o grafo geografico
- usar target oficial SIDE estabelecimentos

## Configuracao

- pacote tensorial: `stgnn_tensor_package_side_target_core_v0.npz`
- grafo geografico: adjacencia por fronteira ZE2020 (existente)
- grafo de mobilidade: fluxos domicilio-trabalho RP 2021, agregados por ZE2020
- alpha selecionado na validacao por minimo WMAPE

## Alphas Selecionados

- grafo geografico: `alpha = 1.00` (val WMAPE = `3.566`)
- grafo de mobilidade: `alpha = 1.00` (val WMAPE = `3.566`)

## Metricas por Modelo

| modelo | split | WMAPE | MAE |
|---|---|---|---|
| `persistence` | train | `7.364` | `278.3` |
| `persistence` | validation | `3.566` | `140.6` |
| `persistence` | test | `9.470` | `412.3` |
| `geo_neighbor_average` | train | `86.575` | `3271.6` |
| `geo_neighbor_average` | validation | `89.559` | `3530.9` |
| `geo_neighbor_average` | test | `83.633` | `3641.3` |
| `geo_blend` | train | `7.364` | `278.3` |
| `geo_blend` | validation | `3.566` | `140.6` |
| `geo_blend` | test | `9.470` | `412.3` |
| `mobility_neighbor_average` | train | `242.565` | `9166.4` |
| `mobility_neighbor_average` | validation | `255.938` | `10090.4` |
| `mobility_neighbor_average` | test | `230.530` | `10037.0` |
| `mobility_blend` | train | `7.364` | `278.3` |
| `mobility_blend` | validation | `3.566` | `140.6` |
| `mobility_blend` | test | `9.470` | `412.3` |

## Leitura

- persistencia (validacao): WMAPE = `3.566`
- blend geografico (validacao): WMAPE = `3.566` (alpha = `1.00`)
- blend mobilidade (validacao): WMAPE = `3.566` (alpha = `1.00`)

**Conclusao: grafo de mobilidade escolheu alpha = 1.0 — ignorar vizinhos e otimo — nenhum grafo simples agrega sinal sobre persistencia**

## Decisao

- o grafo de mobilidade, como o geografico, nao agrega sinal sobre persistencia local
- alpha = 1.0 significa que o otimo e ignorar os vizinhos de mobilidade
- a conclusao se torna mais forte: nem vizinhanca geografica nem fluxo de trabalhadores
  adiciona sinal preditivo sobre o target SIDE com as features e temporal depth atuais
- isso nao invalida o uso do grafo no STGNN, mas exige que o STGNN seja avaliado
  contra persistencia com rigor antes de qualquer interpretacao
- proximo passo: extensao temporal das features (FLORES historico, SIDE stocks 2019-2020)
  para aumentar o numero efetivo de amostras de treino