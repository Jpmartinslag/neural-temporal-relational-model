# HERALD 16 — Model Training Block Audit (France ZE2020)

**Created:** 2026-06-24. **Scope:** the training/modeling block only — every script under
`src/modeles/`, `src/modeles/real_world/`, `src/modeles/synthetic/`, `src/analyse/`, and
`scripts/` that fits, runs, or evaluates a model. Does **not** re-open, re-run, or alter
any closed branch, any HPC job, the dashboard, Italy/Austria, or raw data. This document
is the code-path-map equivalent of `HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md` for the
training side, and executes that document's own deferred next step (§10: *"audit
`train_herald_v6.py`/`v7.py` and `scripts/02_ridge_ar_official.py` for whether they can be
pointed at `fr_ze2020_model_ready_panel.csv` instead of the legacy leaky panel, as a
separate, reviewed task"*).

**Method:** every file below was read (imports, path constants, CLI args, output writes) —
not just named by pattern. Classification cross-checked against
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, `reports/HERALD_CURRENT_STATE.md`,
`reports/herald_artifact_registry.json`, and `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
(which already pre-classified most of this block on 2026-06-18 — this pass verifies that
classification against actual current file contents and fills in the parts HERALD_10 left
at folder-name granularity).

**Answer to the one-line question this audit exists to answer:** no training script in
this repository today reads `fr_ze2020_model_ready_panel.csv`. The France ZE2020 tabular
forecasting track has a clean data lineage (HERALD_15) but **no current trainer** — that
gap is what Task 3 below closes with a new, minimal, smoke-tested script.

---

## 0. Executive summary

| Question | Answer |
|---|---|
| Does any current/active trainer read the new canonical panel (`fr_ze2020_model_ready_panel.csv`)? | **No, until this pass.** New script added: `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` (Task 3). |
| Does any script claimed as "current" read the legacy panel (`dynamic_stgnn_feature_panel_v1.csv`)? | **No.** Every script that reads it is already classified `HISTORICAL_EXPERIMENT`/`LEGACY_DO_NOT_USE` in `HERALD_10_CODE_PATH_MAP.md`, and that classification is confirmed accurate by this pass (see §1). |
| Were any legacy files moved or deleted? | **No.** Four files (`train_herald_v6.py`, `v7.py`, `train_herald_semi_v2.py`, `train_herald_regime_experiment.py`) are currently **modified/uncommitted** in the worktree. Human clarification on 2026-06-24: these are intentional historical architecture-improvement attempts, not accidental scope creep. They remain outside the current canonical trainer and cannot support current claims without reauditing, but should be preserved as architecture-history evidence (see §5). |
| Is there a current graph-forecast pipeline for ZE2020? | **No, and none is proposed.** Two prior FR ZE2020 graph-forecast attempts both failed/closed (DEC-031 `S1_FR_FAIL`, plus the dual-graph branch on FR NUTS3, DEC-029 `DUAL_GRAPH_S1_FAIL`). §4 documents what exists as raw material for *future* research, explicitly not a pipeline. |
| Final status | **PARTIAL** — see §8. Documentation, one new smoke-tested script, and registry/map updates done; no file moved; nothing trained beyond local smoke. |

---

## 1. Full inventory — France ZE2020 tabular/temporal forecasting track

This is the track the task is about: every script that does or did try to forecast
`establishment_creations`/`side_establishment_creations_official` per ZE2020 zone × year.

| File | Input | Output | Model type | Legacy panel? | New panel? | Recommended status | Note |
|---|---|---|---|---|---|---|---|
| `src/modeles/train_herald_v3.py` | `dynamic_stgnn_feature_panel_v1.csv` (`PANEL_PATH`), `graph_adjacency_core_v0.csv`, `graph_adjacency_mobility_v0.csv`, `graph_node_index_core_v0.csv`, raw URSSAF quarterly | `herald_v3_predictions_*_v1.csv`, `*_internals_*_v1.npz` | GRU quarterly encoder + gated dynamic graph residual (`HERALDv3Residual`) + Ridge persistence inside the same file | **Yes** | No | `LEGACY_DO_NOT_USE` | Standalone (no import of other `train_herald_*`). Tracked, clean (no pending diff). |
| `src/modeles/train_herald_v4.py` | same as v3 + `side_creations_a10_ze2020_v1.csv` (A10 sector) | `herald_v4_predictions_*_v1.csv` | Sectoral dynamic graph residual (`HERALDv4Residual`) | **Yes** | No | `LEGACY_DO_NOT_USE` | Standalone. Tracked, clean. |
| `src/modeles/train_herald_v5.py` | same as v4 | `herald_v5_predictions_{total,sector}_*_v1.csv` | GRU + A10 sector graph residual (`HERALDv5Residual`) | **Yes** | No | `LEGACY_DO_NOT_USE` | Standalone. Tracked, clean. |
| `src/modeles/train_herald_v6.py` | same as v4/v5 | `herald_v6_predictions_{total,sector}_*_v1.csv`, `herald_v6_forecast_*_v1.csv` | GRU + graph residual; Ridge persistence/lag fit (`fit_zone_mask` param) | **Yes** | No | `HISTORICAL_ARCHITECTURE_ATTEMPT` / `PENDING_REAUDIT` | **Modified, uncommitted.** Human clarification on 2026-06-24: intentional architecture-history attempt, not accidental scope creep. This is the "Q7 base" — `HERALD_Q7_FRANCE_RESULT` (`PENDING_REAUDIT`) traces here. It is preserved to explain architectural evolution, but it is not the current canonical trainer and cannot support current claims until reaudited against the clean panel. |
| `src/modeles/train_herald_v7.py` | `import train_herald_v6 as base` → same panel | `herald_v7_predictions_{total,sector}_*_v1.csv` | `HERALDv7Residual`, built on v6 | **Yes** (transitively via v6) | No | `HISTORICAL_ARCHITECTURE_ATTEMPT` / `PENDING_REAUDIT` | **Modified, uncommitted.** Intentional architecture-history attempt building on v6. Imports v6 directly, so it cannot be moved/isolated independently of v6. Not current, not claim-bearing without reauditing. |
| `src/modeles/train_herald_semi_v1.py` | `dynamic_stgnn_feature_panel_v1.csv` directly (standalone, predates the `import ... as base` pattern) | `herald_semi_predictions_{total,sector}_*_v1.csv`, `herald_semi_forecast_*_v1.csv` | GRU + graph residual variant | **Yes** | No | `LEGACY_DO_NOT_USE` | Standalone. Tracked, clean. |
| `src/modeles/train_herald_semi_v2.py` | `import train_herald_v6 as base`, `import train_herald_v7 as v7`, `from herald_fold_controls import apply_fold_eu_control`, `herald_phase3c_labor_tutor_features.csv` | `herald_semi_v2_predictions_{total,sector}_*_v1.csv` | Ensemble/blend over v6+v7 + labor-tutor features + fold EU control | **Yes** (transitively) | No | `HISTORICAL_ARCHITECTURE_ATTEMPT` / `PENDING_REAUDIT` | **Modified, uncommitted.** Intentional architecture-history attempt. Depends on untracked `herald_fold_controls.py` (no test). Preserved as evolution evidence, but not current and not claim-bearing. |
| `src/modeles/train_herald_regime_experiment.py` | `import train_herald_v6 as base`, `import train_herald_semi_v2 as semiv2`, `herald_regime_modes.py` | (regime-mode experiment outputs, no fixed `OUT_*` constant — CLI-driven) | Regime-gated variant (covid/rebound/growth modes) on top of v6+semi_v2 | **Yes** (transitively) | No | `HISTORICAL_ARCHITECTURE_ATTEMPT` / `PENDING_REAUDIT` | **Modified, uncommitted.** Intentional architecture-history attempt, furthest from anything validated because it stacks on v6 and semi_v2. Preserved to show the architecture direction explored, but not current and not claim-bearing. |
| `src/modeles/train_dynamic_stgnn_models_v1.py` | `dynamic_stgnn_feature_panel_v1.csv` directly | `dynamic_stgnn_model_predictions_v1.csv` | 3 candidate architectures: `DiffusionGRUResidual`, `GraphWaveNetResidual`, `DynamicSTGNNResidual`, + Ridge baseline | **Yes** | No | `LEGACY_DO_NOT_USE` | Earliest architecture-search file (predates the v3-v7 naming scheme). Standalone. Tracked, clean. |
| `src/modeles/train_temporal_baselines_v1.py` | `dynamic_stgnn_feature_panel_v1.csv` directly | `temporal_baselines_predictions_*_v1.csv` | Ridge (lag features) + `LocalLSTM` (per-zone univariate) — **no graph** | **Yes** | No | `LEGACY_DO_NOT_USE` | Conceptually the closest pre-existing analog to a "minimal baseline" file — but reads the leaky panel. Listed `ACTIVE_PREDICTION` in HERALD_10 (DEC-006) for its *cross-country* persistence/Ridge role; for **France specifically** it is legacy because of the panel, not the method. Tracked, clean. |
| `src/modeles/sector_baselines_v1.py` | `import train_herald_v6 as base` for `PANEL_PATH`/splits | predictions CSV (`--predictions-out`) | A10 sector naive baselines (lag-1, historical mean) — no fitting | **Yes** (transitively) | No | `LEGACY_DO_NOT_USE` | Naive-only (no `Ridge`/`nn.Module`). Tracked, clean. |
| `src/modeles/run_herald_prospective_forecast_v1.py` | `import train_herald_v6 as base`, `v7`, `semi_v2` | `herald_forecast_{total,sector}_*_v1.csv` (2026/2027 forward forecast) | Ensemble forward-forecast wrapper, no own architecture | **Yes** (transitively) | No | `LEGACY_DO_NOT_USE` | Forward-forecast tool, not a trainer per se; inherits every upstream dependency's legacy-panel status. Tracked, clean. |
| `src/modeles/build_dynamic_stgnn_feature_panel_v1.py` | raw FLORES/URSSAF/SIDE | `dynamic_stgnn_feature_panel_v1.csv` (the legacy panel itself) | N/A (data builder, not a trainer) | N/A (generator) | No | `LEGACY_DO_NOT_USE` | The leak (`growth_1y`/`growth_2y` = `pct_change()` on the target itself) lives here — see `HERALD_15` §5. Registry: `FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL`, `INVALID_FOR_CLAIMS`. |
| `src/modeles/integrate_side_2025_for_herald_v6.py` | legacy panel + 2025 raw extension | `target_side_establishments_annual_core_through_2025_v1.csv` | N/A (data extension, not a trainer) | **Yes** | No | `LEGACY_DO_NOT_USE` | Extends the legacy lineage to 2025; not reconciled against the new HERALD_15 pipeline (which stops at 2024, matching its own raw source). |
| `src/modeles/herald_regime_modes.py` | N/A (pure functions: covid/rebound/growth mode definitions) | N/A | UTILITY | N/A | N/A | `LEGACY_DO_NOT_USE` (adjacent) | Only consumer is `train_herald_regime_experiment.py`. |
| `src/modeles/herald_fold_controls.py` | N/A (pure function `apply_fold_eu_control`) | N/A | UTILITY | N/A | N/A | `UNKNOWN_REVIEW_REQUIRED` | **Untracked, no test.** Only consumer is `train_herald_semi_v2.py` (itself unreviewed). Per HERALD_14: resolve the semi_v2 review first. |
| `src/modeles/herald_map_utils.py` | `graph_adjacency_core_v0.csv`, `graph_adjacency_mobility_v0.csv`, `graph_node_index_core_v0.csv`, legacy panel-derived map data | map/visualization helper outputs | UTILITY (no model) | **Yes** | No | `LEGACY_DO_NOT_USE` (adjacent) | Feeds `src/visualisation/plot_herald_v3_dashboard.py`, `plot_herald_v3_v6_dashboard.py`, `plot_herald_v6_2025_dashboard.py` — all pre-Q7, already `HISTORICAL_EXPERIMENT` per HERALD_10. |
| `src/analyse/02_ridge_ar_official.py` | `import train_herald_v6 as base` for `PANEL_PATH`/`SPAT_COLS=["side_lag_1","growth_1y"]` | Ridge AR metrics (printed/CSV, CLI-driven) | Ridge (AR + spatial-aggregate features) | **Yes** | No | `LEGACY_DO_NOT_USE` | **This is the script HERALD_15 §5 found reading `growth_1y` directly as a feature** (`SPAT_COLS`), the exact same-row target leak. Confirms the file's own comment ("forecast-safe") is wrong for that column. Path note: HERALD_15 and the registry's `claim_forbidden` text both wrote `scripts/02_ridge_ar_official.py`; the real path is `src/analyse/02_ridge_ar_official.py` — **fixed in the registry by this pass** (§6). |
| `src/analyse/01_sector_baselines.py`, `03_select_gate.py` | legacy panel (via shared constants) | gate-selection CSV/JSON | Sector baselines + Q7 architecture gate selection | **Yes** | No | `LEGACY_DO_NOT_USE` | Pre-Q7 architecture search (Phase 3E). |
| `src/analyse/analyze_herald_v3_statistical_evidence.py`, `evaluate_dynamic_feature_panel_baselines_v1.py`, `summarize_herald_semi_total.py` | legacy panel / v3-v6 prediction outputs | analysis reports/CSVs | Post-hoc statistical analysis, not trainers | **Yes** | No | `LEGACY_DO_NOT_USE` | Analysis-only, downstream of the scripts above. |
| **`src/modeles/france_ze2020/train_fr_ze2020_baselines.py`** | **`data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv`** | `fr_ze2020_baseline_predictions_v1.csv`, `fr_ze2020_baseline_metrics_v1.csv` (CLI-driven `--output-dir`, not committed by default) | Persistence (`y_hat = lag_1`) + Ridge(lag_1, lag_2, lag_3, growth_1y_safe, growth_2y_safe), causal rolling-origin | **No** | **Yes** | `CURRENT_BASELINE_CANDIDATE` | **New, this pass.** See Task 3 (§3). 12/12 tests pass, runs in <1s. |

**Confirms HERALD_10's existing classification is accurate** for every row above except the
new one — no re-classification was needed, only verification (every `PANEL_PATH` constant
was actually read from source, not assumed from the file name).

The one-off repository-migration helper previously listed in this table was subsequently
archived from the delivery tree after a dependency audit confirmed that no code or test imported
it. Its completed migration remains traceable through the repository history and the delivery
provenance record.

---

## 2. Closed graph-forecast branches (real data, FR/NL — not the legacy CSV, not the new panel)

These do not read either France ZE2020 panel (legacy or new) at all — they read purpose-built
tensors. Listed for completeness because the task asked about the whole training block, and
because §4 needs to distinguish these (closed, real, forecast-oriented) from the *future*
graph track (not yet built).

| File | Input | Model type | Recommended status | DEC |
|---|---|---|---|---|
| `src/modeles/train_dual_graph_experiment.py`, `dual_graph_models.py`, `run_dual_graph_pilot.py`, `run_dual_graph_smoke.py` | `data/processed/dual_graph_tensors/fr_{year}.npz` (FR **NUTS3**, not ZE2020) | Dynamic dual economic graph GNN, 5 controls × 5 seeds | `LEGACY_DO_NOT_USE` (`CLOSED_BRANCH`) | DEC-029, `DUAL_GRAPH_S1_FAIL` — all 7 gate criteria fail |
| `src/modeles/graph_temporal_models.py`, `graph_temporal_train.py`, `run_e0_smoke_nl.py`, `run_e0_smoke_nl_v2.py`, `run_s0_fr_smoke.py`, `run_s1_fr_local.py` | `data/processed/graph_temporal_v2/{country}/{year}/fold_v2.npz` (FR **ZE2020** + NL COROP, schema 2.0) | GConvGRU / EvolveGCN-H low-capacity residual over a statistically-derived per-year adjacency | `LEGACY_DO_NOT_USE` (`CLOSED_BRANCH`) | DEC-031, `S1_FR_FAIL` — fails all 5 frozen gate criteria; indistinguishable from permutation nulls (p=1.0) |
| `src/modeles/phase5/corrector.py`, `l2_pool.py`, `neural_corrector.py`, `rolling_origin.py`, `manifest.py` | `data/processed/economic_graph/g1_l2_cogrowth/` (territorial co-growth, fixed graph) | Fixed-L2 neural residual corrector | `LEGACY_DO_NOT_USE` (`CLOSED_BRANCH`) | DEC-023, `NOT_SUPPORTED` |

**Important for §4:** the one branch that *did* use a ZE2020-grain graph as a forecast input
(`graph_temporal_*`, DEC-031) failed. This is the directly relevant negative prior for any
future FR ZE2020 graph-forecast claim.

---

## 3. Real-data sector-relation research track (different axis: sector→sector, not territory→territory)

`src/modeles/real_world/` and the sector-precedence builders read **European-panel sector
data** (`data/processed/european_panel/{france,pt_municipal_sector,nl}_panel.csv`,
`sector_panel_fr_nl_pt.csv`) — never the legacy or new France ZE2020 panel. They answer a
different question (do sectors temporally precede other sectors?) than this task's question
(can ZE2020 zones be forecast, and could a future zone-to-zone graph help?).

| File(s) | Type | Recommended status | Note |
|---|---|---|---|
| `build_sector_precedence_graph.py`, `gates_dec060_france_audit.py`, `run_dec060_france_signal_audit.py`, `gates_dec064_pt_municipal_phase7.py`, `run_dec064_pt_municipal_phase7.py`, `phase7_threshold_calibration.py`, `merge_nl_gemeente_proxy_phase7.py`, `preflight_granular_phase7.py` | Signed lag-1 sector precedence (bootstrap/permutation/FDR) | `REAL_WORLD_RELATION_PIPELINE` | `ACTIVE_RELATION_EVIDENCE` per HERALD_10. Methodologically the strongest prior art for *any* future relation-evidence work (rigorous null/stability controls) — reusable as a **methodology template**, not as code that touches ZE2020-to-ZE2020 edges. |
| `build_phase7_weak_labels.py`, `train_real_relation_weak_labels.py`, `run_shared_relation_real.py`, `run_p0_checkpointed.py`, `run_dec059_weak_label_revalidation.py`, `gates_dec058.py`, `gates_dec059.py` | `SharedRelationEncoder` (trained on synthetic data) fine-tuned/evaluated on real sector pairs | `EXPERIMENTAL_RESEARCH` | DEC-056/058/059, `REAL_WEAK_LABEL_TUNING_PARTIAL`. Sign transfer weak (0.438-0.667), no robust cross-country replication. Not reusable as-is; the *encoder architecture* could be a reference if a future zone-to-zone encoder is ever attempted, but that is a different graph (sector pairs, not territory pairs). |
| `run_dec062_granular_preflight_gates.py`, `run_dec063_granular_evidence_gates.py`, `prepare_dec064_hpc_manifest.py` | Gate evaluators | `REAL_WORLD_RELATION_PIPELINE` (utility) | No model fit; preflight/manifest helpers. |
| `scripts/audit_sector_precedence_results.py`, `merge_sector_precedence_results.py`, `prepare_task_manifest.py` (symlinks into `hpc/phase7_sector_precedence/scripts/`) | Phase 7 result audit/merge tooling | `REAL_WORLD_RELATION_PIPELINE` (utility) | Not training scripts; not related to ZE2020 tabular forecasting at all. The task's prompt listed `scripts/02_ridge_ar_official.py` — **that file does not exist**; the real Ridge AR script is `src/analyse/02_ridge_ar_official.py` (see §1). |

---

## 4. Future ZE2020 graph track — what exists, classified, and the recommended path

**Status: research/future, explicitly not a current pipeline** (per the task's own
constraint — this section documents, it does not implement).

### 4.1 Pre-existing FR ZE2020 territorial adjacency artifacts (found, not previously cross-referenced in HERALD_09)

| Path | Content | Generator | Status |
|---|---|---|---|
| `data/processed/graph_adjacency_core_v0.csv` | 280×280 **binary** matrix (values strictly `{0,1}`) — geographic neighbor adjacency | **Not found in the current tree.** | `UNKNOWN_REVIEW_REQUIRED` |
| `data/processed/graph_adjacency_mobility_v0.csv` | 280×280 **weighted** matrix (0–0.94), row-normalized in `herald_map_utils.py` as `mobility` | **Not found in the current tree.** | `UNKNOWN_REVIEW_REQUIRED` |
| `data/processed/graph_node_index_core_v0.csv` | 280-row node index (`node_idx` ↔ `ZE2020`) | Not found. | `UNKNOWN_REVIEW_REQUIRED` |

These are **real**, already at the exact ZE2020 grain the task asks about, and conceptually
match two of the five relation types the task lists (`territorial neighborhood` ≈ `core`,
`commuting flows` ≈ `mobility`) — confirmed by `reports/HERALD_INTELLIGENCE_LAYER_SPEC.md`
line 46, which independently describes `graph_adjacency_mobility_v0.csv` as a 280×280
pre-COVID mobility-weight matrix that may underrepresent remote work. **But
their construction method (distance threshold? administrative contiguity? which commuting
survey/year?) cannot be verified — the builder script is missing from the current tree.**
Same provenance-gap pattern already documented for other pre-Q7 artifacts in HERALD_15 §1.

**Recommendation:** treat these three files as **candidate raw material only**, never as a
validated or ready-to-use territorial graph. Before any future use: (1) locate the original
generation method (check git history pre-2026-04-08 if traceable, or treat as
unreconstructible and rebuild from a documented source); (2) do not reuse the *binary*
`core` matrix's threshold/definition without knowing it; (3) the only architecture that ever
consumed them (`train_herald_v3..v7`, `semi_v1`) is itself `LEGACY_DO_NOT_USE` and was never
validated under the current causal protocol — their use there is not evidence the matrices
are correct, only that they exist and have the right shape.

### 4.2 Closed/negative prior specific to FR ZE2020 graph-as-forecast-input

`graph_temporal_*` (§2) built an **independent**, statistically-derived (correlation-based,
`positive_topk`) per-year FR ZE2020 adjacency — methodologically documented (DEC-028,
`FR_ADJACENCY_READY`: 280 ZE, 5 eval years, 0 isolated nodes, 26-39% negative raw
correlations) — and used it as a GConvGRU/EvolveGCN-H forecast input. Result: **`S1_FR_FAIL`
(DEC-031)** — indistinguishable from random permutation. This is a different adjacency than
§4.1's `core`/`mobility` matrices, but it is the most relevant negative prior: **a
ZE2020-grain graph has already been tried once as a forecast-improving input for France, and
failed.** Any future graph work should be framed as the project's own Bloco 2 direction
already states — *descriptive/evidence layer, not a forecast-accuracy claim* — unless a
genuinely new hypothesis or data source is added.

### 4.3 Reference methodology (not directly reusable, different country/grain)

`data/external/build_phase4c_adjacency.py` (queen contiguity, NL/BE/PT NUTS3),
`build_phase4d_commuting_graph.py` (commuting, NL/BE; PT blocked),
`build_phase4d_sector_similarity.py` — `CLOSED_BRANCH` (DEC-008/009 FAIL). Useful only as a
**code-pattern reference** (how a queen-contiguity / commuting graph was built and tested
against a gate) if a future FR ZE2020 builder is written from scratch — not reusable
directly (different countries/territorial units), and the branch's own forecast-improvement
conclusion was negative everywhere it was tried.

### 4.4 Classification answering the task's exact question

| Requested category | Scripts |
|---|---|
| **Synthetic** | `src/modeles/synthetic/` whole tree (`phase11_generalization/` ... `phase16_decoupled/`, `gates*.py`, `herald_graph_imputer*.py`, `run_*.py`) — zero real data, `SYNTHETIC_BENCHMARK` |
| **Real** | `train_dual_graph_experiment.py`+tensors (FR NUTS3), `graph_temporal_*`+tensors (FR ZE2020/NL COROP), `build_phase4c/4d_*` (NL/BE/PT NUTS3), `build_g1_*`/`build_g2_*` (FR/NL/PT sector-territory co-growth), `real_world/*relation*` (FR/NL/PT sector pairs) — all real, all closed/partial, none is a territory-to-territory ZE2020 commuting/distance/similarity graph |
| **Reusable** | (a) the bootstrap/permutation/FDR/LOYO methodology pattern from `build_sector_precedence_graph.py` and `build_g2_*` (statistical rigor template); (b) `graph_adjacency_core_v0.csv`/`mobility_v0.csv` as **candidate raw data only**, pending provenance verification (§4.1) |
| **Must not be used** | Everything in §2 as a *forecast-improvement* claim (both FR attempts — NUTS3 dual-graph and ZE2020 graph-temporal — failed their gates); `graph_adjacency_core_v0.csv`/`mobility_v0.csv` as a *silently-trusted* input (provenance unverified) |

**No `CURRENT_GRAPH_CANDIDATE` exists, and none is proposed by this pass** — consistent with
the task's explicit instruction not to implement the future graph track yet, only to
classify what exists and define what "connection between ZE" would need before any
implementation (a documented distance/commuting/similarity definition, not reuse of an
unverified legacy matrix).

---

## 5. Legacy isolation decision (Task 5)

**Decision: document-only, no file moved.** The task's fallback rule required risky moves to
be replaced by an explicit documentation classification, and moving was not safe at that point because:

1. Four files (`train_herald_v6.py`, `v7.py`, `train_herald_semi_v2.py`,
   `train_herald_regime_experiment.py`) are **currently modified, uncommitted**, with real
   new functionality. Human clarification on 2026-06-24 resolved the intent question:
   these are deliberate architecture-improvement attempts kept as historical evidence of
   where the architecture went, not accidental scope creep. Relocating them now would still
   be risky because their code is dirty, transitively imported, and not reaudited against the
   new `fr_ze2020_model_ready_panel.csv` path.
2. The import chain (`v7`/`semi_v2`/`regime_experiment`/`sector_baselines_v1`/
   `run_herald_prospective_forecast_v1` all do `import train_herald_v6 as base`, relying on
   `src/modeles/` being on `sys.path` directly, not as a package) means any single file move
   would require moving the entire cluster atomically and re-verifying every relative
   import — a bigger, riskier change than this pass's mandate.
3. `herald_fold_controls.py` is untracked and itself pending review (only consumer is the
   unreviewed `semi_v2`).

**What this pass does instead:** every file in §1 already carries an explicit
`LEGACY_DO_NOT_USE`, `HISTORICAL_ARCHITECTURE_ATTEMPT`/`PENDING_REAUDIT`,
`EXPERIMENTAL_RESEARCH`, or `UNKNOWN_REVIEW_REQUIRED` status in the table above,
cross-referenced against `HERALD_10_CODE_PATH_MAP.md` (§6 below records the one new
cross-reference added there). No script that depends on the legacy panel is described
anywhere in this repository's documentation as a current or recommended training path.

---

## 6. Documentation and registry changes made by this pass

- **New file:** `reports/canonical/HERALD_16_MODEL_TRAINING_BLOCK_AUDIT.md` (this document).
- **New file:** `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` (Task 3).
- **New file:** `tests/test_fr_ze2020_baselines.py` (12 tests).
- **`reports/canonical/HERALD_10_CODE_PATH_MAP.md`:** added the new script under
  `ACTIVE_PREDICTION`, with a cross-reference to this document.
- **`reports/canonical/HERALD_09_DATA_ASSET_MAP.md`:** added a row for
  `graph_adjacency_core_v0.csv`/`mobility_v0.csv`/`graph_node_index_core_v0.csv` (§4.1
  finding — these were previously not listed anywhere in the data asset map).
- **`reports/herald_artifact_registry.json`:** (a) added `FR_ZE2020_BASELINE_PREDICTIONS_V1`
  (status `REGENERABLE`, `tracked_in_git: false`, explicit `exploratory_smoke` claim
  language); (b) fixed a path typo in `FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL`'s
  `claim_forbidden`/`origin_decision` text (`scripts/02_ridge_ar_official.py` →
  `src/analyse/02_ridge_ar_official.py`, the actual path).
- **`reports/HERALD_NAMING_CONVENTIONS.md`:** added `claim_status` (`exploratory_smoke`) to
  the canonical label/tag vocabulary section.
- **`reports/HERALD_CURRENT_STATE.md`:** added a short note under Bloco 1 distinguishing the
  new minimal FR ZE2020 baseline path from the unrelated, still-`PENDING_REAUDIT` Q7 result.
- **`README.md`, `reports/README.md`:** added `HERALD_15`/`HERALD_16` to the canonical-maps
  list (both files listed maps only up to `HERALD_14`, even though `HERALD_15` already
  existed before this pass).

No row above touches the dashboard, `hpc_results/`, Italy/Austria, or raw data.

---

## 7. Tests

```
python3 -m pytest tests/test_fr_ze2020_clean_panel.py tests/test_fr_ze2020_model_ready_panel.py \
  tests/test_herald_artifact_registry.py tests/test_herald_france_lineage_consistency.py \
  tests/test_fr_ze2020_baselines.py -q
```

Result recorded in §8 of the session summary (final verification step), run after all
documentation/registry edits in §6 were made, to confirm the registry edits did not break
the existing lineage-consistency suite.

---

## Cross-reference

- Data layer this document builds on: `reports/canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md`
- Code structure (pre-existing classification, verified accurate by this pass): `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
- Data structure: `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
- Worktree/dirty-file decisions referenced in §5: `reports/canonical/HERALD_14_WORKTREE_DECISION_AUDIT.md`
- Artefact provenance: `reports/herald_artifact_registry.json`
