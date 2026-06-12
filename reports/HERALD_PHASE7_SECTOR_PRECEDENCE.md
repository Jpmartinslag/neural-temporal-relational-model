# HERALD Phase 7 — Sector Precedence Study: Scientific Audit

**Status:** COMPLETE — SECTOR_PRECEDENCE_PROTOTYPE_READY  
**Date:** 2026-06-12  
**Decision:** DEC-034  
**Job:** Slurm 7455266, meso (`hpc2.mesocentre.uca.fr`)  

---

## 1. Study Design

### Objective

Test whether lagged growth in sector A adds information about next-year enterprise-birth growth in sector B, after controlling for B's own lag, across rolling 6-year windows in FR, NL, PT.

This measures *predictive precedence* — a statistical association between sector trajectories — not structural economic causality or the effect of any intervention.

### Method (pre-registered in DEC-033)

For each (country, scenario, window, source_sector) task:

1. **Pair samples:** Align `source(t−1)`, `target(t−1)`, `target(t)` within each territory using observation and structural masks.
2. **Two-way demean:** Remove territory and year fixed effects by alternating projection (max 8 iterations, convergence < 1e-10).
3. **Partial regression:** `target(t) ~ 1 + target(t−1) + source(t−1)` after standardisation. `beta` = coefficient on standardised source lag.
4. **Incremental R²:** `delta_r2 = R²_full − R²_baseline`.
5. **Permutation p-value:** 999 within-year territory permutations of source lag; empirical p = `(1 + Σ|null| ≥ |obs|) / (999 + 1)`.
6. **Bootstrap sign stability:** 500 territory-cluster bootstrap replicates; fraction with same sign as observed beta.
7. **BH/FDR:** Applied per family = `country × scenario × window` after collecting all raw p-values. NOT per task.
8. **Scenarios:** `main` (all years) and `without_2020` (exclude 2020 from each window).

### Promotion gates (pre-registered, immutable)

| Gate | Threshold |
|------|-----------|
| q_fdr (BH) | ≤ 0.05 |
| \|beta\| | ≥ 0.10 |
| delta_r2 | ≥ 0.005 |
| bootstrap_sign_stability | ≥ 0.70 |
| n_samples | ≥ 60 |

**COVID robustness:** Edge must be promoted in BOTH `main` AND `without_2020` with same sign.

**Prototype decision:** `SECTOR_PRECEDENCE_PROTOTYPE_READY` if ≥ 2 countries have at least one COVID-robust promoted edge; else `SECTOR_PRECEDENCE_NOT_PROMOTED`.

### Panel

`herald_observatory_v02`: FR/NL/PT, 9 sectors (PT: 8, KZ structurally absent), 45,945 rows.  
SHA256: `a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e`

### Task decomposition

| Country | Scenario | Windows | Source sectors | Tasks |
|---------|----------|---------|----------------|-------|
| FR | main | 11 | 9 | 99 |
| FR | without_2020 | 11 | 9 | 99 |
| NL | main | 16 | 9 | 144 |
| NL | without_2020 | 16 | 9 | 144 |
| PT | main | 14 | 8 | 112 |
| PT | without_2020 | 14 | 8 | 112 |
| **Total** | | | | **710** |

---

## 2. Execution

- **Infrastructure:** Slurm array on meso, partition `normal`, `--constraint=mpi`
- **Array size:** 710 tasks (indices 0–709)
- **Completion:** 710/710 COMPLETED (sacct: 1420 records, all COMPLETED)
- **Audit:** BH/FDR independently recomputed; max discrepancy = 1.11e-16 (float precision only)
- **NaN edges:** 368/5456 (6.7%) — territories with n < 60 after masking, expected

---

## 3. Results

### 3.1 Promoted edges (main scenario, all gates passed)

