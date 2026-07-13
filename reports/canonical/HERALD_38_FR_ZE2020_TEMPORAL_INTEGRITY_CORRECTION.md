# HERALD 38 -- France ZE2020 temporal integrity correction

**Date:** 2026-07-13
**Status:** `TEMPORAL_INTEGRITY_CORRECTED`

## 1. Scope

This correction freezes the numerical claims from HERALD_32--37 and repairs the active
France ZE2020 x A10 ranking and dynamic-relation chain. It does not promote a model and
does not authorize a new HPC run.

## 2. Defects confirmed

1. Three-year ranking folds trained on every `decision_year < eval_year`. Labels from the
   two most recent training years depended on outcomes after the evaluation year.
2. Target-aligned lift features used the same not-yet-mature labels.
3. The exploratory relation export aggregated the complete 2017--2025 window into
   `year_end` and `stability_score`, then the graph treated those values as historical.
4. The ranking panel consumed only 64 intra-ZE sector interactions and excluded the main
   ZE-to-ZE relation families.
5. The ranking builder, trainer, tests and panel were present locally but absent from git.
6. HPC gates compared aggregate means; the lift beat its shuffled control in only 14/30
   paired seed-year comparisons despite the aggregate gate passing.

## 3. Corrected contracts

### Mature labels

For horizon `h`, a row may train an evaluation at year `T` only when:

```text
decision_year + h <= T
```

For `h=3`, the first default evaluation with three complete training years is 2019.

### Temporal relations

New canonical model input:

```text
data/processed/france_ze2020/fr_ze2020_temporal_relation_signals.csv.gz
```

Builder:

```text
src/data/france_ze2020/build_fr_ze2020_temporal_relation_signals.py
```

The file contains 226,980 unique relation-year snapshots for 2017--2025:

| Family | Rows |
|---|---:|
| `ze_similarity` | 113,400 |
| `cross_ze_same_sector` | 113,400 |
| `intra_ze_sector` | 180 |

Every strength uses lagged history available at the decision year. Recurrence and
stability denominators are cumulative only through that year. The retrospective
`fr_ze2020_exploratory_relation_signals.csv` remains interpretation-only.

### Corrected graph input

The regenerated bundle contains:

- 35,280 node-year rows;
- 226,980 instant annual edges;
- 661,613 leakage-safe edge-memory rows;
- 14 split rows.

For each relation and year, memory uses the latest snapshot at or before that year. A
future snapshot cannot alter an earlier graph.

### Corrected ranking input

The ranking panel remains 35,280 rows and 41 columns. Relation coverage is now complete
for all 2,520 ZE-sector nodes from 2017 onward. Relation features aggregate the latest
known incident ZE-similarity, cross-ZE same-sector and intra-ZE sector edges.

## 4. Gate correction

The HPC auditor now requires paired seed-year evidence with a minimum 60% win rate and a
positive mean NDCG delta. Target shuffle is an explicit gate. Aggregate mean superiority
alone is insufficient.

## 5. Claim consequences

- HERALD_32--36 numerical results: `INVALID_FOR_CLAIMS` until rerun.
- HERALD_34 and HERALD_37 HPC specifications: superseded.
- Dynamic graph/ranking outputs from the previous relation bundle: superseded by the
  regenerated inputs, but all model metrics still require rerun.
- No neural superiority, causal relation or recommendation claim is authorized.

## 6. Validation and required next step

The focused ranking/lift/temporal-snapshot suite and the dynamic-graph integration suite
pass locally after regeneration. This validates the corrected data and code contracts; it
does not recreate or validate any numerical model result.

Run the corrected falsifications next. A new full HPC specification may be created only
if outputs are finite, temporally invariant under truncation, and the paired gates are
pre-registered. Do not reinterpret jobs 7734742 or 7754322.

## 7. Corrected remote smoke

The owner requested that compute-heavy smoke execution use `meso` instead of the local
workstation. Slurm job `7755797` (`smoke_temporal_fix_20260713_143010`) completed on
2026-07-13 with exit `0:0` in 65 seconds.

The isolated smoke used seed 42, evaluation years 2019 and 2022, and 12 MLP epochs. The
remote audit confirmed finite outputs, 30,240 prediction rows, no recommendation/causal
output columns, and horizon-aware training histories of 3 years for evaluation 2019 and
6 years for evaluation 2022. The expected convergence warnings from the deliberately
short MLP run do not invalidate the execution check.

This smoke validates runtime, schema, and temporal-cut integration only. Its ranking
metrics are not scientific evidence and do not authorize model promotion or automatic
recommendation.

## 8. Full corrected falsification audit

Jobs `7755806` (top-3) and `7755807` (relation-lift) completed 40/40 tasks with exit
`0:0`. The corrected horizon-aware results do not support relation-layer promotion:
formula relation features do not beat the no-relation MLP, and target-aligned lift does
not beat no-relation, base-formula, or shuffled-lift controls under paired seed-year
gates. Temporal shuffle also fails to degrade the candidates.

The audit exposed one additional control bug: `target_shuffle` permuted
`future_growth_3y` but left the precomputed `future_top3_growth_3y_label` attached to its
original sector. The classifier therefore retained its effective label. The correction
now permutes the complete future-target bundle together (future value, count/share,
rank, top-3 label, and availability mask). Only the ten target-shuffle tasks are invalid
and require rerun; the full-control, temporal-shuffle, and sector-shuffle tasks remain
valid negative evidence.

### Corrected target-shuffle rerun

Jobs `7755853` (top-3) and `7755854` (relation-lift) reran only array tasks `15-19`,
covering seeds 42--46 for the corrected `target_shuffle`. All 10 tasks completed with
exit `0:0`; logs contain no fatal error and all required prediction, metric, summary,
and run-metadata files are present. The corrected outputs were combined for audit with
the 30 unaffected tasks from jobs `7755806` and `7755807`.

The target control now behaves as intended. For the top-3 base-formula MLP, mean NDCG
falls from `0.608817` under full control to `0.419905` after target shuffle; full control
wins all 20 paired seed-year comparisons (mean delta `+0.188912`). For the relation-lift
MLP, mean NDCG falls from `0.594127` to `0.333430`; full control wins 19/20 paired
comparisons (mean delta `+0.260697`). The lift auditor's target-shuffle gate therefore
passes.

This establishes that the evaluated task contains learnable target-aligned signal and
that the corrected target placebo destroys much of it. It does not establish that the
current relation features add useful information: lift still fails against no-relation,
base-formula, and shuffled-lift controls, while temporal shuffle still does not degrade
performance. The relation layer remains exploratory and is not promoted.
