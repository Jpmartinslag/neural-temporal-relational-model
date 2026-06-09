# HERALD Phase 4I-A - Selective Transfer Benchmark Audit

Date: 2026-06-09  
Job: `7439835`  
Valid root: `hpc_results/herald_phase4i_a_20260609_113632_r1`

## Verdict

**PASS for execution. Both admission gates fail. Do not launch Phase 4I-B.**

The Phase 4I-A benchmark confirms that neither the current source-country
compatibility rule nor geographic message passing is reliable enough to
justify another neural graph residual battery.

The strongest universal baseline is the last observed value. The unweighted
source-fitted Ridge from Phase 4H-B remains competitive and is preferable when
a trained transferable model is required, but it does not beat persistence on
the four-country balanced objective.

## Integrity

- 40/40 Slurm tasks completed with exit code `0:0`.
- Four full deterministic benchmark runs, one per outer country.
- Nine additional MLP seeds per country.
- Rolling outer LOCO evaluation over 2018-2024.
- Source compatibility recomputed fold by fold using history through `t-1`.
- No outer target year used for fitting or source selection.
- Real and within-country permuted geographic controls included.

The earlier root `herald_phase4i_a_20260609_113155_r1` is invalid for scientific
comparison because its `ridge_all` was country-balanced while being labelled
as the unweighted Phase 4H-B Ridge. The valid rerun explicitly separates
`ridge_all` and `ridge_balanced_all`.

## Country-balanced ranking

| Configuration | Mean WMAPE | Worst country |
|---|---:|---:|
| Last value | **0.093912** | **0.123588** |
| Elastic Net | 0.096497 | 0.130430 |
| Ridge, unweighted | 0.096922 | 0.130927 |
| Pooled AR OLS | 0.097223 | 0.131528 |
| Permuted spatial Ridge | 0.105266 | 0.130118 |
| Real spatial Ridge | 0.105667 | 0.127390 |
| Spatial-lag OLS | 0.106134 | 0.128112 |
| Drift | 0.113355 | 0.164531 |
| Country-balanced Ridge | 0.114640 | 0.150414 |
| Compatible-source Ridge | 0.128215 | 0.195437 |
| Log-growth Ridge | 0.132323 | 0.231646 |
| Compatible spatial Ridge | 0.143478 | 0.248518 |
| Small balanced MLP | 0.189099 | 0.306248 |

## Best model by country

| Country | Best configuration | WMAPE |
|---|---|---:|
| FR | Country-balanced Ridge | 0.082979 |
| NL | Compatible-source Ridge | 0.067838 |
| BE | Last value | 0.087930 |
| PT | Last value | 0.123588 |

There is no single trained configuration that dominates across countries.
France benefits from balancing, Netherlands from source selection, while
Belgium and Portugal are best served by persistence.

## Compatibility gate

Compatible-source Ridge improves over unweighted Ridge in:

- NL: `-2.8%`;
- PT: `-2.2%`.

It fails severely in:

- FR: `+113.4%`;
- BE: `+27.4%`.

Although two countries improve by more than 1%, country-balanced WMAPE and
worst-country WMAPE both regress. The selector chooses two sources in 27 of 28
folds, but descriptor proximity does not predict transfer reliability.

**Compatibility gate: FAIL.**

## Graph gate

Real spatial Ridge beats plain Ridge only in Portugal. It does not demonstrate
an advantage over both plain Ridge and the permuted graph in at least two
countries:

- FR: spatial Ridge is 36.5% worse than Ridge;
- NL: 0.7% worse;
- BE: 4.8% worse and the permuted graph is better;
- PT: 2.7% better, but the real-vs-permuted difference is not significant.

**Graph gate: FAIL.**

## Frugal nonlinear baseline

The one-layer MLP predicts clipped log-growth and uses balanced source-country
weights. Across ten seeds it remains unstable:

| Country | Mean WMAPE | Seed std |
|---|---:|---:|
| FR | 0.230248 | 0.070542 |
| NL | 0.085181 | 0.011870 |
| BE | 0.134717 | 0.015095 |
| PT | 0.306248 | 0.089635 |

This is further evidence against increasing neural capacity under the current
short-panel transfer regime.

## Scientific interpretation

1. Short annual panels strongly favor persistence and regularized linear
   models.
2. Equal country weighting is not universally beneficial: it improves France
   but degrades the smaller countries.
3. Simple descriptor distance is insufficient for source-domain admission.
4. Geographic neighbor aggregation is not a transferable spatial mechanism.
5. The negative graph result is robust to a topology permutation control.

## Decision

1. Close Phase 4I-A as a valid negative transfer result.
2. Do not run the conditional selective neural residual Phase 4I-B.
3. Use last value as the universal benchmark floor.
4. Keep unweighted Ridge as the canonical trained LOCO model.
5. Report country-specific oracle results only as diagnostics, not as a
   deployable selector.
6. The next methodological work should target uncertainty and forecast
   combination, not a larger STGNN:
   - conformal intervals under rolling origin;
   - a causal selector between persistence and Ridge using only source-domain
     validation;
   - comparison with a formally estimated spatial/dynamic panel model when an
     appropriate econometric implementation is available.

## Reproduction

```bash
python3 hpc/phase4/audit_phase4i_results.py \
  --root hpc_results/herald_phase4i_a_20260609_113632_r1
```

Generated artifacts:

- `reports/phase4i_a_summary.csv`
- `reports/phase4i_a_country_balanced.csv`
- `reports/phase4i_a_paired_year_tests.csv`
- `reports/phase4i_a_decision.json`
