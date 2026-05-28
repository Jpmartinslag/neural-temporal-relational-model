# HERALD Phase 3E — q_tensor Architecture Selection

## Objective

Select the optimal q_tensor form for HERALD, based on Phase 3D findings:
- Q6_lag1 was best (mean WMAPE 0.02036)
- Q0_real does not significantly beat Q1_zero (p=0.46)
- effectifs channel ≈ full q_tensor; masse channel weaker

Phase 3E answers: which channel? which lag structure? does ZE identity matter in these sub-configs?

## Design

**12 configs × 20 seeds = 240 runs**

| Config | Policy | sector_lambda | Description |
|--------|--------|--------------|-------------|
| Q0_real | real | 0.2 | Baseline: full q_tensor contemporaneous |
| Q1_zero | zero | 0.2 | No q_tensor (ablation floor) |
| Q3_spatial_perm | spatial_perm | 0.2 | Full q_tensor, ZE permuted (spatial falsification) |
| Q4_effectifs_only | effectifs_only | 0.2 | effectifs channel only |
| Q5_masse_only | masse_only | 0.2 | masse_salariale channel only |
| Q6_lag1 | lag1 | 0.2 | Full q_tensor, lag 1 year |
| Q7_effectifs_lag1 | effectifs_lag1 | 0.2 | effectifs + lag1 (primary candidate) |
| Q8_masse_lag1 | masse_lag1 | 0.2 | masse_salariale + lag1 |
| Q9_lag2 | lag2 | 0.2 | Full q_tensor, lag 2 years |
| Q10_effectifs_spatial_perm | effectifs_spatial_perm | 0.2 | effectifs_only + ZE permuted (falsification) |
| Q11_lag1_spatial_perm | lag1_spatial_perm | 0.2 | lag1 + ZE permuted (falsification) |
| Q12_effectifs_lag1_a10guard | effectifs_lag1 | 0.3 | effectifs_lag1, A10 sector guard cost test |

Q2 (`temporal_perm`) excluded: global year permutation is not fold-safe.

## Seeds

20 seeds: `0 1 7 13 17 42 77 99 123 2025 3 5 11 19 23 29 31 37 101 303`

## Paired Comparisons (Wilcoxon one-sided, α=0.05)

| Comparison | Question |
|------------|---------|
| Q0_real vs Q1_zero | Does q_tensor contribute at all? |
| Q0_real vs Q3_spatial_perm | Does ZE identity matter (full q_tensor)? |
| Q4_effectifs_only vs Q5_masse_only | Which channel is stronger? |
| Q6_lag1 vs Q0_real | Does lag1 improve over contemporaneous? |
| Q7_effectifs_lag1 vs Q4_effectifs_only | Does lag1 improve effectifs alone? |
| Q7_effectifs_lag1 vs Q8_masse_lag1 | Channel comparison at lag1 |
| Q7_effectifs_lag1 vs Q10_effectifs_spatial_perm | ZE identity test for effectifs_lag1 |
| Q6_lag1 vs Q11_lag1_spatial_perm | ZE identity test for lag1 |
| Q7_effectifs_lag1 vs Q12_effectifs_lag1_a10guard | A10 guard cost |

## Guard Rail

WMAPE_2025 degradation ≤ 0.003 vs Q0_real for all winning configs.

## HPC

- Script: `hpc/regime/submit_herald_phase3e_qtensor_arch.sh`
- OUT_ROOT: `hpc_results/herald_regime_phase3e_qtensor_arch_<STAMP>_r1`
- Epochs: 800, mask_warmup: 100
- Audit: `python3 hpc/regime/audit_herald_phase3e_qtensor_arch_results.py --root <OUT_ROOT>`
