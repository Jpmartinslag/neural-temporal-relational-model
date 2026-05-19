# HERALD — Latent Regime Dimension Battery Plan

Date: 2026-05-19

Status: planning document. Do not use as empirical evidence before the battery is run.

## 1. Problem

The current no-flags HERALD uses a learned latent regime vector with dimension 3.

This is useful as model capacity, but it creates a methodological risk:

> A 3-dimensional latent vector must not be interpreted as proof that the economy has 3 regimes, 3 waves, or 3 reaction types.

The dimension is currently an architectural choice. It is not, by itself, a discovered economic fact.

## 2. Methodological Position

Using a fixed latent dimension is acceptable if it is treated as a hyperparameter and validated.

It is not acceptable to claim:

- "HERALD discovered 3 market reactions" only because `REGIME_DIM = 3`;
- "the three latent coordinates correspond to three economic waves" without post-hoc evidence;
- "the model selected 3 regimes" unless the architecture explicitly contains a model-selection mechanism.

Correct wording:

- "HERALD uses a compact latent regime representation."
- "We test whether latent dimensions 1, 2, 3, or 4 improve predictive stability."
- "The effective dimensionality is audited by ablation and variance analysis."

## 3. What the Code Does Today

In `src/modeles/train_herald_v6.py`, `REGIME_DIM = 3`.

In `src/modeles/train_herald_v7.py`, the V7 model imports `base.REGIME_DIM`, so the latent dimension also resolves to 3.

The learned latent regime affects two parts of the model:

1. Local-vs-graph mixture `alpha`

   In `learned_regime_gate*` variants, the latent vector enters `alpha_gate`.

   Effect:
   - alpha close to 1: more local/Ridge residual correction;
   - alpha close to 0: more graph correction.

2. Dynamic graph `A_t`

   In `learned_regime_graph*` and `learned_regime_both*` variants, the latent vector enters the dynamic attention query/key shift used to build `A_t`.

   Effect:
   - the same zones can receive different learned connections depending on the latent regime;
   - therefore changing the latent dimension can change the learned graph.

Current Phase 2J uses `learned_regime_gate_sector_enhanced`, so the learned regime mainly affects `alpha`, not the graph construction itself. If we test `learned_regime_both_sector_enhanced`, it affects both `alpha` and `A_t`.

## 4. Research Questions

Q1. Is latent dimension 3 necessary?

Q2. Does a smaller latent vector, such as 1 or 2, keep the same performance with less methodological risk?

Q3. Does a larger latent vector, such as 4 or 5, improve prediction or only add instability?

Q4. Does the latent vector change only the local/graph arbitration, or does it also create materially different learned graphs?

Q5. Can HERALD learn to ignore unnecessary latent dimensions?

## 5. Battery A — Fixed Latent Dimension

Keep the current clean comparison setup:

- no manual flags;
- feature policy: `side5_lag1_growth1y`;
- no source flags;
- no macro features;
- 10 seeds;
- same folds and evaluation as Phase 2J.

Configs:

| Label | latent_dim | Variant | Purpose |
|---|---:|---|---|
| L1_gate | 1 | learned_regime_gate_sector_enhanced | Minimal latent scalar |
| L2_gate | 2 | learned_regime_gate_sector_enhanced | Small latent vector |
| L3_gate | 3 | learned_regime_gate_sector_enhanced | Current no-flags reference |
| L4_gate | 4 | learned_regime_gate_sector_enhanced | Higher capacity |
| L5_gate | 5 | learned_regime_gate_sector_enhanced | Stress test for overcapacity |

Optional graph-sensitive extension:

| Label | latent_dim | Variant | Purpose |
|---|---:|---|---|
| L1_both | 1 | learned_regime_both_sector_enhanced | Latent affects alpha and graph |
| L2_both | 2 | learned_regime_both_sector_enhanced | Latent affects alpha and graph |
| L3_both | 3 | learned_regime_both_sector_enhanced | Current size, graph-sensitive |
| L4_both | 4 | learned_regime_both_sector_enhanced | Higher graph capacity |

Minimum run count:

- 5 configs x 10 seeds = 50 runs for gate-only.
- 9 configs x 10 seeds = 90 runs if graph-sensitive extension is included.

## 6. Battery B — Auto-Regularized Latent Dimension

Goal: allow HERALD to carry a larger latent vector but penalize unused dimensions so the effective size is learned.

Candidate mechanism:

1. Set maximum latent size: `latent_dim_max = 5`.
2. Add a learned dimension mask:

   `z_eff = z * sigmoid(mask_logits)`

3. Penalize active dimensions:

   `loss += latent_dim_l1_lambda * mean(sigmoid(mask_logits))`

4. Audit effective dimension:

   `effective_dim = sum(sigmoid(mask_logits) > 0.2)`

This does not prove an economic number of regimes, but it tests whether the model can ignore unnecessary latent coordinates.

Configs:

| Label | latent_dim_max | Penalty | Purpose |
|---|---:|---:|---|
| AUTO5_l1_001 | 5 | 0.001 | Light dimension selection |
| AUTO5_l1_005 | 5 | 0.005 | Medium dimension selection |
| AUTO5_l1_010 | 5 | 0.010 | Strong dimension selection |

Minimum run count:

- 3 configs x 10 seeds = 30 runs.

## 7. Required Metrics

Predictive metrics:

- WMAPE mean 2021-2025;
- WMAPE by year;
- WMAPE 2021;
- WMAPE 2025;
- A10 WMAPE;
- wins/losses by seed vs Phase 2J no-flags reference;
- wins/losses by seed vs Phase 2J clean flags.

Latent metrics:

- latent variance per dimension;
- PCA explained variance;
- dimension-wise ablation: zero one coordinate at inference and measure delta WMAPE;
- latent_step 2020->2021 by fold;
- seed stability of the latent trajectory.

Graph metrics:

- if using `learned_regime_both*`, compare `adj_delta_by_year`;
- top-k edge overlap across dimensions and seeds;
- graph difference vs L3 reference;
- alpha vs graph-change correlation.

## 8. Decision Rule

Prefer the smallest latent dimension that:

1. matches or improves WMAPE mean;
2. does not degrade WMAPE 2025;
3. does not degrade A10;
4. is at least as stable across seeds;
5. has interpretable and non-degenerate latent usage.

If L1 or L2 matches L3, use L1 or L2.

If L4 or L5 improves only one year but worsens stability, reject.

If auto-regularization selects 1-2 active dimensions and keeps performance, prefer it over fixed `latent_dim=3`.

## 9. Dashboard Language

Avoid:

- "3 regimes discovered";
- "3 economic waves";
- "3 market reactions".

Use:

- "latent regime representation";
- "effective latent dimension";
- "learned temporal adjustment";
- "active latent coordinates".

## 10. Implementation Notes

Current code change needed:

1. Replace hardcoded use of `base.REGIME_DIM` in V7 with `args.regime_dim` or `args.latent_regime_dim`.
2. Keep manual flags compatibility by projecting manual 3D vectors into the selected latent size only for no-flags variants, or restrict this battery to no-flags only.
3. Save metadata:
   - `latent_regime_dim`;
   - `latent_dim_max`;
   - active mask values if auto-regularized;
   - per-dimension variance;
   - per-dimension ablation deltas.
4. Do not change Phase 2J outputs. Use a new root, e.g.:

   `hpc_results/herald_regime_phase2k_latent_dim_<STAMP>_r1`

