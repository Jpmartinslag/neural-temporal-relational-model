# HERALD 27 — France ZE2020 Relation Objective Gate

**Created:** 2026-07-04.
**Status:** `RELATION_OBJECTIVE_GATE_AND_LOCAL_SMOKE_READY`.
**Scope:** pre-training audit and local relation-learner smoke after HERALD_26.
This document does not launch HPC, does not validate a new graph architecture,
and does not create an operational recommendation layer.

---

## 1. Why this gate exists

HERALD_23 reframed the project away from "better forecast" and toward temporal-
relational representation learning for auditable indicators and future
exploratory ZE x sector ranking.

HERALD_24 then created the ZE x sector ranking bridge.

HERALD_25/HERALD_26 tested the first dynamic graph path and found:

```text
time signal:      supported
sector signal:    supported / moderate
edge magnitude:   not supported in the current message encoder
neural advantage: not supported yet
```

The 20260702 edge-sign placebo is the key blocker: `edge_sign_only` matched or
slightly exceeded `full_control` on the leading edge variants. This means the
current aggregated-message model mostly uses edge presence/sign, not economic
edge intensity.

Therefore the next run must not be "more epochs on the same graph". The next
run needs a relation objective that tests whether HERALD learns relationships
between ZE-sector nodes.

---

## 2. Hypotheses retained

### H1 — Temporal signal

Retained.

Question:

```text
Does ordering and lag history matter?
```

Current evidence:

```text
temporal_shuffle hurts results in ranking/dynamic-graph falsifications
```

Required next check:

```text
Any new relation learner must keep temporal-shuffle and year-order controls.
```

### H2 — Sector structure

Retained.

Question:

```text
Does A10 sector structure add information beyond a flat territorial table?
```

Current evidence:

```text
sector-shuffle and sector-only variants show that sector structure carries signal
```

Required next check:

```text
Any new relation learner must include no-sector and sector-shuffle controls.
```

### H3 — Current edge weights

Rejected for the current message encoder.

Question:

```text
Does edge_weight magnitude behave as economic intensity?
```

Current evidence:

```text
edge_sign_only ≈ full_control on the best candidates
```

Reading:

```text
The current encoder uses edge existence/sign more than magnitude.
```

Consequence:

```text
Do not promote current edge_weight as learned economic intensity.
Do not launch deeper neural training on the same aggregated-message design.
```

### H4 — Relation learning

Still open.

Question:

```text
Can HERALD learn a temporal-relational representation h_{ZE,sector,t} that is
useful for ranking or relation inspection?
```

This has not been answered by HERALD_25/HERALD_26, because those runs tested
hand-built edge aggregation more than a direct relation-learning objective.

---

## 3. Input audit

### Canonical inputs still allowed

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_sector_only.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_precision_sector_only.csv.gz
```

### Forbidden inputs remain forbidden

```text
dynamic_stgnn_feature_panel*
graph_adjacency_core_v0.csv
graph_adjacency_mobility_v0.csv
train_herald_v6/v7/semi_v2/regime outputs as current evidence
```

### 2025 finding

2025 is present in the observed sector panel and in dynamic graph nodes/edges,
but it is not a normal retrospective training/evaluation year in the current
ranking panel:

```text
fr_ze2020_dynamic_graph_nodes.csv:
  2025 rows exist: 2,520
  feature_complete in 2025: 0 / 2,520
