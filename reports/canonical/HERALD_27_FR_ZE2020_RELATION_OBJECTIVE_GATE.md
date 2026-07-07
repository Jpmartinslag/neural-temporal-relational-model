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

Correction after semantic random-target audit:

```text
The first random_edge_targets control was too easy because it could break edge-
type semantics. It now randomizes targets while preserving the edge type's
basic constraint: cross_ze_same_sector keeps the same sector, and intra_ze_sector
keeps the same ZE.
```

With `unseen_pair` + lag-1 features after that correction:

| Scenario | Best model/control | Mean ROC-AUC | Mean average precision | Reading |
|---|---|---:|---:|---|
| `full_control` | `relation_logit` | 0.786 | 0.550 | signal above simple controls |
| `edge_sign_only` | `relation_logit` | 0.786 | 0.550 | magnitude still not used |
| `temporal_shuffle` | `relation_logit` | 0.774 | 0.555 | temporal order still not used enough |
| `sector_shuffle` | `relation_logit` | 0.775 | 0.547 | sector structure still not used enough |
| `random_edge_targets` | `target_popularity` | 0.796 | 0.746 | target popularity remains a strong artifact |
| `random_edge_targets` | `relation_logit` | 0.665 | 0.555 | corrected random-target no longer creates the previous artificial classifier spike |

Updated reading:

```text
The previous extreme random-target result was partly a flawed placebo. After
fixing that placebo, relation_logit has a real but still weak relation signal.
The promotion blocker is now sharper: full_control remains almost tied with
edge_sign_only, temporal_shuffle, and sector_shuffle. Therefore the current
objective still does not demonstrate dynamic temporal-relation learning.
```

Emergent-relation target:

```text
--test-pair-mode unseen_pair --node-feature-lag 1 --positive-edge-states new_relation
```

This changes the question from "is this any observed relation?" to "can the
model identify newly appearing relations from previous-year node features?".
That is closer to the HERALD objective of learning dynamic territorial-sector
signals before a future ranking/recommendation layer.

Result:

| Scenario | Model/control | Mean ROC-AUC | Mean average precision | Reading |
|---|---|---:|---:|---|
| `full_control` | `relation_logit` | 0.877 | 0.892 | strong local signal for new relations |
| `sector_shuffle` | `relation_logit` | 0.743 | 0.778 | sector information matters for this target |
| `temporal_shuffle` | `relation_logit` | 0.838 | 0.867 | temporal order still not used enough |
| `random_edge_targets` | `relation_logit` | 0.847 | 0.865 | corrected target placebo still remains close |
| `pair_history` | control | 0.500 | 0.500 | direct pair recurrence is neutral by construction |
| `target_popularity` | control | 0.500 | 0.500 | target popularity is neutral by construction |

Reading:

```text
This is the first more promising relation objective. It removes the direct
recurrence/popularity shortcut and shows that sector structure matters. However,
it is still a local smoke: temporal_shuffle and corrected random_edge_targets
remain too close to full_control for promotion.
```

Feature-family ablation on the same `new_relation` target:

| Feature family | Scenario | Mean ROC-AUC | Mean average precision | Reading |
|---|---|---:|---:|---|
| `all` | `full_control` | 0.877 | 0.892 | strongest combined local signal |
| `all` | `temporal_shuffle` | 0.838 | 0.867 | temporal perturbation hurts only mildly when sector features remain |
| `all` | `sector_shuffle` | 0.743 | 0.778 | sector perturbation hurts clearly |
| `temporal_only` | `full_control` | 0.816 | 0.863 | temporal features alone carry signal |
| `temporal_only` | `temporal_shuffle` | 0.443 | 0.519 | temporal signal collapses when its order is broken |
| `sector_only` | `full_control` | 0.849 | 0.886 | sector features alone carry signal |
| `sector_only` | `sector_shuffle` | 0.476 | 0.520 | sector signal collapses when sector structure is broken |
| `non_temporal` | `full_control` | 0.875 | 0.898 | non-temporal/sector-heavy features carry strong signal |

Reading:

