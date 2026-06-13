# HERALD Phase 10 — Lagged Architecture Contract

**Decision reference:** DEC-043  
**Status:** FROZEN (written before any benchmark code was executed)  
**Date:** 2026-06-13  
**Pilot smoke test:** PASS (oracle_lagged AUC=1.000, runner exits 0, JSON valid, NaN=0)

---

## 1. Motivation

Phase 9 diagnostic (DEC-042) identified three structural problems:

| Bug | Finding | Status |
|-----|---------|--------|
| B1 | AUC transposition: attention[rows,cols] instead of [cols,rows] | FIXED — AUC 0.27→0.727 |
| B2 | Symmetric adjacency: oracle cannot distinguish direction | DOCUMENTED |
| B3 | Contemporaneous aggregation: lag-1/2 cross-sector effects missed | ARCHITECTURAL FIX → Phase 10 |

Phase 10 implements `HERALDGraphImputerLagged` with explicit lag-1 and lag-2 directed attention matrices and a directed oracle using true lag-specific edges.

---

## 2. Architecture Specification (frozen)

### HERALDGraphImputerLagged

**Parameters:**
- `log_sect_attn_lag1` (n_S × n_S): learnable log-attention for lag-1 cross-sector messages
- `log_sect_attn_lag2` (n_S × n_S): learnable log-attention for lag-2 cross-sector messages
- `log_terr_attn` (n_T × n_T): learnable log-attention for territory messages (contemporaneous)

**Attention semantics:**  
`sect_attn_lagK[i,j]` = weight of source sector j contributing to target sector i at lag K  
(i.e., captures directed edge j → i with delay K years)

**Graph features (3 values per cell):**
1. `sector_nb_lag1`: mask-weighted mean of source sector values at year t-1
2. `sector_nb_lag2`: mask-weighted mean of source sector values at year t-2
3. `territory_nb`: mask-weighted mean of territory neighbors at year t (contemporaneous)

**Boundary conditions:**
- Year 0: lag-1 feature = 0 (no t-1 history)
- Years 0-1: lag-2 feature = 0 (no t-2 history)
- Missing neighbors at lag k: feature collapses to 0 (mask-weighted avg with zero denominator → 0/ε=0)

**MLP:** 10 inputs (7 temporal + 3 graph) → Linear(64) → ReLU → Dropout(0.1) → Linear(32) → ReLU → Linear(2)  
Output: (mean, log_sigma) per cell

**get_sector_attention():** returns elementwise max(lag1, lag2) for backward compatibility with `compute_edge_recovery_metrics`

### Oracle (directed)

For a true lag-K edge `source_sector s → target_sector t`:
- `log_sect_attn_lagK[t, s] = 0.0` (high attention)
- All other entries = `log(1e-6) ≈ -13.8` (strongly suppressed)

Both lag matrices frozen (`requires_grad=False`); MLP weights remain trainable.

**Properties:**
- Fixes B2: uses directed adjacency (not symmetric)
- Fixes B3: uses lag-1/lag-2 values (not contemporaneous)
- AUC with corrected metric = 1.0 (verified in smoke test)

---

## 3. Benchmark Design (15 models)

| ID | Model | Type | New in P10 |
|----|-------|------|-----------|
| B1 | mean | baseline | — |
| B2 | median | baseline | — |
| B3 | ffill | baseline | — |
| B4 | temporal_interp | baseline | — |
| B5 | knn | baseline | — |
| B6 | ridge | baseline | — |
| B7 | graph_ridge | baseline | — |
| C1 | neural_no_graph | contemp neural | — |
| C2 | herald_contemp | contemp neural | — |
| C3 | herald_contemp_permuted | contemp neural | — |
| C4 | herald_contemp_random | contemp neural | — |
| C5 | oracle_contemp | contemp neural | — |
| L1 | herald_lagged | lagged neural | **NEW** |
| L2 | herald_lagged_permuted | lagged neural | **NEW** |
| L3 | oracle_lagged | lagged neural | **NEW** |

