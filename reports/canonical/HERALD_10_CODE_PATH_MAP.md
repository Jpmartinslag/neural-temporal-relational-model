# HERALD 10 — Code Path Map

**Created:** 2026-06-18 (post-consolidation structural mapping).
**Method:** audited by module/file name only. No script was renamed or moved. Claims
about results come from the decision log and canonicals, not from reading code logic.
**Rule:** A script existing and importing cleanly does not mean its output is a
validated claim — check the corresponding DEC-* entry before citing any number it
produces.

---

## ACTIVE_INGESTION

| Path | Country/source | Notes |
|---|---|---|
| `src/data/ingest_belgium_panel.py`, `ingest_italy_panel.py`, `ingest_netherlands_panel.py`, `ingest_portugal_panel.py`, `ingest_portugal_panel_nuts3.py` | BE/IT/NL/PT | Per-country raw-to-panel ingestion |
| `src/data/ingest_eurostat_enterprise_birth_panel.py` | Eurostat | DEC-038 27-country coverage source |
| `src/data/european_panel/adapters/{at,be,france,it,nl,pt}_adapter.py` | AT/BE/FR/IT/NL/PT | Canonical per-country adapters into the harmonized European panel schema |
| `src/data/european_panel/ingest_nl_gemeente_stock_panel.py`, `search_nl_gemeente_birth_sources.py` | NL | Gemeente stock ingestion + the CBS catalog search behind DEC-061/062's "NL blocked" finding |
| `src/data/european_panel/build_nl_cbs_sector_births.py` | NL | CBS 83631NED sector-births ingestion |

## ACTIVE_PANEL_BUILD

| Path | Output | DEC |
|---|---|---|
| `src/data/france_ze2020/build_fr_ze2020_relational_model_ready_panel.py` | FR ZE2020 relational MVP2 panel (Category A trajectory similarity only) | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 10 -- smoke/exploratory, not a headline claim |
| `src/data/france_ze2020/build_fr_ze2020_sector_panel.py`, `build_fr_ze2020_sector_relational_features.py`, `build_fr_ze2020_relational_sector_prototype_panel.py` | FR ZE2020 sector composition / causal sector features / Category A+C integration (MVP2 Categoria C) | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 11 -- prototype, not a headline claim, not a graph |
| `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py`, `build_fr_ze2020_exploratory_relation_examples.py` | Relational analysis layer (NOT a model) -- extracts/reorganizes already-computed relation/feature signals into one interpretable table | New 2026-06-24, see `HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md` -- deterministic, no training, `claim_status=exploratory_association_not_causal` |
| `src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py` | Dynamic graph input bundle: `fr_ze2020_dynamic_graph_nodes.csv`, `fr_ze2020_dynamic_graph_edges.csv`, `fr_ze2020_dynamic_graph_splits.csv` | New 2026-07-01, see `HERALD_25_FR_ZE2020_DYNAMIC_GRAPH_MODEL_SPEC.md` -- input construction only, no model trained, no recommendation, no causal claim |
| `src/data/european_panel/build_european_panel.py` | Canonical FR/NL/BE/PT panel | DEC-002/003 |
| `src/data/european_panel/build_enterprise_birth_subpanel.py` | Path H PT/IT/AT harmonized panel | DEC-005 |
| `src/data/european_panel/build_fr_nuts3_sector_panel.py`, `build_pt_municipal_sector_panel.py` | FR NUTS3, PT municipal sector panels | DEC-062/064 |
| `src/data/european_panel/build_pt_municipal_phase7_panel.py`, `build_nl_gemeente_phase7_panel.py`, `build_nl_gemeente_birth_proxy.py` | PT municipal / NL gemeente proxy Phase 7 panels | DEC-063/064/065 — **the NL gemeente proxy builder's output is BLOCKED for relation labels, not the builder itself** |
| `src/data/european_panel/build_granular_training_matrix.py` | Granular FR/PT/NL evidence model input | DEC-063 |
| `src/data/european_panel/build_pt_municipality_geometry.py` | PT continental municipality GeoJSON | Observatory v0.4.1 |
| `src/data/european_panel/build_pt_eurostat_employment_tensor.py`, `build_be_onss_qtensor_extension.py` | PT/BE employment tensors | Phase 4E |

## ACTIVE_PREDICTION

