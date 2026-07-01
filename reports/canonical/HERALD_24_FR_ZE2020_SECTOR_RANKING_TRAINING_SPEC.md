# HERALD 24 — France ZE2020 Sector Ranking Training Spec

**Created:** 2026-07-01.  
**Status:** `FALSIFICATION_HPC_PREPARED`.  
**Scope:** first training/evaluation block for the reframed HERALD objective in
`HERALD_23`: temporal-relational indicators and retrospective ZE×sector ranking.

This document does not create an operational recommendation system. It defines an
exploratory ranking task that can be trained and falsified.

---

## 1. Objective

The immediate objective is:

> Build and evaluate a retrospective ZE×sector ranking task: using information available
> up to decision year `T`, rank A10 sectors for each ZE2020, then evaluate whether the
> ranked sectors show stronger realized growth in `T+1..2025` than simple baselines and
> placebos.

This is the first trainable bridge between:

```text
apprentissage temporel-relationnel
        -> indicators
        -> exploratory territorial economic recommendation
```

Forecasting remains a control. The main output of this block is ranking quality and
indicator behavior, not WMAPE superiority.

---

## 2. Data contract

### Input files

Read-only inputs:

```text
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
```

Forbidden inputs:

```text
dynamic_stgnn_feature_panel*
graph_adjacency_core_v0.csv
graph_adjacency_mobility_v0.csv
train_herald_v6/v7/semi_v2/regime outputs as current evidence
```

### Output panel

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
```

Grain:

```text
ZE2020 × sector A10 × decision_year
```

The `decision_year` means: information through year `T` may be used to rank sectors.
The builder uses lagged rows from `fr_ze2020_sector_relational_features.csv` at
`year=T+1`, because those columns represent values observed at `T` and earlier.

---

## 3. Ranking labels

Medium-horizon label:

```text
future_growth_3y = (sector_count[T+3] - sector_count[T]) / sector_count[T]
```

Annual label:

```text
future_growth_1y = (sector_count[T+1] - sector_count[T]) / sector_count[T]
```

Rows with zero or missing current count are not used for growth-label evaluation. They
remain auditable through masks, but not as valid ranking labels.

The `3y` target is the conservative medium-term target. Because the panel ends in
2025, it can only be evaluated through decision year 2022.

The `1y` target is the wider-window target. It can be evaluated through decision year
2024 and is used to test whether the architecture remains coherent when almost the
whole observed time span is exploited.

Ranking task:

```text
For each (ZE2020, decision_year), rank 9 A10 sectors by predicted future_growth_1y
or future_growth_3y.
```

---

## 4. Models and baselines

First local block:

| Family | Model | Role |
|---|---|---|
| baseline | random | placebo lower bound |
| baseline | past_volume | rank by current sector count |
| baseline | past_growth | rank by historical sector growth |
| baseline | specialization | rank by current sector share |
| baseline | national_growth | rank by national sector growth |
| statistical | ridge_ranking | linear control |
| neural temporal-relational | mlp_temporal_relational | first small neural encoder over temporal + sector + relation indicators |

Use "neural temporal-relational". This block is not a static graph run. It is the first
ranking-oriented neural model over temporal-relational indicators.

---

## 5. Metrics

Per evaluation year and model:

```text
Precision@K
HitRate@K
NDCG@K
average future growth of predicted top-K
average future growth of actual top-K
```

Default `K=3`, because there are 9 A10 sectors per ZE.

---

## 6. First HPC launch target

The first HPC launch ran:

```text
src/modeles/france_ze2020/train_fr_ze2020_sector_ranking.py
```

Seeds:

```text
42 43 44 45 46
```

Evaluation years:

```text
2018 2019 2020 2021 2022
```

Why 2022 is the last default evaluation year: the primary label is 3-year future growth,
and the current panel ends in 2025.

The next wider-window launch should use:

```text
--target-horizon 1
```

Default 1-year evaluation years:

```text
2015 2016 2017 2018 2019 2020 2021 2022 2023 2024
```

Outputs per seed:

```text
fr_ze2020_sector_ranking_predictions_v1.csv
fr_ze2020_sector_ranking_metrics_v1.csv
```

HPC result interpretation:

- If MLP beats simple baselines, it supports the temporal-relational representation
  direction for ranking.
- If MLP does not beat them, the indicators may still be useful descriptively, but the
  neural ranking claim is not promoted.
- No result is causal.
- No result is an automatic recommendation.

---

## 7. Falsification block

After the first smoke/HPC run, explicit ablations/placebos are prepared in:

```text
src/modeles/france_ze2020/run_fr_ze2020_sector_ranking_falsifications.py
hpc/france_ze2020_ranking/run_fr_ze2020_sector_ranking_falsification_array.sbatch
```

Implemented scenarios:

| Scenario | What is falsified | Interpretation |
|---|---|---|
| full_control | no perturbation | reference ranking run |
| no_relational | relation columns set to zero | tests whether relation indicators add signal |
| random_relational | relation columns shuffled within year | tests whether relation structure matters beyond marginal distribution |
| no_sector_composition | sector-composition columns set to zero | tests whether sector structure adds signal |
| sector_shuffle | sector-composition columns shuffled inside each ZE-year | tests whether correct sector assignment matters |
| temporal_shuffle | lag/growth columns shuffled only inside each decision year | tests whether temporal indicators matter without moving future information into past years |

Not implemented yet:

- geography-only baseline, because a documented canonical geographic graph has not been
  accepted for this ranking task.

The Slurm falsification block reads the ranking panel as input only and writes outputs to
`hpc_results/fr_ze2020_sector_ranking_falsifications_<RUN_ID>/`. It must not rebuild or
overwrite the shared input panel inside array tasks.

---

## 8. Literature anchors for the next dynamic-graph block

This ranking block is not yet the final neural/dynamic graph model. The next block should
use the following references as methodological anchors, all registered in
`reports/bibliography/HERALD_REFERENCES_MASTER.md`:

| Reference | HERALD use | Boundary |
|---|---|---|
| `R-008` EconoGNN | Economic precedent for temporal graph learning | Country-scale resilience classification, not ZE2020 ranking |
| `R-050` / `R-051` / `R-052` dynamic graph surveys | Dynamic graph framing: evolving features, relations, and representations | Background only; does not validate HERALD |
| `R-053` ST-GNN review | Baseline, reproducibility, explainability and scalability cautions | Prevents overclaiming neural/grafo results |
| `R-001` Product Space | Sector relatedness and productive-structure logic | Country/product origin; needs ZE2020 adaptation |
| `R-055` Optimizing Economic Complexity | Recommendation/ranking needs an explicit objective, not only a relatedness map | Future recommendation gate, not current operational recommendation |
| `R-056` metropolitan economic complexity | Subnational complexity framing | US metropolitan employment data, not French ZE2020 creations |
| `R-054` trade networks and forecasting | Network descriptors can be tested against linear/non-linear forecasting baselines | International trade setting, not direct ZE2020 proof |
| `R-057` spatial dynamic panel | Future econometric baseline for spatial-temporal dependence | Requires feasibility check for annual ZE2020 panel |

The immediate methodological consequence is:

```text
do not promote "new EconoGNN-like model" yet
        |
        v
first define and test a dynamic ZE2020 x sector graph encoder
        |
        v
compare against temporal, sector, relation, random-graph, temporal-shuffle,
sector-shuffle and spatial/econometric baselines
```

The current sector-ranking training block remains a bridge: it tests whether the existing
temporal, sector, and relation indicators support retrospective ranking. It is not the
final dynamic graph neural architecture.
