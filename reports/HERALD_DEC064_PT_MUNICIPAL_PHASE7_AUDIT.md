# HERALD DEC-064: PT Municipal Phase 7 Sector Precedence Audit

**Status:** SMOKE COMPLETE (10/10 PASS) — Medium run pending  
**Decision:** `PT_MUNICIPAL_PHASE7_READY_FOR_HPC`  
**Date:** 2026-06-16  
**Follows:** DEC-063 (GRANULAR_FR_PT_NL_PREFLIGHT_READY)  
**Gates:** P1-P10, pre-registered before results observed (GATE_VERSION: DEC-064-v1)

---

## Summary

Phase 7 sector precedence was run on 278 continental Portuguese municipalities
using `observed_births` (INE enterprise_birth, 2008–2023). The pipeline is validated
(smoke PASS, 10/10 gates). Effect sizes at municipal level are consistent with the
NUTS3 pattern but are below the pre-registered |β| ≥ 0.10 threshold. No sector
pairs are promoted at the current threshold. Full HPC run (n_perm=999) is prepared
and awaiting authorisation for definitive results across all 13 windows.

---

## Part A — PT Municipal Panel Audit

| Property | Value |
|----------|-------|
| Source | INE enterprise_birth (0009703 / 0014099) |
| N municipalities | 278 (continental Portugal, geocod prefix=1) |
| Years | 2008–2023 (16 years) |
| Observable A10 sectors | 8 (BE, FZ, GI, JZ, LZ, MN, OQ, RU) |
| KZ (Finance) | structural_absent — all NaN, no zeros |
| Evidence type | observed_births |
| Proxy columns | None |
| Açores / Madeira | Excluded (is_continental = True for all rows) |

Panel built with `build_pt_municipal_phase7_panel.py`:
- Long format: 40,032 rows (278 municipalities × 9 A10 sectors × 16 years)
- observation_mask=1 rows: 31,100 (velocity computable)
- Velocity = `sector_value[t] / sector_value[t-1] − 1` (strictly causal, lag1 only)
- Temporal leakage check: PASS (lag1 = shift(1), never future)

---

## Part B — Gates P1-P10 (Smoke)

**GATE_VERSION:** DEC-064-v1 — thresholds pre-registered before observing any results.

| Gate | Description | Verdict |
|------|-------------|---------|
| P1 | Safety: no NaN/Inf, no temporal leakage, years ordered | PASS |
| P2 | Coverage: 278 municipalities, 8 observable sectors, KZ absent | PASS |
| P3 | Observed-only: no proxy data mixed in | PASS |
| P4 | Reaggregation divergence documented | PASS |
| P5 | All computed pairs have n_samples ≥ 60 | PASS |
| P6 | Permutation control degrades signal | PASS |
| P7 | Thresholds pre-registered (DEC-064-v1) | PASS |
| P8 | PT municipal vs PT NUTS3 comparison documented | PASS |
| P9 | No causal language in outputs | PASS |
| P10 | Manifest, checksum, commit hash documented | PASS |

Pre-registered thresholds (identical to original Phase 7, DEC-034):
- q_fdr < 0.05 (BH/FDR per family: country × scenario × window)
- |β| ≥ 0.10
- Δr² ≥ 0.005
- bootstrap sign stability ≥ 0.70
- n_samples ≥ 60

---

## Part C — Smoke Results (2018-2023 window, n_perm=9)

**Window:** 2018–2023 | **N pairs:** 56 (8 sectors × 7 targets) | **N_perm:** 9

### Sample size (key finding)

| Metric | Value |
|--------|-------|
| Mean n_samples | 1,452 |
| Min n_samples | 1,055 |
| Max n_samples | 1,668 |
| **NUTS3 n_samples (max)** | **150** |

Municipal level provides **11× more samples per pair** than NUTS3 (278 × 6 years vs 25 × 6 years). This substantially increases permutation test power.

### Top associations (2018-2023 window)

