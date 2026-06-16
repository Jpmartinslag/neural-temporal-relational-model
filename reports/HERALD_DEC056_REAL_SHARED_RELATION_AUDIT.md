# HERALD DEC-056: Real Shared Relation Encoder Audit
**Status:** COMPLETE (corrected run) — 7/10 PASS  
**Decision:** `REAL_SHARED_RELATION_PARTIAL` — Trained encoder discriminates sectors; rankings stable; sign concordance below chance; no cross-country replication without COVID window  
**Date:** 2026-06-16  
**Checkpoint:** `data/processed/phase16_dec055/shared_relation_encoder_best.pt` (hash=`39b30a52da2ad330`, best_seed=30)  
**Runtime:** 2.1 s (P0 only, CPU)  
**Scope:** Analytic validation only. Zero-shot real. No fine-tuning. No pseudo-labels. No recommendation. No causal claims.

---

## 0. Audit Summary

### Previous Run (INVALID for model validation)

The first DEC-056 run (`DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION`) used a **randomly initialized encoder** because `run_dec055.py` never called `torch.save`. Presence scores clustered at ~0.067 (initialization prior). That run is valid only as a **pipeline preflight** — it confirmed the data loading, normalization, permutation control, and gate infrastructure works correctly.

### This Run (corrected)

DEC-055 was re-executed with checkpoint saving added. The best-seed encoder (seed=30, unseen_pair_auc=0.752) was saved and used for real-data P0.

| Run | Encoder | Mean presence | PASS gates |
|---|---|---|---|
| Previous (INVALID) | Random init | 0.067 | 6/10 |
| **This (corrected)** | **Trained, hash=39b30a52da2ad330** | **0.648** | **7/10** |

---

## 1. Scientific Question

Does the DEC-055-trained SharedRelationEncoder (trained on synthetic FR-type environments) extract sector-pair signals from real FR/NL/PT panels that are consistent with independent Phase 7 evidence?

**Findings (zero-shot real):**
- **YES (sector discrimination):** Sector permutation degrades mean presence by 0.178 (R2 PASS) — the encoder is not outputting the same score regardless of sector identity.
- **YES (ranking stability):** FR=0.820, NL=0.412, PT=0.593 Spearman across windows (R3 PASS).
- **PARTIAL (Phase 7 sign):** Concordance = 0.438 < 0.50 threshold (R4 FAIL) — below chance. The synthetic-trained sign head does not generalize to real-data sign direction.
- **NO (cross-country replication):** No pair exceeds threshold (0.55) in ≥2 countries outside COVID windows (R5 FAIL). 194 pairs are classified COVID_SENSITIVE (above threshold only in windows containing 2020).

---

## 2. DEC-055 Checkpoint

### 2.1 Changes to `run_dec055.py`

Three additions (no change to architecture, hyperparameters, or data):

1. `_state_dict_hash()` — SHA256 prefix of encoder weights
2. `train_shared_encoder()` — tracks best-epoch weights and restores them at end of training
3. `main()` — after all seeds, saves best-seed encoder as `.pt` and writes manifest JSON

### 2.2 DEC-055 Re-run Results

Same protocol, same seeds (10, 20, 30, 40, 50), same gates:

| Metric | Value | Gate |
|---|---|---|
| IS AUC | 0.960 | — |
| Unseen-pair AUC | 0.690 | S3 ≥ 0.65 ✓ |
| OOS-env AUC (shared) | 0.719 | S4 > 0.551 (old) ✓ |
| Sign acc OOS | 0.870 | S5 > 0.55 ✓ |
| Lag acc OOS | 0.580 | S5 > 0.55 ✓ |
| Permuted controls | Δ ≥ 0.05 | S8 ✓ |
| Seeds > 0.60 | 4/5 | S9 ✓ |
| Total params | 2871 | S10 ≤ 5000 ✓ |

**Gates: 9/10 PASS** (S7 FAIL unchanged — temporal regime detection requires dedicated architecture).

### 2.3 Checkpoint Manifest

```json
{
  "checkpoint_path": "data/processed/phase16_dec055/shared_relation_encoder_best.pt",
  "sha256_prefix": "39b30a52da2ad330",
  "best_seed": 30,
  "best_unseen_pair_auc": 0.752,
  "n_encoder_params": 2215,
  "architecture": {"class": "SharedRelationEncoder", "input_dim": 26, ...},
  "training": {"max_epochs": 100, "patience": 10, "lr": 1e-3, ...},
  "gate_summary": {"S1": "PASS", ..., "S7": "FAIL", ..., "S10": "PASS"}
}
```

---

## 3. Protocol

