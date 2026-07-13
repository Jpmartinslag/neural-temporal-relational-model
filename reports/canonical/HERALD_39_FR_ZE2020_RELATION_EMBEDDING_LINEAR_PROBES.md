# HERALD 39 -- France ZE2020 relation-embedding linear probes

**Date:** 2026-07-13
**Status:** `PROBE_RUN_COMPLETE_GATE_FAIL`

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

## 6. Full run and audit

Final Slurm job `7756238` completed 5 seeds over evaluation years 2019--2025
with exit `0:0` in 4 minutes 6 seconds. All 325 reported metric rows are finite.
The temporal-successor probe has 30 paired seed-year evaluations (2019--2024);
the next-state probe has 35 (2019--2025). Successor year 2025 is unavailable
because that probe requires a complete candidate feature vector at the next
snapshot.

Mean results:

| Probe | View | Primary metric |
|---|---|---:|
| temporal successor | node only | ROC-AUC 0.8655 |
| temporal successor | real graph | ROC-AUC 0.9520 |
| temporal successor | random target | ROC-AUC 0.9481 |
| temporal successor | random endpoints | ROC-AUC 0.9372 |
| temporal successor | past snapshot | ROC-AUC 0.8643 |
| next sector share | node only | MAE 0.012101 |
| next sector share | real graph | MAE 0.012219 |
| next sector share | random target | MAE 0.012247 |
| next sector share | random endpoints | MAE 0.012323 |
| next sector share | past snapshot | MAE 0.012358 |

Paired reading:

- real graph beats node-only, random-endpoint, and past-snapshot successor
  controls in 30/30 comparisons;
- real graph beats random-target successor in 27/30 comparisons, but by only
  `+0.0039` mean ROC-AUC;
- real graph loses to node-only next-state prediction in 25/35 comparisons and
  increases mean MAE by `0.000118`;
- real graph beats the random-endpoint next-state control in 23/35 comparisons,
  but this does not compensate for losing to node-only.

Decision: the current graph aggregates contain reproducible temporal identity
and succession structure, but they do not add next-state information beyond the
node panel. The pre-registered cross-probe gate fails. Do not add contrastive or
semi-supervised training yet. The next diagnostic must isolate which outgoing
graph aggregates drive successor recognition and test whether that signal is
node identity, degree history, or economically transferable relation structure.

Operational note: job `7756235` failed before execution because the remote
checkout lacked the already-versioned encoder helper. The dependency was synced
and validated with a real import preflight. Job `7756236` completed the initial
four-view run; job `7756238` is the final five-view result after adding the
stronger random-endpoint control.
