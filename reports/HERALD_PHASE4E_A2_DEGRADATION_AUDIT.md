# HERALD Phase 4E-A2 Degradation Audit

**Date**: 2026-06-03  
**Auditor**: automated analysis  
**Question**: Why does Phase 4E-A2 show degraded WMAPE vs Phase 4A?

---

## Executive Summary

**The primary cause of apparent degradation is a data leakage bug in Phase 4A that inflated its WMAPE artificially.** Phase 4E-A/A2 fixed this bug; the resulting higher WMAPE reflects true out-of-sample performance. Phase 4A results are **invalid** and should not be used as a scientific performance baseline.

Secondary contributor: Phase 4E evaluates harder post-COVID years not present in Phase 4A (BE +4 years, PT +2 years). Even on common years only, the gap persists — fully attributable to the leakage fix.

Phase 4E-A2 full battery (10 seeds per country) has completed and confirms the Phase 4E-A picture with minimal shift.

---

## Result Table

| Country | Phase 4A (n=20) | Phase 4E-A (n=10) | Phase 4E-A2 (n=10) | Config A2 |
|---------|-----------------|-------------------|---------------------|-----------|
| FR | — (different pipeline) | 0.117044 ± 0.004437 | **0.103189 ± 0.008034** | fr_side2 |
| NL | 0.058184 ± 0.002302 | 0.103570 ± 0.008227 | **0.102759 ± 0.006983** | current_clean + zero |
| BE | 0.070913 ± — | 0.154536 ± 0.008184 | **0.162253 ± 0.008524** | side5_lag1_growth1y + zero |
| PT | 0.169902 ± — | 0.246521 ± 0.013689 | **0.234945 ± 0.009427** | side5_lag1_growth1y + effectifs_lag1 |

Phase 4A and Phase 4E-A use all available eval years (different ranges per country — see §3).  
Phase 4A values are **leaky** (see §1) and listed for historical context only.

Key observation: Phase 4E-A2 improves FR, NL, and PT versus Phase 4E-A, but BE worsens. PT A2 improves because the tensor helps slightly. BE remains the open case — see §4.

---

## Finding 1 — DATA LEAKAGE IN PHASE 4A (BUG CONFIRMED)

**Severity: Critical. Phase 4A WMAPE invalid.**

### What happened

| Pipeline | growth_1y formula | Direction |
|----------|-------------------|-----------|
| Phase 4A (`ingest_*.py`) | `(y[t] - y[t-1]) / y[t-1]` | Uses target `y[t]` → **LEAKY** |
| Phase 4E (`build_european_panel.py:82`) | `(lag1_births - lag2_births) / lag2_births` | = `(y[t-1] - y[t-2]) / y[t-2]` → **CORRECT** |

`growth_1y` in Phase 4A encodes the current year's target births. The model received nearly the answer to predict as an input feature, which explains the artificially low WMAPE.

### Proof (off-by-one pattern)

Portugal, ZE2020=8:
```
year  | growth_1y Phase4A | growth_1y Phase4E | note
2013  |  5.758651          |  -0.214674        | P4A[2013] = P4E[2014]
2014  | -0.461666          |   5.758651        | P4E[2014] = P4A[2013] (same value, one year later)
```
Phase 4E value at year t equals Phase 4A value at year t-1. Classic off-by-one lag.

### Magnitude of differences on common years

| Country | Rows changed / total | max_diff | mean_diff | NaNs P4 | NaNs P4E |
|---------|----------------------|----------|-----------|---------|---------|
| NL | 360 / 440 (82%) | 0.425 | 0.084 | 40 | 80 |
| BE | 504 / 588 (86%) | 0.699 | 0.160 | 42 | 84 |
| PT | 325 / 375 (87%) | 6.220 | 0.301 | 25 | 50 |

Phase 4E doubles the NaN count for growth_1y: the correct lag requires lag2, so the first year of each panel has no lag2 → NaN. Phase 4A had structurally wrong data, not missing data.

### Feature policies affected

`side5_lag1_growth1y` (used for BE and PT) explicitly keeps `growth_1y`.  
`current_clean` (used for NL) keeps all annual features including `growth_1y`.  
**Both policies were leaky in Phase 4A.**

---

## Finding 2 — ALL OTHER PANEL COLUMNS IDENTICAL ON COMMON YEARS