```text
The `new_relation` target is not pure noise: temporal-only and sector-only
families each carry signal, and each collapses under its corresponding shuffle.
The combined model is still not promoted because the two information families
can compensate for each other, making single-shuffle gates too weak.
```

Combined shuffle check:

| Scenario | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `full_control` | 0.877 | 0.892 | combined temporal + sector signal |
| `temporal_shuffle` | 0.838 | 0.867 | temporal-only perturbation is partly compensated by sector features |
| `sector_shuffle` | 0.743 | 0.778 | sector perturbation hurts more clearly |
| `temporal_sector_shuffle` | 0.648 | 0.690 | combined perturbation drops the signal substantially |
| `random_edge_targets` | 0.847 | 0.865 | target-placebo still close enough to block promotion |

Reading:

```text
The combined shuffle is the strongest local evidence so far that the
`new_relation` target uses temporal and sector information jointly. It still
does not authorize HPC/model promotion because corrected random_edge_targets
remains close to full_control.
```

Pair-side ablation:

| Pair feature mode | Scenario | Mean ROC-AUC | Mean average precision | Reading |
|---|---|---:|---:|---|
| `both` | `full_control` | 0.877 | 0.892 | default pair representation |
| `source_only` | `full_control` | 0.500 | 0.500 | source profile alone carries no signal |
| `target_only` | `full_control` | 0.784 | 0.816 | target profile carries substantial signal |
| `difference_only` | `full_control` | 0.860 | 0.881 | source-target distance carries strong signal |
| `pair_structure_only` | `full_control` | 0.500 | 0.500 | edge type / same-zone / same-sector alone is neutral |
| `difference_only` | `random_edge_targets` | 0.909 | 0.915 | corrected target placebo is still easy under distance features |

Reading:

```text
The current `new_relation` classifier is not source-driven. It mostly uses the
target node profile and source-target feature distance. This is useful as a
diagnostic, but it means the next negative sampler must match target profile or
feature distance more tightly before any dynamic relation claim.
```

Distance-hard negative sampling:

```text
distance_hard_negatives
```

For each positive edge, this sampler keeps the typed-hard constraint and chooses
the negative target closest to the positive target in node-feature space. It is
designed to reduce the shortcut found above, where `difference_only` was already
strong.

Result on `new_relation`, `unseen_pair`, lag-1 features:

| Negative strategy | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `typed_hard` | 0.877 | 0.892 | previous typed-hard local signal |
| `distance_hard` | 0.843 | 0.850 | harder negatives reduce but do not eliminate the signal |
| `scaled_distance_hard` | 0.829 | 0.851 | standardized feature distance gives a similar AP, with lower ROC-AUC |
| `pair_distance_hard` | 0.834 | 0.840 | matching source-target distance is slightly harder than target-distance matching |
| `target_preserving_hard` | 0.919 | 0.906 | fixing the target does not collapse the signal; source profile becomes highly discriminative |
| `source_distance_target_preserving_hard` | 0.883 | 0.882 | fixing the target and matching source profile reduces but does not eliminate the signal |
| `dual_profile_hard` | 0.732 | 0.775 | matching both source and target profiles is the hardest control so far |

Pair-side ablation under `source_distance_target_preserving_hard`:

| Pair feature mode | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `both` | 0.883 | 0.882 | default source+target+difference representation |
| `source_only` | 0.877 | 0.884 | source profile alone matches the full representation |
| `target_only` | 0.500 | 0.500 | target is neutral because it is fixed by construction |
| `difference_only` | 0.843 | 0.830 | compatibility/distance signal exists but is weaker than source profile |

Pair-side ablation under `dual_profile_hard`:

| Pair feature mode | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `both` | 0.732 | 0.775 | full pair representation |
| `source_only` | 0.774 | 0.746 | source profile remains strong but no longer dominates AP |
| `target_only` | 0.683 | 0.707 | target profile carries weaker residual signal |
| `difference_only` | 0.706 | 0.764 | source-target distance is close to the full representation |
| `compatibility_only` | 0.667 | 0.726 | distance+interaction signal remains above controls but below full/source/difference |

Local seed check for `dual_profile_hard`, seeds 42-46:

