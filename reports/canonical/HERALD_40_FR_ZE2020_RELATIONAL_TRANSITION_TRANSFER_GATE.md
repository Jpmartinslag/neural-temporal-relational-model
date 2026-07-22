# HERALD 40 -- France ZE2020 relational-transition transfer gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
**Decision:** `DEC-069`

## 1. Question

Do changes in the past relational neighbourhood of a ZE2020 x A10 node help
rank an independently observed future sector transition, and does that signal
transfer to ZE2020 units excluded from model fitting?

This question is narrower than "do economic relations exist?" A failed probe
rejects only the tested graph representation, target, and evaluation protocol.

## 2. Reused canonical inputs

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
```

No legacy STGNN panel or legacy adjacency matrix is permitted. The graph
aggregates are built with the existing audited helper; no new edge builder or
encoder is introduced.

## 3. External transition target

For horizon `h=3`, a candidate sector receives label 1 when:

```text
future_top3_entry_3y = future_top3_growth_3y AND NOT current_top3_share
```

Already-current top-3 sectors are excluded from ranking candidates. The target
comes from observed sector counts at `t+3`; it is not an edge label and is not
constructed from graph predictions.

Training labels must be mature at the decision date:

```text
training_decision_year + 3 <= evaluation_decision_year
```

## 4. Representation under test

For every graph aggregate `g`, the tested change is:

```text
delta_g(i,t) = g(i,t) - g(i,t-1)
```

Only snapshots at `t` and earlier are used. The probe compares:

| View | Purpose |
|---|---|
| `node_only` | temporal-sector control without graph change |
| `node_plus_degree_change` | tests whether simple degree/count change explains the result |
| `real_relation_change` | degree control plus non-count relation changes |
| `random_endpoint_relation_change` | breaks node assignment while preserving year/type edge-value distributions |
| `past_snapshot_relation_change` | replaces the current graph snapshot with one sampled strictly from the node's past |
| `sector_shuffled_relation_change` | breaks sector alignment inside each ZE-year |
| `target_shuffled_relation_change` | breaks the training-label association while preserving yearly prevalence |

## 5. Transfer protocol

Use five deterministic ZE-disjoint folds. For every evaluation year and fold:

- no ZE in the test fold may occur in model fitting;
- training uses only mature labels from the other four folds;
- testing ranks eligible non-top-3 sectors in held-out ZEs;
- the graph remains transductive: observed past features and relations of held-out
  ZEs are available, but their labels never enter fitting.

The model is a standardized logistic regression. This intentionally tests the
representation before adding nonlinear or neural complexity.

## 6. Metrics and gate

Primary metric: `NDCG@3` by ZE-year. Secondary checks: `Precision@3`, hit rate,
average precision, row counts, positive counts, and finite outputs.

The gate passes only if `real_relation_change`:

1. has positive mean `NDCG@3` lift over `node_only`;
2. has positive mean `NDCG@3` lift over `node_plus_degree_change`;
3. beats every graph placebo in at least 60% of paired seed-year-fold results;
4. degrades under both sector shuffle and target shuffle;
5. preserves strict ZE separation and horizon-aware label maturity.

Passing authorizes only a small nonlinear temporal-encoder test. Failure does
not justify discarding territorial relations; it identifies a representation,
target, or protocol that did not transfer.

## 7. Forbidden claims

This diagnostic is not a validated dynamic GNN, causal effect, policy
recommendation, or automatic recommendation system. Allowed language is
association, temporal precedence, transferable signal, and exploratory ranking.
