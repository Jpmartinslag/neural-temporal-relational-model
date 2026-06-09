# HERALD Phase 4I - Selective Transfer Benchmark

## Objective

Determine whether source-country compatibility is predictive enough to justify
another neural graph residual experiment. Phase 4I-A is a low-cost gate; Phase
4I-B is conditional.

## Protocol

- Common 2015-2024 European panel.
- Outer LOCO evaluation for FR, NL, BE, and PT.
- Rolling evaluation over 2018-2024.
- Target-country history is available through `t-1`; the target year is never
  used for fitting or source selection.
- Primary metric: mean yearly territorial WMAPE.
- Country-balanced fitting for pooled trainable baselines.

## Baselines

1. Last value.
2. Drift.
3. Pooled autoregressive OLS.
4. Pooled Ridge, matching the unweighted 4H-B backbone.
5. Country-balanced pooled Ridge.
6. Elastic Net.
7. Ridge predicting clipped log-growth relative to the last value.
8. Small country-balanced one-layer MLP predicting the same log-growth target.
9. Ridge with a forecast-safe geographic neighbor lag.
10. OLS with the geographic neighbor lag.
11. Ridge with a permuted-graph neighbor lag.

The OLS spatial-lag model is a predictive baseline. It is not labelled SAR,
SDM, or spatial dynamic panel because no IV/GMM or spatial likelihood
estimation is performed.

## Compatibility selector

At each outer fold, source countries are ranked using only history through
`train_max`. Descriptors cover relative scale, territorial dispersion,
aggregate growth, median local growth, volatility, and autocorrelation.

The number of selected sources (`k=1` or `k=2`) is chosen by an inner LOCO
procedure over the remaining source countries, minimizing worst-inner-country
mean yearly WMAPE. The final outer target is untouched.

## Gates

Phase 4I-B selective neural residual is permitted only if:

- compatible Ridge improves at least two countries by 1% or more;
- country-balanced WMAPE improves;
- worst-country WMAPE does not regress by more than 1%.

Graph message passing is enabled in 4I-B only if the real geographic lag beats
both plain Ridge and the permuted graph in at least two countries.

If either gate fails, Ridge remains the canonical transferable model and the
negative result is reported rather than increasing neural capacity.