| Model | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `relation_logit` | 0.732 | 0.775 | identical across 5 seeds because the sampler and logit path are deterministic |
| `random` | 0.529 | 0.570 | random baseline varies as expected |
| `pair_history` | 0.500 | 0.507 | neutral |
| `source_popularity` | 0.500 | 0.507 | neutral |
| `target_popularity` | 0.500 | 0.507 | neutral |

Dual-profile shuffle controls:

| Scenario | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `dual_profile_hard` | 0.732 | 0.775 | baseline under the hardest current negative sampler |
| `dual_profile_temporal_shuffle` | 0.646 | 0.725 | temporal perturbation hurts but does not collapse the signal |
| `dual_profile_sector_shuffle` | 0.671 | 0.683 | sector perturbation hurts more clearly |
| `dual_profile_temporal_sector_shuffle` | 0.385 | 0.491 | combined perturbation collapses below the neutral controls |

Compatibility-only shuffle check:

| Scenario | Mean ROC-AUC | Mean average precision | Reading |
|---|---:|---:|---|
| `dual_profile_hard` + `compatibility_only` | 0.667 | 0.726 | compatibility features carry local signal |
| `dual_profile_temporal_sector_shuffle` + `compatibility_only` | 0.414 | 0.510 | combined shuffle removes nearly all compatibility signal |

Compatibility-only feature-family check:

| Feature family | AP before combined shuffle | AP after combined shuffle | Reading |
|---|---:|---:|---|
| `temporal_only` | 0.706 | 0.510 | temporal compatibility contributes signal |
| `sector_only` | 0.690 | 0.517 | sector compatibility contributes signal |
| `non_temporal` | 0.742 | 0.536 | non-temporal/composition features are strongest in this diagnostic |
| `sector_context_only` | 0.705 | 0.512 | explicit sector context carries signal and collapses under shuffle |
| `relation_memory_only` | 0.519 | 0.519 | prior relation-memory features are near-neutral |
| `all` | 0.726 | 0.510 | combined set is useful but not strictly additive |

Sector-context split under `compatibility_only`:

| Feature family | AP before combined shuffle | AP after combined shuffle | Reading |
|---|---:|---:|---|
| `sector_position_only` | 0.781 | 0.570 | strongest family so far; local sector position inside the ZE is highly informative |
| `sector_share_only` | 0.693 | 0.560 | share alone carries signal but is weaker than the combined position profile |
| `sector_rank_only` | 0.673 | 0.604 | rank alone survives shuffle more than desired, so it is not sufficient as a clean signal |
| `dominant_sector_only` | 0.667 | 0.503 | dominant-sector flag alone collapses under shuffle, but is too coarse alone |

Sector-position leave-one-out check under `compatibility_only`:

| Feature family | AP before combined shuffle | AP after combined shuffle | Reading |
|---|---:|---:|---|
| `sector_position_only` | 0.781 | 0.570 | reference: share + rank + dominant flag |
| `sector_position_no_share` | 0.709 | 0.619 | removing share weakens the signal and leaves too much shuffle residue |
| `sector_position_no_rank` | 0.779 | 0.567 | removing rank preserves almost all useful signal |
| `sector_position_no_dominant` | 0.711 | 0.568 | removing dominant flag weakens the signal clearly |

Endpoint-control check for the compact `sector_position_no_rank` family:

| Control | Pair feature mode | Mean ROC-AUC | Mean AP | Reading |
|---|---|---:|---:|---|
| `pair_distance_hard` | `both` | 0.839 | 0.864 | preserving the source and changing only the target keeps strong signal |
| `pair_distance_hard` | `source_only` | 0.500 | 0.500 | source-side shortcut is removed by construction |
| `pair_distance_hard` | `target_only` | 0.819 | 0.864 | target profile alone remains highly informative |
| `pair_distance_hard` | `compatibility_only` | 0.852 | 0.879 | source-target distance/interaction is strongest in this source-preserving control |
| `source_distance_target_preserving_hard` | `both` | 0.907 | 0.917 | preserving the target and changing only the source keeps strong signal |
| `source_distance_target_preserving_hard` | `source_only` | 0.902 | 0.914 | source profile alone explains most of this target-preserving control |
| `source_distance_target_preserving_hard` | `target_only` | 0.500 | 0.500 | target-side shortcut is removed by construction |
| `source_distance_target_preserving_hard` | `compatibility_only` | 0.893 | 0.903 | compatibility signal remains strong but does not beat the source-only shortcut |
| `endpoint_target_matched_hard` | `compatibility_only` | 0.839 | 0.870 | source fixed, negative target matched on compact endpoint profile |
| `endpoint_source_matched_target_preserving_hard` | `compatibility_only` | 0.902 | 0.908 | target fixed, negative source matched on compact endpoint profile |