| Path | Output | DEC |
|---|---|---|
| `src/data/european_panel/build_pt_municipal_prediction_layer.py` | PT municipal causal persistence/Ridge forecast (no proxy, no HPC) | DEC-068 |
| `src/modeles/sector_baselines_v1.py`, `train_temporal_baselines_v1.py` | Persistence/Ridge baselines | DEC-006 |
| `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` | FR ZE2020 minimal current baseline: persistence + Ridge(lag-only), reads `fr_ze2020_model_ready_panel.csv` only, never the legacy `dynamic_stgnn_feature_panel_v1.csv` | New 2026-06-24, see `HERALD_16_MODEL_TRAINING_BLOCK_AUDIT.md` — explicitly exploratory/smoke, not a headline claim |
| `src/modeles/france_ze2020/train_fr_ze2020_relational_baselines.py` | MVP2 relational smoke comparison: persistence vs. ridge_temporal (reuses the script above, not modified) vs. ridge_relational (+3 trajectory-similarity features) | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 10 — relational features did not beat either baseline in this smoke run; `claim_status=relational_smoke_result` |
| `src/modeles/france_ze2020/train_fr_ze2020_neural_relational_mlp.py` | MVP3-A neural relational smoke: sklearn MLPRegressor (PyTorch not installed, no heavy dependency added) over 17 temporal/ZE-to-ZE/sector features, ratio-target reconstruction (`RatioToLevelMLP`) | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 12 — did not beat any baseline in this smoke run; `claim_status=neural_relational_smoke`; gap backfilled into this map by `HERALD_18_FR_ZE2020_TRAINING_PLAN.md` |
| `src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py` | MVP3-B sector graph smoke: ZE2020 x sector nodes (2,520 unique, 35,280 node-year rows), 2 manual message-passing edge types + sklearn MLPRegressor | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 12 — did not beat `persistence_sector` in this smoke run; `claim_status=sector_graph_smoke`; gap backfilled into this map by `HERALD_18_FR_ZE2020_TRAINING_PLAN.md` |
| `src/modeles/france_ze2020/run_fr_ze2020_training_block.py` | Training block orchestrator -- imports and calls the 4 scripts above, no new model, consolidates metrics into one summary CSV | New 2026-06-24, see `HERALD_18_FR_ZE2020_TRAINING_PLAN.md` — `claim_status=training_block_summary_smoke_local_only` |
| `hpc/france_ze2020/run_fr_ze2020_hpc_task.sh`, `run_fr_ze2020_hpc_array.sbatch`, `submit_fr_ze2020_hpc.sh`, `smoke_test_fr_ze2020_hpc.sh` | meso Slurm array (5 seeds) calling the 4 training scripts above via their own CLIs -- no new model; `submit_fr_ze2020_hpc.sh` only calls `sbatch` with `--confirm-submit` | New 2026-06-24, see `HERALD_19_FR_ZE2020_HPC_SPEC.md` — `SPEC_READY`, **not launched** |
| `hpc/france_ze2020/audit_fr_ze2020_hpc_results.py` | Post-collection gate audit (G1-G5), descriptive only, no auto-promotion | New 2026-06-24, see `HERALD_19_FR_ZE2020_HPC_SPEC.md` section 6; tested (`tests/test_fr_ze2020_hpc_audit.py`) |
| `src/modeles/france_ze2020/export_fr_ze2020_relational_prototype_examples.py` | MVP2 Categoria C exploratory export: observed value + persistence baseline + ZE-to-ZE signal + ZE-to-sector signal + deterministic template note per row | New 2026-06-24, see `HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` section 11 — presentation-only, no recommendation, no causal claim |
| `src/modeles/run_ardeco_ridge_fr.py` | ARDECO-extended FR Ridge | Closed exploration (HERALD_ARDECO_* reports, removed from index) |
| `src/analyse/02_ridge_ar_official.py`, `01_sector_baselines.py`, `03_select_gate.py` | France Ridge AR / sector baselines / gate selection | Pre-Q7 architecture search |

## ACTIVE_RELATION_EVIDENCE

