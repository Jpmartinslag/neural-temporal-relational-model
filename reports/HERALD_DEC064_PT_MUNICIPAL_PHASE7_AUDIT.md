# HERALD DEC-064: PT Municipal Phase 7 Sector Precedence Audit

**Status:** COMPLETE — 10/10 gates PASS  
**Decision:** `PT_MUNICIPAL_PHASE7_COMPLETE`  
**Date:** 2026-06-16  
**Follows:** DEC-063 (GRANULAR_FR_PT_NL_PREFLIGHT_READY)  
**Gates:** P1-P10, pre-registered before results observed (GATE_VERSION: DEC-064-v1)  
**HPC Job:** 7472757 (meso, 208/208 tasks complete)

---

## Summary

Phase 7 sector precedence was run at full scale (n_perm=999, n_boot=500) on 278 continental
Portuguese municipalities using `observed_births` (INE enterprise_birth, 2008–2023), across
13 rolling 6-year windows and 2 scenarios (main, without_2020). BH/FDR applied per family
(country × scenario × window).

**Key result:** 2 sector pairs promoted in the 2015-2020 window. Both pairs pass all 5 gates
and are COVID-robust (promoted in main AND without_2020 with same sign). The two pairs are
specific to the 2015-2020 period; no other window produces promoted pairs. Promoted pairs
appear against the background of the NUTS3 baseline of 0 promotions in all 14 windows —
confirming that granular spatial resolution increases statistical power at PT level.

---

## Gates P1-P10 (Full Run)

**GATE_VERSION:** DEC-064-v1 — thresholds frozen before observing any results.

| Gate | Description | Verdict |
|------|-------------|---------|
| P1 | Safety: no NaN/Inf, no temporal leakage, years ordered | **PASS** |
| P2 | Coverage: 278 municipalities, 8 observable sectors, KZ structural_absent | **PASS** |
| P3 | Observed-only: no proxy data mixed in | **PASS** |
| P4 | Reaggregation divergence vs NUTS3 documented | **PASS** |
| P5 | All 728 tested pairs have n_samples ≥ 60 (min=321) | **PASS** |
| P6 | Permutation control degrades signal (mean p_perm observed < 0.5 null) | **PASS** |
| P7 | Thresholds pre-registered (DEC-064-v1) | **PASS** |
| P8 | PT municipal vs PT NUTS3 comparison documented | **PASS** |
| P9 | No causal language in outputs | **PASS** |
| P10 | Manifest, SHA256, commit hash, commands documented | **PASS** |

Pre-registered thresholds (identical to original Phase 7, DEC-034):
- q_fdr < 0.05 (BH/FDR per family)
- |β| ≥ 0.10
- Δr² ≥ 0.005
- bootstrap sign stability ≥ 0.70
- n_samples ≥ 60

---

## HPC Run Summary

| Property | Value |
|----------|-------|
| Job ID | 7472757 (meso, partition=normal) |
| Tasks submitted | 208 (13 windows × 2 scenarios × 8 source sectors) |
| Tasks complete | 208/208 |
| Task status | all complete |
| Runtime range | 19.8 – 46.5 min/task |
| Runtime median | 36.5 min/task |
| Panel SHA256 | `19c4675bbf8323e0daab3ca1ca57e287ec7abd791cb9cedfce16c85db5008794` |
| Commit | `10a7890f5d56` (DEC-063) |
| n_permutations | 999 |
| n_bootstraps | 500 |
| Total edges tested | 1,456 (728 main + 728 without_2020) |

---

## Results: Promoted Edges

### Main scenario — all 5 gates pass

| Source | Target | Window | β | Δr² | p_perm | q_fdr | bss | n_samples |
|--------|--------|--------|---|-----|--------|-------|-----|-----------|
| GI | OQ | 2015-2020 | +0.130 | 0.0166 | 0.001 | 0.028 | 1.000 | 1,668 |
| MN | JZ | 2015-2020 | −0.104 | 0.0108 | 0.002 | 0.037 | 1.000 | 999 |

Both pairs: bootstrap_sign_stability = **1.000** (perfectly stable across 500 bootstrap resamples).

### COVID-robustness check (main AND without_2020, same sign)

| Source | Target | Window | β (main) | β (wo2020) | COVID-robust |
|--------|--------|--------|----------|------------|--------------|
| GI | OQ | 2015-2020 | +0.130 | +0.108 | **YES** |
| MN | JZ | 2015-2020 | −0.104 | −0.125 | **YES** |

Both pairs survive exclusion of 2020 with consistent sign and remain promoted in the
without_2020 scenario (q_fdr=0.028 for both in without_2020).

### Near-miss edge (q_fdr < 0.05, |β| < threshold)

| Source | Target | Window | β | q_fdr | bss | Gate fail |
|--------|--------|--------|---|-------|-----|-----------|
| OQ | GI | 2015-2020 | +0.076 | 0.028 | 1.000 | |β|=0.076 < 0.10 |

