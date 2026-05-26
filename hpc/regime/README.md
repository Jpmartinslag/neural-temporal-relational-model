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
| Phase 2H | macro INSEE/Banque de France | completed | macro not retained; `best_simplified` won that stage |
| Phase 2I | SIDE 5-feature audit | completed | `lag1_growth1y` wins: WMAPE mean 0.021323 |
| Phase 2J | fair flag comparison | completed | no-flags SIDE2 beats clean manual-flags SIDE2 |
| Phase 2K | latent-regime dimension audit | completed | fixed larger latent helped; auto-size did not select cleanly |
| Phase 2L-2N | auto-regulation / internal auditor | completed | useful diagnostics, no main-candidate promotion |
| Phase 2O-2Q | residual shrinkage and robustness | completed | residual calibration became the strongest direction |
| Phase 2R | confirmatory battery | completed | `L5_trainopt` confirmed vs no-calibration control |

## Canonical candidate after Phase 2R

`L5_trainopt` is the current HERALD-France candidate.

Annual features:

- `side_lag_1`
- `growth_1y`

Mechanism:

- Ridge baseline;
- neural residual correction;
- no manual crisis/rebound flags;
- no source flags;
- residual calibration estimated from training years only.

Phase 2R metrics:

- mean WMAPE 2021-2025: `0.020233`
- WMAPE 2021: `0.035020`
- WMAPE 2025: `0.012525`
- A10 WMAPE: `0.158238`
- paired vs no-calibration control: `17/20` wins, `p=0.002818`

Combined audit:

```text
reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md
reports/metrics/herald_phase2r_summary.csv
reports/metrics/herald_phase2r_paired_vs_l5_gate.csv
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
| `submit_herald_phase2k_latent_dim.sh` | `phase2k_latent_dim` |
| `submit_herald_phase2l_latent_dim_wide.sh` | `phase2l_latent_dim_wide` |
| `submit_herald_phase2m_latent_autoreg.sh` | `phase2m_latent_autoreg_strong` |
| `submit_herald_phase2n_internal_auditor.sh` | `phase2n_internal_auditor` |
| `submit_herald_phase2o_residual_shrinkage.sh` | `phase2o_residual_shrinkage` |
| `submit_herald_phase2p_hc_auditor_interaction.sh` | `phase2p_hc_auditor_interaction` |
| `submit_herald_phase2q_input_arch_robustness.sh` | `phase2q_input_arch_robustness` |
| `submit_herald_phase2r_confirmatory.sh` | `phase2r_confirmatory` |

Smoke tests:

| Script | Purpose |
|---|---|
| `smoke_test_phase2d.sh` | phase 2D CPU/GPU sanity |
| `smoke_test_phase2e.sh` | phase 2E sanity |
| `smoke_test_phase2g_feature_noise.sh` | feature-policy sanity |
| `smoke_test_phase2h_macro.sh` | macro-panel sanity |
| `smoke_test_phase2i_side5.sh` | Phase 2I SIDE5 sanity (9 configs) |
| `smoke_test_phase2j_fair_flag.sh` | Phase 2J fair flag sanity (2 configs) |
| `smoke_test_phase2k_latent_dim.sh` | Phase 2K latent dim sanity (5 configs) |

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

Status: **ready to launch** — code implemented, smoke and submit scripts ready.

Important methodological rule:

- `latent_dim = 3` is an architecture hyperparameter, not evidence that the market has 3 regimes.
- Do not claim "3 regimes discovered" unless a model-selection or effective-dimension audit supports it.

Code changes (Phase 2K):

- `HERALDv7Residual` accepts `latent_regime_dim` (default `base.REGIME_DIM=3`) and `auto_mask=False`.
- `latent_proj_q` / `latent_proj_k` (size `latent_regime_dim`) drive the dynamic graph for `learned_regime_both*`.
- `regime_proj_q` / `regime_proj_k` (size `base.REGIME_DIM=3`) keep backward compat for explicit regime.
- `alpha_gate` input size adapts to `latent_regime_dim` (no compat break since no checkpoint loading).
- Auto-mask: `mask_logits` parameter; `z_eff = z * sigmoid(mask_logits)`; L1 term in loss.
- `--latent-regime-dim`, `--latent-dim-l1-lambda`, `--latent-dim-auto-mask` CLI args added to `train_herald_semi_v2.py`.
- Result JSON includes `latent_regime_dim`, `latent_dim_auto_mask`, `latent_dim_l1_lambda`,
  `latent_dim_mask_values`, `latent_dim_effective_dim`.

Configs (13 × 10 seeds = 130 runs):

| Label | latent_dim | Variant | auto_mask | Purpose |
|---|---:|---|---|---|
| `L1_gate` | 1 | `learned_regime_gate_sector_enhanced` | no | H1: minimal latent |
| `L2_gate` | 2 | `learned_regime_gate_sector_enhanced` | no | H1: small latent |
| `L3_gate` | 3 | `learned_regime_gate_sector_enhanced` | no | reference (= Phase 2J no-flags) |
| `L4_gate` | 4 | `learned_regime_gate_sector_enhanced` | no | H2: higher capacity |
| `L5_gate` | 5 | `learned_regime_gate_sector_enhanced` | no | H2: overcapacity test |
| `L1_both` | 1 | `learned_regime_both_sector_enhanced` | no | H3: latent affects graph |
| `L2_both` | 2 | `learned_regime_both_sector_enhanced` | no | H3: latent affects graph |
| `L3_both` | 3 | `learned_regime_both_sector_enhanced` | no | H3: reference + graph |
| `L4_both` | 4 | `learned_regime_both_sector_enhanced` | no | H3: higher graph capacity |
| `L5_both` | 5 | `learned_regime_both_sector_enhanced` | no | H3: overcapacity + graph |
| `AUTO5_l1_001` | 5 | `learned_regime_gate_sector_enhanced` | yes | H4/H5: light selection |
| `AUTO5_l1_005` | 5 | `learned_regime_gate_sector_enhanced` | yes | H4/H5: medium selection |
| `AUTO5_l1_010` | 5 | `learned_regime_gate_sector_enhanced` | yes | H4/H5: strong selection |

All configs: `no_regime`, `no_source_flags`, `side5_lag1_growth1y`, `sector_lambda=0.2`.

Decision rule: prefer the smallest or auto-regularized latent representation that matches
Phase 2J no-flags candidate without degrading 2025, A10, or seed stability.

Hypotheses:

- H1: `latent_dim=1` or `2` matches `L3_gate` → dim 3 not necessary.
- H2: `L4/L5` add instability without improving WMAPE mean.
- H3: `_both` variants show larger `adj_delta` than `_gate` at the same dim.
- H4: auto-mask learns to deactivate unused dimensions.
- H5: `AUTO5` with 1-2 effective dims keeps performance → more defensible than fixed dim 3.

Planning report:

```text
reports/HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md
```

### Smoke test

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
bash hpc/regime/smoke_test_phase2k_latent_dim.sh
```

Smoke validates: L1_gate, L3_gate, L5_gate, L3_both, AUTO5_l1_005 — 1 epoch, 1 seed.
Checks artifacts, `latent_regime_dim` in JSON, mask_values and effective_dim for AUTO5.

### Submit (after smoke passes)

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
STAMP=$(date +%Y%m%d_%H%M%S) \
bash hpc/regime/submit_herald_phase2k_latent_dim.sh
```

OUT_ROOT: `hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1`

Submit enforces: bash -n syntax checks, py_compile, input file existence,
OUT_ROOT uniqueness, 13 × N_SEEDS run count, tag uniqueness, tag non-collision with Phase 2J.

### Post-run: aggregate and audit

```bash
rsync -av meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1/ \
  hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1/

python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1

python3 hpc/regime/audit_herald_phase2k_latent_dim.py \
  --root hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1
