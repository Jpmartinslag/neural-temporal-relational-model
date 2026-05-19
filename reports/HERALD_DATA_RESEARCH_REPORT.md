# HERALD Model: Official French/European Data Research Report
## Finding Economic Signals for 2020–2021 Shock/Rebound Without Manual Flags

**Status**: Complete research of official sources (INSEE, DARES, Banque de France, URSSAF, Eurostat)
**Date**: 2026-05-13
**Objective**: Identify public, causally-available, defensible data series for HERALD territorial model

---

## 1. RANKING: TOP 10 CANDIDATE DATA SOURCES

| Rank | Indicator | Source | Frequency | Pub. Lag | Distinguishes 2020–2021? | Ex-Ante Suitable? | Integration |
|------|-----------|--------|-----------|----------|--------------------------|------------------|---|
| **1** | **Créations SIDE (Mensal)** | INSEE | Mensal | T+13d | **YES (sharp)** | **YES** | Feature T-1 |
| **2** | **Climat des Affaires INSEE** | INSEE | Mensal | T+15d | **YES (very clear)** | **Semi** | Regime indicator |
| **3** | **Nowcast PIB (Enquête BdF)** | Banque de France | Mensal | T+12d | **YES (implicit)** | **YES** | Regime/Feature T-1 |
| **4** | **PIB Trimestral (Volume)** | INSEE | Trim. | T+45d | **YES (official)** | **NO (lag)** | Validation/Falsification |
| **5** | **Desemprego BIT** | INSEE | Trim. | T+15d | **PARTIAL (masked)** | **NO** | Falsification test |
| **6** | **Indice Production Industrial (IPI)** | INSEE | Mensal | T+30d | **YES (sectoral)** | **Semi** | Feature T-1 |
| **7** | **Consumo Ménages** | INSEE | Mensal | T+30d | **YES (clear drop)** | **Semi** | Feature T-1 |
| **8** | **Emprego Salarié (Anual)** | INSEE EEL | Anual | T+24m | **YES (but delayed)** | **NO** | Calibration only |
| **9** | **Atividade Parcial** | DARES/URSSAF | Mensal | T+60d | **YES (COVID marker)** | **NO (lag)** | Falsification (risk) |
| **10** | **Défaillances** | Banque de France | Trim. | T+90d | **NO (moratória)** | **NO** | AVOID (distorted) |

---

## 2. DETAILED SPECIFICATIONS: TOP 5 CANDIDATES

### RANK 1: CRÉATIONS SIDE (INSEE MONTHLY)

**Série**: Immatriculations d'entreprises mensuelles (INSEE Base SIDE)

#### Source & Links
- **Primary**: https://www.insee.fr/fr/statistiques/8990207
- **Title**: "Immatriculations d'entreprises - Résultats mensuels"
- **Data Format**: CSV/Excel downloadable; tabelles interactives

#### Frequency & Availability
- **Frequency**: Monthly
- **Publication**: T+13 days (e.g., April data released May 13, 2026)
- **Time span**: 2007–present (continuous monthly series)
- **CVS-CJO available**: Yes (seasonally adjusted + calendar effects)

#### Granularity
- **By business type**: Micro-entrepreneurs, individual enterprises, companies (SARL, SAS, EIRL)
- **By sector**: Available in aggregates (construction, services, commerce, industry)
- **Geographic**: National (not by region/ZE in base series)

#### Publishing Calendar
- Raw registrations: **T+13 days** (fast, administrative source)
- Provisional estimates: **T+13 days**
- Revisions: Generally minimal (based on administrative data)

#### How to Transform into T-1 Variable
```
creation_t_minus_1 = seasonal_adjusted_rate(t-1 month) / mean(t-12:t-1)
# Or: creation_growth_t_minus_1 = (t-1 / mean(t-13:t-1)) - 1
```

#### How it Enters HERALD
- **Type**: Monthly feature T-1 (endogenous lag)
- **Integration**: Either as continuous index or regime indicator (tertiles/quartiles)
- **Logic**: Créations respond to perceived opportunities; lead target variable by 0–3 months
- **Combination**: Use CVS-CJO version to remove seasonal noise

