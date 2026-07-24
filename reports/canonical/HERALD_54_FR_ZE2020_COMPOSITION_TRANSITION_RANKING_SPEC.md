# HERALD 54 - France ZE2020 composition-transition ranking spec

**Date:** 2026-07-24  
**Decision:** DEC-080  
**Status:** `PRE_REGISTERED_NOT_RUN`

## 1. Question and prior-work boundary

DEC-080 asks whether a small nonlinear model can rank the sectors of a held-out
ZE2020 by the magnitude of their next-year change in sector share and recover
the direction of that change from the complete observed composition history.

This objective is materially different from prior closed tests:

- HERALD_40 ranked three-year entry into a future top-3 growth set using
  changes in inferred graph aggregates;
- HERALD_50/51 tested next-year entry into RCA specialization through
  product-space density;
- HERALD_52/53 reconstructed masked current-year composition levels;
- DEC-080 uses no inferred edge and predicts the continuous next-year change
  of directly observed ZE-sector shares.

No previous gate is reopened. This is a transition-representation diagnostic,
not a validated dynamic graph-neural model or recommendation system.

## 2. Fixed data and support

Only this canonical panel is allowed:

```text
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
```

For territory `z`, sector `s`, and decision year `t`:

```text
delta(z,s,t) = share(z,s,t) - share(z,s,t-1)
target(z,s,t) = share(z,s,t+1) - share(z,s,t)
```

The support-only preflight found:

- 280 ZE2020 and nine A10 sectors;
- decision years 2013--2024;
- evaluation years 2017--2024;
- 30,240 complete decision-year target rows;
- 20,160 held-out evaluation rows per seed;
- exactly 6,720 observed top-3 absolute changes per seed;
- only four exactly zero next-year changes in the full support.

No model score was inspected before registration.

## 3. Fixed representation

For every ZE-sector candidate at year `t`, the full input contains:

```text
complete sector-share vector at t
complete sector-share vector at t-1
complete within-ZE delta vector from t-1 to t
target-sector identity
```

This is the directly observed temporal bipartite composition. No ZE-similarity,
commuting, correlation, product-space, learned, or retrospective relation edge
enters the model.

The model predicts signed `target(z,s,t)`. Ranking uses the absolute predicted
change; direction is evaluated separately from the signed prediction.

## 4. Split and label maturity

- five fixed ZE-disjoint folds;
- seeds: 42--46;
- evaluation years: 2017--2024;
- test rows: held-out ZEs at decision year `t`;
- training ZEs: the other four folds only;
- training decision years: 2013 through `t-1`;
- a training label at year `d` is available only because `d+1 <= t`;
- held-out ZEs never enter fitting, scaling, or threshold construction.

No feature or training label after the evaluation decision year may enter a
fit. The test target at `t+1` is evaluation-only.

## 5. Fixed views

No hyperparameter search is authorized.

| View | Role |
|---|---|
| `zero_change` | predicts no change |
| `past_delta` | repeats each sector's latest observed signed change |
| `ridge_joint` | linear model over the full temporal composition |
| `mlp_joint` | fixed nonlinear MLP over the same full input |
| `mlp_target_history_only` | keeps only the target sector's own two levels and latest delta |
| `mlp_current_only` | removes the `t-1` vector and temporal delta |
| `mlp_sector_shuffle` | shuffles sector identities jointly across level and delta vectors |
| `mlp_temporal_shuffle` | reassigns lagged ZE profiles within year and recomputes deltas |
| `mlp_target_shuffle` | shuffles signed training targets within year and target sector |
| `random_ranking` | random signed ranking control |

Ridge uses training-only standard scaling and `alpha=1.0`. Every MLP uses
training-only standard scaling, hidden layers `(64, 32)`, ReLU, Adam,
`alpha=0.001`, learning rate `0.001`, at most 300 epochs, early stopping,
validation fraction `0.15`, and 20 epochs without improvement. These settings
are inherited unchanged from DEC-079 to prevent architecture tuning.

## 6. Metrics

Primary metric:

```text
graded NDCG@3
```

For each ZE-year, candidates are ordered by absolute predicted change and the
gain is the observed absolute next-year change. This retains information about
transition magnitude instead of reducing every top-3 event to the same label.

Secondary metrics:

- precision@3 against the observed top-3 absolute changes;
- hit rate@3;
- signed MAE over all sectors;
- signed MAE inside the observed top-3 transitions;
- sign accuracy inside the observed top-3 transitions;
- convergence and paired seed/year/fold results.

## 7. Registered gate

Every condition is required:

1. finite outputs, identical test populations and targets across views, zero
   train/test ZE overlap, complete nine-sector groups, and mature labels;
2. `mlp_joint` has higher aggregate graded NDCG@3 than both `past_delta` and
   `ridge_joint`;
3. it beats each of those controls in at least 60% of paired
   seed/year/fold comparisons;
4. it beats `mlp_target_history_only` and `mlp_current_only` with positive
   aggregate lift and at least 60% paired wins;
5. both sector and temporal shuffles degrade with positive aggregate lift and
   at least 60% paired wins;
6. target shuffle loses in at least 80% of paired comparisons;
7. `mlp_joint` has higher observed-top-3 sign accuracy than both `past_delta`
   and `ridge_joint`;
8. it beats past delta, Ridge, and both information ablations in at least 6 of
   the 8 evaluation years;
9. seed-level coefficient of variation of `mlp_joint` NDCG@3 is at most 20%.

## 8. Decision boundary

A pass would show that nonlinear joint temporal-compositional information helps
identify next-year sector-share transitions beyond own-history, linear, and
semantic-placebo controls. It would authorize design of one small transition
representation layer.

A failure closes this continuous transition-ranking specification. It does not
erase the DEC-079 evidence that nonlinear models use joint composition and
time, and it does not prove that economic transitions are unpredictable.

Neither outcome validates a dynamic GNN, structural causality, automatic
territorial recommendation, or policy action.
