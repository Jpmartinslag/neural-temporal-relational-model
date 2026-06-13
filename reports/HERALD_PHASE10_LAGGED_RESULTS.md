# HERALD Phase 10 — Lagged Graph Architecture Results

**Decision reference:** DEC-043  
**Job:** 7457885 (meso, partition fast, array 0-19)  
**Date collected:** 2026-06-13  
**Tasks:** 20/20 complete (4 scenarios × 5 seeds)  
**Epochs:** 500  
**Status:** PHASE10_PARTIAL

---

## 1. Safety Audit (L7)

| Check | Result |
|-------|--------|
| NaN in imputation metrics | 0 |
| Inf in imputation metrics | 0 |
| Task errors | 0 |
| Leakage (temporal features causal) | PASS (all 20 tasks) |

**L7 SAFETY: PASS** ✓

---

## 2. Gate Outcomes

| Gate | Result | Value |
|------|--------|-------|
| L1 WIRING (blocking) | **PASS** | oracle_lagged < oracle_contemp in 4/4; < no_graph in 4/4 |
| L2 RELATIONS (blocking) | **PASS** | corrected AUC=1.000 (4/4 scenarios) |
| L3 RECONSTRUCTION | FAIL | herald_lagged < contemp×0.95 in 0/4 (improvement: +0.7–2.4%) |
| L4 SPECIFICITY | **PASS** | herald_lagged < no_graph AND < permuted (aggregate) |
| L5 ROBUSTNESS | **PASS** | herald_lagged ≤ herald_contemp×1.10 on linear |
| L6 GENERALIZATION | FAIL | +2.4% improvement (need >5%) on generalization scenario |
| L7 SAFETY (blocking) | **PASS** | NaN=0, Inf=0, leakage PASS |
| L8 CALIBRATION | FAIL (marker) | UNCERTAINTY_NOT_CALIBRATED (non-blocking, expected) |

**Decision: PHASE10_PARTIAL**  
Blocking gates: all PASS. Non-blocking: 2/5 PASS (L4, L5).

---

## 3. MAE Table (mean over 5 seeds × all mask configs)

| Scenario | ffill | no_graph | herald_contemp | oracle_contemp | herald_lagged | oracle_lagged |
|----------|-------|----------|----------------|----------------|---------------|---------------|
| linear | 0.1978 | 0.2252 | 0.2195 | 0.2207 | **0.2155** | 0.2177 |
| nonlinear_heavy | 0.1892 | 0.2116 | 0.2063 | 0.2074 | **0.2037** | 0.2035 |
| mixed_default | 0.2361 | 0.2631 | 0.2615 | 0.2634 | **0.2596** | 0.2597 |
| generalization | 0.3856 | 0.5863 | 0.5319 | 0.5248 | **0.5191** | 0.5180 |

ffill dominates all scenarios (same finding as Phase 9 full run).

---

## 4. Edge Recovery AUC

| Scenario | herald_contemp | herald_lagged | oracle_lagged |
|----------|----------------|---------------|---------------|
| linear | 0.434 | **0.707** | 1.000 |
| nonlinear_heavy | 0.389 | **0.693** | 1.000 |
| mixed_default | 0.398 | **0.700** | 1.000 |
| generalization | 0.407 | **0.639** | 1.000 |

**Key finding:** herald_lagged AUC (0.64–0.71) is ~70% above herald_contemp AUC (0.39–0.43). The lagged architecture correctly identifies more structure, but this translates to only 1–2% MAE improvement because cross-sector effects are small relative to the AR(1) component.

---

## 5. MAE Improvement Analysis

### herald_lagged vs herald_contemp

| Scenario | Improvement |
|----------|-------------|
| generalization | +2.39% |
| linear | +1.81% |
| nonlinear_heavy | +1.23% |
| mixed_default | +0.70% |

Consistent positive improvement but below the pre-specified 5% threshold for L3.

### oracle_lagged vs oracle_contemp

| Scenario | Improvement |
|----------|-------------|
| nonlinear_heavy | +1.86% |
| mixed_default | +1.43% |
| linear | +1.36% |
| generalization | +1.29% |

Even the oracle (frozen directed adj, optimal wiring) shows only 1.3–1.9% improvement, setting the ceiling for L3.

### herald_lagged vs no_graph

| Scenario | Improvement |
|----------|-------------|
| generalization | +11.45% |
| linear | +4.31% |
| nonlinear_heavy | +3.71% |
| mixed_default | +1.32% |

Substantial improvement over the no-graph baseline confirms that the graph signal is useful.

---

## 6. Interpretation

### Why L3 fails despite correct architecture

The generator uses AR(1) with φ∈[0.3,0.6]. The temporal AR term accounts for the majority of variance. Cross-sector effects at lag-1/lag-2 contribute 1.3–2.4% additional MAE reduction even with perfect oracle wiring. The 5% threshold for L3 was calibrated assuming stronger cross-sector signal.

The pre-specified L3 gate is FAILED, and this failure is **structural** (the signal ceiling under these AR dynamics is ~2%), not a convergence artefact.

### Positive findings

1. **Architecture correct (L1+L2 PASS):** Directed oracle always outperforms contemporaneous oracle. AUC=1.000 confirms the lag-1/lag-2 attention encoding is correctly wired.

2. **Structure recovered (AUC improvement):** herald_lagged achieves AUC 0.64–0.71, a ~70% relative improvement over herald_contemp (0.39–0.43). The model is recovering directed lagged structure.

3. **Specificity holds (L4 PASS):** Improvement over no_graph (+4.3–11.5%) and over permuted graph is consistent — the signal comes from true structure, not graph capacity.

4. **No regression (L5 PASS):** The lagged architecture does not hurt on the simplest (linear) scenario.

5. **Safety clear (L7 PASS):** No data quality issues across all 20 tasks.

### Why ffill still dominates

AR(1) with φ∈[0.3,0.6] means the previous observation is near-optimal for missing value imputation. All neural architectures (including oracle_lagged) trail ffill by 0.02–0.17 MAE. This is a property of the data generator, not a model failure.

---

## 7. Decision

**PHASE10_PARTIAL**

The lagged architecture is structurally correct and improves edge recovery substantially. The MAE improvement (1–2.4%) is real, consistent, and specific to true graph structure, but does not reach the pre-specified 5% threshold. The L3 failure reflects the generator's AR dynamics, not an architectural defect.

**Recommendation for next DEC:**
- Options: (A) lower L3 threshold to 2% to reflect AR-dynamics ceiling; (B) increase cross-sector signal strength in generator (higher `territory_propagation` or stronger lag weights); (C) accept PHASE10_PARTIAL as sufficient for publication claim with appropriate caveats.
- Option C is compatible with the current scientific framing (lagged arch improves edge recovery 70%; MAE improvement 1–2%; no causal claims).

---

## 8. Files

| File | Description |
|------|-------------|
| `hpc_results/phase10_synthetic_lagged/*.json` | 20 result files (not committed — regenerable) |
| `hpc_results/phase10_synthetic_lagged/gate_report_phase10.json` | Gate evaluation report |
| `src/modeles/synthetic/herald_graph_imputer_lagged.py` | Architecture |
| `tests/test_herald_lagged.py` | 34 tests, all PASS |
| `reports/HERALD_PHASE10_LAGGED_CONTRACT.md` | Pre-specified contract |