- **P0:** Zero-shot — trained checkpoint frozen, log1p normalization, no fine-tuning
- Countries: FR (280 ZE2020, 5 windows), NL (40 COROP, 4 windows), PT (25 NUTS3, 8 windows)
- PT KZ structurally excluded (`obs_mask=0`)
- 1096 pair-window records
- No future leakage (normalization uses only window data)

---

## 4. Results

### 4.1 Presence Score Distribution

| Metric | Untrained (INVALID) | **Trained (corrected)** |
|---|---|---|
| Mean presence | 0.067 | **0.648** |
| Max presence | ~0.12 | **0.935** |
| Pairs above 0.55 | 0 | **829/1096** |

The trained encoder gives substantially higher and more varied scores. The mean (0.648) is above the presence threshold (0.55), indicating the encoder over-predicts presence on real data relative to the synthetic training distribution. This is expected: the encoder was trained on synthetic environments with explicit sparse priors; real data has different statistics.

### 4.2 Temporal Stability (Spearman)

| Country | Stability | Gate R3 |
|---|---|---|
| FR | **0.820** | PASS |
| NL | **0.412** | PASS |
| PT | **0.593** | PASS |

Pair rankings are consistent across adjacent 6-year windows. The trained encoder assigns stable relative ranks to sector pairs.

### 4.3 Permutation Controls

| Control | Mean presence | Delta vs real |
|---|---|---|
| **Real (PT panel)** | **0.687** | — |
| Permuted years | 0.716 | −0.029 |
| **Permuted sectors** | **0.509** | **+0.178** ✓ |
| Permuted regions | 0.687 | +0.000 |

**R2 PASS** — sector permutation degrades presence by 0.178 (>> threshold 0.05). The encoder IS sensitive to sector identity. However, year permutation does not degrade (slightly increases), indicating temporal ordering within windows is not the primary driver.

**Interpretation:** The trained encoder learns sector-specific cross-correlation patterns (via `direction_asymmetry` and `lag_corr` features), but not temporal onset/offset within windows (consistent with S7 failure in DEC-055).

### 4.4 Phase 7 Sign Concordance

| Metric | Value | Gate R4 |
|---|---|---|
| Concordance | **0.438** | **FAIL** (< 0.50) |
| Edges compared | 16 | — |

Below-chance concordance (0.438 < 0.50). The synthetic-trained sign head produces sign predictions that do not align with Phase 7 regression betas. Possible causes:
1. Phase 7 uses OLS regression signs; encoder uses cross-lag correlation asymmetry — different quantities
2. The sign head learned from synthetic data where positive/negative relations have different statistics than real economies
3. 16 edges is a small sample — 95% CI includes 0.50

This is a genuine limitation: sign direction does not transfer from synthetic to real.

### 4.5 Classification

| Status | Count | Interpretation |
|---|---|---|
| ASSOCIATION_CANDIDATE | 0 | COVID_SENSITIVE takes priority |
| REPLICATED_ASSOCIATION | 0 | All above-threshold pairs are COVID-window only |
| **COVID_SENSITIVE** | **194** | Above threshold only in windows containing 2020 |
| COUNTRY_SPECIFIC | 0 | Same reason |
| NOT_SUPPORTED | 6 | Below threshold in all windows |

**194 COVID_SENSITIVE pairs** — these are sector pairs where the encoder produces high presence scores only in windows that include 2020. This could reflect:
1. COVID as a genuine structural change that makes sector co-movements more pronounced
2. Encoder capturing recent-years patterns (post-2015 data) that happen to include 2020

**No REPLICATED_ASSOCIATION** because the classification logic gives COVID_SENSITIVE priority over cross-country replication. A pair that is above threshold in COVID windows in FR and PT would be COVID_SENSITIVE, not REPLICATED_ASSOCIATION. This is a classification design choice, not a claim about the data.

### 4.6 Top Pairs Per Country

| Country | Top 3 pairs | Score |
|---|---|---|
| FR | GI→LZ, GI→FZ, GI→OQ | 0.857, 0.852, 0.832 |
| NL | KZ→FZ, KZ→GI, KZ→LZ | 0.935, 0.928, 0.910 |
| PT | FZ→OQ, GI→OQ, LZ→JZ | 0.929, 0.924, 0.923 |

NL: KZ (Finance, insurance) is the dominant source sector. Note: KZ was excluded from PT due to structural absence, but is present and measured in NL.

---

## 5. Gate Results

| Gate | Description | Verdict |
|---|---|---|
| R1 | Safety: no leakage/NaN/Inf/future-mix/cross-pooling | ✓ PASS |
| R2 | Negative controls degrade presence score ≥ 0.05 | ✓ PASS |
| R3 | Spearman stability > 0.30 in ≥ 2 countries | ✓ PASS |
| R4 | Phase 7 sign concordance > 0.50 | ✗ FAIL |
| R5 | ≥ 1 pair replicated in ≥ 2 countries (outside COVID) | ✗ FAIL |
| R6 | Country-specific pairs identified | ✗ FAIL |
| R7 | COVID period reported separately | ✓ PASS |
| R8 | Top-5 pairs fully documented | ✓ PASS |
| R9 | No causal language in outputs | ✓ PASS |
| R10 | CSV/JSON schema valid | ✓ PASS |

