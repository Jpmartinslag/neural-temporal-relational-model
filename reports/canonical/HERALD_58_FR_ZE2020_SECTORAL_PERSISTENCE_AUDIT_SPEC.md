# HERALD 58 -- France ZE2020 Sectoral Persistence Audit (Part A specification)

**Date:** 2026-07-27
**Status:** `PRE_REGISTERED_SPECIFICATION_NOT_YET_EXECUTED`
**Stage:** E3a of the sequence fixed in HERALD_56 section 5.
**Decision entry:** DEC-083 will record the outcome and reference this frozen specification.

## 0. Scope

This document freezes the protocol **before** any model is fitted and **before** any error
metric is computed. Nothing here is a result.

It specifies one audit: whether sectoral persistence at ZE x sector granularity can be
promoted from **CANDIDATE** to the product's forecasting engine, the designation deliberately
withheld in DEC-081 Q1 for lack of a rolling-origin audit of it.

It does not authorize a neural model, an HPC job, a relational input, or a forecast-derived
state layer. Part B of HERALD_58 (states) may not begin until this part concludes.

## 1. Question

> Under causal rolling-origin evaluation on the canonical ZE2020 x A10 panel, does any
> candidate predictor of next-year sectoral establishment creations beat the naive controls,
> and which one wins?

The audit informs exactly one decision: the Q1 engine designation. It makes no relational,
causal, or recommendation claim.

## 2. Target

`sector_establishment_creations` -- **absolute counts** -- from
`data/processed/france_ze2020/fr_ze2020_sector_panel.csv`, at ZE2020 x A10 x year.

`sector_share` is explicitly **not** the target. Shares sum to one within a ZE-year, so a
closed composition mechanically favours persistence; a win there would be an arithmetic
artifact, not evidence of an engine. This is failure pattern 5 in HERALD_56 section 4, and it
is the pattern that decided DEC-078, DEC-079 and DEC-080.

Counts are also the quantity the product speaks about: a sector growing in a territory.

## 3. Panel, derived features, and completeness

Panel: 280 zones x 9 sectors x 14 years (2012-2025) = 35,280 cells, verified complete in
HERALD_57 part A.

Features are derived per ZE-sector series, from the target only:

```text
lag_1, lag_2, lag_3            y[t-1], y[t-2], y[t-3]
growth_1y_safe                 (y[t-1] - y[t-2]) / y[t-2]
growth_2y_safe                 (y[t-1] - y[t-3]) / y[t-3]
```

This is the feature set and the `RIDGE_ALPHA = 1.0` / `RIDGE_MIN_TRAIN_YEARS = 4` convention
already used by `src/modeles/france_ze2020/train_fr_ze2020_baselines.py` at ZE-total
granularity. Reusing it keeps the sectoral audit comparable in method to the existing
baseline rather than introducing a second convention.

**Completeness requires finite values, tested with `np.isfinite`, not merely `notna`.** The
panel contains one observed zero (`5218 / 2016 / JZ`, HERALD_57 part A), and a zero
denominator makes a growth feature `+/-inf` rather than `NaN`. The precedent is the
`_completeness_mask` note in `train_fr_ze2020_sector_graph_prototype.py`, where exactly this
defect was found before.

Consequence, established as population structure and frozen here: within the official
window, **two cells are incomplete** -- `5218 / JZ / 2018` and `5218 / JZ / 2019`, both
downstream of that zero. They are excluded **identically for every model**, and the exclusion
count must be reported, never silent.

## 4. Evaluation windows

The start of the official window is determined **by the training rules, not by any metric**.
Feature-complete years begin at 2015 (`lag_3` and `growth_2y_safe` require three prior
years). The Ridge rule requires four complete prior training years, which first holds at
**2019**.

| Window | Years | Cells | Role |
|---|---|---|---|
| **Official comparison** | 2019-2025 (7) | 7 x 2,520 - 2 = **17,638** | the only window in which models are ranked against each other |
| **Persistence-only supplement** | 2013-2025 (13) | -- | additional, reported separately |

**Hard rule.** The two windows must never appear in the same ranking table. The supplement is
labelled `NOT_COMPARABLE` in every artifact and every sentence that cites it, because no
fitted model can be evaluated over it. It exists to describe persistence across the full
panel, not to compare anything.

That the official window coincides with `DEFAULT_EVAL_YEARS = [2019...2025]` in the ZE-total
baseline is a consequence of applying the same rule, not a choice.

## 5. Models

| Name | Nature | Rule |
|---|---|---|
| `persistence` | deterministic identity, no fit | `yhat(z,s,t) = y(z,s,t-1)` |
| `ridge_ar` | fitted | Ridge(alpha=1.0) on standardized `lag_1..3`, `growth_1y_safe`, `growth_2y_safe`; trained on training-fold ZEs with `year < t` only |
| `sector_mean` | naive control, estimated on training set | mean of the sector's counts over training-fold ZEs and years `< t` |
| `ze_sector_mean` | naive control, estimated on training set | mean of the cell's own series over years `< t` |
| `national_scaled_persistence` | deterministic baseline | `y(z,s,t-1) x r(s,t)`, where `r(s,t)` is the national growth of sector `s` between `t-2` and `t-1` |

**Estimation discipline, frozen:**

- Both means are computed **exclusively on the training set** -- training-fold ZEs, years
  strictly `< t`. A mean that saw the test fold or the target year is disqualifying.
