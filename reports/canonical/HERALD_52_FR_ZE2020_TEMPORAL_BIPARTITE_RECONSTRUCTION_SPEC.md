# HERALD 52 - France ZE2020 temporal bipartite reconstruction spec

**Date:** 2026-07-24  
**Decision:** DEC-079  
**Status:** `PRE_REGISTERED_NOT_RUN`

## 1. Question and prior-work boundary

DEC-079 asks whether the directly observed ZE2020 x A10 composition at year
`t`, combined with its lagged composition at `t-1`, supports transferable
masked reconstruction in held-out ZEs.

This is materially different from the closed relation objects:

- it does not infer edges from correlation, trajectory similarity, commuting,
  or product-space density;
- it does not reopen DEC-017, DEC-069--075, DEC-077, or DEC-078;
- it does not predict next-year growth or specialization entry;
- it uses observed ZE-sector shares as weighted bipartite edges and evaluates
  only artificial masks over values that are actually observed.

The test is a representation preflight, not production imputation and not a
dynamic graph-neural model.

## 2. Fixed data and support

Only this canonical input is allowed:

```text
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
```

The support-only preflight found:

- 280 ZE2020;
- 9 A10 sectors;
- 14 years, 2012--2025;
- 35,280 unique ZE-year-sector rows;
- 3,920 complete ZE-year compositions;
- every observed composition sums to one within floating-point tolerance;
- every source availability mask equals one.

No reconstruction score was inspected before this registration.

## 3. Observed temporal bipartite object

For each year `t`, define a weighted bipartite graph:

```text
territory nodes: 280 ZE2020
sector nodes:    9 A10 sectors
edge weight:     sector_share(z, s, t)
```

The temporal input for a ZE-year combines:

```text
visible current edges at t
visibility mask at t
complete lagged composition at t-1
target-sector identity
```

No inferred ZE-to-ZE or sector-to-sector edge enters this diagnostic.

## 4. Fixed artificial masking

For every eligible ZE-year, hide exactly three of the nine sectors. Hiding one
sector is forbidden because the compositional sum would reveal it exactly.
The selected triple must have positive hidden mass. Seeds are fixed at
42--46, and every view receives the same ZE-year-sector targets for a given
seed.

The model receives zero payload for hidden current shares plus an explicit
visibility mask. Loss and evaluation use hidden cells only. Real missing
values are neither created nor filled in the canonical panel.

Predictions for each hidden triple are clipped to non-negative values and
renormalized to the known remaining mass:

```text
remaining_mass = 1 - sum(visible current shares)
predicted_hidden_share(s) = remaining_mass * positive_score(s)
                            / sum positive_score(hidden sectors)
```

This makes every compared output compositionally valid.

## 5. Fixed split and temporal protocol

- five fixed ZE-disjoint folds;
- evaluation years: 2017--2025;
- training ZEs: the other four folds only;
- training years for evaluation year `t`: 2013 through `t`;
- held-out ZEs never enter training in any year;
- no year after `t` enters fitting, scaling, masking, or feature construction.

Using current-year observations from training ZEs is allowed because this is a
cross-sectional masked-reconstruction task, not a forecast. The lagged profile
for every sample is exactly year `t-1`.

## 6. Fixed models and controls

No hyperparameter search is authorized.

| View | Role |
|---|---|
| `temporal_persistence` | hidden-sector allocation from the same ZE at `t-1` |
| `sector_mean_closure` | remaining mass allocated by training-ZE target-sector means at `t` |
| `ridge_bipartite` | linear model using current visible edges, masks, lagged shares, and target identity |
| `mlp_bipartite` | one fixed nonlinear MLP using the same inputs as Ridge |
| `mlp_history_only` | removes current visible ZE-sector edges |
| `mlp_current_only` | removes lagged composition |
| `mlp_sector_shuffle` | shuffles current sector identities within ZE-year |
| `mlp_temporal_shuffle` | shuffles lagged ZE profiles within year |
| `random_closure` | random positive allocation of remaining mass |

The MLP is fixed to hidden layers `(64, 32)`, ReLU activation, Adam,
`alpha=0.001`, learning rate `0.001`, at most 300 epochs, and early stopping
with validation fraction `0.15` and 20 epochs without improvement. Standard
scaling is fitted on training rows only. Ridge uses `alpha=1.0` with the same
training-only scaling. Every output is evaluated after the same compositional
projection.

## 7. Metrics

Primary metric:

```text
masked MAE on reconstructed sector shares
```

Secondary metrics:

- masked RMSE;
- allocation MAE inside the hidden three-sector simplex;
- convergence rate;
- paired result by seed, evaluation year, and ZE fold.

Lower error is better.

## 8. Registered gate

Every condition is required:

1. complete finite outputs, identical hidden targets across views, exactly
   three hidden sectors per ZE-year, compositional sums preserved, and zero
   train/test ZE overlap;
2. `mlp_bipartite` has lower aggregate masked MAE than
   `ridge_bipartite`, `temporal_persistence`, and `sector_mean_closure`;
3. `mlp_bipartite` beats `ridge_bipartite` in at least 60% of paired
   seed/year/fold comparisons;
4. it beats both `mlp_history_only` and `mlp_current_only` in at least 60% of
   paired comparisons with positive aggregate lift;
5. both `mlp_sector_shuffle` and `mlp_temporal_shuffle` degrade in at least
   60% of paired comparisons with positive aggregate degradation;
6. `mlp_bipartite` beats Ridge and both information-ablation MLPs in at least
   6 of the 9 evaluation years;
7. seed-level coefficient of variation of `mlp_bipartite` MAE is at most 20%.

## 9. Decision boundary

A pass would show that a small nonlinear temporal encoder learns transferable
information from the observed ZE-sector bipartite composition beyond linear,
closure, single-time, and shuffled controls. It would authorize design of one
small temporal bipartite representation layer.

A failure closes this masked-reconstruction specification. It does not prove
that the observed compositions are economically meaningless.

Neither outcome validates a dynamic GNN, fills real missing data, proves
causality, or authorizes automatic territorial recommendation or policy action.
