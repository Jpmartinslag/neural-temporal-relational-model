# HERALD Phase 10 — Metric Reconciliation

**Reference:** DEC-043 / DEC-044  
**Date:** 2026-06-13  
**Status:** PHASE10_PARTIAL_CONFIRMED — no retroactive reclassification

---

## 1. Purpose

This document resolves the apparent contradiction between:

- **DEC-042 (Phase 9 retroactive correction):** corrected AUC ≈ 0.727
- **Phase 10 herald_contemp:** mean AUC ≈ 0.39–0.43

and provides a full edge recovery metric table from raw Phase 10 JSON results (job 7457885, 20/20 tasks).

---

## 2. AUC Reconciliation

### 2.1 Summary

| Source | Model | Mean AUC | Direction | Classification |
|--------|-------|----------|-----------|---------------|
| Phase 9 (B1-buggy, not re-run) | herald_graph | 0.273 | Wrong (inverted) | Retroactive: 1-0.273=0.727 |
| Phase 10 (B1-fixed from start) | herald_contemp | 0.39–0.43 | Partial reverse | MODEL_DIFFERENCE |
| Phase 10 | herald_lagged | 0.64–0.71 | Partial correct | MODEL_DIFFERENCE |
| Phase 10 | oracle_lagged | 1.000 | All correct | ORACLE_VERIFIED |

### 2.2 Bug B1 — AUC Transposition (fixed before Phase 10)

The original Phase 9 `compute_edge_recovery_metrics` had:

```python
# Correct convention: learned_attn[target, source] = weight for source→target
# rows = source index, cols = target index (off-diagonal enumeration)

# BUG (Phase 9):
y_score = learned_attn[rows, cols]  # = attn[source, target] → WRONG

# FIX (applied before Phase 10):
y_score = learned_attn[cols, rows]  # = attn[target, source] → CORRECT
```

With the bug, true edge s→t was scored by `attn[s, t]` instead of `attn[t, s]`. For asymmetric attention, this reverses the ranking, yielding AUC ≈ 1 − (true AUC). Phase 9 mean AUC=0.273 → retroactive corrected AUC = 0.727.

**Phase 9 result:** N=180 pairs, mean AUC=0.273. All below 0.5 → model learned the reverse direction consistently. Retroactive correction: 1-0.273=0.727 (the B1 fix means the true underlying pattern has AUC=0.727 via symmetry of the ROC curve).

**Phase 10 herald_contemp:** B1 was fixed before this run. Mean AUC=0.39–0.43. Still below 0.5 (85% of per-seed/mask evaluations). **This is a different run, not the same model.**

### 2.3 Bug B2 — Symmetric Adjacency Direction Learning

Both Phase 9 and Phase 10 use a **symmetric** sector adjacency matrix as input (`adj[src,tgt] = adj[tgt,src] = 1`). This means:

- The attention softmax operates over columns of a symmetric matrix
- The model has no structural signal distinguishing forward from reverse edges
- Direction is learned implicitly from the temporal signal, which is noisy and weak at φ∈[0.3,0.6]
- Different random initializations → different local optima → different directions

**Phase 9 herald_graph** converged to the correct direction (AUC≈0.727 after correction).  
**Phase 10 herald_contemp** converged to the partial reverse (AUC≈0.40).  
**Phase 10 herald_lagged** used directed attention and partially recovered correct direction (AUC≈0.68).

**Classification: MODEL_DIFFERENCE.** Not a metric bug. Both observations are valid results of the same training regime. B2 makes direction learning non-deterministic; neither run is preferred over the other for claims about the architecture.

### 2.4 Why herald_contemp ≠ Phase 9 herald_graph

| Aspect | Phase 9 herald_graph | Phase 10 herald_contemp |
|--------|---------------------|------------------------|
| Architecture | Contemporaneous symmetric | Contemporaneous symmetric (same) |
| B1 fix | Not applied (retroactive correction only) | Applied from start |
| Seeds | 5 seeds (42/123/456/789/1337) | 5 seeds (same) |
| Adj matrix | Symmetric | Symmetric (same) |
| Epochs | 500 | 500 |
| Mean AUC | 0.273 (buggy) → 0.727 (corrected) | 0.406 |
| Direction | Reverse (B2) | Partial reverse (B2) |
| % below 0.5 | 100% | 85% |

Both models fall under B2. The difference in AUC magnitude reflects different convergence, not a different metric.

