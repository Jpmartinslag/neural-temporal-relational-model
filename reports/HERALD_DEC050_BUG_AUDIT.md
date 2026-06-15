# HERALD — DEC-050 Bug Audit: pretrain_runner.py
**Phase 14 | Date: 2026-06-15 | Status: RUNNING**
**Predecessor: DEC-049 (PARTIAL — pilot with buggy code)**
**Decision: PENDING (full 30/75/150 run with corrected code)**

---

## 1. Bug Inventory

Three critical bugs identified post-DEC-049 pilot in
`src/modeles/synthetic/phase14_convergence/pretrain_runner.py`.

### Bug A — TEMPORAL_MASKED: loss computed on visible cells (not hidden cells)

**Location:** `compute_multitask_nll`, TEMPORAL_MASKED branch (original lines ~344-367)

**Original code:**
```python
training_mask = mask.copy()
training_mask[indices_to_hide] = 0  # removes artificially hidden cells from mask
return _compute_nll_loss(model, panel, training_mask, adj_s, adj_t, device)
# ↑ NLL is computed on training_mask == 1 (cells the model CAN see)
# ↑ artificially hidden cells (truth known) are EXCLUDED from the loss
```

**What it should do:** Compute NLL on the artificially hidden cells (where the model
doesn't see the truth but the truth is known).

**Impact:** TEMPORAL_MASKED was functionally identical to standard NLL on 60% of
observed cells. The masking objective — "reconstruct the hidden cells from context" —
was never applied. DEC-049 TEMPORAL_MASKED results are therefore NOT the result of a
masked reconstruction pretraining strategy.

**Fix:**
```python
input_mask = structural_mask.copy()
input_mask[indices_to_hide] = 0        # model sees structural minus hidden

loss_mask = np.zeros_like(structural_mask, dtype=np.float32)
loss_mask[indices_to_hide] = 1.0       # loss computed on artificially hidden cells

return _compute_masked_nll_loss(model, panel, input_mask, loss_mask, adj_s, adj_t, device)
```

New function `_compute_masked_nll_loss` asserts `input_mask ∩ loss_mask = ∅`.

---

### Bug B — Edge presence BCE: lag-2 edges treated as negatives

**Location:** `_edge_bce` function (original lines ~199-220)

**Original code:**
```python
for r in true_relations:
    if r.lag == 1:                        # ← only lag-1 marked as positive
        edge_target[t, s] = 1.0
logits = model.log_sect_attn_lag1[mask_diag]  # ← only lag-1 logit used
```

**What it should do:** For edge PRESENCE (does this edge exist at all?), both lag-1
and lag-2 true edges should be positive. The presence loss should not depend on lag.

**Impact:** Every lag-2 true edge was given a negative label (0) in the binary BCE.
The loss actively pushed the model to suppress attention at lag-2 true edge positions.
Edge AUC metrics from DEC-049 GRAPH_MASKED_MULTITASK are biased downward for any
scenario with lag-2 true relations.

**Fix (renamed `_edge_presence_bce`):**
```python
for r in true_relations:
    s, t = r.source_sector, r.target_sector
    if s < n_sectors and t < n_sectors:
        edge_target[t, s] = 1.0          # lag-agnostic: any lag → positive

presence_logits = torch.max(model.log_sect_attn_lag1, model.log_sect_attn_lag2)
logits = presence_logits[mask_diag]
pos_weight = torch.tensor([float(n_neg / n_pos)], device=device)  # class balance
return F.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)
```

---

### Bug C — Sign and lag BCE share same logit (sign BCE architecturally invalid)

**Location:** `_sign_bce` and `_lag_bce` functions (original lines ~222-260)

**Original code:**
```python
def _sign_bce(model, true_relations, n_sectors, device):
    sign_logit = model.log_sect_attn_lag1 - model.log_sect_attn_lag2  # ← identical to lag

def _lag_bce(model, true_relations, n_sectors, device):
    lag_logit = model.log_sect_attn_lag1 - model.log_sect_attn_lag2   # ← identical to sign
```

**What it should do:**
- `_sign_bce`: predict whether the influence is positive or negative
- `_lag_bce`: predict whether the lag is 1 or 2

**Impact (compound):**
1. Both functions used the SAME logit (`lag1 - lag2`), so they were computing
   numerically identical losses on different target labels. The optimizer received
   contradictory gradients from the same signal.
2. Sign prediction is architecturally impossible: HERALD softmax attention computes
   `softmax(Q K^T / sqrt(d))`, which is always non-negative. A ratio of two
   non-negative values (`log_lag1 - log_lag2`) cannot encode the sign (+/-) of
   a causal influence without a dedicated signed output head.

**Fix:**
- `_sign_bce` **removed entirely**. MULTITASK_BETA constant preserved but unused.
- `_lag_bce` kept with the same logit (`lag1 - lag2`) — this is a reasonable proxy
  for lag classification (which lag attention is larger) but is now correctly labelled
  as lag prediction only, applied on known edges only.
- Documented in code: "Sign BCE removed — DEC-050 architectural finding."

---

## 2. Tests Added (tests 26–30)

All in `tests/test_phase14_convergence.py` (total: 30 tests):

| Test | Name | What it verifies |
|------|------|-----------------|
| 26 | `test_temporal_masked_loss_on_hidden_cells` | Loss changes when hidden cell value changes; does NOT change when structurally-missing cell changes |
| 27 | `test_edge_presence_bce_lag2_positive` | lag-2 single-edge loss equals lag-1 single-edge loss (both marked positive) |
| 28 | `test_presence_and_lag_logits_differ` | max(lag1,lag2) ≠ lag1−lag2 with known asymmetric parameter values |
| 29 | `test_sign_bce_not_in_multitask_loss` | `_sign_bce` not in source of `compute_multitask_nll`; not an attribute of module |
| 30 | `test_compute_masked_nll_loss_disjoint_assertion` | Overlapping input+loss masks raise; non-overlapping masks produce finite loss |

---

## 3. What DEC-049 Results Remain Valid

| Finding | Valid? | Reason |
|---------|--------|--------|
| Gradient imbalance ratio (attn/dec) | **YES** | Measured via autograd on actual `.grad` norms |
| aux→attn=True for GRAPH_MASKED_MULTITASK | **YES** | Gradient flow test independent of loss magnitude |
| TEMPORAL_MASKED aux→attn=False | **YES** | Same — gradient flow tested directly |
| Val loss improves 30→75 (E2 PASS) | Partially | Val loss used standard NLL (unaffected by Bug A) |
| GRAPH_MASKED_MULTITASK val_loss < TEMPORAL_MASKED | Partially | NLL portion correct; auxiliary loss was biased (Bug B) |
| MAE results (zero-shot) | **SUPERSEDED** | Pretraining used wrong objectives; re-run required |
| Edge AUC results | **SUPERSEDED** | Bug B biased edge AUC for lag-2 scenarios |
| Few-shot results | **INVALID** | Eval type mismatch bug caused 0 records |

---

## 4. Corrected Run Protocol

| Parameter | Value |
|-----------|-------|
| Epoch budgets | 30, 75, 150 |
| D2 datasets | 50 (seeds 200-249) |
| Mask types | mcar_30, block_30 |
| Test scenarios | novel_lag2, novel_highvar |
| Test seeds | TEST_SEEDS (Phase 11) |
| Few-shot k_fracs | 0.05, 0.10 |
| Output dir | `data/processed/synthetic_benchmark/phase14_convergence_v2/` |
| pretrain_runner.py version | DEC-050 (bugs A/B/C fixed) |

---

## 5. Files Modified

| File | Change |
|------|--------|
| `src/modeles/synthetic/phase14_convergence/pretrain_runner.py` | Bug A: new `_compute_masked_nll_loss`; Bug B: `_edge_bce` → `_edge_presence_bce` with lag-agnostic targets; Bug C: `_sign_bce` removed; `_lag_bce` cleaned up |
| `src/modeles/synthetic/phase14_convergence/run_convergence.py` | `parents[5]` → `parents[4]` (REPO_ROOT off-by-one) |
| `tests/test_phase14_convergence.py` | Test 24 updated (sign_bce removed); tests 26–30 added |
| `reports/HERALD_DEC049_CONVERGENCE_AUDIT.md` | Warning note added re: buggy pilot |
| `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` | DEC-050 entry added |

---

## 6. Results (corrected run: 50 D2, 30/75/150 epochs, 5 seeds, 2 masks, 2 scenarios)

Total runtime: 518s. 2160 records. Output: `data/processed/synthetic_benchmark/phase14_convergence_v2/`

### 6.1 Pretraining convergence

| Variant | Budget | best_epoch | best_val_loss | runtime |
|---------|--------|-----------|--------------|---------|
| NO_PRETRAINING | — | — | — | 0s |
| TEMPORAL_MASKED | 30 | 23 | -1.1206 | 55s |
| TEMPORAL_MASKED | 75 | 56 | -1.1690 | 40s |
| TEMPORAL_MASKED | 150 | 56 | -1.1606 | 39s |
| GRAPH_MASKED_MULTITASK | 30 | 29 | -3.1716 | 17s |
| GRAPH_MASKED_MULTITASK | 75 | 74 | **-31941.71** ⚠️ | 42s |
| GRAPH_MASKED_MULTITASK | 150 | 149 | **-421009.24** ⚠️ | 84s |

**⚠️ TRAINING INSTABILITY**: GRAPH_MASKED_MULTITASK val_loss diverges catastrophically starting at budget=75. Cause: variance collapse in the Gaussian NLL (σ → 0, giving NLL → -∞). This is a pathological solution not a genuine improvement. The `pos_weight = n_neg/n_pos` term in edge BCE combined with 50 datasets accelerates this collapse.

### 6.2 Zero-shot MAE (herald_lagged)

| Variant | Budget | novel_lag2 MAE | novel_lag2 AUC | novel_highvar MAE |
|---------|--------|----------------|----------------|-------------------|
| ffill | — | 0.2568 | — | 0.3740 |
| NO_PRETRAINING | 30 | 0.2562 | 0.5384 | 0.4599 |
| **TEMPORAL_MASKED** | **30** | **0.2437** | 0.4569 | 0.4380 |
| **TEMPORAL_MASKED** | **75** | **0.2327 ✓** | **0.5806** | 0.3847 |
| **TEMPORAL_MASKED** | **150** | **0.2329** | 0.5574 | 0.3921 |
| GRAPH_MASKED_MULTITASK | 30 | 0.2628 | 0.5019 | 0.5789 |
| GRAPH_MASKED_MULTITASK | 75 | 0.2684 | 0.4626 | 0.5296 |
| GRAPH_MASKED_MULTITASK | 150 | 0.3716 ⚠️ | 0.4484 | 0.5955 |

**Key result**: TEMPORAL_MASKED@75 MAE=0.2327 **beats ffill (0.2568) by 9.4%** on novel_lag2. First time HERALD beats ffill in zero-shot evaluation. Bug A fix was decisive: the masked reconstruction pretraining now correctly trains on hidden cells.

### 6.3 Few-shot MAE (A1 adaptation, budget=75)

| Variant | novel_lag2 k=5% | novel_lag2 k=10% | novel_highvar k=5% |
|---------|-----------------|------------------|---------------------|
| NO_PRETRAINING | 0.0537 | 0.0546 | 0.0954 |
| TEMPORAL_MASKED | **0.0509** | 0.0521 | **0.0803** |
| GRAPH_MASKED_MULTITASK | 0.0603 | 0.0609 | 0.1101 |

**Finding**: A1 adaptation (decoder-only fine-tuning, frozen attention) gives 78-80% MAE reduction across ALL pretraining strategies. This is consistent with DEC-047 (best strategy was A1). The adaptation is so effective that differences between pretraining strategies are compressed. However, TEMPORAL_MASKED@75 still achieves the best few-shot MAE.

### 6.4 Gate outcomes

| Gate | Result | Evidence |
|------|--------|---------|
| E1 SAFETY | PASS | 0 NaN, 0 Inf, disjoint seeds |
| E2 CONVERGENCE | PASS | val_loss improves 30→75 for both trained variants |
| E3 RELATION_LEARNING | FAIL | AUC=0.442 (threshold 0.60); AUPRC proxy < 1.5×prevalence |
| E4 RECONSTRUCTION | FAIL | HERALD beats no_graph in 23/90 comparisons (not majority) |
| E5 BASELINE_RELEVANCE | FAIL | HERALD beats ffill 81/180 comparisons (not majority; but TM@75 novel_lag2 alone DOES beat ffill) |
| E6 MULTITASK_VALUE | FAIL | GRAPH_MASKED_MULTITASK 0/10 better than TEMPORAL_MASKED (variance collapse) |
| E7 FEWSHOT_VALUE | PASS | Few-shot beats zero-shot 90/90 comparisons |
| E8 GRAPH_PRESERVATION | PASS | AUC preserved after few-shot 972/1080 comparisons |
| E9 REPLICATION | FAIL | GRAPH_MASKED_MULTITASK never beats NO_PRETRAINING (0/5 seeds) |
| E10 BLOCK_ROBUSTNESS | FAIL | Block_30 gain 0/5 seeds |

**300-epoch trigger**: FIRES (E1+E2 PASS at 150). However, only TEMPORAL_MASKED warrants extension. GRAPH_MASKED_MULTITASK is unstable at scale. **300-epoch run NOT launched** (requires explicit user authorization per project protocol).

---

## 7. Decision

**`TEMPORAL_MASKED_CONFIRMED; GRAPH_MULTITASK_UNSTABLE`**

**Bug A was the critical fix**: TEMPORAL_MASKED now works as designed and beats the ffill baseline in zero-shot evaluation on novel_lag2 (MAE 0.2327 vs 0.2568). DEC-049's conclusion that "pretraining hurts" was an artefact of Bug A.

**New finding from Bug B/C fix**: GRAPH_MASKED_MULTITASK with pos_weight edge BCE is unstable at scale (50 datasets, 75+ epochs). The multitask objective needs gradient clipping or a reduced pos_weight. This is a separate problem requiring a new DEC if GRAPH_MASKED_MULTITASK is pursued further.

**Few-shot A1**: Extremely effective (78-80% MAE reduction) regardless of pretraining. The decoder calibration mechanism is powerful — suggests that for few-shot use cases, the attention encoder pretraining matters less than decoder initialization quality.

**Remaining open problems**:
1. TEMPORAL_MASKED beats ffill only on novel_lag2, not novel_highvar (structural break dynamics)
2. Graph signal (E4) still not exploited in zero-shot reconstruction (herald_lagged ≈ no_graph)
3. AUC (E3) below threshold — edge recovery needs more work
4. GRAPH_MASKED_MULTITASK training instability requires gradient clipping investigation
