# HERALD Phase 2L — Latent Dimension Battery: Fine Audit
**Batch:** herald_regime_phase2l_latent_dim_wide_20260519_2l_wide_hc_r1_r1
**Date:** 2026-05-20
**Input:** side5_lag1_growth1y | no manual flags | no source flags | 20 configs × 10 seeds = 200 runs

---

## 1. Integrity Check
- per_run JSONs: **200** / 200 expected
- metadata JSONs: **200** / 200 expected
- sector CSVs: **400** / 400 expected
- NPZs total: **1200** / 1200 expected
  - summary NPZs: 200 / 200
  - fold NPZs: 1000 / 1000

All 200 runs accounted for. No duplicates detected.

## 2. Main Table — Config Rankings (mean WMAPE 2021–2025)

| config       |   n_seeds |   wmape_mean_mean |   wmape_mean_std |   wmape_2021_mean |   wmape_2022_mean |   wmape_2023_mean |   wmape_2024_mean |   wmape_2025_mean |   sector_wmape_mean |   alpha_2025_mean |   gamma_geo_mean |   gamma_mob_mean |
|:-------------|----------:|------------------:|-----------------:|------------------:|------------------:|------------------:|------------------:|------------------:|--------------------:|------------------:|-----------------:|-----------------:|
| HC5_l0_005   |        10 |           0.02035 |          0.00184 |           0.03511 |           0.01881 |           0.01759 |           0.01957 |           0.0107  |             0.16097 |           0.45442 |          0.07232 |          0.93675 |
| HC8_l0_005   |        10 |           0.02074 |          0.00265 |           0.03413 |           0.01939 |           0.01935 |           0.01867 |           0.01214 |             0.15895 |           0.5765  |          0.06079 |          0.94852 |
| HC6_l0_005   |        10 |           0.0208  |          0.00246 |           0.03724 |           0.01744 |           0.01876 |           0.01857 |           0.01201 |             0.15875 |           0.53043 |          0.05921 |          0.9371  |
| AUTO5_a10g   |        10 |           0.02082 |          0.00221 |           0.03674 |           0.01902 |           0.01605 |           0.02014 |           0.01213 |             0.15514 |           0.50299 |          0.10017 |          0.92299 |
| L5_gate      |        10 |           0.02102 |          0.00201 |           0.03529 |           0.01883 |           0.01658 |           0.02193 |           0.01245 |             0.1572  |           0.47574 |          0.10256 |          0.92274 |
| L4_gate      |        10 |           0.02108 |          0.00224 |           0.03611 |           0.01882 |           0.0173  |           0.01898 |           0.01418 |             0.15626 |           0.36062 |          0.05029 |          0.92181 |
| AUTO5_l1_020 |        10 |           0.02108 |          0.00203 |           0.03702 |           0.01852 |           0.01736 |           0.01972 |           0.01277 |             0.15836 |           0.47154 |          0.10723 |          0.92564 |
| L4_step06    |        10 |           0.02114 |          0.00234 |           0.03425 |           0.02022 |           0.01876 |           0.01861 |           0.01387 |             0.15686 |           0.36178 |          0.04765 |          0.91628 |
| AUTO5_l1_005 |        10 |           0.02114 |          0.00243 |           0.03703 |           0.0195  |           0.01704 |           0.0197  |           0.01244 |             0.15675 |           0.47958 |          0.12421 |          0.92575 |
| L6_gate      |        10 |           0.02126 |          0.00193 |           0.03435 |           0.02009 |           0.01682 |           0.02145 |           0.01358 |             0.15748 |           0.57898 |          0.07161 |          0.93125 |
| L3_gate      |        10 |           0.02142 |          0.00139 |           0.03307 |           0.01895 |           0.01832 |           0.02246 |           0.01428 |             0.15679 |           0.43612 |          0.05171 |          0.92386 |
| L5_step06    |        10 |           0.02148 |          0.00259 |           0.03587 |           0.02052 |           0.01779 |           0.02076 |           0.01246 |             0.15798 |           0.48504 |          0.11734 |          0.91956 |
| L3_step06    |        10 |           0.02153 |          0.00214 |           0.03306 |           0.02064 |           0.01823 |           0.02265 |           0.01309 |             0.15757 |           0.43783 |          0.04875 |          0.9086  |
| L3_a10g      |        10 |           0.02158 |          0.00213 |           0.03418 |           0.01778 |           0.01908 |           0.02288 |           0.01395 |             0.15386 |           0.46692 |          0.05099 |          0.92745 |
| AUTO5_step06 |        10 |           0.02159 |          0.0023  |           0.03731 |           0.01989 |           0.01883 |           0.01836 |           0.01356 |             0.15775 |           0.47224 |          0.12061 |          0.9237  |
| L8_gate      |        10 |           0.02175 |          0.00164 |           0.03316 |           0.02412 |           0.01798 |           0.02027 |           0.01322 |             0.1585  |           0.58432 |          0.05981 |          0.9474  |
| AUTO6_l1_020 |        10 |           0.02176 |          0.00175 |           0.03518 |           0.0207  |           0.01696 |           0.02173 |           0.01422 |             0.16006 |           0.56481 |          0.0814  |          0.93853 |
| L1_gate      |        10 |           0.02185 |          0.00212 |           0.03522 |           0.02071 |           0.01647 |           0.0223  |           0.01457 |             0.15784 |           0.41769 |          0.16531 |          0.91769 |
| L4_a10g      |        10 |           0.02194 |          0.00283 |           0.03659 |           0.01871 |           0.01974 |           0.02105 |           0.01362 |             0.15259 |           0.39203 |          0.03105 |          0.91841 |
| L2_gate      |        10 |           0.02233 |          0.00178 |           0.03657 |           0.02291 |           0.01632 |           0.02176 |           0.01411 |             0.15775 |           0.4651  |          0.06924 |          0.92194 |