| Path | Output | DEC |
|---|---|---|
| `src/data/european_panel/build_sector_precedence_graph.py` | Phase 7 sector→sector edges (original scale) | DEC-033/034 |
| `src/data/european_panel/gates_dec061_municipal_granularity.py`, `gates_dec062_granular_preflight.py`, `gates_dec063_granular_evidence.py` | Granularity/evidence-model gate evaluators | DEC-061/062/063 |
| `src/modeles/real_world/gates_dec060_france_audit.py`, `run_dec060_france_signal_audit.py` | France relation signal recovery audit | DEC-060 |
| `src/modeles/real_world/gates_dec064_pt_municipal_phase7.py`, `run_dec064_pt_municipal_phase7.py`, `prepare_dec064_hpc_manifest.py` | PT Municipal Phase 7 | DEC-064 |
| `src/modeles/real_world/merge_nl_gemeente_proxy_phase7.py`, `preflight_granular_phase7.py` | NL gemeente proxy Phase 7 merge/preflight | DEC-065 — **merges proxy results that are themselves BLOCKED for training; script is fine, output is not promotable** |
| `src/modeles/real_world/phase7_threshold_calibration.py` | Fine-grain threshold policy (4-tier) | DEC-066 |
| `src/data/european_panel/build_g1_l2_cogrowth.py`, `build_g1_communities.py`, `build_g1_l1_sector_graph.py`, `build_g1_observable_graph.py`, `build_g2_aggregate_dynamics.py`, `build_g2_corrected_controls.py`, `build_g2_temporal_preflight.py`, `build_dynamic_sector_preflight.py` | G1/G2 territorial graph layers | DEC-017/019/020/021/023/024/025 |
| `src/data/european_panel/build_territorial_sector_movements.py` | Phase 8 territorial influence decomposition (LOTO) | DEC-037 |

## ACTIVE_OBSERVATORY_EXPORT

