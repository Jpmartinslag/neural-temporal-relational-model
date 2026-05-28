# HERALD Phase 3D — q_tensor Ablation Plan

**Data:** 2026-05-27  
**Status:** ✅ Smoke local OK — aguardando revisão antes do lançamento HPC

---

## Contexto e motivação

A bateria Phase 3C isolation (`no_urssaf`) mostrou que remover o q_tensor URSSAF trimestral
degrada substancialmente o desempenho:

| Config | Mean WMAPE | 2021 WMAPE | 2025 WMAPE |
|--------|-----------|-----------|-----------|
| C0 baseline (com q_tensor) | 0.02100 | 0.03628 | 0.01256 |
| C0_no_urssaf (sem q_tensor) | 0.02931 | 0.05445 | 0.01553 |
| **Degradação** | **+0.00831** | **+0.01817** | **+0.00297** |

O q_tensor (`effectifs_salaries_cvs` + `masse_salariale_cvs`, trimestral por ZE) é claramente
crítico. A hipótese agora é entender **por quê**:
- Carrega informação temporal (estado macroeconômico nacional por trimestre)?
- Carrega informação espacial (especificidade local por ZE)?
- Qual canal é mais informativo (emprego físico vs intensidade salarial)?
- A informação recente (contemporânea) é necessária ou basta um lag?

## Arquitetura dos configs

Todos os configs usam a arquitetura forte atual:
- `no_regime` + `learned_regime_gate_sector_enhanced`
- `no_source_flags`
- `feature_policy=side5_lag1_growth1y` (SIDE limpo, sem FLORES)
- `latent_regime_dim=5`
- `residual_shrinkage_mode=train_opt`
- `labor_tutor_feature_set=none` (sem tutor anual)

O parâmetro novo `quarterly_tensor_policy` (col 41 no schema de configs) controla a
transformação do q_tensor antes de entrar no modelo. A política `real` é o comportamento
original sem modificação.

## Configs

| Config | quarterly_tensor_policy | Descrição |
|--------|------------------------|-----------|
| Q0_real | `real` | Baseline — q_tensor real, sem transformação |
| Q1_zero | `zero` | q_tensor zerado — mede contribuição total |
| Q3_spatial_perm | `spatial_perm` | Permuta ZEs (N axis) — destrói identidade local |
| Q4_effectifs_only | `effectifs_only` | Só `effectifs_salaries_cvs` (zera `masse_salariale`) |
| Q5_masse_only | `masse_only` | Só `masse_salariale_cvs` (zera `effectifs`) |
| Q6_lag1 | `lag1` | q_tensor defasado 1 ano — testa necessidade da info recente |

**Total: 6 configs × 10 seeds = 60 runs.**

> **Q2 (temporal_perm) excluído:** A permutação global do eixo T em `build_quarterly_tensor`
> não é fold-safe — pode introduzir anos futuros em folds de treino anteriores. Uma
> falsificação temporal causal requer permutar apenas `years <= train_max` por fold, dentro
> de `make_sequences`. Não implementado no contrato atual. Se necessário futuramente, deve
> ser implementado como `patched_make_sequences`, não como transform do tensor bruto.

## Implementação técnica

### `apply_quarterly_tensor_policy` (train_herald_regime_experiment.py)

```python
def apply_quarterly_tensor_policy(q, policy, rng_seed):
    # q: [T, Q=3, N=280, C=2] float32
    # temporal_perm: shuffles T axis (years), seed-reproducible
    # spatial_perm:  shuffles N axis (zones), single global permutation
    # effectifs_only: zeros channel 1 (masse_salariale_cvs)
    # masse_only:    zeros channel 0 (effectifs_salaries_cvs)
    # lag1:          shifts T by 1 year forward (q[t] = original[t-1])
```

- Permutação `temporal_perm` usa `np.random.RandomState(seed).permutation(T)`
- Permutação `spatial_perm` usa uma única permutação global de N zonas
- Ambas são deterministicamente seeded pelo `--seed` do run
- `patched_build_quarterly_tensor` aplica a política após o build, antes de qualquer
  normalização (a normalização `normalize_quarterly` opera sobre o tensor já transformado)

