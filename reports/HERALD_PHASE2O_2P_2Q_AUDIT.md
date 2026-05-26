# HERALD Phase 2O-2Q Audit

Date: 2026-05-25

## Integrity

All three batteries completed with Slurm exit code `0:0`.

| Phase | Root | Runs | JSON | Metadata | Total CSV | Sector CSV | NPZ |
|---|---|---:|---:|---:|---:|---:|---:|
| 2O | `hpc_results/herald_regime_phase2o_residual_shrinkage_20260525_2o_shrink_r1_r1` | 90 | 90 | 90 | 90 | 90 | 540 |
| 2P | `hpc_results/herald_regime_phase2p_hc_auditor_interaction_20260525_2p_hc_aud_r1_r1` | 80 | 80 | 80 | 80 | 80 | 480 |
| 2Q | `hpc_results/herald_regime_phase2q_input_arch_robustness_20260525_2q_input_arch_r1_r1` | 90 | 90 | 90 | 90 | 90 | 540 |

## Main Result

No single candidate dominates all criteria. The new batteries produce a Pareto frontier:

- best mean / 2025: `HC5_trainopt`;
- strongest clean shrinkage evidence: `L5_trainopt`;
- best 2021: `L4_a10g` or `minimal_AUDboth`, but both have trade-offs;
- best A10: `AUD_alpha_trainopt`;
- most robust input policy: `side5_lag1_growth1y` / SIDE2.

The correct interpretation is not "HERALD learned a perfect internal auditor." The stronger claim is:

> HERALD is best framed as Ridge plus a learned residual correction whose strength should be calibrated. Shrinkage is useful, but it does not solve every objective simultaneously.

## Phase 2O — Residual Shrinkage

| Label | Mean WMAPE | 2021 | 2025 | A10 | Reading |
|---|---:|---:|---:|---:|---|
| `HC5_trainopt` | 0.020497 | 0.038140 | 0.011259 | 0.160385 | Best mean and 2025, but weaker 2021/A10 |
| `HC5_l0_050` | 0.020966 | 0.037674 | 0.011562 | 0.160364 | Regularizer remains useful |
| `L5_trainopt` | 0.020966 | 0.035976 | 0.012591 | 0.158333 | Cleanest evidence for shrinkage |
| `AUD_alpha_trainopt` | 0.021278 | 0.035732 | 0.012336 | 0.156664 | Best A10 in Phase 2O |
| `L4_a10g` | 0.021455 | 0.031974 | 0.013208 | 0.156884 | Best 2021, with mean trade-off |

Paired vs `L5_gate_no_auditor`:

- `HC5_trainopt` mean: delta `-0.001104`, wins `7/10`, p `0.1602`.
- `HC5_trainopt` 2021: delta `+0.002274`, wins `3/10`, p `0.3750`.
- `L5_trainopt` mean: delta `-0.000634`, wins `10/10`, p `0.0020`.
- `L5_trainopt` 2025: delta `-0.000580`, wins `8/10`, p `0.0078`.

Decision:

- `train_opt` shrinkage is validated as a useful mechanism.
- `HC5_trainopt` is the best raw candidate for mean/2025.
- `L5_trainopt` is the cleaner scientific result because it improves mean in `10/10` paired seeds without relying on HC5.
- Fixed shrinkage `0.50` and `0.75` should be rejected. `L5_shrink050` is significantly worse.

## Phase 2P — HC5 + Auditor

| Label | Mean WMAPE | 2021 | 2025 | A10 | Reading |
|---|---:|---:|---:|---:|---|
| `HC5_alpha_b001` | 0.021110 | 0.035593 | 0.013629 | 0.157151 | Best interaction, but not better than 2O |
| `HC5_l0_050` | 0.021162 | 0.037130 | 0.011739 | 0.159114 | Better 2025, weaker 2021/A10 |
| `AUD_alpha_b001` | 0.021363 | 0.035217 | 0.013037 | 0.157337 | Best 2021 in this phase |
| `HC5_both_b001_s010` | 0.021570 | 0.036785 | 0.013189 | 0.159924 | No clear advantage |

