# HERALD 33 -- France ZE2020 Top-3 Entry Falsification Triage

**Status:** `LOCAL_FALSIFICATION_TRIAGE_READY_NO_MODEL_PROMOTION`.

This document records the first falsification triage for the `HERALD_32`
target-aligned top-3 entry smoke.

## 1. Question

```text
Does the promising HERALD_32 local signal depend on real temporal structure,
sector structure, and relation columns, or does it survive simple placebos?
```

This is not a final model result, not a dynamic graph neural network validation,
not a causal analysis, and not an automatic recommendation system.

## 2. Script

```text
src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py
```

The script reuses:

```text
src/modeles/france_ze2020/run_fr_ze2020_top3_entry_ranking_smoke.py
```

It does not define a new model. It applies perturbations in memory and writes
only to a required `--output-dir`.

## 3. Falsification Scenarios

| Scenario | Meaning |
|---|---|
| `full_control` | unperturbed HERALD_32 smoke |
| `temporal_shuffle` | temporal lag/growth features shuffled within decision year |
| `sector_shuffle` | sector composition features shuffled within ZE-year |
| `target_shuffle` | future 3-year growth columns shuffled within ZE-year |

The relation placebo remains the `shuffled_relation_features` feature config
from `HERALD_32`.

## 4. Local Triage Run

Command:

```text
python3 src/modeles/france_ze2020/run_fr_ze2020_top3_entry_falsifications.py \
  --output-dir /tmp/herald_top3_entry_falsifications_h3_local \
  --target-horizon 3 \
  --eval-years 2017 2018 2019 2020 2021 2022 \
  --seeds 42 43 \
  --scenarios full_control temporal_shuffle sector_shuffle target_shuffle \
  --feature-configs no_relation_features base_formula_features shuffled_relation_features \
  --max-epochs 40
```

Mean NDCG@3, `mlp_entry_classifier`:

| Scenario | No relation | Formula relation | Shuffled relation | Reading |
|---|---:|---:|---:|---|
| `full_control` | 0.6563 | 0.6602 | 0.6588 | small relation lift |
| `temporal_shuffle` | 0.6074 | 0.6131 | 0.6008 | temporal order matters |
| `sector_shuffle` | 0.5768 | 0.5870 | 0.5800 | sector structure matters strongly |
| `target_shuffle` | 0.6497 | 0.6579 | 0.6542 | weak as a falsification gate |

Mean NDCG@3, `logit_entry_classifier`:

| Scenario | No relation | Formula relation | Shuffled relation | Reading |
|---|---:|---:|---:|---|
| `full_control` | 0.6325 | 0.6324 | 0.6317 | relation does not help linear head |
| `temporal_shuffle` | 0.5793 | 0.5793 | 0.5797 | temporal perturbation hurts |
| `sector_shuffle` | 0.4948 | 0.4954 | 0.4949 | sector perturbation hurts strongly |
| `target_shuffle` | 0.6328 | 0.6326 | 0.6319 | weak as a falsification gate |

## 5. Interpretation

The triage supports three narrow conclusions:

1. The task is not purely noise: shuffling temporal and sector features reduces
   performance.
2. The relation features add a small non-linear signal in the MLP head, but not
   in the logistic head.
3. `target_shuffle` is not a strong enough gate here. The baseline NDCG remains
   high because each ZE-year still contains a similar top-3 density after
   within-group target permutation. It must not be used alone to validate the
   model.

This strengthens the direction of `HERALD_32`, but does not authorize model
promotion or HPC-scale claims yet.

## 6. Decision

Allowed next step:

```text
prepare an HPC falsification batch for the top-3 entry objective, partitioned by
scenario and seed, with more seeds and the same no-relation / formula-relation /
shuffled-relation controls.
```

Required gates before promotion:

```text
G1: no runtime/schema errors
G2: formula relation MLP beats no-relation MLP across most seeds
G3: formula relation MLP beats shuffled-relation MLP across most seeds
G4: temporal_shuffle and sector_shuffle degrade performance
G5: output remains separated from recommendation/causal language
```

Blocked:

```text
claiming validated dynamic GNN;
claiming automatic recommendation;
claiming causality;
using target_shuffle alone as a decisive placebo.
```

## 7. Tests

```text
tests/test_fr_ze2020_top3_entry_falsifications.py
```

The tests check:

- explicit falsification scenarios;
- in-memory temporal, sector, and target shuffles;
- real-panel smoke execution;
- output claim status;
- absence of recommendation columns.
