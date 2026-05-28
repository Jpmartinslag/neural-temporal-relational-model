# HERALD Phase 3C Labor Tutor — Audit Report

Data: hpc_results/herald_regime_phase3c_labor_tutor_20260527_000424_r1

Job SLURM 7394700 | 10 array tasks | TODOS COMPLETED exit 0:0

## 1. Integridade

- JSONs encontrados: **180/180** (18 configs × 10 seeds)
- Jobs SLURM: 10 array tasks, todos **COMPLETED**, exit code **0:0**
- Runs CSV: 180 linhas, 18 labels únicos, 10 seeds cada
- Artefatos faltantes: **nenhum**

## 2. Tabela por config (n=10 seeds)

| Cfg | Label | N | Mean WMAPE | std | 2021 | 2022 | 2023 | 2024 | 2025 | Sector |
|-----|-------|---|-----------|-----|------|------|------|------|------|--------|
| C0 | C0_baseline | 10 | 0.02100 | 0.00222 | 0.03628 | 0.01938 | 0.01683 | 0.01995 | 0.01256 | 0.15888 |
| C1 | C1_defm_ze_recovery | 10 | 0.02157 | 0.00203 | 0.03894 | 0.02039 | 0.01608 | 0.02051 | 0.01194 | 0.15858 |
| C2 | C2_defm_ze_recovery_perm | 10 | 0.02198 | 0.00149 | 0.03958 | 0.02176 | 0.01805 | 0.01850 | 0.01201 | 0.15890 |
| C3 | C3_urssaf_cotisants_delta | 10 | 0.02118 | 0.00183 | 0.03449 | 0.02404 | 0.01644 | 0.01913 | 0.01179 | 0.15796 |
| C4 | C4_urssaf_cotisants_delta_perm | 10 | 0.02257 | 0.00275 | 0.04013 | 0.02430 | 0.01717 | 0.01928 | 0.01196 | 0.16052 |
| C5 | C5_combo_defm_urssaf | 10 | 0.02337 | 0.00314 | 0.04088 | 0.02133 | 0.01976 | 0.02188 | 0.01301 | 0.15914 |
| C6 | C6_combo_defm_urssaf_perm | 10 | 0.02232 | 0.00343 | 0.03698 | 0.02283 | 0.01801 | 0.02119 | 0.01257 | 0.16123 |
| C7 | C7_defm_lag2 | 10 | 0.02163 | 0.00141 | 0.03665 | 0.02345 | 0.01514 | 0.02099 | 0.01190 | 0.15785 |
| C8 | C8_urssaf_lag2 | 10 | 0.02199 | 0.00222 | 0.03693 | 0.02196 | 0.01825 | 0.02062 | 0.01221 | 0.15826 |
| C9 | C9_defm_spatial_perm | 10 | 0.02148 | 0.00143 | 0.03754 | 0.02206 | 0.01590 | 0.01990 | 0.01201 | 0.15690 |
| C10 | C10_urssaf_spatial_perm | 10 | 0.02131 | 0.00147 | 0.03425 | 0.02316 | 0.01592 | 0.02145 | 0.01175 | 0.15724 |
| C11 | C11_defm_signed_recovery | 10 | 0.02224 | 0.00233 | 0.03949 | 0.02084 | 0.01574 | 0.02207 | 0.01305 | 0.15848 |
| C12 | C12_defm_yoy | 10 | 0.02332 | 0.00289 | 0.03441 | 0.03232 | 0.01640 | 0.01997 | 0.01353 | 0.15771 |
| C13 | C13_urssaf_negative_only | 10 | 0.02172 | 0.00237 | 0.03769 | 0.02117 | 0.01671 | 0.02092 | 0.01212 | 0.15805 |
| C14 | C14_urssaf_positive_only | 10 | 0.02183 | 0.00182 | 0.03612 | 0.02628 | 0.01557 | 0.01944 | 0.01175 | 0.15883 |
| C15 | C15_combo_step06 | 10 | 0.02371 | 0.00336 | 0.04071 | 0.02169 | 0.01960 | 0.02339 | 0.01314 | 0.15969 |
| C16 | C16_combo_a10_guard | 10 | 0.02271 | 0.00310 | 0.03945 | 0.02312 | 0.01729 | 0.02103 | 0.01267 | 0.15572 |
| C17 | C17_combo_l3dim | 10 | 0.02204 | 0.00190 | 0.04008 | 0.01953 | 0.01782 | 0.02063 | 0.01216 | 0.15990 |

## 3. Comparações principais

C0 baseline: mean=0.02100±0.00222 | 2025=0.01256

