# HERALD 26 — France ZE2020 Edge Learning Plan

**Created:** 2026-07-02.  
**Status:** `EDGE_LEARNING_PLAN_READY`.  
**Scope:** methodological plan for improving the dynamic graph edge layer after the
first HERALD_25 HPC run. This document does not validate a new neural model, does not
create a recommendation system, and does not authorize a causal claim.

---

## 1. Why this plan exists

The first HERALD_25 dynamic graph run showed a useful but incomplete result.

The temporal and sector information are informative for retrospective ZE x sector
ranking, but the current edge layer is not yet strong enough.

HPC run:

```text
ranker:        hpc_results/fr_ze2020_dynamic_graph_ranker_20260702_091544/
falsification: hpc_results/fr_ze2020_dynamic_graph_falsifications_20260702_091540/
edge file:     fr_ze2020_dynamic_graph_edges_expanding.csv.gz
target:        future_growth_1y ranking
seeds:         42..46
eval years:    2017..2024
```

Mean NDCG@K:

| Model | Mean NDCG@K | Reading |
|---|---:|---|
| `ridge_dynamic_graph` | 0.5169 | best current candidate |
| `mlp_dynamic_graph` | 0.4822 | neural head below Ridge |
| `national_growth` | 0.3861 | simple national-sector signal |
| `random` | 0.3342 | random control |
| `past_volume` | 0.2626 | simple level heuristic |
| `specialization` | 0.2626 | simple specialization heuristic |
| `past_growth` | 0.2329 | simple growth heuristic |

Falsification deltas versus `full_control`:

| Scenario | Ridge delta | MLP delta | Reading |
|---|---:|---:|---|
| `temporal_shuffle` | -0.0552 | -0.0549 | time order matters strongly |
| `sector_shuffle` | -0.0093 | -0.0088 | sector structure matters moderately |
| `random_edge_weights` | -0.0029 | -0.0033 | edge weights are weakly used |
| `no_edges` | +0.0081 | -0.0023 | current edges do not help Ridge |
| `no_ze_similarity` | +0.0065 | +0.0080 | ZE-similarity edges may add noise |

Conclusion:

```text
time signal:      supported
sector signal:    weak-to-moderate
current edges:    not supported as useful graph structure
neural advantage: not supported
```

Therefore, the next scientific problem is not heavier training. The next problem is
edge construction, edge selection, and edge learning.

---

## 2. Core hypothesis

HERALD should treat candidate edges as noisy economic relation hypotheses, not as
ground-truth structure.

The working hypothesis is:

> A dynamic ZE2020 x sector graph becomes useful only after the edge layer distinguishes
> persistent, decaying, volatile, complementary, and learned relations instead of passing
> every correlation-like signal directly to message passing.

This is consistent with:

- `R-058` / `R-059`: noisy graph edges can harm GNN message passing and may need denoising
  or learned graph structure.
- `R-060`: dynamic graph edges should carry temporal states, not only static weights.
- `R-061`: spatio-temporal graphs can often be strongly sparsified; more edges are not
  necessarily better.
- `R-062`: recent temporal edges can be noisy; augmentation/denoising can reduce the
  influence of unreliable edges.
- `R-055`: relatedness alone is not a recommendation objective; a ranking target and
  retrospective validation remain required.

---

## 3. Edge families to test next

The next builder should create candidate edge views without overwriting the current
HERALD_25 files.

Recommended names:

```text
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_topk.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_topk.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_feature_compatible.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_feature_compatible_topk.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_stateful.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_stateful_topk.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_sector_only.csv.gz
data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_sector_topk.csv.gz
```

### 3.1 Pruned stable graph

Purpose: test whether fewer, more recurrent edges beat the expanded edge-memory graph.

Candidate filters:

```text
top_k_per_node in {3, 5, 10}
stability_score >= {0.25, 0.40, 0.60}
abs(signal_strength) >= {0.30, 0.50, 0.70}
edge_age <= {1, 3, 5, all}
```

Minimum gate:

```text
pruned graph must beat no_edges on NDCG@K in >= 3/5 seeds
```

### 3.2 Stateful graph

Purpose: encode temporal behavior of the relation.

Proposed `edge_state`:

| State | Simple rule |
|---|---|
| `new_relation` | first year this source-target-type appears |
| `persistent_relation` | observed in at least 2 recent windows |
| `decaying_relation` | not observed recently but still in memory |
| `reappearing_relation` | appears again after a gap |
| `volatile_relation` | high signal but low recurrence |

Candidate weight:

