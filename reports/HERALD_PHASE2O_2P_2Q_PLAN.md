# HERALD Phase 2O-2Q Plan

Date: 2026-05-25

## Why This Exists

Phase 2K-2N answered an important question: global latent-size self-selection is not working as a reliable form of autonomy. Hard-concrete and related masks behaved more like regularizers than true dimension selectors.

The next batteries therefore avoid another wide latent/L0 grid. They test three non-redundant questions:

1. Can HERALD decide how strongly to trust its neural residual correction?
2. Can the HC5 regularizer and the internal auditor complement each other?
3. Are the best architectures robust across clean input policies, or are we selecting an accidental feature/model pair?

All phases keep:

- no manual COVID/rebound flags;
- no source flags;
- no macro features;
- forecast-safe lagged inputs;
- paired seeds.

## Phase 2O — Residual Shrinkage

Hypothesis: HERALD should not always apply the full neural correction on top of Ridge. A small causal shrinkage rule can fall back toward Ridge when the residual branch is risky.

Mechanisms:

- `fixed`: multiply the learned residual by a fixed lambda, e.g. `0.50` or `0.75`;
- `train_opt`: choose lambda per fold using only training years, never the target year.

Controls:

- `L3_gate`
- `L5_gate_no_auditor`
- `HC5_l0_050`
- `L4_a10g`

Victory condition:

- improve or match `L5_gate_no_auditor` on mean WMAPE;
- not degrade 2021;
- not degrade A10;
- chosen shrinkage lambdas must vary sensibly by fold, not always hit one boundary.

## Phase 2P — HC5 + Auditor Interaction

Hypothesis: HC5 gave the best average/2025 behaviour, while the auditor helped more on 2021/A10. The useful model may be their interaction, not either alone.

Tested hybrids:

- `HC5_alpha_b001`
- `HC5_both_b001`
- `HC5_both_b001_s010`

Victory condition:

- beat both `L5_gate_no_auditor` and `HC5_l0_050` on mean WMAPE;
- not worsen 2021;
- not worsen A10;
- auditor confidence must not collapse to all-zero or all-one.

## Phase 2Q — Input Policy × Architecture Robustness

Hypothesis: the gain must survive across clean input policies. If an architecture only wins with one input policy, it is probably brittle.

Input policies:

- `side5_lag1_growth1y`;
- `minimal_side_only`;
- `no_flores_no_side_stock_a10`.

Architectures:

- `L5`;
- `HC5`;
- `AUDboth`.

Victory condition:

- architecture wins or ties in at least two of three input policies;
- input policy wins or ties in at least two architectures;
- no hidden source/manual flags are present.

## Explicit Non-Goals

Do not reopen these now:

- more latent-dimension grids;
- more hard-concrete lambda-only sweeps;
- `latent_scale`;
- manual event flags;
- macro features mixed with auditor tests;
- broad drop-one feature batteries.

