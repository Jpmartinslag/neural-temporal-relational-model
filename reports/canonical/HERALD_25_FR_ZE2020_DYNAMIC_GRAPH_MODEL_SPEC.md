# HERALD 25 — France ZE2020 Dynamic Graph Model Spec

**Created:** 2026-07-01.  
**Status:** `DYNAMIC_GRAPH_MODEL_SPEC_READY`.  
**Scope:** construction specification for the next HERALD block: a dynamic
ZE2020 x sector graph model. This document does not validate a new model, does not
authorize claims of neural superiority, does not create an operational recommendation
system, and does not reopen closed graph branches by itself.

---

## 1. Scientific objective

The next HERALD step is not "make a GNN beat Ridge on WMAPE".

The objective is:

> Build a dynamic temporal-relational graph over ZE2020 territories and A10 sectors, then
> learn representations that can produce auditable indicators and retrospective ZE x
> sector rankings for assisted territorial economic recommendation.

Forecasting remains useful, but only as a control or auxiliary task:

```text
forecasting asks: does the representation carry temporal information?
ranking asks: does the representation help order ZE x sector opportunities retrospectively?
signals ask: which relations are stable enough to inspect?
```

This follows the reframed objective in `HERALD_23` and extends the ranking bridge in
`HERALD_24`.

---

## 2. Why this is not a static GNN

The target architecture is dynamic because both the node information and the relations
change with time:

```text
node features:       X_i,t
edge weights:        A_ij,t
representation:      h_i,t
ranking score:       s_i,t
```

Where:

- `i` is a ZE2020 x A10-sector node;
- `t` is the decision year;
- `X_i,t` uses only information available up to `t`;
- `A_ij,t` is a time-specific relation between nodes;
- `h_i,t` is the learned temporal-relational representation;
- `s_i,t` is the score used for retrospective ranking.

This is closer to dynamic graph representation learning than to a static GNN. References
`R-050`, `R-051`, `R-052`, and `R-053` are background anchors for this distinction.

---

## 3. Graph definition

### Nodes

Canonical node grain:

```text
node_id = ze2020 + "_" + sector_code
```

Each node represents:

```text
one ZE2020 territory
one A10 sector
one decision year
```

Expected node count per year:

```text
280 ZE2020 x 9 A10 sectors = 2,520 nodes/year
```

### Time

The graph is a sequence of yearly snapshots:

```text
G_2015, G_2016, ..., G_2024
```

The exact first usable year depends on lag availability. No snapshot may use current or
future target information when building features for ranking year `t`.

### Edge families

The first implementation should keep edge families explicit and typed:

| Edge type | Form | Meaning | First status |
|---|---|---|---|
| `intra_ze_sector` | `(ze, sector_a, t) -> (ze, sector_b, t)` | sector interaction inside the same ZE | candidate |
| `cross_ze_same_sector` | `(ze_a, sector, t) -> (ze_b, sector, t)` | same sector moving similarly across ZEs | candidate |
| `ze_similarity` | `(ze_a, any_sector, t) -> (ze_b, any_sector, t)` or aggregated feature | trajectory similarity between ZEs | candidate |
| `sector_relatedness` | `(sector_a) -> (sector_b)` lifted to ZE nodes | sector-to-sector relatedness | blocked until ZE-grain provenance |
| `geography_or_mobility` | `(ze_a) -> (ze_b)` lifted to sector nodes | spatial or commuting relation | blocked until provenance/gate |

Do not mix these edge types into one unlabelled adjacency matrix. A relation built from
sector similarity is not the same object as a relation built from geography or commuting.

---

## 4. Canonical inputs

Allowed inputs for the first build:

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
```

Optional, only if already audited in the same task:

```text
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
```

Forbidden inputs:

```text
dynamic_stgnn_feature_panel*
graph_adjacency_core_v0.csv
graph_adjacency_mobility_v0.csv
train_herald_v6/v7/semi_v2/regime outputs as current evidence
any artifact whose generator/provenance is unknown
```

---

## 5. Proposed outputs

The next construction block should create these files, in this order:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_splits.csv
```