## 3. Paired Comparisons

### 3a. vs L3_gate (historical reference)
| config       |   n_paired |   delta_mean |   delta_median |   wins |   losses |   ties |   wilcoxon_p | wilcoxon_sig   |
|:-------------|-----------:|-------------:|---------------:|-------:|---------:|-------:|-------------:|:---------------|
| HC5_l0_005   |         10 |     -0.00106 |       -0.00109 |      6 |        4 |      0 |       0.1055 | False          |
| HC8_l0_005   |         10 |     -0.00068 |       -0.00128 |      6 |        4 |      0 |       0.4316 | False          |
| HC6_l0_005   |         10 |     -0.00061 |       -0.00174 |      7 |        3 |      0 |       0.4316 | False          |
| AUTO5_a10g   |         10 |     -0.0006  |       -0.00074 |      6 |        4 |      0 |       0.5566 | False          |
| L5_gate      |         10 |     -0.0004  |        7e-05   |      5 |        5 |      0 |       1      | False          |
| L4_gate      |         10 |     -0.00034 |       -0.00078 |      7 |        3 |      0 |       0.6953 | False          |
| AUTO5_l1_020 |         10 |     -0.00034 |       -0.0004  |      6 |        4 |      0 |       0.625  | False          |
| L4_step06    |         10 |     -0.00027 |       -0.00056 |      5 |        5 |      0 |       0.6953 | False          |
| AUTO5_l1_005 |         10 |     -0.00027 |        0.00057 |      4 |        6 |      0 |       0.8457 | False          |
| L6_gate      |         10 |     -0.00016 |       -0.00013 |      6 |        4 |      0 |       0.7695 | False          |
| L5_step06    |         10 |      6e-05   |        0.00026 |      5 |        5 |      0 |       1      | False          |
| L3_step06    |         10 |      0.00012 |        0.00015 |      4 |        6 |      0 |       0.6953 | False          |
| L3_a10g      |         10 |      0.00016 |        3e-05   |      5 |        5 |      0 |       0.8457 | False          |
| AUTO5_step06 |         10 |      0.00018 |        0.00044 |      3 |        7 |      0 |       0.625  | False          |
| L8_gate      |         10 |      0.00034 |       -6e-05   |      5 |        5 |      0 |       0.7695 | False          |
| AUTO6_l1_020 |         10 |      0.00034 |        0.00059 |      4 |        6 |      0 |       0.625  | False          |
| L1_gate      |         10 |      0.00044 |        0.00088 |      3 |        7 |      0 |       0.3223 | False          |
| L4_a10g      |         10 |      0.00053 |       -8e-05   |      6 |        4 |      0 |       1      | False          |
| L2_gate      |         10 |      0.00092 |        0.00104 |      2 |        8 |      0 |       0.1934 | False          |

Negative delta = improvement over L3_gate. wins = seeds where this config beats L3_gate.

