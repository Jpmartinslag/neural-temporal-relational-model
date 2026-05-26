# HERALD Repository Cleanup — 2026-05-26

## Objetivo

Reduzir ruído local e deixar o repositório pronto para a próxima tese: um módulo de estado econômico
que ajude HERALD em movimentos raros sem usar flags manuais.

## Manter

- `src/modeles/`: código de treino HERALD.
- `hpc/regime/`: scripts de submissão, planos e auditorias.
- `reports/README.md`: entrada principal para relatórios.
- `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md`: auditoria confirmatória atual.
- `reports/metrics/herald_phase2r_*.csv`: síntese leve da Phase 2R.
- `reports/dashboards/herald_france_dashboard.html`: dashboard atualizado com Phase 2R.
- `hpc_results/README.md`: índice de resultados, sem depender de arquivos pesados.

## Remover

Remover do disco local, sem versionar:

- `hpc_results/herald_regime_*`: árvores de execução HPC com CSVs por seed, `.npz`, logs e relatórios
  regeneráveis.
- `hpc_results/herald_phase2*_smoke_*`: smoke tests.
- `hpc_results/herald_forecast_*`, `herald_leak_stress_*`, `herald_strict_exante_*`: resultados
  brutos antigos, desde que a síntese já esteja em `reports/`.
- logs `.out` / `.err` de jobs parciais.

## Mover/arquivar

Não mover para outro subdiretório dentro do repo se o objetivo é limpeza. Se for necessário guardar
evidência bruta, manter no HPC ou em storage externo. O git deve ficar com sínteses leves e scripts
para regenerar.

## Risco

- Não apagar `data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv`.
- Não apagar painéis processados que alimentam o treino principal.
- Não remover `hpc_results/final_model_comparison_20260429/` e `hpc_results/herald_semi_total_253_geo2025/`
  sem verificar porque partes leves ainda estão versionadas.
- Não usar `git clean -fdx`: isso apagaria dados locais úteis e arquivos ignorados de forma ampla.

## Comandos sugeridos

Depois de confirmar que as sínteses Phase 2R estão em `reports/`, a limpeza local pode remover apenas
as pastas HPC ignoradas e regeneráveis:

```bash
rm -rf hpc_results/herald_regime_*
rm -rf hpc_results/herald_phase2*_smoke_*
rm -rf hpc_results/herald_forecast_*
rm -rf hpc_results/herald_leak_stress_*
rm -rf hpc_results/herald_strict_exante_*
rm -rf hpc_results/project_recomm_herald_v7_*
rm -f hpc_results/final_model_comparison_20260429_partial_failed_7248278/*.out
rm -f hpc_results/final_model_comparison_20260429_partial_failed_7248278/*.err
```

## Estado após esta limpeza lógica

O repositório deve contar a história por camadas:

1. Phase 2R confirma `HERALD no flags calibré`.
2. Hard-concrete/auto-dimension não é tese principal.
3. O próximo avanço deve mirar movimentos raros com um estado econômico causal e contínuo.
4. Dashboards e READMEs apontam para sínteses leves, não para diretórios de execução HPC.
