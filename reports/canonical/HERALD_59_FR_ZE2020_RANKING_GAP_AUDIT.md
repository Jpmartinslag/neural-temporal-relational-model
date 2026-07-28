# HERALD 59 -- France ZE2020 Retrospective Ranking Gap Audit

**Date:** 2026-07-28
**Status:** `RANKING_GAP_AUDIT_COMPLETE` -- delivered after retraction. The original section 5 conclusion was
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

Group key: `(task, scenario, seed, ze2020, decision_year, model, feature_config)`.

**Amended before any metric was computed.** The first version of this section registered
"exactly 9 sectors and exactly 3 selected per group, and 6,720 groups per seed-scenario
file". That was verified on **one** file -- `top3 / full_control / seed_42` -- and is false
across the corpus. Correcting a factual assumption before computing anything is legitimate;
asserting it from a single sample was not. The verified structure is:

**Corrected twice, and the pattern is worth naming.** The first version claimed 9 sectors
and 3 selected, from one `top3` file. The second claimed a lower bound of 3 sectors -- again
from `top3` alone, while `lift` holds groups of 2. Three samples were generalized into
general facts before the corpus was read. The bound is therefore **dropped**: what is
registered is the pair of invariants that actually hold corpus-wide, and observed ranges are
**reported as output**, never as registered constants.

Registered invariants, verified across all 40 admissible files:

| Invariant | Verified |
|---|---|
| `selected == min(3, group size)` | **holds in every group**, both tasks |
| group size identical across feature configs within a cell | **0 disagreements of 89,600 cells** |

Observed structure, reported rather than registered: sectors per group range 3-9 in `top3`
and 2-9 in `lift`, with 9 dominant; groups number 134,400 (`top3`) and 224,000 (`lift`)
across all scenarios and seeds. Variation comes from candidate availability and label
maturity, not from the models. Because size agrees across feature configs, the paired
comparison remains on identical populations, which is what section 10.7 requires.

Consequences fixed here:

- the shape check aborts if `selected != min(3, size)` in any group, or on any disagreement
  of size across feature configs within a cell; it registers **no lower bound on group
  size**, since none is justified;
- `mean_growth_selected` averages over the selected rows, however many were selected;
- Recall@3 is unaffected: its denominator is the positives in the group, not the group size;
- the precision figure is reported as `hits / selected` and is a **cross-check** against the
  already-published Precision@3, not one of the two registered metrics.

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

Paired within `(ze2020, decision_year, model, seed, scenario)`, separately per task, over
the feature configs each task actually carries -- a second single-sample assumption
corrected here before computing:

| Task | Feature configs present |
|---|---|
| `top3` | `base_formula_features`, `no_relation_features`, `shuffled_relation_features` |
| `lift` | `base_formula_features`, `no_relation_features`, `base_plus_target_aligned_lifts`, `target_aligned_lift_features`, `shuffled_target_aligned_lifts` |

Registered pairs, per task: **every relation-bearing config against `no_relation_features`,
and every relation-bearing config against its own shuffled control.** For `top3` that is
`base_formula` vs `no_relation`, `base_formula` vs `shuffled_relation`, and `no_relation` vs
`shuffled_relation`. For `lift` the shuffled control is `shuffled_target_aligned_lifts`.

Report, per task, scenario and model: the mean of each metric, the paired win rate, the tie
rate, and the count of groups entering each comparison. **No threshold and no gate.**

### 10.7 Blocking integrity checks

| Check | Requirement |
|---|---|
| Group shape | `selected == min(3, group size)` in every group, and group size identical across feature configs within a cell, else abort. **No bound on group size is registered** -- the two bounds tried earlier were sampled from one task |
| Population identity | the three feature configs cover identical `(ze2020, decision_year)` groups within a model and seed |
| Source discipline | no file from an `INVALID_FOR_CLAIMS` directory, and no `target_shuffle` from the main directories, is read |
| Finiteness | every reported figure finite, or an explicitly counted `NaN` from the zero-positive rule |
| No model | the recomputer imports no estimator and fits nothing |
| Determinism | two runs produce byte-identical output |

### 10.8 What is delivered

A metrics recomputer with tests, its output table, and nothing else. No training, no HPC, no
rerun, and no change to any existing verdict.

---

## 11. Recomputation result

Executed under section 10, from stored predictions only. **40 files, 358,400 groups, zero
models fitted, zero jobs launched.** Recall@3 is undefined in **7,984** groups, reported as
such and excluded from every mean.

### 11.1 The two metrics, top3 task, `full_control`

| Model | Feature config | Recall@3 | Growth of selected | Attainable ceiling |
|---|---|---:|---:|---:|
| logit | `base_formula_features` | 0.6481 | 0.3832 | 0.6037 |
| logit | `no_relation_features` | 0.6508 | 0.3837 | 0.6037 |
| logit | `shuffled_relation_features` | 0.6508 | 0.3834 | 0.6037 |
| MLP | `base_formula_features` | 0.6503 | 0.3824 | 0.6037 |
| MLP | `no_relation_features` | 0.6476 | **0.3885** | 0.6037 |
| MLP | `shuffled_relation_features` | **0.6539** | 0.3844 | 0.6037 |