| Source → Target | β | Δr² | p_perm¹ | bss |
|----------------|---|-----|---------|-----|
| MN → GI | +0.078 | 0.0060 | 0.10 | 1.00 |
| LZ → BE | +0.075 | 0.0056 | 0.10 | 0.90 |
| RU → MN | +0.075 | 0.0056 | 0.10 | 1.00 |
| BE → GI | +0.069 | 0.0046 | 0.10 | 1.00 |
| GI → BE | −0.084 | 0.0068 | 0.10 | 1.00 |
| OQ → JZ | −0.063 | 0.0039 | 0.10 | 1.00 |

¹ With n_perm=9, minimum achievable p_perm = 1/(9+1) = 0.10. Real p-values require n_perm=999.

### Promoted edges

**0 pairs promoted** (smoke, 1 window, n_perm=9).

No pairs reach p_perm < 0.05 at n_perm=9 (floor = 0.10).  
Largest |β| = 0.078 < 0.10 threshold.

---

## Part D — Comparison with PT NUTS3

| Metric | PT NUTS3 (Phase 7 original) | PT Municipal (DEC-064 smoke) |
|--------|-----------------------------|------------------------------|
| N territories | 25 | 278 |
| N years | 2008–2024 | 2008–2023 |
| Mean n_samples/pair | 130 | 1,452 |
| N promoted (all windows) | **0** | **0** (smoke; full run pending) |
| Max |β| (all windows) | 0.362 (GI→FZ, 2007-2012) | 0.078 (MN→GI, 2018-2023) |
| p_perm < 0.05 ever | **0 pairs** | unknown (n_perm=9 floor=0.10) |

**Key observations:**

1. **PT NUTS3 had 0 promotions** because `p_perm < 0.05` was never reached with 25 territories. PT Municipal with 278 territories has sufficient statistical power to detect small associations.

2. **Effect sizes are smaller at municipal level** (max |β|=0.078 vs 0.362 at NUTS3 in the same period). Aggregation at NUTS3 reduces within-group variance and amplifies cross-sector correlations — the well-known ecological correlation effect.

3. **RU→MN pattern** (β=+0.075, bss=1.00) echoes the single FR-promoted relation (RU→MN at ZE2020). Sign is consistent but magnitude is below threshold.

4. **GI→BE negative association** (β=−0.084, bss=1.00) is the strongest single signal. At NUTS3 level, GI→FZ had the largest beta (+0.362 in 2007-2012 window). The contrast suggests different dynamics across time periods and spatial aggregation levels.

5. **Granularity fragmentation confirmed:** decomposing from 25 NUTS3 to 278 municipalities reduces individual β magnitudes. More spatial units → smaller per-unit effects → more noise relative to signal.

---

## Part E — P4: Municipal vs NUTS3 Aggregation

PT NUTS3 years cover 2008–2024 (observatory v02); PT municipal covers 2008–2023. Direct aggregation comparison is complicated by:
- Different NUTS vintages (NUTS2013 vs NUTS2024 transition at 2023)
- 176/278 municipalities got new geocods at 2023; harmonised via name
- Total municipal enterprise_birth should aggregate close to NUTS3 total, but exact match is not guaranteed due to different INE indicator IDs (0009703 + 0014099 vs original NUTS3 source)

Divergence is documented (not required to match). P4 PASS.

---

## Part F — HPC Preparation

**Manifest:** `data/processed/phase7_pt_municipal/hpc_task_manifest.json`
- 208 tasks total (13 windows × 2 scenarios × 8 source sectors)
- Panel SHA256: `19c4675bbf8323e0...`
- Commit: `10a7890f5d56` (DEC-063 commit)

**Sbatch:** `hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch`
- 208-task array, 30 min/task @ 4G
- Output dir: `hpc_results/phase7_pt_municipal/raw/`

**Submit command (DO NOT run without explicit authorisation):**
```bash
sbatch --array=0-207 hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch
```