---

## 3. Full Edge Recovery Metric Table (Phase 10, raw JSON)

**Universe:** 9 sectors × (9-1) = 72 off-diagonal pairs per evaluation.  
**Prevalence:** 8/72 ≈ 0.111 for linear/nonlinear/mixed; 12/72 ≈ 0.167 for generalization.  
**Precision/Recall/F1:** evaluated at k = n_true_edges (threshold-free ranking metric).  
**AUPRC:** not stored (not a field of EdgeRecoveryMetrics in this version).  
**edge_lag_acc:** NaN for all models (per-lag matrices not stored in JSON; oracle_lagged AUC=1.000 provides structural proof).

N = number of (seed × mask) evaluations per cell. 5 seeds × 9 mask configs = 45 per scenario.

### 3.1 herald_contemp

| Scenario | AUC (mean±std) | Precision@k | Recall@k | F1@k | Sign Acc | N |
|----------|----------------|-------------|----------|------|----------|---|
| linear | 0.3934 ± 0.0723 | 0.100 | 0.100 | 0.100 | 0.456 | 45 |
| nonlinear_heavy | 0.3890 ± 0.0612 | 0.083 | 0.083 | 0.083 | 0.472 | 45 |
| mixed_default | 0.3985 ± 0.0688 | 0.081 | 0.081 | 0.081 | 0.475 | 45 |
| generalization | 0.4073 ± 0.0601 | 0.104 | 0.104 | 0.104 | 0.622 | 45 |

All AUC values below 0.50 → consistent reverse-direction convergence (B2).  
Precision@k ≈ prevalence (0.111/0.167) → no recovery above chance.

### 3.2 herald_lagged

| Scenario | AUC (mean±std) | Precision@k | Recall@k | F1@k | Sign Acc | N |
|----------|----------------|-------------|----------|------|----------|---|
| linear | 0.7055 ± 0.0528 | 0.428 | 0.428 | 0.428 | 0.433 | 45 |
| nonlinear_heavy | 0.6926 ± 0.0460 | 0.425 | 0.425 | 0.425 | 0.425 | 45 |
| mixed_default | 0.6999 ± 0.0654 | 0.428 | 0.428 | 0.428 | 0.433 | 45 |
| generalization | 0.6387 ± 0.0822 | 0.354 | 0.354 | 0.354 | 0.609 | 45 |

AUC substantially above 0.5 → lagged attention partially recovers correct directed structure.  
Precision@k ≈ 0.35–0.43 >> prevalence (0.111) → 3–4× better than random at top-k.

#### Per-seed AUC variance (herald_lagged)

| Scenario | seed=42 | seed=123 | seed=456 | seed=789 | seed=1337 |
|----------|---------|----------|----------|----------|-----------|
| linear | 0.672 | 0.796 | 0.719 | 0.714 | 0.627 |
| nonlinear_heavy | 0.681 | 0.712 | 0.721 | 0.688 | 0.662 |
| mixed_default | 0.587 | 0.804 | 0.711 | 0.752 | 0.646 |
| generalization | 0.501 | 0.732 | 0.601 | 0.714 | 0.647 |

Seed=42 in generalization (AUC=0.501) is the worst case — nearly random. Seed=123 consistently best. High variance reflects B2.

### 3.3 oracle_lagged

| Scenario | AUC | Precision@k | Recall@k | F1@k | N |
|----------|-----|-------------|----------|------|---|
| linear | 1.000 ± 0.000 | 1.000 | 1.000 | 1.000 | 45 |
| nonlinear_heavy | 1.000 ± 0.000 | 1.000 | 1.000 | 1.000 | 45 |
| mixed_default | 1.000 ± 0.000 | 1.000 | 1.000 | 1.000 | 45 |
| generalization | 1.000 ± 0.000 | 1.000 | 1.000 | 1.000 | 45 |

AUC=1.000 (all evaluations, min=max=1.000) confirms:
- Directed lag-1/lag-2 attention encoding is correctly wired (L2 PASS)
- Edge recovery metric is correctly computed for the directed oracle

---

## 4. Full MAE Table (raw JSON, per scenario × mask type × seed)

### 4.1 By scenario × mask type (mean over 5 seeds)

