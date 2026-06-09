# HERALD Phase 4J-A - Forecast Combination Audit

Date: 2026-06-09  
Execution: local, deterministic  
Input: `data/processed/phase4g/joint/panel_ze2020.csv`  
Output: `hpc_results/herald_phase4j_a_20260609_local_r1`

## Verdict

**Aggregate gate: PASS. Final promotion: NOT YET.**

The pre-specified 50/50 mean of persistence and unweighted Ridge improves the
country-balanced mean WMAPE from `0.093912` to `0.087067` (`-7.29%`) and equals
or improves the best isolated component in all four countries. It also improves
pooled WMAPE.

However, the gain is not uniformly stable by year. The fixed mean beats the
best component for only 7 of 28 country-year comparisons, although it beats
persistence in 18/28 and Ridge in 17/28. Its worst-year WMAPE is 29-35% worse
than the safer isolated component in NL, BE, and PT. Therefore it may proceed
to a stability and uncertainty audit, but it is not yet the canonical final
baseline.

## Protocol

- Outer evaluation: FR, NL, BE, PT, years 2018-2024.
- Protocol: parameter zero-shot, target-history-available LOCO.
- Ridge fit: all source countries through `t-1`.
- Persistence: target-country `side_lag_1`.
- Fixed combination: `0.5 * persistence + 0.5 * Ridge`.
- Learned weight: grid `[0, 1]`, step `0.05`, selected through nested rolling
  LOCO among source countries only.
- Fallback: use learned weight only if nested source validation improves
  persistence by at least 1%; otherwise use persistence.
- Outer-country target observations are absent from Ridge fitting and weight
  selection.

## Results

| Country | Persistence | Ridge | Fixed 50/50 | Delta vs best component |
|---|---:|---:|---:|---:|
| FR | 0.085149 | 0.091561 | **0.074465** | -12.55% |
| NL | 0.078982 | 0.069821 | **0.069799** | -0.03% |
| BE | 0.087930 | 0.095380 | **0.084338** | -4.09% |
| PT | 0.123588 | 0.130927 | **0.119667** | -3.17% |

| Configuration | Country-balanced WMAPE | Worst country | Pooled WMAPE |
|---|---:|---:|---:|
| Fixed 50/50 | **0.087067** | **0.119667** | **0.077447** |
| Nested weight | 0.091842 | 0.122154 | 0.086412 |
| Nested weight + fallback | 0.091916 | 0.122154 | 0.086430 |
| Persistence | 0.093912 | 0.123588 | 0.087468 |
| Ridge | 0.096922 | 0.130927 | 0.089400 |

## Interpretation

The fixed mean benefits from complementary errors: persistence and Ridge can
err in opposite directions, so averaging reduces aggregate absolute error.
This effect is strongest in France. In the Netherlands, the gain over Ridge is
negligible and should be treated as a tie.

The source-learned weight does not transfer reliably. It selects almost no
Ridge for FR, small Ridge weights for BE/PT, and larger weights for NL. It
improves the balanced mean but violates the country-safety criterion. More
complex weight selection is therefore not justified.

The fixed mean's weak tail behavior matters. During difficult years, adding
Ridge can damage a strong persistence forecast. Mean improvement alone is
insufficient for final promotion.

## Integrity

- Persistence and Ridge reproduce Phase 4I-A to numerical precision
  (`max_abs_diff = 2.7e-15`).
- 4 countries x 7 years x 5 configurations evaluated.
- Weight selection records `outer_target_used_for_selection=false`.
- Script compiles and `git diff --check` passes.

## Decision

1. Keep fixed 50/50 as the only surviving combination candidate.
2. Reject learned weighting as a transferable selector.
3. Run a stability audit by country and year.
4. Add exploratory rolling conformal intervals, with normalized residuals and
   no formal coverage claim.
5. Do not add countries or enlarge the neural architecture yet.
6. Complete the semantic target gate independently before any cross-country
   generalization claim.

## Phase 4J-B Follow-up

Rolling stability confirms mixed behavior:

| Country | Wins vs persistence | Wins vs Ridge | Wins vs yearly best component |
|---|---:|---:|---:|
| FR | 5/7 | 6/7 | 4/7 |
| NL | 5/7 | 3/7 | 1/7 |
| BE | 4/7 | 4/7 | 1/7 |
| PT | 4/7 | 4/7 | 1/7 |

Exploratory rolling conformal coverage for fixed 50/50:

| Country | Nominal 90% | Observed | Mean relative width |
|---|---:|---:|---:|
| FR | 90% | 99.2% | 0.679 |
| NL | 90% | 87.1% | 0.262 |
| BE | 90% | 88.5% | 0.387 |
| PT | 90% | 96.0% | 0.713 |

Coverage is descriptive only. France and Portugal achieve high coverage with
very wide intervals. This does not support a strong calibrated-uncertainty
claim.

The semantic audit in
`reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md` also finds that the current
panel mixes local-unit creations, VAT registrations, and enterprise births.
Consequently, fixed 50/50 remains a useful heterogeneous-task benchmark
candidate, not evidence of transfer for one harmonized target.

## Reproduction

```bash
python3 hpc/phase4/run_phase4j_forecast_combination.py \
  --output-dir hpc_results/herald_phase4j_a_20260609_local_r1
```
