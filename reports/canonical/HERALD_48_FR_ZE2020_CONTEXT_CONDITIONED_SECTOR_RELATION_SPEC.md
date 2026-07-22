# HERALD 48 -- ZE2020 context-conditioned sector-relation specification

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
**Decision:** `DEC-077`

## 1. What is already known

This experiment is not a rerun of sector precedence at ZE scale.

- Phase 7 already pooled France ZE2020 observations in lag-1 partial
  regressions with territory/year demeaning, permutation, FDR, and territory
  bootstrap.
- France produced one main promoted edge and zero COVID-robust edges.
- DEC-060 showed that the fixed absolute-beta threshold was the main binding
  gate; several associations were stable but small.
- Phase 8 LOTO localized influence on already-robust country coefficients. It
  did not estimate one relation model per ZE, and France had no robust edge to
  localize.
- HERALD_29--30 learned and tested graph-memory embeddings, but their current
  relation objective did not improve downstream ranking over no-relation
  controls.

## 2. Remaining question

Does lagged source-sector change add transferable information about a target
sector only after conditioning on the ZE's lagged economic composition?

The hypothesis is heterogeneity, not a larger pooled coefficient. A relation
may be useful in one ZE context and negligible or reversed in another. Fitting
72 directed pairs independently inside each ZE is not admissible: 14 annual
observations per zone are insufficient. The model must share parameters across
ZEs and be evaluated on zones excluded from training.

## 3. Canonical data contract

Read only:

```text
fr_ze2020_sector_panel.csv
fr_ze2020_sector_relational_features.csv
```

For target sector `b`, source sector `a`, ZE `z`, and year `t`:

```text
label                = growth of sector b ending at t
target_history       = growth of sector b ending at t-1
source_relation      = growth of sector a ending at t-1
ZE context           = shares/diversity/concentration observed through t-1
```

The label is evaluation-only. Every feature ends at `t-1` or earlier. Missing
growth is excluded from that sample; it is never filled with a pseudo-value.
Source and target sectors must differ.

## 4. Fixed views

| View | Purpose |
|---|---|
| `no_source_mlp` | nonlinear target-history and ZE-context control |
| `pooled_linear_relation` | closest reusable Phase 7-style source-lag baseline |
| `context_conditioned_mlp` | source lag plus shared nonlinear interactions with lagged ZE context |
| `source_shuffled_mlp` | false source-sector lag, shuffled within year and source/target sector |
| `context_shuffled_mlp` | real source lag with ZE context assigned to another zone in the same year |
| `target_shuffled_mlp` | false training labels; sanity control only |

Use the existing `(32,16)` ReLU/Adam MLP configuration from DEC-071, with
early stopping and at most 500 iterations. The 500-iteration ceiling was fixed
after the technical smoke showed that 200 iterations could stop unconverged;
this is a convergence correction, not a performance search. Every fit records
its iteration count and convergence status. No architecture, depth, width,
learning-rate, feature, or threshold search is permitted after the full run.

## 5. Evaluation

- rolling-origin evaluation;
- evaluation years fixed before execution from years with complete mature
  labels and at least four prior training years;
- five ZE-disjoint folds and seeds 42--46;
- identical test rows for all views;
- primary metric: MAE of target-sector growth;
- secondary metrics: R2 and paired absolute-error lift;
- relation signal summaries are associations/precedence only.

## 6. Pre-registered gate

All conditions are required:

1. no non-finite metric, no duplicate key, zero train/test ZE overlap, and all
   substantive model fits converged; target-shuffle convergence is recorded but
   does not block integrity because random labels may contain no learnable
   stopping signal;
2. `context_conditioned_mlp` has lower mean MAE than `no_source_mlp`;
3. it has lower mean MAE than `pooled_linear_relation`;
4. it beats `source_shuffled_mlp` in at least 60% of paired
   seed/year/fold comparisons and has positive mean lift;
5. context shuffle has positive mean MAE degradation and loses at least 60% of
   paired seed/year/fold comparisons, showing that any source signal depends on
   ZE context rather than source lag alone;
6. target shuffle increases relative mean MAE by at least 5% and loses at least
   80% of paired comparisons;
7. every feature is reconstructable from information available by `t-1`.

## 7. Interpretation boundary

A pass would show only that nonlinear, context-conditioned predictive
precedence transfers to held-out ZEs under this task. It would authorize the
design of a small temporal relation encoder, not validate one.

A failure would close this target/feature specification. It would not prove
that French sector relations do not exist.

No outcome establishes structural causality, validates a dynamic GNN, or
authorizes automatic territorial recommendation.

## 8. Implementation readiness

The fixed runner and five-seed Slurm package are implemented in:

```text
src/modeles/france_ze2020/run_fr_ze2020_context_conditioned_sector_relation_gate.py
hpc/france_ze2020_context_sector_relation/
```

Corrected technical smoke job `7781009` completed on Meso in 8m05s with exit
`0:0`, empty stderr, finite metrics, zero ZE overlap, identical populations,
and convergence for every view (127--279 iterations for the five MLP fits).
The single 2024/fold-0/seed-42 cell beat the nonlinear no-source and shuffled
controls but lost to the pooled linear control. This is a runtime and
convergence check only; it is not the registered multi-year/fold/seed result.
