# HERALD 79 — Known-truth dynamic-relation benchmark

Status: pre-execution specification
Date: 2026-08-11
Parent experiment: HERALD 78, Slurm `7860350`

## 1. Question

HERALD 78 produced a mechanically valid dynamic GNN but did not establish
reliable learned mutations. This benchmark separates three explanations:

1. the architecture/optimisation cannot recover a dynamic graph even when the
   signal is present;
2. the validation controls reject known true dynamics or accept a known null;
3. the architecture and controls work under known truth, implying that the
   French panel is below the detectable signal regime.

Synthetic scores are never compared numerically with French scores. Recovery
is evaluated only against the known truth of the panel that generated it.

## 2. Semi-synthetic substrate

The benchmark keeps the real dimensions (14 years, 280 ZE2020 zones and nine
A10 sectors), the 2025 release-aware INSEE commuting prior, and the empirical
2012 count distribution. The last available commuting logit matrix is held
constant across synthetic years so that every graph mutation is known to come
from the injected deviation rather than a prior release.

For truth seed 271828, persistent rank-four factors and a smooth regime produce

`D[t] = scale * U diag(z[t]) V.T` and
`A[t] = topk_softmax(P + D[t], k=28)`.

Counts are generated causally. Growth at `t+1` combines mean reversion, a
national/sector shock observable in the distribution at `t`, propagation of
growth at `t` through `A[t]`, and count noise. The model receives only the
resulting counts and the observed prior; it never receives U, V, z, D, A or the
simulation innovations.

Negative-binomial sampling uses mean/variance parameterisation with `phi=1`
meaning Poisson and `Var(Y)=phi*E(Y)` otherwise. All clipping bounds and random
seeds are exported.

## 3. Paired scenarios

Every scenario uses identical truth factors and paired innovations.

| Scenario | deviation/prior SD | graph coefficient | phi | Purpose |
|---|---:|---:|---:|---|
| `macro_null` | 0 | 0 | 2.5 | false dynamic relations under macro trends |
| `static_prior` | 0 | 0.8 | 2.5 | useful observed graph but no learned mutation |
| `dynamic_native` | 0.015 | 0.8 | 2.5 | scale measured in HERALD 78 |
| `dynamic_medium` | 0.10 | 0.8 | 2.5 | detectable intermediate signal |
| `dynamic_medium_noisy` | 0.10 | 0.8 | 8.0 | same truth with realistic strong overdispersion |
| `dynamic_strong` | 0.30 | 1.1 | 2.5 | positive-control signal |

The ratio is a declared simulation control, not an estimate from the output.
The 0.015 level is anchored to the 0.0141 mean measured in HERALD 78; other
levels form a diagnostic dose curve and are not literature-derived.

## 4. Same model, no oracle assistance

The tested model is `HERALD78` without architectural changes. Evaluation is the
2025 one-step origin, optimisation seeds 0--4, epoch sweep 50/100/200 and
magnitude weights 0.01/0.1. Hyperparameters are selected on the declared two
validation years, followed by reset and train+validation refit. A matched
identity-permuted-prior fit uses the selected hyperparameters and the same
optimisation seed.

## 5. Known-truth outcomes

Primary outcomes do not use forecast error:

- correlation between learned and true dense deviations, off diagonal;
- Jaccard of the full top-k graph;
- precision, recall and F1 for edges added relative to the fixed prior;
- precision, recall and F1 for dated births and deaths;
- false added-edge rate in `macro_null` and `static_prior`;
- recovery loss under the identity-permuted prior;
- stability across the five optimisation seeds.

Forecast macro-F1, rho and MAE remain auxiliary.

## 6. Placebo calibration

The current HERALD 78 P1 is audited unchanged. It computes movement only
between the first and last dense matrices and then permutes years. A second,
prospectively declared statistic computes mean adjacent path roughness,

`mean_t(1 - corr(D[t-1], D[t]))`.

For smooth known dynamics the chronological path must be less rough than a
random ordering. Both statistics receive the same 199 derangements and exact
lower-tail randomisation p-value. Applying them directly to true D separates a
bad model from a bad temporal statistic.

## 7. Diagnostic decision rules

These are engineering calibration rules, not literature-derived discovery
thresholds. Continuous outcomes are always reported.

1. **Null specificity:** at least 4/5 seeds have added-edge false-positive rate
   at most 0.10 in `macro_null` and `static_prior`.
2. **Strong recovery:** at least 4/5 `dynamic_strong` seeds have added-edge F1
   at least 0.50 and dated-event F1 at least 0.30.
3. **Dose response:** median added-edge F1 is ordered native <= medium <= strong,
   with strong minus native at least 0.10.
4. **Noise response:** noisy-medium median recovery does not exceed clean-medium
   by more than 0.05; this is a direction check, not a success requirement.
5. **Relational specificity:** in at least 4/5 strong seeds, the correctly
   identified prior beats the permuted-prior fit by at least 0.10 added-edge F1.
6. **Placebo calibration:** the corrected path statistic rejects random order
   for the true medium and strong paths at p<=0.05 and does not reject the
   static truth. The legacy endpoint statistic is reported, never repaired
   after seeing the benchmark.

Interpretation is fail-closed:

- oracle truth fails a control -> validation-statistic defect;
- oracle passes but trained model fails strong recovery -> model/supervision
  defect;
- strong and medium recovery pass but native does not -> measured detection
  limit;
- native recovery passes but French relations fail -> real-data signal or
  misspecification, not a generic incapacity of the architecture.

## 8. Required guards

Before the scientific array: deterministic generation; exact shapes; causal
transition alignment; zero truth mutations in static scenarios; non-zero dated
events in dynamic scenarios; truth hidden from model inputs; perfect-recovery
metric identity; non-trivial prior-only baseline; permutation changes identity
while preserving weights; corrected path statistic rejects a smooth oracle and
not a static oracle; explicit use of HERALD78; atomic result files; and a
mutation audit that deliberately breaks each property.
