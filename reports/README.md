# HERALD Reports

This directory is now intentionally small at the top level.

The old phase-by-phase reports were consolidated into five canonical synthesis
documents under `reports/canonical/`. Historical reports are still recoverable from
git history (every one of the 210 removed files was individually re-read and verified
against the canonicals — see `canonical/HERALD_DEEP_REPORT_AUDIT.md`), but they are no
longer the public entry point.

**Do not start with:** `hpc_results/` (raw HPC outputs), raw data under
`data/external/*/raw/`, or any dashboard HTML other than the current candidate. These
require cross-referencing the decision log before any number is trusted.

## Read First

1. `canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
2. `canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`
3. `canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
4. `canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
5. `canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`

## Second-level canonical maps

Built on top of the five above, for cross-cutting traceability:

6. `canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md` — one row per phase/block (data,
   granularity, technique, validation, result, DEC-*, status, citability).
7. `canonical/HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md` — the scientific reasoning in
   narrative form, for the article.
8. `canonical/HERALD_08_REPOSITORY_TRACEABILITY_MAP.md` — what each folder is and what
   not to cite from it.
9. `canonical/HERALD_09_DATA_ASSET_MAP.md` — every data path classified (canonical,
   valid-processed, raw-regenerable, historical, blocked-for-training).
10. `canonical/HERALD_10_CODE_PATH_MAP.md` — every `src/` module classified (active,
    historical, closed branch, research-track).
11. `canonical/HERALD_11_HPC_AND_RESULTS_MAP.md` — every HPC job/result classified
    with its DEC trace.
12. `canonical/HERALD_12_FINAL_PHASE_MAP.md` — the single end-to-end phase table.

`canonical/HERALD_13_ORGANIZATION_BACKLOG.md` is an organizational chore list (not a
scientific document) — uncommitted worktree state and future data/code/HPC decisions.
`canonical/HERALD_14_WORKTREE_DECISION_AUDIT.md` is the decision layer on top of it:
per-group commit/gitignore/keep-local/requires-new-DEC/human-review calls. `01`-`12` are
the science/structure base; `13`-`14` are housekeeping against that base.

13. `canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md` — France ZE2020 data layer
    (raw ingestion through `fr_ze2020_model_ready_panel.csv`), separate from training.
14. `canonical/HERALD_16_MODEL_TRAINING_BLOCK_AUDIT.md` — its training-side counterpart:
    every training script classified current/legacy/experimental/closed, and the minimal
    current FR ZE2020 baseline path. Also housekeeping, not a new scientific result.
15. `canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` — audit and plan for a
    future ZE2020/sector relational layer: artifact inventory, what's usable now vs.
    needs provenance, the scientific hypothesis, and a staged MVP. Planning only — no
    graph/neural model implemented, no claim made.
16. `canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md` — audits the 4 current FR ZE2020
    training scripts, defines the local training architecture (Task A: ZE-level
    forecast; Task B: sector graph), and specifies (but does not run) the HPC-ready
    hypotheses and checklist for the next HPC step. No HPC job launched, no headline
    claim.
17. `canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md` — executable HPC spec for the FR
    ZE2020 training block (5 seeds x the 4 scripts), pre-registered gates G1-G5,
    and the `hpc/france_ze2020/` infrastructure. Launched 2026-06-24 (job `7498752`,
    5/5 tasks COMPLETED): gate G3 (candidate beats baseline in >=3/5 seeds) FAILED
    for all 3 candidates -- no predictive gain, confirmed robustly across seeds,
    not just the single-seed local smoke. G4 (relation-signal stability) PASSED.
18. `canonical/HERALD_20_FR_ZE2020_EXPLORATORY_RELATION_SIGNALS.md` — reorientation
    from predictive performance to relational analysis: extracts and organizes the
    already-computed ZE-to-ZE / ZE-to-sector / intra-ZE relation signals into one
    interpretable table, after HERALD_19 found no predictive gain. No new model, no
    causal claim, no automatic recommendation.
19. `canonical/HERALD_21_FR_ZE2020_RELATION_LAYER_AUDIT.md` — audit of HERALD_20
    before accepting it as canonical: schema/content/builder/doc/registry checks,
    `RELATION_LAYER_AUDITED`. Found and fixed 2 small gaps (missing "ZE2020 as
    functional economic node" framing; missing causal_effect/causal_impact column
    check in tests) — no methodology change, no new training.
20. `canonical/HERALD_22_FR_ZE2020_DASHBOARD_MVP.md` — first France-ZE2020-only
    dashboard MVP (map + prediction-as-control + sector view + exploratory relation
    graph), separate from the Observatory v0.3/v0.4/v0.5/v0.5.1 dashboards. Geometry
    (`data/external/ze2020_geometry.geojson`) verified 280/280 canonical coverage.
    `DASHBOARD_MVP_READY`. No causal/recommendation language, no fabricated
    prediction series.
21. `canonical/HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md` — canonical
    reframing of the project objective: forecasting is now a control/auxiliary task;
    the main target is temporal-relational representation learning for auditable
    indicators and future exploratory ZE×sector ranking. No operational recommendation
    claim and no final validated STGNN claim.
22. `canonical/HERALD_24_FR_ZE2020_SECTOR_RANKING_TRAINING_SPEC.md` — first concrete
    training spec for the reframed objective: a retrospective ZE×sector ranking task,
    its baselines, metrics, and HPC launch target. Exploratory only; no automatic
    recommendation and no causal claim.
23. `canonical/HERALD_25_FR_ZE2020_DYNAMIC_GRAPH_MODEL_SPEC.md` — construction spec for
    the next model block: a dynamic ZE2020 x A10-sector graph, with explicit node/edge
    schemas, leakage rules, typed relations, ranking objective, falsification gates, and
    conditions required before HERALD can be described as a new dynamic graph model.
    Specification only; no model result and no operational recommendation claim.
24. `canonical/HERALD_26_FR_ZE2020_EDGE_LEARNING_PLAN.md` — post-HERALD_25 edge-layer
    plan: documents the expanded-edge HPC finding (time signal strong, sector signal
    moderate, current edges not yet useful), adds edge-denoising/structure-learning
    references, and defines the next pruned/stateful/learned edge variants before any
    heavier neural claim.
25. `canonical/HERALD_27_FR_ZE2020_RELATION_OBJECTIVE_GATE.md` — pre-training gate and
    local smoke after the edge-sign placebo: confirms that the current encoder mostly
    uses edge presence/sign rather than economic magnitude, separates retrospective
    evaluation from 2025 inference, and locally tests dynamic relation learning with
    typed hard negatives plus recurrence/popularity, unseen-pair, lagged-feature,
    positive edge-state, feature-family, pair-side, combined temporal+sector shuffle,
    semantics-preserving random-target, and distance-hard/scaled/pair-distance controls. Result:
    `new_relation` is the most promising local objective so far; temporal-only and
    sector-only signals are real under targeted shuffles, but target/difference
    shortcuts plus local-only compatibility/composition evidence still block HPC/model promotion.
26. `canonical/HERALD_28_FR_ZE2020_RELATION_OBJECTIVE_HPC_SPEC.md` — executable HPC
    falsification spec for the HERALD_27 relation objective: compares the local
    compatibility learner against deterministic formulas across seeds, endpoint controls,
    and temporal/sector placebos. Run `7733592` passed G1-G5, authorizing the next
    representation-layer prototype only; no dynamic-GNN, causal, or recommendation claim.
27. `canonical/HERALD_29_FR_ZE2020_DYNAMIC_RELATION_ENCODER.md` — converts the passed
    relation objective into a dynamic relation encoder: learned source-target scores and
    node-level ZE2020 x sector relation embeddings. Representation layer only, not a final
    model or recommendation claim.
28. `canonical/HERALD_30_FR_ZE2020_RELATION_EMBEDDING_RANKING_DIAGNOSTIC.md` — downstream
    diagnostic for HERALD_29 embeddings in the retrospective ZE2020 x sector ranking task.
    Regression heads remain below base formula features; the 3-year MLP top-3 classifier
    shows dense graph above the shuffled-graph placebo, but the stricter no-relation control
    performs best. No HPC promotion, no model promotion, and no recommendation claim.
29. `canonical/HERALD_31_FR_ZE2020_TOP3_ENTRY_TARGET_PREFLIGHT.md` — target preflight after
    HERALD_30: defines and audits `future_top3_entry_{1,3}y_label`, confirming that the
    3-year entry target has enough eligible rows for the next target-aligned relation model.
    No model, no causal claim, and no recommendation claim.
30. `canonical/HERALD_32_FR_ZE2020_TOP3_ENTRY_RANKING_SMOKE.md` — first target-aligned
    local smoke for `future_top3_entry_3y_label`: MLP with formula relation features beats
    both no-relation and shuffled-relation controls locally, but only as a small diagnostic
    result. No dynamic-GNN/model/recommendation promotion.
31. `canonical/HERALD_33_FR_ZE2020_TOP3_ENTRY_FALSIFICATION_TRIAGE.md` — local falsification
    triage around HERALD_32: temporal and sector shuffles degrade performance, formula
    relation gives a small MLP lift, and target shuffle is documented as a weak gate. No
    model/recommendation/causal promotion.
32. `canonical/HERALD_34_FR_ZE2020_TOP3_ENTRY_HPC_SPEC.md` — superseded HPC spec; its
    training contract predates the horizon-aware label-maturity correction in HERALD_38.
33. `canonical/HERALD_35_FR_ZE2020_TOP3_ENTRY_HPC_AUDIT.md` — historical audit of job
    7734742, now `INVALID_FOR_CLAIMS` because the run used immature 3-year labels.
34. `canonical/HERALD_36_FR_ZE2020_TARGET_ALIGNED_RELATION_LIFT.md` — historical local
    diagnostic, now `INVALID_FOR_CLAIMS`; its lift history also used immature labels.
35. `canonical/HERALD_37_FR_ZE2020_TOP3_ENTRY_LIFT_HPC_SPEC.md` — superseded by the
    corrected temporal contract and paired seed-year audit gates in HERALD_38.
36. `canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md` — correction audit:
    enforces horizon-aware label maturity, separates retrospective interpretation from
    as-of-time relation inputs, regenerates the ranking/dynamic-graph chain, and invalidates
    all dependent local/HPC results pending a clean rerun.
37. `canonical/HERALD_39_FR_ZE2020_RELATION_EMBEDDING_LINEAR_PROBES.md` — minimal
    representation diagnostic using frozen linear probes over the existing dynamic graph:
    temporal successor and next-year sector state against node-only, randomized-endpoint,
    and past-only snapshot controls. No new encoder or recommendation claim.
38. `canonical/HERALD_40_FR_ZE2020_RELATIONAL_TRANSITION_TRANSFER_GATE.md` —
    pre-registered ZE-disjoint probe of whether past relational-neighbourhood changes
    transfer to an externally observed future top-3 sector entry. Job 7780697 fails the
    gate: current relation changes do not separate from randomized or sector-shuffled
    controls; the next diagnostic isolates and normalizes edge families.
39. `canonical/HERALD_41_FR_ZE2020_EDGE_FAMILY_ISOLATION_GATE.md` — isolates equal-schema
    blocks for each dynamic edge family under the same ZE-disjoint transition task. Job
    7780874 finds a limited pass for `ze_similarity` only; sparse sector-economic families
    do not pass and are not promoted.
40. `canonical/HERALD_42_FR_ZE2020_SIMILARITY_NONLINEAR_TRANSFER_GATE.md` — fixed MLP gate
    for the isolated ZE-similarity block. Job 7780890 fails: node-only MLP is strongest,
    while adding ZE similarity degrades ranking and AP. Recurrent/neural graph complexity
    remains blocked.
41. `canonical/HERALD_43_FR_ZE2020_RELATION_BOTTLENECK_FUSION_GATE.md` — pre-prediction
    PCA bottleneck for ZE-similarity before the MLP head. Job 7780898 recovers the raw
    concatenation loss but remains below node-only and near randomized endpoints; neural
    fusion stays blocked pending better externally grounded edge semantics.
42. `canonical/HERALD_44_FR_ZE2020_OFFICIAL_COMMUTING_EDGE_PROVENANCE.md` — replaces
    the unverified legacy mobility matrix with reproducible directed commuting snapshots
    from official INSEE commune flows (2012/2017/2023), reconciled to 280 ZE2020 through
    official COG events. Observation-time and strict ex-ante availability are separate;
    the implemented strict assignment covers decision years 2016--2025 without using the
    2023 release. This remains a model-input candidate, not a neural result.
43. `canonical/HERALD_45_FR_ZE2020_COMMUTING_RELATION_GATE.md` — records the
    release-aware linear transfer gate for official commuting relations. The
    raw weighted relation failed because uniform weights were better; a matched
    topology-only endpoint placebo is the remaining admissible diagnostic.
44. `canonical/HERALD_46_FR_ZE2020_COMMUTING_TOPOLOGY_GATE.md` — records the
    matched topology-only falsification required by HERALD_45. Randomized
    uniform destinations outperformed the real uniform topology, closing
    weight transforms and neural integration for this representation.
45. `canonical/HERALD_47_FR_ZE2020_A10_SOURCE_PROVENANCE.md` — closes the
    France ZE2020 A10 lineage gap by rebuilding the canonical sector panel
    directly from checksum-pinned official INSEE SIDE data. The reconstructed
    panel is byte-identical; this validates provenance, not a relation model.
46. `canonical/HERALD_48_FR_ZE2020_CONTEXT_CONDITIONED_SECTOR_RELATION_SPEC.md`
    — separates the already-completed pooled Phase 7 precedence study from the
    remaining ZE-heterogeneity question and pre-registers a held-out-ZE,
    linear-versus-nonlinear relation gate with matched shuffles.
47. `canonical/HERALD_49_FR_ZE2020_CONTEXT_CONDITIONED_SECTOR_RELATION_RESULT.md`
    — records the five-seed DEC-077 result. The context-conditioned MLP loses
    strongly to the pooled linear control and does not degrade consistently
    under source/context placebos, closing this target/feature specification.
48. `canonical/HERALD_50_FR_ZE2020_PRODUCT_SPACE_ENTRY_DENSITY_SPEC.md`
    — pre-registers a leakage-safe, held-out-ZE test of whether product-space
    density ranks next-year specialization entries beyond sector prevalence,
    target RCA, and matched semantic placebos.
49. `canonical/HERALD_51_FR_ZE2020_PRODUCT_SPACE_ENTRY_DENSITY_RESULT.md`
    — records the DEC-078 gate failure: product-space density beats matched
    random/semantic placebos but not current target RCA and exceeds both
    marginal controls in only 4/13 years.
50. `canonical/HERALD_52_FR_ZE2020_TEMPORAL_BIPARTITE_RECONSTRUCTION_SPEC.md`
    — pre-registers a held-out-ZE masked-reconstruction test over directly
    observed ZE2020 x A10 sector compositions, with compositional, linear,
    temporal, information-ablation, and semantic-shuffle controls.
51. `canonical/HERALD_53_FR_ZE2020_TEMPORAL_BIPARTITE_RECONSTRUCTION_RESULT.md`
    — records the DEC-079 gate failure: the full nonlinear view beats Ridge,
    information ablations, and semantic shuffles, but previous-year
    compositional persistence remains decisively stronger.
52. `canonical/HERALD_54_FR_ZE2020_COMPOSITION_TRANSITION_RANKING_SPEC.md`
    — pre-registers a held-out-ZE ranking test of next-year sector-share
    transition magnitude and direction using observed temporal compositions,
    with own-history, linear, ablation, and semantic-shuffle controls.
53. `canonical/HERALD_55_FR_ZE2020_COMPOSITION_TRANSITION_RANKING_RESULT.md`
    — records the DEC-080 gate failure: the joint MLP uses nonlinear temporal
    and sector-identity information but loses to past delta and target-sector
    history, so this transition-ranking specification is closed.
54. `canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`
    — freezes, under DEC-081, what the product's forecasting engine is (sectoral
    persistence at ZE x sector, recorded as a candidate pending its own
    rolling-origin audit; the ZE-total baseline stays macro dashboard context),
    what the relational layer may claim (association and audited predictive
    precedence; never generalized incremental predictive value, causality, or
    automatic recommendation), and the single condition that authorizes another
    model experiment (an exogenous sectoral structure independent of the
    enterprise-birth panel that survives a matched placebo). Also fixes the E1–E7
    delivery sequence and records the documentary sweep for inconsistent ranges.
55. `canonical/HERALD_57_FR_ZE2020_AVAILABILITY_MASKS.md`
    — separates, under DEC-082, the A10 observational mask (already complete:
    35,280 cells, one reconciled observed zero, nothing to build) from a new
    standalone relational availability mask that classifies all 84 family x
    decision-year cells and states why a relation is absent — commuting has no
    snapshot released before 2016, and the three derived signal families cannot
    exist before 2017 because their growth feature starts in 2014 under a
    three-year correlation minimum. Records, without fixing, that the dynamic
    graph splits file assigns training roles to years holding no edges.
56. `canonical/HERALD_58_FR_ZE2020_SECTORAL_PERSISTENCE_AUDIT_SPEC.md`
    — pre-registered protocol for the rolling-origin audit that decides whether
    sectoral persistence at ZE x sector can be promoted from candidate to the
    product's forecasting engine. Fixes the target as absolute counts and
    excludes shares, whose closed composition is a plausible structural
    limitation consistent with DEC-078/079/080 rather than a demonstrated
    mechanism, making a persistence win there uninterpretable;
    derives the official 2019–2025 comparison window from the training rules
    rather than from any metric, keeps the 2013–2025 persistence-only figure in
    a separate non-comparable table, forbids seed repetition for deterministic
    models including Ridge, and pre-registers a gate that reads WMAPE alone and
    admits `NO_ENGINE_DESIGNATED` as an outcome. Registered as DEC-083 before
    execution. **Part A result appended after execution (DEC-084):
    `ENGINE_DESIGNATED`, engine = sectoral persistence.** `ridge_ar` had the
    lower aggregate WMAPE (0.1062 vs 0.1165) but was blocked by two conditions
    registered in advance — it beat persistence in only 4 of 7 years against the
    required 6, and regressed past the 10% per-sector veto in FZ and KZ — so the
    result must never be read as persistence being more accurate than Ridge. The
    national-trend baseline was worse than plain persistence. **Part B closes as
    `NO_FORECAST_DERIVED_STATE_LAYER` (DEC-085):** persistence predicts zero
    change by construction, so states derived from it would label every cell
    STAGNATION under any threshold. No thresholds were chosen and no
    distribution was inspected; a direction estimator would be a new model
    experiment, reachable only via DEC-081 Q3.
57. `canonical/HERALD_59_FR_ZE2020_RANKING_GAP_AUDIT.md`
    — E4 coverage map of the HERALD_23 §5-§6 ranking metrics and controls
    against what DEC-069→080 and HERALD_38 §8 actually executed. NDCG@3,
    Precision@3, Hit Rate@3 and the random-graph, temporal-shuffle,
    sector-shuffle and no-graph controls are covered; Recall@K, average future
    growth of top-K, the no-sector ablation, a geography-only baseline,
    leave-one-year-out and bootstrap edges are not. Decisive finding: the
    executed gates stored aggregated metrics only, never per-cell predictions,
    but that conclusion was **falsified by the repository's own artifacts**: the
    corrected HERALD_38 §8 runs do store per-cell predictions, so Recall@3 and
    the average future growth of the selected top-3 are recomputable without
    running any model. E4 is reclassified INCOMPLETE, the recomputation is
    pre-registered in §10, and the four remaining gaps (no-sector,
    geography-only, leave-one-year-out, bootstrap edges) stay unauthorized under
    Q3. **Delivered (DEC-086 result addendum):** 40 files, 358,400 groups, no
    model fitted. Recall@3 is undefined in 7,984 groups and excluded from every
    mean; the selected three sectors grew 0.3824 on average against 0.6037 for
    the three that actually grew most, about 63% of what was attainable.
    No consistent incremental advantage of relation-bearing configurations is
    observed in these descriptive recomputed metrics (spread 0.006 across
    configurations, ties dominant at 72–84%); the differences are small in this
    stored output, but no equivalence margin or test was pre-registered, so
    statistical equivalence is not claimed. The corrected target shuffle collapses both
    metrics; temporal shuffle raises recall while lowering growth. Nothing is
    promoted, the closed targets stay closed, and E5 is unblocked.
58. `canonical/HERALD_60_FR_ZE2020_GRAPH_FIRST_DASHBOARD_SPEC.md`
    — E5 specification, no code written (DEC-087). Fixes what each visual
    element may assert before any of it exists: the node shows what was
    observed, the panel reports the predicted level, the edge shows an audited
    association. Node colour is the recent **observed** trajectory on a
    continuous scale with no bins and no growth/stagnation/decline wording, so
    it cannot become the forecast-derived state DEC-085 refused; persistence is
    confined to a numeric field because it repeats the last level and carries no
    direction. Each edge species is its own layer with its own grain and
    evidence scale — ZE↔ZE has a scale of its own, DEC-066 tiers being
    sector-to-sector only — and the DEC-082 availability mask decides whether a
    layer renders at all, with unavailable years narrated rather than blank.
    IAT/NAF/NACE absent until E6. Three product decisions are reserved for the
    owner before implementation.

## Control Documents

- `HERALD_CURRENT_STATE.md` — current component status and next step.
- `HERALD_METHODOLOGICAL_DECISION_LOG.md` — immutable DEC-* decision trail.
- `HERALD_ACTIVE_DOCUMENT_INDEX.md` — classification of current, historical, and closed evidence.
- `HERALD_REPORTS_CONSOLIDATION_MAP.md` — where each old report cluster is represented.
- `HERALD_PROJECT_CHARTER.md` — permitted and forbidden claims.
- `HERALD_NAMING_CONVENTIONS.md` — canonical labels and status vocabulary.
- `herald_artifact_registry.json` — artifact provenance and allowed use.

## Dashboards

Current dashboard candidate:

- `dashboards/herald_observatory_v051_narrative_dashboard.html`

Stable scientific baseline/dashboard lineage is documented in the canonical roadmap.

## Policy

Do not add new root-level phase reports. New scientific work needs a DEC-* entry and
should either update a canonical report or create a clearly scoped artifact referenced
from the active document index.
