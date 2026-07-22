# HERALD 43 -- France ZE2020 relation-bottleneck fusion gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
**Decision:** `DEC-072`

## 1. Question

Can a compact ZE-similarity representation be fused with temporal node history
before prediction without the degradation observed under raw concatenation?

This is explicitly not residual correction. Both representations are built and
combined before the ranking head, following the HERALD_23 architecture.

## 2. Fixed contract

Unchanged from HERALD_42:

- canonical inputs and `ze_similarity` edges only;
- external 3-year top-3-entry target;
- horizon-aware maturity;
- evaluation years 2020--2022;
- five ZE-disjoint folds and seeds 42--46;
- MLP `(32,16)`, ReLU, Adam, early stopping, maximum 200 epochs;
- `NDCG@3` primary metric.

## 3. Pre-prediction fusion

For every training fold:

```text
node history ------> StandardScaler --------------------+
                                                        +--> MLP ranking head
ZE similarity -----> StandardScaler -> PCA(90% variance)+
```

Both scalers and PCA are fit on training rows only. PCA component count is
selected mechanically by the pre-registered 90% variance threshold; it is not
tuned against evaluation results.

## 4. Views

| View | Purpose |
|---|---|
| `mlp_node_only` | nonlinear temporal control |
| `mlp_raw_ze_similarity` | failed raw-concatenation reference |
| `mlp_bottleneck_ze_similarity` | compact pre-prediction fusion under test |
| `mlp_bottleneck_endpoint_randomized` | matched relation-assignment placebo |
| `mlp_bottleneck_target_shuffled` | training-label placebo |

## 5. Gate

The bottleneck passes only if it:

1. has positive mean `NDCG@3` lift over `mlp_node_only`;
2. has positive mean lift over `mlp_raw_ze_similarity`;
3. has positive mean lift and at least 60% paired wins over the endpoint placebo;
4. degrades under target shuffle;
5. preserves identical populations, finite metrics, mature labels, and zero ZE
   overlap.

A pass authorizes only design of a learned dual encoder before ranking. It does
not validate a dynamic GNN, causal effect, or recommendation system.