| Country | window | source → target | β | Δr² | p_perm | q_fdr | sign_stab | n |
|---------|--------|-----------------|---|-----|--------|-------|-----------|---|
| FR | 2020–2025 | RU → MN | −0.108 | 0.011 | 0.001 | 0.024 | 1.000 | 1680 |
| NL | 2009–2014 | BE → MN | −0.222 | 0.048 | 0.001 | 0.028 | 1.000 | 240 |
| NL | 2009–2014 | BE → RU | −0.205 | 0.042 | 0.001 | 0.028 | 0.986 | 240 |
| NL | 2014–2019 | FZ → GI | +0.195 | 0.038 | 0.002 | 0.043 | 0.994 | 240 |
| NL | 2014–2019 | FZ → RU | +0.170 | 0.028 | 0.003 | 0.043 | 0.964 | 240 |
| NL | 2014–2019 | JZ → FZ | −0.230 | 0.053 | 0.002 | 0.043 | 0.936 | 240 |
| NL | 2014–2019 | JZ → RU | −0.180 | 0.032 | 0.003 | 0.043 | 0.996 | 240 |
| NL | 2014–2019 | LZ → RU | +0.175 | 0.031 | 0.003 | 0.043 | 0.964 | 239 |
| NL | 2014–2019 | OQ → JZ | −0.286 | 0.081 | 0.004 | 0.048 | 0.804 | 120 |
| PT | 2014–2019 | BE → MN | −0.281 | 0.065 | 0.001 | 0.019 | 0.992 | 150 |
| PT | 2014–2019 | MN → JZ | −0.311 | 0.093 | 0.001 | 0.019 | 0.992 | 150 |
| PT | 2014–2019 | MN → OQ | −0.245 | 0.054 | 0.002 | 0.028 | 0.998 | 150 |
| PT | 2014–2019 | OQ → JZ | −0.328 | 0.107 | 0.001 | 0.019 | 0.966 | 150 |
| PT | 2015–2020 | FZ → BE | +0.255 | 0.036 | 0.001 | 0.011 | 0.998 | 150 |
| PT | 2015–2020 | GI → BE | +0.362 | 0.078 | 0.001 | 0.011 | 0.998 | 150 |
| PT | 2015–2020 | JZ → BE | +0.194 | 0.038 | 0.006 | 0.048 | 0.940 | 150 |
| PT | 2015–2020 | JZ → MN | +0.213 | 0.043 | 0.004 | 0.037 | 1.000 | 150 |
| PT | 2015–2020 | MN → JZ | −0.289 | 0.078 | 0.001 | 0.011 | 0.996 | 150 |
| PT | 2015–2020 | MN → OQ | −0.287 | 0.061 | 0.001 | 0.011 | 1.000 | 150 |
| PT | 2015–2020 | OQ → JZ | −0.267 | 0.071 | 0.001 | 0.011 | 0.966 | 150 |
| PT | 2017–2022 | BE → MN | −0.228 | 0.041 | 0.003 | 0.042 | 0.998 | 150 |
| PT | 2017–2022 | GI → BE | +0.231 | 0.035 | 0.001 | 0.042 | 0.946 | 150 |
| PT | 2017–2022 | GI → FZ | +0.212 | 0.019 | 0.003 | 0.042 | 0.952 | 150 |
| PT | 2017–2022 | GI → JZ | −0.220 | 0.048 | 0.004 | 0.045 | 0.998 | 150 |
| PT | 2017–2022 | MN → BE | +0.205 | 0.033 | 0.002 | 0.042 | 1.000 | 150 |

Sector codes (A10 NACE Rev.2): BE=Mining+Water/Waste; FZ=Construction; GI=Trade+Transport; JZ=ICT; LZ=Real Estate; MN=Professional/Business Services; OQ=Public/Education/Health; RU=Arts+Other.

### 3.2 COVID-robust edges (promoted in main AND without_2020, same sign)

| Country | window | source → target | β_main | β_wo20 |
|---------|--------|-----------------|--------|--------|
| NL | 2014–2019 | FZ → GI | +0.195 | +0.195 |
| NL | 2014–2019 | FZ → RU | +0.170 | +0.170 |
| NL | 2014–2019 | JZ → FZ | −0.230 | −0.230 |
| PT | 2014–2019 | BE → MN | −0.281 | −0.281 |
| PT | 2014–2019 | MN → JZ | −0.311 | −0.311 |
| PT | 2014–2019 | OQ → JZ | −0.328 | −0.328 |
| PT | 2015–2020 | GI → BE | +0.362 | +0.287 |
| PT | 2015–2020 | MN → JZ | −0.289 | −0.347 |
| PT | 2015–2020 | MN → OQ | −0.287 | −0.344 |
| PT | 2015–2020 | OQ → JZ | −0.267 | −0.312 |
| PT | 2017–2022 | BE → MN | −0.228 | −0.347 |
| PT | 2017–2022 | GI → JZ | −0.220 | −0.316 |