**Scenarios (4):** linear, nonlinear_heavy, mixed_default, generalization  
**Seeds (5):** 42, 123, 456, 789, 1337  
**Mask types (3):** mcar, mar, block  
**Mask levels (3):** 10%, 30%, 50%  
**Total tasks (HPC):** 4 scenarios × 5 seeds = 20 array tasks  
**Epochs (HPC):** 500 full; 200 pilot  
**Pilot scenarios:** linear + nonlinear_heavy, seeds 42/123/456, 10%+30%

---

## 4. Gates L1-L8 (frozen before any benchmark)

All gates defined here. No gate modification after results are observed.

### L1 — WIRING (blocking)
`oracle_lagged < oracle_contemp` AND `oracle_lagged < neural_no_graph`  
in ≥ 3/4 scenarios (aggregate over seeds and mask configs)

> Validates that lag-specific message passing reaches targets better than contemporaneous and
> that the directed oracle wiring is correctly implemented.

### L2 — RELATIONS (blocking)
Corrected AUC ≥ 0.60 AND lag_accuracy > 0.50 on oracle_lagged  
(corrected AUC = AUC using `learned_attn[cols, rows]` indexing; lag_accuracy = fraction of top-k edges that have correct lag label)

> Validates that the attention matrices encode edge direction and lag correctly.

### L3 — RECONSTRUCTION (non-blocking)
`herald_lagged < herald_contemp × 0.95` in ≥ 2/4 scenarios

> Validates that lagged message passing translates to better imputation, not just better oracle wiring.

### L4 — SPECIFICITY (non-blocking)
`herald_lagged < neural_no_graph` AND `herald_lagged < herald_lagged_permuted`  
in 5-seed aggregate

> Validates that benefit is specific to true graph structure, not just graph capacity.

### L5 — ROBUSTNESS (non-blocking)
`herald_lagged ≤ herald_contemp × 1.10` on linear scenario

> Validates no regression (lagged arch does not hurt on the simplest scenario).

### L6 — GENERALIZATION (non-blocking)
L3 condition holds on generalization scenario specifically

> Validates improvement generalises to out-of-distribution structural patterns.

### L7 — SAFETY (blocking)
NaN = 0, Inf = 0, leakage_check = PASS across all tasks

> Mandatory data quality gate. BLOCKING.

### L8 — CALIBRATION (non-blocking, marker)
Always marked `UNCERTAINTY_NOT_CALIBRATED`  
No calibration head in Phase 10. Records the gap for future work.

---

## 5. HPC Auto-Authorization

HPC full array is automatically authorized if **L1 + L2 + L7 all PASS** in pilot.  
Do not launch full array otherwise.

---

## 6. Decision Vocabulary

| Decision | Condition |
|----------|-----------|
| PHASE10_PASS | L1+L2+L7 PASS, non-blocking ≥ 3/5 |
| PHASE10_PARTIAL | L1+L2+L7 PASS, non-blocking 1-2/5 |
| PHASE10_FAIL | L1+L2+L7 PASS, non-blocking 0/5 |
| HPC_BLOCKED | Any blocking gate fails |

---

## 7. Files

| File | Role |
|------|------|
| `src/modeles/synthetic/herald_graph_imputer_lagged.py` | Architecture |
| `src/modeles/synthetic/run_phase10_benchmark.py` | Runner |
| `src/modeles/synthetic/gates_phase10.py` | Gate evaluator |
| `tests/test_herald_lagged.py` | 34 tests (16 categories), all PASS |
| `hpc/phase10_synthetic_lagged/` | HPC infrastructure |
| `hpc_results/phase10_synthetic_lagged/` | HPC output (remote) |
| `data/processed/synthetic_benchmark/phase10_pilot/` | Local pilot output |

---

## 8. Safety Constraints

- No claims of causal inference — edges represent lagged predictive precedence only.
- No architecture modification after benchmark begins.
- No gate modification after results observed.
- No HPC full array without explicit L1+L2+L7 authorization.
- Commit all code before sync to meso. Sync without `--delete`.