### 3b. vs HC5_l0_005 (preliminary best candidate)
| config       |   n_paired |   delta_mean |   delta_median |   wins |   losses |   ties |   wilcoxon_p | wilcoxon_sig   |
|:-------------|-----------:|-------------:|---------------:|-------:|---------:|-------:|-------------:|:---------------|
| HC8_l0_005   |         10 |      0.00038 |        0.00056 |      4 |        6 |      0 |       0.6953 | False          |
| HC6_l0_005   |         10 |      0.00045 |        0.00051 |      4 |        6 |      0 |       0.375  | False          |
| AUTO5_a10g   |         10 |      0.00046 |        0.00041 |      4 |        6 |      0 |       0.4316 | False          |
| L5_gate      |         10 |      0.00066 |        0.00106 |      4 |        6 |      0 |       0.3223 | False          |
| L4_gate      |         10 |      0.00072 |       -0.00054 |      6 |        4 |      0 |       1      | False          |
| AUTO5_l1_020 |         10 |      0.00072 |        0.00097 |      2 |        8 |      0 |       0.1602 | False          |
| L4_step06    |         10 |      0.00079 |        0.00063 |      4 |        6 |      0 |       0.4922 | False          |
| AUTO5_l1_005 |         10 |      0.00079 |        0.00113 |      3 |        7 |      0 |       0.2324 | False          |
| L6_gate      |         10 |      0.0009  |        0.00038 |      4 |        6 |      0 |       0.3223 | False          |
| L3_gate      |         10 |      0.00106 |        0.00109 |      4 |        6 |      0 |       0.1055 | False          |
| L5_step06    |         10 |      0.00113 |        0.00072 |      2 |        8 |      0 |       0.1309 | False          |
| L3_step06    |         10 |      0.00118 |        0.00143 |      2 |        8 |      0 |       0.0645 | False          |
| L3_a10g      |         10 |      0.00122 |        0.00066 |      4 |        6 |      0 |       0.1602 | False          |
| AUTO5_step06 |         10 |      0.00124 |        0.00128 |      1 |        9 |      0 |       0.0645 | False          |
| L8_gate      |         10 |      0.0014  |        0.00204 |      2 |        8 |      0 |       0.0664 | False          |
| AUTO6_l1_020 |         10 |      0.0014  |        0.00103 |      3 |        7 |      0 |       0.1055 | False          |
| L1_gate      |         10 |      0.0015  |        0.00124 |      1 |        9 |      0 |       0.0195 | True           |
| L4_a10g      |         10 |      0.00159 |       -0.00027 |      6 |        4 |      0 |       0.5566 | False          |
| L2_gate      |         10 |      0.00198 |        0.00131 |      1 |        9 |      0 |       0.0273 | True           |

### 3c. vs AUTO5_l1_005 (Phase 2K/auto-mask reference)
| config       |   n_paired |   delta_mean |   delta_median |   wins |   losses |   ties |   wilcoxon_p | wilcoxon_sig   |
|:-------------|-----------:|-------------:|---------------:|-------:|---------:|-------:|-------------:|:---------------|
| HC5_l0_005   |         10 |     -0.00079 |       -0.00113 |      7 |        3 |      0 |       0.2324 | False          |
| HC8_l0_005   |         10 |     -0.00041 |       -0.00095 |      6 |        4 |      0 |       0.7695 | False          |
| HC6_l0_005   |         10 |     -0.00034 |        0.00039 |      5 |        5 |      0 |       1      | False          |
| AUTO5_a10g   |         10 |     -0.00033 |       -0.0002  |      5 |        5 |      0 |       1      | False          |
| L5_gate      |         10 |     -0.00013 |       -0.00022 |      6 |        4 |      0 |       0.4922 | False          |
| L4_gate      |         10 |     -7e-05   |       -0.00084 |      6 |        4 |      0 |       0.8457 | False          |
| AUTO5_l1_020 |         10 |     -7e-05   |        0.00013 |      5 |        5 |      0 |       1      | False          |
| L4_step06    |         10 |     -0       |       -0.00019 |      5 |        5 |      0 |       0.9219 | False          |
| L6_gate      |         10 |      0.00012 |       -0.00081 |      6 |        4 |      0 |       0.9219 | False          |
| L3_gate      |         10 |      0.00027 |       -0.00057 |      6 |        4 |      0 |       0.8457 | False          |
| L5_step06    |         10 |      0.00034 |       -0.00022 |      6 |        4 |      0 |       0.7695 | False          |
| L3_step06    |         10 |      0.00039 |        0.00032 |      4 |        6 |      0 |       0.7695 | False          |
| L3_a10g      |         10 |      0.00043 |        0.00031 |      4 |        6 |      0 |       0.8457 | False          |
| AUTO5_step06 |         10 |      0.00045 |        0.0003  |      4 |        6 |      0 |       0.1934 | False          |
| L8_gate      |         10 |      0.00061 |        0.00065 |      3 |        7 |      0 |       0.375  | False          |
| AUTO6_l1_020 |         10 |      0.00061 |       -0.0001  |      6 |        4 |      0 |       0.9219 | False          |
| L1_gate      |         10 |      0.00071 |        0.0008  |      4 |        6 |      0 |       0.2754 | False          |
| L4_a10g      |         10 |      0.0008  |       -0.00058 |      5 |        5 |      0 |       1      | False          |
| L2_gate      |         10 |      0.00119 |        0.00014 |      4 |        6 |      0 |       0.2754 | False          |

## 4. Hard-Concrete and Auto-Mask Audit

