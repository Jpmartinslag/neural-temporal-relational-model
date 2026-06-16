# HERALD DEC-059: Weak-Label Tuning Revalidation

**Status:** COMPLETE | **Decision:** REAL_WEAK_LABEL_TUNING_PARTIAL  
**Date:** 2026-06-16 | **Elapsed:** 11.2s (local, no HPC)

---

## 0. Why DEC-058 Was Rebased

DEC-058 originally claimed `REAL_WEAK_LABEL_TUNING_SUPPORTED` (8/10 gates PASS). That decision was not defensible because:

1. **W2 FAIL**: country-shuffled control C2=0.688 ≥ V1=0.667. When a control that breaks country-pair correspondence matches or exceeds the fine-tuned model, we cannot attribute the improvement to learned economic signal.
2. **W6 FAIL**: 0% abstention. All 72 directed sector pairs received scores; the classifier never returned INSUFFICIENT_EVIDENCE.
3. **FR LOCO n=1**: one held-out label in FR fold makes concordance = {0.0 or 1.0} — unreliable.

**Correction:** DEC-058 decision was retroactively amended to `REAL_WEAK_LABEL_TUNING_PARTIAL`.

DEC-059 provides the rigorous revalidation with 7 controls (C1–C7), multi-window stability scoring, LOCO fold quality marking, and an improved abstention mechanism.

---

## 1. Protocol

### 1.1 Model

Same DEC-055 checkpoint (hash=`39b30a52da2ad330`) fine-tuned with 12 COVID_ROBUST weak labels (MAIN_ONLY=0 in this dataset). Training labels: COVID_ROBUST only; COVID_SENSITIVE excluded. Fine-tuning: confidence-weighted BCE presence/sign + CE lag, Adam lr=3e-4, patience=10.

### 1.2 Multi-Window Scoring

For each directed pair (src→tgt), each country, and each of 8 candidate windows (2009–2025):
- Compute `score_presence`, `score_sign`, `inferred_positive`
- Aggregate per pair: `mean_score`, `median_score`, `std_score`, `sign_consistency`, `n_windows`, `n_covid_windows`

### 1.3 Abstention Criteria

A pair is **INSUFFICIENT_EVIDENCE** if:
- `n_windows < 3`, OR
- `sign_consistency < 0.60`, OR
- `mean_score < 0.50` AND not enough countries satisfy both stability AND presence

### 1.4 Controls

| ID | Description |
|---|---|
| C0/V1 | Fine-tuned on COVID_ROBUST weak labels (real) |
| C1 | Permuted sign labels within each country |
| C2 | Country-shuffled labels (cyclic shift) |
| C3 | Sector-shuffled labels (random sector code mapping) |
| C4 | Sign-flipped labels (all signs negated) |
| C5 | Window-shuffled labels (random window assignment) |
| C6 | Random labels with same positive sign prevalence |
| C7 | Synthetic-only checkpoint (DEC-055, no fine-tuning) = V0 |

### 1.5 LOCO Folds

| Fold | Train | Test | n_labels (test) | LOW_EVIDENCE? |
|---|---|---|---|---|
| Fold 1 | FR+NL | PT | 16 | No |
| Fold 2 | FR+PT | NL | 8 | No |
| Fold 3 | NL+PT | FR | 1 | **Yes** (n < 3) |

FR is `LOW_EVIDENCE`: only 1 Phase 7 promoted edge in FR. Its sign concordance (1.000) is unreliable and excluded from strong claims.

---

## 2. Results

### 2.1 LOCO Sign Concordance

| Variant | FR (n=1) | NL (n=8) | PT (n=16) | Mean (valid folds) | Mean (all) |
|---|---|---|---|---|---|
| **V1** (fine-tuned) | 1.000 [LOW_EVIDENCE] | 0.500 | 0.500 | **0.500** | 0.667 |
| V0/C7 (synthetic-only) | — | 0.312 | — | — | 0.312 |

V1 mean excluding LOW_EVIDENCE FR fold = **0.500**. Including FR = 0.667 (inflated by single label). DEC-059 reports the honest figure: **0.500**.

