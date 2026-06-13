# HERALD Phase 10 — Signal Sensitivity Experiment

**Reference:** DEC-044  
**Date:** 2026-06-13  
**Status:** CONTRACT FROZEN — gates S1-S7 written before execution

---

> **Isolation guarantee:** This experiment is distinct from Phase 10 (DEC-043).
> It does NOT substitute, reclassify, or modify PHASE10_PARTIAL.
> Results here are labeled PHASE10_SIGNAL_SENSITIVITY and tracked separately.

---

## 1. Motivation

Phase 10 (PHASE10_PARTIAL) found that herald_lagged achieves AUC improvement (+70% relative) but MAE improvement below the L3 threshold (+1–2.4%). The core question is:

> **Is the +1–2% MAE improvement a fundamental ceiling given the AR dynamics, or does it increase when cross-sector signal is stronger?**

If stronger cross-sector signal yields larger MAE gains, the architecture is correct and L3 failure is a data-generation choice, not an architectural defect. If not, the model does not translate edge recovery into imputation utility under any signal regime.

---

## 2. Experiment Grid

| Axis | Levels | Values |
|------|--------|--------|
| cross_sector_force | low / original / high | weight_range: (0.1,0.3) / (0.4,0.8) / (0.8,1.2) |
| AR | low / original / high | ar_coef_range: (0.1,0.3) / (0.3,0.6) / (0.5,0.8) |
| noise | low / original | noise_sigma_range: (0.05,0.10) / (0.08,0.18) |
| lag | lag1 / lag2 / mixed | forced_lag: 1 / 2 / None |
| scenario | linear / nonlinear_heavy | — |
| seed | 42 / 123 / 456 | — |
| mask | mcar_30 / block_30 | 30% missingness |

**Total tasks:** 3 × 3 × 2 × 3 × 2 × 3 = 324  
**Models per task × mask:** 7 (ffill, ridge, no_graph, herald_contemp, herald_lagged, herald_lagged_permuted, oracle_lagged)

### Notes on grid axes

- `cross_sector_force=high` (weight_range 0.8–1.2) is out-of-distribution for the benchmark. This is intentional — it tests the architecture's upper envelope.
- `AR=low` (φ∈[0.1,0.3]) reduces the AR(1) dominance, making cross-sector effects more salient.
- `lag=lag1 / lag2` forces all true relations to a single lag, making the oracle match cleaner.
- `block_30`: block masking (contiguous missingness) is the most structurally informative for graph imputation.

---

## 3. Gates S1-S7 (frozen 2026-06-13, before any execution)

These gates are immutable. They were written BEFORE any sensitivity results were observed.  
The gate evaluator is in `src/modeles/synthetic/gates_sensitivity.py` (version: `sensitivity_gates_v1`).

### S1: Oracle upper bound
**oracle_lagged MAE < ffill AND oracle_lagged MAE < no_graph**

The oracle (directed attention frozen, MLP trained) must provide imputation benefit over both the trivial baseline (ffill) and the graph-free neural model. Failure = the graph structure is not exploitable for imputation even under perfect knowledge.

### S2: Learned graph utility
**herald_lagged MAE < no_graph AND herald_lagged MAE < herald_lagged_permuted**

The learned lagged graph must outperform both the no-graph baseline (capacity control) and the permuted graph (structure specificity control). Failure = the learned graph does not provide net imputation benefit.

### S3: Edge recovery threshold
**mean herald_lagged edge AUC ≥ 0.60**

The lagged architecture must recover directed edge structure above the AUC=0.60 threshold. This is lower than the oracle (1.0) but substantially above chance (0.5). Calibrated against Phase 10 results where herald_lagged achieved 0.64–0.71.

### S4: Structural precision
**mean herald_lagged edge_precision@k > prevalence (≈ 0.111 for n_true=8, n=9)**

At k = n_true_edges, precision must exceed random ranking. Tests whether the top-ranked edges in learned attention are non-random.

### S5: Seed consistency
**herald_lagged MAE < no_graph in ≥ 2/3 seeds per (scenario, config) combination**

Imputation utility must be consistent across seeds, not driven by a single favorable initialization.

### S6: Safety
**Zero NaN, Inf in imputation MAE; leakage_check passed for all tasks**

No data quality issues permitted.

### S7: Monotonicity
**Oracle advantage (no_graph MAE − oracle_lagged MAE) is non-decreasing from cs_force=low to cs_force=high**

If stronger cross-sector signal makes the oracle more useful, the oracle-vs-no-graph gap should increase. Failure = the graph oracle becomes relatively less useful as the signal it captures increases, which would indicate a model or metric problem.

---

## 4. Runner and Output

