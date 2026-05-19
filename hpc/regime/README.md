# HERALD regime and feature-audit batteries

This directory contains the SLURM entrypoints for HERALD regime discovery, feature minimality and
macro/falsification batteries.

## Current status

| Phase | Purpose | Status | Main result |
|---|---|---|---|
| Phase 2A | latent gate without manual flags | completed | useful signal, A10 trade-off |
| Phase 2B | A10 guard | completed | sector guard helped, 2021 remained difficult |
| Phase 2C | critical falsifications | completed | candidate used latent signal, but unstable in 2021 |
| Phase 2D | stability regularizers | completed | no stable fix for 2021 |
| Phase 2E | residual/rebound tests | completed | no robust improvement |
| Phase 2G | feature-noise removal | completed | simplified SIDE core became best candidate |
| Phase 2H | macro INSEE/Banque de France | completed | macro not retained; `best_simplified` wins globally |
| Phase 2I | SIDE 5-feature audit | completed | `lag1_growth1y` wins: WMAPE mean 0.021323 |
| Phase 2J | fair flag comparison | completed | no-flags SIDE2 beats clean manual-flags SIDE2 |
| Phase 2K | latent-regime dimension audit | planned | test whether latent size 3 is necessary or over-conditioning |

## Canonical candidate after Phase 2H

`best_simplified` is the current HERALD-France candidate.

Annual features:

- `side_lag_1`
- `side_lag_2`
- `side_lag_3`
- `growth_1y`
- `growth_2y`

Phase 2H metrics:

- mean WMAPE 2021-2025: `0.025347`
- WMAPE 2021: `0.036236`
- WMAPE 2025: `0.014990`
- A10 WMAPE: `0.161675`
- seed std: `0.002189`

Combined audit:

```text
hpc_results/phase2h_combined_audit/PHASE2H_COMBINED_AUDIT.md
reports/HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md
reports/HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md
```

## Entrypoints

| Script | Role |
|---|---|
| `regime_plan_configs.sh` | central registry of plan labels and config rows |
| `run_herald_regime_seed.sh` | executes one seed across all configs in a plan |
| `run_herald_regime_array.sbatch` | SLURM array wrapper |
| `aggregate_herald_regime_results.py` | aggregates per-run JSON metrics |
| `audit_herald_regime_plan.py` | plan/preflight helper |

Submit scripts:

| Script | Plans |
|---|---|
| `submit_herald_regime_discovery.sh` | `discovery`, old baseline |
| `submit_herald_regime_phase2b.sh` | `phase2b_a10_guard` |
| `submit_herald_regime_phase2c.sh` | `phase2c_critical` |
| `submit_herald_phase2d_stability.sh` | `phase2d_stability` |
| `submit_herald_phase2e_residual_rebound.sh` | `phase2e_residual_rebound` |
| `submit_herald_phase2g_feature_noise.sh` | `phase2g_feature_noise` |
| `submit_herald_phase2h_macro.sh` | `phase2h_macro_real`, `phase2h_macro_permute`, `phase2h_macro_extra` |
| `submit_herald_phase2i_side5.sh` | `phase2i_side5_audit` |
| `submit_herald_phase2j_fair_flag.sh` | `phase2j_fair_flag` |

Smoke tests:

| Script | Purpose |
|---|---|
| `smoke_test_phase2d.sh` | phase 2D CPU/GPU sanity |
| `smoke_test_phase2e.sh` | phase 2E sanity |
| `smoke_test_phase2g_feature_noise.sh` | feature-policy sanity |
| `smoke_test_phase2h_macro.sh` | macro-panel sanity |
| `smoke_test_phase2i_side5.sh` | Phase 2I SIDE5 sanity (9 configs) |
| `smoke_test_phase2j_fair_flag.sh` | Phase 2J fair flag sanity (2 configs) |

## Safe launch protocol

Before any long run:

1. use a unique `OUT_ROOT`;
2. run the matching smoke test;
3. check `REGIME_PLAN` expected count;
4. check generated run tags are unique;
5. verify required input files exist on the HPC;
6. submit only after smoke and preflight pass.

Example for Phase 2H:

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
bash hpc/regime/smoke_test_phase2h_macro.sh

