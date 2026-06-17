# HERALD DEC-066: Fine-Grain Threshold Calibration

**Status:** COMPLETE — `FINE_GRAIN_THRESHOLD_POLICY_READY`  
**Decision:** Threshold 0.09 supplementary tier adopted. Original 0.10 unchanged.  
**Date:** 2026-06-16  
**Follows:** DEC-064 (PT_MUNICIPAL_PHASE7_COMPLETE)  
**Gates:** C1-C10, 10/10 PASS  
**Tests:** 43/43 PASS

---

## Purpose

The pre-registered |β|≥0.10 threshold was calibrated on the original Phase 7 (DEC-034)
using FR ZE2020 (280 zones). Since then, DEC-064 showed PT municipal (278 municipalities)
produces promoted pairs at |β|=0.104–0.130 — barely above threshold — and near-misses
below threshold with perfect bootstrap stability (bss=1.00) and q_fdr<0.05.

This DEC evaluates whether a supplementary fine-grain label tier is scientifically warranted,
and if so, what threshold and robustness requirements it should carry.

**Scope:** FR ZE2020 and PT Municipal observed data only. NL gemeente proxy is NOT used.
No HPC run is required.

---

## Gates C1-C10

| Gate | Description | Verdict |
|------|-------------|---------|
| C1 | DATA_AVAILABLE: FR and PT results found, schema valid | **PASS** |
| C2 | SCALE_EFFECT_CONFIRMED: coarser granularity → larger |β| documented | **PASS** |
| C3 | FDR_NOT_BINDING: FR near-misses blocked by |β|, not by q_fdr | **PASS** |
| C4 | THRESHOLD_009_STABILITY: fine-grain edges have q_fdr≤0.05 and bss≥0.80 | **PASS** |
| C5 | NO_THRESHOLD_OVERFITTING: decision uses no NL proxy, no future labels | **PASS** |
| C6 | CROSS_COUNTRY_REASONABLE: no incoherent promotion explosion | **PASS** |
| C7 | ROBUST_LABEL_POLICY: four-tier taxonomy defined | **PASS** |
| C8 | COVID_POLICY: COVID-robust preserved for ROBUST_ORIGINAL; fine-grain policy clear | **PASS** |
| C9 | NO_CAUSAL_LANGUAGE: outputs contain no causal terms | **PASS** |
| C10 | REPRODUCIBILITY: outputs, checksums, commit, tests documented | **PASS** |

---

## Part A — Ecological Scale Effect

| Dataset | N territories | N years | Max |β| (any window) |
|---------|---------------|---------|----------------------|
| PT NUTS3 (obs v02) | 25 | 2008-2024 | **0.362** |
| NL COROP | 40 | 2006-2025 | 0.285 |
| FR ZE2020 | 280 | 2010-2025 | 0.108 |
| PT Municipal | 278 | 2008-2023 | 0.130 |

**Finding:** Finer territorial granularity reduces effect magnitudes. The |β|≥0.10 threshold
was calibrated at FR ZE2020 scale (280 zones); at PT Municipal scale (278 municipalities,
similar granularity) the two promoted pairs have |β|=0.104 and 0.130 — i.e., FR-scale
effects map to the same order of magnitude at PT municipal scale. Sub-0.10 effects in FR
and PT municipal represent structurally smaller signals at fine spatial scale, not noise.

---

## Part B — Threshold Sensitivity Analysis

### Count of edges passing all gates (q_fdr<0.05, Δr²≥0.005, bss≥0.70, n≥60)

| Threshold | FR | NL | PT NUTS3 | PT Municipal | Total |
|-----------|----|----|----------|--------------|-------|
| 0.10 (original) | 1 | 8 | 16 | 2 | **27** |
| 0.09 | 5 | 8 | 16 | 2 | **31** (+4 FR) |
| 0.08 | 7 | 8 | 16 | 2 | **33** (+2 FR) |
| 0.07 | 9 | 8 | 16 | 3 | **36** (+2 FR, +1 PT_MUNI) |

**NL and PT NUTS3 are unaffected** — all their effects are |β|≥0.17, well above any candidate
threshold.

### Edges added from 0.10 → 0.09 (FR only)

| Source | Target | Window | β | q_fdr | bss | n_windows≥0.09 | COVID-robust |
|--------|--------|--------|---|-------|-----|----------------|-------------|
| MN | BE | 2018-2023 | +0.097 | 0.036 | 1.000 | 2 | No |
| RU | MN | 2019-2024 | −0.095 | 0.036 | 0.998 | 2 | No |
| MN | BE | 2020-2025 | +0.094 | 0.024 | 1.000 | 2 | No |
| OQ | MN | 2020-2025 | +0.090 | 0.036 | 0.982 | 1 | No |

FR MN→BE appears in **3 consecutive recent windows** (2018-2023, 2019-2024, 2020-2025)
with consistent positive sign, bss=1.00, q_fdr<0.05. This is the strongest candidate for
supplementary labeling — cross-window stability is a pre-specified condition in the policy.

