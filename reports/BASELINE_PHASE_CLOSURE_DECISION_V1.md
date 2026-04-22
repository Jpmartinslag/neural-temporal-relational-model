# Baseline Phase Closure Decision v1

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date: 2026-04-21

## Objective

Freeze the current short-baseline phase after the extended temporal, spatial, regime, and external-source checks.

This version supersedes the operational baseline choice in `BASELINE_PHASE_CLOSURE_DECISION_V0.md`.

## Closed Decisions

| Topic | Decision | Status |
| :--- | :--- | :--- |
| Target | Official `SIDE` establishment creations aggregated to `ZE2020` | Operational target |
| Conservative baseline | `persistence` | Operational sanity baseline |
| Former short benchmark | `ridge_lag_only` | Historical reference |
| Interim short benchmark | `ridge_lag_nbcom` | Historical reference |
| Current main short benchmark | `side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1` | Operational baseline candidate promoted |
| Geographic graph | Not useful in current linear/minimal nonlinear tests | Closed for now |
| Mobility graph | Not useful in current simple tests | Closed for now |
| Energy features | Tested, not promoted | Diagnostic only |
| RP employment features | Tested, not promoted | Diagnostic only |
| BPE / FILOSOFI light features | Tested, not promoted | Diagnostic only |
| Monthly SITADEL heavy variants | Deferred backup path | Not immediate priority |

## Operational Baselines

Current operational references:

- `rei_created_baseline`: `side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1`
- `ridge_lag_nbcom`: previous validated short baseline, kept as reference
- `persistence`: conservative sanity baseline

Observed mean WMAPE:

- `rei_created_baseline`: `6.699%`
- `ridge_lag_nbcom`: `7.649%`
- `ridge_lag_only`: `7.664%`
- `persistence`: `7.680%`

Per-year comparison vs `ridge_lag_nbcom`:

- `2021`: equal within numerical tolerance
- `2022`: equal within numerical tolerance
- `2023`: strong improvement
- `2024`: improvement

Decision rule:

- Promotion is accepted with numerical tolerance because no year worsens beyond tolerance and the mean improvement is material.

## What Was Rejected

Rejected for current operational use:

- geographic linear blends
- graph-derived tabular spatial covariates
- learned linear geo mixing
- gated linear geo mixing
- minimal nonlinear geo mixing
- generic hub shrinkage rules
- causal segmented hub rule based on recent momentum only
- tested light energy features
- tested RP employment feature
- tested BPE / FILOSOFI light additions

## Interpretation

The main weak years (`2022–2023`) were driven by overprediction in large hubs.

The best new signal was not graph structure and not a size proxy. It was:

- prior-year microentrepreneur creation flow from `REI/CFE`

This signal improves the exact subset that was causing the previous baseline to fail, especially hubs in `2023`.

## Queue After Closure

Immediate next priority:

1. Use `rei_created_baseline` as the official reference for the next phase

Deferred / backup:

2. monthly communal `SITADEL` H1 lag variant only if a backup exogenous source is needed

Later:

3. `SIRENE`
4. deeper structural uses of energy / ZAN / BPE / FILOSOFI

## Final Closure Statement

The short-baseline phase is now sufficiently closed for forward progress.

The strongest validated short reference is no longer the pure temporal ridge baseline. It is the REI-augmented baseline:

- `side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1`

Future experiments should beat this reference, not `ridge_lag_only`.
