# Dataset Candidate Matrix v0

Date : 2026-04-21

## Current leader

- Best current new candidate: `rei_cfe_microentrepreneurs_created_n_1_lag_1`
- Result vs `ridge_lag_nbcom`:
  - baseline: `7.649`
  - candidate: `6.699`
- Practical reading:
  - strong improvement in `2023`
  - improvement in `2024`
  - `2021` and `2022` are effectively unchanged

## Matrix

| Family | Current status | Best tested signal | Read on usefulness |
| :--- | :--- | :--- | :--- |
| `REI/CFE` | `leader` | `rei_cfe_microentrepreneurs_created_n_1_lag_1` | Best new exogenous source so far. Captures hub regime change better than spatial or light panel signals. |
| `Energy` | `tested, rejected for now` | `energy_electricity_pdl_nonres_lag_1` | Full coverage, but behaved like a noisy size/intensity proxy. Worsened `2021` and `2024`. |
| `RP employment` | `tested, rejected for now` | `unemployment_rate_est_lag_1` | Least redundant RP candidate still failed. Did not solve weak years. |
| `BPE` | `already tested, weak` | `bpe_evolution_commune_type_presence_total_lag_1` | Some structural signal, but not enough and too weak for the short-baseline phase. |
| `FILOSOFI` | `already tested, weak` | `filosofi_s_dir_tax_di_weighted_proxy_lag_1` | Coverage usable, but signal weak and not robust. |
| `FLORES` | `not useful now` | none | Current processed form is effectively unusable for this phase. |
| `ZAN` | `not prioritized` | none in this round | More structural/slow-moving. Better for future structural analysis than short-baseline correction. |
| `SITADEL` | `partially processed, low return so far` | `sitadel_surface_commencee_lag_1` | Processed annualized versions already failed in short-baseline tests. Heavy monthly communal raw data remains a future option. |
| `Population / stocks / size proxies` | `already rejected` | `pop_lag_1`, `stock_lag_1`, `total_establishments` | Mostly redundant with the baseline or actively harmful. |
| `Graph / spatial` | `closed for now` | none | Linear, gated, and minimal nonlinear versions all failed. |

## What each family may still help with later

- `REI/CFE`
  - leading signal for entrepreneurial regime change in hubs
  - current best operational form is the simple raw `created_n_1` lag
  - light variants checked so far (`hub` interaction, broader local REI blocks, `log1p`) did not show a more robust replacement

- `Energy`
  - may still help as structural intensity or sector-shift signal
  - more suitable for later derived ratios or structural diagnostics than immediate short-baseline use

- `RP employment`
  - useful for interpretation of local labor-market context
  - not currently a strong direct additive predictor

- `BPE`
  - useful for long-run ecosystem structure
  - not convincing as a short-run corrective signal

- `FILOSOFI`
  - useful for socio-economic interpretation and heterogeneity analysis
  - weak as a direct short-baseline feature in current form

- `ZAN`
  - useful for land-use / structural territorial narrative
  - probably too slow-moving for the current short-baseline problem

- `SITADEL`
  - still has future value if the heavy monthly communal source is processed carefully
  - not justified as the next immediate test before REI is exhausted

## Decision now

- Next formal source to prioritize: `REI/CFE`
- Best specific feature today: `rei_cfe_microentrepreneurs_created_n_1_lag_1`
- Immediate second-tier families:
  - `BPE`
  - `FILOSOFI`
- Deferred:
  - `Energy`
  - `RP employment`
  - `ZAN`
  - heavy `SITADEL` monthly communal processing
