# HERALD 32 -- France ZE2020 Top-3 Entry Ranking Smoke

**Status:** `LOCAL_SMOKE_PROMISING_NO_MODEL_PROMOTION`.

This document records the first target-aligned ranking smoke after `HERALD_31`.
Unlike `HERALD_30`, this smoke does not ask whether descriptive relation
embeddings help generic future top-3 ranking. It asks whether formula relation
features help rank sectors that **enter** the future top-3 growth set.

## 1. Question

```text
Do existing formula relation features help rank future top-3 entry sectors
inside each ZE2020, compared with a no-relation control and a shuffled-relation
placebo?
```

This is still a local diagnostic. It is not a final model, not a validated
dynamic graph neural network, not a causal analysis, and not an automatic
recommendation system.

## 2. Script

```text
src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py
```

Input:

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
```

Output, only under a required `--output-dir`:

```text
fr_ze2020_top3_entry_ranking_predictions_v1.csv
fr_ze2020_top3_entry_ranking_metrics_v1.csv
fr_ze2020_top3_entry_ranking_summary_v1.csv
fr_ze2020_top3_entry_ranking_run_v1.json
```

## 3. Configurations

| Feature config | Meaning |
|---|---|
| `no_relation_features` | temporal and sector features only |
| `base_formula_features` | temporal, sector, and existing formula relation features |
| `shuffled_relation_features` | same columns as base, but relation columns shuffled inside each decision year |

Models:

```text
logit_entry_classifier
mlp_entry_classifier
```

Target:

```text
future_top3_entry_3y_label
```

Evaluation:

```text
decision years: 2017..2022
seeds:          42, 43, 44
metric:         NDCG@3 / Precision@3 / HitRate@3
```

The 3-year target stops at 2022 because later decision years do not yet have
complete 3-year future observations.

## 4. Local Smoke Result

Command:

```text
python3 src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py \
  --output-dir /tmp/herald_top3_entry_ranking_smoke_h3 \
  --target-horizon 3 \
  --eval-years 2017 2018 2019 2020 2021 2022 \
  --seeds 42 43 44 \
  --feature-configs no_relation_features base_formula_features shuffled_relation_features \
  --max-epochs 80
```

Mean NDCG@3:

| Feature config | Logistic entry | MLP entry |
|---|---:|---:|
| no relation features | 0.6325 | 0.6533 |
| base formula features | 0.6324 | 0.6645 |
| shuffled relation features | 0.6319 | 0.6577 |

Reading:

- the logistic classifier is essentially unchanged by relation features;
- the MLP classifier gains about `+0.0112` NDCG@3 over the no-relation control;
- the MLP classifier also stays above the shuffled-relation placebo by about
  `+0.0068` NDCG@3;
- this is the first local result where relation features help under a target
  aligned with future top-3 entry.

## 5. Interpretation

This does not overturn `HERALD_30`. The previous diagnostic showed that current
descriptive relation embeddings are weak for generic ranking. `HERALD_32`
instead shows that the **target definition matters**: relation features become
more useful when the task asks for future entry into the top-3 set.

The result is promising but not sufficient for promotion:

- only 3 seeds;
- local run only;
- MLP emitted convergence warnings at `max_epochs=80`;
- formula relation features are tested, not a new dynamic graph architecture;
- the margin over the shuffled-relation placebo is positive but modest.

## 6. Decision

Allowed next step:

```text
prepare a deeper target-aligned dynamic relation model for future_top3_entry_3y_label
and evaluate it against no-relation, shuffled-relation, temporal-shuffle, and
sector-shuffle controls.
```

Blocked:

```text
promoting this smoke as a validated model;
claiming a dynamic GNN;
using the output as automatic recommendation;
claiming causality.
```

## 7. Tests

```text
tests/test_fr_ze2020_top3_entry_ranking_smoke.py
```

The tests check:

- explicit feature configurations;
- relation-column removal for `no_relation_features`;
- relation-column shuffling without changing non-relation columns;
- real-panel smoke execution;
- output claim status and absence of recommendation columns.
