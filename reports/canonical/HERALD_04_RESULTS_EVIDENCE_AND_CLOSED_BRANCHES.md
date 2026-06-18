# HERALD 04 — Results, Evidence, and Closed Branches

**Created:** 2026-06-18 (canonical consolidation pass).
**Status:** Documentation only — restates `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
and `reports/HERALD_PROJECT_CHARTER.md` §4-5. The 32-claim evidence matrix
(`HERALD_EVIDENCE_MATRIX.md`, F-01→F-07, G-01→G-18, GEN-01→03, REC-01→02, MET-01→06) was
removed from the git index in the 2026-06-18 root cleanup; every claim's verdict is either
already in the table below or in the decision log directly — see git history for the full
matrix with per-claim evidence-strength/external-validity/limitations columns. If this
document disagrees with the decision log, the decision log wins.
**Represents:** the per-phase results audits (4N/4O/4P/4Q, G1/G2 audits, P6/graph-temporal
final audits, DEC-048→DEC-066 reports). None deleted — see
`reports/HERALD_REPORTS_CONSOLIDATION_MAP.md`.

---

## Claim / evidence / status / source / permitted-in-article table

| Claim | Evidence | Status | Source | Permitted in article? |
|---|---|---|---|---|
| Persistence is the best LOCO baseline for PT/IT/AT | Balanced WMAPE: persistence 0.0874 vs n3_residual 0.0865 (gain concentrated in PT only, 1/3 countries) | **VALIDATED** | DEC-006, `HERALD_PHASE4N_RESULTS_AUDIT.md` | **Yes** |
| France HERALD Q7 achieves WMAPE 0.0204 | 306 ZE, 2021–2025, rolling-window, Phase 3E/2R | **PENDING_REAUDIT** | `HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md` | **Caveat only** — not as a headline claim until the causal-feature audit (`growth_1y/2y`, `effectifs_lag1`) completes |
| Italian residuals show robust spatial autocorrelation | Moran's I, FDR, LOO-stable | **SUPPORTED** | DEC-007, `HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Yes, scoped to Italy only |
| Geographic queen-contiguity lag improves forecasts | Real graph WMAPE 0.0562 vs persistence 0.0549; p=0.19 vs 99 permuted controls | **FAIL / FORBIDDEN CLAIM** | DEC-008, `HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md` | **No** |
| FR/NL/BE/PT targets are semantically equivalent | Target definitions documented per official source (établissement creation / local unit opening / VAT registration / enterprise birth) | **FAIL — heterogeneous** | DEC-003, `HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` | **No**, except the explicitly harmonized Path H (PT/IT/AT) subpanel |
| G1-L2 co-growth field is temporally stable (FR/NL/PT) | 3/3 pass, temporal q=0.005, territory q=0.005, COVID-robust | **VALIDATED** | DEC-019/020, `HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md` | Yes, as association/co-movement only — never causal |
| G1-L3 territory-structure projection contains temporally stable, territory-specific associations | 2/2 eligible countries (FR/NL) pass, q=0.005; PT excluded (KZ zero mass) | **SUPPORTED** (evidence matrix G-07) | `HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md` | Yes, scoped to FR/NL only |
| HERALD transfers robustly across European regions (LOCO zero-shot) | Phase 4G-4I LOCO, FR/NL/BE/PT | **NOT_SUPPORTED** (evidence matrix GEN-01) — persistence dominates, n=4 country domains | `HERALD_PHASE4H_B_RESULTS_AUDIT.md`, `HERALD_PHASE4I_A_RESULTS_AUDIT.md` | **No** as a positive transfer claim |
| Louvain communities are a valid structure on G1 | 0/3 PASS under valid temporal/territory nulls + modularity/AMI FDR gate | **FAIL** | `HERALD_G1_COMMUNITIES_AUDIT.md` | **No** |
| G2 aggregate temporal signal is robust | FR 9/9 COVID-robust; NL/PT COVID-sensitive, no 2-country replication | **PARTIALLY_SUPPORTED** (FR only) | DEC-024c/d, `HERALD_G2_COVID_SENSITIVITY_AUDIT.md` | France only, with the COVID caveat stated |
| Individual G2 edges are stable | M2 range 0.06–0.26 | **NOT_SUPPORTED** | Charter §5 | **No** |
| P6 dual dynamic graph improves prediction | All 7 gate criteria fail; C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%); seed Jaccard 0.34 | `DUAL_GRAPH_S1_FAIL` — **CLOSED** | DEC-029, `HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` | **No** |
| P6 learned sector edges represent economic structure | Sector name mapping in the CSV does not match tensor sector_ids; source unverifiable | `INVALID_FOR_INTERPRETATION` | Charter §6 | **No** — index-based gate metrics (Jaccard, density, MAE) remain valid |
| Graph-temporal (GConvGRU/EvolveGCN-H) improves on Ridge | Indistinguishable from permutation nulls (p=1.0 for GConvGRU); WMAPE Ridge 0.06486 vs GConvGRU 0.06492 vs EvolveGCN-H 0.06497 | `S1_FR_FAIL` — **CLOSED** | DEC-031, `HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` | **No** |
| Phase 7 sector→sector relations are valid (FR/NL COROP/PT Municipal) | 20 edges, bootstrap/permutation/FDR-corrected, pre-registered |β| thresholds | **VALIDATED** | DEC-034, `HERALD_PHASE7_SECTOR_PRECEDENCE.md` | Yes, as association/predictive precedence — never causal |
| France's weak sector-relation signal reflects a methodology gap | 280 small ZE → systematically smaller |β| (0.076–0.097), below threshold; not a power/methodology failure | **AUDIT_COMPLETE, scale finding** | DEC-060 | Yes, framed as a scale/granularity finding, not a gap |
| PT can be raised to municipal grain; NL can | PT: INE API confirms 278/297 municipalities, 17 sectors, 2008–2023. NL: CBS has no gemeente×births×sector table (5,927-table catalog searched) | `PT_READY_NL_BLOCKED` | DEC-061 | Yes |
| PT Municipal Phase 7 produces valid relations | 2 COVID-robust pairs (GI→OQ, MN→JZ), both period-specific 2015–2020 | `PT_MUNICIPAL_PHASE7_COMPLETE` | DEC-064 | Yes, with the period-specific caveat |
| NL gemeente proxy edges are valid relations | Automated gate count says SUPPORTED (121 edges), but structural diagnostic finds the proxy method injects spurious cross-sector correlation (share_velocity coef. 13.0 vs corop_velocity 1.33, R²=0.635) | `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` — **manual override**, **CLOSED for relation labels** | DEC-065 | **No** — NL COROP (8 promoted, 3 COVID-robust, observed) remains the only valid NL baseline |
| Fine-grain thresholds (0.09/0.07-0.09) are a valid supplementary policy | 10/10 gates PASS, 43/43 tests PASS | `FINE_GRAIN_THRESHOLD_POLICY_READY` | DEC-066 | Yes, with tier explicitly stated per label |
| SharedRelationEncoder detects real sector relations | Synthetic: unseen-pair AUC=0.690 (strong). Real: sign concordance 0.438–0.667, 4/7 controls within 0.05 of best variant, 0 abstentions ever recorded | `REAL_WEAK_LABEL_TUNING_PARTIAL` | DEC-055/056/058/059 | Synthetic result: yes. Real-data result: only as "partial, not final," never as a headline claim |
| Observatory v0.5.1 is a finished, validated dashboard | 103/103 structural (DOM/JS string) tests pass; **no Playwright/screenshot validation ever performed** | `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN` | DEC-068 | **No** — citable as "current candidate, structurally tested, not visually validated" only |
| 27-country European sector-coverage preflight is integration-ready | FI eligible-with-mapping; 9 countries eligible-with-download; BE blocked (semantics); K_L sectors combined in Eurostat source for all countries | **ELIGIBILITY CLASSIFICATION ONLY — no country integrated** | DEC-038, `HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md` | Yes, as an eligibility audit only — not as evidence of expansion |
| Synthetic benchmark architecture (Phase 9) is valid | 10T×5S×12Y generator, causal features, 2 seeds smoke run, no NaN/leakage | `SMOKE PASS` | DEC-039/040 | Yes, scoped to "architecture validated at smoke scale" |
| Phase 10 lagged-graph AUC contradicts Phase 9's graph-usage diagnostic | DEC-042 AUC=0.727 vs Phase10 `herald_contemp` AUC=0.40 | **`MODEL_DIFFERENCE`, not a bug** — `PHASE10_PARTIAL` | DEC-042/043/044 | Yes, with the model-difference caveat explicit |
| Learned edge structure generalizes out-of-distribution | AUC=0.611 OOD (edge structure transfers); MLP decoder does not generalize under 85-90% nonlinear shift | **PARTIAL** — structure transfers, decoder does not | DEC-045 | Yes, both halves stated together |
| Few-shot adaptation (frozen attention + adapted decoder) improves OOD imputation | B0 ffill MAE≈0.244 beats all neural strategies (≈0.281) | `FEWSHOT_ADAPTATION_FAILED` | DEC-047 | **No** as a positive claim — yes as a documented negative result |
| Recommendation layer exists | — | **0% — NOT STARTED** | Charter §2.6, §3 | **No** |

