# HERALD Semi Total geo2025 — Bateria 253 model-runs

## Origem

Bateria HPC executada em 2026-05-02, jobs SLURM: 7269589, 7270929, 7270930, 7270931, 7270932, 7270933.

Arquivo original: `hpc_semi_total_253_results.tar.gz`

## Estrutura

```
herald_semi_total_geo2025_7269589/     # V3, V6, STGNNs, baselines temporais
  reports/                             # herald_v3, herald_v6, herald_semi (seeds 0,1)
  stgnn_reports/                       # DCRNN, Dynamic STGNN, Graph WaveNet (10 seeds)
  stgnn_data_processed/                # CSVs de predição STGNN
  temporal_baselines/                  # LSTM (10 seeds), naive_lag1, ridge_ar, arima (1 seed)
  data_processed/                      # NPZs internos (V3/V6)
herald_semi_total_geo2025_7270929-7270933/   # HERALD Semi bateria principal
  reports/                             # herald_semi_total_metrics_v1.json (34 runs/job)
                                       # herald_semi_total_precovid_metrics_v1.json
  data_processed/                      # NPZs internos semi (170 runs)
reports/figures/                       # Dashboard HTML final
```

## Contagem de runs

| Categoria | Configs | Seeds | Total |
|---|---|---|---|
| HERALD Semi (17 configs) | 17 | 10 | 170 |
| HERALD V6 no-semi (h32 + h64) | 2 | 10 | 20 |
| HERALD V3 | 1 | 10 | 10 |
| HERALD Semi precovid | 1 | 10 | 10 |
| STGNNs (DCRNN + Dynamic + GWN) | 3 | 10 | 30 |
| LSTM local | 1 | 10 | 10 |
| naive_lag1 + ridge_ar + arima_local | 3 | 1 | 3 |
| **TOTAL** | | | **253** |

## Período avaliado

- **Período principal**: 2021–2025 (folds rolling-origin, treino até t-1)
- **Período pré-COVID**: 2016–2019 (somente config `total_h64_semi_mask0.10_precovid`)

## Seeds usadas

{0, 1, 7, 13, 17, 42, 77, 99, 123, 2025}

## Dataset

SIDE/INSEE — criações de estabelecimentos por zone d'emploi, geografia geo2025 (ZE 2020, nomenclatura 2026), 280 zones d'emploi de France métropolitaine.

## Modelos comparados

**Baselines locais**: naive_lag1, ridge_ar, arima_local, lstm_local  
**STGNNs literatura**: DCRNN residual, Graph WaveNet residual, Dynamic STGNN residual  
**HERALD família**: V3, V6 h32, V6 h64, Semi (17 configurações de mascaramento)

## Conclusão principal

**HERALD V6 h64 é o melhor modelo atual** (mean WMAPE = 0.03130 ± 0.00460).

A semi-supervisão por mascaramento **não melhorou** HERALD:
- Semi mask0.10 random: WMAPE = 0.03413 (pior que V6 h64)
- Comparação pareada por seed: wins 3/10, Wilcoxon p=0.105
- Mascaramento vs controle (mask0.0): mascaramento é PIOR (p=0.049)
- O ganho observado vem da capacidade h64, não do mascaramento

O grafo dinâmico tem **forte valor interpretativo** (adj_delta COVID 10-20× maior que pré-COVID) mas o ganho preditivo isolado exige ablação `fixed_adj` ainda não rodada nesta bateria.

## Resultado negativo útil

A semi-supervisão falhou como esperado na forma testada. O Semi cria 117 novas conexões estáveis entre zonas (vs V6 h64), mas essas conexões são 9× mais fracas que as conexões estabelecidas e não melhoram a previsão. Algumas conexões intra-regionais (Aude/Carcassonne) podem ter interesse interpretativo, mas requerem validação com dados de mobilidade externe.

## Observações metodológicas pendentes

1. Ablação `fixed_adj` não rodada — necessária para isolar ganho do grafo dinâmico
2. Validação precovid incompleta — só 1 config Semi; V6/V3 não comparados no mesmo protocolo
3. Logs de treinamento ausentes — convergência não verificável
4. STGNNs são "residuais" — protocolo de comparação deve ser explicitado no paper
5. spatial_block catastrófico (WMAPE +40% vs V6) — possível bug de implementação a verificar

## Dashboard

`reports/figures/herald_geo2025_final_dashboard.html`
