# HERALD 36 -- France ZE2020 target-aligned relation lift diagnostic

Status: INVALID_FOR_CLAIMS (HERALD_38)

Date: 2026-07-08

Correction 2026-07-13: `year < t` was insufficient for a three-year outcome. Lift
features now use only rows satisfying `year + 3 <= t`. All numerical results below are
historical and require rerun.

## 1. Purpose

HERALD_35 showed that the current top-3 entry objective has real temporal and
sector signal, while the formula relation layer adds only a small MLP gain. The
next question is therefore not whether to claim a final dynamic graph model, but
how to make the relation layer more aligned with the ranking objective.

This pass adds a narrow diagnostic:

`src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_diagnostic.py`

It builds rolling relation-lift features for `future_top3_entry_3y_label`, using
only decision years strictly before the evaluated year.

## 2. What was added

The script creates target-aligned lift features from four relation bins:

| Bin family | Meaning |
|---|---|
| `relation_has_signal_bin` | Whether a ZE-sector row has any prior relation signal |
| `relation_count_bin` | Coarse bucket of prior relation count |
| `relation_strength_bin` | Coarse bucket of prior maximum relation strength |
| `relation_stability_bin` | Coarse bucket of prior mean relation stability |

For each bin family and each decision year `t`, the script estimates from years
`< t`:

```
entry_rate_prior(bin, t) = mean(future_top3_entry_3y_label | bin, year < t)
base_rate_prior(t)       = mean(future_top3_entry_3y_label | year < t)
entry_lift_prior(bin, t) = clip(entry_rate_prior / base_rate_prior, 0.25, 2.0)
```

The output features are diagnostic features only. They are not policy labels and
not recommended sectors.

## 3. Controls

The local diagnostic compares five feature configurations:

| Config | Content |
|---|---|
| `no_relation_features` | Temporal and sector features only |
| `base_formula_features` | Existing full formula features |
| `target_aligned_lift_features` | Non-relation features plus rolling lift features |
| `base_plus_target_aligned_lifts` | Existing formula features plus rolling lift features |
| `shuffled_target_aligned_lifts` | Same as previous, but lift columns shuffled within each decision year |

The shuffled-lift control is important: if the lift features help only because
they add extra columns or extra variance, the shuffled version should perform
similarly. A useful relation lift should remain above this placebo.

## 4. Local run

Command:

```bash
python3 src/modeles/france_ze2020/run_fr_ze2020_top3_entry_lift_diagnostic.py \
  --output-dir /tmp/herald_top3_entry_lift_h3_local \
  --eval-years 2017 2018 2019 2020 2021 2022 \
  --seeds 42 43 44 \
  --feature-configs no_relation_features base_formula_features target_aligned_lift_features base_plus_target_aligned_lifts shuffled_target_aligned_lifts \
  --max-epochs 60
```

Local outputs are regenerable and intentionally not tracked:

- `/tmp/herald_top3_entry_lift_h3_local/fr_ze2020_top3_entry_lift_predictions_v1.csv`
- `/tmp/herald_top3_entry_lift_h3_local/fr_ze2020_top3_entry_lift_metrics_v1.csv`
- `/tmp/herald_top3_entry_lift_h3_local/fr_ze2020_top3_entry_lift_summary_v1.csv`
- `/tmp/herald_top3_entry_lift_h3_local/fr_ze2020_top3_entry_lift_run_v1.json`

## 5. Result

Mean NDCG@3 over decision years 2017-2022 and seeds 42-44:

| Model | Feature config | Mean NDCG@3 |
|---|---:|---:|
| Logit | `no_relation_features` | 0.632497 |
| Logit | `base_formula_features` | 0.632450 |
| Logit | `target_aligned_lift_features` | 0.631267 |
| Logit | `base_plus_target_aligned_lifts` | 0.631116 |
| Logit | `shuffled_target_aligned_lifts` | 0.630978 |
| MLP | `base_plus_target_aligned_lifts` | 0.664397 |
| MLP | `base_formula_features` | 0.661768 |
| MLP | `target_aligned_lift_features` | 0.660144 |
| MLP | `no_relation_features` | 0.653780 |
| MLP | `shuffled_target_aligned_lifts` | 0.650546 |

Interpretation:

- Linear logit does not benefit from the target-aligned lift features.
- The MLP benefits modestly from `base_plus_target_aligned_lifts`.
- The lift signal is above both `no_relation_features` and the shuffled-lift
  placebo in this local run.
- The effect remains small and local. It is a construction clue for the next
  relation layer, not a final model result.

## 6. Claim boundary

Authorized:

- The current formula relation layer is likely too generic.
- A target-aligned rolling relation lift adds a small local MLP signal.
- This supports testing relation features that are explicitly aligned with the
  retrospective ZE-sector ranking objective.

Forbidden:

- Claiming HERALD now has a validated dynamic graph neural model.
- Claiming a causal relation between sectors or territories.
- Treating output rows as sector recommendations.
- Promoting this local diagnostic to an operational result.

## 7. Tests

Executed:

```bash
python3 -m pytest -q \
  tests/test_fr_ze2020_top3_entry_lift_diagnostic.py \
  tests/test_fr_ze2020_top3_entry_target.py \
  tests/test_fr_ze2020_top3_entry_ranking_smoke.py
```

Result: 13 passed.

The tests verify:

- lift columns are explicit and named canonically;
- lift features use only prior decision years;
- mutating a future year does not alter prior-year lift values;
- shuffled lifts preserve within-year distributions;
- outputs keep the expected exploratory claim status.

## 8. Next step

Build the next relation layer around target-aligned relation evidence instead of
generic formula-only relation features. The immediate candidate is an HPC
falsification batch for `base_plus_target_aligned_lifts` versus:

- no relation;
- base formula relation;
- shuffled target-aligned lift;
- temporal shuffle;
- sector shuffle.

This should remain a relation-layer test, not a final model-promotion test.