| Column | NL changed | BE changed | PT changed |
|--------|-----------|-----------|-----------|
| side_lag_1 | 0 | 0 | 0 |
| side_lag_2 | 0 | 0 | 0 |
| side_lag_3 | 0 | 0 | 0 |
| growth_2y | 0 | 0 | 0 |
| side_stock_total_t_minus_1 | 0 | 0 | 0 |
| **growth_1y** | **360/440** | **504/588** | **325/375** |
| feature_forecast_safe | 40 | 42 | 25 (unused) |

Lags, growth_2y, and stock are identical on common years. The panel change is isolated to growth_1y. This rules out data ingestion bugs in lags or stock.

`feature_forecast_safe` changed (first year per country: 1→0, correctly marking the earliest year as lag-unsafe), but `feature_forecast_safe` is not referenced in `train_herald_semi_v2.py` or `train_herald_regime_experiment.py`. **Zero training impact.**

---

## Finding 3 — COMPARISON PARTIALLY UNFAIR (HARDER EVAL YEARS IN PHASE 4E)

### Splits differ

| Country | Phase 4A eval years | Phase 4E eval years | New years |
|---------|---------------------|---------------------|-----------|
| NL | 2017–2024 | 2017–**2025** | +1 (2025) |
| BE | 2010–2020 | 2010–**2024** | +4 (2021–2024) |
| PT | 2010–2022 | 2010–**2024** | +2 (2023–2024) |

BE 2021–2024 and PT 2023–2024 are post-COVID years, harder to predict. Including them inflates aggregate WMAPE for Phase 4E.

Training window also wider in Phase 4E:
- NL: starts 2015 vs 2016 (+1 year)
- BE: starts 2007 vs 2009 (+2 years)
- PT: starts 2008 vs 2009 (+1 year)

Wider training should help, not hurt.

### Gap persists on common years

| Country | Phase 4A (common yrs) | Phase 4E-A (common yrs) | Delta |
|---------|----------------------|------------------------|-------|
| NL 2017–2024 | 0.058184 | 0.066305 | +13.9% |
| BE 2010–2020 | 0.070913 | 0.082228 | +15.9% |
| PT 2010–2022 | 0.169902 | 0.248367 | +46.2% |

The gap exists even on identical year ranges → attributable to leakage fix, not new years.

---

## Finding 4 — PHASE 4E-A2 VS PHASE 4E-A (OPEN QUESTION)

Phase 4E-A2 changes the feature/tensor protocol to approximate the old country-specific Phase 4A choices on the corrected European panel:

| Country | Phase 4E-A | Phase 4E-A2 | Config change |
|---------|-----------|------------|---------------|
| FR | 0.117044 | 0.103189 | baseline_annual → fr_side2 |
| NL | 0.103570 | 0.102759 | baseline_annual → current_clean + zero |
| BE | 0.154536 | 0.162253 | baseline_annual → side5_lag1_growth1y + zero |
| PT | 0.246521 | 0.234945 | baseline_annual → side5_lag1_growth1y + effectifs_lag1 |

FR, NL, and PT improve vs A. BE worsens.

Phase 4E-A used `baseline_annual` which appears to mean all 5 SIDE features (lag1–3, growth_1y, growth_2y). Phase 4E-A2 uses country-specific Phase 4A best configs:
- NL: `current_clean` drops lag2, lag3, growth_2y → keeps lag1 + growth_1y + stock
- BE: `side5_lag1_growth1y` drops lag2, lag3, growth_2y → keeps lag1 + growth_1y only

The BE A2 config uses fewer features than Phase 4E-A. **Dropping lag2/lag3 may hurt on the European panel** even though it helped on the leaky Phase 4A panel — in the leaky panel, growth_1y carried almost all signal, making other features redundant. Without leakage, lag2/lag3 carry real information.

This is a hypothesis, not confirmed. Requires a controlled ablation (Phase 4E-B with systematic feature policy sweep).

---

## Finding 5 — WRAPPER AND MODEL PARAMS CONSISTENT

Both wrappers call `train_herald_regime_experiment.main()`. Per metadata (NL A2 seed_42 vs Phase 4A NL best):

| Param | Phase 4A | Phase 4E-A2 NL | Phase 4E-A2 PT |
|-------|----------|----------------|----------------|
| mode | full | full | full |
| v7_variant | learned_regime_gate_sector_enhanced | same | same |
| regime_mode | no_regime | no_regime | no_regime |
| tensor_policy | zero | zero | **effectifs_lag1** |
| residual_shrinkage | train_opt | train_opt | train_opt |
| dropped_source_flags | flores/side/urssaf | same | same |

