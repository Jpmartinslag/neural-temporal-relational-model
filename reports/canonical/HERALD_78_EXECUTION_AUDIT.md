# HERALD 78 — Execution and self-audit

Date: 2026-08-11
Scientific run: Slurm array `7860350`, origins 2021--2025, five seeds/origin
Remote artifact root: `/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald78/run_7860350`

## Execution integrity

All five array tasks completed with Slurm state `COMPLETED` and exit code `0:0`.
Elapsed time ranged from 23:03 to 59:18 and peak resident memory from 1.53 to
1.64 GB. All five stderr files are empty.

The run produced 25 seed reports, 25 graph archives, 25 event files, five
cross-seed reports, five cross-seed band archives, five reliable-edge exports
and five stable-event exports. No produced file has zero bytes and no graph
archive contains non-finite values. Heavy artifacts remain on the cluster; the
three aggregate summaries are mirrored locally under
`hpc_results/herald78/run_7860350/`.

The pre-execution suite passed 18/18 guards and killed 18/18 deliberate
mutants. This establishes mechanical conformance, not scientific success.

## Forecasting result

The table reports the mean over five optimisation seeds. Baselines do not vary
with optimisation seed.

| Origin | HERALD macro-F1 | Mean reversion | Delta | National-sector mean |
|---:|---:|---:|---:|---:|
| 2021 | 0.2104 | 0.3014 | -0.0910 | 0.1885 |
| 2022 | 0.3203 | 0.2686 | +0.0517 | 0.2400 |
| 2023 | 0.1913 | 0.3967 | -0.2055 | 0.2783 |
| 2024 | 0.3420 | 0.4387 | -0.0968 | 0.2090 |
| 2025 | 0.3912 | 0.4531 | -0.0619 | 0.3151 |
| **Mean** | **0.2910** | **0.3717** | **-0.0807** | **0.2462** |

HERALD beats mean reversion in one of five origins and 5/25 seed-origin fits.
Across the 25 fits, its macro-F1 standard deviation is 0.0893 and the paired
delta standard deviation is 0.0937. Mean Spearman rho is 0.2531. Forecasting is
auxiliary to the relational claim, so this negative comparison does not by
itself reject a dynamic graph; it does reject a claim that this fitted model is
a better one-step state predictor than the declared primary baseline.

## Independent dynamism gates

| Origin | Joint pass | Above NB floor | Below all P1 placebos | LOYO invariant | Precedence | Relational placebo valid | Stable event identities |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 2021 | no | 0/5 | 0/5 | 3/5 | 4/5 | 4/5 | 0 |
| 2022 | no | 1/5 | 0/5 | 1/5 | 3/5 | 4/5 | 223 |
| 2023 | no | 4/5 | 0/5 | 2/5 | 1/5 | 1/5 | 0 |
| 2024 | no | 3/5 | 0/5 | 2/5 | 5/5 | 5/5 | 0 |
| 2025 | no | 4/5 | 0/5 | 1/5 | 4/5 | 5/5 | 0 |
| **Total** | **0/5** | **12/25** | **0/25** | **9/25** | **17/25** | **19/25** | **223** |

Mean dense-score movement is 0.0271 and the mean maximum NB-resample floor is
0.0170. Movement clears that conservative noise floor in only 12/25 fits. More
decisively, chronological movement is below every one of the 19 temporally
deranged controls in 0/25 fits. This gate does not use forecast error.

Only origin 2022 has cross-seed stable learned-attributable event identities:
223 zone-edge identities, expanded to 2,007 zone-sector event rows. Its median
pairwise event Jaccard is only 0.111; the other four origins have Jaccard zero.
The 19,827 exported reliable zone-sector edge rows and the 2,007 stable event
rows are therefore diagnostic exports, not validated economic relations under
the pre-registered joint gate.

## Scale and recurrence of the old failure

At the scored end of each fit, the mean learned-deviation/prior SD ratio is
0.0141, mean correlation between prior and full dense score is 0.999895, and
mean top-k Jaccard with the prior is 0.8893. Thus the inferred `z_t` is no
longer absent or gradient-dead, but the learned deviation remains roughly 1.4%
of prior scale. The former `r=0.9994` prior-reproduction failure is reproduced
scientifically, although not through the old implementation defect.

This run therefore supports: deterministic execution, causal availability of
the inferred regime, valid dense export, some matched precedence signals, and
one-origin event stability. It does **not** establish learned dynamic relations
that survive the declared noise and temporal controls.

## Defect found after execution

The first aggregation attempt failed because the glob
`origin_{year}_seed_*_report.json` also selected
`origin_{year}_cross_seed_report.json`, and the parser used the wrong split
position even for valid seed names. No scientific result was affected. The
aggregator now accepts only the exact regular expression
`origin_{year}_seed_(digits)_report.json`; aggregation then completed over all
25 reports.

## Decision and next step

Do not relax the gates after seeing the result and do not present the exported
edges as discovered economic structure. HERALD 78 is an executable and
mechanically defended negative experiment: the principal relational claim is
not established by this architecture/data regime.

The next experiment, if pursued, must be a new pre-registered study. Priority:

1. diagnose why the relational gradient settles at 1.4% of prior scale,
   reporting gamma, `z`, U/V gradients and scale by epoch without changing the
   current verdict;
2. test the already specified recurrent `g(z[t-1])` and hybrid arms as named
   sensitivity architectures, not as repairs to HERALD 78;
3. add direct relational supervision or longer/repeated observed commuting
   releases if the scientific goal is graph identification, because forecast
   loss alone did not identify stable mutations here;
4. retain forecasting as an auxiliary imputation/ranking output and assess it
   against nonlinear and mean-reversion baselines on the same target; do not
   infer relational validity from its score.

One specification ambiguity should be closed before a successor run: section 9
speaks at origin level, whereas the implementation requires every gate in every
seed. That conjunction is conservative. It does not change this verdict because
the temporal-placebo gate failed in all 25 fits and stable event identities were
absent in four of five origins.
