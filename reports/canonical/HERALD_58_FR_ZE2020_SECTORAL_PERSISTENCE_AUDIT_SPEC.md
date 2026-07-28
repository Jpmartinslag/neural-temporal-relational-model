# HERALD 58 -- France ZE2020 Sectoral Persistence Audit (Part A specification)

**Date:** 2026-07-28
**Status:** `PRE_REGISTERED_SPECIFICATION_NOT_YET_EXECUTED`
**Stage:** E3a of the sequence fixed in HERALD_56 section 5.
**Decision entries:** **DEC-083** registers this specification *before* execution, as
HERALD_56 section 5 requires of any stage carrying a methodological decision. **DEC-084**
will record the outcome and reference this frozen text. The temporal proof of
pre-registration is the commit that introduces DEC-083 and this file, not the date written
here.

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

`sector_share` is explicitly **not** the target. Shares sum to one within a ZE-year. Closed
composition is a **plausible structural limitation consistent with DEC-078, DEC-079 and
DEC-080, not a demonstrated mechanism** -- the wording fixed by the DEC-081 correction
addendum, and repeated here so this specification cannot reintroduce a stronger claim than
the contract allows. Because no test has isolated compositional closure as a cause, a
persistence win on shares would be uninterpretable rather than informative, which is reason
enough to exclude it as a target.

**What the target measures, stated precisely.** `sector_establishment_creations` is the
count of **establishments created in a sector, a zone and a year**: an annual flow of new
establishments. It is **not** growth of the establishment stock, not employment, not
output, and not firm survival. A rise in this series means more establishments were created
that year, nothing more. Every sentence produced by this audit and by anything downstream of
it must respect that reading.

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

Consequence, established as population structure and frozen here. Two cells are incomplete
from 2015 onward, both downstream of that zero: `5218 / JZ / 2018` and `5218 / JZ / 2019`.
Of these, **only `5218 / JZ / 2019` falls inside the official evaluation window**; 2018 is
before it.

- `5218 / JZ / 2019` is **excluded from evaluation, identically for every model**.
- `5218 / JZ / 2018` is never evaluated because 2018 is not an evaluation year, but it is
  still **dropped from `ridge_ar` training rows** for every later evaluation year, under the
  same `isfinite` rule.

The exclusion count must be reported, never silent.

*Corrected before execution.* An earlier draft of this section stated two exclusions inside
the official window and a population of 17,638. That conflated "incomplete from 2015 onward"
with "incomplete inside 2019-2025". See the DEC-083 second correction addendum.

## 4. Evaluation windows

The start of the official window is determined **by the training rules, not by any metric**.
Feature-complete years begin at 2015 (`lag_3` and `growth_2y_safe` require three prior
years). The Ridge rule requires four complete prior training years, which first holds at
**2019**.

| Window | Years | Cells | Role |
|---|---|---|---|
| **Official comparison** | 2019-2025 (7) | 7 x 2,520 - 1 = **17,639** | the only window in which models are ranked against each other |
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
| `ridge_ar` | fitted | see section 5.1 |
| `sector_mean` | cross-sectional control, estimated on training ZEs | mean of the sector's counts over **training-fold ZEs** and years `< t` |
| `ze_sector_mean` | own-history control, causal | mean of the **test cell's own** series over years `< t` |
| `national_scaled_persistence` | deterministic baseline | `y(z,s,t-1) x r(s,t)`, see section 5.2 |

**Estimation discipline, frozen. The two controls are causally different objects and must
not share one rule:**

- `sector_mean` is **cross-sectional**: it borrows information from other zones, so it is
  computed exclusively on **training-fold ZEs** with years strictly `< t`. Reading the test
  fold would be leakage across zones.
- `ze_sector_mean` is **own-history**: by definition it is the mean of the test cell's own
  past. Restricting it to training ZEs would make it uncomputable for the cells it is meant
  to score. It therefore uses the **test cell's own series, years strictly `< t`**, exactly
  the causal window `persistence` uses -- persistence takes the last value of that window,
  `ze_sector_mean` takes its mean. Neither ever reads year `t`.
- **Neither control, and no model, may read the target at year `t`.** That is the single
  invariant both rules serve; "training set only" was too coarse a phrasing for it and is
  replaced by the two rules above.

### 5.1 `ridge_ar`, fully specified

```text
sklearn.pipeline.Pipeline([
    ("scaler", sklearn.preprocessing.StandardScaler()),
    ("ridge",  sklearn.linear_model.Ridge(alpha=1.0)),
])
```

- Features: `lag_1`, `lag_2`, `lag_3`, `growth_1y_safe`, `growth_2y_safe`, in that order.
- `StandardScaler` is fitted **on the training rows only** and applied unchanged to the test
  rows. Fitting it on the pooled data would leak test distribution into training.
