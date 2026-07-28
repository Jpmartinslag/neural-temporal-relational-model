# HERALD 59 -- France ZE2020 Retrospective Ranking Gap Audit

**Date:** 2026-07-28
**Status:** `RANKING_GAP_AUDIT_INCOMPLETE_CORRECTED` -- the original section 5 conclusion was
falsified by the repository's own artifacts. See section 5 and the DEC-086 correction
addendum.
**Stage:** E4 of the sequence fixed in HERALD_56 section 5.
**Decision entry:** DEC-086.

## 0. Scope

This is a **documentary audit**. It runs no model, executes no gate, produces no metric and
creates no code, as HERALD_56 section 4 requires of a stage of this kind.

Its single question is: of the metrics and controls that
`HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md` sections 5 and 6 require of a
retrospective ZE x sector ranking validation, **which have already been executed, and what
genuinely remains**. The point is to avoid re-running a battery that DEC-069 through DEC-080
and HERALD_38 section 8 have already covered.

It does not prejudge whether the remainder should be executed. That question is answered in
section 5, and the answer is not the audit's to make.

## 1. Method

Coverage was established from three sources, not from memory:

1. the metric keys each executed gate runner emits, read from
   `src/modeles/france_ze2020/run_*.py`;
2. the control views named in the DEC records for DEC-069 to DEC-080 and in HERALD_38
   section 8;
3. what the executed runs actually left on disk, under `hpc_results/`.

A metric or control counts as **covered** only when an executed run reported it. Being
implemented in a script that never ran under a valid specification does not count, and is
recorded separately.

## 2. Metric coverage (HERALD_23 section 5)

| Metric | Status | Evidence |
|---|---|---|
| **NDCG@K** | **covered**, K=3 | primary metric of DEC-069, 070, 071, 072, 074, 075, 078, 080 |
| **Precision@K** | **covered**, K=3 | `precision_at_3` emitted by the transfer probe, edge-family isolation, commuting, product-space and composition-transition gates |
| **Hit Rate@K** | **covered**, K=3 | `hit_rate_at_3` emitted by the same five runners |
| Average precision | covered (extra) | `average_precision` in four of the five |
| **Recall@K** | **NOT COVERED** | required by HERALD_23 section 5 and HERALD_17 section 255; **zero occurrences of `recall` anywhere in `src/modeles/france_ze2020/`** |
| **Average future growth of top-K vs baseline top-K** | **NOT COVERED by any valid run** | implemented as `mean_future_growth_top_k` / `mean_future_growth_actual_top_k` **only** in `train_fr_ze2020_sector_ranking.py`, whose numerical results are `INVALID_FOR_CLAIMS` (HERALD_38 section 5). None of the three corrected falsification runners computes it |

The second gap is the economically meaningful one: every covered metric scores whether the
ranking put the right sectors on top, and none of them reports **how much the recommended
sectors actually grew** relative to a baseline's picks.

## 3. Control coverage (HERALD_23 section 6)

| Control | Status | Evidence |
|---|---|---|
| **random graph / random score** | **covered** | randomized endpoints in DEC-069, 070, 071, 072, 074; matched uniform randomized endpoints in DEC-075; reassigned product-space identities and random score in DEC-078; random ranking in DEC-080 |
| **temporal shuffle** | **covered** | 5 runners; executed in DEC-079, DEC-080 and the corrected HERALD_38 section 8 runs |
| **sector shuffle** | **covered** | 8 runners; executed in DEC-069, 070, 078, 079, 080 and HERALD_38 section 8 |
| **no graph** | **covered** | node-only / no-relation views in 11 runners; the reference view of DEC-069 to DEC-072 |
| **no sector** | **NOT COVERED by any valid run** | a `no_sector_composition` view exists in `run_fr_ze2020_sector_ranking_falsifications.py`, but that belongs to the HERALD_24 line, whose status is `CORRECTED_PENDING_RERUN`; HERALD_38 section 8 audited only the top-3 and relation-lift jobs |
| **geography-only** | **NOT COVERED at this grain** | zero occurrences of contiguity or distance-based ranking in the ZE2020 runners. Geography was tested at Italy NUTS3 and closed (DEC-008/011); commuting (DEC-073/074/075) is functional mobility, a different object from geographic proximity |
| **leave-one-year-out** | **NOT COVERED** | zero occurrences anywhere in `src/modeles/france_ze2020/`. Evaluation is rolling-origin, which is not the same test: rolling-origin asks whether the model works going forward, leave-one-year-out asks whether one year carries the result |
| **bootstrap edges** | **NOT COVERED at this grain** | zero occurrences in the ZE2020 code. Phase 7 used bootstrap at country grain on a different object (DEC-034) |

## 4. Baseline coverage (HERALD_23 section 5)

