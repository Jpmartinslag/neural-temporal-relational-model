# HERALD Graph-Temporal S1 France Audit

**Date:** 2026-06-11
**Decision:** `S1_FR_FAIL`
**Scope:** France, 280 ZE2020, evaluation years 2021-2025

## Result

The canonical AR-Ridge remains the best tested predictor:

| Model | Mean WMAPE | Years beating Ridge | Temporal-null p | Territory-null p |
|---|---:|---:|---:|---:|
| AR-Ridge | 0.064856 | - | - | - |
| A0 neural, no graph | 0.064888 | - | - | - |
| GConvGRU | 0.064922 | 1/5 | 1.0000 | 1.0000 |
| EvolveGCN-H | 0.064973 | 1/5 | 1.0000 | 0.2927 |

Both graph-temporal candidates fail the frozen gate:

- no improvement of at least 1% over AR-Ridge;
- no improvement of at least 1% over the equal-capacity no-graph control;
- fewer than half of evaluation years beat Ridge;
- graph controls are not rejected.

Leakage, seed-stability and tail-risk checks pass. Excluding observation year
2020 from adjacency construction does not materially change the result.

## Interpretation

This result rejects the tested graph-temporal correction under the current
three-feature tensor:

1. one-year sector growth;
2. sector share;
3. normalized sector births.

It does not prove that all regional economic covariates are useless. It does
show that a trainable recurrent graph cannot be justified merely by replacing
the fixed graph corrector while keeping the same narrow information set.

No larger GNN, new hidden-width search or HPC sweep is authorized from S1.
Any reopening requires a new information hypothesis, tested first against
AR-Ridge without a graph.

ARDECO provided that new information hypothesis but failed as a direct linear
predictor (`ARDECO_RIDGE_NOT_PROMOTED`). This keeps the total-forecast
correction branch closed. A separate neural representation task may still be
tested for sector transitions and interpretable territory-sector embeddings;
it is not a continuation of the failed residual-correction search.

Source artifact:
`data/processed/graph_temporal_s1/s1_fr_results.json`.