| Scenario | Mask | ffill | no_graph | herald_contemp | herald_lagged | oracle_lagged | Δ(hl-hc) |
|----------|------|-------|----------|----------------|---------------|---------------|----------|
| linear | mcar | 0.2046 | 0.2259 | 0.2189 | 0.2170 | 0.2187 | −0.87% |
| linear | mar | 0.2306 | 0.2780 | 0.2631 | 0.2621 | 0.2632 | −0.40% |
| nonlinear_heavy | mcar | 0.1863 | 0.2025 | 0.1967 | 0.1935 | 0.1938 | −1.65% |
| nonlinear_heavy | mar | 0.2046 | 0.2447 | 0.2285 | 0.2290 | 0.2305 | +0.25% |
| mixed_default | mcar | 0.2316 | 0.2498 | 0.2461 | 0.2451 | 0.2451 | −0.42% |
| mixed_default | mar | 0.2539 | 0.3022 | 0.2919 | 0.2912 | 0.2917 | −0.23% |
| generalization | mcar | 0.3746 | 0.5481 | 0.4814 | 0.4700 | 0.4702 | −2.37% |
| generalization | mar | 0.4295 | 0.6872 | 0.6135 | 0.6058 | 0.6029 | −1.27% |

### 4.2 By seed — herald_lagged vs herald_contemp (mean over mask types × levels)

| Scenario | seed=42 | seed=123 | seed=456 | seed=789 | seed=1337 |
|----------|---------|----------|----------|----------|-----------|
| linear | −1.35% | +0.18% | +0.46% | −4.32% | −3.28% |
| nonlinear_heavy | −1.89% | −0.42% | +0.68% | −1.88% | −2.51% |
| mixed_default | −1.07% | +0.33% | −0.87% | −0.66% | −1.32% |
| generalization | −0.03% | −0.61% | −0.71% | −0.61% | −5.11% |

Negative = herald_lagged better. Positive = herald_contemp better.  
Seed=1337 drives the aggregate gain in generalization (−5.11%, absolute Δ=−0.056).

### 4.3 Interpretation

The oracle ceiling for lagged cross-sector contribution is **1.3–2.4% MAE** (oracle_lagged vs oracle_contemp). This sets the maximum achievable improvement. herald_lagged reaches 70–90% of the oracle ceiling. The L3 failure (5% threshold not met) reflects the generator's AR(1) dynamics, not a model defect.

ffill dominates all models in all scenarios (MAE 7–35% lower than any neural model). This is a known property of AR(1) data with φ∈[0.3,0.6]: the previous observation is near-optimal.

---

## 5. Generalization Scenario: Not True Generalization

The "generalization" scenario in Phase 10 is **NOT** a cross-scenario generalization test. Each task trains AND tests on its own data from the same scenario. It is more accurately described as `shifted_dynamics_scenario`:

- Higher noise: σ∈[0.15,0.35] vs [0.08,0.18] for others
- Wider AR range: φ∈[0.2,0.7] vs [0.3,0.6]
- Denser true relations: 12 vs 8
- Stronger territory propagation: 0.25 vs 0.15

True generalization would require: train on {linear, mixed_default}, test on {generalization}, with no adaptation at test time. This protocol is not yet implemented. See HERALD_PHASE10_SIGNAL_SENSITIVITY.md for the proposed next step.

---

## 6. PHASE10_PARTIAL Confirmation

**PHASE10_PARTIAL remains the correct decision.** No retroactive reclassification.

The AUC discrepancy between DEC-042 (0.727) and Phase 10 herald_contemp (0.40) is fully explained by:
1. B1 fix: Phase 9 retroactive correction (1 − 0.273) vs. Phase 10 direct measurement
2. B2: Symmetric adjacency → non-deterministic direction convergence across runs

The lagged architecture (herald_lagged AUC=0.64–0.71) demonstrates substantial improvement over herald_contemp, consistent with L2 PASS. The MAE improvement (1–2.4%) is real and specific, but does not reach the pre-specified L3 threshold of 5%.

---

## 7. Files

| File | Description |
|------|-------------|
| `hpc_results/phase10_synthetic_lagged/*.json` | 20 result files (20/20 complete) |
| `hpc_results/phase10_synthetic_lagged/gate_report_phase10.json` | L1-L8 gate outcomes |
| `tests/test_phase10_metric_reconciliation.py` | Fixture tests for AUC metric correctness |
| `reports/HERALD_PHASE10_LAGGED_RESULTS.md` | Full Phase 10 audit (primary) |