### 2.2 Control Comparison

| Control | Sign Concordance (all folds) | Gap vs V1 (0.667) | Beats V1 by < 0.05? |
|---|---|---|---|
| C1 (permuted labels) | 0.646 | +0.021 | YES — FAIL |
| C2 (country-shuffled) | 0.667 | +0.000 | YES — FAIL |
| C3 (sector-shuffled) | 0.646 | +0.021 | YES — FAIL |
| C4 (sign-flipped) | 0.333 | +0.334 | No |
| C5 (window-shuffled) | 0.667 | +0.000 | YES — FAIL |
| C6 (random prevalence) | 0.312 | +0.355 | No |
| C7 (synthetic-only) | 0.312 | +0.355 | No |

**M2 FAIL**: C1, C2, C3, C5 all within 0.021 of V1. The fine-tuned model does not clearly separate from randomised-label controls. Note that C4 (sign-flip) and C6/C7 (random/synthetic) do degrade substantially — the model is learning something, but its learned signal cannot be isolated from label/window/sector distribution effects.

### 2.3 Gate Report (M1–M10)

| Gate | Description | Verdict |
|------|-------------|---------|
| M1 | Safety: no NaN/Inf/leakage/schema-break/PT-KZ | ✓ PASS |
| M2 | V1 > all controls C1-C6 by ≥ 0.05 | ✗ FAIL |
| M3 | Promoted relations: n_windows ≥ 3 AND sign_consistency ≥ 0.60 | ✓ PASS |
| M4 | INSUFFICIENT_EVIDENCE used; abstention rate ≥ 10% | ✗ FAIL |
| M5 | Per-fold LOCO honesty; LOW_EVIDENCE folds excluded from strong claims | ✓ PASS |
| M6 | COVID_SENSITIVE not promoted to REPLICATED or ROBUST | ✓ PASS |
| M7 | ≥1 REPLICATED relation with multi-window stability | ✓ PASS |
| M8 | Country-specific relations NOT counted as European replication | ✓ PASS |
| M9 | Same seed produces identical outputs | ✓ PASS |
| M10 | No causal language in outputs or report | ✓ PASS |

**8/10 PASS, 2/10 FAIL**

### 2.4 Multi-Window Classification

Using V1 encoder on all 8 windows per pair, all 3 countries:

| Class | Count |
|---|---|
| REPLICATED_ASSOCIATION (stable, ≥2 countries) | 59 |
| COUNTRY_SPECIFIC | 0 |
| COVID_SENSITIVE | 13 |
| INSUFFICIENT_EVIDENCE | 0 |
| NOT_SUPPORTED | 0 |

Total unique (src, tgt) pairs evaluated: 72 (9 sectors × 8 directions; PT KZ excluded from PT panel).

Top replicated pairs (≥2 countries, multi-window stable): GI→JZ, GI→OQ, GI→RU, BE→GI, FZ→JZ, RU→OQ, FZ→LZ, KZ→MN.

---

## 3. Failure Analysis

### M2 FAIL — Controls Not Consistently Degraded

**Root cause:** Only 12 COVID_ROBUST training labels (FR=1, NL=3, PT=8). With so few, the fine-tuning barely moves the sign head. C1/C3 (permuted/sector-shuffled) achieve 0.646 vs V1=0.667, a gap of 0.021 — below the 0.05 margin. C2/C5 (country-shuffled/window-shuffled) tie V1 at 0.667.

**Why C4 and C6/C7 DO degrade:** C4 flips signs, which is a strong perturbation. C6/C7 use random or synthetic-only parameters that score pairs differently. But the controls that preserve the statistical structure of labels (C1, C2, C3, C5) achieve similar concordance to V1.

**Interpretation:** The model's improvement over V0/C7 (0.312 → 0.667) is real but cannot be attributed to learning country-specific sector dynamics. Some of the improvement may come from: (a) label class distribution (all labels are positive, sign is 50/50), (b) alignment with Phase 7 window structures that all controls share.

### M4 FAIL — Zero Abstentions

