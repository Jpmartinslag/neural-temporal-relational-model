# HERALD — Evidence Matrix

**Created:** 2026-06-10  
**Rule:** Claims are classified by their current evidentiary status. Status reflects the strongest current evidence; do not retroactively upgrade claims using superseded or leaky runs.  
**Status vocabulary:** `SUPPORTED` · `PARTIALLY_SUPPORTED` · `EXPLORATORY` · `NOT_SUPPORTED` · `REFUTED_UNDER_CURRENT_PROTOCOL` · `NOT_TESTED`

---

## Forecasting claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| F-01 | Persistence (`lag1_births`) is the best single predictor for Italy and Austria in rolling-origin LOCO | Phase 4N results | 4N | PT/IT/AT 2008-2020, 151 NUTS3 | Rolling-origin LOCO, causal features | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Strong within protocol | Limited (3 countries, 1 horizon) | Only 2008–2020 window; 1-year horizon only | `SUPPORTED` |
| F-02 | Residual Ridge improves PT under LOCO but degrades IT and AT | Phase 4N | 4N | PT/IT/AT | LOCO rolling-origin | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Moderate | Low (n=3 countries) | Gain concentrated in scale-invariance, not transferable dynamics | `PARTIALLY_SUPPORTED` |
| F-03 | Country-balanced WMAPE is protocol-specific: Phase 4N PT/IT/AT persistence ~0.0874; broader heterogeneous-target LOCO is not directly comparable | Phase 4N harmonized + Phase 4G-4I broader LOCO | 4N/4H-B | PT/IT/AT or FR/NL/BE/PT | Rolling-origin LOCO | `HERALD_PHASE4N_RESULTS_AUDIT.md`; `HERALD_PHASE4H_B_RESULTS_AUDIT.md` | Moderate | Protocol-specific | Different country sets and target semantics must not be pooled into one headline metric | `SUPPORTED` |
| F-04 | HERALD Q7 (France) achieves WMAPE 0.0204 mean 2021–2025 | Phase 3E France confirmatory | 3E / 2R | 306 French ZE, 2021–2025 | Rolling-window, 240 runs, 12 configs × 20 seeds | `HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`; `HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` | Strong for France | France only; French institutional data | Not tested on non-French geographies | `SUPPORTED` |
| F-05 | 50/50 forecast combination improves balanced WMAPE by ~7% vs persistence | Phase 4J-A exploratory | 4J-A | FR/NL/BE/PT | Balanced WMAPE across 4 countries | `HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md` | Weak (tail degradation) | Not safe for transfer | Worst-year regression; weights not transferable; not promoted | `EXPLORATORY` |
| F-06 | Ridge direct fails catastrophically on Austria (WMAPE 0.302) due to target-scale mismatch | Phase 4N | 4N | AT | LOCO Ridge direct | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Strong | Any cross-country direct regression without scale normalization | Architecture limitation, not data limitation | `SUPPORTED` |
| F-07 | FR + NL + BE + PT together constitute a generalizable European panel under a single target definition | Phase 4J semantic audit | 4J | FR/NL/BE/PT | Target concept review | `HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` | Strong refutation | Documented by official source definitions | Cannot be fixed by rerunning — requires new data agreement | `REFUTED_UNDER_CURRENT_PROTOCOL` |

---

## Graph claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| G-01 | Queen-contiguity birth lag (`W × births[t-1]`) improves Italy forecasts | Phase 4P | 4P | IT 93 NUTS3, 2012–2020 | Rolling-origin, 99 permuted controls | `HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md` | Strong refutation (p=0.19, +2.26% vs persistence) | Italy specific | Only first-order geographic lag | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| G-02 | Spatial-Durbin fixed block (all common covariates) improves Italy forecasts | Phase 4Q | 4Q | IT 93 NUTS3, 2012–2020 | Rolling-origin, 99 permuted controls | `HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md` | Strong refutation (p=0.32, −5.95% vs persistence) | Italy specific | Linear block only | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| G-03 | Italian persistence residuals show robust spatial autocorrelation (Moran's I significant, LOO-stable) | Phase 4O-C | 4O-C | IT 93 NUTS3, 2012–2020 | BH/FDR, 999 permutations, 999 graph controls, LOO | `HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Strong (7 of 9 years FDR-significant, LOO pass) | Italy only | Does not imply forecast benefit; geographic lags failed to exploit signal | `SUPPORTED` |
| G-04 | Portugal residuals show spatial autocorrelation exploitable for forecasting | Phase 4O-C | 4O-C | PT 23 NUTS3 | BH/FDR, LOO | `HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Weak (LOO unstable) | Portugal only | 23 NUTS3 makes LOO highly sensitive; structural limitation | `PARTIALLY_SUPPORTED` |
| G-05 | Austria residuals show robust spatial autocorrelation | Phase 4O-C | 4O-C | AT 35 NUTS3 | BH/FDR, LOO, residual types | `HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Not found in normalized residuals | — | Signal only in absolute residuals → possible heteroscedasticity | `NOT_SUPPORTED` |
| G-06 | Geographic graph (real queen-contiguity) adds value beyond permuted-graph control for Italy | Phase 4P/4Q | 4P, 4Q | IT 93 NUTS3 | 99 conjugated graph controls | `HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md`; `HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md` | Strong refutation (p=0.19, p=0.32) | Italy only | Two linear ablations only | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| G-07 | The L3 territory projection from sector shares contains temporally stable, territory-specific associations | G1-L3 observable graph | G1/G4-lite | FR/NL clean nine-sector panels | Temporal and territory nulls, BH/FDR, LOYO, bootstrap | `HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md` | Strong within current protocol (2/2 eligible pass, q=0.005) | Two countries; heterogeneous territorial systems | PT excluded because KZ has zero mass; other layers unvalidated | `SUPPORTED` |
| G-08 | RCA/product-space sector co-specialization is reproducible across the common country nucleus | G1-L1 observable graph | G1/G4-lite | FR/NL; PT ineligible | Temporal and configuration nulls, BH/FDR, LOYO, bootstrap | `HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md` | Refuted by gate (NL pass, FR fail, PT ineligible) | One passing country | Stable marginal prevalence reproduces FR stability | `NOT_SUPPORTED` |
| G-10 | Same-sector cross-territory co-growth patterns are temporally stable across the country nucleus | G1-L2 causal co-growth | G1/G4-lite | FR (9 sectors), NL (9 sectors), PT (8 sectors; KZ excluded per DEC-018) | Temporal and territory nulls, BH/FDR, LOYO, bootstrap, COVID sensitivity | `HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md` | Strong: 3/3 pass, q=0.005, COVID-robust; FR 0.782, NL 0.789, PT 0.778 | Rolling Pearson conflates co-movement with shared trends; MAUP applies; heterogeneous territorial systems | Edges are statistical associations, not structural causality | `SUPPORTED` |
| G-09 | Functional/mobility network provides predictive signal for enterprise births | Not yet run | — | — | — | — | None | — | Data availability not confirmed at NUTS3 level | `NOT_TESTED` |