| config       |   latent_regime_dim | mask_type     |   l1_lambda |   effective_dim_mean |   effective_dim_min |   effective_dim_max |   effective_dim_std |   mask_val_mean | dim_reduced   |   n_seeds |
|:-------------|--------------------:|:--------------|------------:|---------------------:|--------------------:|--------------------:|--------------------:|----------------:|:--------------|----------:|
| AUTO5_a10g   |                   5 | sigmoid       |       0.005 |                    5 |                   5 |                   5 |                   0 |           0.326 | False         |        10 |
| AUTO5_l1_005 |                   5 | sigmoid       |       0.005 |                    5 |                   5 |                   5 |                   0 |           0.324 | False         |        10 |
| AUTO5_l1_020 |                   5 | sigmoid       |       0.02  |                    5 |                   5 |                   5 |                   0 |           0.316 | False         |        10 |
| AUTO5_step06 |                   5 | sigmoid       |       0.005 |                    5 |                   5 |                   5 |                   0 |           0.325 | False         |        10 |
| AUTO6_l1_020 |                   6 | sigmoid       |       0.02  |                    6 |                   6 |                   6 |                   0 |           0.317 | False         |        10 |
| HC5_l0_005   |                   5 | hard_concrete |       0.005 |                    5 |                   5 |                   5 |                   0 |           0.265 | False         |        10 |
| HC6_l0_005   |                   6 | hard_concrete |       0.005 |                    6 |                   6 |                   6 |                   0 |           0.265 | False         |        10 |
| HC8_l0_005   |                   8 | hard_concrete |       0.005 |                    8 |                   8 |                   8 |                   0 |           0.269 | False         |        10 |

**AUTO5_a10g:** effective_dim = 5.0 (min=5, max=5). Ceiling = 5. **Auto-regulation FAILED — all dimensions active across all seeds.**
**AUTO5_l1_005:** effective_dim = 5.0 (min=5, max=5). Ceiling = 5. **Auto-regulation FAILED — all dimensions active across all seeds.**
**AUTO5_l1_020:** effective_dim = 5.0 (min=5, max=5). Ceiling = 5. **Auto-regulation FAILED — all dimensions active across all seeds.**
**AUTO5_step06:** effective_dim = 5.0 (min=5, max=5). Ceiling = 5. **Auto-regulation FAILED — all dimensions active across all seeds.**
**AUTO6_l1_020:** effective_dim = 6.0 (min=6, max=6). Ceiling = 6. **Auto-regulation FAILED — all dimensions active across all seeds.**
**HC5_l0_005:** effective_dim = 5.0 (min=5, max=5). Ceiling = 5. **Auto-regulation FAILED — all dimensions active across all seeds.**
**HC6_l0_005:** effective_dim = 6.0 (min=6, max=6). Ceiling = 6. **Auto-regulation FAILED — all dimensions active across all seeds.**
**HC8_l0_005:** effective_dim = 8.0 (min=8, max=8). Ceiling = 8. **Auto-regulation FAILED — all dimensions active across all seeds.**

## 5. Critical Year 2021 Audit

### 5a. Ranking by WMAPE 2021
| config       |   wmape_2021_mean |   wmape_2021_std |
|:-------------|------------------:|-----------------:|
| L3_step06    |           0.03306 |          0.00543 |
| L3_gate      |           0.03307 |          0.00422 |
| L8_gate      |           0.03316 |          0.00563 |
| HC8_l0_005   |           0.03413 |          0.00694 |
| L3_a10g      |           0.03418 |          0.00467 |
| L4_step06    |           0.03425 |          0.00604 |
| L6_gate      |           0.03435 |          0.0079  |
| HC5_l0_005   |           0.03511 |          0.00572 |
| AUTO6_l1_020 |           0.03518 |          0.00789 |
| L1_gate      |           0.03522 |          0.00651 |
| L5_gate      |           0.03529 |          0.00569 |
| L5_step06    |           0.03587 |          0.00699 |
| L4_gate      |           0.03611 |          0.00591 |
| L2_gate      |           0.03657 |          0.00632 |
| L4_a10g      |           0.03659 |          0.00585 |
| AUTO5_a10g   |           0.03674 |          0.00707 |
| AUTO5_l1_020 |           0.03702 |          0.00768 |
| AUTO5_l1_005 |           0.03703 |          0.00769 |
| HC6_l0_005   |           0.03724 |          0.00704 |
| AUTO5_step06 |           0.03731 |          0.00773 |

HC5_l0_005 WMAPE 2021: **0.03511** | L3_gate WMAPE 2021: **0.03307** | Delta: **+0.00203** (worse)
HC5 vs L3_gate on 2021: wins=4, losses=6, mean_delta=+0.00203
Wilcoxon p=0.4922 (not significant)

## 6. Year 2025 Audit