### Metadados por run

Os seguintes campos são gravados no per-run JSON (via `train_herald_semi_v2.py`):
- `quarterly_tensor_policy`: policy aplicada (`real`, `zero`, etc.)

E no metadata JSON (via `train_herald_regime_experiment.py`):
- `quarterly_tensor_policy`
- `quarterly_tensor_zeroed`
- `q_tensor_channels_active`
- `q_tensor_transform_seed`

## Critérios de vitória e interpretação

| Resultado | Interpretação |
|-----------|---------------|
| Q0 bate Q1_zero (p<0.05) | q_tensor tem contribuição real mensurável |
| Q0 bate Q2_temporal_perm (p<0.05) | informação temporal (ordem dos anos) é usada |
| Q0 bate Q3_spatial_perm (p<0.05) | informação espacial (ZE-específica) é usada |
| Q0 bate temporal mas não spatial | q_tensor carrega estado nacional, não local |
| Q0 bate spatial mas não temporal | ZE-identidade importa, ordem dos anos menos |
| Q0 bate ambos | evidência causal local + temporal — resultado forte |
| Q4 ≈ Q0 > Q5 | effectifs domina (emprego físico mais informativo) |
| Q5 ≈ Q0 > Q4 | masse_salariale domina (intensidade salarial mais informativa) |
| Q4 ≈ Q5 << Q0 | ambos canais necessários — combinação é o que importa |
| Q6_lag1 ≈ Q0 | q_tensor recente não é necessário — lag suficiente |
| Q6_lag1 << Q0 | modelo usa informação contemporânea — recency matters |

## Arquivos entregues

| Arquivo | Descrição |
|---------|-----------|
| `src/modeles/train_herald_regime_experiment.py` | `apply_quarterly_tensor_policy()`, `--quarterly-tensor-policy` arg, re-inject em remaining |
| `src/modeles/train_herald_semi_v2.py` | `--quarterly-tensor-policy` arg, campo no per-run JSON |
| `hpc/regime/run_herald_regime_seed.sh` | col 41 support, pass `--quarterly-tensor-policy`, echo diagnostic |
| `hpc/regime/regime_plan_configs.sh` | `phase3d_qtensor` plan (7 configs × 41 cols) |
| `hpc/regime/smoke_test_phase3d_qtensor.sh` | smoke local (1 epoch, 7 JSONs, validação policy) |
| `hpc/regime/submit_herald_phase3d_qtensor.sh` | submit HPC (70 runs, preflight completo) |
| `hpc/regime/audit_herald_phase3d_qtensor_results.py` | audit com Wilcoxon paired, guard rail 2025, tabela per-year |

## Smoke local

```
Phase 3D q_tensor smoke OK
artifacts: hpc_results/herald_phase3d_qtensor_smoke_20260527_150729
configs tested: Q0-Q6
Artifact count: 7/7
Policy validation: OK
```

## Próximos passos (após revisão)

1. Rsync para HPC:
```bash
rsync -av src/modeles/train_herald_regime_experiment.py \
          src/modeles/train_herald_semi_v2.py \
          hpc/regime/regime_plan_configs.sh \
          hpc/regime/run_herald_regime_seed.sh \
          hpc/regime/smoke_test_phase3d_qtensor.sh \
          hpc/regime/submit_herald_phase3d_qtensor.sh \
          hpc/regime/audit_herald_phase3d_qtensor_results.py \
  meso:~/project_recomm_herald_v6_2025_20260430/dataset/src/modeles/ \
  meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc/regime/
```

2. Smoke remoto:
```bash
ssh meso 'cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
  EPOCHS=1 DEVICE=cpu bash hpc/regime/smoke_test_phase3d_qtensor.sh'
```

3. Submit 70 runs:
```bash
ssh meso 'cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
  bash hpc/regime/submit_herald_phase3d_qtensor.sh'
```

4. Após resultados, aggregate + audit:
```bash
python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_regime_phase3d_qtensor_<STAMP>_r1
python3 hpc/regime/audit_herald_phase3d_qtensor_results.py \
  --root hpc_results/herald_regime_phase3d_qtensor_<STAMP>_r1
```