```text
edge_weight = signal_strength * state_multiplier * stability_score / (1 + edge_age)
```

Where `state_multiplier` is pre-registered, for example:

```text
persistent_relation: 1.00
reappearing_relation: 0.75
new_relation: 0.50
decaying_relation: 0.35
volatile_relation: 0.15
```

The exact multipliers must be tested as specification variants, not tuned after seeing
the test result.

### 3.3 Learned edge weights

Purpose: let the model down-weight candidate relations.

Minimal frugal version:

```text
learned_edge_weight = sigmoid(
    b0
  + b1 * signal_strength
  + b2 * stability_score
  + b3 * edge_age
  + b4 * same_sector_flag
  + b5 * edge_type_embedding
)
```

Then message passing uses:

```text
message_weight = edge_weight * learned_edge_weight
```

This is not yet a full neural STGNN. It is an auditable bridge between fixed edges and
learned dynamic graph structure.

---

## 4. What not to do

Do not:

- increase MLP depth/epochs before improving edges;
- cite `mlp_dynamic_graph` as better than Ridge;
- cite current edges as useful just because the full model beats random;
- convert `signal_strength` into causality;
- call any output a policy recommendation;
- overwrite `fr_ze2020_dynamic_graph_edges.csv` or
  `fr_ze2020_dynamic_graph_edges_expanding.csv.gz`;
- reuse `graph_adjacency_core_v0.csv` or `graph_adjacency_mobility_v0.csv` without a new
  provenance decision.

---

## 5. Evaluation protocol

Every edge variant must be compared against:

```text
no_edges
random_edge_weights
random_edge_targets
temporal_shuffle
sector_shuffle
no_cross_ze_same_sector
no_intra_ze_sector
no_ze_similarity
```

A variant is only promising if:

```text
G1: no missing/Inf outputs
G2: better than no_edges in >= 3/5 seeds
G3: better than random_edge_weights and random_edge_targets
G4: temporal_shuffle still hurts
G5: relation signals remain exploratory and non-causal
```

Optional stronger gates:

```text
bootstrap edge stability
leave-one-region-group-out
leave-one-year-out
top-k relation recurrence across seeds
```

---

## 6. Implementation lots

### Lot A — audit-only edge diagnostics

Create a small audit script:

```text
src/modeles/france_ze2020/audit_fr_ze2020_dynamic_edge_variants.py
```

It should report:

```text
edge count by type/year
node degree by type/year
weight distribution
stability distribution
edge age distribution
share of volatile edges
share of edges that survive pruning thresholds
```

No model training.

**Implemented 2026-07-02.** The script reports type/year counts, target-node degree
statistics, edge age, stability and volatile-edge shares. It writes optional audit CSV/JSON
outputs only when `--output-dir` is supplied.

### Lot B — pruned stable edge builder

Create:

```text
src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py
```

First output:

```text
fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
```

This first pruned output has no learned weights. Rolling learned-edge gates were
added later in Lot B4 as separate files; this pruned-stable file remains unchanged.

**Implemented 2026-07-02.**

```text
script: src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py
output: data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
rows:   31,551
size:   589,818 bytes
sha256: 8cf728720b5feb56590326e09ac11ba0ae5fbfb58a83f90920d7a7f34121b5f9
```

Pruning rule:

```text
top_k_per_node = 5
stability_score >= 0.25
abs(signal_strength) >= 0.30
edge_age <= 5
```

Retained share versus the expanding edge-memory table:

```text
31,551 / 258,460 = 0.1221
```

This is a candidate edge variant only. It has not passed ranker/falsification gates.

### Lot B2 — stateful edge builder

Implemented in the same builder:

```text
script: src/data/france_ze2020/build_fr_ze2020_dynamic_edge_variants.py
output: data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful.csv.gz
rows:   258,460
size:   3,633,728 bytes
sha256: 329ec5ddee5b4cd2a3aa96fba084b4fafff6b866c9b6ce73cf6959b6d4bd9f0d
```

This variant does not cut edges. It reweights the expanding edge-memory table with a
pre-registered state multiplier:

```text
persistent_relation: 1.00
reappearing_relation: 0.75
new_relation: 0.50
decaying_relation: 0.35
volatile_relation: 0.15
```

Actual states present in v1:

| Edge state | Rows |
|---|---:|
| `volatile_relation` | 220,336 |
| `decaying_relation` | 22,028 |
| `new_relation` | 16,096 |

Weight formula:

```text
edge_weight = signal_strength * stability_score * state_multiplier / (1 + edge_age)
```