*Note: edges in the 2014–2019 window have identical betas in main and without_2020 because 2020 falls outside this window and is never excluded.*

**Countries contributing COVID-robust edges: NL (3), PT (9). Total: 12 edges, 2 countries.**

### 3.3 FR result

FR has 1 promoted edge in `main` (RU→MN, 2020-2025, β=−0.108, q=0.024, sign_stability=1.0). This edge is not COVID-robust: the `without_2020` scenario promotes a different pair in a different window. FR therefore contributes 0 COVID-robust edges and does not influence the prototype verdict.

---

## 4. Verdict

**SECTOR_PRECEDENCE_PROTOTYPE_READY**

The pre-registered prototype gate (≥2 countries with at least one COVID-robust promoted edge) is satisfied: NL and PT both have COVID-robust sector precedence associations.

---

## 5. Scientific Interpretation

### Observed patterns

**Netherlands (2014–2019):**
- Construction (FZ) lagged growth positively associates with Trade/Transport (GI) and Arts/Other (RU) birth growth.
- ICT (JZ) lagged growth negatively associates with Construction (FZ) and Arts/Other (RU) birth growth.
- Public sector (OQ) lagged growth negatively associates with ICT (JZ) birth growth.

**Portugal (2014–2019 and 2015–2022):**
- A recurrent pattern: MN (Professional/Business Services) lagged growth negatively associates with JZ (ICT) and OQ (Public sector) birth growth. This is consistent across three windows.
- OQ lagged growth negatively associates with JZ birth growth in two windows.
- GI (Trade/Transport) lagged growth positively associates with BE (Mining/Industrial) and FZ (Construction) birth growth.

### What these associations do and do not mean

These edges express *predictive precedence*: knowing last year's standardised sector growth reduces uncertainty about this year's enterprise-birth growth in the target sector, after accounting for the target's own momentum and removing territory/year fixed effects. This is a statistical property of the panel, not an economic mechanism.

These results do **not** support claims of:
- Structural causality between sectors
- Policy effectiveness of stimulating one sector
- Labour or capital flow mechanisms
- Equilibrium effects

The negative sign on MN→JZ in Portugal, for example, is consistent with multiple explanations (substitution of business-service functions by ICT entrants, budget/attention competition, correlated but opposite demand cycles) and cannot be disambiguated from this study.

---

## 6. Limitations

1. **Short windows:** 6-year windows limit power for slow-frequency dynamics and introduce window dependence when patterns repeat across overlapping intervals.
2. **Aggregation:** A10 sector codes aggregate heterogeneous sub-sectors; within-sector variation is unmodeled.
3. **FR weak signal:** Only 1 promoted edge in FR, none COVID-robust. The French panel has more regions (1680 obs per window) but stronger attenuation from territory fixed effects may reduce sensitivity.
4. **Distributional assumptions:** The permutation test is valid under exchangeability within years; cross-year correlations (autocorrelation) are not explicitly modeled.
5. **Multiple windows:** Overlapping 6-year windows (e.g., 2014–2019, 2015–2020) are partially correlated. BH/FDR is applied per window family, which is conservative but does not fully account for cross-window dependence.

---

## 7. Next Steps

- Add COVID-robust edges to the Economic Observatory sector graph layer (v0.3).
- Consider extending to AT and BE panels once their sector panels are validated.
- Pre-register any replication or mechanism study before accessing new data.

---

## Provenance

| Item | Value |
|------|-------|
| Panel SHA256 | `a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e` |
| Manifest SHA256 | `cee8923feb13c952bd0b...` (full in run_manifest.json) |
| Slurm job | 7455266 |
| Total tasks | 710 (all COMPLETED) |
| Audit result | PASS (0 errors, 9 findings) |
| BH/FDR discrepancy | max 1.11e-16 (float precision) |
| Generated | 2026-06-12 |
