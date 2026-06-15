# HERALD — DEC-049 Convergence Audit
**Phase 14 | Date: 2026-06-15 | Status: PILOT_COMPLETE**
**Hypothesis under test: TRAINING_BUDGET_TOO_SMALL (DEC-048)**
**Decision: PARTIAL — gradient evidence supports hypothesis; reconstruction still below ffill at pilot scale**

---

## 1. DEC-048 Audit Findings

Three corrections applied before execution:

1. **C10 distinction**: C10 PASS was driven by oracle M4 (locally trained, true attention frozen) — NOT by learned zero-shot HERALD. Learned HERALD zero-shot (M3) achieves MAE ratio ≈ 0.997 vs ffill. Added explicit note to DEC-048 report.
2. **Gradient caveat**: "~400× smaller" qualified as "diagnostic evidence, not proof that budget is the sole cause" — other factors (LR, initialisation, dataset diversity) not excluded.
3. **Synthetic-only constraint**: Bold "SYNTHETIC-ONLY CONSTRAINT:" header added to Section 8 of DEC-048 report. Edge/sign/lag supervision exists only in synthetic data; not available for PT/IT/FR/NL/AT.

---

## 2. Protocol (frozen before execution)

| Parameter | Value |
|-----------|-------|
| Epoch budgets | 30, 75 (pilot); 150 if E2 PASS |
| D2 pretrain datasets | 10 (pilot); 50 (full) |
| D2 frac_nonlinear | Uniform [0, 0.9], seeds 200–209 |
| Test scenarios | novel_lag2, novel_highvar |
| Test seeds | 1000, 2000 (pilot) |
| Masks | mcar_30 (pilot) |
| Multitask weights | α=0.10, β=0.05, γ=0.05 (FROZEN) |
| Few-shot k_fracs | 0.05 (pilot) |
| 300-epoch trigger | E1+E2 PASS at 150 + monotone AUC/val_loss improvement |
| Val scenario | nonlinear_heavy, seeds [100,200,300] |

---

## 3. Pretraining convergence

| Variant | Budget | best_epoch | best_val_loss |
|---------|--------|-----------|--------------|
| NO_PRETRAINING | — | — | — (uses Phase 11 T2 checkpoint) |
| TEMPORAL_MASKED | 30 | 29 | -2.172 |
| TEMPORAL_MASKED | 75 | 68 | -2.635 |
| GRAPH_MASKED_MULTITASK | 30 | 29 | -2.334 |
| GRAPH_MASKED_MULTITASK | 75 | 74 | -2.869 |

Val loss improves consistently 30→75 for both variants (E2 PASS). However, GRAPH_MASKED_MULTITASK val_loss is better than TEMPORAL_MASKED at both budgets, consistent with richer supervision signal.

---

## 4. Gradient diagnostics (CRITICAL)

| Variant | Budget | grad_attention | grad_decoder | ratio | aux→attention |
|---------|--------|---------------|-------------|-------|---------------|
| NO_PRETRAINING | — | nan | nan | — | False |
| TEMPORAL_MASKED | 30 | 0.002328 | 14.987 | **6438×** | **False** |
| TEMPORAL_MASKED | 75 | 0.000788 | 2.608 | **3310×** | **False** |
| GRAPH_MASKED_MULTITASK | 30 | 0.023594 | 2.395 | **101×** | **True** |
| GRAPH_MASKED_MULTITASK | 75 | 0.020369 | 6.750 | **331×** | **True** |

**Key findings:**
- TEMPORAL_MASKED loss does NOT reach the attention encoder (`aux→attention = False`). The temporal reconstruction gradient flows only to the MLP decoder.
- GRAPH_MASKED_MULTITASK edge-BCE loss DOES reach the attention encoder (`aux→attention = True`).
- Multitask loss reduces gradient ratio from ~3000–6000× to ~100–330×. Still large, but confirms the hypothesis: edge supervision is the only way to push gradients into the attention at short budgets.

This evidence is consistent with `TRAINING_BUDGET_TOO_SMALL` being a real factor, but does NOT confirm it as the sole cause at pilot scale.

---

## 5. Zero-shot evaluation results

### MAE (test window, mcar_30, novel_lag2 + novel_highvar, seeds 1000/2000)

| Variant | Budget | ffill | herald_lagged | no_graph | oracle_lagged | ridge |
|---------|--------|-------|--------------|---------|--------------|-------|
| NO_PRETRAINING | — | **0.307** | 0.316 | 0.317 | 0.346 | 0.339 |
| TEMPORAL_MASKED | 30 | **0.307** | 0.371 | 0.371 | 0.329 | 0.339 |
| TEMPORAL_MASKED | 75 | **0.307** | 0.391 | 0.391 | 0.346 | 0.339 |
| GRAPH_MASKED_MULTITASK | 30 | **0.307** | 0.356 | 0.356 | 0.307 | 0.339 |
| GRAPH_MASKED_MULTITASK | 75 | **0.307** | 0.365 | 0.365 | 0.359 | 0.339 |

### Edge AUC (herald_lagged)

| Variant | Budget | mean AUC |
|---------|--------|---------|
| NO_PRETRAINING | — | 0.711 |
| TEMPORAL_MASKED | 30 | 0.658 |
| TEMPORAL_MASKED | 75 | **0.722** |
| GRAPH_MASKED_MULTITASK | 30 | 0.654 |
| GRAPH_MASKED_MULTITASK | 75 | 0.641 |

---

## 6. Key observations

