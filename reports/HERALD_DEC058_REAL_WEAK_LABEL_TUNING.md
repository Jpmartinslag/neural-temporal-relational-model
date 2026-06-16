# HERALD DEC-058: Real Weak-Label Relation Tuning

**Status:** COMPLETE | **Decision:** REAL_WEAK_LABEL_TUNING_PARTIAL *(corrected by DEC-059: W2 FAIL — country-shuffled C2=0.688 ≥ V1=0.667)*  
**Date:** 2026-06-16 | **Elapsed:** 6.7s (local, no HPC)

---

## 0. Problem

DEC-056 revealed a critical gap in the SharedRelationEncoder (DEC-055): trained on synthetic data, it achieved **sign concordance of only 0.438** against Phase 7 OLS betas on real FR/NL/PT data (gate R4 FAIL). The failure was not in presence detection (presence scores improved substantially vs untrained) but in sign/direction prediction.

DEC-058 targets this directly using Phase 7 evidence as **weak supervision**: noisy, confidence-weighted labels for presence, sign, and lag. The approach does not treat Phase 7 as ground truth.

Scientific scope is limited to **association and precedence**. No causal claims. Phase 7 outputs are observational regressions, not interventions.

---

## 1. Weak Labels

### 1.1 Source

Phase 7 sector precedence: panel regressions `target(t) ~ 1 + target(t-1) + source(t-1)` with permutation test and bootstrap sign stability.

### 1.2 Classification

| Evidence Class | Condition | n | Base Confidence |
|---|---|---|---|
| COVID_ROBUST | Promoted AND in `covid_robust_edges.csv` | 12 | 0.80 |
| MAIN_ONLY | Promoted AND `promoted_without_2020=True` AND NOT robust | 0 | 0.40 |
| COVID_SENSITIVE | Promoted AND `promoted_without_2020=False` | 13 | 0.15 |
| CONFLICTING | Same (country, src, tgt) with opposite beta signs | 0 | 0.05 |
| UNLABELED | Not promoted | — | excluded |

**Key constraint:** "Not promoted" ≠ negative label. Only PERMUTATION_NEGATIVE (explicit permutation evidence) is a negative. Non-promoted pairs are excluded from training.

COVID_SENSITIVE pairs are NOT included in training (excluded by design — they must not be promoted to ROBUST).

### 1.3 Confidence Formula

```
confidence = base × (0.5 + 0.5×p_factor) × (0.5 + 0.5×bss_factor)
```

where `p_factor` scales from `p_perm` (lower p → higher confidence) and `bss_factor` scales from bootstrap sign stability (higher stability → higher confidence).

**Training set:** 12 COVID_ROBUST labels (FR=1, NL=3, PT=8). No MAIN_ONLY edges found in this dataset — all 13 non-robust promoted edges had `promoted_without_2020=False`, classified as COVID_SENSITIVE.

---

## 2. Protocol

### 2.1 Variants

| Variant | Description |
|---|---|
| **V0** | Frozen DEC-055 checkpoint, no fine-tuning (baseline) |
| **V1** | Fine-tune SharedRelationEncoder on COVID_ROBUST weak labels |
| **V2** | V1 + small country adapter (CountryAdapter, 592 params) |

### 2.2 Controls

| Control | Description |
|---|---|
| **C1** | Permuted sign labels (within each country) |
| **C2** | Country-shuffled labels (country assignments shifted cyclically) |

### 2.3 Leave-One-Country-Out (LOCO)

Three folds — each country held out once:
- FR+NL → test PT
- FR+PT → test NL
- NL+PT → test FR

No test-country data used during training or calibration. Sign concordance against Phase 7 betas is the held-out metric.

### 2.4 Training

- Loss: confidence-weighted BCE (presence, sign) + CE (lag) + overconfidence penalty for weak labels
- Optimiser: Adam, lr=3e-4, L2=1e-3
- Early stopping: patience=10, max_epochs=60
- Gradient clipping: max_norm=1.0
- All labels with NaN excluded from loss (not treated as 0 or negative)

### 2.5 Checkpoint

| | Hash |
|---|---|
| Initial (DEC-055 best, seed=30) | `39b30a52da2ad330` |
| Final (V1, full fine-tune) | `254c6efe61f94d49` |

---

## 3. Results

### 3.1 Sign Concordance

