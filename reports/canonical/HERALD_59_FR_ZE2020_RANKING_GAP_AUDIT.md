# HERALD 59 -- France ZE2020 Retrospective Ranking Gap Audit

**Date:** 2026-07-28
**Status:** `RANKING_GAP_AUDIT_COMPLETE_NO_EXECUTION_AUTHORIZED`
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

## 5. The finding that decides what E4 can execute

**The executed gates persisted aggregated metric rows and summaries only. No per-cell
predictions were stored anywhere.**

Verified: every gate runner writes `*_metrics_v1.csv`, `*_summary_v1.csv` and a gate JSON,
and the `hpc_results/` directories for the executed runs contain exactly those files. There
is no prediction table to recompute from.

The consequence is decisive and was not obvious before this audit:

> The two missing metrics -- Recall@K and average future growth of top-K -- **cannot be
> added by recomputation**. Obtaining them requires **re-executing a closed specification**.

And the three missing controls are worse placed still. `no_sector` belongs to a line that is
`CORRECTED_PENDING_RERUN`; `geography-only` would introduce a new relational input at
ZE2020 grain; `leave-one-year-out` and `bootstrap edges` would be new falsifications applied
to targets that DEC-069, DEC-078 and DEC-080 **closed**.

Under HERALD_56, re-running a closed gate, or applying new controls to a closed target, is
not authorized by this stage. DEC-081 Q3 is the only route, and Q3 requires an exogenous
sectoral structure surviving a matched placebo -- which E6 has not yet even preflighted.

**Therefore E4 executes nothing.** That is not a deferral for convenience; it is what the
contract already decided, made visible by the storage finding.

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

E4 closes with a coverage map and no execution. E5, the graph-first dashboard, is unblocked
and is the next stage with work in it: it depends on E2 (availability mask, delivered),
DEC-084 (the level engine, delivered) and DEC-085 (no forecast-derived states, delivered),
and on nothing in this document.

The gaps above become relevant only if E6 and E7 produce an authorized experiment, at which
point the metric and control set of a new specification should be drawn from section 7
rather than reinvented.

## 9. Cross-reference

- Objective, metrics and controls required: `reports/canonical/HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md` sections 5-6.
- Contract, delivery sequence and Q3: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`.
- Invalidated ranking numbers and the corrected falsifications: `reports/canonical/HERALD_38_FR_ZE2020_TEMPORAL_INTEGRITY_CORRECTION.md` sections 5 and 8.
- Closed ranking targets: DEC-069, DEC-078, DEC-079, DEC-080.
- Engine designation and the absence of forecast-derived states: DEC-084, DEC-085.