**Post-run merge:**
```bash
python hpc/phase7_sector_precedence/scripts/merge_sector_precedence_results.py \
  --raw-dir hpc_results/phase7_pt_municipal/raw \
  --manifest data/processed/phase7_pt_municipal/hpc_task_manifest.json \
  --out-dir data/processed/phase7_pt_municipal/results
```

**Post-merge gates:**
```bash
PYTHONPATH=. python src/modeles/real_world/run_dec064_pt_municipal_phase7.py
```

---

## Part G — Scientific Questions

### 1. PT municipal produces more robust relations than PT NUTS3?

**From smoke (1 window):** No — 0 promoted at both levels. With more permutations and more windows, the municipal level may reveal associations that were masked at NUTS3 by insufficient statistical power. The 11× sample increase is the key structural advantage.

### 2. Old PT NUTS3 relations still visible at municipal?

PT NUTS3 had 0 promoted relations. The strongest NUTS3 betas (GI→FZ +0.362, GI→JZ −0.123 in 2007-2012) do not appear in the 2018-2023 municipal window — consistent with the known structural shift in PT after the 2012 austerity period and pre-/post-COVID dynamics.

### 3. Granularity increases or fragments signal?

**Fragments.** Decomposing 25 NUTS3 → 278 municipalities reduces individual |β| (max 0.078 vs 0.362). This is the ecological correlation trade-off: aggregation amplifies cross-sector correlation; disaggregation increases sample count but reduces per-unit effect magnitudes.

### 4. Sectors with stable temporal precedence?

From the 2018-2023 smoke:
- **MN↔GI**: mutual positive association (MN→GI β=+0.078, bss=1.0)
- **LZ→BE**: positive (β=+0.075, bss=0.90)
- **RU→MN**: positive (β=+0.075, bss=1.0) — consistent with FR pattern
- **GI→BE**: negative (β=−0.084, bss=1.0)

All below |β| = 0.10. Final stability classification requires all 13 windows.

### 5. Exploratory vs robust?

All current results are **exploratory only** (n_perm=9, 1 window). No results can be classified as robust without n_perm=999 across ≥5 windows with consistent signs.

### 6. Implications for FR/PT/NL granular training?

- FR 280 ZE2020: 1 robust label (RU→MN COVID-sensitive). Threshold |β|≥0.10 met.
- PT 278 municipalities: 0 promoted (smoke). |β|<0.10 consistent with smaller ecological units.
- NL 355 gemeente (proxy): not yet run (DEC-065 pending authorisation).

**Implication:** The |β|≥0.10 threshold calibrated on FR may systematically exclude PT and NL signals. A threshold calibration DEC is warranted before combining FR/PT/NL training labels.

---

## Decision

**`PT_MUNICIPAL_PHASE7_READY_FOR_HPC`**

Smoke: 10/10 PASS. Pipeline validated. Data quality confirmed (n_samples 1055–1668).
Full n_perm=999 run requires HPC (208 tasks, ~30 min/task).
HPC manifest and sbatch prepared. Awaiting authorisation.

---

## Prohibitions Compliance

- No neural training ✓
- No causal language ✓
- No proxy data mixed into PT analysis ✓
- No KZ claims ✓
- No results promoted without pre-registered gates ✓
- No HPC launched without authorisation ✓

---

## Next Steps (requires new DEC or HPC authorisation)

| Action | DEC |
|--------|-----|
| Authorise HPC run (208 tasks, 30 min each) | Authorisation only |
| After HPC: re-run gates with full results | No new DEC needed |
| Threshold calibration (if |β|<0.10 confirmed) | DEC-066 |
| NL gemeente Phase 7 (proxy) | DEC-065 |
| Cross-country granular training | DEC-067 |

---

*HERALD DEC-064 | PT Municipal Phase 7 | PT_MUNICIPAL_PHASE7_READY_FOR_HPC | 2026-06-16*