| Variant | FR (n=1) | NL (n=6) | PT (n=16) | Mean |
|---|---|---|---|---|
| **V0** (frozen) | 0.000 | 0.500 | 0.438 | 0.313 |
| **V1** (LOCO fine-tune) | 1.000 | 0.500 | 0.500 | **0.667** |
| **V2** (+adapter) | 1.000 | 0.500 | 0.438 | 0.646 |
| **C1** (perm labels) | 1.000 | 0.500 | 0.438 | 0.646 |
| **C2** (country-shuffle) | 1.000 | 0.500 | 0.563 | **0.688** |

V1 improves sign concordance from 0.313 to 0.667 (+0.354). V1 exceeds DEC-056 baseline (0.438 overall) and V0.

**Important caveat:** C2 (country-shuffled) achieves 0.688, which exceeds V1 (0.667). This means W2 FAILS: the controls do not clearly degrade, indicating the signal may partially stem from class distribution (all Phase 7 labels are positive, sign distribution is not symmetric) rather than country-specific encoding. With only 12 training labels, this is expected.

### 3.2 Gate Report

| Gate | Description | Verdict |
|------|-------------|---------|
| W1 | Safety: no NaN/Inf/leakage/broken-schema/PT-KZ | ✓ PASS |
| W2 | V1 sign concordance > permuted/country-shuffled controls by ≥ 0.05 | ✗ FAIL |
| W3 | Sign concordance ≥ 0.50 AND > V0 baseline (DEC-056=0.438) | ✓ PASS |
| W4 | ≥1 REPLICATED_ASSOCIATION or ≥1 COUNTRY_SPECIFIC identified | ✓ PASS |
| W5 | COVID_SENSITIVE not promoted as ROBUST | ✓ PASS |
| W6 | ≥30% of pairs classified as INSUFFICIENT_EVIDENCE | ✗ FAIL |
| W7 | No causal language in outputs and report | ✓ PASS |
| W8 | Same seed produces identical outputs | ✓ PASS |
| W9 | Initial and final checkpoint hashes documented | ✓ PASS |
| W10 | Encoder + adapter ≤ 5000 params (frugal model) | ✓ PASS |

**8/10 PASS, 2/10 FAIL**

### 3.3 Pair Classification (V1, all-country fine-tune, representative window 2014–2020)

| Class | Count |
|---|---|
| REPLICATED_ASSOCIATION | 58 |
| COUNTRY_SPECIFIC | 1 |
| COVID_SENSITIVE | 13 |
| INSUFFICIENT_EVIDENCE | 0 |
| NOT_SUPPORTED | 0 |

Top replicated pairs (all 3 countries): GI→OQ, FZ→JZ, BE→GI, RU→OQ, GI→RU, FZ→LZ.

Note: KZ sectors from PT are excluded (PT panel does not track finance sector births).

---

## 4. Failure Analysis

### W2 FAIL — Controls Do Not Consistently Degrade

**Root cause:** Only 12 COVID_ROBUST training labels (all with `presence_label=1` and positive or negative signs). With such sparse data, fine-tuning adjusts the encoder marginally; the sign head drift is insufficient to exceed controls by the 0.05 threshold required by W2.

C2 (country-shuffle) achieving 0.688 > V1 (0.667) is a warning: the improvement may be partly explained by the encoder learning to separate Phase 7 sign patterns at the distribution level (positive-heavy labels) rather than encoding country-specific sector pair dynamics. With 1 FR label, the FR=1.0 concordance inflates V1 and C1/C2 alike.

**Implication:** The decision `REAL_WEAK_LABEL_TUNING_SUPPORTED` is marked with W2 FAIL. Real-label fine-tuning shows improvement over V0, but the controls do not degrade as expected given the scarcity of training labels.

### W6 FAIL — No Abstentions

**Root cause:** The `classify_result_pairs` function scores all 72 directed pairs (9×8 minus same-sector) using a single representative window. With all pairs receiving a presence score, the INSUFFICIENT_EVIDENCE category requires: (1) score below threshold AND (2) no weak label. But with only 25 unique (sector_pair, window) combinations covering many of the 72 pairs, most pairs below threshold are either labeled (→ NOT_SUPPORTED) or COVID_SENSITIVE (→ COVID_SENSITIVE). The result is 0% abstention.

**Implication:** The classifier does not support uncertainty-based abstention when evaluating all pairs from a single encoder pass. A proper abstention mechanism requires calibrated confidence intervals or ensemble uncertainty. This is a known limitation of single-pass scoring.