Paired vs `L5_gate_no_auditor`:

- `HC5_alpha_b001` mean: delta `-0.000733`, wins `7/10`, p `0.3223`.
- `HC5_alpha_b001` 2021: delta `-0.000908`, wins `5/10`, p `0.8457`.
- `AUD_alpha_b001` 2021: delta `-0.001284`, wins `7/10`, p `0.1309`.

Decision:

- The `alpha_neutral` auditor remains useful as an A10/2021 stabilizer.
- The interaction `HC5 + alpha` is plausible but not strong enough to become the main candidate.
- `both` remains weaker than `alpha_neutral`; do not expand `both` without a new reason.

## Phase 2Q — Input Policy x Architecture

| Label | Mean WMAPE | 2021 | 2025 | A10 | Reading |
|---|---:|---:|---:|---:|---|
| `side2_HC5` | 0.021434 | 0.037067 | 0.011749 | 0.160665 | Best mean in 2Q |
| `side2_L5` | 0.021451 | 0.036651 | 0.012793 | 0.160473 | Baseline nearly tied |
| `side2_AUDboth` | 0.021700 | 0.034600 | 0.011776 | 0.158726 | Better 2021/A10, slight mean cost |
| `no_noise_HC5` | 0.023092 | 0.035549 | 0.011574 | 0.162108 | Not enough to beat SIDE2 |
| `minimal_AUDboth` | 0.024950 | 0.031813 | 0.012056 | 0.161674 | Best 2021, but mean degrades |

Paired vs `side2_L5`:

- `side2_HC5` mean: delta `-0.000017`, wins `5/10`, p `0.7695`.
- `side2_AUDboth` 2021: delta `-0.002051`, wins `6/10`, p `0.3750`.
- `minimal_AUDboth` 2021: delta `-0.004838`, wins `8/10`, p `0.0273`.
- `minimal_AUDboth` mean: delta `+0.003499`, wins `2/10`, p `0.0645`.

Decision:

- SIDE2 remains the robust input base.
- `minimal_side_only` helps 2021 but damages mean WMAPE too much.
- `no_flores_no_side_stock_a10` does not beat SIDE2 in this crossing.
- The architecture result is not independent of inputs; this argues for keeping input policy fixed in confirmatory runs.

## Hypotheses Answered

1. **Should HERALD always apply the full neural residual?**
   No. `train_opt` shrinkage improves the L5 control in mean WMAPE with `10/10` paired wins.

2. **Does shrinkage solve 2021?**
   No. The best mean candidate `HC5_trainopt` worsens 2021 relative to `L5_gate_no_auditor`.

3. **Does HC5 + auditor produce a new dominant model?**
   No. `HC5_alpha_b001` is reasonable but does not beat Phase 2O.

4. **Is SIDE2 still the best input policy?**
   Yes. The input x architecture battery supports SIDE2 as the main policy.

5. **Is the auditor useless?**
   No. `AUD_alpha` helps A10/2021, but it is a stabilizer, not the global winner.

## Recommendation

Promote two candidates to the final confirmatory audit:

1. `L5_trainopt`: cleaner scientific shrinkage result.
2. `HC5_trainopt`: best raw mean/2025 candidate.

Keep as guardrail comparisons:

- `L5_gate_no_auditor`;
- `L4_a10g`;
- `AUD_alpha_trainopt`;
- `side2_AUDboth`.

Stop expanding:

- fixed shrinkage;
- more hard-concrete lambda grids;
- more `both` auditor variants;
- minimal input as primary model;
- broad feature drop batteries.

Next audit should be confirmatory, not exploratory: paired bootstrap, non-inferiority margins, Pareto decision, and sector baseline comparison for A10.