OQ→GI fails only the |β| threshold. This is the reciprocal direction of GI→OQ. The
two-way association pattern (GI↔OQ) in 2015-2020 is noted but GI→OQ is the direction
that meets all 5 pre-registered gates.

---

## Cross-Window Consistency Analysis

### GI→OQ across all 13 windows

| Window | n_samples | β | q_fdr | bss | Promoted |
|--------|-----------|---|-------|-----|----------|
| 2006-2011 | 556 | +0.156 | 0.280 | 0.99 | No |
| 2007-2012 | 834 | +0.062 | 0.722 | 0.93 | No |
| 2008-2013 | 1,112 | −0.062 | 0.590 | 0.97 | No |
| 2009-2014 | 1,390 | −0.040 | 0.377 | 0.94 | No |
| 2010-2015 | 1,668 | +0.015 | 0.890 | 0.71 | No |
| 2011-2016 | 1,668 | +0.023 | 0.604 | 0.83 | No |
| 2012-2017 | 1,668 | +0.023 | 0.750 | 0.83 | No |
| 2013-2018 | 1,668 | +0.018 | 0.667 | 0.85 | No |
| 2014-2019 | 1,668 | +0.044 | 0.440 | 0.96 | No |
| **2015-2020** | **1,668** | **+0.130** | **0.028** | **1.00** | **Yes** |
| 2016-2021 | 1,668 | +0.066 | 0.149 | 0.98 | No |
| 2017-2022 | 1,667 | +0.054 | 0.177 | 0.94 | No |
| 2018-2023 | 1,667 | +0.032 | 0.416 | 0.85 | No |

**Interpretation:** GI→OQ is not a persistent cross-window association. The pattern is
window-specific: early windows (2006-2011) show β=+0.156 (q_fdr=0.28, insufficient power),
middle windows are near-zero, and the 2015-2020 window shows the strongest effect.
Sign changes occur (negative in 2008-2013, 2009-2014). The promotion is localized to
the 2015-2020 economic period; it is not a structural invariant across time.

### MN→JZ across all 13 windows

| Window | n_samples | β | q_fdr | bss | Promoted |
|--------|-----------|---|-------|-----|----------|
| 2006-2011 | 321 | +0.032 | 0.876 | 0.72 | No |
| 2007-2012 | 472 | +0.033 | 0.845 | 0.76 | No |
| 2008-2013 | 622 | +0.028 | 0.783 | 0.75 | No |
| 2009-2014 | 773 | +0.055 | 0.386 | 0.95 | No |
| 2010-2015 | 921 | +0.034 | 0.818 | 0.86 | No |
| 2011-2016 | 911 | +0.012 | 0.862 | 0.64 | No |
| 2012-2017 | 922 | −0.027 | 0.882 | 0.81 | No |
| 2013-2018 | 950 | −0.046 | 0.479 | 0.96 | No |
| 2014-2019 | 976 | −0.067 | 0.434 | 0.99 | No |
| **2015-2020** | **999** | **−0.104** | **0.037** | **1.00** | **Yes** |
| 2016-2021 | 1,028 | −0.075 | 0.149 | 0.99 | No |
| 2017-2022 | 1,068 | −0.048 | 0.448 | 0.96 | No |
| 2018-2023 | 1,105 | −0.001 | 0.986 | 0.54 | No |

**Interpretation:** MN→JZ undergoes a sign reversal around 2012 (positive before, negative
after). The negative association strengthens from 2013-2018 onwards, peaking in 2015-2020.
The 2015-2020 promotion reflects the period of maximum effect. The reversal in 2018-2023
(β≈0) indicates the pattern dissipated after 2020. Interpreted as a period-specific
association, not a structural invariant.

---

## Comparison: PT Municipal vs PT NUTS3

| Metric | PT NUTS3 (all 14 windows) | PT Municipal (all 13 windows) |
|--------|--------------------------|-------------------------------|
| N territories | 25 | 278 |
| N observable sectors | 8 | 8 |
| Max n_samples/pair | 150 | 1,668 |
| N promoted (all windows) | **0** | **2** (2015-2020 only) |
| Max |β| (any window) | 0.362 (GI→FZ, 2007-2012) | 0.130 (GI→OQ, 2015-2020) |
| p_perm < 0.05 ever | 0 pairs | 3 pairs (same window) |
| COVID-robust pairs | 0 | **2** (GI→OQ, MN→JZ) |

**Key finding:** PT NUTS3 never produced a significant permutation p-value despite large β
because 25 territories × 6 years = 150 samples is insufficient power. PT Municipal 278 × 6 =
1,668 samples provides the statistical power needed. Granularity resolves the power problem
at the cost of ecological fragmentation (smaller β magnitudes).

