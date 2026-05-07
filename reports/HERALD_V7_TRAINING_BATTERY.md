# HERALD V7 - bateria de treino geo2025

Data: 2026-05-03  
Status: launcher operacional criado; `src/modeles/train_herald_v7.py` implementado e validado por smoke test local.

## Objetivo

Preparar a proxima bateria para testar a hipotese V7:

- bater Ridge AR em 2025;
- ser mais estavel que HERALD V6 h64;
- preservar conexoes territoriais reais;
- melhorar A10 contra baselines setoriais fortes;
- testar semi-supervisao economica sem repetir apenas mascaramento bruto.

## Arquivos criados

- `hpc/run_herald_v7_research_battery.sh`
- `hpc/run_herald_v7_research_battery.sbatch`

## Secoes disponiveis

| Secao | Executavel agora? | Conteudo |
|---|---:|---|
| `smoke` | sim | baseline curto + V6 h64 + Semi control |
| `baselines` | sim | naive, Ridge, ARIMA, LSTM, DCRNN, Graph WaveNet, Dynamic STGNN |
| `controls` | sim | V6 h64 full, self_only, fixed_geo_mob, no_regime, static_adaptive, no_sector, precovid |
| `semi_probe` | sim | controles semi pequenos, incluindo A10 target |
| `semi_v2` | sim | masked economic variables, A10 denoise, ranking, temporal regime |
| `v7` | sim | variantes V7 |
| `all` | sim | baselines + controls + semi_probe + semi_v2 + v7 |

## Variantes V7 esperadas

O launcher espera que `src/modeles/train_herald_v7.py` aceite:

```text
--variant
--seed
--run-tag
--panel-path
--splits-path
--side-a10-path
--prediction-output-dir
--metrics-path
--model-card-path
```

Variantes planejadas:

| Variante | Objetivo |
|---|---|
| `ridge_graph_gate` | mistura adaptativa Ridge/grafo |
| `graph_only` | controle sem componente local |
| `fixed_graph` | isola valor do grafo dinamico |
| `fixed_alpha_0.5` | mistura nao aprendida |
| `no_regime_gate` | testa regime no gate local/grafo |
| `sector_enhanced` | A10 forte |
| `full` | V7 completo |

## Modos Semi V2

| Modo | Hipotese |
|---|---|
| `masked_variables` | mascarar variaveis economicas, nao zonas inteiras |
| `sector_denoise` | reconstruir A10 com prior setorial parcialmente oculto |
| `ranking_aux` | melhorar ranking territorial de crescimento |
| `temporal_regime` | estabilizar alpha/grafo em anos normais |
| `full` | combina masked variables, A10 denoise, ranking e regime |

## Comando smoke

```bash
cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430
bash hpc/run_herald_v7_research_battery.sh smoke
```

## Comando HPC para controles executaveis agora

Use se quiser rodar os controles antes da implementacao V7:

```bash
cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430
SECTION=controls REQUIRE_V7=0 sbatch hpc/run_herald_v7_research_battery.sbatch
```

## Comando HPC para bateria V7 completa

Usa o V7 implementado:

```bash
cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430
SECTION=all REQUIRE_V7=1 sbatch hpc/run_herald_v7_research_battery.sbatch
```

## Monitoramento

```bash
squeue -u $USER
tail -f logs/herald-v7-g25-<JOBID>.out
tail -f logs/herald-v7-g25-<JOBID>.err
```

## Saidas

```text
hpc_results/herald_v7_research_geo2025_<JOBID>/
  reports/
  data_processed/
  temporal_baselines/
  stgnn_reports/
  stgnn_data_processed/
```

Arquivos principais:

```text
reports/herald_v7_controls_metrics_v1.json
reports/herald_v7_semi_probe_metrics_v1.json
reports/herald_v7_metrics_v1.json
```

## Criterio de sucesso do V7

V7 so deve substituir V6 se:

- vencer Ridge AR em 2025;
- vencer V6 h64 na media 2021-2025;
- reduzir ou igualar o desvio padrao entre seeds;
- vencer ou explicar `fixed_graph`;
- melhorar A10 contra `lag1_by_zone` e `hist_mean_by_zone`;
- mostrar gate local/grafo coerente: mais local em anos estaveis, mais grafo em choque.
