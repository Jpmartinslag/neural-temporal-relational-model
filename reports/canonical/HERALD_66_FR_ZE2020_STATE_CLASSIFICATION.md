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