```

Reason:

```text
HERALD_24 defines decision_year=T using feature rows from year=T+1, because the
feature file's lag columns represent values observed up to T.
```

So:

```text
decision_year=2024 can be evaluated for 1-year target using observed 2025.
decision_year=2025 cannot be evaluated retrospectively without future 2026.
decision_year=2025 should instead be handled by a separate inference panel.
```

Required before any "2025 recommendation/ranking" output:

```text
Build a separate inference-safe panel, for example:
data/processed/france_ze2020/fr_ze2020_sector_ranking_inference_2025.csv
```

This panel must have features available through 2025, no future label required,
and a different claim status from retrospective evaluation rows.

---

## 4. Objective correction

The next model should not start as:

```text
predict future_growth with aggregated messages
```

That was already tested and the edge layer failed the sign/magnitude placebo.

The next objective should test relation learning directly:

```text
learn h_{i,t} for node i=(ZE2020, sector)
```

Then evaluate one or more of:

| Objective | What it tests | Caveat |
|---|---|---|
| temporal edge prediction | whether future/held-out relations are distinguishable from plausible non-relations | depends heavily on negative sampling |
| edge-state reconstruction | whether the model learns persistent/new/decaying relation states | does not prove economic causality |
| contrastive ZE-sector embedding | whether related nodes are closer than controlled negatives | requires careful negatives |
| ranking auxiliary head | whether learned representations help ZE x sector ranking | ranking remains exploratory |

The simplest acceptable next prototype is not a new "validated dynamic GNN".
It is:

```text
dynamic relation learner smoke
```

---

## 5. Negative sampling warning

Dynamic link/relation learning is sensitive to negative sampling. Random
non-edges may be too easy and can produce a false positive result.

Required controls for any relation-objective model:

```text
random negative pairs
typed hard negatives
same-year hard negatives
degree/popularity baseline
edge-sign-only control
random-edge-target control
temporal shuffle
sector shuffle
```

Do not accept a relation learner that only beats easy random negatives.

---

## 6. Literature check

Recent temporal graph work supports the gate rather than contradicting it:

- Jiang and Pu (2023), *Exploring Time Granularity on Temporal Graphs for
  Dynamic Link Prediction in Real-world Networks*: time granularity and negative
  sampling strongly affect dynamic link prediction.
- Hu et al. (2024 revision), *Dynamic Graph Representation Learning via Edge
  Temporal States Modeling and Structure-reinforced Transformer*: edge temporal
  states should be modeled explicitly; static weights can miss changing
  inter-node relationships.
- Daniluk and Dabrowski (2023), *Temporal graph models fail to capture global
  temporal dynamics*: simple baselines and negative-sampling design can expose
  degeneration in temporal graph models.
- Romero et al. (2023), *New Perspectives on the Evaluation of Link Prediction
  Algorithms for Dynamic Graphs*: dynamic link-prediction evaluation depends
  critically on the kind of negative samples used and varies over time.

Implication for HERALD:

```text
The next model must be evaluated as a temporal relation learner with hard
placebos, not as a generic neural ranker.
```

---

## 7. Local executable lot

HPC remains blocked.

Implemented local lot:

```text
src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py
tests/test_fr_ze2020_dynamic_relation_learner.py
```

Minimum behavior:

```text
input:  dynamic graph nodes + one audited edge candidate file
output: local-only metrics/predictions under data/processed/france_ze2020/
claim:  exploratory relation-learning smoke, not recommendation
```

Minimum scenarios:

```text
full_control
easy_random_negatives
typed_hard_negatives
edge_sign_only
random_edge_targets
temporal_shuffle
sector_shuffle
```

`typed_hard_negatives` means:

```text
cross_ze_same_sector: negative target keeps the same sector but changes ZE.
intra_ze_sector:      negative target keeps the same ZE but changes sector.
```

This avoids an artificial shortcut where the model separates positives and
negatives only because the negative pair violates the edge type's own semantics.

Minimum metrics:

```text
ROC-AUC
Average Precision
Precision@K over candidate pairs
year-by-year metrics
target-popularity baseline
source-target pair-history baseline
all-pair and unseen-pair test modes
same-year and lag-1 node-feature modes
```

Promotion gate:

```text
The model must beat hard negatives and simple popularity/degree baselines across
multiple years before any HPC batch is prepared.
```

If this local gate fails, the next step is not a deeper neural network. The next
step is revising relation labels/edge construction.

---

## 8. Local smoke result

Local smoke command:

```text
python3 src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py \
  --output-dir /tmp/fr_ze2020_dynamic_relation_learner_smoke_typed \
  --scenarios full_control easy_random_negatives typed_hard_negatives \
              edge_sign_only random_edge_targets temporal_shuffle sector_shuffle \
  --eval-years 2021 2022 2023 2024 2025 \
  --max-iter 150 \
  --k 20