---

## Generalization claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| GEN-01 | HERALD transfers robustly across European regions | Phase 4G–4I LOCO | 4G/4H/4I | FR/NL/BE/PT | LOCO zero-shot with target history | `HERALD_PHASE4H_B_RESULTS_AUDIT.md`; `HERALD_PHASE4I_A_RESULTS_AUDIT.md` | Moderate refutation | n=4 country domains | Not cold-start; heterogeneous targets; persistence dominates | `NOT_SUPPORTED` |
| GEN-02 | Persistence provides a transferable baseline across European harmonized `enterprise_birth` regions | Phase 4N LOCO | 4N | PT/IT/AT 2008-2020 | LOCO rolling-origin | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Moderate | 3 countries, same Eurostat indicator, mainland only | 1-year horizon; 2008–2020 window | `SUPPORTED` |
| GEN-03 | LOCO protocol is cold-start (no target-country history available at inference) | Phase 4H code/concept audit | 4H | — | Protocol review | `HERALD_PHASE4H_CODE_CONCEPT_AUDIT_2026.md` | Confirmed refutation of claim | — | The protocol is zero-shot parameter transfer WITH target-country lag history | `REFUTED_UNDER_CURRENT_PROTOCOL` |

---

## Recommendation claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| REC-01 | The system provides economic recommendations for territorial planning | None | — | — | — | — | None | — | Recommendation module does not exist yet | `NOT_TESTED` |
| REC-02 | Dynamic economic graph identifies productive opportunities for territories | Not yet run | — | — | — | — | None | — | L3 is descriptive only; opportunity/recommendation layer does not exist | `NOT_TESTED` |

---

## Methodological claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| MET-01 | Causal rolling-origin evaluation (no target leakage) is enforced in all post-4D phases | Code audit + validation guard | 4E → 4Q | All panels | `validation.py` + per-run audit | `HERALD_LEAK_AUDIT_FINAL_20260507.md` | Strong | All current experiments | Legacy 4A/4D excluded | `SUPPORTED` |
| MET-02 | Moran's I with 999 permutations and BH/FDR correction is the correct spatial autocorrelation protocol | Phase 4O-C protocol | 4O-C | IT/PT/AT | Pre-registered gate | `HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Moderate | Standard for spatial econometrics | LOO threshold (50%) is ad-hoc | `SUPPORTED` |
| MET-03 | Pooled WMAPE is an admissible primary result for European panel | Phase 4J semantic audit | 4J | FR/NL/BE/PT | — | `HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` | Strong refutation | Universal | Incommensurable targets cannot be pooled | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| MET-04 | Graph attention weights are interpretable explanations of economic relations | Not tested | — | — | — | — | None | — | Requires validation against null model and economic ground truth | `NOT_TESTED` |

---

## Summary counts

| Status | Count |
|--------|------:|
| `SUPPORTED` | 8 |
| `PARTIALLY_SUPPORTED` | 2 |
| `EXPLORATORY` | 1 |
| `NOT_SUPPORTED` | 2 |
| `REFUTED_UNDER_CURRENT_PROTOCOL` | 6 |
| `NOT_TESTED` | 5 |
| **Total** | **24** |

---

## Gate: claims permitted in publications

**PERMITTED (supported evidence, conditioned on scope):**
- Persistence is the best-balanced baseline for PT/IT/AT harmonized enterprise-birth LOCO, 2008–2020, 1-year horizon.
- Italian persistence residuals show robust spatial autocorrelation (Moran's I, FDR-corrected, LOO-stable, 7/9 years significant).
- Geographic queen-contiguity lags (first-order and Spatial-Durbin) do not improve Italy forecasts under current protocol.
- FR/NL/BE/PT targets are semantically heterogeneous; pooled WMAPE is not a valid generalization metric.
- HERALD Q7 achieves 0.0204 mean WMAPE on French ZE 2021–2025.

**PROHIBITED (not tested or refuted):**
- "HERALD provides economic recommendations."
- "The economic dynamic graph is operational."
- "Geographic graphs improve forecasting." (refuted under current protocol)
- "LOCO protocol is cold-start."
- "The system generalizes to arbitrary European countries."
- "Attention weights explain economic relations."
- "Granger predictability implies economic causality."
