# HERALD Phase 4H-B - Results and Methodological Audit

Date: 2026-06-09  
Job: `7434844`  
Root: `hpc_results/herald_phase4h_b_20260608_223045_r1`

## Verdict

**Technical protocol: PASS. Scientific graph-transfer hypothesis: NOT
SUPPORTED.**

All 20 Slurm tasks completed successfully and all 380 expected trainings are
present. The outer country was excluded from fitting, residual shrinkage was
selected only through nested source-country holdouts, the EU falsification was
fold-local, and the geographic graphs contain real non-diagonal edges.

The corrected experiment nevertheless does not show a residual correction
that transfers robustly to an unseen country:

- Ridge is better in France, Belgium, and Portugal;
- the residual improves the Netherlands only for `base_identity`;
- that Netherlands gain is concentrated in 2019 and 2024 and is not stable
  across evaluation years;
- EU signals do not improve transfer consistently;
- the real geographic graph does not beat both identity and graph permutation
  consistently in any defensible cross-country pattern.

The current canonical zero-shot forecast should therefore remain the
source-fitted Ridge backbone.

## 1. Integrity and protocol

| Check | Result |
|---|---:|
| Slurm array tasks | 20/20 completed, exit `0:0` |
| Expected trainings | 380/380 |
| Nested calibration trainings | 180 |
| Final outer-country trainings | 200 |
| Metadata files | 380 |
| Nested selectors | 20 |
| Outer seeds per country/config | 10/10 |
| Prediction CSV files | 760 |
| Neural internal files | 3040 |
| Non-empty Slurm error logs | 0 |

All nested metadata exclude exactly `{outer_country, inner_country}` and
evaluate only the inner country. Final metadata exclude and evaluate exactly
the outer country. Every selector uses seeds `{0, 7, 42}`, the three remaining
source countries, and records `outer_targets_used=false`.

This is a **parameter zero-shot, target-history-available LOCO** protocol. It
is not strict cold-start: the held-out country supplies its historical lagged
targets and its known geographic topology at inference.

## 2. Primary outer-country results

Primary metric: arithmetic mean of yearly territorial WMAPE. The pooled WMAPE
is retained only as a sensitivity metric.

| Country | Best HERALD configuration | HERALD | Ridge | Relative delta | Wins vs Ridge |
|---|---|---:|---:|---:|---:|
| FR | `eu_control_identity` | 0.099619 | 0.091561 | +8.8% | 0/10 |
| NL | `base_identity` | 0.066831 | 0.069821 | -4.3% | 9/10 |
| BE | `base_identity` | 0.097402 | 0.095380 | +2.1% | 2/10 |
| PT | `eu_geo` | 0.132358 | 0.130927 | +1.1% | 4/10 |

For the common `base_identity` configuration:

| Country | Delta HERALD - Ridge | Wins | Paired Wilcoxon p |
|---|---:|---:|---:|
| FR | +0.008358 | 0/10 | 0.00195 |
| NL | -0.002991 | 9/10 | 0.00391 |
| BE | +0.002023 | 2/10 | 0.06445 |
| PT | +0.003500 | 0/10 | 0.00195 |

Across countries, the balanced means are:

| Forecast/configuration | Country-balanced WMAPE |
|---|---:|
| Ridge | **0.096922** |
| `base_identity` | 0.099645 |
| `eu_control_identity` | 0.100416 |
| `eu_identity` | 0.102269 |
| `eu_geo_perm` | 0.103623 |
| `eu_geo` | 0.103929 |

Thus no shared HERALD configuration beats Ridge on the balanced four-country
objective.

## 3. Nested shrinkage selection

The nested selector chose a positive residual weight in 19 of 20
country/configuration pairs:

- France: `alpha=0.20` for all configurations;
- Belgium: `alpha=0.20` for all configurations;
- Netherlands: `alpha=0.10`, except the EU temporal control (`alpha=0`);
- Portugal: `alpha=0.10` or `0.20`.

Only one of those 19 admitted residuals improved the final outer-country mean:
Netherlands `base_identity`.

This is not leakage. It is a substantive negative result: performance on the
remaining source-country holdouts is a weak predictor of transfer to a
structurally different outer country. Several choices are also fragile:

- NL `base_identity`: selector margin only `0.000075`;
- PT `eu_geo`: selector margin only `0.000020`;
- PT EU control: selector margin only `0.000315`.

