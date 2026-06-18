# HERALD 09 — Data Asset Map

**Created:** 2026-06-18 (post-consolidation structural mapping).
**Method:** audited by path, folder structure, and file size only — large files were not
opened. No data was moved, renamed, or deleted to produce this map.
**Status:** Documentation only. If this map disagrees with
`reports/herald_artifact_registry.json` on any specific artifact's status, the registry
wins — it is the authoritative per-artifact source.

---

## 1. Canonical data (used in canonical claims / current dashboard)

| Path | Country/phase | Type | Trainable? | Visualizable? | Justifying doc/DEC |
|---|---|---|---|---|---|
| `data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv` | FR/PT/NL, all grains | observed + proxy (tagged) | Per-row tag governs; proxy rows context-only | Yes | DEC-063/065, canonical #2 |
| `data/processed/herald_observatory_v04_granular/granular_relation_edges.csv` | FR ZE2020=9, NL COROP=8, PT Municipal=3 | observed | Yes (DEC-066 tiers) | Yes | DEC-034/064/066 |
| `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv` | NL gemeente proxy, 121 rows | proxy, structurally invalid | **No** | Context-only, must show `BLOCKED_PROXY_ARTIFACT` tag | DEC-065 |
| `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv` | PT/IT/AT, Path H | observed | Yes (LOCO baseline) | Yes | DEC-005/006, canonical #1 |
| `data/processed/european_panel/pt_municipal_sector_panel.csv` | PT, 278 municipalities (`PT_MUNICIPALITY_CONTINENTE`) | observed | Yes | Yes | DEC-062/064 |
| `data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv` | NL, 355 gemeenten | **proxy_disaggregated_by_stock_share** | **No** (relation labels) | Context-only | DEC-063/065 |
| `data/processed/phase7_pt_municipal/results/covid_robust_edges.csv` | PT Municipal, 2 pairs | observed, COVID-robust | Yes | Yes | DEC-064 |
| `data/processed/sector_precedence_results/covid_robust_edges.csv` | FR/NL/PT original-scale Phase 7 | observed | Yes | Yes | DEC-034 |
| `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json` | All countries | policy artefact | n/a (defines the rule, not a label) | n/a | DEC-066 |
| `data/processed/geometries/pt_municipalities_continental.geojson` | PT, 278 features | observed geometry | n/a | Yes (map rendering) | Observatory v0.4.1 |

## 2. Valid processed data (not yet a headline claim, but observed and usable)

| Path | Country/phase | Notes |
|---|---|---|
| `data/processed/european_panel/at_panel.csv`, `be_panel.csv`, `france_panel.csv`, `fr_nuts3_panel.csv`, `it_panel.csv`, `nl_panel.csv`, `pt_panel.csv` | per-country canonical panels | Inputs to the European panel adapters (DEC-002); BE remains target-heterogeneous (DEC-003) |
| `data/processed/european_panel/european_panel_all.csv` | pooled FR/NL/BE/PT | **Pooled WMAPE from this file is sensitivity-only**, never a primary result (Charter §5, DEC-003) |
| `data/processed/european_panel/european_sector_coverage_matrix.csv` | 27-country preflight | DEC-038 eligibility classification, no model trained from it |
| `data/processed/economic_graph/g1_l2_cogrowth/`, `g2_dynamics/` (under `g2_preflight/`) | FR/NL/PT | G1-L2/G2 validated analytical graph artefacts (DEC-019/020/024/025) |
| `data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv` | FR | the one `data/raw/` file explicitly kept tracked (per `.gitignore`); feeds the France q_tensor |

## 3. Raw data, regenerable (gitignored or large, not committed)