---

## Closed branches — summary (do not reopen without a new DEC-*, Charter §8)

1. Geographic/mobility graph as a predictive feature (queen-contiguity, Italy spatial lag + Spatial Durbin) — FAIL.
2. P6 Dynamic Dual Economic Graph — `DUAL_GRAPH_S1_FAIL`, all 7 gates.
3. Graph-temporal neural prediction (GConvGRU, EvolveGCN-H) — `S1_FR_FAIL`, indistinguishable from nulls.
4. Louvain community detection on G1 — FAIL, 0/3 under valid nulls.
5. Phase 5 fixed-L2 residual corrector — `NOT_SUPPORTED`.
6. RCA co-specialization (G1-L1) — `NOT_SUPPORTED` (NL pass, FR fail).
7. NL gemeente proxy as a relation-label source — `BLOCKED` (manual override of an automated SUPPORTED count).

## Partial / research-only (open, not in any dashboard)

- SharedRelationEncoder real-data validation (DEC-056/058/059) — `REAL_WEAK_LABEL_TUNING_PARTIAL`.

## Exploratory only (never a training label)

- `EXPLORATORY_FINE_GRAIN` tier (DEC-066, |β| 0.07–0.09).
- France's 8 near-miss-beta and 7 near-miss-fdr pairs (DEC-060) — documented, not promoted.

---

## Cross-reference

- Phase-by-phase narrative: `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
- Data provenance: `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`
- Methods/architecture: `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
- Dashboard/article roadmap: `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`
- Full decision text for any row above: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
