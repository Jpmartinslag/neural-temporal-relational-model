# Atlas IAT → HERALD Integration — Experiment Plan

**Date:** 2026-05-18  
**Status:** Planning only — no training runs here  
**Purpose:** Define the experimental roadmap for integrating Atlas/IAT-derived features into HERALD, starting from the current SIDE5-only baseline.

---

## 0. Starting Point

**Frente A (active):** HERALD with a single dataset (SIDE), 5 features:
- `side_lag_1`, `side_lag_2`, `side_lag_3`, `growth_1y`, `growth_2y`
- Aggregation: ZE2020 × A10 × year
- No manual flags, no external data
- Goal: clean baseline, minimal noise, maximum robustness

**Frente B (this plan):** Atlas/IAT audit and preparation.  
Integration experiments are planned here but **will not be run until Frente A baseline is stable and validated.**

---

## 1. Methodological Separation

| System | Role | Unit | Time |
|---|---|---|---|
| HERALD | Territorial forecast | ZE2020 × A10 × year | Dynamic (2012–2025) |
| Atlas/IAT | Economic intelligence | Establishment × sector × product | Static (snapshot 2022) |
| Atlas/IAT re-aggregated | Derived features | ZE2020 × A10 × year (ex-ante) | Dynamic (where updatable) |

**Correct language:**
- "Atlas/IAT-derived features re-aggregated by ZE2020"
- "HERALD uses a territorial layer derived from Atlas/IAT"
- NOT: "Atlas/IAT uses ZE2020" — the original system does not

---

## 2. Prerequisites Before Any Integration Run

Before running any experiment from Phase 3 onward:

1. **DB restored** (`iat_restore` database operational)
2. **Coverage audit completed:**
   - % establishments with valid `insee_code`
   - % communes covered by `commune_to_ze2020_2026.csv`
   - ZE2020 coverage density map produced
3. **Temporal validity confirmed** for each candidate feature
4. **Baseline HERALD SIDE5 stable:**
   - WMAPE not sensitive to seed variance
   - 2021 instability understood and documented
   - Ablation battery complete

---

## 3. Experiment Sequence

### Exp 0 — HERALD SIDE5 baseline (Frente A)
**Already running / in progress.**

Metrics to lock in before proceeding:
- Overall WMAPE (mean)
- WMAPE 2021 (instability year)
- WMAPE 2025 (most recent)
- WMAPE by A10 sector
- Seed variance (std over ≥5 seeds)
- Large ZE vs. small ZE performance gap

---

### Exp 1 — HERALD + Atlas structural (static, low leakage)

**Features to add (Category A, static):**
- `avg_product_complexity` (PCI, Harvard 2018 vintage)
- `nace_io_linkage_strength` (IO coefficients, static)
- `product_space_density` (proximity × RCA_t2)

**Leakage check:** PCI and IO are structural/static. Use T-2 RCA from Douanes. Safe for all HERALD years.

**Hypothesis:** Structural complexity and IO linkages add low-noise information about sector productive capacity.

**Pass criterion:** WMAPE does not increase by more than 0.5pp versus Exp 0. No new 2021 instability introduced.

---

### Exp 2 — HERALD + Establishment stock (dynamic, T-1)

**Features to add (Category A, dynamic):**
- `n_active_establishments_iat` (from SIRENE T-1)
- `sector_diversity_naf` (Shannon entropy, from SIRENE T-1)
- `sector_concentration_hhi` (from SIRENE T-1)
- `workforce_per_estab` (from SIRENE T-1, if available)

**Leakage check:** Use SIRENE stock from year T-1. Reconstruct from historical SIRENE snapshots for backtest 2012–2023.

**Hypothesis:** Absolute establishment stock and diversity complement SIDE creation data.  
**Risk:** High correlation with SIDE target → potential redundancy or noise amplification.

**Pass criterion:** WMAPE improvement ≥ 0.3pp versus Exp 1, OR no degradation + interpretability gain documented.

---

### Exp 3 — HERALD + Trade features (dynamic, T-2)

**Features to add (Category A, dynamic):**
- `export_rca_strength` (RCA > 1 product count, from Douanes T-2)
- `import_dependency_score` (import/export ratio, from Douanes T-2)
- `product_space_density` (updated with T-2 RCA, replacing static version)

**Leakage check:** T-2 Douanes data. For year Y prediction: use Y-2 trade data.

**Note:** ZE2020-native RCA requires department → ZE2020 aggregation (population-weighted or establishment-weighted).

**Hypothesis:** Export capacity and import dependency signal territorial economic openness and structural resilience.

---

### Exp 4 — HERALD + NAF proximity (structural)

**Features to add (Category B):**
- `mean_naf_proximity` within ZE2020 (how complementary is local sector mix)
- `sector_green_potential` (if green scores confirmed)

**Leakage check:** NAF proximity matrix is static structural. Sector presence uses T-1 SIRENE.