**Runner:** `src/modeles/synthetic/run_signal_sensitivity.py`  
**Gates:** `src/modeles/synthetic/gates_sensitivity.py`  
**Smoke test:** `python -m src.modeles.synthetic.run_signal_sensitivity --smoke-test`  
**Local pilot:** `python -m src.modeles.synthetic.run_signal_sensitivity --local-pilot`  
**Full run:** 324-task SLURM array (requires explicit HPC authorization)  
**Manifest version:** `sensitivity_v1`

Output directory structure:
```
data/processed/synthetic_benchmark/
  sensitivity_smoke/           # 1 task, 50 epochs
  sensitivity_pilot/           # pilot grid, 100 epochs
  sensitivity_full/            # full 324 tasks, 200+ epochs
```

---

## 5. Smoke Test Results

**Config:** linear, cs=original, ar=original, noise=original, lag=mixed, seed=42, 50 epochs, local.

| Model | MAE (mcar_30) | MAE (block_30) | AUC (mcar_30) | AUC (block_30) |
|-------|---------------|----------------|---------------|----------------|
| ffill | 0.2478 | 0.2493 | — | — |
| ridge | 0.2743 | 0.2849 | — | — |
| no_graph | 0.2737 | 0.2826 | — | — |
| herald_contemp | 0.2709 | 0.2821 | 0.516 | 0.508 |
| herald_lagged | 0.2750 | 0.2848 | 0.492 | 0.400 |
| herald_lagged_permuted | 0.2690 | 0.2879 | — | — |
| oracle_lagged | 0.2701 | 0.2813 | 1.000 | 1.000 |

**Smoke test verdict:** Code runs to completion. oracle_lagged AUC=1.000 (wiring correct). 50 epochs insufficient for learned models to converge — MAE ordering is not representative. Full pilot/HPC run required for gate evaluation.

---

## 6. Pilot Results (if executed)

*Populated after pilot run (original parameters only, 2 seeds, 100 epochs).*

---

## 7. Full Results (HPC — requires separate authorization)

*Not yet executed. Requires explicit authorization per project safety rules.*

---

## 8. Calibration Contract

This section documents the calibration protocol for a future implementation. No code is implemented here.

### 8.1 Why calibration is deferred

Phase 10 (L8) found `UNCERTAINTY_NOT_CALIBRATED`. The model currently produces point estimates only. Conformal calibration would require:
1. A held-out calibration set (not the same as the training mask)
2. A non-conformity score function (e.g., absolute residual)
3. Inductive conformal prediction intervals at coverage 1-α

### 8.2 Proposed protocol (future DEC)

**Method:** Split conformal prediction over the temporal axis.
- Train on years [0, T_cal), calibrate on years [T_cal, T_test), test on years [T_test, T].
- Non-conformity score: |imputed − true| at observed calibration cells.
- Coverage targets: 50%, 80%, 90%.
- Reporting: empirical coverage + mean interval width (sharpness).

**Blocking condition:** Conformal calibration requires that calibration and test cells are exchangeable. Under temporal AR(1), this may not hold. Verify exchangeability assumption before implementing.

**When to implement:** After MAE utility is demonstrated (L3 PASS or explicit reclassification). Calibration without utility is premature.

### 8.3 Gates for future calibration DEC

- C1: Empirical 90% coverage ≥ 85% (tolerance for finite calibration set)
- C2: Empirical 50% coverage ∈ [45%, 55%]
- C3: Interval width < 2× oracle imputation MAE
- C4: Coverage monotone with α (50% < 80% < 90%)

---

## 9. Generalization Protocol Proposal

The current "generalization" scenario in Phase 10 is not true generalization (see HERALD_PHASE10_METRIC_RECONCILIATION.md, §5). This section proposes a true protocol for a future experiment.

**GENERALIZATION_NOT_YET_TESTED**

Proposed true generalization protocol:
1. **Train** models on {linear + mixed_default} scenarios
2. **Validate** hyperparameters on {nonlinear_heavy}
3. **Test** on {generalization / shifted_dynamics} with NO further adaptation
4. **Report** MAE and AUC on held-out test scenario

This protocol is not implemented in Phase 10 or in this experiment. It requires:
- A single combined training dataset (multiple scenarios, shared model)
- Fixed hyperparameters before test exposure
- At least 3 seeds for test stability

The shifted dynamics scenario (renamed from "generalization") serves as the natural test set given its divergent dynamics.

---

## 10. Files

| File | Description |
|------|-------------|
| `src/modeles/synthetic/run_signal_sensitivity.py` | Sensitivity runner (324 tasks) |
| `src/modeles/synthetic/gates_sensitivity.py` | S1-S7 gate evaluator (frozen) |
| `tests/test_phase10_metric_reconciliation.py` | AUC fixture tests + forced_lag tests |
| `reports/HERALD_PHASE10_METRIC_RECONCILIATION.md` | AUC reconciliation + full metric table |
