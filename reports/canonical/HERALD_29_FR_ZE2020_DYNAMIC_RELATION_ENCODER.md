# HERALD 29 -- France ZE2020 Dynamic Relation Encoder

**Status:** `ENCODER_PROTOTYPE_READY_NOT_FINAL_MODEL`.

HERALD_28 passed the deeper relation-objective falsification batch. The next
step is therefore not to claim a final dynamic GNN, but to materialize the
learned relation signal as a reusable representation layer.

## 1. Purpose

The encoder answers this narrow question:

```text
Can the passed relation objective be converted into learned source-target scores
and node-level ZE2020 x sector relation embeddings for the next model stage?
```

It does not answer:

```text
Which sector should be recommended?
What caused a relation?
Does a dynamic GNN improve the final territorial model?
```

## 2. Inputs

| Input | Role |
|---|---|
| `fr_ze2020_dynamic_graph_nodes.csv` | node-year ZE2020 x sector features |
| `fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz` | candidate typed relations |
| `train_fr_ze2020_dynamic_relation_learner.py` | rolling local compatibility learner |

Configuration:

```text
scenario: dual_endpoint_matched_negatives
target: new_relation
node_feature_lag: 1
feature_family: sector_position_no_rank
pair_feature_mode: compatibility_only
test_pair_mode: unseen_pair
```

## 3. Outputs

Script:

```text
src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_encoder.py
```

Regenerable outputs:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_edges_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_node_embeddings_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_metrics_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_run_v1.json
```

The edge file contains learned `relation_score` values for evaluated
source-target pairs. The embedding file aggregates these scores per node-year:

```text
relation_in_score_mean
relation_in_score_max
relation_in_score_top3_mean
relation_in_count
relation_out_score_mean
relation_out_score_max
relation_out_score_top3_mean
relation_out_count
relation_embedding_available
```

The node embedding table deliberately excludes `relation_label`, `sample_role`,
and `edge_state`, so it can be used as a representation layer rather than a
label leak.

## 4. Local Smoke

Smoke over 2022-2025:

| Eval year | AP | ROC-AUC | Rows |
|---|---:|---:|---:|
| 2022 | 1.0000 | 1.0000 | 16 |
| 2023 | 1.0000 | 1.0000 | 16 |
| 2024 | 0.9228 | 0.9053 | 26 |
| 2025 | 0.9440 | 0.9378 | 60 |
| mean | 0.9545 | 0.9475 | 118 |

These numbers reproduce the passed HERALD_28 relation objective. They are not a
final model result; they confirm the encoder is a faithful representation layer.

## 5. Claim Policy

Allowed:

```text
HERALD now has a learned dynamic relation representation layer for ZE2020 x
sector nodes, derived from a falsified relation objective.
```

Forbidden:

```text
HERALD has validated a dynamic GNN.
HERALD has validated automatic recommendation.
HERALD has discovered causal economic influence.
HERALD has proven final model superiority.
```

## 6. Next Step

The next stage should test whether these embeddings improve a downstream
retrospective ranking/recommendation objective against:

```text
no relation embeddings
deterministic formula embeddings only
temporal/sector shuffled embeddings
random relation scores
```
