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
| `fr_ze2020_dynamic_graph_edges_expanding.csv.gz` | audited historical edge memory for dense node-year aggregates |
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

The learned relation scores are intentionally sparse because the objective
scores controlled evaluation pairs, not every possible ZE2020 x sector node.
The encoder therefore also exports dense graph-memory aggregates:

```text
relation_graph_in_weight_mean
relation_graph_in_weight_abs_sum
relation_graph_in_signal_mean
relation_graph_in_stability_mean
relation_graph_in_count
relation_graph_out_weight_mean
relation_graph_out_weight_abs_sum
relation_graph_out_signal_mean
relation_graph_out_stability_mean
relation_graph_out_count
relation_graph_in_<edge_type>_weight_mean
relation_graph_embedding_available
```

These dense fields come from the audited dynamic graph edge memory and preserve
the representation role of the layer. They are not learned labels and they are
not recommendation scores.

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

## 4b. Downstream Ranking Smoke

Local diagnostic after adding dense graph-memory aggregates:

| Coverage year | Learned sparse available | Dense graph available |
|---:|---:|---:|
| 2017-2021 | 0 / 2520 rows per year | 2520 / 2520 rows per year |
| 2022 | 22 / 2520 | 2520 / 2520 |
| 2023 | 22 / 2520 | 2520 / 2520 |
| 2024 | 35 / 2520 | 2520 / 2520 |
| 2025 | 80 / 2520 | 2520 / 2520 |

The coverage problem is fixed for downstream representation tests. The ranking
value is still mixed:

| Target | Config | Ridge ΔNDCG@3 vs base | MLP ΔNDCG@3 vs base |
|---|---|---:|---:|
| 1y | learned sparse embeddings | +0.0001 | +0.0001 |
| 1y | dense graph embeddings | -0.0177 | +0.0147 |
| 1y | shuffled dense graph embeddings | -0.0135 | +0.0031 |
| 3y | learned sparse embeddings | +0.0000 | +0.0182 |
| 3y | dense graph embeddings | -0.0002 | +0.0054 |
| 3y | shuffled dense graph embeddings | -0.0030 | -0.0190 |

Interpretation: the dense representation is now usable as model input, but no
downstream ranking claim is authorized yet. The next test must run repeated
seeds and stronger placebos before any promotion.

## 5. Claim Policy

Allowed:

```text
HERALD now has a learned dynamic relation representation layer for ZE2020 x
sector nodes, plus dense graph-memory aggregates derived from audited dynamic
edge inputs.
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