| Path | Notes |
|---|---|
| `data/raw/` (28 GB total) | Almost entirely gitignored except the URSSAF file above. Regenerate via `src/data/ingest_*` scripts. Includes business_demography/SIDE, business_registry/SIRENE, census, territorial (ZE2020 shapefiles), population, policy (QPV/ZRR/ZAN), phase3c_labor_tutor raw signals — all superseded inputs to closed or historical branches except where an active builder still reads them. |
| `data/external/*/raw/` (Portugal/Belgium/Italy/Netherlands/Eurostat raw downloads, ~579 MB external total) | Gitignored. Regenerate via the corresponding `src/data/european_panel/` or `src/data/ingest_*` script. |
| `data/interim/tables/` (142 MB total) | Intermediate France ingestion tables (BPE, FILOSOFI, SIDE communal stocks/creations, SITADEL, RP census) feeding the pre-Q7/Q7 pipeline. Regenerable from `data/raw/` via ingestion scripts; not independently authoritative. |
| `data/interim/atlas_iat/` | Pre-HERALD ATLAS/IAT exploration tables — out of scope (see canonical #1 trajectory; ATLAS reports removed from git index, see deep audit) |
| Large narrative-dashboard exports under `data/processed/herald_observatory_v05*_narrative/*.json|*.csv` | Gitignored (tens of MB each); only `manifest.json` tracked. Regenerate via `build_observatory_v05*_narrative_exports.py`. |

## 4. Historical / superseded processed data

| Path | Status | Superseded by |
|---|---|---|
| `data/processed/european_panel/enterprise_birth_pt_it_panel.csv` | SUPERSEDED | `enterprise_birth_pt_it_at_mainland_panel.csv` (AT added, DEC-005) |
| `data/processed/dual_graph_s1/`, `dual_graph_pilot_all_folds/`, `dual_graph_preflight/`, `dual_graph_tensors/` | FROZEN/FAIL, historical only | `DUAL_GRAPH_S1_FAIL` (DEC-029) — index-based gate metrics remain numerically valid; sector edge labels `INVALID_FOR_INTERPRETATION` |
| `data/processed/graph_temporal_s0/`, `graph_temporal_s1/`, `graph_temporal_preflight/` | FROZEN/FAIL (S1) or superseded (preflight schema 1.0) | `S1_FR_FAIL` (DEC-031); `graph_temporal_v2/` is the active schema 2.0 |
| `data/processed/phase4/`, `phase4d/`, `phase4e/`, `phase4g/`, `phase5/` | Historical intermediate Phase 4/5 outputs | Final results are DEC-002/006/008/009/023, summarized in canonical #1/#4 |
| `data/processed/synthetic_benchmark/` (phase9-15 subfolders) | Research track, partial | DEC-039→059, summarized in canonical #3 §4b |
| `data/processed/real_dec059_results/`, `real_relation_weak_labels/`, `real_shared_relations/`, `real_shared_relations_checkpointed/`, `real_weak_label_results/` | Research track, partial (`REAL_WEAK_LABEL_TUNING_PARTIAL`) | DEC-055/056/058/059, canonical #3 §4 |
| `data/processed/herald_observatory_v01/`, `v02/`, `v03/`, `v04/` (pre-granular) | Historical Observatory milestones | `herald_observatory_v04_granular/` is the current stable export layer |
| `data/processed/herald_phase3c_labor_tutor_features.csv`, `phase2h_macro_annual_features_v1.csv`, `dynamic_stgnn_feature_panel*.csv`, `flores_panel_ze2020_annual_v1.csv`, `side_creations_a10_ze2020*.csv`, `side_stocks_lagged_ze2020_annual_v1.csv`, `target_side_establishments_annual_core*.csv` | Pre-Q7 France feature/target panels (V3-V7, Phase 2/3 search) | Superseded by the Q7 pipeline; kept for traceability of the pre-Q7 search |
| `data/processed/ardeco_extension/`, `france_relation_audit/`, `municipal_granularity_audit/`, `granular_phase7_preflight/` | Closed/superseded preflight or exploratory outputs | DEC-060/061/062 (granularity) absorb the relevant findings |
| `data/processed/phase16_dec053/`, `phase16_dec054/`, `phase16_dec055/` | Research-track checkpoints (SharedRelationEncoder) | DEC-053/054/055, canonical #3 §4 |
| `data/processed/graph_adjacency_*.csv`, `graph_edge*.csv`, `graph_node*.csv` (core_v0/ze2020_core_v0) | Early G0/G1 graph artefacts | Superseded by `economic_graph/` outputs |

## 5. Blocked for training (must never become a relation/training label)

| Path | Reason | DEC |
|---|---|---|
| `data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv` | Stock-share proxy injects spurious cross-sector correlation (`share_velocity` coef. 13.0 vs `corop_velocity` 1.33) | DEC-065 |
| `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv` | The 121 NL gemeente proxy edges, explicitly tagged `BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false` | DEC-065 |
| `data/processed/phase7_nl_gemeente_proxy/results/*` | Same proxy method, raw Phase 7 run outputs | DEC-065 |
| `data/processed/european_panel/european_panel_all.csv` (as a pooled training target) | Target heterogeneity across FR/NL/BE/PT — pooled WMAPE is sensitivity-only | DEC-003 |
| `data/processed/dual_graph_s1/learned_sector_edges.csv` | Sector name mapping does not match tensor `sector_id`s — `INVALID_FOR_INTERPRETATION` | Charter §6 |

---

## Cross-reference

- Artefact-level authoritative status: `reports/herald_artifact_registry.json`
- Evidence-tier vocabulary: `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`
- Code that builds/consumes these paths: `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
