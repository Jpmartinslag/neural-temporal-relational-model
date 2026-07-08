# HERALD 35 -- France ZE2020 Top-3 Entry HPC Audit

**Status:** `HPC_AUDIT_READY_PROMISING_NO_MODEL_PROMOTION`.

This document records the audited HPC result for the `HERALD_34` top-3 entry
falsification batch.

## 1. Run

```text
Slurm job: 7734742
Run ID:    fr_ze2020_top3_entry_20260708_174219
Tasks:     20/20 completed
Exit code: 0:0 for all tasks
Runtime:   about 8-9 minutes per task
```

Local audit report copied to:

```text
hpc_results/fr_ze2020_top3_entry_20260708_174219/fr_ze2020_top3_entry_hpc_audit_report.json
```

The bulky per-task HPC outputs remain under `hpc_results/` and are not promoted
as canonical tracked data.

## 2. Gates

The descriptive G1-G5 audit passed:

| Gate | Result | Meaning |
|---|---|---|
| G1 | PASS | all expected outputs exist and metrics are finite |
| G2 | PASS | formula-relation MLP beats no-relation MLP in full control |
| G3 | PASS | formula-relation MLP beats shuffled-relation MLP in full control |
| G4 | PASS | temporal and sector shuffles degrade formula-relation MLP |
| G5 | PASS | output separation: no recommendation/causal columns |

This authorizes interpretation of the batch. It does not validate a final
dynamic graph model.

## 3. Main Result

Mean NDCG@3, `mlp_entry_classifier`, 5 seeds:

| Scenario | No relation | Formula relation | Shuffled relation | Reading |
|---|---:|---:|---:|---|
| `full_control` | 0.656976 | 0.658672 | 0.654628 | relation signal is small but positive |
| `temporal_shuffle` | 0.609328 | 0.613661 | 0.610464 | temporal structure matters |
| `sector_shuffle` | 0.575802 | 0.578077 | 0.577609 | sector structure matters strongly |
| `target_shuffle` | 0.653531 | 0.651878 | 0.650234 | weak gate, not decisive |

Mean Precision@3, `mlp_entry_classifier`, 5 seeds:

| Scenario | No relation | Formula relation | Shuffled relation |
|---|---:|---:|---:|
| `full_control` | 0.517817 | 0.519206 | 0.515873 |
| `temporal_shuffle` | 0.478849 | 0.482500 | 0.478651 |
| `sector_shuffle` | 0.406508 | 0.408810 | 0.409048 |
| `target_shuffle` | 0.515119 | 0.512381 | 0.514563 |

## 4. Interpretation

The batch proves that the `future_top3_entry_3y_label` task contains real
structure:

- temporal perturbation reduces performance;
- sector perturbation reduces performance even more;
- formula relation features improve the non-linear MLP head in full control;
- shuffled relation features are weaker than formula relation features.

The strongest signal is not the relation layer alone. The strongest finding is
that **time and sector composition are structurally important** for the ZE2020 x
sector top-3 entry task.

The relation gain is real but small:

```text
formula relation MLP - no relation MLP = +0.001696 NDCG@3
formula relation MLP - shuffled relation MLP = +0.004044 NDCG@3
```

This supports continuing with a better target-aligned relation model, but it
does not justify claiming that a graph/neural architecture is already validated.

## 5. Important Limitation

`target_shuffle` remains a weak gate. It stays close to full control because the
within-ZE-year target density is preserved. Therefore:

```text
target_shuffle must not be used alone as the decisive placebo.
```

The stronger falsifications in this batch are:

```text
temporal_shuffle
sector_shuffle
shuffled_relation_features
```

## 6. Claim Policy

Allowed:

```text
The top-3 entry ranking task is structurally meaningful: temporal and sector
shuffles degrade performance, and relation features add a small non-linear signal
over no-relation and shuffled-relation controls.
```

Forbidden:

```text
HERALD has validated a dynamic GNN.
HERALD has a final recommendation system.
HERALD has proven causal influence between ZEs or sectors.
The relation layer is already strong enough for operational recommendation.
```

## 7. Next Step

The next model step should not simply rerun the same formula relation features.
It should improve the relation layer itself:

```text
learn relation features directly for future_top3_entry_3y_label
```

and then retest against:

```text
no_relation_features
shuffled_relation_features
temporal_shuffle
sector_shuffle
```