| Baseline | Status |
|---|---|
| random ranking | covered (DEC-078, DEC-080) |
| largest past growth | covered -- `past_delta`, and it **won** DEC-080 |
| simple specialization share | covered -- current target RCA, and it **won** DEC-078 |
| persistence / temporal baseline | covered (DEC-079, DEC-080, and DEC-084 at the level target) |
| largest past volume | partially covered -- target-sector prevalence in DEC-078 |
| sector-only baseline | partially covered -- target-history-only MLP in DEC-080 |
| geography-only relation | **not covered** (see section 3) |

## 5. The original decisive finding was wrong

**Superseded.** This section originally asserted that "the executed gates persisted
aggregated metric rows and summaries only. No per-cell predictions were stored anywhere",
and concluded that the missing metrics could not be recomputed. **That is false**, and the
falsifying evidence was already in the repository.

The error was a partial search generalized into a universal claim: three gate runners and
the `hpc_results/` directories of the DEC-069 to DEC-080 gates were inspected, and the
absence found there was asserted of everything. The corrected HERALD_38 section 8 runs were
never looked at, and they do store per-cell predictions.

### 5.1 Corrected inventory, by run

| Class | Runs | Consequence |
|---|---|---|
| **Corrected outputs with per-cell predictions** | `fr_ze2020_top3_entry_temporal_fix_top3_20260713_143828` (20 prediction files); `fr_ze2020_top3_entry_lift_temporal_fix_lift_20260713_143828` (20); plus the corrected target-shuffle reruns `..._target_top3_20260713_145326` (5) and `..._target_lift_20260713_145326` (5) | **metrics can be recomputed without running any model** |
| **Aggregated outputs only** | commuting relation gate; commuting topology gate; context sector relation; product-space entry density; relation-embedding probes; temporal bipartite; transition ranking | metrics there would require re-executing a closed specification |
| **`INVALID_FOR_CLAIMS`** | the pre-HERALD_38 ranking runs (`fr_ze2020_sector_ranking_20260701_183849`, `fr_ze2020_sector_ranking_falsifications_20260701_185923`, `fr_ze2020_dynamic_graph_ranker_20260702_091544`, `fr_ze2020_top3_entry_20260708_174219`) and the `target_shuffle` scenario **inside** the two corrected main directories, superseded by the reruns above (HERALD_38 section 8) | must not be used for any metric, old or new |

The smoke run `fr_ze2020_top3_entry_smoke_temporal_fix_20260713_143010` also holds
predictions but is explicitly not scientific evidence (HERALD_38 section 7) and is excluded.

### 5.2 What this changes

Two of the six gaps are **recomputable from stored predictions**: Recall@3 and the average
future growth of the selected top-3. Both are recomputed under the pre-registration in
section 10 below.

The other four -- the `no_sector` ablation, a geography-only baseline, leave-one-year-out
and bootstrap edges -- are unchanged and **remain unauthorized**: they would apply new
controls to closed targets, or introduce a new relational input, both of which DEC-081 Q3
governs. (The original text said "three missing controls" while listing four; corrected
here.)

## 6. What must not be re-run

For the record, so that a future pass does not mistake coverage for absence:

- The NDCG@3 / Precision@3 / Hit Rate@3 batteries of DEC-069 to DEC-080. Covered, with
  matched placebos, and their targets are closed.
- The random-graph, temporal-shuffle, sector-shuffle and no-graph controls. Covered
  repeatedly, across several targets.
- The corrected top-3 and relation-lift falsifications of HERALD_38 section 8, including the
  repaired target-shuffle bundle.

Adding a metric to any of these means re-running it, and re-running it means reopening a
closed specification.

## 7. Recorded gaps, for whenever a specification legitimately reopens them

Kept as a checklist, not as a work plan. None is authorized now.

| Gap | Why it would matter | What it would cost |
|---|---|---|
| Average future growth of top-K vs baseline top-K | the only metric that says whether the recommended sectors actually grew, rather than whether they were ranked correctly | re-execution of a closed ranking specification, or a new target |
| Recall@K | complements Precision@K when the positive set varies in size across ZE-years | same |
| `no_sector` ablation | isolates how much of the ranking is A10 structure rather than territory dynamics | same, plus the HERALD_24 line must first clear its `CORRECTED_PENDING_RERUN` status |
| Geography-only baseline | HERALD_23 section 6 asks whether HERALD adds anything over physical proximity; commuting does not answer it | a new relational input at ZE2020 grain, which Q3 governs |
| Leave-one-year-out | rolling-origin does not test whether a single year drives a result; 2020 and 2021 are obvious candidates given the COVID sensitivity recorded throughout | re-execution |
| Bootstrap edges | robustness of relation signals at ZE2020 grain, as Phase 7 did at country grain | re-execution |

## 8. Consequence for the sequence

E4 does **not** close with the original "no execution" verdict. It closes only after the two
recomputable metrics are produced under section 10. **E5 remains blocked until then.**

The four unauthorized gaps become relevant only if E6 and E7 produce an authorized
experiment, at which point a new specification should draw its metric and control set from
section 7 rather than reinvent it.