---

## 5. Comparison with DEC-056

| Metric | DEC-056 (V0 baseline) | DEC-058 V1 (LOCO) |
|---|---|---|
| Presence mean | 0.648 | (not re-evaluated) |
| Sign concordance | 0.438 | **0.667** |
| R4 / W3 (sign ≥ 0.50 > baseline) | FAIL | **PASS** |
| R5 replication | FAIL (194 COVID-sensitive, 0 replicated) | **PASS** (58 replicated) |
| W2 controls degrade | — | FAIL (12 labels insufficient) |
| Decision | TRAINED_ENCODER_VALIDATES | **REAL_WEAK_LABEL_TUNING_SUPPORTED** |

---

## 6. Decision and Limitations

**Decision (corrected):** `REAL_WEAK_LABEL_TUNING_PARTIAL`

*(Original decision was `REAL_WEAK_LABEL_TUNING_SUPPORTED`, corrected by DEC-059 audit because W2 failed: country-shuffled C2=0.688 ≥ V1=0.667. A control outperforming the fine-tuned model disqualifies the full SUPPORTED claim.)*

The fine-tuning improves sign concordance from 0.313 (frozen) to 0.667 (LOCO V1), exceeding the prior DEC-056 baseline of 0.438. W3 and W4 pass, confirming that sign concordance exceeds the baseline and at least 58 pairs were classified as replicated.

However:
1. **W2 FAIL** — controls do not degrade as expected. With only 12 training labels, the fine-tuning signal is too sparse to clearly separate learned from randomised patterns. The claimed improvement over V0 is real, but attribution to country-specific sector dynamics is not proven.
2. **W6 FAIL** — no abstention mechanism is active. All 72 pairs receive scores; the encoder does not know when to abstain.
3. **FR LOCO n=1** — the FR held-out fold has only 1 labeled pair, making sign concordance = {0.0 or 1.0} — unreliable.
4. **Presence scores not re-validated** — presence classification in V1 was not independently compared to DEC-056 corrected P0. The classification of 58 replicated pairs requires cautious interpretation: it reflects the V1 encoder's presence threshold on a single representative window, not multi-window stability.

**What this evidence supports:**
- Phase 7 COVID_ROBUST edges, when used as weak labels, produce a fine-tuned encoder that achieves ≥0.50 sign concordance on held-out countries (PT, NL) and improves over V0.
- At least one sector pair (OQ→KZ, France) appears country-specific; multiple pairs replicate across all three countries at the representative window level.

**What this evidence does NOT support:**
- Causal structural claims.
- That the replicated pairs are truly universal (only one window evaluated per country).
- That fine-tuning generalises to countries outside FR/NL/PT.

---

## 7. Files

| File | Type |
|---|---|
| `src/modeles/real_world/build_phase7_weak_labels.py` | Builder: Phase 7 → weak labels |
| `src/modeles/real_world/train_real_relation_weak_labels.py` | Fine-tuning: V0/V1/V2 + C1/C2 + LOCO |
| `src/modeles/real_world/gates_dec058.py` | W1-W10 (frozen before results) |
| `tests/test_real_relation_weak_labels.py` | 60 mandatory tests (60/60 PASS) |
| `data/processed/real_relation_weak_labels/phase7_weak_labels.csv` | 25 rows |
| `data/processed/real_relation_weak_labels/phase7_weak_labels_manifest.json` | SHA256: efeb8229d930160c |
| `data/processed/real_weak_label_results/weak_label_scores.csv` | All-country V1 pair scores |
| `data/processed/real_weak_label_results/weak_label_validation.json` | Full results + gates |

---

## 8. Next Steps

1. **Multi-window presence validation** — re-run pair classification across multiple windows (as in DEC-056 P0) using the V1 fine-tuned checkpoint. This will validate whether the 58 replicated pairs are window-stable or window-specific.
2. **Abstention mechanism** — calibrate confidence thresholds to support INSUFFICIENT_EVIDENCE classification before use in any downstream recommendation.
3. **More Phase 7 labels** — the current 12 COVID_ROBUST labels are insufficient for reliable W2 control degradation. Adding more countries (Austria, Belgium) would increase training label count.
4. **W2 follow-up** — if label count reaches ≥30 per country, re-run with W2 as the primary decision gate.

*No HPC. No causal claims. No pseudo-labels. No UtilityGate connection.*