PT A2 is the only country where tensor_policy ≠ zero. PT uses `effectifs_lag1` with `qtensor_path = portugal_qtensor_births_cae_nuts3.csv`, column `births`. This is a births-proxy tensor (not employment), matching the Phase 4A `sector_births_lag1` config.

**Wrappers are consistent with configs. Model architecture unchanged.**

---

## Finding 6 — A10 SECTOR TENSOR

- Same columns and sectors in both pipelines
- **NL A10 in Phase 4E shorter**: 2015–2024 vs 2010–2024 in Phase 4. Missing 2010–2014.
  - Phase 4E NL eval starts 2017; training folds see A10 from 2015 onward. Not a problem.
- BE/PT A10 extended to cover new eval years — consistent with splits
- NL, BE, FR use `quarterly_tensor_policy = zero` in A2 → A10 unused
- PT uses `effectifs_lag1` with births tensor → A10 active for PT only

---

## Root Cause Classification

| Finding | Classification |
|---------|---------------|
| growth_1y leakage in Phase 4A | **BUG CONFIRMED — invalidates Phase 4A WMAPE** |
| Phase 4E evaluates harder post-COVID years | Methodological difference (expected, intended) |
| Phase 4E-A2 worse than Phase 4E-A for NL/BE | **Open hypothesis: fewer features without leakage hurts** |
| PT A2 better than PT A | Config improvement (births tensor helps PT) |
| feature_forecast_safe corrected | Methodological fix, no training effect |
| Wrapper/model params identical | No issue |
| NL A10 shorter in Phase 4E | Benign (eval range not affected) |

---

## Establishing the New Clean Baseline

Phase 4A must not appear in scientific claims. New baselines:

| Country | Phase 4E-A (all eval yrs) | Phase 4E-A2 (all eval yrs) | Recommended baseline |
|---------|--------------------------|---------------------------|----------------------|
| FR | 0.117044 ± 0.004437 | 0.103189 ± 0.008034 | Phase 4E-A2 |
| NL | 0.103570 ± 0.008227 | 0.102759 ± 0.006983 | Phase 4E-A2 (≈ empate, menor mean) |
| BE | 0.154536 ± 0.008184 | 0.162253 ± 0.008524 | Phase 4E-A |
| PT | 0.246521 ± 0.013689 | 0.234945 ± 0.009427 | Phase 4E-A2 (tensor helps) |

BE A2 regression needs a controlled feature-policy ablation before promoting `side5_lag1_growth1y` for Belgium.

---

## What to Do Before Phase 4E-B/C/D

### 1. Retire Phase 4A as performance baseline (immediate)
Use Phase 4E-A or Phase 4E-A2 (per-country, see table above).

### 2. Understand BE A2 regression
Why does dropping lag2/lag3 hurt Belgium in Phase 4E but helped in Phase 4A? Run a controlled ablation: Phase 4E panel + `side5_full` (all 5 features) versus `side5_lag1_growth1y`.

### 3. Investigate PT structural difficulty
PT remains structurally difficult after leakage removal. It has fewer zones (25), shorter history, and higher variance. This may require architecture tuning, not just feature policy changes.

### 4. Do not "fix" Phase 4A to recover old scores
Phase 4E is the correct pipeline. Phase 4A was wrong. The WMAPE drop is expected and correct.

---

## Recommendation: Launch Phase 4E-B/C/D?

**Phase 4E-B complete (2026-06-03).** See `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md`.

> **Phase 4E-B supersedes Phase 4E-A/A2 as the causal baseline.**  
> Phase 4E-A/A2 values in this document are historical intermediates only.

Per-country clean baselines established by Phase 4E-B (180/180 runs):

| Country | Phase 4E-B winner | WMAPE |
|---------|------------------|-------|
| FR | `b2_side2_zero` | 0.1031 ± 0.0084 |
| NL | `b0_baseline_annual` | 0.1017 ± 0.0075 |
| BE | `b3_current_clean_zero` | 0.1488 ± 0.0063 |
| PT | `b5_side2_emp_lag1` | 0.2286 ± 0.0148 |

Phase 4E-C must compare against these per-country winners.
