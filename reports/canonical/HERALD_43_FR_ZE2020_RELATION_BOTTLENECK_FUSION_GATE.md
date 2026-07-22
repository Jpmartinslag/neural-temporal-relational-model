# HERALD 43 -- France ZE2020 relation-bottleneck fusion gate

**Date:** 2026-07-22  
**Status:** `PROBE_RUN_COMPLETE_GATE_FAIL`  
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

## 6. Execution audit

Smoke job `7780897` completed first. Full Meso job `7780898` completed in 8
minutes 11 seconds with exit `0:0` and empty stderr.

- 5 seeds, evaluation years 2020--2022, and 5 ZE-disjoint folds;
- 5 views, 375 metric rows, and 75 paired seed-year-fold keys;
- identical train, test, and positive populations across every view;
- zero ZE overlap and all metrics finite;
- PCA, scalers, and MLP fit separately inside every training fold.

## 7. Results

| View | Mean NDCG@3 | Mean AP |
|---|---:|---:|
| `mlp_node_only` | 0.61426 | 0.54633 |
| `mlp_raw_ze_similarity` | 0.59570 | 0.50063 |
| `mlp_bottleneck_ze_similarity` | 0.61147 | 0.53240 |
| `mlp_bottleneck_endpoint_randomized` | 0.61030 | 0.53413 |
| `mlp_bottleneck_target_shuffled` | 0.45135 | 0.37412 |

Paired `NDCG@3` findings for bottleneck fusion:

- lift over node-only MLP: `-0.00279`;
- lift over raw-concatenation MLP: `+0.01577`;
- lift over endpoint-randomized bottleneck: `+0.00117`, with 54.7% paired wins;
- lift over target-shuffled bottleneck: `+0.16012`, with 98.7% paired wins.

Compression clearly mitigates the raw-concatenation failure. It does not satisfy
the relation gate because node-only remains better and endpoint assignment does
not reach the registered recurrence threshold.

## 8. Decision

Decision: `RELATION_BOTTLENECK_FUSION_GATE_FAIL`.

This result confirms that the integration location was not the only problem.
Even with relation compression and fusion before prediction, current
ZE-similarity semantics add no robust neural transfer beyond node history.

No residual correction, recurrent encoder, dynamic-GNN promotion, or
post-result PCA/MLP tuning is authorized. The next admissible work returns to the
relation layer: audit or reconstruct externally grounded functional edges such
as commuting/mobility flows with reproducible ZE2020 provenance. Current legacy
mobility matrices remain forbidden until that provenance exists.
