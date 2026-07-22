# HERALD 42 -- France ZE2020 similarity nonlinear transfer gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
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