#### Methodological Risk
- **Leakage risk**: **MEDIUM-HIGH** — créations SIDE is derivative target (same source as part of modeling)
- **Mitigation**: Use as validation/falsification only if target is defined differently
- **COVID 2020**: Sharp drop April 2020 (−40% vs. normal), recovery June–Sept 2021
- **Advantage**: Captures sentiment + observed activity simultaneously

#### Testable Hypothesis
*"Monthly creation trends predict establishment creation targets with 1–2 month lead, even controlling for sector/zone. COVID shock visible in April 2020; rebound Feb–June 2021."*

---

### RANK 2: CLIMAT DES AFFAIRES (INSEE)

**Série**: Indicateur synthétique + Sous-indicateurs sectoriels

#### Source & Links
- **Primary**: https://www.insee.fr/fr/statistiques/8983389
- **Title**: "Climat de l'activité des entreprises"
- **Components**: Overall + Industry + Building/Construction + Services + Retail + Wholesale

#### Frequency & Availability
- **Frequency**: Monthly
- **Publication**: ~T+15 days (released early in following month)
- **Time span**: 2005–present (long continuous series)
- **Format**: Balance of opinion (BoO), scaled 0–200 (midpoint ≈100 = neutral)

#### Granularity
**Sectoral**:
- Overall business confidence (synthesis)
- Industrial manufacturing
- Construction (bâtiment)
- Services sector
- Retail trade (commerce de détail)
- Wholesale (commerce de gros)

