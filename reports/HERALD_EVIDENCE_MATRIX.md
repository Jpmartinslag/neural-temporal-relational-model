# HERALD — Evidence Matrix

**Created:** 2026-06-10  
**Rule:** Claims are classified by their current evidentiary status. Status reflects the strongest current evidence; do not retroactively upgrade claims using superseded or leaky runs.  
**Status vocabulary:** `SUPPORTED` · `PARTIALLY_SUPPORTED` · `EXPLORATORY` · `NOT_SUPPORTED` · `REFUTED_UNDER_CURRENT_PROTOCOL` · `NOT_TESTED` · `PENDING_REAUDIT`

---

## Forecasting claims

| # | Claim | Evidence | Phase | Data | Protocol | Artefact | Evidence strength | External validity | Limitations | Status |
|---|-------|----------|-------|------|----------|----------|-------------------|------------------|-------------|--------|
| F-01 | Persistence (`lag1_births`) is the best single predictor for Italy and Austria in rolling-origin LOCO | Phase 4N results | 4N | PT/IT/AT 2008-2020, 151 NUTS3 | Rolling-origin LOCO, causal features | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Strong within protocol | Limited (3 countries, 1 horizon) | Only 2008–2020 window; 1-year horizon only | `SUPPORTED` |
| F-02 | Residual Ridge improves PT under LOCO but degrades IT and AT | Phase 4N | 4N | PT/IT/AT | LOCO rolling-origin | `HERALD_PHASE4N_RESULTS_AUDIT.md` | Moderate | Low (n=3 countries) | Gain concentrated in scale-invariance, not transferable dynamics | `PARTIALLY_SUPPORTED` |
| F-03 | Country-balanced WMAPE is protocol-specific: Phase 4N PT/IT/AT persistence ~0.0874; broader heterogeneous-target LOCO is not directly comparable | Phase 4N harmonized + Phase 4G-4I broader LOCO | 4N/4H-B | PT/IT/AT or FR/NL/BE/PT | Rolling-origin LOCO | `HERALD_PHASE4N_RESULTS_AUDIT.md`; `HERALD_PHASE4H_B_RESULTS_AUDIT.md` | Moderate | Protocol-specific | Different country sets and target semantics must not be pooled into one headline metric | `SUPPORTED` |
| F-04 | HERALD Q7 (France) achieves WMAPE 0.0204 mean 2021–2025 | Phase 3E France confirmatory | 3E / 2R | 306 French ZE, 2021–2025 | Rolling-window, 240 runs, 12 configs × 20 seeds | `HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`; `HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` | Strong for France | France only; French institutional data | Causal audit of Phase 3E/2R pipeline features (`growth_1y/2y`, `effectifs_lag1`) not yet formally complete for French track | `PENDING_REAUDIT` |
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
| G-10 | Dense same-sector cross-territory co-growth weight fields are temporally stable across the country nucleus | G1-L2 co-growth without future data | G1/G4-lite | FR (9 sectors), NL (9 sectors), PT (8 sectors; KZ excluded per DEC-018) | Temporal and territory nulls, BH/FDR, dense-weight stability, bootstrap, COVID sensitivity | `HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`; `HERALD_G2_COVID_SENSITIVITY_AUDIT.md` | Strong for the dense weight field: 3/3 pass, q=0.005; FR 0.782, NL 0.789, PT 0.778 | Does not imply stable individual top-k edges; rolling Pearson conflates co-movement with shared trends; MAUP applies | Statistical association field, not Granger predictability or structural causality | `SUPPORTED` |
| G-11 | The L2 co-growth graph exhibits community structure significantly exceeding temporal and territory permutation nulls | Corrected G1-L2 community baseline | G1 / task 2.8 | FR, NL, PT | Symmetric top-k=5; L2 rebuilt from 99 temporal + 99 territory series permutations; equal Louvain budget; modularity and AMI with BH/FDR; COVID sensitivity | `HERALD_G1_COMMUNITIES_AUDIT.md` | 0/3 pass: modularity is reproducible by nulls; some AMI evidence survives but full gate fails | Three heterogeneous territorial systems | L2 stability remains supported, but Louvain communities are not validated | `NOT_SUPPORTED` |
| G-12 | Fixed-L2 residual corrector (sklearn MLP on pre-aggregated L2 features) improves out-of-sample territorial forecasting over AR-Ridge baseline | Phase 5 ablation v3 | Phase 5 | NL 40 COROP, eval 2021-2023 | Rolling-origin; 5 seeds; widths (2,)(4,)(8,)(16,8); temporal+territory permuted-graph controls; gate: H2 ≤ H0b×1.1, beats H1, beats both controls | `HERALD_PHASE5_HPC_SPEC.md`; DEC-023 | H2-neural (best width=(8,)) 5.53% vs H0b 3.41% — 62% regression. Beats permuted controls but worse than H1-neural (no graph). Linear H2 also fails (5.56%). n_train fixed (39→440 after imputation). Architecture confirmed NOT a GNN: fixed non-trainable 1-hop aggregation. | NL only; other countries not run | Residual corrector architecture may be insufficient; result does not preclude trainable GNN on other data | `NOT_SUPPORTED` |
| G-13 | The sparse L2 top-k=5 graph shows aggregate temporal coherence above permutation nulls | G2 corrected controls + COVID sensitivity (DEC-024c/d) | Bloco 2 / G2 | FR 9 sectors · NL 9 sectors · PT 8 sectors; top-k=5; 199 perms N1+N2 in both COVID scenarios | M1 consecutive Jaccard; M2 mean pairwise Jaccard; main includes obs-year 2020; sensitivity excludes only obs-year 2020; BH/FDR q=0.05 | `HERALD_G2_PREFLIGHT.md` §7; `HERALD_G2_COVID_SENSITIVITY_AUDIT.md` | FR is robust (9/9 in both). NL changes 4/9 to 5/9 and crosses the country gate only without 2020. PT changes 4/8 to 0/8 and crosses the gate only with 2020. Seven of 26 sector decisions change. Edge stability remains unsupported (M2 0.06–0.28; threshold 0.70); M3 null blocked. | Global 2/3 gate passes in both scenarios but with different countries, so two-country replication is not COVID-robust | Aggregate evidence is robust only for FR; NL/PT are COVID-sensitive. No individual-edge, causal, pooled-country or recommendation claim. | `PARTIALLY_SUPPORTED` |
| G-14 | The positive top-k L2 graph's aggregate density and weight distributions vary modestly across rolling windows ending before, during and after 2020 | G2 aggregate dynamics (DEC-025) | Bloco 2 / G2 | FR 9 sectors · NL 9 sectors · PT 8 sectors; top-k=5; 200 pair-resampling sensitivity draws; period defined by last observation year in each five-year window | Density, mean/median weight, turnover, Jaccard, period comparisons, COVID sensitivity, top-k 3/5/10 | `HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md` | FR: Δdensity <0.001, Δweight <0.01; NL: Δdensity +0.006, Δweight +0.011; PT: Δdensity +0.001, Δweight +0.048. Turnover high (FR 79%, NL 59%, PT 51%). Pair-resampling intervals are descriptive, not confidence intervals. | FR COVID-robust under G-13; NL/PT COVID-sensitive; no cross-country replication | Descriptive only. Overlapping rolling windows; positive-edge selection by construction; no causal, individual-edge, community, forecast or recommendation claim. | `SUPPORTED` |
| G-09 | Functional/mobility network provides predictive signal for enterprise births | Not yet run | — | — | — | — | None | — | Data availability not confirmed at NUTS3 level | `NOT_TESTED` |
| G-15 | Dynamic dual economic graph (territory graph + learned sector graph, ≤10,000 params) improves territorial enterprise-birth prediction, regime classification, or recovery detection | P6_DDEG_S1 full study — Slurm job 7453691 — 275/275 complete | Phase 6 | FR 101 NUTS3, 9 A10 sectors, eval 2021–2025 | 5-fold rolling-origin, 11 controls, 5 seeds, fail-closed gate §9 | `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`; `data/processed/dual_graph_s1/gate_result.json` | Strong refutation: all 7 gate criteria fail. C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%). C5 never beats both graph permutation nulls simultaneously. | FR only; one parameter budget (hidden_dim=8); one horizon | Low-capacity architecture; higher-capacity graph-temporal models (A1 contract) not precluded | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| G-16 | The P6_DDEG_S1 learned sector adjacency encodes reproducible sector associations across seeds | P6_DDEG_S1 full study (DEC-029) | Phase 6 | FR 101 NUTS3, 9 A10 sectors | Mean seed Jaccard per fold over 5 seeds | `data/processed/dual_graph_s1/learned_sector_edges.csv` | Weak (mean Jaccard 0.3353; threshold 0.50 fails). Descriptively: C↔KZ appears in 80%, FZ↔HZ in 76% of fold×seed runs. | FR only; optimization artifact from failed gate | Jaccard below stability threshold; sectors are L1-regularized optimization outputs, not validated economic structure | `NOT_SUPPORTED` |
| G-17 | GConvGRU (A1a) or EvolveGCN-H (A1b) improves territorial enterprise-birth prediction over AR-Ridge for France under the fail-closed A1 gate | S1_FR local test (DEC-031) | A1/S1-FR | FR 280 ZE, eval 2021–2025, 5 seeds {42–46} | Rolling-origin, 5 eval years, temporal+territory null permutations (9999 seeds), fail-closed gate pre-registered at DEC-028 | `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md`; `data/processed/graph_temporal_s1/s1_fr_results.json` | Strong refutation: both models fail all 5 gate criteria. GConvGRU WMAPE 0.064922 vs Ridge 0.064856 (+0.1%), p_temporal=1.0, p_territory=1.0, wins 1/5 years. EvolveGCN-H WMAPE 0.064973 (+0.2%), p_temporal=1.0, p_territory=0.293, wins 1/5 years. Both models indistinguishable from null permutations. | FR only; 3-feature tensor | Feature-set limitation, not necessarily architecture limitation. Does not preclude wider economic feature sets. | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| G-18 | Lagged sector growth predicts enterprise-birth growth in another sector (predictive precedence), surviving BH/FDR, bootstrap sign stability and COVID-19 exclusion sensitivity | Phase 7 distributed study — Slurm job 7455266 — 710/710 complete (DEC-034) | Phase 7 | FR/NL/PT; 9 sectors (PT 8, KZ absent); 45,945 rows; 6-year rolling windows; 2 scenarios | 999 within-year permutations; 500 territory-cluster bootstraps; BH/FDR per country×scenario×window family; COVID sensitivity (without_2020) | `reports/HERALD_PHASE7_SECTOR_PRECEDENCE.md`; `data/processed/sector_precedence_results/decision.json`; `data/processed/sector_precedence_results/covid_robust_edges.csv` | Strong within current protocol: 12 COVID-robust edges in 2 countries (NL=3, PT=9); audit PASS; BH/FDR discrepancy max 1.11e-16. FR: 1 promoted (main) but not COVID-robust. | FR contributes 0 COVID-robust edges; edges are A10 aggregations | Associations only; no structural causality, mechanism, or intervention claim. Short windows and overlapping intervals limit power for slow-frequency dynamics. | `SUPPORTED` |

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
| MET-05 | GConvGRU or EvolveGCN-H is the correct graph-temporal architecture for HERALD | S1_FR local test (DEC-031) | A1/S1-FR | FR 280 ZE, eval 2021–2025 | Pre-registered fail-closed gate | `HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md`; `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` | Strong refutation for predictive use: both architectures fail all 5 gate criteria under current 3-feature tensor | Not established for other feature sets | Both architectures indistinguishable from null permutations; does not preclude use as representation learning with richer features | `REFUTED_UNDER_CURRENT_PROTOCOL` |
| MET-06 | The schema 2.0 pipeline exports causal, deterministic graph-temporal sequences aligned with the canonical H0b Ridge | E0-v2 smoke (DEC-028): 8 checks pass, 57 tests pass, 2-run determinism, FR adjacency audit 5 folds | DEC-027/028 | NL 40 COROP (smoke); FR 280 ZE (adjacency audit) | LeakageError assertions; 57 invariant tests; two-run NPZ checksum comparison; FR 8 fail-closed adjacency criteria | `HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md`; `HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` | Strong for data infrastructure | NL and FR only; GConvGRU/EvolveGCN-H trained on FR tensors and failed S1 gate (DEC-031) | Does not imply GConvGRU or EvolveGCN-H improves forecasting — confirmed by S1_FR_FAIL; tensor infrastructure remains valid | `SUPPORTED` |