Later training may create:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_embeddings_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_ranking_predictions_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_ranking_metrics_v1.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_relation_signals_v1.csv
```

HPC outputs should stay under:

```text
hpc_results/fr_ze2020_dynamic_graph_<RUN_ID>/
```

Do not overwrite shared input panels inside array jobs.

---

## 6. Node schema

Minimum node table:

| Column | Type | Rule |
|---|---|---|
| `node_id` | string | `ze2020_sector_code`, unique inside year |
| `ze2020` | string | 4-character zero-padded |
| `ze2020_label` | string | display only |
| `sector_code` | string | A10 code |
| `sector_label` | string | display only |
| `decision_year` | int | year `t` |
| `current_sector_count` | float | count at `t` |
| `sector_share_lag_1` | float | lagged or decision-year-safe value |
| `sector_growth_lag_1` | float | lagged only |
| `sector_growth_lag_2` | float | lagged only |
| `dominant_sector_lag_1` | string/bool | safe lagged descriptor |
| `sector_diversity_lag_1` | float | safe lagged descriptor |
| `sector_concentration_hhi_lag_1` | float | safe lagged descriptor |
| `national_sector_growth_lag_1` | float | safe lagged descriptor |
| `mask_*` | int | 1 observed/usable, 0 missing/unusable |
| `future_growth_1y` | float | label only, never feature |
| `future_growth_3y` | float | label only, never feature |

Labels must be physically excluded from the feature matrix before training.

---

## 7. Edge schema

Minimum edge table:

| Column | Type | Rule |
|---|---|---|
| `edge_id` | string | deterministic hash or formatted source-target-year-type |
| `source_node_id` | string | must exist in node table for same year |
| `target_node_id` | string | must exist in node table for same year |
| `decision_year` | int | edge snapshot year |
| `edge_type` | string | one of the explicit families in section 3 |
| `edge_weight` | float | finite numeric value |
| `signal_strength` | float | optional, if derived from signal layer |
| `stability_score` | float | optional, recurrence measure |
| `source_basis` | string | input artifact/method |
| `claim_status` | string | exploratory/non-causal |

Rules:

- no self-loop unless the edge type explicitly requires it;
- no future year may be used to build edge weights for decision year `t`;
- edge weights must be finite;
- edge families must remain separable for ablation.

---

## 8. First model family

The first neural model should be intentionally small and inspectable.

Recommended name:

```text
HERALD-DG-Rank prototype
```

Where `DG` means dynamic graph, not validated final model.

Minimal encoder:

```text
message_i,t = aggregate_j(edge_weight_ji,t * transform(X_j,t))
h_i,t       = temporal_encoder(X_i,t, message_i,t, h_i,t-1)
score_i,t   = ranking_head(h_i,t)
```

Allowed implementation options:

| Option | Why acceptable now |
|---|---|
| manual message passing + MLP/GRU | simplest, auditable, no heavy dependency |
| GraphMLP with typed aggregated messages | keeps edge-family ablation easy |
| temporal GRU over node embeddings | tests dynamic memory without overclaiming STGNN |

Defer full library-heavy ST-GNN until the data contract and falsification gates pass.

---

## 9. Training tasks

Primary task:

```text
retrospective ZE x sector ranking
```

For each ZE2020 and decision year `t`, rank A10 sectors by predicted future growth:

```text
future_growth_1y or future_growth_3y
```

Auxiliary tasks, optional after primary task works:

| Task | Purpose |
|---|---|
| next-year count forecast | sanity check for temporal information |
| masked node-feature reconstruction | test whether representation learns structure |
| edge-weight reconstruction | test whether graph signals are coherent |
| sector-presence/rank auxiliary loss | connect representation to recommendation objective |

No auxiliary task may introduce future leakage.

---

## 10. Evaluation and falsification gates

Promotion gates:

| Gate | Requirement |
|---|---|
| G1 data safety | no forbidden input, no label column in features, no non-finite feature |
| G2 time safety | truncation/mutation tests show no future leakage |
| G3 ranking value | model beats simple baselines on NDCG@K or HitRate@K under repeated seeds |
| G4 relation value | real graph beats no-relation and random-relation controls |
| G5 temporal value | full model beats temporal-shuffle control |
| G6 sector value | full model beats sector-shuffle and no-sector controls |
| G7 stability | top relation/ranking signals recur across seeds/windows |
| G8 claim hygiene | no causal, automatic recommendation, or policy-prescription language |

Required controls:

```text
random ranking
past volume
past growth
specialization
national growth
ridge ranking
mlp without graph
no relation
random relation
temporal shuffle
sector shuffle
no sector composition
```

Future controls:

```text
geography-only graph
spatial dynamic panel
LightGBM/XGBoost or equivalent tabular non-linear baseline
```

These future controls require separate dependency/provenance decisions.

---

## 11. What would justify calling it a new model

HERALD can later be presented as a new model family only if all of the following are true:

1. the graph is explicitly dynamic, with yearly node and/or edge states;
2. the architecture learns node representations `h_i,t`, not only hand-built features;
3. the ranking head is evaluated retrospectively against future observed outcomes;
4. ablations show that time, sector structure, and graph relations add information;
5. the result is reproducible across seeds and windows;
6. the method stays non-causal and human-in-the-loop for recommendation.

If these conditions are not met, the correct wording remains:

```text
temporal-relational architecture / prototype / representation candidate
```

not:

```text
validated new dynamic graph model
```

---

## 12. Immediate implementation sequence

Next technical lots:

1. **Builder spec/test:** create `build_fr_ze2020_dynamic_graph_inputs.py`.
2. **Node table:** generate and test `fr_ze2020_dynamic_graph_nodes.csv`.
3. **Edge table:** generate and test `fr_ze2020_dynamic_graph_edges.csv`.
4. **Leakage audit:** truncation and label-mutation tests.
5. **Smoke encoder:** manual typed-message-passing model, local only.
6. **Falsification wrapper:** no-relation, random-relation, temporal-shuffle,
   sector-shuffle, no-sector.
7. **HPC spec:** only after local smoke and auditors pass.

Do not combine all seven in one commit unless the repository state is clean and the test
surface remains small enough to audit.

---

## 12b. First construction lot implemented

Implemented 2026-07-01:

```text
src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py
```

Outputs:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv
data/processed/france_ze2020/fr_ze2020_dynamic_graph_splits.csv
```

