# HERALD — Few-shot Adaptation Protocol Contract
**DEC-047 | Data: 2026-06-13 | Status: FROZEN BEFORE EXECUTION**

> This document defines the DEC-047 evaluation protocol. Gates A1-A10, thresholds and decision vocabulary are FROZEN and may not be modified after first pilot execution.

---

## 1. Scientific Question

Given a model trained on synthetic linear/mixed scenarios (Phase 11, T2 strategy):
- Can few-shot adaptation of the MLP decoder (with frozen attention matrices) improve imputation on novel scenarios (novel_lag2, novel_highvar)?
- Does the learned graph structure (AUC=0.611 from DEC-045) provide measurable benefit over no-graph baselines when the decoder is adapted?
- At what fraction K% of observed labels does adaptation benefit become reliable?
- Does a bottleneck adapter (A2) outperform full decoder fine-tuning (A1)?

**Hypothesis (falsifiable):** With K=5% labels from the target domain and frozen attention matrices, at least one adapted strategy achieves MAE < zero-shot MAE on novel_lag2 in >= 50% of evaluations.

---

## 2. Scenarios

| Scenario | frac_nonlinear | forced_lag | territory_radius | n_years | n_sectors | n_territories |
|----------|---------------|-----------|-----------------|---------|-----------|---------------|
| novel_lag2 | 0.85 | 2 | 0.25 | 20 | 9 | 30 |
| novel_highvar | 0.90 | None | 0.42 | 20 | 9 | 30 |

Both scenarios are novel (never seen in Phase 11 training). novel_lag2 is the primary pilot scenario.

**Pilot:** novel_lag2 only, dataset_seeds=[1000, 2000, 3000], k_fracs=[0.0, 0.05, 0.10].

---

## 3. Strategies and Freeze Policies

| Strategy | Attention | net[0] (10→64) | net[1-4] | Adapter | net[-1] (→2) | Description |
|----------|-----------|----------------|----------|---------|-------------|-------------|
| Z0 | FROZEN | FROZEN | FROZEN | — | FROZEN | Zero-shot, no adaptation |
| A1 | FROZEN | trainable | trainable | — | trainable | Decoder-only fine-tuning |
| A2 | FROZEN | FROZEN | FROZEN | trainable | trainable | Adapter + output only |
| A3 | trainable | FROZEN | trainable | — | trainable | Attention unfrozen + decoder |
| A4 | trainable | trainable | trainable | — | trainable | Full fine-tuning |
| C0 | FROZEN | trainable | trainable | — | trainable | Decoder, adj_s=0 (no graph) |
| P0 | FROZEN | trainable | trainable | — | trainable | Decoder, permuted adj (wrong graph) |
| B0 | — | — | — | — | — | Forward fill baseline |
| B1 | — | — | — | — | — | Ridge regression baseline |

**Attention parameters:** log_sect_attn_lag1, log_sect_attn_lag2, log_terr_attn

---

## 4. Adapter Architecture Specification

```
AdapterBottleneck(dim=32, bottleneck=16):
  x → Linear(32, 16) → GELU → Linear(16, 32) → + x  (residual)

Param count: 2 * 32 * 16 + 32 + 16 = 1072 parameters

Insertion point (A2 only):
  Original net: [L0, ReLU, Drop, L3, ReLU, L5]
                  0    1     2    3    4    5
  Adapted net:  [L0, ReLU, Drop, L3, ReLU, Adapter, L5]
                  0    1     2    3    4       5       6
```

Full model param count (HERALDGraphImputerLagged):
- log_sect_attn_lag1: 9×9 = 81
- log_sect_attn_lag2: 9×9 = 81
- log_terr_attn: 30×30 = 900
- net: Linear(10,64)+Linear(64,32)+Linear(32,2) + biases ≈ 3,106
- Total: ~4,168 parameters

---

## 5. Few-shot Fraction Table

Estimated absolute label counts for novel_lag2 (n_T=30, n_S=9, n_Y=20, ~70% observed):

| k_frac | Estimated n_labels | EXTREME_LOW_SHOT flag |
|--------|-------------------|-----------------------|
| 0.0 | 0 | — (zero-shot) |
| 0.01 | ~38 | if <5: YES |
| 0.05 | ~189 | NO |
| 0.10 | ~378 | NO |
| 0.20 | ~756 | NO |

Effective cells in support window (65% of n_Y=13 years × 30 × 9 × 0.70): ~2,457 observed cells.

---

## 6. Temporal Split Specification