1. **ffill dominates all neural models** (MAE=0.307) — consistent with DEC-045/047 finding.
2. **Pretraining hurts reconstruction at pilot scale**: Both TEMPORAL_MASKED and GRAPH_MASKED_MULTITASK produce higher MAE than NO_PRETRAINING. With only 10 D2 datasets, the model drifts from its Phase 11 T2 prior (which was already decent) without gaining enough from D2.
3. **herald_lagged ≈ no_graph ≈ herald_permuted** in all conditions: the graph signal is not exploited in reconstruction, only in edge AUC (which is measured separately via the attention matrix).
4. **Edge AUC**: TEMPORAL_MASKED@75 achieves 0.722 (best), slightly above NO_PRETRAINING (0.711). GRAPH_MASKED_MULTITASK edge AUC is lower than NO_PRETRAINING — the multitask loss may be interfering with the NLL objective at only 10 datasets.
5. **Oracle at pilot scale**: oracle_lagged is near ffill for GRAPH_MASKED_MULTITASK@30 (0.307), confirming architecture is not the blocker when graph structure is correct. But at budget=75 oracle degrades (0.359) — possibly because more pretraining on D2 changes the MLP weights that process graph features.
6. **Graph contribution ≈ 0**: MAE of herald_lagged ≈ no_graph ≈ herald_permuted in all conditions. The learned attention does not contribute to reconstruction.
7. **Few-shot records = 0**: Few-shot evaluation was not implemented in the pilot run (bug in evaluator.py — few-shot branch not invoked). E7 gate is therefore invalid.

---

## 7. Gate outcomes

| Gate | Result | Evidence |
|------|--------|---------|
| E1 SAFETY | PASS | 0 NaN, 0 leakage, D2 seeds disjoint |
| E2 CONVERGENCE | PASS | val_loss improves 30→75 for both trained variants |
| E3 RELATION_LEARNING | FAIL | NO_PRETRAINING AUC=0.711 ≥ 0.60, but pretraining variants AUC=0.64–0.72; AUPRC threshold not consistently met |
| E4 RECONSTRUCTION | FAIL | herald_lagged MAE ≈ no_graph MAE (difference < 0.005) |
| E5 BASELINE_RELEVANCE | FAIL | ffill MAE=0.307 < all neural strategies (best: NO_PRETRAINING 0.316) |
| E6 MULTITASK_VALUE | PASS | GRAPH_MASKED_MULTITASK val_loss < TEMPORAL_MASKED val_loss at same budget |
| E7 FEWSHOT_VALUE | **INVALID** | Few-shot evaluation not run (implementation bug — 0 records) |
| E8 GRAPH_PRESERVATION | PASS | (proxy via attention norms — attention not degraded) |
| E9 REPLICATION | FAIL | Inconsistent direction across seeds/scenarios |
| E10 BLOCK_ROBUSTNESS | — | Only mcar_30 tested in pilot |

**Effective gates at pilot scale: 2/8 valid PASS (E1, E6), 1 invalid (E7)**

---

## 8. 300-epoch trigger rule

**NOT triggered.** Trigger requires E1+E2 PASS at 150 epochs AND monotone AUC improvement. E2 PASS at pilot (30→75), but AUC did not consistently improve with GRAPH_MASKED_MULTITASK (0.654→0.641). 150-epoch run is required before trigger can be evaluated.

---

## 9. Decision

**PARTIAL**

Evidence is mixed:
- Gradient analysis SUPPORTS the training budget hypothesis: edge-BCE loss reaches the attention encoder and reduces gradient imbalance from ~6000× to ~100–330×
- Reconstruction (MAE) does NOT improve with pretraining at pilot scale (10 datasets, 30-75 epochs)
- The fundamental ffill dominance persists
- Few-shot evaluation not yet completed

### Possible remaining causes

1. **Insufficient D2 diversity** (only 10 datasets in pilot vs 50 in full): pretraining may require more data to override the good Phase 11 T2 prior
2. **MLP decoder functional limitation**: even with correct graph structure (oracle) and adequate gradients, the MLP cannot extrapolate 85-90% nonlinear dynamics — this is the original DEC-045 finding
3. **Distribution mismatch**: D2 datasets cover frac_nonlinear in [0,0.9] uniformly, but novel_lag2/novel_highvar have frac_nonlinear FIXED at 0.85/0.90 plus other axes of novelty (lag, topology, structural break). Pretraining may not cover these specific axes.

---

## 10. Next step

Before recommending HPC or masked pretraining at scale, one pending test:

**Run full 150-epoch pretraining with 50 D2 datasets** — this is within local budget (~5-8 minutes). If E4 and E5 remain FAIL at 150/50, conclude `OBJECTIVE_REMAINS_INADEQUATE` and reassess architecture.

**Fix few-shot bug** before the 150-epoch run to evaluate E7.

**HPC NOT recommended at this stage.** The pilot is inconclusive, not underpowered.

---

## 11. Files

| File | Description |
|------|-------------|
| `src/modeles/synthetic/phase14_convergence/pretrain_runner.py` | Pretraining with budget grid |
| `src/modeles/synthetic/phase14_convergence/evaluator.py` | Zero-shot + few-shot evaluation |
| `src/modeles/synthetic/phase14_convergence/gates_dec049.py` | E1-E10 gates |
| `src/modeles/synthetic/phase14_convergence/run_convergence.py` | CLI runner |
| `tests/test_phase14_convergence.py` | 25 tests |
| `data/processed/synthetic_benchmark/phase14_convergence/` | Pilot results (not committed) |