The aim is to keep exploratory relation visibility while penalizing noisy or old
relations. It remains an edge candidate, not a validated graph structure.

### Lot B3 — batch edge hypothesis bundle

Implemented 2026-07-02 in the same builder. The bundle is intentionally redundant:
the goal is to falsify edge-construction hypotheses in parallel instead of spending
manual time on one variant at a time.

| Variant | File | Rows | Size bytes | Purpose |
|---|---|---:|---:|---|
| `pruned_stable` | `fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz` | 31,551 | 589,818 | strong stable-edge pruning |
| `stateful` | `fr_ze2020_dynamic_graph_edges_stateful.csv.gz` | 258,460 | 3,633,728 | temporal state reweighting |
| `stateful_sector_only` | `fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz` | 637 | 23,278 | remove noisy ZE-similarity family |
| `stateful_topk` | `fr_ze2020_dynamic_graph_edges_stateful_topk.csv.gz` | 107,275 | 1,708,851 | cap incoming degree after stateful weighting |
| `stateful_sector_topk` | `fr_ze2020_dynamic_graph_edges_stateful_sector_topk.csv.gz` | 637 | 29,405 | sector-only plus top-k cap |
| `feature_compatible` | `fr_ze2020_dynamic_graph_edges_feature_compatible.csv.gz` | 258,460 | 14,254,732 | gate stateful edges by known source-target feature compatibility |
| `feature_compatible_topk` | `fr_ze2020_dynamic_graph_edges_feature_compatible_topk.csv.gz` | 107,275 | 7,320,223 | feature-compatible plus top-k cap |
| `learned_stateful` | `fr_ze2020_dynamic_graph_edges_learned_stateful.csv.gz` | 258,460 | 19,613,759 | rolling learned gate over all stateful edges |
| `learned_stateful_topk` | `fr_ze2020_dynamic_graph_edges_learned_stateful_topk.csv.gz` | 107,275 | 9,613,982 | learned-stateful plus top-k cap |
| `learned_sector_only` | `fr_ze2020_dynamic_graph_edges_learned_sector_only.csv.gz` | 637 | 64,058 | rolling learned gate over sector-only edges |
| `learned_sector_topk` | `fr_ze2020_dynamic_graph_edges_learned_sector_topk.csv.gz` | 637 | 72,160 | learned-sector plus top-k cap |

The feature-compatible variants use only known node features at the decision year:

```text
sector_growth_lag_1
sector_share_t
national_sector_growth_lag_1
```

They do not use the future label of the decision year. They are adaptive edge-feature
variants, not learned neural edge gates.

### Lot B4 — rolling learned-edge gates

Implemented 2026-07-02 after the first 40-task HPC falsification showed that
`stateful_sector_only` was the least weak edge family but still fragile against random
edge weights.

For decision year `t`, the learned gate trains only on edge rows from years `< t`.
The label is whether the target ZE-sector node was in the top-3 future one-year growth
sectors inside its ZE-year in a prior year. This makes the gate retrospective and
rolling-origin; it is not allowed to see the target label for year `t`.

Gate features:

```text
abs_signal_strength
stability_score
edge_age
state_multiplier
recent_observation_count
total_observation_count
source/target sector_growth_lag_1
source/target sector_share_t
source/target national_sector_growth_lag_1
absolute source-target differences
edge_type dummies
```

The learned gate is a small balanced logistic regression:

```text
learned_edge_gate = P(target_top3_growth_1y | prior-year edge features)
edge_weight = stateful_edge_weight * learned_edge_gate
```

Neutral fallback:

```text
learned_edge_gate = 0.5
```

is used when no prior training history or only one label class exists.

### Lot C — local ranker/falsification smoke

Use existing ranker and falsification scripts with:

```text
--edges fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
```

**Executed locally 2026-07-02.**

Smoke 1:

```text
seed:       42
eval year:  2024
epochs:     15 for ranker, 10 for falsification
```

The run completed, but `no_edges` remained better than `full_control`.

Smoke 2:

```text
seed:       42
eval years: 2017..2024
epochs:     10
scenarios:  full_control, no_edges, random_edge_weights, temporal_shuffle, sector_shuffle
```

Mean NDCG@K:

| Scenario | Ridge dynamic graph | MLP dynamic graph | Reading |
|---|---:|---:|---|
| `full_control` | 0.5078 | 0.4786 | pruned-stable graph candidate |
| `no_edges` | 0.5250 | 0.5029 | better than graph candidate |
| `random_edge_weights` | 0.5067 | 0.4823 | near full control |
| `sector_shuffle` | 0.4866 | 0.4468 | sector signal still matters |
| `temporal_shuffle` | 0.4456 | 0.4166 | time order still matters |

