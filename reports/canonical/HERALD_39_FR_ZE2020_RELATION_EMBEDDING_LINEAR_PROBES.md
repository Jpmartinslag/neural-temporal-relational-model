# HERALD 39 -- France ZE2020 relation-embedding linear probes

**Date:** 2026-07-13
**Status:** `PROBE_IMPLEMENTED_PENDING_FULL_RUN`

## 1. Question

Before adding a contrastive or semi-supervised objective, test the existing
ZE2020 x sector representations with frozen linear probes:

```text
Do current graph aggregates encode temporal succession or next-year node state
beyond node-only and falsified-graph controls?
```

This is a representation diagnostic. It is not a new graph encoder, a validated
dynamic-GNN, a causal analysis, or an automatic recommendation system.

## 2. Implementation

Script:

```text
src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_linear_probes.py
```

Read-only canonical inputs:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
```

The script reuses `build_dense_graph_signal_embeddings()` and the audited
`random_edge_targets` falsification. It writes only to a required
`--output-dir`.

## 3. Probes

| Probe | Task | Metric |
|---|---|---|
| `temporal_successor` | distinguish the true next-year node state from a sector/year-matched wrong node | ROC-AUC, average precision |
| `next_sector_share` | predict next-year observed sector share from the current node representation | MAE, R2 |

Both probes use rolling-origin evaluation. Training rows always have
`target_year < eval_year`.

## 4. Views

| View | Meaning |
|---|---|
| `node_only` | canonical node features, no graph aggregates |
| `real_graph` | node features plus audited dynamic graph aggregates |
| `random_target_graph` | identical edge weights/types with targets shuffled inside year and edge type |
| `random_endpoint_graph` | identical edge values with both source and target assignments shuffled inside year and edge type |
| `past_snapshot_graph` | each node-year graph snapshot replaced only by a snapshot sampled strictly from that node's past |

The past-snapshot placebo never copies a current or future graph snapshot into an
earlier year.

## 5. Decision gate

No contrastive or semi-supervised model should be added unless the real graph:

1. beats `node_only` on paired seed-year results;
2. beats `random_target_graph`;
3. beats `random_endpoint_graph`;
4. beats `past_snapshot_graph`;
5. shows the same direction on both probes;
6. remains finite and stable across the five registered seeds.

Failure means that the current representation has not justified additional
training complexity. Passing authorizes only a minimal auxiliary temporal loss
inside the existing encoder, not a new architecture or a recommendation claim.