5,600 groups per row, 20 with undefined recall.

**The economic reading, now available for the first time.** The selected three sectors grew
on average **0.3824** against **0.6037** for the three that actually grew most -- the
ranking captures about **63%** of the attainable growth. That is the number the previous
metric set could not express, and it is reported here for the record; it is not a gate and
it authorizes nothing.

**Relation features add nothing on either new metric.** The spread across configs is 0.006
on recall and 0.006 on growth. `no_relation_features` attains the **highest** growth of the
three, and `shuffled_relation_features` the **highest** recall. Both new metrics therefore
agree with the HERALD_38 section 8 conclusion rather than qualifying it.

### 11.2 Paired comparison, MLP, `full_control`

| Metric | Left | Right | left wins | ties | right wins |
|---|---|---|---:|---:|---:|
| Recall@3 | base_formula | no_relation | 0.1353 | 0.7405 | 0.1242 |
| Recall@3 | base_formula | shuffled_relation | 0.0742 | 0.8443 | 0.0815 |
| Recall@3 | no_relation | shuffled_relation | 0.1306 | 0.7224 | 0.1470 |
| Growth | base_formula | no_relation | 0.2395 | 0.4971 | 0.2634 |
| Growth | base_formula | shuffled_relation | 0.1386 | 0.7091 | 0.1523 |
| Growth | no_relation | shuffled_relation | 0.2729 | 0.4636 | 0.2636 |

**Ties dominate** -- 72% to 84% on recall -- and the win and loss shares are near-symmetric
in every pair. Reporting only a win share here would have been misleading, which is why the
tie share is carried beside it.

"Indistinguishable" is used in a defined sense, pinned by test rather than by impression:
across the six model-config combinations of `top3 / full_control`, the **spread between the
best and worst configuration is at most 0.01 on both metrics**, and the **tie share is at
least 0.70 on every recall pair**. `tests/test_fr_ze2020_ranking_metric_coverage.py`
asserts both against the produced artifacts, so if a regeneration ever moves them, the
wording here fails with the test instead of silently outliving its evidence.

### 11.3 Scenario behaviour, MLP, `base_formula_features`

| Scenario | Recall@3 | Growth of selected |
|---|---:|---:|
| `full_control` | 0.6503 | 0.3824 |
| `temporal_shuffle` | **0.7563** | 0.3525 |
| `sector_shuffle` | 0.5409 | 0.3004 |
| `target_shuffle` (corrected rerun) | 0.4826 | 0.2668 |

Three readings:

1. **The corrected target shuffle collapses both metrics**, as it should. This independently
   reproduces the HERALD_38 section 8 repair on two metrics that repair never used.
2. **Sector shuffle degrades**, consistent with the record.
3. **Temporal shuffle behaves inconsistently across the two metrics, and the earlier
   wording here was wrong.** Recall **rises** from 0.6503 to 0.7563, while growth of the
   selected **falls** from 0.3824 to 0.3525. Saying it "does not degrade" was an
   over-reading taken from the recall column alone. The precise statement is: destroying
   temporal order does not degrade the ranking's ability to pick labelled positives -- it
   improves it -- while it does reduce the realized growth of the picks. The first half
   corroborates the HERALD_38 section 8 finding on the metric that finding used; the second
   half is new and points the other way. Neither is a result about relations; both are
   warnings about the target's temporal structure.

### 11.4 What this does not do

It promotes nothing, reopens nothing and changes no verdict. DEC-069, DEC-078 and DEC-080
remain closed; the relation layer still fails against no-relation, base-formula and shuffled
controls. Two entries of the HERALD_23 section 5 metric checklist are now filled, and the
four unauthorized controls of section 7 remain unauthorized.

### 11.5 Artifacts

| Item | Path |
|---|---|
| Summary | `data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_summary_v1.csv` |
| Paired | `data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_paired_v1.csv` |
| Manifest | `data/processed/france_ze2020/fr_ze2020_ranking_metric_coverage_v1.json` |
| Recomputer | `src/modeles/france_ze2020/recompute_fr_ze2020_ranking_metrics.py` |
| Tests | `tests/test_fr_ze2020_ranking_metric_coverage.py` (23 passing) |

Verification: determinism confirmed across two independent output directories; the
recomputer imports no estimator, asserted by test; forbidden and superseded sources abort,
each with its own mutation test; and the zero-positive rule is covered by five tests,
including one that fails if an undefined recall is ever imputed as 0 or 1.

## 12. E4 status

**`RANKING_GAP_AUDIT_COMPLETE`.** The coverage map stands, its false central finding is
retracted and recorded, the two recomputable metrics are delivered, and the four remaining
gaps stay unauthorized. **E5 is unblocked.**