- `Ridge(alpha=1.0)`, `fit_intercept=True` (the scikit-learn default, stated rather than
  assumed), `solver` left at its default `auto`, no `positive` constraint, no sample weights.
- Training rows are those of the training-fold ZEs with `year < t` **that are feature- and
  target-complete under the `isfinite` rule of section 3**. Non-finite rows are removed from
  training and are already outside the comparable population.
- **No imputation.** A cell with a non-finite feature is excluded identically for every
  model, never filled.
- **No clipping and no rounding** of Ridge predictions. This repeats the convention of the
  existing ZE-total baseline; introducing a floor at zero here would be a silent
  post-registration modelling choice.
- Because counts are non-negative but unconstrained regression is not, the **number and
  share of negative Ridge predictions must be reported** in the run manifest, per year and
  overall. This is a diagnostic disclosure, not a gate.
- The **scikit-learn version** is recorded in the run manifest, so a future rerun that
  produces different numbers can be attributed to the library rather than to the data.

### 5.2 `national_scaled_persistence`, and its fail-closed division

```text
r(s,t) = national_total(s, t-1) / national_total(s, t-2)
yhat(z,s,t) = y(z,s,t-1) x r(s,t)
```

`national_total(s, y)` sums the sector's counts over **all 280 zones** at year `y`. It uses
**only data through `t-1`** and never reads year `t`.

**The division must fail closed.** Before use, `national_total(s, t-2)` is required to be
**finite and strictly positive**, and `r(s,t)` is required to be finite. A zero, negative,
missing or non-finite denominator **aborts the audit with an explicit error**. It must never
produce an infinity, never be imputed, never be silently dropped, and never cause a cell to
disappear from one model's population but not another's.

`national_scaled_persistence` is a **baseline, never a candidate engine** (section 8). It
exists because HERALD_56 section 4.8 records that national-trend information was already
available as a feature and did not suffice; testing it directly settles whether the national
signal alone carries the sectoral series, which is cheap and worth knowing.

## 6. Folds, repetition, and the once-only rule

Five ZE-disjoint folds, assigned deterministically by position in the sorted list of the 280
zone codes (`index mod 5`). **No seed is involved anywhere in this audit.**

For each evaluation year, every zone belongs to exactly one test fold. Which models consult
the folds follows from section 5 and not from a separate rule:

> `ridge_ar` and `sector_mean` use the remaining training-fold ZEs. `ze_sector_mean`,
> `persistence` and `national_scaled_persistence` use the test cell's causal history through
> `t-1` and do not fit on folds.

The three fold-independent objects produce the same value regardless of fold membership, so
for them the folds serve only to give every model an identical paired population.

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

### 8.1 Eligibility

| Object | Role | Can be designated engine? |
|---|---|---|
| `persistence` | candidate | **yes** |
| `ridge_ar` | candidate | **yes** |
| `sector_mean` | control | **never** |
| `ze_sector_mean` | control | **never** |
| `national_scaled_persistence` | baseline | **never** |

`national_scaled_persistence` is excluded from designation by registration, not by outcome.
It is a diagnostic about the national signal; promoting a product engine that multiplies
every territory by one national ratio per sector would assert a uniformity this audit does
not test. If it were to outperform both candidates, that is a **finding to report and a
reason to write a new specification**, not a promotion under this one.

### 8.2 Definition of "beats"

**"Beats" means strictly lower WMAPE.** Equality is not a win, at the aggregate level and in
every yearly comparison. Ties count against the challenger.

### 8.3 Naive-control gate

A candidate qualifies only if it beats **both** `sector_mean` and `ze_sector_mean` on
aggregate WMAPE **and** in at least **6 of the 7** evaluation years.

### 8.4 Promotion

1. If `ridge_ar` qualifies under 8.3, beats `persistence` on aggregate WMAPE and in at least
   6/7 years, **and** passes the per-sector safety veto of 8.5, it is designated the engine.
2. Otherwise, if `persistence` qualifies under 8.3, sectoral persistence is promoted from
   CANDIDATE to the product's forecasting engine.
3. **If neither clause 1 nor clause 2 designates an engine, the verdict is
   `NO_ENGINE_DESIGNATED`**: sectoral persistence remains a CANDIDATE and Part B does not
   proceed until a new specification exists.

Clause 3 is written as the exhaustive complement of clauses 1 and 2, not as a separate
condition, so every combination of outcomes lands in exactly one verdict. An earlier
phrasing made clause 3 conditional on neither candidate beating the controls, which left
several reachable states with no verdict at all -- for instance `ridge_ar` beating both
controls but not `persistence`, or beating `persistence` but failing the per-sector veto, or
`persistence` failing the controls while `ridge_ar` passes them without beating it.

### 8.5 Per-sector safety veto

For each A10 sector `s`, with `W_c(s)` the candidate's sectoral WMAPE and `W_p(s)`
persistence's:

