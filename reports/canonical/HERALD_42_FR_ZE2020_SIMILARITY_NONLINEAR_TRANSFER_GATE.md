# HERALD 42 -- France ZE2020 similarity nonlinear transfer gate

**Date:** 2026-07-22  
**Status:** `PROBE_RUN_COMPLETE_GATE_FAIL`  
**Decision:** `DEC-071`

## 1. Question

Does a small nonlinear classifier extract transferable transition-ranking
information from the isolated ZE-similarity block beyond linear and node-only
controls?

This is not yet a recurrent encoder, message-passing network, or validated
dynamic GNN. It is the minimum gate before introducing those components.

## 2. Fixed inputs and protocol

Reuse without modification:

- canonical dynamic nodes and expanding edge memory;
- only `edge_type=ze_similarity`;
- family-prefixed graph aggregates and their year-over-year changes;
- `future_top3_entry_3y_label` outside the current top 3;
- evaluation years 2020--2022;
- horizon-aware training-label maturity;
- five deterministic ZE-disjoint folds and seeds 42--46;
- primary metric `NDCG@3`.

## 3. Models and controls

| View | Purpose |
|---|---|
| `logit_node_only` | linear non-graph reference |
| `logit_ze_similarity` | passed DEC-070 linear relation reference |
| `mlp_node_only` | isolates nonlinearity without graph information |
| `mlp_ze_similarity` | nonlinear representation under test |
| `mlp_ze_similarity_endpoint_randomized` | breaks ZE assignment of relation edges |
| `mlp_ze_similarity_target_shuffled` | breaks training-label association |

The MLP is fixed before execution: hidden layers `(32,16)`, ReLU, Adam,
standard scaling fit on training rows only, early stopping, and maximum 200
epochs. There is no tuning or architecture search.

## 4. Gate

`mlp_ze_similarity` passes only if it:

1. has positive mean `NDCG@3` lift over `mlp_node_only`;
2. has positive mean lift over `logit_ze_similarity`;
3. has positive mean lift and at least 60% paired wins over
   `mlp_ze_similarity_endpoint_randomized`;
4. degrades under `mlp_ze_similarity_target_shuffled`;
5. preserves identical populations, finite metrics, mature labels, and zero ZE
   overlap.

A pass authorizes only the design of a small recurrent temporal encoder using
the same relation block. It does not authorize causal, recommendation, or final
dynamic-GNN claims.

## 5. Execution audit

Smoke job `7780889` completed first. Full Meso job `7780890` completed in 6
minutes 51 seconds with exit `0:0` and empty stderr.

- 5 seeds, evaluation years 2020--2022, and 5 ZE-disjoint folds;
- 6 views, 450 metric rows, and 75 paired seed-year-fold keys;
- identical train, test, and positive populations across all views;
- zero ZE overlap and all metrics finite;
- no hyperparameter search after observing results.

## 6. Results

| View | Mean NDCG@3 | Mean AP |
|---|---:|---:|
| `logit_node_only` | 0.60096 | 0.53709 |
| `logit_ze_similarity` | 0.60677 | 0.53289 |
| `mlp_node_only` | 0.61426 | 0.54633 |
| `mlp_ze_similarity` | 0.59570 | 0.50063 |
| `mlp_ze_similarity_endpoint_randomized` | 0.58868 | 0.49054 |
| `mlp_ze_similarity_target_shuffled` | 0.44392 | 0.36485 |

Paired `NDCG@3` findings for MLP ZE-similarity:

- lift over MLP node-only: `-0.01856`;
- lift over logistic ZE-similarity: `-0.01107`;
- lift over endpoint-randomized MLP: `+0.00702`, with 56.0% paired wins;
- lift over target-shuffled MLP: `+0.15178`, with 97.3% paired wins.

The target is learnable and the endpoint assignment contains some information,
but neither fact satisfies the gate: the relation MLP loses to both required
non-placebo controls.

## 7. Decision

Decision: `NONLINEAR_ZE_SIMILARITY_GATE_FAIL`.

The MLP node-only result shows that nonlinear interactions in the canonical node
history can be useful. Adding the current ZE-similarity block makes both ranking
and average precision worse. This is consistent with noisy or overly sparse
relational inputs, but the experiment does not identify the mechanism.

ZE similarity remains a linear exploratory ranking indicator. No recurrent
temporal encoder, graph-neural architecture, causal claim, or recommendation
layer is authorized by this result. Hyperparameter tuning after seeing the gate
would invalidate the pre-registration and is therefore not performed.