Reading:

```text
Distance-matched negatives make the objective harder, confirming that part of
the earlier signal came from target/distance shortcuts. Standardizing feature
scales changes ROC-AUC but not AP materially. Matching the source-target
distance directly is slightly harder, but the signal still does not collapse.
Target-preserving negatives fix the positive target and replace only the source
with a semantically valid non-edge source. This removes the target-popularity
shortcut; `target_only` then collapses to AP=0.500, while `source_only` remains
high at AP=0.888. A simple historical `source_popularity` baseline is neutral
at AP=0.500, so the surviving source-side signal is not just "this source has
often appeared before"; it is tied to the source node's temporal/sector feature
profile. Matching the negative source to the positive source profile reduces AP
from 0.906 to 0.882, but the signal does not collapse. Therefore the surviving
signal is not only "popular target" or simple "active source". However,
`source_only` under the hardest current control is still as strong as the full
pair representation, while `difference_only` is weaker. This means the current
objective still does not isolate source-target compatibility cleanly. It remains
a diagnostic gate rather than a promoted model.

The stricter `dual_profile_hard` control matches both sides of the pair. This is
the first local check where the full pair representation beats `source_only` in
AP (0.775 vs 0.746), although the margin is small and `difference_only` remains
close (0.764). This supports continuing toward a compatibility-specific
objective, but it is still not enough to launch HPC or promote a validated graph
model.

The 5-seed local check confirms the `relation_logit` result is stable under the
current deterministic sampler/estimator path. This is useful for reproducibility,
but it is not the same as validating a neural/dynamic-graph architecture across
stochastic training seeds.

The dual-profile shuffle controls are the strongest evidence in this gate. When
both temporal and sector structure are perturbed, the relation signal collapses
from AP=0.775 to AP=0.491, while pair/source/target popularity controls remain
neutral. This supports the hypothesis that the local compatibility signal uses
joint temporal-sector information. The effect is still local and linear-logit
based, so it remains a gate for the next objective rather than a validated model.

The `compatibility_only` feature mode removes raw source and target profiles and
keeps only source-target distance/interactions. It remains above neutral
(AP=0.726), but below the full pair representation (AP=0.775) and close to the
other pair-side controls. The combined temporal+sector shuffle drops it to
AP=0.510, showing the compatibility signal is not merely static geometry in
feature space.

The feature-family split shows the compatibility signal is not purely temporal.
Temporal-only and sector-only both carry signal, while non-temporal/composition
features are strongest in this local diagnostic. This supports a future
temporal-sector model, but it also warns against claiming that temporal dynamics
alone explain the relation objective.

Splitting the non-temporal family shows that the signal is not coming from simple
edge-memory recycling: `relation_memory_only` is near neutral (AP=0.519), while
sector context remains informative (AP=0.705). This makes the next objective more
credible as a ZE-sector compatibility task rather than a recurrence shortcut.

The sector-context split is the clearest actionable result of this gate. The
model is not only detecting whether a sector is dominant, nor only using its raw
share or rank. The combined local sector-position profile -- share, within-ZE
rank, and dominant-sector flag -- is stronger than each isolated component
(AP=0.781 versus 0.693/0.673/0.667). This supports the next HERALD objective:
representing ZE x sector nodes with their position inside the local economic
structure before learning dynamic relations. The remaining warning is that
`sector_rank_only` does not collapse enough under the combined shuffle
(AP=0.604), so future falsification must keep checking whether ranking
artifacts or coarse sector ordering explain part of the signal.

The leave-one-out position check refines this reading. Removing `rank` almost
does not hurt the relation objective (AP=0.779 versus 0.781), while removing
`share` or the dominant-sector flag drops AP to about 0.71. The cleanest
interpretable hypothesis is therefore not "ordinal sector rank" but local
sector weight plus structural dominance: whether the sector has meaningful mass
in the ZE and whether it anchors the local sector profile. This is useful for
the dynamic architecture because it gives a compact, interpretable node
description for ZE x sector learning. It is still a local diagnostic, not a
validated recommendation signal.

The endpoint-control check sharpens the warning. When the source is fixed,
`source_only` correctly collapses to AP=0.500, but `target_only` remains high.
When the target is fixed, `target_only` correctly collapses to AP=0.500, but
`source_only` remains high. Therefore the compact `share + dominant flag`
profile is informative, but the current objective can still be solved largely
from one endpoint profile depending on how negatives are built. This is not yet
a clean proof of non-linear source-target interaction. The next objective must
score compatibility as an added value over source-only and target-only endpoint
baselines, not only report a high pair-classification AP.

The compact endpoint-matched variants reduce the most obvious endpoint shortcut
on the side that is replaced, but they do not solve the problem symmetrically.
Source-preserving endpoint-matched negatives produce a small compatibility
margin over target-only. Target-preserving endpoint-matched negatives still
leave source-only slightly stronger than compatibility-only. This is a useful
direction, not a pass.
```