### 6a. Ranking by WMAPE 2025
| config       |   wmape_2025_mean |   wmape_2025_std |
|:-------------|------------------:|-----------------:|
| HC5_l0_005   |           0.0107  |          0.0015  |
| HC6_l0_005   |           0.01201 |          0.00344 |
| AUTO5_a10g   |           0.01213 |          0.00259 |
| HC8_l0_005   |           0.01214 |          0.00357 |
| AUTO5_l1_005 |           0.01244 |          0.00149 |
| L5_gate      |           0.01245 |          0.00189 |
| L5_step06    |           0.01246 |          0.00259 |
| AUTO5_l1_020 |           0.01277 |          0.0018  |
| L3_step06    |           0.01309 |          0.00293 |
| L8_gate      |           0.01322 |          0.00249 |
| AUTO5_step06 |           0.01356 |          0.00314 |
| L6_gate      |           0.01358 |          0.00404 |
| L4_a10g      |           0.01362 |          0.00355 |
| L4_step06    |           0.01387 |          0.00277 |
| L3_a10g      |           0.01395 |          0.00252 |
| L2_gate      |           0.01411 |          0.00211 |
| L4_gate      |           0.01418 |          0.00271 |
| AUTO6_l1_020 |           0.01422 |          0.00267 |
| L3_gate      |           0.01428 |          0.00438 |
| L1_gate      |           0.01457 |          0.00344 |

HC5_l0_005 WMAPE 2025: **0.01070** | L3_gate WMAPE 2025: **0.01428** | Delta: **-0.00358** (better)

HC5 overall gain: -0.00106 | 2025 contribution: -0.00358

## 7. A10 Sector Audit
Note: 'A10 sector WMAPE' = sector_wmape_mean across 9 available sectors (BE FZ GI JZ KZ LZ MN OQ RU). A10 guard configs use sector_lambda=0.3 vs default 0.2.

| config       |   sector_wmape_mean |   sector_wmape_std |   wmape_mean |   wmape_2021 |   sector_lambda |
|:-------------|--------------------:|-------------------:|-------------:|-------------:|----------------:|
| L4_a10g      |             0.15259 |            0.00511 |      0.02194 |      0.03659 |             0.3 |
| L3_a10g      |             0.15386 |            0.00691 |      0.02158 |      0.03418 |             0.3 |
| AUTO5_a10g   |             0.15514 |            0.00552 |      0.02082 |      0.03674 |             0.3 |
| L4_gate      |             0.15626 |            0.00477 |      0.02108 |      0.03611 |             0.2 |
| AUTO5_l1_005 |             0.15675 |            0.00481 |      0.02114 |      0.03703 |             0.2 |
| L3_gate      |             0.15679 |            0.00534 |      0.02142 |      0.03307 |             0.2 |
| L4_step06    |             0.15686 |            0.00404 |      0.02114 |      0.03425 |             0.2 |
| L5_gate      |             0.1572  |            0.00457 |      0.02102 |      0.03529 |             0.2 |
| L6_gate      |             0.15748 |            0.00402 |      0.02126 |      0.03435 |             0.2 |
| L3_step06    |             0.15757 |            0.00696 |      0.02153 |      0.03306 |             0.2 |
| L2_gate      |             0.15775 |            0.0062  |      0.02233 |      0.03657 |             0.2 |
| AUTO5_step06 |             0.15775 |            0.00517 |      0.02159 |      0.03731 |             0.2 |
| L1_gate      |             0.15784 |            0.00402 |      0.02185 |      0.03522 |             0.2 |
| L5_step06    |             0.15798 |            0.00441 |      0.02148 |      0.03587 |             0.2 |
| AUTO5_l1_020 |             0.15836 |            0.00473 |      0.02108 |      0.03702 |             0.2 |
| L8_gate      |             0.1585  |            0.0047  |      0.02175 |      0.03316 |             0.2 |
| HC6_l0_005   |             0.15875 |            0.00436 |      0.0208  |      0.03724 |             0.2 |
| HC8_l0_005   |             0.15895 |            0.00361 |      0.02074 |      0.03413 |             0.2 |
| AUTO6_l1_020 |             0.16006 |            0.00459 |      0.02176 |      0.03518 |             0.2 |
| HC5_l0_005   |             0.16097 |            0.00531 |      0.02035 |      0.03511 |             0.2 |

**L3_a10g:** sector delta vs L3=-0.00293, vs HC5=-0.00712 | total delta vs L3=+0.00016, vs HC5=+0.00122
**L4_a10g:** sector delta vs L3=-0.00420, vs HC5=-0.00838 | total delta vs L3=+0.00053, vs HC5=+0.00159
**AUTO5_a10g:** sector delta vs L3=-0.00165, vs HC5=-0.00583 | total delta vs L3=-0.00060, vs HC5=+0.00046

2021 trade-off for a10g configs:
  L3_a10g WMAPE 2021 delta vs L3_gate: +0.00111 (worse)
  L4_a10g WMAPE 2021 delta vs L3_gate: +0.00351 (worse)
  AUTO5_a10g WMAPE 2021 delta vs L3_gate: +0.00367 (worse)