The selector should be retained as a valid experimental mechanism, but it
cannot currently be used as evidence that residual admission is reliable.

## 4. Geographic graph audit

The graph artifacts are valid:

| Property | Result |
|---|---:|
| Matrix shape | 387 x 387 |
| Non-diagonal geographic edges | 1952 |
| Cross-country edges | 0 |
| Negative/non-finite weights | 0 |
| Real graph equals permutation | No |
| FR mean degree | 5.31 |
| NL mean degree | 4.40 |
| BE mean degree | 4.67 |
| PT mean degree | 3.76 |

Adjacency is row-normalized by the trainer before message passing. The mobility
matrix remains identity, so `fixed_graph` blends normalized geographic
neighbors with a self-loop.

The graph comparisons do not establish useful spatial transfer:

| Country | Real graph vs identity | Real graph vs permuted | Interpretation |
|---|---:|---:|---|
| FR | +7.0% | +4.1% | real graph is worse |
| NL | +0.5% | -0.2% | practical tie |
| BE | -0.9% | -1.8% | small, non-significant gain |
| PT | -0.1% | -0.9% | practical tie |

No graph comparison remains significant after Holm correction across the
planned falsification family. The experiment tests transfer of a shared graph
operator to each unseen country's **within-country** topology. Because the
matrix is block-diagonal, it does not test cross-country message passing.

## 5. EU signal audit

EU signals are not robust zero-shot covariates:

- FR: `eu_identity` is 4.6% worse than `base_identity`;
- NL: `eu_identity` is 8.8% worse, 0/10 wins, Holm-adjusted `p=0.03125`;
- BE: 2.0% worse;
- PT: 1.4% better, but not significant and not clearly superior to the
  fold-safe temporal control.

The fold-local temporal control is implemented causally: source training years
are permuted only among years available up to `train_max`, and target rows
receive values sampled only from those source years.

## 6. Netherlands exception

The only mean improvement over Ridge is not broad across time:

| Year | HERALD | Ridge | Delta | Seed wins |
|---:|---:|---:|---:|---:|
| 2018 | 0.039595 | 0.039609 | -0.000013 | 7/10 |
| 2019 | 0.054344 | 0.061093 | -0.006750 | 10/10 |
| 2020 | 0.089823 | 0.086638 | +0.003186 | 1/10 |
| 2021 | 0.063379 | 0.053390 | +0.009990 | 1/10 |
| 2022 | 0.049152 | 0.044557 | +0.004594 | 0/10 |
| 2023 | 0.021769 | 0.019501 | +0.002268 | 1/10 |
| 2024 | 0.149751 | 0.183961 | -0.034210 | 10/10 |

The aggregate gain is driven mainly by 2019 and 2024. This supports reporting
the result as a localized diagnostic, not as robust temporal transfer.

## 7. Statistical interpretation

Wilcoxon tests across seeds measure optimization stability conditional on the
same dataset and folds. Seeds are not independent territorial samples, so
their p-values must not be interpreted as population-level economic
significance. With only four countries, cross-country inference remains
descriptive.

The primary scientific evidence is therefore the combined pattern of effect
sizes, seed wins, year stability, country balance, and falsification controls,
not a single p-value.

## 8. Decision

1. Close Phase 4H-B as a valid negative result.
2. Keep Ridge as the canonical LOCO zero-shot baseline.
3. Do not promote EU signals or geographic message passing to the transferable
   architecture.
4. Do not increase neural capacity; the evidence indicates negative transfer,
   not underfitting.
5. Preserve `base_identity` for Netherlands as an exploratory local result,
   not a universal component.
6. Before adding countries, compare Ridge against strong short-panel baselines
   and estimate source-target compatibility. Any future residual should be
   admitted only for compatible source groups, with Ridge fallback otherwise.

## Reproducibility

Audit command:

```bash
python3 hpc/phase4/audit_phase4h_b_methodology.py \
  --root hpc_results/herald_phase4h_b_20260608_223045_r1 \
  --output-dir \
    hpc_results/herald_phase4h_b_20260608_223045_r1/reports/methodology
```

Generated tables:

- `phase4h_b_outer_seed_metrics.csv`
- `phase4h_b_summary.csv`
- `phase4h_b_selectors.csv`
- `phase4h_b_paired_comparisons.csv`