**Hypothesis:** Complementary sector mix → more resilient economic zone → smoother establishment creation growth.

---

### Exp 5 — HERALD + IO-based features (static)

**Features to add:**
- `nace_io_linkage_strength` (sum of IO coefficients for sector pairs co-present in ZE2020)
- Supplier chain exposure indicator

**Leakage check:** IO coefficients are static. Sector presence from T-1 SIRENE.

**Hypothesis:** Zones with strong input-output linkages (local supply chains) show different creation dynamics than purely export-oriented zones.

---

### Exp 6 — HERALD + Rankings (structural)

**Features to add (Category B/C):**
- `avg_product_resilience` (static resilience scores)
- `basic_need_coverage` (static necessity scores)

**Note:** Green and basic need scores are not yet confirmed sources. Use only after source validation.

**Hypothesis:** Zones producing basic necessities or resilient products show more stable establishment creation patterns.

---

### Exp 7 — Minimum robust combination

After Exps 1–6 are evaluated, identify the **minimum combination of Atlas features that:**
1. Does not worsen WMAPE versus Exp 0
2. Improves at least one of: WMAPE 2021, large ZE performance, interpretability
3. Satisfies all leakage rules
4. Is annualisable from open sources

Expected candidate set: PCI + IO coefficients + sector diversity (T-1) + export RCA (T-2).

---

### Exp 8 — Ablations by block

For each feature block that enters the minimum combination:
- Remove it and measure WMAPE delta
- Identify true signal contributors vs. redundant features
- Document which blocks are noise vs. signal

---

## 4. Metrics

All experiments evaluated on:

| Metric | Description |
|---|---|
| `wmape_overall` | Weighted Mean Absolute Percentage Error across all ZE2020 × A10 × year |
| `wmape_2021` | WMAPE restricted to year 2021 (instability probe) |
| `wmape_2025` | WMAPE restricted to year 2025 (latest year) |
| `wmape_by_a10` | WMAPE per A10 sector (identify which sectors benefit or suffer) |
| `seed_std` | Standard deviation of WMAPE over ≥5 random seeds (stability) |
| `wmape_large_ze` | WMAPE for ZE2020 with > median establishment count |
| `wmape_small_ze` | WMAPE for ZE2020 with < median establishment count |
| `n_features` | Total feature count (parsimony tracker) |

---

## 5. Pass/Fail Criteria

| Condition | Action |
|---|---|
| WMAPE increases by > 0.5pp | Reject feature block, document why |
| Seed variance increases | Investigate which feature drives instability |
| 2021 WMAPE worsens | Flag leakage risk, audit feature vintage |
| Feature corr > 0.9 with SIDE lag_1 | Mark as redundant, drop |
| WMAPE improves ≥ 0.5pp, stable seeds | Accept feature block |
| WMAPE improves ≥ 0.3pp, interpretability gains | Accept with documentation |
| No WMAPE improvement, clear interpretability gain | Accept as recommendation layer only (Category C) |

---

## 6. Product Vision

The final product is not just a lower WMAPE number.

**HERALD output (from SIDE5 model):**
- Zone X: +12% establishment creation expected in sector A10-G (trade)
- Zone Y: -5% expected in A10-C (industry)
- Zone Z: uncertain signal, high variance

**Atlas/IAT dynamic layer adds:**

For Zone X (trade expansion predicted):
> "Current export RCA: 1.3 in HS4-8471 (computers). IO linkage: strong wholesale-logistics chain. Sector diversity: high (Shannon 2.1). Resilience: medium. Recommended: attract logistics firms to serve existing trade cluster. Green opportunity: moderate (2 green products in current basket)."

For Zone Y (industry contraction predicted):
> "Sector concentration HHI: 0.6 (dominated by manufacture A10-C). Product space density: low (few nearby products). IO exposure: high dependency on national supply chain. Resilience: low. Recommended: support diversification toward A10-M (professional services) or A10-J (ICT)."

**This transforms a territorial forecast into an economic recommendation, without claiming causality.**

---

## 7. Prohibited Language and Methods

Throughout all experiments:

- Do NOT call Atlas-derived features "causal variables"
- Do NOT call HERALD output "confirmed economic policy" — it is a **forecast with uncertainty**
- Do NOT use 2022 Atlas snapshot as feature for year ≤ 2021 backtests without reconstruction
- Do NOT use manual crisis/rebound flags
- Do NOT call nowcast (in-sample fit) a forecast
- Do NOT claim that Atlas/IAT methodology was designed for ZE2020 — it was not; we adapted it

---

## 8. Files and Versioning

All outputs versioned:
- `atlas_iat_ze2020_static_features_v0.csv` → first static prototype
- `atlas_iat_ze2020_dynamic_features_v0.csv` → first dynamic panel
- Increment to v1, v2 etc. on significant revision

No overwriting of existing files.  
No push to remote until Frente A is complete and validated.