```text
relative_regression(s) = (W_c(s) - W_p(s)) / W_p(s)
veto if   relative_regression(s) > 0.10   for any s
```

Degenerate reference: if `W_p(s) = 0` the ratio is undefined, and the veto fires when
`W_c(s) > 0`; if both are `0` there is no regression. If `W_p(s)` is `NaN` because the
sectoral denominator is zero, the audit aborts rather than proceeding with an
uninterpretable veto.

**This clause is a safety veto, never a promotional metric.** It can only *block* a
promotion that clause 8.4 already granted on aggregate WMAPE; it can never create one, and a
favourable sector can never lift a candidate that failed 8.3 or 8.4. That is what keeps it
consistent with section 7: decompositions do not promote. It exists so a fitted model cannot
be promoted on the strength of the largest sectors while degrading the rest -- which the
skew described in section 7 makes a live risk, not a hypothetical one.

No outcome is anticipated here. All three verdicts in 8.4 are valid results of this audit.

## 9. Integrity checks, all blocking

| Check | Requirement |
|---|---|
| Causality | every prediction for year `t` uses only observations at `t-1` or earlier |
| Truncation invariance | re-running with the panel truncated at `t-1` reproduces the predictions for `t` bit for bit |
| Identical populations | all five models predict exactly the same set of cells in every year and fold |
| Coverage | every eligible cell in the official window receives a prediction from every model; the single excluded cell (`5218 / JZ / 2019`) is excluded from all five and counted |
| Once-only | the pooled metric row count equals 17,639, with no duplicated ZE-sector-year |
| Fold disjointness | train and test zone sets never intersect for the fitted models |
| Finiteness | every reported metric is finite, or explicitly `NaN` with its cause recorded |
| National denominator | `national_total(s, t-2)` finite and strictly positive, and `r(s,t)` finite, for every sector and evaluation year -- otherwise abort (section 5.2) |
| Scaler discipline | `StandardScaler` fitted on training rows only, never on pooled data |
| No imputation | no cell excluded by the `isfinite` rule is filled for any model |
| Determinism | two independent runs produce byte-identical outputs |
| Environment | scikit-learn and pandas versions recorded in the run manifest |

A failure of any integrity check invalidates the run; it is not reported as a model result.

Reported alongside, as disclosure rather than gate: the count and share of negative
`ridge_ar` predictions, per year and overall.

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

---

# Part A -- Result

**Written after execution. Sections 0-12 above are the pre-registered text and were not
edited to fit this outcome.** Decision entry: **DEC-084**.

**Verdict: `ENGINE_DESIGNATED`. Engine: `persistence`, by clause 8.4.2.**

## 13. Official comparison, 2019-2025, 17,639 cells

| Model | WMAPE | MAE | Role |
|---|---:|---:|---|
| `ridge_ar` | **0.106180** | 46.143 | candidate |
| `persistence` | **0.116458** | 50.610 | candidate, **designated** |
| `national_scaled_persistence` | 0.134060 | 58.260 | baseline, never eligible |
| `ze_sector_mean` | 0.314233 | 136.559 | control |
| `sector_mean` | 0.828618 | 360.100 | control |

## 14. Why the better aggregate did not win

This is the outcome the pre-registration was built for, and it must not be reported as
"persistence is more accurate than Ridge".

`ridge_ar` has the **lower aggregate WMAPE**. It nevertheless fails clause 8.4.1 on **two
independent grounds**:

**Year stability.** It beats `persistence` in only **4 of 7** years, against the registered
minimum of 6.

| Year | `persistence` | `ridge_ar` | winner |
|---|---:|---:|---|
| 2019 | 0.140862 | 0.096219 | ridge |
| 2020 | 0.101007 | 0.133846 | persistence |
| 2021 | 0.156650 | 0.104730 | ridge |
| 2022 | 0.154629 | 0.170793 | persistence |
| 2023 | 0.085187 | 0.110976 | persistence |
| 2024 | 0.097503 | 0.062839 | ridge |
| 2025 | 0.086831 | 0.073870 | ridge |

**Per-sector safety veto.** It regresses against `persistence` by more than the registered
10% in two A10 sectors.

| Sector | `persistence` | `ridge_ar` | relative regression |
|---|---:|---:|---:|
| BE | 0.147321 | 0.129126 | -12.35% |
| **FZ** | 0.099042 | 0.112199 | **+13.28%  veto** |
| GI | 0.123954 | 0.112423 | -9.30% |
| JZ | 0.128446 | 0.111176 | -13.45% |
| **KZ** | 0.154072 | 0.174881 | **+13.51%  veto** |
| LZ | 0.157612 | 0.153458 | -2.64% |
| MN | 0.098999 | 0.074922 | -24.32% |
| OQ | 0.096139 | 0.093734 | -2.50% |
| RU | 0.115117 | 0.110525 | -3.99% |

