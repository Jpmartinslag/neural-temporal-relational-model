# HERALD Synthetic Controlled Benchmark — Contract

**Decision:** DEC-039
**Date:** 2026-06-13
**Phase:** Phase 9 — Generalisation validation with controlled synthetic data
**Authority:** This contract is pre-specified and sealed before any model is trained.

---

## Hypothesis

This experiment tests whether graph-aware imputation (HERALD) provides measurable gains
over simpler baselines when recovering missing economic panel labels with known ground truth.
**The hypothesis may be refuted.** No assumption is made that neural or graph-based models
will outperform simple baselines.

---

## Primary hypothesis

> H1 — Imputation: HERALD-graph achieves strictly lower MAE than the best non-graph baseline
> on at least 2 of 3 masking mechanisms (MCAR, MAR, block).

> H2 — Relation recovery: The attention weights learned by HERALD identify true sector-sector
> edges with AUC > 0.60 (random baseline AUC = 0.50, permuted graph < 0.55).

> H3 — Calibration: 90% prediction intervals achieve ≥ 80% empirical coverage.

---

## PASS / FAIL gates

| Gate | Threshold | Failure mode |
|------|-----------|--------------|
| G1: MAE improvement | MAE_graph ≤ MAE_best_baseline × 0.95 on ≥ 2/3 mechanisms | FAIL: HERALD does not advance for imputation claims |
| G2: AUC edge recovery | AUC > 0.60 averaged over seeds | FAIL: graph not learning useful structure |
| G3: Permuted graph worse | MAE_permuted ≥ MAE_graph × 1.00 (permuted must not beat true graph) | FAIL: model ignores graph, attention is noise |
| G4: Calibration | 90% interval coverage ≥ 80% | FAIL: uncertainty not calibrated |
| G5: No leakage | Temporal features use only t′ < t; verified by test | FAIL: architecture is invalid |
| G6: No false promotion | False positive rate for edge recovery ≤ 30% | FAIL: model generates spurious structure |

**Minimum criterion (from protocol):** HERALD advances only if G1 PASS OR G2 PASS, AND G5 PASS
(no leakage), AND G3 PASS (permuted graph does not win).

---

## Data generating process

- `n_territories` ∈ {10 (smoke), 30 (full)}
- `n_sectors` ∈ {5 (smoke), 9 (full)}
- `n_years` ∈ {12 (smoke), 20 (full)}
- Seeds: 2 (smoke), 10 (full)
- True sector-sector relations: ~20% density, lags 1-2, positive and negative, some nonlinear
- True territory adjacency: geometric random graph
- Regimes: growth, stagnation, decline, crisis+recovery, sectoral waves, structural break
- Masking mechanisms: MCAR, MAR (biased toward extreme values), block-temporal
- Masking levels: 10%, 20%, 30%

---

## Baselines

| # | Baseline | Graph? |
|---|---------|--------|
| B1 | Global mean | — |
| B2 | Series median (temporal) | — |
| B3 | Forward fill (causal) | — |
| B4 | Causal temporal interpolation | — |
| B5 | Ridge on temporal features | — |
| B6 | Neural MLP on temporal features | No |
| B7 | HERALD: neural + sector+territory graph | Yes (learned) |
| B8 | HERALD control: permuted adjacency | Permuted |

All baselines: explicit masks, no impute-zero, causal temporal features only.

---

## Evaluation metrics

- **Imputation:** MAE, RMSE, Pearson r, sign accuracy (at masked positions only)
- **State:** economic state classification accuracy (growth / stagnation / decline / recovery)
- **Relation recovery:** AUC, precision@k, recall@k, F1 for sector-sector true edges
- **Calibration:** coverage at 50%, 80%, 90% prediction intervals
- **Leakage check:** automated test asserting causal feature construction

---

## Smoke test specification

```
n_territories=10, n_sectors=5, n_years=12
n_seeds=2
masking: MCAR 20% only
baselines: B1, B3, B5, B6, B7, B8
epochs: 100
expected runtime: < 3 minutes local CPU
```

Smoke PASS: all baselines produce valid output; no NaN in predictions; leakage test passes.
Smoke does NOT need to satisfy G1–G4 (too small). Smoke validates architecture only.

---

## Scope limits

- No real data touched in this task.
- No HPC submission without smoke PASS and exact command agreed.
- No claim that HERALD solves missing data; experiment demonstrates or refutes.
- Structural breaks and non-linear dynamics are in the generator; whether HERALD recovers
  them is determined by the results, not asserted in advance.
