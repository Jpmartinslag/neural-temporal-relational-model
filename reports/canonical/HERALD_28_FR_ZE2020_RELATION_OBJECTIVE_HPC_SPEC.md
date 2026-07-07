# HERALD 28 -- France ZE2020 Relation Objective HPC Spec

**Status:** `HPC_FALSIFICATION_PASS_NOT_A_MODEL_CLAIM`.

This document specifies the HPC falsification batch for the HERALD_27 relation
objective. It does not validate a dynamic GNN, does not authorize causal claims,
and does not create automatic recommendations.

Run `fr_ze2020_relation_objective_20260707_185547` completed on meso as Slurm
job `7733592` with 5/5 seed tasks finished and empty stderr logs.

## 1. Question

The local HERALD_27 gate found that a compact source-target compatibility learner
can beat simple anchor/peripheral formulas on a strict dual-endpoint task.

The HPC question is narrower:

```text
Does the learned compatibility signal remain stronger than deterministic formulas
across seeds and falsification controls, while degrading under temporal/sector
placebos?
```

## 2. Inputs

Canonical/audited inputs only:

| Input | Role |
|---|---|
| `data/processed/france_ze2020/fr_ze2020_dynamic_graph_nodes.csv` | ZE2020 x sector node-year features |
| `data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz` | typed candidate relation edges |
| `src/modeles/france_ze2020/audit_fr_ze2020_relation_lift_over_formulas.py` | local lift-over-formulas evaluator |
| `src/modeles/france_ze2020/train_fr_ze2020_dynamic_relation_learner.py` | local logistic compatibility learner |

Forbidden inputs remain forbidden:

```text
dynamic_stgnn_feature_panel*
graph_adjacency_core_v0.csv
graph_adjacency_mobility_v0.csv
train_herald_v6/v7/semi_v2/regime as current path
```

## 3. Batch

Default HPC batch:

```text
seeds: 42, 43, 44, 45, 46
target: new_relation
node_feature_lag: 1
eval_years: 2017-2025
feature_family: sector_position_no_rank
pair_feature_mode: compatibility_only
```

Scenarios:

| Scenario | Purpose |
|---|---|
| `dual_endpoint_matched_negatives` | main strict local gate |
| `dual_endpoint_temporal_sector_shuffle` | matched temporal+sector placebo |
| `dual_profile_hard_negatives` | harder source+target profile control |
| `dual_profile_temporal_shuffle` | time-order placebo |
| `pair_distance_hard_negatives` | pair-distance control |
| `source_preserving_endpoint_matched_negatives` | source-preserving shortcut check |
| `target_preserving_endpoint_matched_negatives` | target-preserving shortcut check |
| `source_distance_target_preserving_negatives` | target fixed, source profile control |

## 4. Gates

The audit script reports five descriptive gates:

| Gate | Criterion | Meaning |
|---|---|---|
| G1 | all expected seeds present, finite metrics, no forbidden columns | run integrity |
| G2 | real dual-endpoint lift over best formula >= 0.05 in every seed | learner adds information beyond formulas |
| G3 | real AP - matched shuffle AP >= 0.20 in every seed | signal weakens under placebo |
| G4 | coefficient of variation of real lift <= 0.20 | seed stability |
| G5 | no recommendation/causal output language | output separation |

Passing these gates means:

```text
relation objective is worth promoting to the next prototype design stage
```

It does not mean:

```text
dynamic GNN validated
recommendation validated
causal mechanism discovered
```

## 5. Result

HPC audit status:

```text
RELATION_OBJECTIVE_HPC_AUDIT_PASS
```

| Gate | Result | Main number |
|---|---|---:|
| G1 no errors | PASS | 5/5 seeds found |
| G2 real lift over formula | PASS | mean lift +0.1217 AP |
| G3 shuffle degradation | PASS | mean AP drop 0.3042 |
| G4 lift stability | PASS | CV 0.0 |
| G5 output separation | PASS | no forbidden claim status |

Main relation objective:

| Scenario | Learner AP | Best formula AP | Lift |
|---|---:|---:|---:|
| `dual_endpoint_matched_negatives` | 0.9545 | 0.8328 | +0.1217 |
| `dual_endpoint_temporal_sector_shuffle` | 0.6503 | 0.5973 | +0.0530 |

Reading:

```text
The learned compatibility signal remains stronger than deterministic formulas
across five seeds and drops clearly under matched temporal+sector shuffle. This
authorizes the next prototype design stage: a dynamic relation encoder that
exports learned source-target relation scores and node-level relation embeddings.
It still does not validate a dynamic GNN, causal mechanism, or recommendation
model.
```

## 6. Files

HPC package:

```text
hpc/france_ze2020_relation_objective/README.md
hpc/france_ze2020_relation_objective/run_fr_ze2020_relation_objective_task.sh
hpc/france_ze2020_relation_objective/run_fr_ze2020_relation_objective_array.sbatch
hpc/france_ze2020_relation_objective/submit_fr_ze2020_relation_objective_hpc.sh
hpc/france_ze2020_relation_objective/audit_fr_ze2020_relation_objective_hpc_results.py
```

Expected result directory:

```text
hpc_results/fr_ze2020_relation_objective_<RUN_ID>/seed_<SEED>/
```

Expected per-seed output:

```text
fr_ze2020_relation_lift_over_formulas_metrics_v1.csv
fr_ze2020_relation_lift_over_formulas_run_v1.json
```

## 7. Launch

Dry run:

```bash
bash hpc/france_ze2020_relation_objective/submit_fr_ze2020_relation_objective_hpc.sh
```

Real submission:

```bash
bash hpc/france_ze2020_relation_objective/submit_fr_ze2020_relation_objective_hpc.sh --confirm-submit
```

Audit after collection:

```bash
python3 hpc/france_ze2020_relation_objective/audit_fr_ze2020_relation_objective_hpc_results.py \
  hpc_results/fr_ze2020_relation_objective_<RUN_ID> \
  --out reports/metrics/fr_ze2020_relation_objective_<RUN_ID>_gate_report.json
```