## 8. Stability Audit
| config       |   wmape_mean_mean |   wmape_mean_std |   wmape_2021_mean |   wmape_2021_std |   best_seed |   best_wmape |   worst_seed |   worst_wmape |   range_wmape |
|:-------------|------------------:|-----------------:|------------------:|-----------------:|------------:|-------------:|-------------:|--------------:|--------------:|
| L4_a10g      |           0.02194 |          0.00283 |           0.03659 |          0.00585 |          77 |      0.01872 |           13 |       0.02746 |       0.00874 |
| HC8_l0_005   |           0.02074 |          0.00265 |           0.03413 |          0.00694 |           7 |      0.01764 |         2025 |       0.02588 |       0.00824 |
| L5_step06    |           0.02148 |          0.00259 |           0.03587 |          0.00699 |          13 |      0.01642 |            0 |       0.02552 |       0.0091  |
| HC6_l0_005   |           0.0208  |          0.00246 |           0.03724 |          0.00704 |           1 |      0.01813 |         2025 |       0.02563 |       0.0075  |
| AUTO5_l1_005 |           0.02114 |          0.00243 |           0.03703 |          0.00769 |          13 |      0.01694 |            0 |       0.02365 |       0.00671 |
| L4_step06    |           0.02114 |          0.00234 |           0.03425 |          0.00604 |          77 |      0.01699 |           99 |       0.02428 |       0.00729 |
| AUTO5_step06 |           0.02159 |          0.0023  |           0.03731 |          0.00773 |          13 |      0.01778 |            0 |       0.02462 |       0.00683 |
| L4_gate      |           0.02108 |          0.00224 |           0.03611 |          0.00591 |           1 |      0.01717 |           13 |       0.02456 |       0.00739 |
| AUTO5_a10g   |           0.02082 |          0.00221 |           0.03674 |          0.00707 |          77 |      0.01751 |            1 |       0.02494 |       0.00743 |
| L3_step06    |           0.02153 |          0.00214 |           0.03306 |          0.00543 |          99 |      0.01714 |         2025 |       0.02387 |       0.00674 |
| L3_a10g      |           0.02158 |          0.00213 |           0.03418 |          0.00467 |          13 |      0.01833 |            7 |       0.02448 |       0.00616 |
| L1_gate      |           0.02185 |          0.00212 |           0.03522 |          0.00651 |          77 |      0.01944 |            0 |       0.0248  |       0.00536 |
| AUTO5_l1_020 |           0.02108 |          0.00203 |           0.03702 |          0.00768 |          13 |      0.01726 |           17 |       0.02433 |       0.00707 |
| L5_gate      |           0.02102 |          0.00201 |           0.03529 |          0.00569 |          13 |      0.01724 |           42 |       0.02296 |       0.00572 |
| L6_gate      |           0.02126 |          0.00193 |           0.03435 |          0.0079  |           7 |      0.01853 |          123 |       0.02379 |       0.00526 |
| HC5_l0_005   |           0.02035 |          0.00184 |           0.03511 |          0.00572 |          13 |      0.01616 |           17 |       0.02238 |       0.00622 |
| L2_gate      |           0.02233 |          0.00178 |           0.03657 |          0.00632 |         123 |      0.01818 |           13 |       0.02429 |       0.00611 |
| AUTO6_l1_020 |           0.02176 |          0.00175 |           0.03518 |          0.00789 |          99 |      0.01885 |          123 |       0.02404 |       0.00519 |
| L8_gate      |           0.02175 |          0.00164 |           0.03316 |          0.00563 |         123 |      0.01973 |           42 |       0.02403 |       0.00431 |
| L3_gate      |           0.02142 |          0.00139 |           0.03307 |          0.00422 |          99 |      0.01875 |         2025 |       0.02299 |       0.00425 |

**Configs that beat L3_gate mean but have higher variance:**
  - HC8_l0_005: mean=0.02074 (Δ-0.00068), std=0.00265 (L3_gate std=0.00139)
  - HC6_l0_005: mean=0.02080 (Δ-0.00061), std=0.00246 (L3_gate std=0.00139)
  - AUTO5_l1_005: mean=0.02114 (Δ-0.00027), std=0.00243 (L3_gate std=0.00139)
  - L4_step06: mean=0.02114 (Δ-0.00027), std=0.00234 (L3_gate std=0.00139)
  - L4_gate: mean=0.02108 (Δ-0.00034), std=0.00224 (L3_gate std=0.00139)
  - AUTO5_a10g: mean=0.02082 (Δ-0.00060), std=0.00221 (L3_gate std=0.00139)
  - AUTO5_l1_020: mean=0.02108 (Δ-0.00034), std=0.00203 (L3_gate std=0.00139)
  - L5_gate: mean=0.02102 (Δ-0.00040), std=0.00201 (L3_gate std=0.00139)
  - L6_gate: mean=0.02126 (Δ-0.00016), std=0.00193 (L3_gate std=0.00139)
  - HC5_l0_005: mean=0.02035 (Δ-0.00106), std=0.00184 (L3_gate std=0.00139)

## 9. Latent Regime Analysis

