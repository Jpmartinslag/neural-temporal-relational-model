# HERALD Active Document Index
**Updated:** 2026-06-18 (consolidation/freeze pass — adds DEC-060→DEC-068 entries above the
fold, which were already present from earlier same-day edits, plus the exhaustive appendix
at the bottom covering every `reports/*.md` file not otherwise listed, per the "be exhaustive"
instruction. No prior entry was removed or reclassified without a stated reason.)
**Rule:** Documents not listed here should be treated as historical/archived unless explicitly referenced by an active decision.

---

## Category legend (2026-06-18 curation pass)

This index previously labelled almost everything "ACTIVE", which stopped being useful
once the repository passed 200+ reports. Every section below now maps to one of these
seven categories. The category tag appears in the section heading; per-row "Status"
columns are left as originally written (they often carry more detail, e.g. "ACTIVE
(closed branch)") and should be read together with the section's category tag, not
instead of it.

| Category | Meaning |
|---|---|
| `CANONICAL_READ_FIRST` | Read these before anything else; they define scope, state, and rules. |
| `CURRENT_SCIENTIFIC_EVIDENCE` | Results currently citable as evidence (validated baselines, validated relations, current research-track findings). |
| `SOURCE_AUDITS` | Explain where a current result came from (e.g. France Q7 selection) — not the headline claim itself, but required reading to trust it. |
| `HISTORICAL_BUT_IMPORTANT` | Superseded for citation but explains the path that led to current state; do not delete, do not cite as current. |
| `SUPERSEDED_OR_CLOSED_BRANCH` | Tested and rejected under a pre-registered gate; reopening requires a new DEC-* per Charter §8. |
| `GENERATED_DASHBOARD_OR_EXPORT` | Build output, regenerable from a builder script; not itself a scientific claim. |
| `DO_NOT_START_HERE` | Real artefacts but not an entry point for understanding the project (pre-HERALD, operational housekeeping, raw HPC dumps). |

See `reports/HERALD_PROJECT_TRAJECTORY.md` for the narrative version of how these
pieces fit together chronologically, and `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md`
for which canonical synthesis document now represents each cluster of older reports.

---

## Source of Truth Documents (read first) — `CANONICAL_READ_FIRST`

| Document | Purpose | Status |
|----------|---------|--------|
| `README.md` | Public entry point, project trajectory summary, repository map | ACTIVE |
| `reports/HERALD_PROJECT_TRAJECTORY.md` | Narrative evolution of the project, April→June 2026, with caveats preserved | ACTIVE |
| `reports/HERALD_CURRENT_STATE.md` | State per component, blockers, next step | ACTIVE |
| `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` | All decisions DEC-001→DEC-037 | ACTIVE |
| `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` | Classifies every report into 7 categories | ACTIVE |
| `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md` | Which canonical doc represents which report cluster | ACTIVE |
| `reports/HERALD_PROJECT_CHARTER.md` | Official direction, scope, permitted/forbidden claims | ACTIVE |
| `reports/HERALD_EVIDENCE_MATRIX.md` | All claims and their evidentiary status (32 claims) | ACTIVE |
| `reports/HERALD_RESEARCH_GANTT.md` | Timeline and task dependencies | ACTIVE |
| `hpc/HPC_PHASE_INDEX.md` | HPC phase registry and status | ACTIVE |
| `hpc/hpc_phase_registry.json` | Machine-readable HPC registry | ACTIVE |
| `reports/herald_artifact_registry.json` | Artefact manifest with status and claims | ACTIVE |

---

## Active Scientific Reports

### France / Phase 2–3 — `SOURCE_AUDITS`
Explains where France's prediction layer (Q7) came from. The headline number itself
is PENDING_REAUDIT (see below) — these are the audits that justify trusting the
selection process, not a substitute for the reaudit.
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md` | Q7 selection, WMAPE 0.0204 France | ACTIVE |
| `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` | France confirmatory result | ACTIVE |

### International Harmonization / Phase 4 — `CURRENT_SCIENTIFIC_EVIDENCE` (PASS rows) / `SUPERSEDED_OR_CLOSED_BRANCH` (FAIL rows)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_PHASE4N_RESULTS_AUDIT.md` | LOCO baseline PT/IT/AT | ACTIVE |
| `reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md` | Spatial autocorrelation diagnostics | ACTIVE |
| `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md` | Italy spatial lag FAIL | ACTIVE (closed branch) |
| `reports/HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md` | Italy Spatial Durbin FAIL | ACTIVE (closed branch) |
| `reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` | Target heterogeneity audit | ACTIVE |
| `reports/HERALD_PHASE4M_PT_IT_AT_PANEL_AUDIT.md` | PT/IT/AT harmonized panel | ACTIVE |
| `reports/HERALD_PHASE4M_COMMON_FEATURE_CONTRACT.md` | Feature contract LOCO | ACTIVE |
| `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md` | Causal baseline per country | ACTIVE |
| `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md` | Leakage audit 4A/4D | ACTIVE (historical reference) |
| `reports/HERALD_LEAK_AUDIT_FINAL_20260507.md` | Integrity audit | ACTIVE |

### Dynamic Economic Graph / Phase 5–6 — `CURRENT_SCIENTIFIC_EVIDENCE` (G1-L2/G2 PASS rows) / `SUPERSEDED_OR_CLOSED_BRANCH` (communities, Phase 5, P6 dual-graph rows)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_G0_FORMAL_CONTRACT.md` | G0 conceptual contract (10/10) | ACTIVE |
| `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md` | G1-L2 PASS (DEC-019/020) | ACTIVE |
| `reports/HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md` | G2 dynamics descriptive (DEC-025) | ACTIVE |
| `reports/HERALD_G2_COVID_SENSITIVITY_AUDIT.md` | G2 COVID sensitivity (DEC-024d) | ACTIVE |
| `reports/HERALD_G1_COMMUNITIES_AUDIT.md` | Community detection NOT_SUPPORTED | ACTIVE (closed branch) |
| `reports/HERALD_PHASE5_HPC_SPEC.md` | Phase 5 NOT_SUPPORTED (DEC-023) | ACTIVE (closed branch) |
| `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md` | P6 FAIL results summary | ACTIVE (closed branch) |
| `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` | P6 FAIL full audit (DEC-029) | ACTIVE (closed branch) |
| `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` | G0→G6 roadmap | ACTIVE |

### Graph-Temporal Architecture — `SUPERSEDED_OR_CLOSED_BRANCH`
S1_FR_FAIL (DEC-031) closed the whole branch; contract/preflight docs kept for
traceability of why the architecture was chosen before it failed.
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md` | A1 contract FROZEN (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md` | E0-v2 PASS, schema 2.0 (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` | FR adjacency READY (DEC-028) | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md` | DEC-027 preflight decision | ACTIVE |
| `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` | S1_FR_FAIL (DEC-031) — GConvGRU/EvolveGCN-H fail frozen gate | ACTIVE (closed branch) |

### Economic Observatory — `CURRENT_SCIENTIFIC_EVIDENCE` (contracts/methods) + `GENERATED_DASHBOARD_OR_EXPORT` (the .html files)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_OBSERVATORY_V01_DATA_CONTRACT.md` | Aggregate v0.1.1 + sector v0.2 contract, evidence separation and causal guarantees (DEC-032) | ACTIVE |
| `reports/HERALD_SECTOR_PRECEDENCE_GRAPH_CONTRACT.md` | Signed lag-1 sector→sector method and fail-closed execution gate (DEC-033) | ACTIVE |
| `reports/HERALD_PHASE7_SECTOR_PRECEDENCE.md` | Phase 7 full HPC study audit; SECTOR_PRECEDENCE_PROTOTYPE_READY (DEC-034) | ACTIVE |
| `reports/HERALD_OBSERVATORY_V03_AUDIT.md` | Observatory v0.3 integration audit: sector relations, dashboard, tests (DEC-035/036) | ACTIVE |
| `src/data/european_panel/build_territorial_sector_movements.py` | Phase 8 LOTO builder: territorial influence decomposition of 12 ROBUST relations (DEC-037) | ACTIVE |

### Dashboard — `GENERATED_DASHBOARD_OR_EXPORT`, except the France original which is `HISTORICAL_BUT_IMPORTANT` (original operational base, do not modify casually)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/dashboards/herald_france_final_dashboard.html` | France operational dashboard — the original base everything else (v0.3→v0.5.1) was incrementally adapted from | ACTIVE — do not modify without explicit decision |
| `reports/dashboards/herald_observatory_v03_dashboard.html` | Observatory v0.3: choropleth map + sector graph + states + territory + provenance (DEC-035/036, 6.2 MB self-contained) | ACTIVE |

### Granular FR/PT/NL Evidence (DEC-063→DEC-066, Observatory v0.4) — `CURRENT_SCIENTIFIC_EVIDENCE` (contracts/audits) + `GENERATED_DASHBOARD_OR_EXPORT` (dashboard/exports)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_DEC063_GRANULAR_FR_PT_NL_EVIDENCE_MODEL.md` | FR/PT/NL granular evidence model, NL gemeente proxy construction | ACTIVE |
| `reports/HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md` | Evaluation must report observed-only/proxy-excluded sensitivity | ACTIVE |
| `reports/HERALD_DEC064_PT_MUNICIPAL_PHASE7_AUDIT.md` | PT Municipal Phase 7, 2 COVID-robust pairs | ACTIVE |
| `reports/HERALD_DEC066_FINE_GRAIN_THRESHOLD_CALIBRATION.md` | DEC-066 four-tier label taxonomy (0.10/0.09/0.07) | ACTIVE |
| `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md` | **NL_GEMEENTE_PROXY_PHASE7_BLOCKED** — structural validity defect (stock-share induced cross-sector correlation) | ACTIVE |
| `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` | Post-DEC-065 policy: observed vs proxy evidence, label classes, language rules | ACTIVE |
| `reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md` | Observatory v0.4 4-layer contract; NL gemeente proxy excluded from relation graph | ACTIVE |
| `data/processed/herald_observatory_v04_granular/` | Clean exports: territory_state, relation_edges (observed-only), blocked_proxy_edges, manifest | ACTIVE |
| `reports/dashboards/herald_observatory_v04_granular_dashboard.html` | Observatory v0.4.1 dashboard: FR/NL COROP/PT Municipality real choropleth + NL gemeente table fallback + dynamic observed-only relation graph (timeline/play/modes/heatmap) + blocked proxy panel (10.0 MB, offline) | ACTIVE |
| `src/data/european_panel/build_observatory_v04_dashboard.py` | Dashboard builder; fail-closed asserts NL gemeente proxy never in relation graph; loads PT geometry with fallback | ACTIVE |
| `src/data/european_panel/build_pt_municipality_geometry.py` | PT continental municipality geometry builder (geoapi.pt/DGT-CAOP source, 278/278, name crosswalk) | ACTIVE |
| `data/processed/geometries/pt_municipalities_continental.geojson` | PT continental municipality boundaries (278 features, 1.18 MB simplified) | ACTIVE |

### Layperson Narrative Observatory v0.5 (DEC-067, presentation layer on top of v0.4) — `HISTORICAL_BUT_IMPORTANT` (superseded for dashboard-readiness by v0.5.1, underlying data unaffected)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` | Prediction layer audit: FR/NL validated (joined from v0.3 Ridge/persistence forecasts); PT gap CLOSED in v0.5.1 (§6 appended) via causal persistence/Ridge on the observed PT municipal panel, no proxy, no HPC | ACTIVE (corrected) |
| `data/processed/herald_observatory_v05_narrative/` | Narrative exports: territory_view, sector_view, relation_view, prediction_view, map_state_by_year_sector.json, relation_timeline.json, manifest.json | ACTIVE (historical, v0.5 dashboard-readiness superseded) |
| `src/data/european_panel/build_observatory_v05_narrative_exports.py` | Builds v0.5 presentation-layer exports from v0.4 granular + v0.3 forecast data; never recomputes a scientific number | ACTIVE (historical, untouched) |
| `reports/dashboards/herald_observatory_v05_narrative_dashboard.html` | Layperson-friendly dynamic Observatory: map-as-heatmap, dynamic spatial sector graph, prediction layer (FR/NL), evidence badges, "How it works", collapsible technical panel (14.8 MB, offline). English UI; superseded for dashboard-readiness purposes by v0.5.1 | ACTIVE (historical, untouched) |
| `src/data/european_panel/build_observatory_v05_narrative_dashboard.py` | Dashboard builder; fail-closed asserts NL gemeente proxy never in relation graph; PT/KZ disabled with structural-absence tooltip | ACTIVE (historical, untouched) |
| `tests/test_observatory_v05_narrative_dashboard.py` | 65 tests: no raw NaN, sector names always paired with codes, PT/KZ structural absence, NL gemeente proxy exclusion, blocked-edge isolation, determinism | ACTIVE (historical, untouched, still passes) |

### Layperson Narrative Observatory v0.5.1 (correction of v0.5 dashboard-readiness) — `CURRENT_SCIENTIFIC_EVIDENCE` (audit) + `GENERATED_DASHBOARD_OR_EXPORT` (dashboard/exports) — **current candidate, not final** (DEC-068)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md` | Point-by-point record of what was wrong in v0.5 and what v0.5.1 fixed | ACTIVE |
| `src/data/european_panel/build_pt_municipal_prediction_layer.py` | Closes the PT prediction gap: causal persistence/Ridge AR(1) (verbatim method reused from `build_observatory_export.py`) on the observed PT municipal panel, no proxy, no HPC, with an explicit leakage assertion | ACTIVE |
| `data/processed/herald_observatory_v051_narrative/` | Corrected French exports: territory_view, sector_view, relation_view, prediction_view (incl. PT municipal), pt_municipal_prediction_view.csv, map_state_by_year_sector.json, relation_timeline.json, prediction_lookup.json, economic_basins.json, manifest.json | ACTIVE |
| `src/data/european_panel/build_observatory_v051_narrative_exports.py` | Builds v0.5.1 French exports from v0.4 granular + v0.3 forecast + new PT municipal forecast; never recomputes a v0.4 scientific number | ACTIVE |
| `reports/dashboards/herald_observatory_v051_narrative_dashboard.html` | French, article-grade Observatory: HERALD method diagram opens the page (before the map), integrated FR/NL/PT prediction, "Bassins économiques" geographic heatmap, graph-to-map wiring, French evidence summary, collapsible "Détails méthodologiques" | ACTIVE |
| `src/data/european_panel/build_observatory_v051_narrative_dashboard.py` + `..._template.py` | Dashboard builder/template; fail-closed asserts NL gemeente proxy never in relation graph; PT/KZ disabled with structural-absence tooltip; causal language confined to methodological-details | ACTIVE |
| `tests/test_observatory_v051_narrative_dashboard.py` | 103 tests covering every Part N requirement: French language, architecture-at-top, PT prediction integration, no raw NaN, PT/KZ disabled, NL gemeente exclusion, blocked-edge isolation, no causal language in main body, sector-name pairing, technical-term confinement, economic basins, graph-map wiring, timeline controls, determinism | ACTIVE |

### Bibliography — `CANONICAL_READ_FIRST` (for writing) / `CURRENT_SCIENTIFIC_EVIDENCE` (for citation status)
| Document | Covers | Status |
|----------|--------|--------|
| `reports/bibliography/HERALD_REFERENCES_MASTER.md` | 25 master references | ACTIVE |
| `reports/bibliography/herald_references.bib` | BibTeX (Friedman 2008 verified) | ACTIVE |
| `reports/bibliography/HERALD_REFERENCE_AUDIT.csv` | Reference audit | ACTIVE |

---

## Historical / Archived Documents — `HISTORICAL_BUT_IMPORTANT` / `SUPERSEDED_OR_CLOSED_BRANCH`

The following documents are retained for audit trail but are superseded for active decision-making. They must not be cited as current results. Rows under a closed-branch DEC
(communities, P6, geographic/mobility graph, graph-temporal, Phase 5 L2 corrector) are
`SUPERSEDED_OR_CLOSED_BRANCH`; everything else in this section is `HISTORICAL_BUT_IMPORTANT`
(it explains the path to the current state even though it isn't itself a closed gate).

### Superseded by later phases
| Document | Superseded by |
|----------|--------------|
| `reports/HERALD_PHASE4H_B_RESULTS_AUDIT.md` | Phase 4N (corrected causal baseline) |
| `reports/HERALD_PHASE4I_A_RESULTS_AUDIT.md` | Phase 4N |
| `reports/HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md` | Not promoted (DEC-004) |
| `reports/HERALD_PHASE4G_*.md` | Superseded by 4H–4J |
| `reports/HERALD_PHASE4E_C_*.md` | Superseded by 4N |
| `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` | Schema 1.0 — superseded by schema 2.0 (DEC-028) |
| `reports/HERALD_G2_PREFLIGHT.md` | Superseded by full corrected controls audit |
| `reports/HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md` | Partially superseded by L2/L3 specific audits |
| `reports/HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md` | G1-L1 NOT_SUPPORTED (DEC-017); historical |
| `reports/HERALD_PHASE4D_DATA_AND_GRAPH_AUDIT.md` | Leaky (Phase 4A/4D affected) |
| All `reports/HERALD_PHASE2*.md` (except 2R) | Exploratory architecture search history |
| All `reports/HERALD_PHASE3*.md` (except 3E) | Steps toward 3E |

### `DO_NOT_START_HERE` — Legacy (pre-2026 or v3/v4/v5)
- `reports/archive/herald_v4/`, `reports/archive/herald_v5/` — archived
- `reports/ATLAS_IAT_*.md` — pre-HERALD project, historical only

### Documents with P6 / A1 language (status corrected by DEC-029/030/031)
- Any document referencing "P6 pending" must be read in light of DEC-029 (P6 FAIL).
- Any document referencing "S1-FR BLOCKED" or "A1 pending implementation" must be read in light of DEC-031 (S1_FR_FAIL; branch closed).

---

## P6 Sector Label Status

`data/processed/dual_graph_s1/learned_sector_edges.csv` uses sector names (AZ, BE, C, DE, GI, JZ, KZ, LZ, MN) that do not match tensor sector_ids (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU). Source of mapping unverifiable.

**Status: INVALID_FOR_INTERPRETATION.** Preserved as historical artefact. Index-based gate metrics remain valid.

---

## WMAPE 0.0204 France — PENDING_REAUDIT

The French WMAPE 0.0204 (HERALD Q7, Phase 3E) uses French SIDE/SIRENE data. **Status: PENDING_REAUDIT.** The causal audit of the full Phase 3E/2R pipeline features (`growth_1y/2y`, `effectifs_lag1`) is not yet formally complete for the French track. This result must not be cited as a headline claim until the audit is done. Scope limitation still applies: France only, 2021–2025, rolling-window.

---

## File Naming Policy

Active documents: `reports/HERALD_*.md`
Archived documents: `reports/archive/<phase>/` or marked SUPERSEDED in this index.
Do not create new Phase-N reports without a corresponding DEC-* entry.

---

## Appendix — Exhaustive classification of all remaining `reports/*.md` files (2026-06-18)

The sections above predate several phases and do not mention every report file in the
repository. This appendix closes that gap: every `reports/*.md` not already named above is
classified here by pattern, cross-checked against the decision log. None of these were
read in full for this pass (only their phase/decision context was checked) — if a specific
claim from one of these files needs to be cited, re-verify it against the decision log first.

### `CURRENT_SCIENTIFIC_EVIDENCE` — research track (DEC-048→DEC-062, real-data and synthetic relation-learning)
| Document | Covers |
|----------|--------|
| `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md` | DEC-048 training-budget diagnostic |
| `reports/HERALD_DEC049_CONVERGENCE_AUDIT.md` | DEC-049 (superseded by DEC-050, kept for traceability) |
| `reports/HERALD_DEC050_BUG_AUDIT.md` | DEC-050 bug fixes + corrected run |
| `reports/HERALD_DEC051_STABLE_OBJECTIVE_AUDIT.md` | DEC-051/052 stable-objective + NT audit |
| `reports/HERALD_DEC053_DECOUPLED_GRAPH_AUDIT.md` | DEC-053 decoupled graph (superseded by DEC-054 for utility gate question) |
| `reports/HERALD_DEC054_UTILITY_GATE_OOS_AUDIT.md` | DEC-054 utility gate OOS — UTILITY_GATE_NOT_SUPPORTED |
| `reports/HERALD_DEC055_SHARED_RELATION_ENCODER.md` | DEC-055 SharedRelationEncoder — synthetic, SUPPORTED |
| `reports/HERALD_DEC056_REAL_SHARED_RELATION_AUDIT.md` | DEC-056 real-data validation — REAL_SHARED_RELATION_PARTIAL |
| `reports/HERALD_REAL_RELATION_LEARNING_RESEARCH.md` | DEC-057 corrected research direction (RESEARCH_ONLY) |
| `reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md` | DEC-058 weak-label tuning (corrected by DEC-059) |
| `reports/HERALD_DEC059_WEAK_LABEL_REVALIDATION.md` | DEC-059 revalidation — REAL_WEAK_LABEL_TUNING_PARTIAL |
| `reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md` | DEC-060 — already listed above |
| `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md` | DEC-061 PT/NL municipal granularity audit — **note: this file exists and is referenced extensively by DEC-062, but DEC-061 has no standalone `## DEC-061` heading in `HERALD_METHODOLOGICAL_DECISION_LOG.md`. Recorded as a finding, not fixed.** |
| `reports/HERALD_DEC062_GRANULAR_PHASE7_PREFLIGHT.md` | DEC-062 — already listed above |
| `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_DRAFT.md` | Superseded draft — DEC-065 final audit is `HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md` (already listed above) |
| `reports/HERALD_POST_DEC045_ARCHITECTURE_RESEARCH.md` | DEC-046 research-only architecture survey |
| `reports/HERALD_FEWSHOT_ADAPTATION_CONTRACT.md`, `reports/HERALD_FEWSHOT_ADAPTATION_PILOT.md` | DEC-047 few-shot adaptation (FEWSHOT_ADAPTATION_FAILED) |
| `reports/HERALD_PHASE9_GRAPH_USAGE_DIAGNOSTIC.md` | DEC-042 graph usage diagnostic |
| `reports/HERALD_PHASE10_LAGGED_CONTRACT.md`, `..._RESULTS.md`, `..._METRIC_RECONCILIATION.md`, `..._SIGNAL_SENSITIVITY.md` | DEC-043/044 Phase 10 lagged graph (PHASE10_PARTIAL) |
| `reports/HERALD_PHASE11_SYNTHETIC_GENERALIZATION.md` | DEC-045 Phase 11 generalization protocol |
| `reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md` | DEC-039/040 synthetic benchmark contract |

**Status for this group: ACTIVE SCIENTIFIC RESULTS**, all on the synthetic/real relation-learning research track described in `HERALD_CURRENT_STATE.md`'s "Graph/neural layer" row (~20% complete, useful on synthetic data, partial on real data, not a final claim).

### `SOURCE_AUDITS` — Phase 2 (France architecture search, pre-Q7)
`HERALD_PHASE2B_A10_GUARD_AUDIT.md`, `HERALD_PHASE2C_CRITICAL_AUDIT.md`, `HERALD_PHASE2D_STABILITY_PLAN.md`,
`HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md`, `HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md`,
`HERALD_PHASE2L_LATENT_DIM_FINE_AUDIT.md`, `HERALD_PHASE2M_AUTOREG_AUDIT.md`,
`HERALD_PHASE2O_2P_2Q_AUDIT.md`, `HERALD_PHASE2O_2P_2Q_PLAN.md`, `HERALD_PHASE2R_CONFIRMATORY_PLAN.md` —
all exploratory steps superseded by Phase 3E/Q7 selection, per the existing rule
"All `reports/HERALD_PHASE2*.md` (except 2R)" above; `HERALD_PHASE2R_CONFIRMATORY_PLAN.md` is the
plan counterpart to the already-ACTIVE `HERALD_PHASE2R_CONFIRMATORY_AUDIT.md`.

### `SOURCE_AUDITS` — Phase 3 (France q_tensor/labor pre-3E)
`HERALD_PHASE3C_LABOR_TUTOR_AUDIT.md`, `HERALD_PHASE3C_LABOR_TUTOR_DATA_STATUS.md`,
`HERALD_PHASE3C_MISSING_DATA_DOWNLOAD_AUDIT.md`, `HERALD_PHASE3C_URSSAF_METHOD_AUDIT.md`,
`HERALD_PHASE3D_QTENSOR_PLAN.md`, `HERALD_PHASE3E_QTENSOR_ARCH_PLAN.md`,
`HERALD_PHASE3_TUTOR_BLOCK_A_AUDIT.md` — steps toward 3E, per the existing rule "All
`reports/HERALD_PHASE3*.md` (except 3E)" above.

### `HISTORICAL_BUT_IMPORTANT` — Phase 4 (international generalization, pre-4N or non-canonical sub-steps)
`HERALD_PHASE4_COVERAGE_MASK_PLAN.md`, `HERALD_PHASE4_DATA_VERIFICATION.md`,
`HERALD_PHASE4_INTERNATIONAL_PLAN.md`, `HERALD_PHASE4_NEXT_STEP_INDEPENDENT_AUDIT.md`,
`HERALD_PHASE4E_B_FEATURE_POLICY_PLAN.md`, `HERALD_PHASE4E_C_EU_SIGNALS_PLAN.md`,
`HERALD_PHASE4E_C_RESULTS_AUDIT.md` (superseded by 4N), `HERALD_PHASE4E_F_GRAPH_REACTIVATION_PLAN.md`,
`HERALD_PHASE4E_MISSING_DATA_SEARCH.md`, `HERALD_PHASE4E_PT_2024_EXTENSION_AUDIT.md`,
`HERALD_PHASE4G_B_COUNTRY_BALANCE_PLAN.md`, `HERALD_PHASE4G_C_CONFIRMATION_PLAN.md`,
`HERALD_PHASE4G_JOINT_EUROPE_PLAN.md`, `HERALD_PHASE4H_CODE_CONCEPT_AUDIT_2026.md`,
`HERALD_PHASE4H_LOCO_PLAN.md`, `HERALD_PHASE4I_SELECTIVE_TRANSFER_PLAN.md`,
`HERALD_PHASE4J_CANONICAL_REGISTRY_AUDIT.md`, `HERALD_PHASE4J_PATH_M_PROTOCOL.md`,
`HERALD_PHASE4J_TARGET_AWARE_RESULTS.md`, `HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`,
`HERALD_PHASE4K_ENTERPRISE_BIRTH_COUNTRY_PREFLIGHT.md`, `HERALD_PHASE4L_ITALY_SEMANTIC_AUDIT.md`,
`HERALD_PHASE4L_PT_IT_PANEL_AUDIT.md`, `HERALD_PHASE4M_THIRD_COUNTRY_PREFLIGHT.md`,
`HERALD_PHASE4N_HARMONIZED_LOCO_PLAN.md` (plan counterpart to the ACTIVE `..._RESULTS_AUDIT.md`),
`HERALD_PHASE4O_RESIDUAL_SPATIAL_DIAGNOSTIC.md` (plan counterpart to ACTIVE `..._B_RESIDUAL_SPATIAL_AUDIT.md`),
`HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_PLAN.md` (plan counterpart to ACTIVE `..._AUDIT.md`) —
all intermediate plans/audits feeding into the canonical 4M/4N/4O/4P/4Q results already
classified ACTIVE above. Kept for audit trail, not citable as standalone results.

### `SUPERSEDED_OR_CLOSED_BRANCH` — Dual graph / regime / V7 architecture search (pre-P6, pre-DEC-029)
`HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md`, `HERALD_DUAL_GRAPH_MODEL_AUDIT.md`,
`HERALD_DUAL_GRAPH_TARGET_AUDIT.md`, `HERALD_DUAL_GRAPH_TENSOR_AUDIT.md`,
`HERALD_DUAL_GRAPH_TRAINER_AUDIT.md` — preflight/design docs for P6, superseded by the
final `HERALD_DUAL_GRAPH_S1_RESULTS.md`/`HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md` (DUAL_GRAPH_S1_FAIL,
already ACTIVE/closed-branch above).
`HERALD_GRAPH_TEMPORAL_ARCHITECTURE_REVIEW.md` — superseded by `HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md` (DEC-027, already ACTIVE above).
`HERALD_REGIME_ARCHITECTURE_REVIEW.md`, `HERALD_REGIME_DISCOVERY_BATTERY.md`,
`HERALD_REGIME_PHASE2C_CRITICAL_PLAN.md`, `HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md`,
`HERALD_V7_RESEARCH_PLAN.md`, `HERALD_V7_TRAINING_BATTERY.md`,
`HERALD_SEMI_V2_VALIDATION_BATTERY.md`, `HERALD_ECONOMIC_STATE_TUTOR_PLAN.md` — France
regime-learner/V6/V7 architecture-search history predating the Q7 selection (Phase 3E);
historical only, not citable for current claims.
`HERALD_CURRENT_MODEL_DECISION_20260527.md` — historical France model-selection snapshot,
superseded by Phase 3E Q7 (already ACTIVE above via `HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md`).

### `SUPERSEDED_OR_CLOSED_BRANCH` / `HISTORICAL_BUT_IMPORTANT` — Other closed/early-exploration branches
`HERALD_ECONOGNN_TRANSFERABILITY_AUDIT.md` — EconoGNN reference audit, concluded `REFERENCE_ONLY` (see CODEX_MEMORY DEC-028 section); historical.
`HERALD_ARDECO_FR_EXTENSION_CONTRACT.md`, `HERALD_ARDECO_RIDGE_FR_AUDIT.md` — ARDECO extension exploration, not part of the current canonical pipeline; historical.
`HERALD_AUTO_REGULATION_HYPOTHESIS_AUDIT.md`, `HERALD_RARE_REBOUND_DATA_AUDIT.md`,
`HERALD_2021_INSTABILITY_DIAGNOSIS.md`, `HERALD_2021_STABILITY_LITERATURE_REVIEW.md`,
`HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md` — France 2021-instability diagnostic
branch, historical, predates the current causal-baseline framing.
`HERALD_PREDICTION_INTERPRETATION_METHODS.md` — general methods survey, historical reference only.
`HERALD_EUROPEAN_PANEL_ADAPTER_AUDIT.md`, `HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md`,
`HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md` (already covered by the DEC-038 entry above
under a different filename pattern — `reports/HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md`
IS the DEC-038 report, status ACTIVE, not historical) — adapter/standard-plan docs are
historical design notes superseded by the actually-built `src/data/european_panel/` adapters.
`HERALD_G1_SECTOR_DATA_PREFLIGHT.md` — superseded by the canonical sector panel build (G0/G1 contract docs already ACTIVE above).
`HERALD_G2_DASHBOARD_INTEGRATION_SPEC.md`, `HERALD_G2_REPORT_FIGURE_SELECTION.md`,
`HERALD_G2_REPORT_SECTION_FR.md` — G2 write-up planning docs, historical (G2 results
already classified ACTIVE via `HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md`/`HERALD_G2_COVID_SENSITIVITY_AUDIT.md`).
`HERALD_INTELLIGENCE_LAYER_SPEC.md` — ARCHIVED per the artifact registry (`status: ARCHIVED`); structural reference only for future Bloco 3, not an active capability.
`HERALD_DATA_AVAILABILITY_CALENDAR.md`, `HERALD_DATA_RESEARCH_REPORT.md` — early data-scoping notes, historical.

### `DO_NOT_START_HERE` — Regenerable / operational (not scientific reports)
`HERALD_HPC_ORGANIZATION_AUDIT.md` — HPC directory organization audit; operational reference, regenerate-on-reorg only.
`HERALD_DASHBOARD_FINAL_IMPLEMENTATION_PLAN.md`, `HERALD_DASHBOARD_PRESENTATION_SPEC.md`,
`DASHBOARD_TODO.md` — pre-Observatory dashboard planning notes (France-only era); superseded
by the Observatory v0.1→v0.5.1 contracts already listed as ACTIVE above.
`HERALD_REPOSITORY_AND_DASHBOARD_CLEANUP_PLAN.md`, `HERALD_REPOSITORY_CLEANUP_20260526.md`,
`reports/REPOSITORY_CLEANUP_20260519.md` — prior repo-cleanup passes; historical record of
earlier consolidation efforts (this 2026-06-18 pass is the latest in that lineage).

### `DO_NOT_START_HERE` — Out of HERALD scope (pre-HERALD project, already noted above)
`ATLAS_IAT_ANNUAL_RECONSTRUCTION_STANDBY.md`, `ATLAS_IAT_DATABASE_AUDIT.md`,
`ATLAS_IAT_DYNAMIC_INTELLIGENCE_PLAN.md`, `ATLAS_IAT_SOURCE_REPRODUCIBILITY_AUDIT.md`,
`ATLAS_IAT_STATIC_LAYER_AUDIT.md`, `ATLAS_IAT_TO_HERALD_EXPERIMENT_PLAN.md` — already
covered by the existing rule "`reports/ATLAS_IAT_*.md` — pre-HERALD project, historical only".

### Blocked/invalid for interpretation (cross-reference)
No additional files beyond what is already listed above (`learned_sector_edges.csv` and its
governing Charter §6 entry, and the NL gemeente proxy DEC-065 entries). This appendix found
no other report claiming a blocked/invalid result that wasn't already flagged.