**Ecological fragmentation effect:** NUTS3 max |β| = 0.362 vs Municipal max |β| = 0.130.
Disaggregation from 25 to 278 spatial units reduces per-unit effect sizes, consistent with
the ecological correlation trade-off. Effects visible at NUTS3 level may correspond to
different sector pairs/windows than at municipal level due to spatial averaging.

---

## Statistical Overview (Main Scenario, 13 Windows)

| Metric | Value |
|--------|-------|
| Total edge tests (main) | 728 (56 pairs × 13 windows) |
| Pairs with n_samples ≥ 60 | 728/728 (100%) |
| q_fdr < 0.05 | 3 edges (all in 2015-2020) |
| |β| ≥ 0.10 | 7 edges across all windows |
| Promoted (all 5 gates) | **2 edges** |
| COVID-robust | **2 edges** |
| Windows with promotions | **1** (2015-2020) |
| Window with highest max |β| | 2006-2011 (|β|=0.156, not promoted: q_fdr=0.28) |

---

## Scientific Interpretation

### What the results show

1. **GI→OQ, 2015-2020 (β=+0.130, q_fdr=0.028, bss=1.00):** In the period 2015-2020,
municipalities where Growth and Information sectors (GI) showed higher lagged velocity
exhibited systematically higher subsequent velocity in Public and Health services (OQ),
after two-way territory+year demeaning. This pattern is COVID-robust (survives exclusion
of 2020). The direction reverses or vanishes in adjacent windows.

2. **MN→JZ, 2015-2020 (β=−0.104, q_fdr=0.037, bss=1.00):** In the same period,
municipalities with higher lagged Professional/Administrative sector velocity (MN) showed
lower subsequent Information/Real-estate velocity (JZ). A negative temporal precedence
association, COVID-robust, and period-specific to 2015-2020.

### What the results do not show

- No cross-window structural invariant is identified. Both promotions are window-specific.
- No causal mechanism is implied. These are temporal co-movement associations after
  controlling for territory and year fixed effects.
- The pattern in GI→OQ is not persistent: sign changes occur in 2008-2013.
- Results cannot be compared directly with FR ZE2020 (different sector codes, time period,
  economic structure).

### Verdict label

The merge script returns `SECTOR_PRECEDENCE_NOT_PROMOTED` (the multi-country criterion
requiring ≥2 countries was not met — PT is a single country). For DEC-064, the correct
scientific verdict is **`PT_MUNICIPAL_PHASE7_COMPLETE`**: 2 COVID-robust promoted pairs
found in the pre-registered analysis of a single country, period-specific to 2015-2020.

---

## Prohibitions Compliance

- No neural training ✓
- No causal language ✓
- No proxy data mixed into PT analysis ✓
- No KZ claims ✓
- No results promoted without pre-registered gates ✓
- HPC launched with explicit authorisation ✓
- Results not over-interpreted across windows ✓
- Ecological fragmentation effect acknowledged ✓

---

## Reproducibility

| Artefact | Path |
|----------|------|
| Panel | `data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv` |
| Panel SHA256 | `19c4675bbf8323e0...` |
| HPC manifest | `data/processed/phase7_pt_municipal/hpc_task_manifest.json` |
| All edges (raw+q_fdr) | `data/processed/phase7_pt_municipal/results/all_edges.csv` |
| Promoted (main) | `data/processed/phase7_pt_municipal/results/latest.csv` |
| COVID-robust | `data/processed/phase7_pt_municipal/results/covid_robust_edges.csv` |
| Merge decision | `data/processed/phase7_pt_municipal/results/decision.json` |
| Sbatch | `hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch` |
| Gates | `src/modeles/real_world/gates_dec064_pt_municipal_phase7.py` |
| Commit | `10a7890f5d56` |

---

## Next Steps

| Action | DEC | Status |
|--------|-----|--------|
| Threshold calibration (|β|≥0.10 may be too high for municipal level) | DEC-066 | Open |
| NL gemeente Phase 7 (proxy, 355 gemeente) | DEC-065 | Draft ready |
| FR ZE2020 Phase 7 (280 zones, comparison) | DEC-067? | Not started |
| Cross-country granular training (using DEC-064 + DEC-065 results) | DEC-068? | Blocked on DEC-065 |

**Threshold note:** Both promoted pairs have |β| ∈ [0.10, 0.13], just above the threshold.
The 2006-2011 window showed GI→OQ with β=0.156 that did not reach q_fdr<0.05 with lower
sample count (556 vs 1668 in 2015-2020). If the threshold were lowered to |β|≥0.07, several
additional pairs with bss≥0.90 would appear. DEC-066 should assess this threshold calibration
before DEC-065 and any granular training.

---

*HERALD DEC-064 | PT Municipal Phase 7 | PT_MUNICIPAL_PHASE7_COMPLETE | 10/10 PASS | 2026-06-16*