| Path | Output | DEC |
|---|---|---|
| `src/data/european_panel/build_observatory_export.py`, `build_observatory_v03.py` | Observatory v0.1.1/v0.2/v0.3 exports | DEC-032/035 |
| `src/data/european_panel/build_observatory_v04_granular_exports.py` | v0.4 granular exports (the three CSVs in canonical #9 §1) | DEC-063/065 |
| `src/data/european_panel/build_observatory_v05_narrative_exports.py`, `build_observatory_v051_narrative_exports.py` | v0.5/v0.5.1 narrative exports | DEC-067/068 |
| `src/data/european_panel/audit_european_sector_coverage.py` | DEC-038 27-country preflight | DEC-038 |

## ACTIVE_DASHBOARD_BUILD

| Path | Output | Status |
|---|---|---|
| `src/data/european_panel/build_observatory_v04_dashboard.py` | v0.4/v0.4.1 dashboard | ACTIVE, stable baseline |
| `src/data/european_panel/build_observatory_v05_narrative_dashboard.py` | v0.5 dashboard | HISTORICAL (rejected UX, superseded) |
| `src/data/european_panel/build_observatory_v051_narrative_dashboard.py` + `_template.py` | v0.5.1 dashboard | Current candidate, not final |
| `src/data/france_ze2020/build_fr_ze2020_dashboard_mvp.py` | `fr_ze2020_dashboard_mvp.html` -- France ZE2020-only MVP (map, prediction-as-control, sector view, exploratory relation graph) | New 2026-06-24, see `HERALD_22_FR_ZE2020_DASHBOARD_MVP.md` -- separate from the Observatory dashboards above, no causal/recommendation language, no fabricated prediction |

## HISTORICAL_EXPERIMENT (pre-Q7 France architecture search, superseded)

`src/modeles/train_herald_v3.py` ... `v7.py`, `train_herald_semi_v1.py`/`v2.py`,
`train_herald_regime_experiment.py`, `train_dynamic_stgnn_models_v1.py`,
`build_dynamic_stgnn_feature_panel_v1.py`, `integrate_side_2025_for_herald_v6.py`,
`src/modeles/herald_regime_modes.py`, `src/data/build_herald_phase3c_labor_tutor_features.py`,
`src/data/build_phase2h_macro_panel.py`,
`src/analyse/analyze_herald_v3_statistical_evidence.py`,
`src/analyse/evaluate_dynamic_feature_panel_baselines_v1.py`,
`src/analyse/summarize_herald_semi_total.py`,
`src/visualisation/generate_herald_geo2025_dashboard.py`,
`generate_herald_phase4_dashboard.py`, `generate_herald_semi_v2_dashboard.py`,
`plot_herald_v3_dashboard.py`, `plot_herald_v3_v6_dashboard.py`,
`plot_herald_v6_2025_dashboard.py`
— all predate Q7 selection (Phase 3E); kept for traceability and, for the later
`v6`/`v7`/`semi_v2`/`regime_experiment` cluster, as **historical architecture-improvement
attempts** showing where the model design went. They are not safe to reuse for current
claims without re-validating against the current causal protocol (DEC-001 leakage
discipline) and the clean France ZE2020 model-ready panel. Full file-by-file
entrada/saída/model-type table, plus the import-chain detail (`v7`/`semi_v2`/
`regime_experiment`/`sector_baselines_v1`/`run_herald_prospective_forecast_v1` all
transitively depend on `train_herald_v6.py`'s `PANEL_PATH`):
`reports/canonical/HERALD_16_MODEL_TRAINING_BLOCK_AUDIT.md` §1.

## CLOSED_BRANCH (reopening requires a new DEC, Charter §8)

| Path | Branch | DEC |
|---|---|---|
| `src/data/european_panel/build_dual_graph_tensors.py`, `audit_dual_graph_targets.py`, `src/modeles/train_dual_graph_experiment.py`, `dual_graph_models.py`, `run_dual_graph_pilot.py`, `run_dual_graph_smoke.py` | P6 dynamic dual graph | DEC-029, `DUAL_GRAPH_S1_FAIL` |
| `src/data/european_panel/build_graph_temporal_preflight.py`, `build_graph_temporal_v2.py`, `src/modeles/graph_temporal_models.py`, `graph_temporal_train.py`, `run_e0_smoke_nl.py`/`_v2.py`, `run_s0_fr_smoke.py`, `run_s1_fr_local.py` | Graph-temporal GConvGRU/EvolveGCN-H | DEC-031, `S1_FR_FAIL` |
| `src/modeles/phase5/corrector.py`, `l2_pool.py`, `neural_corrector.py`, `rolling_origin.py`, `manifest.py` | Phase 5 fixed-L2 residual corrector | DEC-023, `NOT_SUPPORTED` |
| `data/external/build_phase4c_adjacency.py`, `build_phase4d_commuting_graph.py`, `build_phase4d_sector_similarity.py` | Geographic/functional graph (queen-contiguity, commuting) | DEC-008/009, FAIL |
| `src/modeles/run_ardeco_ridge_fr.py`, `src/data/european_panel/audit_ardeco_fr_extension.py` | ARDECO FR extension | Closed exploration |

## Research track (PARTIAL — not CLOSED, not promoted, not in any dashboard)

| Path | Sub-phase | DEC |
|---|---|---|
| `src/modeles/synthetic/` (whole tree: `phase11_generalization/`, `phase12_few_shot/`, `phase13_diagnostic/`, `phase14_convergence/`, `phase15_stable_objective/`, `phase16_decoupled/`, plus `gates*.py`, `herald_graph_imputer*.py`, `run_*.py`) | Synthetic benchmark + SharedRelationEncoder research line | DEC-039→059 |
| `src/modeles/real_world/build_phase7_weak_labels.py`, `train_real_relation_weak_labels.py`, `run_shared_relation_real.py`, `run_p0_checkpointed.py`, `gates_dec058.py`, `gates_dec059.py`, `run_dec059_weak_label_revalidation.py` | Real-data weak-label fine-tuning | DEC-056/058/059, `REAL_WEAK_LABEL_TUNING_PARTIAL` |

This entire research track requires **synthetic data or real-data weak labels with a
documented PARTIAL verdict** — none of it is wired into the Observatory dashboard, and
none of it should be cited as a validated real-data relation-learning result.

## UTILITY

| Path | Purpose |
|---|---|
| `src/data/european_panel/schema.py`, `validation.py`, `territorial_scope.py`, `eurostat_jsonstat.py` | Shared schema/validation/scope helpers |
| `src/data/european_panel/eu_signals/` (whole subtree) | EU macro-signal fetchers (ECB/Eurostat/EC-BCS), feeding Phase 4E-C |
| `src/data/phase4_preflight.py` | Phase 4 preflight helper |
| `src/data/synthetic/generate_herald_synthetic.py` | Synthetic-benchmark data generator (Phase 9 base) |
| `src/modeles/herald_fold_controls.py`, `herald_map_utils.py` | Shared fold/map utilities |
| `src/data/european_panel/preflight_enterprise_birth_candidates.py` | Country-eligibility preflight helper (DEC-038-adjacent) |

## UNKNOWN_NEEDS_REVIEW

None identified — every `src/*.py` file found in this audit mapped cleanly to one of
the categories above via its name and the decision log. If a future script doesn't fit,
add it here rather than guessing its category.

---

## Cross-reference

- Data this code reads/writes: `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
- HPC jobs that ran this code: `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md`
- What's safe to claim from any of this: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
