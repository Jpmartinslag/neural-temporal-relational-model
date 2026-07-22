# HERALD 45 -- France ZE2020 commuting-relation gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
**Decision:** `DEC-074`

## 1. Question

Do official, release-aware commuting relations carry transferable
territorial-sector information beyond time availability, random endpoints,
unweighted topology, reversed direction, and the previously retained
trajectory-similarity relation?

This is a linear relation gate. It does not train a neural graph encoder.

## 2. Fixed evaluation contract

The target and protocol are unchanged from HERALD_40--43:

- target: externally observed future top-3 sector entry over three years;
- evaluation years: 2020, 2021, 2022;
- five ZE-disjoint folds;
- seeds 42--46;
- training labels admitted only after the full three-year horizon matures;
- standardized logistic regression;
- primary metric: `NDCG@3`;
- identical candidate populations across paired views.

## 3. Relation representation

For each ZE-sector node and decision year, the strict commuting matrix
`W_t` aggregates five already-observed node features:

```text
outgoing profile = W_t X_t
incoming profile = column_normalize(W_t)' X_t
```

The five inputs are sector count, sector share, sector rank, lagged sector
growth, and dominant-sector flag. The relation block also contains outgoing
degree, maximum weight, weight entropy, incoming degree, incoming weight sum,
and a separate availability mask.

This occurs before prediction. It is not a residual correction.

## 4. Views

| View | What it tests |
|---|---|
| `node_only` | temporal-sector baseline |
| `commuting_availability_only` | whether a release-period flag alone explains a lift |
| `commuting_real` | official directed weighted commuting semantics |
| `commuting_endpoint_randomized` | same source/year weights and target multiset, false destinations without self-loops |
| `commuting_uniform_weights` | real topology without commuting intensity |
| `commuting_reversed_direction` | workplace-to-residence instead of residence-to-workplace |
| `trajectory_similarity_reference` | surviving DEC-070 similarity family under the same target/folds |
| `commuting_target_shuffled` | false training labels |

## 5. Pre-registered gate

`commuting_real` passes only if all conditions hold:

1. positive mean NDCG@3 lift over `commuting_availability_only`;
2. positive mean lift and at least 60% paired wins over randomized endpoints;
3. positive mean lift over uniform weights;
4. positive mean lift over reversed direction;
5. positive mean lift over the trajectory-similarity reference;
6. positive degradation relative to target shuffle;
7. identical train/test populations, finite metrics, mature labels, and zero ZE overlap.

A failure rejects this representation under this target and protocol. It does
not reject commuting as an economic relation generally.

## 6. Decision rule

A pass authorizes only a small pre-prediction dual temporal/commuting encoder.
It does not validate a dynamic GNN, causal influence, automatic recommendation,
or policy action.

A failure blocks neural integration and requires inspecting whether commuting
must be sector-conditioned, flow-thresholded, or used under a different
auditable relational objective.

## 7. Execution

Pending. This section must record job ID, environment, row/population checks,
metrics, paired gates, and final decision after the fixed run.