```

Summary after adding explicit recurrence/popularity baselines:

| Scenario | Negative strategy | Best model/control | Mean ROC-AUC | Mean average precision | Reading |
|---|---|---|---:|---:|---|
| `easy_random_negatives` | `easy_random` | `relation_logit` | 0.951 | 0.931 | easy negatives are too easy |
| `full_control` | `typed_hard` | `pair_history` | 0.894 | 0.894 | pair recurrence beats the learned classifier |
| `edge_sign_only` | `typed_hard` | `pair_history` | 0.894 | 0.894 | edge magnitude still not used |
| `temporal_shuffle` | `typed_hard` | `pair_history` | 0.894 | 0.894 | current task does not force temporal representation learning |
| `sector_shuffle` | `typed_hard` | `pair_history` | 0.894 | 0.894 | current task does not force sector representation learning |
| `random_edge_targets` | `typed_hard` | `relation_logit` | 0.957 | 0.966 | target-randomization control exposes a weak task design |

For the core `full_control` / `typed_hard` scenario:

| Model/control | Mean ROC-AUC | Mean average precision | Mean precision@K |
|---|---:|---:|---:|
| `pair_history` | 0.894 | 0.894 | 0.990 |
| `target_popularity` | 0.891 | 0.884 | 0.975 |
| `relation_logit` | 0.762 | 0.783 | 0.810 |
| `random` | 0.488 | 0.507 | 0.480 |

Interpretation:

```text
The local relation learner can distinguish observed typed edges from controlled
non-edges, but it does not yet prove dynamic temporal-relational learning. In
the core scenario, simple source-target recurrence and target popularity are
stronger than the learned node-pair classifier.
```

Additional stricter split:

```text
--test-pair-mode unseen_pair
```

This removes from each test year any pair that already appeared as a positive
training relation. It tests whether the model can identify newly appearing
relations instead of repeated source-target pairs.

Core `full_control` / `typed_hard` result under `unseen_pair`:

| Model/control | Mean ROC-AUC | Mean average precision | Mean precision@K |
|---|---:|---:|---:|
| `relation_logit` | 0.743 | 0.579 | 0.438 |
| `target_popularity` | 0.515 | 0.195 | 0.175 |
| `random` | 0.491 | 0.190 | 0.163 |
| `pair_history` | 0.500 | 0.172 | 0.163 |

Reading:

```text
The relation classifier has signal on unseen pairs once direct recurrence is
blocked. This is useful, but still not enough for promotion: temporal_shuffle
improves to ROC-AUC 0.831 / AP 0.665, and random_edge_targets remains very high
(ROC-AUC 0.957 / AP 0.965).
```

Lagged-feature variant:

```text
--test-pair-mode unseen_pair --node-feature-lag 1
```

This predicts relation labels at year `t` using source/target node features
from year `t-1`. It is closer to future-relation prediction than the same-year
diagnostic.

Core `full_control` / `typed_hard` result under `unseen_pair` + lag-1 features:

| Model/control | Mean ROC-AUC | Mean average precision | Mean precision@K |
|---|---:|---:|---:|
| `relation_logit` | 0.786 | 0.550 | 0.500 |
| `target_popularity` | 0.521 | 0.206 | 0.210 |
| `random` | 0.490 | 0.190 | 0.150 |
| `pair_history` | 0.500 | 0.177 | 0.170 |

Reading:

```text
Lag-1 features preserve a relation signal above recurrence/popularity controls,
but still do not validate dynamic temporal learning: temporal_shuffle remains
essentially tied with full_control (ROC-AUC 0.774 / AP 0.555), and
random_edge_targets remains much higher (ROC-AUC 0.939 / AP 0.951).
```

The strongest warning is `random_edge_targets`: this control should have hurt if
the task were truly learning meaningful source-target relation structure. Its
improvement suggests that the current classification task can still be solved by
node/type distribution artifacts.

Decision:

```text
Do not launch HPC from this local learner.
Do not promote it as a graph model.
Use it as a diagnostic showing that the next objective must be stricter:
future-edge prediction, held-out-pair validation, or contrastive embeddings with
harder source-target controls.
```

Tests:

```text
tests/test_fr_ze2020_dynamic_relation_learner.py: 8 passed
```

---

## 9. Claim policy

Allowed after this gate:

```text
HERALD has identified and locally tested a cleaner next objective: dynamic
relation learning over ZE2020 x sector nodes.
```

Forbidden:

```text
HERALD has validated a new dynamic GNN.
HERALD learns causal economic influence.
HERALD can recommend sectors automatically.
2025 rankings are validated outcomes.
Edge weights are economic intensity in the current encoder.
The local relation learner validates a dynamic graph model.
```

Current scientific position:

```text
The data chain is usable, but the next model must be redesigned around relation
learning and stricter source-target falsification. The present blocker is
methodological, not just computational.
```