```

## Phase 2N — internal auditor

Goal: test real self-regulation with a year-by-year confidence signal. This is different from
Phase 2M masks: the auditor is conditioned on the current hidden state and can reduce how much the
learned latent regime affects the gate/alpha for a specific year.

What changes:

- `--auditor-mode none|latent_scale|alpha_neutral|both`
- `latent_scale`: scales the learned latent regime before it enters the gate.
- `alpha_neutral`: pulls alpha toward `0.5` when confidence is low.
- `both`: applies both controls.
- `--auditor-budget-lambda`: small pressure to lower confidence when the auditor is not useful.
- `--auditor-smooth-lambda`: optional smoothness to avoid year-to-year jitter.

Configs: 11 × 10 seeds = 110 runs.

References:

- `L3_gate`: best simple 2021 reference from latent-dim work.
- `L5_gate_no_auditor`: clean dimension-5 control. Required to isolate the auditor effect.
- `HC5_l0_050`: best Phase 2M mean/2025 reference.
- `L4_a10g`: best A10 reference.

Auditor variants:

- `AUD_lat_b001`, `AUD_lat_b005`
- `AUD_alpha_b001`, `AUD_alpha_b005`
- `AUD_both_b001`, `AUD_both_b005`, `AUD_both_b001_s010`

Decision rule:

- Main auditor comparison must be against `L5_gate_no_auditor`, not only `L3_gate`.
- Pass only if it improves or matches mean WMAPE while not degrading 2021 and A10.
- Auditor confidence must vary by year; all-ones or all-zeros means no useful autonomy.

Smoke:

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
bash hpc/regime/smoke_test_phase2n_internal_auditor.sh
```

Submit:

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
STAMP=$(date +%Y%m%d_%H%M%S) \
bash hpc/regime/submit_herald_phase2n_internal_auditor.sh
```

## Phase 2O-2Q — next non-redundant batteries

Canonical plan: `reports/HERALD_PHASE2O_2P_2Q_PLAN.md`.

These phases intentionally avoid another broad latent-dimension or hard-concrete sweep.
They test three distinct questions:

- `phase2o_residual_shrinkage`: should the learned residual correction be shrunk or
  selected fold-by-fold against Ridge?
- `phase2p_hc_auditor_interaction`: does HC5's mean/2025 gain combine with auditor
  gains on 2021/A10?
- `phase2q_input_arch_robustness`: do the best architectures survive across clean
  input policies?

Shared submit template:

- `hpc/regime/submit_herald_phase_template.sh`

Phase submit commands:

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset

STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/regime/submit_herald_phase2o_residual_shrinkage.sh
STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/regime/submit_herald_phase2p_hc_auditor_interaction.sh
STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/regime/submit_herald_phase2q_input_arch_robustness.sh
```

Default run counts:

- Phase 2O: 9 configs × 10 seeds = 90 runs.
- Phase 2P: 8 configs × 10 seeds = 80 runs.
- Phase 2Q: 9 configs × 10 seeds = 90 runs.

The submit template checks shell syntax, Python compilation, input files, expected
run count, duplicate tags, and OUT_ROOT uniqueness before calling Slurm. By default
it excludes `hpcgpu02` because prior Phase 2N failures were node-local.

## Phase 2R — confirmatory battery

Phase 2R freezes the candidate set after 2O/2P/2Q. It is not another broad
search. It tests whether the main claim survives with more seeds and fair
controls in the same run.

Main question:

- does `L5_trainopt` provide a robust no-flags HERALD result: Ridge baseline
  plus neural residual correction calibrated from training years only?

Controls included:

- `ridge_side2`: Ridge-only fallback in the same HERALD pipeline;
- `L5_gate_no_auditor`: no-flags, no shrinkage control;
- `L3_gate`: legacy 2021-oriented control;
- `HC5_trainopt`: best raw mean/2025 trade-off from 2O;
- `AUD_alpha_trainopt`, `AUD_both_trainopt`, `side2_AUDboth`: auditor/stability controls;
- `L4_a10g`: A10 guard comparison;
- `clean_flags_side2`, `clean_flags_side2_trainopt`: manual flags with the same clean SIDE2 inputs;
- `extended_flags_current`, `extended_flags_current_trainopt`: historical broader flag controls.

Submit:

```bash
cd ~/project_recomm_herald_v6_2025_20260430/dataset
STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/regime/submit_herald_phase2r_confirmatory.sh
```

Default run count:

- Phase 2R: 13 configs × 20 seeds = 260 runs.

Audit after completion:

```bash
python3 hpc/regime/aggregate_herald_regime_results.py --root <OUT_ROOT>
python3 hpc/regime/audit_herald_phase2r_confirmatory.py --root <OUT_ROOT> --strict
```