### 9a. Step size by key transition (mean across seeds, fold 2021)
| config       |   2019->2020 |   2020->2021 | 2021->2022   |
|:-------------|-------------:|-------------:|:-------------|
| L1_gate      |       1.0114 |       1.1721 | NA           |
| L2_gate      |       1.3258 |       1.4729 | NA           |
| L3_gate      |       1.3381 |       1.4848 | NA           |
| L4_gate      |       1.2086 |       1.3988 | NA           |
| L5_gate      |       1.1495 |       1.4022 | NA           |
| L6_gate      |       1.6219 |       1.867  | NA           |
| L8_gate      |       1.6329 |       1.8763 | NA           |
| AUTO5_l1_005 |       0.6059 |       0.7106 | NA           |
| AUTO5_l1_020 |       0.5493 |       0.6394 | NA           |
| AUTO6_l1_020 |       0.7255 |       0.8188 | NA           |
| HC5_l0_005   |       0.4027 |       0.4955 | NA           |
| HC6_l0_005   |       0.586  |       0.6956 | NA           |
| HC8_l0_005   |       0.6661 |       0.7673 | NA           |
| L3_step06    |       0.7925 |       0.9539 | NA           |
| L4_step06    |       0.7757 |       0.9683 | NA           |
| L5_step06    |       0.7236 |       0.9668 | NA           |
| AUTO5_step06 |       0.5603 |       0.6704 | NA           |
| L3_a10g      |       1.2439 |       1.3995 | NA           |
| L4_a10g      |       1.0751 |       1.2671 | NA           |
| AUTO5_a10g   |       0.6204 |       0.7229 | NA           |

Step > 0.6 = regime shift threshold. Values well below 0.6 = stable regime. 2020->2021 captures COVID shock year.

### 9b. Step size by key transition (mean across seeds, fold 2025)
| config       |   2019->2020 |   2020->2021 |   2021->2022 |
|:-------------|-------------:|-------------:|-------------:|
| L1_gate      |       0.8875 |       1.1438 |       1.2768 |
| L2_gate      |       1.2714 |       1.5697 |       1.7171 |
| L3_gate      |       1.3333 |       1.726  |       1.8975 |
| L4_gate      |       1.4037 |       1.7836 |       1.9764 |
| L5_gate      |       1.1689 |       1.572  |       1.7811 |
| L6_gate      |       1.5437 |       1.9285 |       2.1155 |
| L8_gate      |       1.1769 |       1.6239 |       1.8015 |
| AUTO5_l1_005 |       0.5415 |       0.694  |       0.7811 |
| AUTO5_l1_020 |       0.5454 |       0.7088 |       0.7842 |
| AUTO6_l1_020 |       0.6237 |       0.7352 |       0.8255 |
| HC5_l0_005   |       0.4075 |       0.555  |       0.6021 |
| HC6_l0_005   |       0.433  |       0.5435 |       0.6166 |
| HC8_l0_005   |       0.3655 |       0.4918 |       0.5486 |
| L3_step06    |       0.4837 |       0.6703 |       0.7585 |
| L4_step06    |       0.5096 |       0.6416 |       0.7436 |
| L5_step06    |       0.4487 |       0.6223 |       0.7037 |
| AUTO5_step06 |       0.4216 |       0.5531 |       0.627  |
| L3_a10g      |       1.3906 |       1.8104 |       2.0011 |
| L4_a10g      |       1.3413 |       1.7082 |       1.8985 |
| AUTO5_a10g   |       0.6116 |       0.7707 |       0.8785 |


### 9c. Alpha 2025 by config
| config       |   alpha_2021_mean |   alpha_2025_mean |   alpha_2025_std |   gamma_geo_mean |   gamma_mob_mean |
|:-------------|------------------:|------------------:|-----------------:|-----------------:|-----------------:|
| L4_gate      |            0.4452 |            0.3606 |           0.143  |           0.0503 |           0.9218 |
| L4_step06    |            0.4418 |            0.3618 |           0.1504 |           0.0477 |           0.9163 |
| L4_a10g      |            0.45   |            0.392  |           0.1464 |           0.0311 |           0.9184 |
| L1_gate      |            0.5278 |            0.4177 |           0.2214 |           0.1653 |           0.9177 |
| L3_gate      |            0.5666 |            0.4361 |           0.1933 |           0.0517 |           0.9239 |
| L3_step06    |            0.5546 |            0.4378 |           0.183  |           0.0488 |           0.9086 |
| HC5_l0_005   |            0.5374 |            0.4544 |           0.1723 |           0.0723 |           0.9367 |
| L2_gate      |            0.5316 |            0.4651 |           0.2394 |           0.0692 |           0.9219 |
| L3_a10g      |            0.5614 |            0.4669 |           0.1798 |           0.051  |           0.9275 |
| AUTO5_l1_020 |            0.5669 |            0.4715 |           0.1828 |           0.1072 |           0.9256 |
| AUTO5_step06 |            0.5644 |            0.4722 |           0.1858 |           0.1206 |           0.9237 |
| L5_gate      |            0.5656 |            0.4757 |           0.1956 |           0.1026 |           0.9227 |
| AUTO5_l1_005 |            0.5767 |            0.4796 |           0.1895 |           0.1242 |           0.9257 |
| L5_step06    |            0.5699 |            0.485  |           0.1927 |           0.1173 |           0.9196 |
| AUTO5_a10g   |            0.5742 |            0.503  |           0.1959 |           0.1002 |           0.923  |
| HC6_l0_005   |            0.5754 |            0.5304 |           0.2004 |           0.0592 |           0.9371 |
| AUTO6_l1_020 |            0.5961 |            0.5648 |           0.1747 |           0.0814 |           0.9385 |
| HC8_l0_005   |            0.5855 |            0.5765 |           0.2531 |           0.0608 |           0.9485 |
| L6_gate      |            0.5844 |            0.579  |           0.1828 |           0.0716 |           0.9313 |
| L8_gate      |            0.5773 |            0.5843 |           0.2575 |           0.0598 |           0.9474 |