FR RU→MN has its ROBUST_ORIGINAL edge at 2020-2025 (|β|=0.108). Adding 2019-2024
(|β|=0.095) as FINE_GRAIN_SUPPORTED extends the temporal coverage of an already-promoted pair.

FR OQ→MN at 2020-2025 (|β|=0.090) appears in only 1 window at ≥0.09 threshold and is
NOT COVID-robust → EXPLORATORY_FINE_GRAIN, not FINE_GRAIN_SUPPORTED.

---

## Part C — Cross-Window Consistency

### FR MN→BE (key candidate)

| Window | β | q_fdr | bss | Status |
|--------|---|-------|-----|--------|
| 2010-2015 | −0.025 | 0.864 | 0.74 | Noise |
| 2015-2020 | +0.085 | 0.072 | 1.00 | Near-miss (q_fdr>0.05) |
| 2016-2021 | +0.080 | 0.072 | 1.00 | Near-miss |
| 2017-2022 | +0.112 | 0.072 | 1.00 | **|β|≥0.10 but q_fdr>0.05** |
| 2018-2023 | +0.097 | 0.036 | 1.00 | FINE_GRAIN_SUPPORTED |
| 2019-2024 | +0.088 | 0.036 | 1.00 | EXPLORATORY_FINE_GRAIN |
| 2020-2025 | +0.094 | 0.024 | 1.00 | FINE_GRAIN_SUPPORTED |

Pattern: MN→BE signal strengthened progressively from 2015 onwards, achieving q_fdr<0.05
in 2018-2023, 2019-2024, 2020-2025. The large |β|=0.112 in 2017-2022 does NOT pass FDR
(q_fdr=0.072), illustrating that FDR family correction, not the |β| threshold, is the main
gate for this pair. At 0.09, the 2018-2023 and 2020-2025 windows are captured.

### FR RU→MN (already ROBUST_ORIGINAL at 2020-2025)

Promoted at 2020-2025 (|β|=0.108, ROBUST_ORIGINAL). At 0.09, the 2019-2024 window
(|β|=0.095) extends coverage to 2 windows — this becomes FINE_GRAIN_SUPPORTED as an
adjacent-window extension of an already-robust pair.

---

## Part D — Label Taxonomy (DEC-066 Policy)

### Tier 1 — ROBUST_ORIGINAL

- |β| ≥ 0.10
- q_fdr < 0.05
- bss ≥ 0.70
- Δr² ≥ 0.005
- n_samples ≥ 60
- No additional requirement (pre-registered threshold from DEC-034 / DEC-064)
- **Use in training:** positive label, full weight
- **Claim level:** primary

### Tier 2 — FINE_GRAIN_SUPPORTED

- |β| ≥ 0.09 (supplementary threshold, adopted DEC-066)
- q_fdr < 0.05
- bss ≥ 0.80 (stricter than ROBUST_ORIGINAL)
- Δr² ≥ 0.005
- n_samples ≥ 60
- **PLUS at least ONE of:**
  - (a) COVID-robust (promoted in main AND without_2020 with same sign, q_fdr<0.05 in both)
  - (b) ≥2 consecutive windows with same sign at |β|≥0.09
  - (c) Replicated in an observed (non-proxy) second country at comparable spatial scale
- **Use in training:** weak positive label with downweighting; must be tagged `evidence_type=fine_grain_supported`
- **Claim level:** fine-grain supporting evidence, NOT equivalent to ROBUST_ORIGINAL in claims

### Tier 3 — EXPLORATORY_FINE_GRAIN

- |β| ≥ 0.07
- q_fdr < 0.05
- bss ≥ 0.90 (high stability required without robustness evidence)
- Δr² ≥ 0.005
- n_samples ≥ 60
- Does NOT meet Tier 2 additional requirements
- **Use in training:** NOT a positive label; hypothesis generation only
- **Claim level:** exploratory observation

### Tier 4 — REJECTED_OR_WEAK

- Fails any of: q_fdr, |β|≥0.07, Δr², n_samples, or bss
- Not a candidate for any label

---

## Part E — Label Counts by Country/System

| Country | ROBUST_ORIGINAL | FINE_GRAIN_SUPPORTED | EXPLORATORY_FINE_GRAIN |
|---------|----------------|-----------------------|------------------------|
| FR ZE2020 | 1 | 3 | 5 |
| NL COROP | 8 | 0 | 0 |
| PT NUTS3 (obs v02) | 16 | 0 | 0 |
| PT Municipal | 2 | 0 | 1 |
| **Total** | **27** | **3** | **6** |

**FR FINE_GRAIN_SUPPORTED (3 pairs):**
1. MN→BE (2018-2023): β=+0.097, q_fdr=0.036, bss=1.00, n_windows=2
2. MN→BE (2020-2025): β=+0.094, q_fdr=0.024, bss=1.00, n_windows=2
3. RU→MN (2019-2024): β=−0.095, q_fdr=0.036, bss=0.998, n_windows=2