Observed output sizes:

| File | Rows | Meaning |
|---|---:|---|
| `fr_ze2020_dynamic_graph_nodes.csv` | 35,280 | 280 ZE2020 x 9 A10 sectors x 14 decision years |
| `fr_ze2020_dynamic_graph_edges.csv` | 52,087 | typed exploratory edges from already-audited relation signals |
| `fr_ze2020_dynamic_graph_splits.csv` | 14 | one split row per decision year |

Implemented edge types:

```text
cross_ze_same_sector
intra_ze_sector
ze_similarity
```

Deliberate non-implementation:

```text
ze_sector_specialization
```

Reason: specialization is a node/territory-sector attribute candidate, not an edge. The
builder does not fabricate self-loops or pseudo-edges from this family.

Validation:

```text
tests/test_fr_ze2020_dynamic_graph_inputs.py
```

The tests check schema, determinism, forbidden legacy inputs, node/edge consistency,
finite weights, label/feature separation, and claim hygiene.

---

## 12c. First smoke encoder implemented

Implemented 2026-07-01:

```text
src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py
```

This is the first `HERALD-DG-Rank prototype` smoke implementation. It is deliberately
small:

```text
nodes + typed edges
        |
        v
manual typed message passing
        |
        v
Ridge / MLP ranking heads
        |
        v
retrospective ZE x sector ranking metrics
```

Message formula:

```text
message_i,t,type,f =
    sum_j(edge_weight_j,i,t,type * feature_j,t,f)
    / sum_j(abs(edge_weight_j,i,t,type))
```

Non-finite message values are set to `0.0` after aggregation. This prevents unusable
neighbor histories from entering the model as `NaN`/`Inf`; the original node-level
availability remains represented by masks and `feature_complete`.

The smoke encoder does not make the project a validated dynamic graph model. It only
establishes that the HERALD_25 graph input can be consumed by a typed temporal-relational
ranker without reintroducing forbidden legacy inputs.

Validation:

```text
tests/test_fr_ze2020_dynamic_graph_ranker.py
```

The tests check typed-message construction, label/feature separation, finite model
features on usable rows, 1-year and 3-year target support, and claim hygiene.

---

## 13. References

Primary project references:

- `HERALD_23_TEMPORAL_RELATIONAL_RECOMMENDATION_OBJECTIVE.md`
- `HERALD_24_FR_ZE2020_SECTOR_RANKING_TRAINING_SPEC.md`
- `HERALD_REFERENCES_MASTER.md`

Literature anchors:

- `R-008` EconoGNN
- `R-050` dynamic GNN survey
- `R-051` dynamic GNN survey
- `R-052` dynamic graph representation learning survey
- `R-053` spatio-temporal GNN review
- `R-054` economic network forecasting
- `R-055` optimizing economic complexity
- `R-056` metropolitan economic complexity
- `R-057` spatial dynamic panel baseline
