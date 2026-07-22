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
| `src/data/france_ze2020/build_fr_ze2020_sector_panel.py`, `build_fr_ze2020_sector_relational_features.py`, `build_fr_ze2020_relational_sector_prototype_panel.py` | Official INSEE SIDE -> FR ZE2020 sector composition / causal sector features / Category A+C integration | First builder now reads the checksum-pinned SIDE ZIP directly and fails unless the nine A10 sectors reconcile exactly with the clean panel (DEC-076/HERALD_47). Downstream layers remain exploratory, not a headline claim or validated graph. |
| `src/data/france_ze2020/build_fr_ze2020_exploratory_relation_signals.py`, `build_fr_ze2020_exploratory_relation_examples.py` | Retrospective interpretation layer (NOT a model and forbidden as as-of-time model input) | New 2026-06-24; full-window summaries remain valid for descriptive use only. See `HERALD_20` and `HERALD_38` |
| `src/data/france_ze2020/build_fr_ze2020_temporal_relation_signals.py` | Leakage-safe annual relation snapshots with recurrence/stability calculated only from information available through each decision year | New 2026-07-13; canonical model relation input. See `HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md` |
| `src/data/france_ze2020/build_fr_ze2020_sector_ranking_panel.py` | Canonical ZE2020 x A10 sector ranking panel, including evaluation-only future targets and temporal relation features | Corrected 2026-07-13; consumers must enforce label maturity. See `HERALD_24` and `HERALD_38` |
| `src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py` | Corrected dynamic graph input bundle built only from the ranking panel and temporal relation snapshots | Corrected 2026-07-13; 226,980 instant and 661,613 expanding-memory edges. Prior graph results require rerun. See `HERALD_25` and `HERALD_38` |
| `src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py` | HERALD_26 edge variant builder: pruned-stable, stateful, sector-only, top-k, sector-top-k, feature-compatible, learned-gate, and historical-precision `.csv.gz` edge tables | New 2026-07-02, see `HERALD_26_FR_ZE2020_EDGE_LEARNING_PLAN.md` -- edge construction and rolling edge-gate inputs only, falsification inputs, no recommendation, no causal claim |
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
| `src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py` | HERALD_25 first dynamic-graph ranker smoke: typed manual message passing over `fr_ze2020_dynamic_graph_nodes.csv` + selectable edge table (`fr_ze2020_dynamic_graph_edges.csv` or `fr_ze2020_dynamic_graph_edges_expanding.csv.gz`), then Ridge/MLP ranking heads | New 2026-07-01, smoke/prototype only; no causal claim, no automatic recommendation, no validated model claim |
| `src/modeles/france_ze2020/run_fr_ze2020_dynamic_graph_falsifications.py` | HERALD_25 dynamic-graph ranker falsification runner: no edges, random edge weights/targets, edge-type ablations, temporal shuffle, sector shuffle | New 2026-07-01, local/HPC-prep falsification only; perturbations in memory, no shared input overwrite |
| `src/modeles/france_ze2020/audit_fr_ze2020_dynamic_edge_variants.py` | HERALD_26 audit-only edge diagnostic: type/year counts, degree distributions, retained edge share, volatile-edge share | New 2026-07-02, no training and no performance claim |
| `src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py` | HERALD_27 local relation-objective smoke: distinguishes observed typed ZE2020 x sector edges from controlled non-edges using node-pair features plus recurrence/source/target popularity controls, unseen-pair testing, optional lagged node features, positive edge-state filtering, feature-family and pair-side ablations including compatibility-only/sector-context/sector-position/relation-memory modes, sector-position leave-one-out checks, combined temporal+sector shuffle, semantics-preserving random-target placebo, distance-hard/scaled-distance-hard/pair-distance-hard negatives, source/target/dual endpoint-matched negatives, target-preserving/source-distance/dual-profile hard negatives, and matching shuffle controls | New 2026-07-04, local diagnostic only; dual-endpoint controls show the strongest local compatibility signal so far, but the matching shuffle placebo still requires a stricter degradation gate before HPC or validated model claims |
| `src/modeles/france_ze2020/audit_fr_ze2020_relation_endpoint_controls.py` | HERALD_27 endpoint-control audit: reruns the local relation learner across `both`, `source_only`, `target_only`, and `compatibility_only`, then checks whether compatibility AP exceeds the best endpoint-only shortcut and drops under matched temporal+sector shuffle | New 2026-07-07, local audit only; compact `sector_position_no_rank` now passes the symmetric dual-endpoint combined local gate (endpoint margin + shuffle degradation), supporting the next contrastive relation objective but still not validating a GNN/HPC model |
| `src/modeles/france_ze2020/audit_fr_ze2020_anchor_peripheral_signal.py` | HERALD_27 formula-only audit: computes interpretable pair scores (`dominance_asymmetry_score`, `sector_share_product_score`, `anchor_peripheral_score`) on the dual-endpoint local gate and its matched temporal+sector shuffle | New 2026-07-07, no training; supports an anchor/peripheral hypothesis for the next contrastive objective, but sample size remains small and no recommendation/causal/model claim is authorized |
| `src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py` | HERALD_27 lift-over-formulas audit: compares the local compatibility learner with deterministic anchor/peripheral formulas on the same dual-endpoint gate and matched temporal+sector shuffle | New 2026-07-07, local audit only; the learner adds AP above the best formula in the real gate, but the result remains exploratory and not a dynamic-GNN/HPC/recommendation claim |
| `src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_encoder.py` | HERALD_29 dynamic relation encoder: converts the passed HERALD_28 relation objective into learned source-target relation scores and node-level ZE2020 x sector relation embeddings | New 2026-07-07, representation layer only; not a final dynamic-GNN, causal, or recommendation model |
| `src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_ranking.py` | HERALD_30 relation-embedding ranking diagnostic: compares base ranking features, dense graph embeddings, and shuffled dense graph placebo across seeds/horizons with regression and top-3 classification heads | New 2026-07-08, diagnostic only; 3-year MLP top-3 classifier shows a small local dense-graph lift, still no model promotion |
| `src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_linear_probes.py` | HERALD_39 frozen linear probes over existing dynamic graph aggregates: temporal-successor classification and next-year sector-share regression with node-only, random-target graph, and past-only snapshot controls | New 2026-07-13, representation diagnostic only; designed to decide whether any contrastive/semi-supervised objective is justified before adding model complexity |
| `src/modeles/france_ze2020/run_fr_ze2020_relational_transition_transfer_probe.py` | HERALD_40 ZE-disjoint linear probe: tests whether changes in audited graph aggregates help rank future top-3 sector entries beyond node-only, degree, randomized-endpoint, past-snapshot, sector-shuffle, and target-shuffle controls | New 2026-07-22, DEC-069; job 7780697 completed 5 seeds and failed the pre-registered transfer gate. Diagnostic only; no neural, causal, or recommendation promotion |
| `src/modeles/france_ze2020/run_fr_ze2020_edge_family_isolation_probe.py` | HERALD_41 edge-family isolation: builds equal-schema blocks for ZE similarity, cross-ZE same-sector, and intra-ZE sector relations, then applies the HERALD_40 ZE-disjoint transition protocol and matched endpoint controls | New 2026-07-22, DEC-070; job 7780874 gives a limited gate pass only to `ze_similarity`. Sector-economic families remain blocked; no dynamic-GNN, causal, or recommendation claim |
| `src/modeles/france_ze2020/run_fr_ze2020_similarity_nonlinear_transfer_probe.py` | HERALD_42 fixed MLP transfer gate over node-only and isolated ZE-similarity inputs, with linear, endpoint-randomized, and target-shuffled controls under the same ZE-disjoint protocol | New 2026-07-22, DEC-071; job 7780890 fails because MLP ZE-similarity loses to both MLP node-only and logistic ZE-similarity. No recurrent or graph-neural promotion |
| `src/modeles/france_ze2020/run_fr_ze2020_relation_bottleneck_fusion_probe.py` | HERALD_43 pre-prediction fusion gate: separately scales node history, compresses ZE-similarity with training-only PCA, then combines both before the fixed MLP ranking head | New 2026-07-22, DEC-072; job 7780898 mitigates raw-concatenation loss but fails against node-only and endpoint-placebo gates. Further neural fusion remains blocked |
| `src/data/france_ze2020/build_fr_ze2020_commuting_edges.py` | Downloads checksum-pinned official INSEE 2012/2017/2023 residence-to-workplace flows, resolves historical commune codes through official COG events, and aggregates directed ZE2020 commuting edges with separate observation-time and strict ex-ante clocks | New 2026-07-22, DEC-073 / HERALD_44. Relation-source builder only; never reads the legacy mobility matrix and does not train a model |
| `src/data/france_ze2020/build_fr_ze2020_commuting_strict_ex_ante_edges.py` | Assigns official commuting snapshots to 2012--2025 decision years using publication-aware intervals, emits cross-ZE directed weights only, and leaves 2012--2015 explicitly unavailable | New 2026-07-22, DEC-073 implementation / HERALD_44. Model-input candidate only; no model or recommendation logic |
| `src/modeles/france_ze2020/run_fr_ze2020_commuting_relation_gate.py` | Builds mask-aware incoming/outgoing neighbour-sector profiles from strict ex-ante commuting matrices and evaluates them with the fixed ZE-disjoint linear transition protocol against semantic and random placebos | DEC-074 / HERALD_45 closed: weighted relation gate failed because uniform weights were better; topology-only matched placebo remains pending. No neural encoder |
| `src/modeles/france_ze2020/run_fr_ze2020_commuting_topology_gate.py` | Isolates official commuting topology by comparing real and randomized endpoints under matched uniform outgoing weights, with node, availability, degree-only, reversed-direction, and target-shuffle controls | DEC-075 / HERALD_46 closed: randomized endpoints outperformed real topology; weight transforms and neural integration blocked for this representation |
| `src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py` | HERALD_31 target preflight: audits the stricter `future_top3_entry_{1,3}y_label` objective for ZE2020 x sector ranking before any new model is trained | New 2026-07-08, target audit only; no model, no recommendation, no causal claim |
| `src/modeles/france_ze2020/train_fr_ze2020_sector_ranking.py`, `run_fr_ze2020_top3_entry_ranking_smoke.py` | Ranking controls and target-aligned smoke with explicit horizon-aware label maturity | Corrected 2026-07-13: train rows satisfy `decision_year + horizon <= eval_year`. Earlier outputs are invalid for claims pending rerun; see `HERALD_38` |
| `src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py` | Target-aligned falsifications with coherent feature-bundle permutation and within-entity temporal shuffle | Corrected 2026-07-13; prior outputs invalid for claims pending rerun |
| `src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_diagnostic.py` | Relation-lift diagnostic using only labels matured by the current decision year | Corrected 2026-07-13; prior HERALD_36 result invalid for claims pending rerun |
| `src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_falsifications.py` | HERALD_37 relation-lift falsification runner: reuses HERALD_33 in-memory temporal/sector/target perturbations and evaluates the HERALD_36 lift diagnostic under each scenario | New 2026-07-10, local/HPC runner only; no model/recommendation/causal claim |
| `src/modeles/france_ze2020/run_fr_ze2020_training_block.py` | Training block orchestrator -- imports and calls the 4 scripts above, no new model, consolidates metrics into one summary CSV | New 2026-06-24, see `HERALD_18_FR_ZE2020_TRAINING_PLAN.md` — `claim_status=training_block_summary_smoke_local_only` |
| `hpc/france_ze2020/run_fr_ze2020_hpc_task.sh`, `run_fr_ze2020_hpc_array.sbatch`, `submit_fr_ze2020_hpc.sh`, `smoke_test_fr_ze2020_hpc.sh` | meso Slurm array (5 seeds) calling the 4 training scripts above via their own CLIs -- no new model; `submit_fr_ze2020_hpc.sh` only calls `sbatch` with `--confirm-submit` | New 2026-06-24, see `HERALD_19_FR_ZE2020_HPC_SPEC.md` — `SPEC_READY`, **not launched** |
| `hpc/france_ze2020/audit_fr_ze2020_hpc_results.py` | Post-collection gate audit (G1-G5), descriptive only, no auto-promotion | New 2026-06-24, see `HERALD_19_FR_ZE2020_HPC_SPEC.md` section 6; tested (`tests/test_fr_ze2020_hpc_audit.py`) |
| `hpc/france_ze2020_dynamic_graph/*` | HERALD_25 dynamic graph ranker/falsification HPC package: task scripts, Slurm arrays, dry-run submitters, and descriptive audit | New 2026-07-01, prepared after local falsification tests; no job launched by documentation alone |
| `hpc/france_ze2020_dynamic_graph/run_fr_ze2020_edge_variant_falsification_task.sh`, `run_fr_ze2020_edge_variant_falsification_array.sbatch`, `submit_fr_ze2020_edge_variant_falsifications_hpc.sh` | HERALD_26 dynamic edge-variant falsification array: 16 edge inputs x 5 seeds, each task writes isolated outputs under `hpc_results/fr_ze2020_dynamic_edge_variants_<RUN_ID>/<variant>/seed_<seed>/` | New 2026-07-02; falsification only, no auto-promotion and no recommendation |
| `hpc/france_ze2020_relation_objective/*` | HERALD_28 relation-objective HPC package: runs the lift-over-formulas audit across seeds and stricter relation controls, then audits G1-G5 (integrity, lift over formula, shuffle degradation, seed stability, output separation) | New 2026-07-07; falsification only, no dynamic-GNN/model-promotion/recommendation claim |
| `hpc/france_ze2020_top3_entry/*` | Superseded HERALD_34 package | Inputs/training contract were corrected by HERALD_38; prior job 7734742 is invalid for claims and the package must be rebuilt before rerun |
| `hpc/france_ze2020_top3_entry_lift/*` | Corrected audit now uses paired seed-year wins and explicit target-shuffle degradation | HERALD_37 spec/results before HERALD_38 are superseded; no new HPC run authorized by the correction alone |
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