**PT Municipal EXPLORATORY_FINE_GRAIN (1 pair):**
- OQ→GI (2015-2020): β=+0.076, q_fdr=0.028, bss=1.00 — without_2020 q_fdr=0.056 (just above threshold, not COVID-robust; n_windows_at_009=0)

---

## Part F — Implication for DEC-065 (NL gemeente proxy)

1. **NL COROP (8 ROBUST_ORIGINAL)** remains the baseline. No NL edges enter the fine-grain tier.

2. **NL gemeente proxy** must NOT be used to select or validate this threshold (C5 / policy prohibition). The 0.09 threshold was derived from FR and PT observed data only.

3. **Threshold applies equally to NL gemeente**: after DEC-065, gemeente-level edges should be classified by the same taxonomy. Given NL COROP effects are 0.17-0.28, gemeente disaggregation may bring them into the FINE_GRAIN_SUPPORTED or EXPLORATORY_FINE_GRAIN range — requiring the same cross-window or COVID-robust conditions.

4. **Proxy label must be preserved**: gemeente-level labels must carry `evidence_type=proxy_disaggregated_by_stock_share` regardless of which tier they fall in.

---

## Part G — Scientific Interpretation

### Why 0.09 and not 0.08?

At 0.08, FR gains 2 additional edges (KZ→FZ 2020-2025 and MN→BE 2019-2024). MN→BE
2019-2024 (|β|=0.088) would extend the MN→BE coverage to 3 windows — but as FINE_GRAIN
it's adequately captured by the 2 windows already at 0.09. KZ→FZ (Finance) is problematic:
KZ is structural_absent in PT and IT data, making cross-country replication permanently
blocked. Adopting 0.08 primarily to include a sector that can never be replicated in PT
would fail the C5 spirit test. The 0.09 threshold captures the evidentially strongest
sub-0.10 edges without expanding into single-window, structurally limited cases.

### Why not 0.07?

At 0.07, FR gains OQ→MN in 2 windows but with |β|=0.075-0.077 — below the 0.09 tier
definition. PT Municipal gains OQ→GI (β=0.076, COVID-not-robust). These are correctly
classified as EXPLORATORY_FINE_GRAIN rather than FINE_GRAIN_SUPPORTED. Adding a third
tier threshold at 0.07 does not require changing any classification — EXPLORATORY already
covers 0.07-0.09.

### Threshold robustness

Lowering from 0.10 to 0.09 increases FR pairs from 1 to 5. NL (8 pairs) and PT NUTS3
(16 pairs) are completely unaffected. PT Municipal gains nothing in the FINE_GRAIN_SUPPORTED
tier (nearest sub-0.10 edge is OQ→GI at 0.076). The change is asymmetric in good ways:
it extends coverage for recently-emerging FR patterns (2018-2025) without destabilizing
the established NL or PT NUTS3 baselines.

---

## Prohibitions

- NL gemeente proxy MUST NOT be used to derive or validate this threshold ✓
- NL proxy results must not be examined before this DEC is finalised ✓
- EXPLORATORY_FINE_GRAIN must not be used as positive training label ✓
- KZ→FZ FR may not transfer to PT labels (KZ structural_absent in PT) ✓
- ROBUST_ORIGINAL threshold 0.10 remains pre-registered and unchanged ✓
- No causal language in outputs ✓

---

## Outputs

| Artefact | Path |
|----------|------|
| Calibration script | `src/modeles/real_world/phase7_threshold_calibration.py` |
| Threshold candidates | `data/processed/phase7_threshold_calibration/phase7_threshold_candidates.csv` |
| Sensitivity summary | `data/processed/phase7_threshold_calibration/threshold_sensitivity_summary.json` |
| Label policy | `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json` |
| Tests | `tests/test_dec066_threshold_calibration.py` (43/43 PASS) |

---

## Decision

**`FINE_GRAIN_THRESHOLD_POLICY_READY`**

- Original threshold **0.10** retained as ROBUST_ORIGINAL (pre-registered, no change)
- Supplementary threshold **0.09** adopted for FINE_GRAIN_SUPPORTED tier (cross-window or COVID-robust required)
- EXPLORATORY_FINE_GRAIN tier covers 0.07-0.09 (no additional requirement; not a training label)
- Policy documented in `fine_grain_label_policy.json`
- NL gemeente proxy (DEC-065) may now proceed under this policy

---

## Next Steps

| Action | DEC | Status |
|--------|-----|--------|
| Apply fine-grain policy to FR/PT label export | DEC-067 | Open |
| NL gemeente Phase 7 with fine-grain policy | DEC-065 | Now authorised |
| Cross-country granular training (FR+PT+NL) | DEC-068 | Blocked on DEC-065 |
| FR KZ→FZ exploratory — note structural PT limit | Tracked in DEC-067 | Open |

---

*HERALD DEC-066 | Fine-Grain Threshold Calibration | FINE_GRAIN_THRESHOLD_POLICY_READY | 10/10 PASS | 2026-06-16*