Endpoint-margin audit:

```text
script: src/modeles/france_ze2020/audit_fr_ze2020_relation_endpoint_controls.py
gate:   compatibility AP must exceed max(source_only AP, target_only AP) by >= 0.02
```

Result on `sector_position_no_rank`, `new_relation`, lag-1 features,
`unseen_pair`, 2021-2025:

| Scenario | Best endpoint AP | Compatibility AP | Compatibility minus endpoint | Gate |
|---|---:|---:|---:|---|
| `pair_distance_hard_negatives` | 0.864 | 0.879 | +0.015 | FAIL |
| `source_preserving_endpoint_matched_negatives` | 0.849 | 0.870 | +0.021 | PASS, small and one-sided |
| `target_preserving_endpoint_matched_negatives` | 0.913 | 0.908 | -0.004 | FAIL |
| `source_distance_target_preserving_negatives` | 0.914 | 0.903 | -0.011 | FAIL |
| `dual_profile_hard_negatives` | 0.883 | 0.779 | -0.105 | FAIL |
| `dual_profile_temporal_sector_shuffle` | 0.523 | 0.567 | +0.044 | PASS, but only on the shuffled placebo |

Reading:

```text
The compatibility-only representation now passes one real source-preserving
endpoint-matched control by a very small margin (+0.021), but it still fails the
target-preserving endpoint-matched control and the stricter dual-profile control.
The pass on the combined-shuffle placebo is not useful evidence for promotion.
Therefore the current local learner should not be deepened into HPC/neural
training as-is. The next technical task is to make endpoint matching symmetric
or add an explicit contrastive compatibility objective where the pair term is
evaluated against source-only and target-only baselines by construction.
```

The strongest warning for the broad any-relation target is the near-tie between
`full_control`, `edge_sign_only`, `temporal_shuffle`, and `sector_shuffle`. For
the narrower `new_relation` target, sector structure starts to matter, but
`temporal_shuffle` and corrected `random_edge_targets` remain too close to
`full_control`.

Decision:

```text
Do not launch HPC from this local learner.
Do not promote it as a graph model.
Use it as a diagnostic showing that the next objective should focus on
emergent relations (`new_relation`) and still needs stronger temporal controls,
held-out-pair validation, and a compatibility-specific objective where the full
pair representation or compatibility-only representation must beat source-only
and target-only endpoint baselines.
```

Tests:

```text
tests/test_fr_ze2020_dynamic_relation_learner.py
tests/test_fr_ze2020_relation_endpoint_controls.py
tests/test_herald_artifact_registry.py
latest targeted run: 40 passed
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