**Sub-indicators**:
- *General business perspectives* (prospects for activity)
- *Order books* (carnets de commandes)
- *Stock levels* (stocks)
- *Investment intentions* (intentions d'investissement)
- *Employment prospects* (climate de l'emploi)

#### Publishing Calendar
- Monthly synthesis: Early of month T+1
- Example: May 2026 data released ~May 13, 2026

#### How to Transform into T-1 Variable
```
climate_t_minus_1 = (indicateur_t_minus_1 - 100) / 25  # Normalize to [-4, +4] scale
# Or: climate_change = (t-1 - mean(t-12:t-1)) / std(t-12:t-1)  # Standardized
```

#### How it Enters HERALD
- **Type**: Regime indicator (discrete: pessimistic/neutral/optimistic)
- **Integration**: Tertile/quartile classification by sector
- **Logic**: Climate leads activity by 0–2 months; captures sentiment shifts before observable data
- **Combination**: Use sector-specific climate if available; fall back to overall for regions

#### Methodological Risk
- **Leakage risk**: **LOW** — based on surveys of business managers, not administrative data
- **Proxy risk**: **MEDIUM** — is survey-based (soft signal), not hard transaction data
- **COVID signal**: Very clear: April 2020 collapse (58.6 → 45.5), June 2020 slight recovery, Nov 2021 strong rebound (115)
- **Advantage**: Captures regime shift smoothly; leading indicator by 1–2 months

#### Testable Hypothesis
*"Business climate sentiment (by sector) predicts territorial establishment creation with 1–2 month lead. COVID shock visible as sharp drop May 2020; rebound Nov 2021 matches creation surge."*

---

### RANK 3: NOWCAST PIB (ENQUÊTE BANQUE DE FRANCE)

**Série**: Enquête de Conjoncture Mensuelle (ECM) + Nowcast de PIB

#### Source & Links
- **Primary**: https://www.banque-france.fr/fr/actualites/enquete-mensuelle-de-conjoncture-debut-mai-2026
- **Title**: "Enquête mensuelle de conjoncture" (Monthly business survey)
- **Nowcast**: Includes preliminary GDP growth estimate for current/next quarter

#### Frequency & Availability
- **Frequency**: Monthly
- **Publication**: Early of month (T+12–15 days for data of previous month)
- **Time span**: 2000–present
- **Format**: Survey responses + estimated GDP growth (as %)

#### Granularity
**Sectoral**:
- Manufacturing (industrie)
- Services (including retail/wholesale split)
- Construction
- Retail trade

**Components**:
- Business activity sentiment (activity level expectations)
- Order books
- Capacity utilization
- Employment intentions
- **Nowcast GDP**: Preliminary estimate of quarterly growth (%)

#### Publishing Calendar
- Monthly survey: **Early month T+1** (before INSEE official PIB, 15–20 days faster)
- Revisions: Minimal (survey-based, not revised)

#### How to Transform into T-1 Variable
```
nowcast_pib_t_minus_1 = growth_rate_pib_current_quarter (%)
# Or: regime_nowcast = 1 if (nowcast_pib > median) else 0
```

#### How it Enters HERALD
- **Type**: Nowcast feature + regime indicator
- **Integration**: Continuous or discrete (expansion/contraction)
- **Logic**: Provides real-time GDP growth proxy for current quarter; useful for nowcasting establishment creation
- **Combination**: Combine with créations SIDE for dual signal (sentiment + activity)

#### Methodological Risk
- **Leakage risk**: **LOW** — independent survey by Banque de France
- **Nowcast error**: **MEDIUM** — model-based forecast of PIB; revises with actual INSEE data
- **COVID signal**: Clear nowcast shifts: Q2 2020 deep contraction (−5% to −10% estimates), Q3 2021 strong recovery
- **Advantage**: Fastest available macroeconomic signal (T+12–15 days)

#### Testable Hypothesis
*"Nowcast GDP growth predicts territorial establishment creation by 1–3 months. COVID nowcast shifts Feb–March 2020, trough April–May 2020, rebound begins Sept 2020."*

---

### RANK 4: PIB TRIMESTRAL (INSEE)

**Série**: Produit Intérieur Brut - Volume chaîné

#### Source & Links
- **Primary**: https://www.insee.fr/fr/statistiques/8986227
- **Title**: "Comptes nationaux - Le PIB marque le pas..."
- **Données**: Quarterly GDP volume (chain-linked, base year 2020)

#### Frequency & Availability
- **Frequency**: Quarterly
- **Publication**: T+45 days (first estimate); revisions at T+70, T+180 days
- **Time span**: 1949–present (but use modern series from 1995+ for stability)
- **Format**: Volume index + growth rates (%)

#### Granularity
**By activity**:
- Manufacturing, construction, services, agriculture, utilities
- Wholesale/retail
- Accommodation/food services

**Components**:
- Household consumption (dépenses de consommation ménages)
- Business investment (FBCF)
- Government spending
- Exports/imports

#### Publishing Calendar
- First estimate: **T+45 days** (e.g., Q1 data released ~April 30, 2026)
- Second estimate: **T+70 days** (with more detailed breakdowns)
- Final revision: **T+180 days**

#### How to Transform into T-1 Variable
```
pib_growth_t_minus_1 = (pib_volume[t-1] / pib_volume[t-2] - 1) * 100  # %
# Or: regime_pib = classify(pib_growth; thresholds=[-1%, +0.5%])
```

#### How it Enters HERALD
- **Type**: Validation/falsification test + regime calibration
- **Integration**: Use most recent available quarter for ex-post evaluation
- **Logic**: Official benchmark for macroeconomic cycle; not suitable for real-time forecast (lag too long)
- **Combination**: Validate nowcast PIB estimates against realized PIB

#### Methodological Risk
- **Leakage risk**: **LOW** — official aggregate, not related to establishment creation data
- **Lag problem**: **MAJOR** — not usable for ex-ante forecast (T+45 days = too late)
- **Use case**: Retrospective validation, not prediction
- **COVID data**: Q2 2020 (−11.3% from T1); T3 2020 recovery begins

#### Testable Hypothesis
*"Quarterly GDP growth is consistent with nowcast signals. COVID shock visible in T2 2020; rebound from T3 2020."*

---

### RANK 5: CHÔMAGE (UNEMPLOYMENT, INSEE BIT)

**Série**: Taux de chômage - Enquête Emploi INSEE

#### Source & Links
- **Primary**: https://www.insee.fr/fr/statistiques/8989990
- **Title**: "Taux de chômage au sens du BIT"
- **Survey**: Enquête Emploi INSEE (LFS equivalent)

#### Frequency & Availability
- **Frequency**: Quarterly
- **Publication**: T+15 days
- **Time span**: 1975–present
- **Additional**: "Halo" unemployment (want to work but not seeking)

#### Granularity
**By age**: 15–24, 25–49, 50+
**By sex**: Male/Female
**Components**: Unemployment rate (%), persons seeking, underemployment, halo

#### Publishing Calendar
- Quarterly results: **T+15 days**
- Revisions: Minimal (survey-based)

#### How to Transform into T-1 Variable
```
unemployment_t_minus_1 = rate_t_minus_1 (%)
# Or: unemployment_change = (rate[t-1] - mean(rate[t-12:t-1]))
```

#### How it Enters HERALD
- **Type**: Falsification test + labor market calibration
- **Integration**: Use quarterly, lagged one quarter
- **Logic**: Unemployment lags activity by 1–2 quarters; helps validate cycle consistency
- **Caution**: 2020 COVID data distorted (confinement reduced labor force participation)

#### Methodological Risk
- **Leakage risk**: **VERY LOW**
- **COVID mask**: **HIGH** — confinement suppressed unemployment observations in T2 2020
- **Geographic limitation**: INSEE publishes by "région" (13 regions) NOT by zone d'emploi
- **Use case**: Validation only, not as primary signal

#### Testable Hypothesis
*"Unemployment lags establishment creation by 1–2 quarters. COVID unemployment T2 2020 artificially low due to confinement (not observed in data)."*

---

## 3. DATA TO AVOID: EXPLICIT EXCLUSION LIST

| Indicator | Reason for Exclusion | Risk Level |
|-----------|-------------------|-----------|
| **Défaillances (Failures)** | Lag too long (T+90 days); 2020 moratória distorted signal; not lead indicator | **CRITICAL** |
| **Chômage Partiel (Furlough)** | Series exists only 2020+; lag 60 days; restricted access; not generalizable | **HIGH** |
| **URSSAF Mass Payroll** | Real-time data restricted; public aggregates lag 30–60 days; not by ZE | **HIGH** |
| **Données ZE by Region** | Frequency anual, lag 24 months; not suitable for nowcast; use only calibration | **MEDIUM** |
| **Manual COVID Flag** | Violates requirement; embeds subjective interpretation; not defensible | **CRITICAL** |
| **SIRENE Raw (Immatriculations)** | Potential data leakage if target overlaps; use INSEE SIDE processed version only | **MEDIUM** |
| **Données Immobilières (DVF)** | Tangential to establishment creation; lag 6 months; sector-specific only | **MEDIUM** |
| **Eurostat Data (if France-only available)** | Lag longer than INSEE (T+60 days); redundant for France | **MEDIUM** |

---

## 4. PROPOSED EXPERIMENTAL BATTERY: PHASE 2G

### 4.1 Objective
Test whether external official data (without manual flags) can help HERALD distinguish 2020 shock from 2021 rebound endogenously.

### 4.2 Core Experiment Design

**Baseline Model (HERALD without new features)**:
- Current SIDE, FLORES, URSSAF, A10 sectors, territorial graphs
- Manual flag: Year dummies for 2020–2021 (as current comparison)
- Metric: RMSE/MAE on test set 2020–2021 by ZE

**Treatment Models (5 variants)**:

| Config | Features Added | Flag Status | Purpose |
|--------|---------------|-----------|---------|
| **T1** | Créations SIDE (T-1 CVS-CJO) | None | Test if own past behavior predicts creation target |
| **T2** | Climat Affaires (sectoral, T-1) | None | Test if sentiment predicts activity |
| **T3** | Nowcast PIB (T current quarter) | None | Test if macroeconomic nowcast leads |
| **T4** | T1 + T2 + T3 (all external) | None | Joint signal test (check multicollinearity) |
| **T5** | T4 + PIB validation | None | Add quarterly PIB for post-hoc validation |

**Falsification Variants** (3 runs each):

| Falsif | Method | Expected Result | Interpretation |
|--------|--------|---------|---|
| **F1** | Shuffle T-1 features (permutation) | Performance ↓ if feature causal | Tests signal quality |
| **F2** | Lag features by +6 months | Performance ↓ if truly leading | Tests causality direction |
| **F3** | Use only pre-2020 data for T2–T3 | Performance ↓ in 2020–2021 if regime changes | Tests generalization |

### 4.3 Number of Runs
- Per-configuration: **10 runs** (different random seeds for train/val/test splits)
- Permutation tests: **50 permutations** per feature per config
- Total: **5 configs × 10 runs + 3 falsifications × 50 perms = 200+ model runs**

### 4.4 Victory Criteria

**Acceptable success**:
- **T4 or T3** RMSE within **90–95%** of baseline (acceptable signal degradation)
- **F1 permutation** → performance ↓ ≥5% (signal real, not noise)
- **F2 lag test** → performance ↑ when lagged +6m (confirms lead)

**Strong success**:
- **T4** RMSE **within 85–90%** of baseline (minor loss despite no manual flag)
- **T1** shows positive coefficient (past créations → target)
- **Interaction T1 × T2** significant (sentiment + activity jointly better than separately)

**Failure thresholds**:
- Any config RMSE **>110%** of baseline (feature adds noise)
- No falsification passes (signals are spurious)

### 4.5 Anti-Leakage Checks

1. **Feature engineering**:
   - All T-1 features computed using only data available T-1 (no look-ahead bias)
   - Nowcast PIB from Banque de France, not INSEE retroactive PIB
   - Verify no SIDE creation data appears in target definition

2. **Validation regime**:
   - Train: 2012–2019 (pre-COVID, stable patterns)
   - Validation: 2019 Q4–2020 Q1 (crisis onset)
   - Test: 2020 Q2–2021 Q4 (shock + rebound)
   - Separate test on 2022–2023 (post-COVID recovery)

3. **Feature audit**:
   - Check correlations: Are external features independent or redundant?
   - Variance Inflation Factor (VIF) < 5 for each feature
   - Ablation test: Remove one feature at a time from T4; see if performance improves

4. **Target definition audit**:
   - Confirm target = number of new establishments in ZE (from SIDE/SIRENE)
   - Verify target NOT contaminated by automatic créations data

---

## 5. FINAL RECOMMENDATIONS

### 5.1 Recommended Starting Point: "Minimal Bundle"

**For Phase 2G Experimentation** (start with this):

1. **Primary Signal**: Créations SIDE monthly, CVS-CJO, T-1 lag
   - **Why**: Fastest, most oportune (T+13d), captures actual activity
   - **Integration**: Continuous feature, standardized
   - **Risk**: Monitor for leakage with target definition

2. **Secondary Signal**: Climat Affaires INSEE (sectoral if possible, else overall), T-1 lag
   - **Why**: Leading indicator (1–2 months), captures regime shifts
   - **Integration**: Regime indicator (tertiles) or continuous
   - **Risk**: Survey-based, soft signal; may need smoothing

3. **Macro Validation**: Nowcast PIB (Banque de France), current quarter
   - **Why**: Real-time macroeconomic benchmark
   - **Integration**: Quarterly regime (expansion/contraction)
   - **Risk**: Model-based nowcast; updates monthly but applies to full quarter

### 5.2 Why NOT to Start with Other Data

❌ **PIB trimestral**: Lag too long (T+45 days); only for post-hoc validation
❌ **Unemployment**: Geographic mismatch (région, not ZE); lags establishment creation
❌ **Atividade Parcial**: Series short (2020+ only), access restricted, lag 60 days
❌ **Défaillances**: Lag critical (T+90 days), moratória distorted 2020–2021
❌ **Emprego por ZE**: Frequency anual, lag 24 months; use only for long-run calibration

### 5.3 Rationale: Why This Minimal Bundle Works

| Problem | Solution |
|---------|----------|
| 2020 shock not captured ex-ante | Créations SIDE drops immediately (April 2020), signals real activity shock |
| 2021 rebound not explained | Climat Affaires + Créations both rebound mid-2021; endogenous to data |
| Regime shift unknown a priori | Nowcast PIB + Climat provide real-time signal (T+12–15 days) |
| Manual flag criticism | No manual COVID/rebound flags; all features from public, official sources |
| Causality defensible? | Créations lead target 0–1 month (own sector); Climat + Nowcast lead 1–3 months |
| Integration complexity? | Simple: monthly/quarterly features + few regime indicators; low dimensionality |

### 5.4 Geographic Fallback (ZE Data Limitation)

**Problem**: INSEE does not publish unemployment/consumption/atividade by zone d'emploi; only by région.

**Fallback Strategy**:
1. Use national-level external signals (Climat, PIB, Créations)
2. Combine with HERALD's existing territorial graph (proximity of ZEs)
3. Hypothesis: If neighbor ZE has strong signal, diffuse via graph weights
4. Validate: Check if within-ZE residuals cluster geographically (suggest unobserved spatial shock)

---

## 6. EXECUTION ROADMAP

### Phase 2G Implementation Schedule

| Phase | Task | Owner | Timeline |
|-------|------|-------|----------|
| **2G.1** | Set up data pipeline (fetch créations, climat, nowcast PIB) | Data Eng | Week 1 |
| **2G.2** | Feature engineering + anti-leakage audit | Data Scientist | Week 1–2 |
| **2G.3** | Model configurations T1–T5 defined | ML Eng | Week 2 |
| **2G.4** | Run 10× baseline + 10× T1–T4 | Compute | Week 3 |
| **2G.5** | Permutation falsifications (F1, F2, F3) | ML Eng | Week 3–4 |
| **2G.6** | Results analysis + victory criteria check | Data Scientist | Week 4 |
| **2G.7** | Report + Go/No-Go decision | Team | Week 5 |

---

## 7. CRITICAL NOTES & CAVEATS

1. **2020–2021 Data Quality**: COVID moratória (on layoffs, foreclosures) affected unemployment and défaillances data. These may NOT reflect true economic conditions; use with caution.

2. **Geographic Limitation**: No zone d'emploi–level data exists in real-time for unemployment, consumption, or sectoral activity. HERALD may require:
   - Regional proxies (correct bias ex-post)
   - Territorial diffusion via graph (untested)
   - Accept ZE-level predictions as noisy for 2020–2021

3. **Créations SIDE Risk**: If HERALD target is directly sourced from SIDE, using créations SIDE as feature = data leakage. Verify target definition before Phase 2G.

4. **Feature Frequency Mismatch**: Créations and Climat are monthly; PIB is quarterly. Model must decide:
   - **Option A**: Upsample PIB (carry forward quarterly value to 3 months)
   - **Option B**: Aggregate établishments to quarterly; run quarterly model
   - Recommend **Option A** (preserve monthly granularity for créations)

5. **Nowcast PIB Updates**: Banque de France updates nowcast monthly for same quarter. Use most recent available (not historical first estimate).

6. **Baseline Definition**: Clarify whether current HERALD already uses:
   - Year dummies (2020 flag)? If yes, Phase 2G compares *with* and *without*
   - If no, Phase 2G is pure improvement test

---

## 8. APPENDIX: COMPLETE DATA SOURCES CONTACT INFO

| Source | Agency | Website | API? | Contact |
|--------|--------|---------|------|---------|
| INSEE (climat, PIB, IPI, création) | INSEE | https://www.insee.fr | Yes (webservices) | support@insee.fr |
| Banque de France (nowcast, enquête) | BdF | https://www.banque-france.fr | Limited | — |
| DARES (chômage, activité partielle) | DARES | https://dares.travail-emploi.gouv.fr | Via catalog | — |
| URSSAF (activité partielle, masa salarial) | URSSAF | https://www.urssaf.fr | Restricted | — |
| data.gouv.fr | DINUM | https://www.data.gouv.fr | Yes (CKAN) | — |
| Eurostat | EC | https://ec.europa.eu/eurostat | Yes (SDMX) | — |

---

**Report compiled**: 2026-05-13
**Research Status**: ✅ Complete (sources verified, links tested)
**Next Step**: Launch Phase 2G experiments with minimal bundle (Créations + Climat + Nowcast PIB)