- The national trend `r(s,t)` uses **only data through `t-1`**: it is the ratio of national
  sector totals at `t-1` and `t-2`. It never reads year `t`.
- `national_scaled_persistence` is a **baseline, not a model**. It exists because HERALD_56
  section 4.8 records that national-trend information was already available as a feature and
  did not suffice; testing it directly as a baseline is cheap and settles whether the
  national signal alone carries the sectoral series.

## 6. Folds, repetition, and the once-only rule

Five ZE-disjoint folds, assigned deterministically by position in the sorted list of the 280
zone codes (`index mod 5`). **No seed is involved anywhere in this audit.**

For each evaluation year, every zone belongs to exactly one test fold; `ridge_ar` and the two
means train on the remaining folds' zones with years `< t`. `persistence` and
`national_scaled_persistence` produce the same value regardless of fold membership, so folds
serve only to give every model an identical paired population.

**Each observation is evaluated exactly once.** The pooled metric covers each ZE-sector-year
in the official window once, and the fold structure must never duplicate a row.

**No seed repetition for any deterministic model, Ridge included.** Ridge on fixed data with
a fixed alpha is deterministic; repeating it under different seeds would inflate apparent
sample size without adding information, exactly as it would for persistence. Any seed axis in
this audit is duplicate evidence and is prohibited.

## 7. Metrics

| Metric | Role |
|---|---|
| **WMAPE**, `sum|y - yhat| / sum|y|` | **primary; the gate reads this and nothing else** |
| MAE | secondary, diagnostic only |
| WMAPE by A10 sector | diagnostic, mandatory |
| WMAPE by evaluation year | diagnostic, mandatory |
| paired win rate per ZE-sector-year | diagnostic, mandatory |

The decompositions are mandatory because the target is extremely skewed: the median cell is
121 creations and the maximum is 73,956, so an aggregate WMAPE is dominated by a handful of
large zones and could hide failure across most of the panel. They are diagnostic: **no
decomposition and no secondary metric may promote a model.** Reading the gate off MAE, or off
a favourable sector, after seeing WMAPE would be metric shopping and is prohibited.

WMAPE is `NaN` where the denominator is zero; such a slice is reported, never silently
dropped.

## 8. Pre-registered gate

Let `A` and `B` be aggregate WMAPE on the official window and yearly WMAPE per evaluation
year.

**Naive-control gate.** A model qualifies only if it beats **both** `sector_mean` and
`ze_sector_mean` on aggregate WMAPE **and** in at least **6 of the 7** evaluation years.

**Promotion.**

1. If a fitted model qualifies **and** beats `persistence` on aggregate WMAPE, in at least
   6/7 years, **and** does not regress against `persistence` by more than **10% relative
   WMAPE in any single A10 sector**, it is designated the engine.
2. Otherwise, if `persistence` qualifies under the naive-control gate, sectoral persistence is
   promoted from CANDIDATE to the product's forecasting engine.
3. If **no** model beats both naive controls under the rule above, the verdict is
   **`NO_ENGINE_DESIGNATED`**: sectoral persistence remains a CANDIDATE, and Part B does not
   proceed until a new specification exists.

The per-sector regression clause exists so a fitted model cannot be promoted on the strength
of the largest sectors while degrading the rest.

No outcome is anticipated here. Any of the three is a valid result of this audit.

## 9. Integrity checks, all blocking

| Check | Requirement |
|---|---|
| Causality | every prediction for year `t` uses only observations at `t-1` or earlier |
| Truncation invariance | re-running with the panel truncated at `t-1` reproduces the predictions for `t` bit for bit |
| Identical populations | all five models predict exactly the same set of cells in every year and fold |
| Coverage | every eligible cell in the official window receives a prediction from every model; the 2 excluded cells are excluded from all five and counted |
| Once-only | the pooled metric row count equals 17,638, with no duplicated ZE-sector-year |
| Fold disjointness | train and test zone sets never intersect for the fitted models |
| Finiteness | every reported metric is finite, or explicitly `NaN` with its cause recorded |
| Determinism | two independent runs produce byte-identical outputs |

A failure of any integrity check invalidates the run; it is not reported as a model result.

## 10. What the outcome authorizes

A promotion designates the Q1 engine and unblocks HERALD_58 Part B, the forecast-derived
states, whose thresholds remain reserved for the project owner (HERALD_56 section 8).

It authorizes nothing else. In particular it does not authorize a relational input, a neural
encoder, an HPC job, a causal statement, or any recommendation claim. Q3 of the contract
remains the only route to another model experiment.

## 11. Pre-registration statement

At the time of writing, **no model has been fitted and no error metric has been computed**
for this audit. The cell counts in sections 3 and 4 are population structure, established
only to fix the evaluation window by rule rather than by outcome, as DEC-081 requires.

## 12. Cross-reference

- Contract, Q1 and the deterministic-baseline protocol: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md` sections 1 and 5.
- Panel completeness and the single observed zero: `reports/canonical/HERALD_57_FR_ZE2020_AVAILABILITY_MASKS.md` section 1.
- A10 source provenance: DEC-076, `HERALD_47`.
- ZE-total baseline conventions: `src/modeles/france_ze2020/train_fr_ze2020_baselines.py`.
- Closed-composition failure pattern: DEC-078, DEC-079, DEC-080.
