# HERALD — Current Model Decision

Date: 2026-05-27

## Decision

Freeze `Q7_effectifs_lag1` as the current HERALD no-flags candidate for the next presentation/dashboard comparison.

This is not because it wins every metric. It is the best compromise between performance, stability, simplicity, and methodological defensibility.

## Current Candidate

| Item | Choice |
|---|---|
| Model | HERALD no flags |
| Annual SIDE inputs | `side_lag_1`, `growth_1y` |
| Manual flags | none |
| Latent regime | learned, dimension 5 |
| Residual calibration | train-only `train_opt` |
| q_tensor | URSSAF `effectifs_salaries_cvs`, lagged by one year |
| q_tensor excluded | `masse_salariale_cvs` |
| A10 guard | not in the default candidate |

## Evidence From Phase 3E

Phase 3E completed 240/240 runs with 20 seeds per config.

| Config | Mean WMAPE | Std | WMAPE 2021 | WMAPE 2025 | Sector WMAPE | Reading |
|---|---:|---:|---:|---:|---:|---|
| `Q6_lag1` | 0.020251 | 0.001718 | 0.0339 | 0.0123 | 0.15680 | best raw mean, but keeps both q_tensor channels |
| `Q12_effectifs_lag1_a10guard` | 0.020371 | 0.001959 | 0.0347 | 0.0124 | 0.15509 | best sector WMAPE, adds guard complexity |
| `Q7_effectifs_lag1` | 0.020398 | 0.001498 | 0.0348 | 0.0114 | 0.15612 | best default compromise |
| `Q0_real` | 0.020559 | 0.001835 | 0.0349 | 0.0113 | 0.15827 | full contemporaneous q_tensor baseline |
| `Q1_zero` | 0.020659 | 0.002045 | 0.0315 | 0.0130 | 0.15688 | q_tensor removed; competitive but weaker 2025 |

Key pairwise readings:

- `Q0_real` vs `Q1_zero`: q_tensor is not indispensable for global WMAPE.
- `Q0_real` vs `Q3_spatial_perm`: there is weak/moderate evidence of ZE-local signal, but not enough for a strong claim.
- `effectifs` beats `masse_salariale` directionally in both contemporaneous and lagged forms.
- lagged q_tensor is preferred over contemporaneous q_tensor.
- `Q12` improves sector WMAPE, but the global gain over `Q7` is too small to justify making it the default.

## What We Can Claim

- The current evidence favors a simpler HERALD no-flags architecture.
- The useful labor signal appears to be lagged employment level/trend, not the full contemporaneous quarterly tensor.
- Removing manual flags remains methodologically cleaner and competitive.
- The learned regime remains useful as a model mechanism, but we should not claim it discovered a complete economic taxonomy by itself.

## What We Should Not Claim

- Do not claim a strong ZE-specific q_tensor effect. Spatial falsification is not strong enough.
- Do not claim q_tensor is essential. `Q1_zero` is competitive.
- Do not claim the model fully understands rare rebounds. 2021 remains a stress case.
- Do not call `HERALD flags extended` a fair comparator against no-flags clean; it has a broader input set.

## Next Step

Build the final comparison/dashboard around:

1. `HERALD no flags Q7_effectifs_lag1` as the current candidate.
2. `HERALD no flags Q0_real` as the previous full q_tensor reference.
3. `HERALD flags clean` as the fair manual-flag comparator.
4. `HERALD flags extended` as the older broad-input control.
5. Ridge AR, ARIMA, LSTM, DCRNN, and Dynamic STGNN as external baselines.

No new feature search is recommended before this comparison is made readable.