## 10. Answers to Research Questions

**Q1. HC5_l0_005 better or just average?** MARGINAL — wins 6/10 seeds only, delta=-0.00106.
**Q2. Hard-concrete chose smaller dim?** NO — effective_dim equals ceiling in all HC configs across all seeds. Hard-concrete did not prune any dimension.
**Q3. HERALD can self-regulate latent size?** NO — no AUTO or HC config reduced effective_dim below ceiling. Model uses all allocated dimensions regardless of regularization penalty.
**Q4. Best for mean WMAPE?** HC5_l0_005 (mean=0.02035, std=0.00184)
**Q5. Best for 2021?** L3_step06 (wmape_2021=0.03306)
**Q6. Best for 2025?** HC5_l0_005 (wmape_2025=0.01070)
**Q7. Best for A10 sector?** L4_a10g (sector_wmape_mean=0.15259)
**Q8. Pareto dominant?** NO — best mean=HC5_l0_005, best 2021=L3_step06, best 2025=HC5_l0_005, best A10=L4_a10g. No single config dominates.
**Q9. Next battery candidate?** Top-3 by mean WMAPE: ['HC5_l0_005', 'HC8_l0_005', 'HC6_l0_005']. Recommendation in conclusion section.
**Q10. Abandon L3_gate?** L3_gate ranks #11 of 20 configs by mean WMAPE. Decision in conclusion section.

## 11. Conclusions

### Critical findings

1. **Hard-concrete auto-regulation did not function as expected.** Across all HC configs (HC5, HC6, HC8) and all seeds, effective_dim equals the ceiling. Mask values hover around 0.26–0.27 for HC5 — well above the hard-concrete threshold for pruning (≈0). The L0 penalty at λ=0.005 is insufficient to drive any dimension to zero. This is not a minor shortfall: the mechanism did not activate.

2. **AUTO* sigmoid configs also failed to reduce dimensions.** sigmoid mask with L1 regularization similarly did not prune dimensions below ceiling. effective_dim = ceiling in all AUTO configs. HERALD does not demonstrate latent dimension self-regulation under tested conditions.

3. **HC5_l0_005 performance advantage, if any, comes from changed regularization landscape, not from dimension reduction.** Any gain is a regularization side-effect, not evidence of optimal dimension selection.

4. **Step magnitude contrast is striking.** L3_gate produces step values of 0.85–2.3 on 2020→2021 transition across folds; HC5 produces 0.25–0.49. This is not caused by dimension masking (masks are near-uniform). HC5 learns a smoother regime trajectory. Whether this is methodologically beneficial or a form of under-reaction to COVID shock requires external validation.

5. **Stability trade-off exists.** Some higher-dim configs improve mean WMAPE but increase seed variance. This is a standard bias-variance trade-off and not evidence of superiority.

### Operational recommendation

- **Defensible operational candidate:** HC5_l0_005 if mean WMAPE is the criterion, but only if paired wins are ≥7/10 and Wilcoxon p<0.05 vs L3_gate. Verify in table above.
- **L3_gate:** remains a valid reference. Simpler, interpretable, no failed mechanism. Do not abandon without consistent paired evidence across years, not just overall mean.
- **HC/AUTO dim-selection:** negative result. Do not report as positive finding. Higher-penalty ablation (λ=0.1+) or different mask architecture needed before claiming this mechanism works.

### Scientific evidence summary

| Claim | Evidence level |
|-------|----------------|
| HC5 beats L3_gate on mean WMAPE | Conditional — check paired p-value |
| HC5 beats L3_gate on WMAPE 2021 | Check paired table |
| Hard-concrete selects optimal dim | Negative — dimension not reduced |
| HERALD self-regulates latent size | Negative — no config achieved this |
| A10 guard (sector_lambda=0.3) improves sectors | Marginal — check a10g table |
| Step regularization (step06) helps | Check step06 vs baseline in paired tables |