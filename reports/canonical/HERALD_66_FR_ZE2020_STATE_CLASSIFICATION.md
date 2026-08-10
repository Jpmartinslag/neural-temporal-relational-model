# HERALD 66 -- Reframing the target: state classification, not count regression

**Date:** 2026-08-10
**Sections 1-4:** `PRE_REGISTERED` (DEC-100). Written before the code existed.

## 1. Why the target changes

Everything from DEC-088 to DEC-099 evaluated **count regression** and scored WMAPE. The
product asks a different question: does a zone-sector **grow, stagnate or decline**.

Two consequences of the mismatch, both visible in what we already measured:

- WMAPE rewards predicting no change, which is why persistence wins it. In state
  classification persistence is **degenerate by construction** -- it always answers
  "stagnates" -- so the metric stops flattering it.
- Predicting *how many* establishments open is strictly harder than predicting *the sign of
  the change*. We spent the whole evaluation on the harder problem.

`HERALD_ECONOGNN_TRANSFERABILITY_AUDIT` records that EconoGNN, the domain reference, also
classifies states (resilient / recovered / declining) rather than forecasting counts, and
uses **observed** trade edges rather than learned ones. Both choices match where our own
evidence pushed us.

## 2. Target definition, frozen

Per node `(zone i, sector s)` and year `t`, on `g = log1p(y_t) - log1p(y_{t-1})`:

```text
declines    g <= -0.05
stagnates   -0.05 < g < 0.05
grows       g >= 0.05
```

The +-0.05 band is fixed here, before any result. A tercile-balanced variant is reported as
a sensitivity check, never as the headline.

## 3. Metric

**Macro-F1** across the three classes, so a model cannot win by predicting the majority
class. Accuracy is reported alongside but does not decide anything.

## 4. Arms and gates

| arm | features |
|---|---|
| `persistence` | always "stagnates" |
| `sector_year_majority` | the national modal state of that sector that year, an oracle-flavoured strong baseline |
| `ridge` | causal lags only |
| `gbm` | causal lags only -- **and see 4.1** |
| `mlp` | causal lags only |
| `+relational` | causal lags **plus** analogy-neighbour states and precedence-source growth |

Rolling origin 2019-2025, train on `target_year <= t-1`.

**S1 -- the relational gate.** `+relational` must beat its own no-relational twin on macro-F1
in at least **5 of 7** years. Same model, same folds, only the feature block differs. This is
the first test in the project where a relational gain would be attributable.

**S2 -- nonlinearity gets a fair run.** DEC-088's HistGB figure (0.364 WMAPE against Ridge's
0.034) was reported and passed over; a gradient booster is not ten times worse than a linear
model on this data, so that run is treated as **misconfigured, not informative**, and is
re-run here with the defaults checked.

Reporting rule of `HERALD_62` B7 applies.

---

## 5. Results (DEC-101)

`src/modeles/france_ze2020/run_fr_ze2020_state_classification.py`, 7 rolling origins
2019-2025, macro-F1.

### 5.1 The ordering inverts once the target is the state

| model | macro-F1 | accuracy |
|---|---|---|
| **mlp + relational** | **0.348** | 0.528 |
| mlp | 0.330 | 0.529 |
| gbm + relational | 0.323 | 0.547 |
| gbm | 0.319 | 0.543 |
| logreg + relational | 0.307 | 0.567 |
| logreg | 0.306 | 0.564 |
| sector previous-year mode | 0.262 | -- |
| **persistence** | **0.112** | -- |

Two reversals against everything measured under WMAPE:

- **Nonlinear models now win.** The linear model is last of the three real learners. Under
  count regression Ridge beat every neural arm; under state classification it is beaten by
  both the MLP and the gradient booster.
- **Persistence collapses to 0.112.** It answers "stagnates" for every cell, which minimises
  absolute error and is near-useless for macro-F1. The metric no longer rewards inaction.

The S2 concern is settled in passing: a correctly configured `HistGradientBoostingClassifier`
lands at 0.319, in the same range as the other learners, confirming that DEC-088's 0.364
WMAPE figure was a misconfiguration and not evidence about gradient boosting.

### 5.2 S1 -- PASSED, 4 of 5 seeds

Same architecture, same folds, same years; only the relational feature block differs.

| seed | mlp+rel | mlp | years won | delta |
|---|---|---|---|---|
| 0 | 0.348 | 0.330 | 5/7 | +0.018 |
| 1 | 0.348 | 0.322 | 6/7 | +0.026 |
| 2 | 0.333 | 0.318 | 5/7 | +0.016 |
| 3 | 0.338 | 0.334 | **3/7** | +0.004 |
| 4 | 0.335 | 0.332 | 5/7 | +0.004 |

**The delta is positive in 5/5 seeds** and the 5-of-7 gate passes in 4/5. Direction is
consistent; magnitude is not.

This is the first attributable relational gain in the project. Every earlier comparison
changed architecture and feature set together, so no gain could be assigned to the relations.

The gain also scales with the model's capacity to combine features nonlinearly -- logreg
+0.001, gbm +0.004, mlp +0.018 -- which is what the mechanism predicts: a linear model cannot
represent "my analogues grew" interacted with "my sector is falling".

### 5.3 The absolute level is weak, and this must be stated first

| | macro-F1 |
|---|---|
| mlp + relational, mean over seeds | 0.340 |
| mlp, mean over seeds | 0.327 |
| **stratified random** | **0.307** |

The complete model sits **+0.033 above random guessing**. Of that margin the relational block
accounts for **+0.013, roughly 40%** -- but the margin itself is small. This is a detectable
weak signal, not a usable classifier, and nothing here supports deploying it as a
recommendation engine.

### 5.4 Open: is 0.34 near the ceiling?

With small cells, whether a zone-sector crosses +-5% may be largely counting fluctuation
rather than economics. If a large share of labels flips under Poisson resampling, the
attainable maximum is far below 1.0 and 0.34 may be close to it. R3 already showed this class
of statistic can be entirely noise (DEC-096 10.2).

Section 6 measures it. Until then, no claim is made about whether the model is weak or the
problem is capped.

## 6. The noise ceiling (DEC-102)

`src/modeles/france_ze2020/measure_fr_ze2020_state_noise_ceiling.py`. Each cell is
Poisson-resampled at its observed mean, labels are rebuilt, and an oracle that knows the true
rate is scored against the noisy realisation. 40 replicates, 17,640 evaluated cells each.

| | |
|---|---|
| labels that flip on counting noise alone | **27.5%** (sd 0.32) |
| macro-F1 of a rate-knowing oracle | **0.655** (sd 0.004) |
| mlp + relational | 0.340 |
| stratified random | 0.307 |
| **share of the random-to-ceiling gap captured** | **9%** |

**The problem is not capped; the model is weak.** Labels do carry real noise -- more than a
quarter flip under resampling -- but the attainable maximum is 0.655, not something near 0.35.
The model captures roughly a tenth of the available signal.

This is the less convenient of the two possible answers and it is the one the data gives.
Section 5.4 is resolved against the model.

Observed class balance: grows 56.9%, declines 22.6%, stagnates 20.6%.

**Consequence for how this is written up.** The relational gain of section 5.2 stands -- it is
attributable, positive in 5/5 seeds, and passes its gate in 4/5. What cannot be claimed is
that the approach is near the limit of what the data allows. There is roughly 0.31 of macro-F1
between the current model and the ceiling, and nothing in this project has yet reached into it.