Decision:

```text
Do not launch HPC for pruned_stable v1.
```

Reason:

```text
The local all-year smoke fails G2: full_control does not beat no_edges.
The result confirms that simple pruning alone is not enough.
```

This is not a failure of the pipeline. It is a falsification result: the next work should
move to stateful or learned edge weights rather than spending HPC budget on this exact
pruned-stable specification.

Stateful smoke:

```text
seed:       42
eval years: 2017..2024
epochs:     10
scenarios:  full_control, no_edges, random_edge_weights, temporal_shuffle, sector_shuffle
```

Mean NDCG@K:

| Scenario | Ridge dynamic graph | MLP dynamic graph | Reading |
|---|---:|---:|---|
| `full_control` | 0.5179 | 0.4498 | stateful graph candidate |
| `no_edges` | 0.5250 | 0.5029 | still better than graph candidate |
| `random_edge_weights` | 0.5146 | 0.4573 | close to full control |
| `sector_shuffle` | 0.5064 | 0.4451 | sector signal still matters |
| `temporal_shuffle` | 0.4616 | 0.3910 | time order still matters |

Decision:

```text
Do not launch HPC for stateful v1.
```

Reason:

```text
Stateful v1 improves Ridge versus pruned_stable v1, but still fails G2:
full_control does not beat no_edges.
```

Feature-compatible-top-k integration smoke:

```text
seed:       42
eval year:  2024
epochs:     5
scenarios:  full_control, no_edges, random_edge_weights, temporal_shuffle, sector_shuffle
```

The run completed without schema/runtime errors. It is not interpreted as a model result
because it is one year and one seed only.

The next edge work is now a batch falsification run: all variants should be tested under
the same seeds/scenarios before deciding whether learned edge weights are justified.

### Lot D — HPC edge-variant falsification batch

Created:

```text
hpc/france_ze2020_dynamic_graph/run_fr_ze2020_edge_variant_falsification_task.sh
hpc/france_ze2020_dynamic_graph/run_fr_ze2020_edge_variant_falsification_array.sbatch
hpc/france_ze2020_dynamic_graph/submit_fr_ze2020_edge_variant_falsifications_hpc.sh
```

Design:

```text
12 edge inputs x 5 seeds = 60 Slurm array tasks
seeds = 42, 43, 44, 45, 46
target_horizon = 1
eval_years = 2017..2024
scenarios = full_control, no_edges, random_edge_weights, random_edge_targets,
            no_cross_ze_same_sector, no_intra_ze_sector, no_ze_similarity,
            temporal_shuffle, sector_shuffle
```

The batch is falsification-only. Passing one metric does not automatically promote an
edge variant; results must still be audited after collection.

### Lot E — learned edge gate

Superseded by Lot B4 on 2026-07-02. The learned gate was implemented before the
next HPC batch because the first 40-task edge-variant run found no robust edge
win and identified sector-only/stateful variants as the least weak candidates.

The implemented files are:

```text
fr_ze2020_dynamic_graph_edges_learned_stateful.csv.gz
fr_ze2020_dynamic_graph_edges_learned_stateful_topk.csv.gz
fr_ze2020_dynamic_graph_edges_learned_sector_only.csv.gz
fr_ze2020_dynamic_graph_edges_learned_sector_topk.csv.gz
```

They must be evaluated against the same `no_edges` and random-edge placebos
before any claim about edge usefulness.

---

## 7. Claim policy

Allowed if the next edge variant passes gates:

```text
The pruned/stateful/learned edge variant carries retrospective ranking signal under
placebo tests.
```

Forbidden:

```text
The graph discovers causal influence.
The neural model is superior.
HERALD recommends policy actions.
The edge layer is validated because it looks interpretable.
```

The strongest near-term scientific claim remains:

> HERALD separates temporal signal, sector structure, and graph structure through
> auditable falsification tests, showing that graph edges must be learned or pruned rather
> than assumed from raw association.

---

## 8. Next executable step

Start with Lot A and Lot B:

1. audit current edge distributions;
2. create pruned stable variants;
3. run local ranker/falsification smoke;
4. launch HPC only if local smoke is clean.

Do not move to heavier neural architecture until at least one edge variant beats
`no_edges` under the pre-registered gates. The fixed/adaptive edge bundle must be audited
first. If every variant still fails `no_edges`, the next move is learned edge weights or a
different relation objective, not deeper MLP/STGNN training.
