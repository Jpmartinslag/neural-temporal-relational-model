# HERALD 40 -- France ZE2020 relational-transition transfer gate

**Date:** 2026-07-22  
**Status:** `PROBE_RUN_COMPLETE_GATE_FAIL`  
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

## 8. Execution and audit

The pre-registered smoke job `7780695` completed first with one seed. The full
Meso job `7780697` then completed in 5 minutes 54 seconds with exit `0:0` and
empty stderr.

Audit facts:

- 5 seeds: 42--46;
- evaluation years: 2020--2022;
- 5 deterministic ZE-disjoint folds;
- 525 metric rows and 75 paired seed-year-fold keys;
- 224 train ZEs and 56 test ZEs per fold, with zero overlap;
- identical train, test, and positive populations across all seven views;
- all primary and secondary metrics finite.

## 9. Results

| View | Mean NDCG@3 | Mean AP |
|---|---:|---:|
| `node_only` | 0.60096 | 0.53709 |
| `node_plus_degree_change` | 0.60497 | 0.53755 |
| `real_relation_change` | 0.60595 | 0.53218 |
| `random_endpoint_relation_change` | 0.60569 | 0.52860 |
| `past_snapshot_relation_change` | 0.59505 | 0.51593 |
| `sector_shuffled_relation_change` | 0.60618 | 0.53033 |
| `target_shuffled_relation_change` | 0.46040 | 0.37009 |

Paired `NDCG@3` findings for real relation change:

- lift over node-only: `+0.00499`;
- lift over degree change: `+0.00098`;
- lift over randomized endpoints: `+0.00026`, with only 53.3% paired wins;
- lift over past snapshot: `+0.01090`, with only 46.7% paired wins;
- lift over sector shuffle: `-0.00023`, with only 18.7% paired wins;
- lift over target shuffle: `+0.14555`, with 92.0% paired wins.

The target-shuffle degradation shows that the external transition task is
learnable. It does not rescue the relation hypothesis: real relation changes do
not separate from endpoint-randomized or sector-shuffled controls.

## 10. Decision and next diagnostic

Decision: `RELATIONAL_TRANSITION_TRANSFER_GATE_FAIL`.

This result rejects only the current graph-change representation under this
target and protocol. It does not reject nonlinear economic relations generally.
No nonlinear temporal encoder or semi-supervised objective is authorized from
this gate.

The expanding graph is highly imbalanced by edge family:

| Edge family | Rows |
|---|---:|
| `ze_similarity` | 257,823 |
| `cross_ze_same_sector` | 426 |
| `intra_ze_sector` | 211 |

The next admissible diagnostic is therefore to isolate each edge family and
normalize family scales, then rerun the same ZE-disjoint transition gate. This
tests whether the sparse economic relations are hidden by the dominant general
ZE-similarity layer. It must precede any larger neural architecture.