For n_years=20:
- support_years: [0, 1, ..., 12] — first 65% (13 years)
- val_years: [13, 14, 15] — next 15% (3 years)
- test_years: [16, 17, 18, 19] — last 20% (4 years)

**Key invariants:**
- Support cells: observed (obs_mask=1) in support_years only
- Val cells: observed (obs_mask=1) in val_years — for early stopping only
- Evaluation target: HIDDEN (obs_mask=0) cells in test_years
- Zero overlap guaranteed by verify_disjoint_splits()

---

## 7. Evaluation Protocol

### Primary metrics (on hidden test cells):
- MAE (primary)
- RMSE
- Spearman rank correlation
- Sign accuracy

### Graph preservation metrics (on attention matrices):
- auc_before, auc_after: edge AUC before/after adaptation
- auc_change = auc_after - auc_before
- attn_correlation: Pearson correlation of attention weights before/after
- mean_weight_change: mean absolute change in attention weights
- graph_preserved: bool, True if auc_change >= -0.05

### Adaptation protocol:
- Loss: Gaussian NLL on support cells (same as Phase 11)
- Optimizer: Adam, lr=1e-3
- Early stopping: patience=15 on val NLL (pilot: patience=10, epochs=50)
- No optimizer state at evaluation time

---

## 8. Gates A1-A10 (Frozen Thresholds)

| Gate | Name | Condition | Threshold |
|------|------|-----------|-----------|
| A1 | SAFETY | zero leakage, NaN=0, n_hidden>0 | 100% |
| A2 | ADAPTATION_BENEFIT | adapted_mae < z0_mae in ≥ 50% of combos | 50% |
| A3 | GRAPH_CONTRIBUTION | graph strategy < C0 and P0 in ≥ 50% | 50% |
| A4 | BASELINE_RELEVANCE | neural < B0 and B1 in ≥ 50% (informational) | 50% |
| A5 | FEWSHOT_EFFICIENCY | benefit at k_frac ≤ 0.10 in ≥ 50% | k≤0.10 |
| A6 | GRAPH_PRESERVATION | auc_change ≥ -0.05 for all adapted strategies | -0.05 |
| A7 | BLOCK_ROBUSTNESS | result holds in block_30 mask | 50% |
| A8 | REPLICATION | effect direction consistent in ≥ 4/5 seeds | 4/5 |
| A9 | ADAPTER_VALUE | A2 MAE < A1 MAE in ≥ 50% | 50% |
| A10 | FINETUNING_TRADEOFF | A4 better iff graph not degraded | 50% |

---

## 9. Decision Vocabulary

| Decision | Condition |
|----------|-----------|
| ADAPTER_FEWSHOT_SUPPORTED | A2+A3+A8+A9 PASS |
| FULL_FINETUNING_SUPPORTED | A2+A3+A8+A10 PASS (graph preserved) |
| DECODER_ONLY_SUPPORTED | A2+A3+A8 PASS |
| GRAPH_PRESERVATION_FAILED | A6 FAIL (any strategy) |
| FEWSHOT_ADAPTATION_PARTIAL | A2 PASS but A5 FAIL |
| FEWSHOT_ADAPTATION_FAILED | A2 FAIL |

---

## 10. Out of Scope

The following are explicitly OUT OF SCOPE for DEC-047:

- Masked pretraining (PATH 2 in DEC-046) — separate DEC needed
- EnbPI/conformal calibration — deferred until reconstruction strategy chosen
- GRIN or SAITS implementation — classified as SECONDARY_BASELINE (deferred)
- Application to FR/NL/PT real data — requires pilot PASS first
- novel_highvar scenario — included in full run, not pilot
- HPC grid search — pilot is unambiguous at local scale
- MAML / meta-learning — too few meta-tasks (see DEC-046)
- Geographic graph (queen-contiguity) — CLOSED (DEC-010/011)

---

## 11. Safety Invariants

1. **No leakage:** support_mask ∩ imputation_test_mask = 0 (checked at every evaluate_one)
2. **No optimizer at Z0:** zero-shot evaluation never calls optimizer
3. **Hash integrity:** checkpoint_hash verified before AND after evaluation
4. **Temporal order:** support < val < test (strictly non-overlapping year windows)
5. **No test statistics:** no normalization or feature computation uses test cells
6. **Frozen protocol:** gates, thresholds, seeds frozen before execution
7. **A1 gate is a hard stop:** if A1 FAIL, report and stop (leakage is fatal)