REGIME_PLAN=phase2h_macro_real \
STAMP=20260515_1205_macro_real_r3 \
bash hpc/regime/submit_herald_phase2h_macro.sh
```

Monitor:

```bash
squeue -u "$USER"
sacct -j <JOBID> --format=JobID,JobName%35,State,ExitCode,Elapsed
tail -f hpc_results/<OUT_ROOT>/logs/*.out
```

Recover:

```bash
rsync -av \
  meso-direct:/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/<OUT_ROOT>/ \
  hpc_results/<OUT_ROOT>/
```

Aggregate:

```bash
python3 hpc/regime/aggregate_herald_regime_results.py --root hpc_results/<OUT_ROOT>
```

## Rules

- Do not reuse an existing `OUT_ROOT`.
- Do not edit old phase labels after results exist.
- Add new hypotheses as new labels, not by changing historical labels.
- Keep manual flags out of clean-candidate plans.
- Keep source flags out of clean-candidate plans.
- Treat macro additions as exploratory unless a permutation test supports the signal.
- Do not move these scripts without updating the submit scripts; the current structure is path-stable.

## Phase 2I — SIDE5 feature audit

Goal: audit contribution of each of the five SIDE annual features in `best_simplified`.

Status: preflight-ready. Feature policies implemented. Smoke and submit scripts ready.

Important: each Phase 2I policy removes the tested feature from both the HERALD annual neural input
and the Ridge AR base component. This is required because the final prediction is `Ridge AR + neural
residual`; dropping a feature only from the residual branch would not be a valid feature ablation.

Labels and feature policies (9 configs):

| label | feature_policy | SIDE5 features kept |
|---|---|---|
| `side5_full` | `side5_full` | side_lag_1, side_lag_2, side_lag_3, growth_1y, growth_2y |
| `drop_lag1` | `side5_drop_lag1` | side_lag_2, side_lag_3, growth_1y, growth_2y |
| `drop_lag2` | `side5_drop_lag2` | side_lag_1, side_lag_3, growth_1y, growth_2y |
| `drop_lag3` | `side5_drop_lag3` | side_lag_1, side_lag_2, growth_1y, growth_2y |
| `drop_growth1y` | `side5_drop_growth1y` | side_lag_1, side_lag_2, side_lag_3, growth_2y |
| `drop_growth2y` | `side5_drop_growth2y` | side_lag_1, side_lag_2, side_lag_3, growth_1y |
| `lags_only` | `side5_lags_only` | side_lag_1, side_lag_2, side_lag_3 |
| `growth_only` | `side5_growth_only` | growth_1y, growth_2y |
| `lag1_growth1y` | `side5_lag1_growth1y` | side_lag_1, growth_1y |

Same architecture, hyperparameters, splits and panel as `best_simplified`. No manual flags, no source flags, no macro.

### Preflight audit

```bash
REGIME_PLAN=phase2i_side5_audit \
python3 hpc/regime/audit_herald_phase2i_side5_plan.py
```

### Smoke test

```bash
bash hpc/regime/smoke_test_phase2i_side5.sh
```

### Submit (after smoke passes)

```bash
STAMP=$(date +%Y%m%d_%H%M%S) \
bash hpc/regime/submit_herald_phase2i_side5.sh
```

The submit script enforces: bash -n syntax checks, py_compile, input file existence,
OUT_ROOT uniqueness, 9 × N_SEEDS run count, run_tag uniqueness, feature policy audit.

## Phase 2J — fair flag comparison

Goal: test whether HERALD without manual flags can match or beat HERALD with manual flags,
when both use the same clean input set (`side_lag_1 + growth_1y` only).

Status: completed. Root recovered locally:

```text
hpc_results/herald_regime_phase2j_fair_flag_20260518_170504_r1/
```

Hypothesis: the regime that HERALD learns internally (through the latent gate) approximates
the temporal regime that the researcher was previously providing manually as a methodological
shortcut (`is_covid_year`, `is_post_covid_rebound`). If the learned regime is sufficient, the
no-flags variant should perform comparably in 2021-2025, including the difficult 2021 fold.

Configs (2 configs × 10 seeds = 20 runs):

| label | regime_mode | variant | feature_policy | manual flags in inputs |
|---|---|---|---|---|
| `lag1_growth1y_nf` | `no_regime` | `learned_regime_gate_sector_enhanced` | `side5_lag1_growth1y` | NO |
| `lag1_growth1y_flags` | `manual_flags` | `full` | `side5_lag1_growth1y` | YES (`is_covid_year`, `is_post_covid_rebound`) |

Common inputs for both variants:
- SIDE features: `side_lag_1`, `growth_1y`
- Dropped: `side_lag_2`, `side_lag_3`, `growth_2y`, `flores_*`, `side_stock_*`
- Source flags: dropped (`no_source_flags`)
- Macro: none

The only difference between the two is the presence of 2 manual regime flags.

Phase 2J tags do not collide with Phase 2I (label suffix `_nf` and `_flags`).

Reference baselines for comparison table (from existing batteries):

| Model | WMAPE mean 2021-2025 | WMAPE 2021 | WMAPE 2025 | Source |
|---|---:|---:|---:|---|
| Ridge AR | 0.060652 | — | 0.036085 | strict exante no_source_flags |
| ARIMA local | — | — | 0.028898 | strict exante no_source_flags |
| LSTM local | — | — | 0.114935 | strict exante no_source_flags |
| DCRNN residual | 0.055283 | — | 0.031139 | strict exante no_source_flags |
| Dynamic STGNN residual | 0.055328 | — | 0.031853 | strict exante no_source_flags |
| HERALD no-flags SIDE5 (Phase 2I) | 0.024830 | 0.035664 | 0.014871 | Phase 2I side5_full |
| HERALD no-flags SIDE2 (Phase 2I) | 0.021323 | 0.034885 | 0.013004 | Phase 2I lag1_growth1y |
| HERALD no-flags SIDE2 (Phase 2J) | 0.020897 | 0.033931 | 0.012546 | Phase 2J lag1_growth1y_nf |
| HERALD flags SIDE2 clean (Phase 2J) | 0.028217 | 0.039469 | 0.012157 | Phase 2J lag1_growth1y_flags |
| HERALD flags étendu (Phase 2E) | 0.029163 | 0.034272 | 0.025466 | older control with broader inputs |

### Preflight audit

```bash
python3 hpc/regime/audit_herald_phase2j_fair_flag.py
```

## Phase 2K — latent-regime dimension audit

Goal: test whether the current learned latent regime vector of size 3 is a useful capacity choice or
an implicit conditioning that encourages a false "three economic reactions" interpretation.

Important methodological rule:

- `latent_dim = 3` is an architecture hyperparameter, not evidence that the market has 3 regimes.
- Do not claim "3 regimes discovered" unless a model-selection or effective-dimension audit supports it.

Code impact:

- In the current Phase 2J candidate (`learned_regime_gate_sector_enhanced`), the learned latent vector
  mainly affects `alpha`, the local-vs-graph mixture.
- In `learned_regime_graph*` or `learned_regime_both*`, the same latent vector also affects the
  dynamic graph `A_t`.

Planned configs:

| Label family | Latent sizes | Variant | Purpose |
|---|---:|---|---|
| `L*_gate` | 1, 2, 3, 4, 5 | `learned_regime_gate_sector_enhanced` | test alpha/gate sensitivity |
| `L*_both` | 1, 2, 3, 4 | `learned_regime_both_sector_enhanced` | test alpha + graph sensitivity |
| `AUTO5_l1_*` | max 5 | masked latent with L1 penalty | let HERALD deactivate unused dimensions |

Decision rule: prefer the smallest or auto-regularized latent representation that matches the Phase
2J no-flags candidate without degrading 2025, A10, or seed stability.

Planning report:

```text
reports/HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md
```

### Smoke test

```bash
bash hpc/regime/smoke_test_phase2j_fair_flag.sh
```

### Submit (after smoke passes)

```bash
STAMP=$(date +%Y%m%d_%H%M%S) \
bash hpc/regime/submit_herald_phase2j_fair_flag.sh
```

The submit script enforces: bash -n syntax checks, py_compile, input file existence,
OUT_ROOT uniqueness, 2 × N_SEEDS run count, tag uniqueness, tag non-collision with Phase 2I,
feature policy audit.

### Post-run: aggregate and audit

```bash
# After rsync from HPC:
rsync -av meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald_regime_phase2j_fair_flag_<STAMP>_r1/ \
  hpc_results/herald_regime_phase2j_fair_flag_<STAMP>_r1/

python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_regime_phase2j_fair_flag_<STAMP>_r1

python3 hpc/regime/audit_herald_phase2j_fair_flag.py
```