## 9. Cross-reference

- Objective, metrics and controls required: `reports/canonical/HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md` sections 5-6.
- Contract, delivery sequence and Q3: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`.
- Invalidated ranking numbers and the corrected falsifications: `reports/canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md` sections 5 and 8.
- Closed ranking targets: DEC-069, DEC-078, DEC-079, DEC-080.
- Engine designation and the absence of forecast-derived states: DEC-084, DEC-085.

---

## 10. Pre-registered recomputation of the two recoverable metrics

**Written before either metric was computed.** Registered as the DEC-086 correction
addendum, in a commit that precedes the implementation commit, so the ordering is provable
from git rather than self-reported.

### 10.1 Scope, and what it may not become

This is a **recomputation from stored predictions**. It fits no model, reruns no gate,
launches no HPC job and touches no closed specification's execution.

**It cannot promote anything.** DEC-069, DEC-078 and DEC-080 closed their targets, and the
HERALD_38 section 8 conclusion -- that the relation layer fails against no-relation,
base-formula and shuffled controls -- stands regardless of what these two metrics show.
Completing a metric checklist is not a new gate, and a favourable number here would be a
**coverage completion, not evidence for promotion**. Any reading beyond that requires Q3.

### 10.2 Source, frozen

| Scenario | Directory |
|---|---|
| `full_control`, `sector_shuffle`, `temporal_shuffle` | `hpc_results/fr_ze2020_top3_entry_temporal_fix_top3_20260713_143828/` and `..._lift_temporal_fix_lift_20260713_143828/` |
| `target_shuffle` | **only** `..._temporal_fix_target_top3_20260713_145326/` and `..._temporal_fix_target_lift_20260713_145326/` |

The `target_shuffle` subdirectories **inside** the two main run directories are
`INVALID_FOR_CLAIMS` (HERALD_38 section 8: the shuffle left the precomputed top-3 label
attached to its original sector) and are excluded. The smoke run is excluded.

### 10.3 Grouping and selection, frozen

Group key: `(ze2020, decision_year, model, feature_config)`. Verified population structure:
each group holds exactly **9 sectors**, exactly **3** are selected by `rank_predicted <= 3`,
and one seed-scenario file yields **6,720 groups**. Models are `logit_entry_classifier` and
`mlp_entry_classifier`; feature configs are `base_formula_features`, `no_relation_features`
and `shuffled_relation_features`; decision years are 2019-2022 at horizon 3.

### 10.4 Recall@3, with the zero-positive rule fixed in advance

```text
Recall@3(group) = (positives among the 3 selected) / (positives in the group)
```

The denominator varies: **positives per group range from 0 to 3**, so Recall@3 is not a
rescaling of Precision@3 and the two genuinely differ.

**Zero-positive rule.** When a group contains no positive at all the denominator is zero and
Recall@3 is **undefined**. It is reported as `NaN`, **excluded from every mean**, and the
**count of such groups is reported alongside every Recall figure**. It is never imputed as
0, never as 1, and never silently dropped. Population structure, inspected only to fix this
rule: **24 of 6,720 groups** in the inspected file have no positive. No metric was computed.

### 10.5 Average future growth of the selected top-3

```text
mean_growth_selected(group)  = mean of target_growth over the 3 selected rows
mean_growth_actual_top3(group) = mean of target_growth over the 3 highest target_growth rows
```

`target_growth` is finite in every row of the inspected file. The second quantity is the
attainable ceiling and is reported as a reference, never as a competitor.

This is the metric that says **how much the recommended sectors actually grew**, rather than
whether they were ordered correctly.

### 10.6 Paired comparison, frozen

Within `(ze2020, decision_year, model, seed, scenario)`, compare the three feature configs
pairwise:

- `base_formula_features` versus `no_relation_features`;
- `base_formula_features` versus `shuffled_relation_features`;
- `no_relation_features` versus `shuffled_relation_features`.

Report, per scenario and per model: the mean of each metric, the paired win rate, and the
count of groups entering each comparison. **No threshold and no gate**: these are descriptive
completions of the HERALD_23 section 5 metric set.

### 10.7 Blocking integrity checks

| Check | Requirement |
|---|---|
| Group shape | exactly 9 sectors and exactly 3 selected per group, else abort |
| Population identity | the three feature configs cover identical `(ze2020, decision_year)` groups within a model and seed |
| Source discipline | no file from an `INVALID_FOR_CLAIMS` directory, and no `target_shuffle` from the main directories, is read |
| Finiteness | every reported figure finite, or an explicitly counted `NaN` from the zero-positive rule |
| No model | the recomputer imports no estimator and fits nothing |
| Determinism | two runs produce byte-identical output |

### 10.8 What is delivered

A metrics recomputer with tests, its output table, and nothing else. No training, no HPC, no
rerun, and no change to any existing verdict.