The skew warned about in section 7 is exactly what happened, and the two readings must be
kept apart:

- **By absolute error reduction**, Ridge's advantage sits in **MN and GI**, which together
  account for **87.8%** of the 78,788 units of absolute error it removes (MN 43,607;
  GI 25,597). These are the two heaviest sectors by observed mass.
- **By relative gain**, the largest improvements are **MN -24.32%, JZ -13.45%,
  BE -12.35%** -- a different ordering, since GI improves only -9.30% relatively while
  contributing the second-largest absolute reduction.

Meanwhile Ridge degrades the two veto sectors, construction (FZ) and finance-insurance
(KZ), by 8,333 and 4,937 units of absolute error. It also beats persistence in only
**51.6%** of individual cells, close to a coin flip.

`ridge_ar` is therefore **not rejected as a model**; it failed a stability and safety
condition registered in advance. Revisiting it under a different, pre-registered stability
criterion would require a new DEC -- changing the criterion now, having seen these numbers,
is precisely what the pre-registration exists to prevent.

## 15. Controls and the national baseline

Both candidates beat both naive controls on aggregate **and in 7/7 years**, so the
naive-control gate is not the binding constraint anywhere.

`national_scaled_persistence` (0.134060) is **worse than plain `persistence`** (0.116458)
and beats it in only 47.3% of cells. Scaling each territory-sector by its national sector
ratio *degrades* the forecast. This is a direct, if narrow, corroboration of the note in
HERALD_56 section 4.8: national-trend information does not carry the sectoral series. It is
a finding about this baseline on this target, not a general statement about detrending.

## 16. Integrity

| Check | Result |
|---|---|
| Rows | 17,639 = registered count, no duplicated ZE-sector-year |
| Excluded cells | 1 (`5218 / JZ / 2019`), identical for all five models |
| Target-mutation invariance | PASS -- with every year after `t` removed **and the target at `t` itself replaced**, the predictions for `t` are unchanged for all five models. This replaces the registered "truncate at `t-1`" phrasing of section 9, which cannot be executed literally: the year-`t` rows would vanish and leave nothing to predict. The implemented check is strictly stronger, since it also mutates `y[t]` |
| Seeds used | 0 |
| Populations | all five models predict the same cells in every year and fold |
| Determinism | two independent output directories, identical SHA-256 |
| Negative predictions | `ridge_ar` 143 of 17,639 (0.81%); every other model 0. Reported per year as well as overall: 2019 82, 2020 43, 2021 11, 2022 4, 2023 1, 2024 1, 2025 1 -- disclosure, not a gate |
| Environment | python 3.10.12, pandas 2.3.3, numpy 1.26.4, scikit-learn 1.7.2 |

## 17. Persistence-only supplement -- `NOT_COMPARABLE`

`persistence` over 2013-2025, 32,760 cells: WMAPE **0.113114**.

No fitted model can be evaluated over this window, so this figure **must never be placed in
the same ranking table** as section 13. It describes persistence across the full panel; it
compares nothing.

## 18. Two implementation corrections, disclosed

**Population count, corrected before the audit ran.** The pre-registration stated 17,638
cells and two exclusions inside the official window. That conflated "incomplete from 2015
onward" with "incomplete inside 2019-2025": `5218 / JZ / 2018` is earlier than the window.
It was corrected to **17,639** and one exclusion before any model was fitted.

*Limitation of the temporal record.* That correction was committed **together with** the
result rather than in a separate earlier commit, so **git does not independently prove it
preceded the run**. The claim rests on the working sequence, not on the commit history. It
is an arithmetic correction to a population count, independent of any metric and unable to
favour any model, since all five predict the same cells -- but it should be read as a
self-reported ordering, not as a guarantee established by the repository.

**Supplement eligibility, corrected after execution.** The first run restricted the
supplement to cells complete on all five features, truncating it to 2015-2025 although the
registration fixed 2013-2025. `persistence` consumes `lag_1` alone, so eligibility there now
requires `lag_1` and the target only, and the supplement covers the registered 32,760 cells.
**The official window, its population and the verdict are untouched**: the official
predictions file is byte-identical before and after the fix, and the supplement is
`NOT_COMPARABLE` and enters no gate.

## 19. What this authorizes

Sectoral persistence at ZE x sector is promoted from **CANDIDATE** to the product's
forecasting engine, for the target and window audited here. HERALD_58 Part B
(forecast-derived states) is unblocked; its thresholds remain reserved for the project
owner.

Nothing else. No relational input, no neural encoder, no HPC job, no causal or
recommendation claim. Q3 of the contract remains the only route to another model
experiment. The engine forecasts an **annual flow of newly created establishments** -- not
stock growth, employment, output or survival.