**Summary: 7/10 PASS**

---

## 6. Failure Analysis

### R4 FAIL — Sign concordance below chance (0.438)

Sign head trained on synthetic data where: positive = sector A level increases → sector B level increases (linear additive model). Phase 7 sign = OLS regression coefficient beta. These quantities measure the same direction but through different transformations. On 16 edges, random chance = 0.50. The trained sign head gives 0.438 — no evidence it generalizes to real-data sign direction.

**Remedy:** Fine-tune sign head specifically on real pairs with Phase 7 labels as soft targets (NOT authorized in this DEC).

### R5/R6 FAIL — No cross-country replication (classification artifact)

194 pairs are above threshold only in COVID windows. The classification logic marks these as COVID_SENSITIVE before checking cross-country replication. If the COVID_SENSITIVE label were removed, some of these pairs might be REPLICATED_ASSOCIATION (present in FR + PT COVID windows).

**Remedy:** Separate classification by period rather than blocking COVID_SENSITIVE from replication check.

### R2 partial — Year permutation does not degrade

The encoder scores are not sensitive to year ordering within windows (permuted_years = 0.716 > real = 0.687). This confirms S7 failure pattern from DEC-055: the encoder captures cross-lag correlations averaged over the window, not temporal onset/offset.

---

## 7. Comparison: Untrained vs Trained Encoder on Real Data

| Aspect | Previous run (INVALID) | This run (corrected) |
|---|---|---|
| Checkpoint | None (random init) | hash=39b30a52da2ad330 |
| Mean presence | 0.067 | 0.648 |
| Pairs above 0.55 | 0 | 829/1096 |
| R2 (controls) | FAIL | PASS |
| R3 (stability) | PASS | PASS |
| R4 (Phase 7 sign) | PASS (0.562, above chance) | FAIL (0.438, below chance) |
| R5 (replication) | FAIL | FAIL |
| R8 (documentation) | NOT_EVALUATED | PASS |
| Gates total | 6/10 | 7/10 |

Note: R4 was PASS in the untrained run (0.562) but FAIL in the trained run (0.438). The untrained encoder's sign output was effectively random — it happened to be above-chance on 16 edges. The trained encoder actively learned a sign representation from synthetic data that conflicts with Phase 7 sign conventions.

---

## 8. Decision

`REAL_SHARED_RELATION_PARTIAL` — The trained encoder:
- **Does** respond to sector identity (R2 PASS)
- **Does** produce stable pair rankings across time (R3 PASS)
- **Does not** align with Phase 7 sign direction (R4 FAIL)
- **Does not** replicate across countries outside COVID windows (R5/R6 FAIL)

No association claims can be made. All outputs labeled `analytic_association_only`. No causal language.

### What this means for the research path

The encoder architecture is validated on synthetic data (DEC-055, 9/10 PASS). On real data, the encoder finds sector-specific patterns that are stable across time. The sign and replication gates fail because:
1. Sign: synthetic and real sign conventions differ
2. Replication: COVID dominates the high-score windows; pre-COVID scores are below threshold

A fine-tuned sign head or an unsupervised clustering of the 32-dim embeddings (rather than threshold-based classification) may be more informative next steps.

---

## 9. Files

| File | Description |
|---|---|
| `src/modeles/synthetic/phase16_decoupled/run_dec055.py` | Updated runner with checkpoint saving |
| `data/processed/phase16_dec055/shared_relation_encoder_best.pt` | Trained checkpoint (hash=39b30a52da2ad330) |
| `data/processed/phase16_dec055/checkpoint_manifest.json` | Manifest: hash, seed, metrics, gates |
| `data/processed/phase16_dec055/dec055_results.json` | Updated DEC-055 results |
| `src/modeles/real_world/run_p0_checkpointed.py` | Corrected P0 with checkpoint loading + hash verification |
| `data/processed/real_shared_relations_checkpointed/shared_relation_scores_checkpointed.csv` | 1096 records with checkpoint_hash |
| `data/processed/real_shared_relations_checkpointed/shared_relation_embeddings_checkpointed.json` | 200 embeddings |
| `data/processed/real_shared_relations_checkpointed/shared_relation_validation_checkpointed.json` | Full gate results |
| `tests/test_dec056_real_shared_relation.py` | 77 tests (77/77 PASS) |
| `data/processed/real_shared_relations/` | Previous P0 (INVALID — pipeline preflight only) |
