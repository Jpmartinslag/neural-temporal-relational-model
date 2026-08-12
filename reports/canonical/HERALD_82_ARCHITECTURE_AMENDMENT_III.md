# HERALD 82 — Amplitude and dynamism-metric amendment

Status: pre-execution specification
Date: 2026-08-11
Supersedes the affected formulas in HERALD 77; HERALD 78 remains historical.

## 1. Defect being corrected

Known-truth runs 7860475 and 7860492 established two independent defects.

First, unit-norm U/V together with `|z|<=1` bounds every factor singular value
by one. The native, medium and strong truths required maxima 2.56, 17.07 and
51.22. The old architecture therefore could not represent the tested truth.

Second, the temporal placebo used only first-versus-last distance. Smooth
monotonic truth returned `p=1.0`, while an adjacent-path statistic returned
`p=0.005`.

## 2. Binding architecture

`D[t] = U diag(exp(a) * z[t]) V.T`

U and V retain unit-norm columns, `z[t]=tanh(W c[t]+b)` remains dynamic and
bounded, and `exp(a)` is a persistent positive amplitude per rank component.
This adds exactly four relational parameters at rank four: 2,501 becomes 2,505.

Amplitude is initialised by a declared parity rule, not an observed result:

`amplitude_0 = 0.5 * n_zones / sqrt(rank)`.

For 280 zones and rank four this is 70. The factor 0.5 approximates the
off-diagonal SD of the presence-only-standardised prior; the exact realised
prior/deviation scale is still reported. A large starting amplitude does not
force a large deviation because z can contract toward zero. No amplitude
penalty or post-result clipping is introduced in this experiment.

## 3. Binding temporal statistic

Dynamism is measured in one unit everywhere — observed fit, NB resamples, LOYO
and temporal permutation:

`R(D) = mean_t(1 - corr(D[t-1],D[t]))`.

The lower-tail exact permutation p-value uses 199 derangements in known-truth
calibration and 19 in the later French confirmatory run. Endpoint distance is
retained only as a historical diagnostic and is not a gate.

Passing temporal order is necessary but not sufficient: known-null edge/event
false positives and known-truth identity recovery must pass before French data
may be rerun. This prevents recurrently imposed smoothness from being called an
economic relation.

## 4. Required order

1. mechanical guards and mutation audit;
2. corrected generator with distinct macro-null and static-prior panels;
3. truth generated inside the HERALD 82 model class;
4. deterministic clean controls, then NB overdispersion;
5. dense deviation, changed-edge and dated-event recovery;
6. French rolling-origin run only if the known-truth gates pass.

The recovery thresholds remain those declared in HERALD 79. Failure cannot be
repaired by weakening them after observing HERALD 82.