| Par | A mean | B mean | Δ(A-B) | wins_A | p Wilcoxon | Δ2025 A vs C0 | Veredicto |
|-----|--------|--------|--------|--------|-----------|---------------|-----------|
| DEFM real vs temporal perm | 0.02157 | 0.02198 | -0.00041 | 6/10 | 0.3125 | -0.00062 ✓ | ✗ n.s. |
| URSSAF real vs temporal perm | 0.02118 | 0.02257 | -0.00139 | 8/10 | 0.0967 | -0.00077 ✓ | ✗ n.s. |
| Combo real vs perm | 0.02337 | 0.02232 | +0.00105 | 3/10 | 0.9033 | +0.00045 ✓ | ✗ n.s. |
| C1 vs C7 lag2 | 0.02157 | 0.02163 | -0.00005 | 5/10 | 0.4229 | -0.00062 ✓ | ✗ n.s. |
| C3 vs C8 lag2 | 0.02118 | 0.02199 | -0.00081 | 9/10 | 0.0322 | -0.00077 ✓ | ✓ real<perm |
| C1 vs C9 spatial perm | 0.02157 | 0.02148 | +0.00009 | 5/10 | 0.5391 | -0.00062 ✓ | ✗ n.s. |
| C3 vs C10 spatial perm | 0.02118 | 0.02131 | -0.00013 | 4/10 | 0.5771 | -0.00077 ✓ | ✗ n.s. |
| C5 vs C15 step06 | 0.02337 | 0.02371 | -0.00034 | 6/10 | 0.1875 | +0.00045 ✓ | ✗ n.s. |
| C5 vs C16 a10_guard | 0.02337 | 0.02271 | +0.00066 | 3/10 | 0.7842 | +0.00045 ✓ | ✗ n.s. |
| C5 vs C17 l3dim | 0.02337 | 0.02204 | +0.00133 | 4/10 | 0.8125 | +0.00045 ✓ | ✗ n.s. |

### C0 vs todos

| Cfg | Label | Δmean vs C0 | Δ2025 vs C0 | Guard 2025 |
|-----|-------|------------|------------|------------|
| C1 | C1_defm_ze_recovery | +0.00057 | -0.00062 | ✓ |
| C2 | C2_defm_ze_recovery_perm | +0.00098 | -0.00055 | ✓ |
| C3 | C3_urssaf_cotisants_delta | +0.00018 | -0.00077 | ✓ |
| C4 | C4_urssaf_cotisants_delta_perm | +0.00157 | -0.00060 | ✓ |
| C5 | C5_combo_defm_urssaf | +0.00237 | +0.00045 | ✓ |
| C6 | C6_combo_defm_urssaf_perm | +0.00132 | +0.00001 | ✓ |
| C7 | C7_defm_lag2 | +0.00063 | -0.00067 | ✓ |
| C8 | C8_urssaf_lag2 | +0.00099 | -0.00035 | ✓ |
| C9 | C9_defm_spatial_perm | +0.00048 | -0.00055 | ✓ |
| C10 | C10_urssaf_spatial_perm | +0.00031 | -0.00081 | ✓ |
| C11 | C11_defm_signed_recovery | +0.00124 | +0.00049 | ✓ |
| C12 | C12_defm_yoy | +0.00232 | +0.00097 | ✓ |
| C13 | C13_urssaf_negative_only | +0.00072 | -0.00044 | ✓ |
| C14 | C14_urssaf_positive_only | +0.00083 | -0.00081 | ✓ |
| C15 | C15_combo_step06 | +0.00271 | +0.00058 | ✓ |
| C16 | C16_combo_a10_guard | +0.00171 | +0.00011 | ✓ |
| C17 | C17_combo_l3dim | +0.00104 | -0.00040 | ✓ |

## 4. Veredito metodológico

### Real vs permutado
- **C1 vs C2 (DEFM)**: real=0.02157 < perm=0.02198 → ✓ real ganha | p=0.3125 (n.s.)
- **C3 vs C4 (URSSAF)**: real=0.02118 < perm=0.02257 → ✓ real ganha | p=0.0967 (n.s.)
- **C5 vs C6 (Combo)**: real=0.02337 < perm=0.02232 → ✗ real perde | p=0.9033 (n.s.)

### Melhora 2021 sem destruir 2025
- Melhor 2021: **C10** (0.03425 vs C0=0.03628)
- Melhor 2025: **C10** (0.01175 vs C0=0.01256)
- Configs que melhoram 2021 sem destruir 2025 (Δ2025≤+0.001):
  - C10 (C10_urssaf_spatial_perm): 2021=0.03425 (Δ=-0.00203), 2025=0.01175 (Δ=-0.00081)
  - C12 (C12_defm_yoy): 2021=0.03441 (Δ=-0.00188), 2025=0.01353 (Δ=+0.00097)
  - C3 (C3_urssaf_cotisants_delta): 2021=0.03449 (Δ=-0.00179), 2025=0.01179 (Δ=-0.00077)
  - C14 (C14_urssaf_positive_only): 2021=0.03612 (Δ=-0.00017), 2025=0.01175 (Δ=-0.00081)

### Combo vs sinais individuais
- C5 combo (0.02337) vs C1 (0.02157) e C3 (0.02118)
- **Combo piora vs ambos individuais** → adiciona ruído, não valor

### Lag2 / spatial perm — sinal causal vs proxy
- C1 real (0.02157) vs C7 lag2 (0.02163): C1 ganha
- C1 real (0.02157) vs C9 spatial_perm (0.02148): spatial_perm ganha ou empate
- C3 real (0.02118) vs C8 lag2 (0.02199): C3 ganha
- C3 real (0.02118) vs C10 spatial_perm (0.02131): C3 ganha
- **DEFM: lag2/spatial competem com contemporâneo** → sinal pode ser proxy temporal/espacial
- **URSSAF: sinal contemporâneo mais informativo** → evidência causal mais forte

### A10 guard (C16)
- C16 a10_guard: sector_wmape=0.15572 vs C0=0.15888 (Δ=-0.00317)
- C16 mean_wmape=0.02271 vs C0=0.02100 (Δ=+0.00171)
- **A10 guard MELHORA setor sem penalizar total significativamente** ✓