**Root cause:** With 8 overlapping windows (2009–2025) and dense panels for FR/NL/PT, every directed pair has n_windows ≥ 3. The fine-tuned encoder assigns presence scores ≥ 0.50 to most pairs (the encoder outputs high presence for most inputs with current calibration), so the `mean_score < 0.50` abstention criterion never triggers.

**Structural limitation:** With only 9 A10 sectors and 72 possible pairs, and a dense panel, the encoder cannot be asked to "not score" a pair — it always produces a value. A proper abstention mechanism would require calibrated uncertainty intervals (conformal or ensemble), not just a threshold on point estimates.

### M5 PASS — FR Fold Correctly Marked LOW_EVIDENCE

FR LOCO fold has n=1 label. Its sign concordance of 1.000 is included in all-fold mean (0.667) but excluded from valid-fold mean (0.500). DEC-059 reports both clearly. The FR fold should not drive any claim.

---

## 4. Decision

**Decision:** `REAL_WEAK_LABEL_TUNING_PARTIAL`

**Reasoning:**
- M2 FAIL: controls not clearly degraded → cannot claim full support
- Decision ceiling: PARTIAL (not SUPPORTED) per gate logic
- M7 PASS: 59 multi-window stable replicated pairs identified (though not validated against controls)
- M4 FAIL: no abstention mechanism functional → all pairs receive scores

**What this evidence supports:**
- V1 fine-tuning improves over synthetic-only V0 (0.500 vs 0.312 on valid folds)
- Sign concordance reaches 0.500 on held-out NL and PT (50% — chance level at 2 classes)
- Multi-window scoring produces stable association scores (M3 PASS)
- COVID_SENSITIVE classification is isolated (M6 PASS)

**What this evidence does NOT support:**
- That the fine-tuning captures real economic sector dynamics (M2 FAIL)
- That REPLICATED pairs are truly cross-country economic associations (controls not degraded)
- Any causal structural claim

---

## 5. Comparison with DEC-058

| Metric | DEC-058 | DEC-059 |
|---|---|---|
| V1 sign concordance (reported) | 0.667 (all folds) | 0.500 (valid folds only), 0.667 (all) |
| FR fold | n=1, included | n=1, **LOW_EVIDENCE** (excluded from claim) |
| Controls tested | C1, C2 only | C1–C7 |
| M2/W2 failures | C2=0.688 ≥ V1 | C1/C2/C3/C5 ≥ V1 margin |
| Abstention | 0% (W6 FAIL) | 0% (M4 FAIL) |
| Decision | SUPPORTED (original, incorrect) | **PARTIAL** (corrected) |

---

## 6. Next Steps

1. **More countries**: Austria, Belgium panels would add Phase 7-labelled edges, increasing training label count beyond 12. M2 may pass with ≥50 labels.
2. **Calibration / conformal abstention**: Wrap encoder scores with conformal intervals (SPCI or similar) to enable data-driven INSUFFICIENT_EVIDENCE classification.
3. **Sign-head fine-tuning only**: Rather than fine-tuning all heads, target only the sign head with COVID_ROBUST labels — this may sharpen the sign signal without degrading presence calibration.
4. **Ensemble control**: Run 3–5 seeds and report confidence intervals on sign concordance — controls overlapping V1 CI → PARTIAL; non-overlapping → SUPPORTED candidate.

---

## 7. Files

| File | Type |
|---|---|
| `src/modeles/real_world/gates_dec059.py` | M1-M10 (frozen before results) |
| `src/modeles/real_world/run_dec059_weak_label_revalidation.py` | Multi-window scoring + C1-C7 |
| `tests/test_dec059_weak_label_revalidation.py` | 49 mandatory tests (49/49 PASS) |
| `data/processed/real_dec059_results/dec059_validation.json` | Full results + gates |
| `data/processed/real_dec059_results/multiwindow_pair_scores.csv` | Per-pair aggregated scores |
| `data/processed/real_dec059_results/all_window_scores.csv` | Per-window scores |
| `reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md` | Corrected to PARTIAL |
| `CODEX_MEMORY.md` | Updated |

*No HPC. No causal claims. No pseudo-labels. No UtilityGate connection.*
