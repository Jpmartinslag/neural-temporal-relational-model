# HERALD 34 -- France ZE2020 Top-3 Entry HPC Spec

**Status:** `HPC_SPEC_READY_NOT_YET_INTERPRETED`.

This document defines the HPC batch for the `HERALD_33` top-3 entry
falsification triage.

## 1. Objective

Run a deeper falsification batch for:

```text
future_top3_entry_3y_label
```

The purpose is to test whether the small local `HERALD_32` relation lift is
stable across more seeds and falsification scenarios.

This is not a final model, not a validated dynamic graph neural network, not a
causal analysis, and not an automatic recommendation system.

## 2. HPC Package

```text
hpc/france_ze2020_top3_entry/
```

Files:

```text
README.md
run_fr_ze2020_top3_entry_task.sh
run_fr_ze2020_top3_entry_array.sbatch
submit_fr_ze2020_top3_entry_hpc.sh
audit_fr_ze2020_top3_entry_hpc_results.py
```

The submitter is dry-run by default. Real submission requires:

```text
--confirm-submit
```

## 3. Batch Design

```text
4 scenarios x 5 seeds = 20 Slurm tasks
```

Scenarios:

```text
full_control
temporal_shuffle
sector_shuffle
target_shuffle
```

Seeds:

```text
42 43 44 45 46
```

Evaluation years:

```text
2017 2018 2019 2020 2021 2022
```

Feature configs:

```text
no_relation_features
base_formula_features
shuffled_relation_features
```

Default local/HPC model setting:

```text
max_epochs = 120
```

## 4. Output Location

Each task writes to:

```text
hpc_results/fr_ze2020_top3_entry_<RUN_ID>/<scenario>/seed_<seed>/
```

Expected files per task:

```text
fr_ze2020_top3_entry_falsification_predictions_v1.csv
fr_ze2020_top3_entry_falsification_metrics_v1.csv
fr_ze2020_top3_entry_falsification_summary_v1.csv
fr_ze2020_top3_entry_falsification_run_v1.json
```

## 5. Gates

The audit script reports descriptive gates:

| Gate | Meaning |
|---|---|
| G1 | all expected outputs exist and metrics are finite |
| G2 | formula-relation MLP beats no-relation MLP in full control |
| G3 | formula-relation MLP beats shuffled-relation MLP in full control |
| G4 | temporal and sector shuffles degrade formula-relation MLP |
| G5 | outputs contain no recommendation/causal columns |

Passing these gates authorizes interpretation and the next modeling step. It
does not by itself validate a final model.

## 6. Validation Before Commit

Executed locally:

```text
bash -n hpc/france_ze2020_top3_entry/*.sh hpc/france_ze2020_top3_entry/*.sbatch
python3 -m py_compile hpc/france_ze2020_top3_entry/audit_fr_ze2020_top3_entry_hpc_results.py
python3 -m pytest -q tests/test_fr_ze2020_top3_entry_hpc.py \
  tests/test_fr_ze2020_top3_entry_falsifications.py \
  tests/test_herald_artifact_registry.py
```

Result:

```text
22 passed
```

Warnings are limited to expected short-test `MLPClassifier` convergence warnings
with low `max_epochs`.

## 7. Claim Policy

Allowed:

```text
HERALD has a prepared and tested HPC falsification batch for the top-3 entry
objective.
```

Forbidden:

```text
HERALD has validated a dynamic GNN.
HERALD has an automatic recommendation system.
HERALD has proven causal influence.
HPC submission alone is a scientific result.
```
