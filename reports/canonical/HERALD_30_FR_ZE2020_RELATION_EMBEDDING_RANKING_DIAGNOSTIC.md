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

Two head modes are available:

| Head mode | Models | Question |
|---|---|---|
| `regression` | Ridge and MLP over future growth | Can the model score sectors by realized growth? |
| `classification` | Logistic and MLP classifiers over future top-3 labels | Can the model identify sectors that enter the future top-3? |

The classification head is closer to the ranking objective because it directly
learns the top-3 event rather than a continuous growth value.

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

## 4b. Classification Head Smoke

Local run:

```text
outputs:          /tmp/herald_relation_embedding_ranking_classifier_local/
target horizons:  1y and 3y
seeds:            42 43 44 45 46
max_epochs:       80
head mode:        classification
feature configs:  base_formula_features, dense_graph_embeddings,
                  shuffled_dense_graph_embeddings
```

Mean NDCG@3:

| Target | Config | Logistic top-3 | MLP top-3 |
|---|---|---:|---:|
| 1y | base formula | 0.5051 | 0.4971 |
| 1y | dense graph | 0.5046 | 0.4797 |
| 1y | shuffled dense graph | 0.5036 | 0.4822 |
| 3y | base formula | 0.4600 | 0.5047 |
| 3y | dense graph | 0.4595 | 0.5076 |
| 3y | shuffled dense graph | 0.4573 | 0.4907 |

Reading:

- for the 1-year target, dense graph embeddings do not help;
- for the 3-year target, `mlp_top3_classifier` with dense graph embeddings is
  slightly above base formula features (`+0.0030` NDCG@3) and more clearly above
  shuffled dense graph (`+0.0170` NDCG@3);
- this is the first ranking-head result aligned with the project objective, but
  the margin is still too small for model promotion.

### Added no-relation control

Additional local control:

```text
outputs:          /tmp/herald_relation_embedding_ranking_classifier_h3_controls/
target horizon:   3y
seeds:            42 43 44 45 46
head mode:        classification
feature configs:  no_relation_features, base_formula_features,
                  dense_graph_embeddings, shuffled_dense_graph_embeddings
```

Mean NDCG@3:

| Config | Logistic top-3 | MLP top-3 |
|---|---:|---:|
| no relation features | 0.4601 | 0.5230 |
| base formula | 0.4600 | 0.5047 |
| dense graph | 0.4595 | 0.5076 |
| shuffled dense graph | 0.4573 | 0.4907 |

Reading:

- the dense graph remains above shuffled dense graph;
- however, removing relation features entirely performs best for the MLP
  classifier (`0.5230` NDCG@3);
- therefore the current relation/graph features are not yet a useful ranking
  input, even though they contain non-random structure.

### Relation-gating triage

A follow-up local triage tested whether filtering the dense graph by stability
or recency fixes the issue:

```text
target horizon:   3y
seeds:            42 43
head mode:        classification
tested filters:   all edges, recent only, age<=1, stability>=0.25,
                  stability>=0.25 and age<=1, stability>=0.5 and age<=1
base control:     no_relation_features
```

Mean NDCG@3, MLP top-3 classifier:

| Feature set | NDCG@3 |
|---|---:|
| no relation features | 0.5283 |
| all dense graph edges | 0.4987 |
| stability >= 0.5 and age <= 1 | 0.4978 |
| stability >= 0.25 and age <= 1 | 0.4933 |
| stability >= 0.25, all ages | 0.4876 |
| recent only | 0.4827 |
| age <= 1 | 0.4782 |

Reading:

- simple stability/recency gating does not solve the problem;
- the current dense graph features still reduce ranking quality versus the
  no-relation control;
- this blocks relation-feature integration into the ranking head for now.

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

The classification-head smoke initially looked promising because the 3-year
`mlp_top3_classifier` beat the base and shuffled controls by a small local
margin. The added no-relation control is stricter and changes the decision:
removing relation features performs best. This blocks HPC promotion of the
current relation embeddings as a ranking input.

The relation-gating triage strengthens that decision: the issue is not only
that old or unstable edges are included. The current graph representation itself
is not yet aligned with the ranking objective.

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
2. do not launch the current relation-embedding ranking test to HPC as a model
   promotion batch;
3. keep relation signals available for exploration and dashboard interpretation;
4. rebuild the relation objective so it is aligned with top-3 sector ranking, not
   only edge existence/compatibility;
5. only then rerun the 3-year top-3 classification objective.
```
