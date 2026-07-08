# HERALD 30 -- France ZE2020 Relation-Embedding Ranking Diagnostic

**Status:** `DIAGNOSTIC_READY_NO_MODEL_PROMOTION`.

This document records the first downstream test of the HERALD_29 dynamic
relation encoder embeddings in the retrospective ZE2020 x sector ranking task.
It does not create an operational recommendation system and does not validate a
dynamic GNN.

## 1. Question

The diagnostic asks:

```text
Do the HERALD_29 relation embeddings improve retrospective ZE2020 x sector
ranking beyond the existing formula features and a shuffled graph placebo?
```

This is a representation test, not a policy recommendation.

## 2. Script

```text
src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_ranking.py
```

The script reads:

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_node_embeddings_v1.csv
```

It writes only to a required `--output-dir`, so it does not overwrite canonical
processed inputs by default.

## 3. Configurations

| Feature config | Meaning |
|---|---|
| `base_formula_features` | existing ranking features from HERALD_24 |
| `no_relation_features` | formula features with relation columns removed |
| `learned_sparse_embeddings` | base features plus learned relation-score aggregates |
| `dense_graph_embeddings` | base features plus dense `relation_graph_*` memory aggregates |
| `all_embeddings` | base features plus sparse learned and dense graph aggregates |
| `shuffled_dense_graph_embeddings` | dense graph columns shuffled inside each year |

The shuffled configuration is the key local placebo: if real graph embeddings do
not beat this, the representation is not yet defensible as a ranking input.

## 4. Local Diagnostic

Local run:

```text
input embeddings: /tmp/herald_relation_embedding_ranking_inputs/
outputs 1y:       /tmp/herald_relation_embedding_ranking_local_h1/
outputs 3y:       /tmp/herald_relation_embedding_ranking_local_h3/
seeds:            42 43 44 45 46
max_epochs:       40
feature configs:  base_formula_features, dense_graph_embeddings,
                  shuffled_dense_graph_embeddings
```

### 1-year target

Mean NDCG@3 across 5 seeds x 3 eval years:

| Config | Ridge | MLP |
|---|---:|---:|
| base formula | 0.5015 | 0.4782 |
| dense graph | 0.4838 | 0.4740 |
| shuffled dense graph | 0.4828 | 0.4642 |

Reading:

- dense graph is slightly above shuffled graph for MLP (`+0.0097` NDCG@3);
- dense graph is below the base formula features (`-0.0042` for MLP, `-0.0177` for Ridge);
- no ranking claim is authorized.

### 3-year target

Mean NDCG@3 across 5 seeds x 3 eval years:

| Config | Ridge | MLP |
|---|---:|---:|
| base formula | 0.4588 | 0.5001 |
| dense graph | 0.4586 | 0.4856 |
| shuffled dense graph | 0.4565 | 0.4777 |

Reading:

- dense graph is again above shuffled graph for MLP (`+0.0079` NDCG@3);
- dense graph remains below the base formula features (`-0.0145` for MLP);
- Ridge is essentially unchanged;
- no ranking claim is authorized.

## 5. Interpretation

The result is scientifically useful but not promotional:

```text
The dense graph representation carries some non-random structure because it
beats the shuffled dense graph placebo in the MLP head. However, it does not yet
beat the existing base formula features, so it cannot be promoted as a superior
downstream ranking representation.
```

This means the next work should improve the representation objective or model
architecture before any HPC-heavy claim.

## 6. Claim Policy

Allowed:

```text
HERALD has a tested relation-embedding ranking diagnostic.
The dense graph representation is usable and contains weak non-random ranking
signal relative to the shuffled graph placebo.
```

Forbidden:

```text
HERALD has validated a dynamic GNN.
HERALD has validated automatic recommendation.
HERALD has proven that relation embeddings improve ranking over the base formula
features.
HERALD has identified causal economic influence.
```

## 7. Next Step

Do not launch a broad HPC run of this exact diagnostic as a promoted model test.
The useful next step is narrower:

```text
1. keep dense graph embeddings as a representation input;
2. test a stronger model head or contrastive/auto-supervised objective;
3. keep the shuffled graph placebo and base formula control;
4. only then prepare an HPC batch.
```