---

## Summary counts

| Status | Count |
|--------|------:|
| `SUPPORTED` | 11 |
| `PARTIALLY_SUPPORTED` | 3 |
| `EXPLORATORY` | 1 |
| `NOT_SUPPORTED` | 5 |
| `REFUTED_UNDER_CURRENT_PROTOCOL` | 8 |
| `NOT_TESTED` | 4 |
| `PENDING_REAUDIT` | 1 |
| **Total** | **33** |

_Updated 2026-06-12 (DEC-035): Observatory v0.3 integrates G-18 SUPPORTED result. Sector→sector layer: 12 ROBUST + 13 MAIN_ONLY_EXPLORATORY edges. Dashboard: `reports/dashboards/herald_observatory_v03_dashboard.html`. F=7, G=12, GEN=3, REC=2, MET=6; total=34._

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
- "The L2 co-growth graph improves territorial forecasting." (G-12 NOT_SUPPORTED)
- "LOCO protocol is cold-start."
- "The system generalizes to arbitrary European countries."
- "Attention weights explain economic relations."
- "Granger predictability implies economic causality."
- "The G-12 result refutes trainable GNN architectures." (only fixed-L2 residual corrector tested)
- "The L2 graph has structurally stable individual edges." (LOYO Jaccard 0.07-0.26; persistence 0.4%; both below threshold)
- "The L2 graph shows structural evolution." (use: "observed aggregate variation in density and weights")
