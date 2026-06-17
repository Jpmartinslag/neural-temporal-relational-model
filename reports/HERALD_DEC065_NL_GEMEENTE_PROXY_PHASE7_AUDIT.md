# HERALD DEC-065: NL Gemeente Proxy Phase 7 Sector Precedence — Audit

**Status:** COMPLETE — `NL_GEMEENTE_PROXY_PHASE7_BLOCKED`
**Decision:** Gemeente proxy edges are NOT usable as DEC-066 training labels (any tier). Structural validity defect found.
**Date:** 2026-06-17
**Follows:** DEC-063 (proxy panel construction), DEC-064 (PT Municipal Phase 7), DEC-066 (fine-grain threshold policy)
**HPC job:** 7475756 on meso — 252/252 tasks complete
**Gates:** N1-N10 — 71/71 tests PASS (tests verify schema/structure; the BLOCKED verdict is a manual scientific override, see below)

**Explicit markers (consolidated 2026-06-17, see `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md`):**
- All **121 NL gemeente proxy edges** are marked **`INVALID_FOR_TRAINING_LABELS`**
  (label_class=`BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false`).
- NL gemeente proxy data **cannot be used as a sector→sector relation label**, under
  any DEC-066 tier, at any window.
- **NL COROP observed** (8 promoted, 3 COVID-robust) **remains valid** —
  `NL_COROP_PHASE7 = VALID_OBSERVED`.
- NL gemeente proxy **may be used as visual/territorial context only**
  (`allowed_use=territory_state_context_only`) — never as relation-graph or training
  evidence. See `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv`.

---

## Summary

The automated merge script computed `NL_GEMEENTE_PROXY_PHASE7_SUPPORTED` from the
pre-registered gate thresholds alone (121 promoted edges, 97 nominally COVID-robust,
7/8 COROP pairs preserved). **This automated verdict is overridden to `BLOCKED`** after
a structural validity diagnostic showed that the proxy disaggregation method itself
injects cross-sector correlation unrelated to any births-precedence relationship,
explaining the implausible 15x jump in promoted edges (8 in COROP observed → 121 in
gemeente proxy) without genuine new economic signal.

This is the central finding of this audit. All other gates (N1, N2, N3, N5, N6, N7,
N9, N10) pass and are documented below, but **N4 and the overall scientific verdict
must be read in light of the structural defect**, not in isolation.

---

## HPC Execution

- **Job 7475756**, array 0-251, submitted to meso, partition=normal, constraint=mpi
- 252/252 tasks `COMPLETED` (confirmed via `sacct`)
- 252/252 raw JSON outputs present in `hpc_results/phase7_nl_gemeente_proxy/raw/`
- Remote smoke (task 0, n_perm=9): 63.0s; full task median: not separately measured, all completed within 3h time limit
- Rsynced to local: `hpc_results/phase7_nl_gemeente_proxy/raw/` (252 files)
- Merged: 2,016 edges (252 tasks × 8 targets), BH/FDR per country×scenario×window family

---

## Gates N1-N10

| Gate | Description | Verdict |
|------|-------------|---------|
| N1 | SAFETY: 252/252 tasks complete, schema valid | **PASS** |
| N2 | PROXY_INTEGRITY: evidence_type=proxy_disaggregated_by_stock_share preserved throughout | **PASS** |
| N3 | OBSERVED_VS_PROXY_SEPARATION: gemeente results not merged into `sector_precedence_results/` (NL COROP), comparison CSV documents both sources | **PASS** |
| N4 | COROP_SIGNAL_PRESERVATION: ≥50% of 8 COROP promoted pairs appear in proxy, same sign, p_perm<0.20 | **PASS (7/8)** — but see Structural Validity Finding below; preservation is not informative given the defect |
| N5 | REAGGREGATED_VALIDATION: proxy reaggregates to COROP within tolerance (DEC-063, max_abs_error=0.0); panel coverage ≥85% | **PASS** |
| N6 | DEC066_LABEL_POLICY: all labels conform to taxonomy, EXPLORATORY/REJECTED never used as training labels | **PASS (schema)** — labels themselves are not trustworthy, see below |
| N7 | CONTROLS: no NaN/Inf, p_perm/bss/q_fdr in [0,1], n_samples≥60 for promoted, q_fdr≥p_perm | **PASS** |
| N8 | NO_PROXY_OVERCLAIM: no unnegated overclaim language in decision/label outputs | **PASS** |
| N9 | NO_CAUSAL_LANGUAGE: no causal terms in decision/label/comparison outputs | **PASS** |
| N10 | REPRODUCIBILITY: checksums, commit, manifest, task counts, n_perm/n_boot documented | **PASS** |

**71/71 tests PASS** (`tests/test_dec065_nl_gemeente_proxy_phase7.py`). These tests verify
schema, structure, and textual integrity — they do NOT and cannot test statistical
validity of the underlying regression assumptions. The structural defect below was
found through targeted diagnostic analysis, not through the pre-registered N-gates.

---

## Raw Results

- **Total edges:** 2,016 (252 tasks × 8 targets)
- **Promoted (main, all gates):** 121 — unique source→target pairs: **35** (out of 72 possible directed pairs)
- **COVID-robust (main AND without_2020, same sign):** 97
- **n_samples for promoted edges:** 1,298–2,075 (vs COROP's fixed 240 per window: 40 territories × 6 years)
- **|β| range for promoted edges:** 0.100–0.219

For comparison:
| Dataset | N territories | Promoted (main) | COVID-robust |
|---------|---------------|------------------|---------------|
| NL COROP (observed) | 40 | 8 | 3 |
| PT Municipal (observed) | 278 | 2 | 2 |
| **NL gemeente (proxy)** | **355** | **121** | **97** |

A 15x jump in promoted edges and a 32x jump in COVID-robust edges, going from COROP
(observed) to gemeente (proxy) for the **same country and same underlying births
series**, is not consistent with genuine signal gained from finer spatial resolution.
PT Municipal — disaggregating from 25 PT NUTS3 to 278 municipalities using **directly
observed** births (INE) — gained statistical power but found *fewer* promoted edges
than NUTS3, consistent with the ecological-fragmentation pattern documented in DEC-066
(finer units → smaller, not larger, effect counts). NL gemeente proxy breaks this
pattern sharply, which is the first warning sign.

---

## Structural Validity Finding: Stock-Share-Induced Cross-Sector Correlation

### Mechanism

The DEC-063 proxy method computes:

```
estimated_births_gemeente[g, s, t] = observed_births_corop[c(g), s, t] × stock_share[g, s, t]
stock_share[g, s, t] = stock_gemeente[g, s, t] / Σ_g' stock_gemeente[g', s, t]   (within COROP c(g))
```

Velocity for Phase 7 is `value[t]/value[t-1] - 1` (causal lag-1). Decomposing:

```
gm_velocity[g,s,t] ≈ corop_velocity[c(g),s,t] + share_velocity[g,s,t]   (approximately, for small changes)
```

where `share_velocity` is the year-on-year change in the gemeente's stock share
within its COROP — driven by local establishment-stock composition shifts
(new development, gentrification, business turnover), **not by births**.

### Quantitative evidence

1. **Variance decomposition** of gemeente velocity by COROP×year×sector group:
   - Between-group (shared COROP-level) variance: 32.5%
   - Within-group (gemeente-specific) variance: 67.5%
   - → Not pure replication of COROP signal, but the within-group component is itself dominated by `share_velocity`, not genuine local births variation (see below).

2. **Decomposition regression** `gm_velocity ~ corop_velocity + share_velocity` (n=54,811, R²=0.635):
   - `corop_velocity` coefficient: **1.33**
   - `share_velocity` coefficient: **13.01** — roughly **10x larger**
   - → Small year-to-year fluctuations in stock share dominate the proxy birth velocity, swamping the actual COROP-level birth dynamics that the method is supposed to disaggregate.

3. **Cross-sector correlation of `share_velocity`** (the weighting term, computed independently of any births data):
   - Range 0.34–0.82 across most sector pairs (e.g. GI↔MN: 0.82, FZ↔GI: 0.75, MN↔RU: 0.74)
   - Only OQ is decorrelated from the rest (0.08–0.20)
   - → A gemeente's general establishment-stock growth (development, gentrification) moves across most A10 sectors simultaneously. This is a structural property of urban economic geography, unrelated to any sector-to-sector births-precedence mechanism.

4. **Cross-sector correlation of the actual proxy births velocity** used in the Phase 7 regression: 0.0–0.53, lower than `share_velocity`'s correlation but still elevated for the same pairs (e.g. GI↔MN: 0.53) — consistent with `share_velocity` being a major contributor.

### Consequence

The Phase 7 sector-precedence regression (`target_growth ~ source_lag`, two-way
territory+year demeaning) run on the gemeente panel is substantially picking up the
shared local stock-growth co-movement injected by the proxy construction, not a births
precedence signal. The permutation test and bootstrap stability statistics are computed
under an implicit i.i.d. assumption across gemeente-year observations within the panel;
that assumption is violated because gemeenten within the same COROP are not independent
— they share both a COROP-level births component (32.5% of variance) and a
cross-sector-correlated stock-share component (dominant within the remaining 67.5%).
`n_samples≥60` and `q_fdr<0.05` are satisfied at face value but do not reflect the true
effective degrees of freedom.

Full diagnostic: `data/processed/phase7_nl_gemeente_proxy/results/structural_validity_diagnostic.json`

---

## Verdict Override

The merge/labelling script (`src/modeles/real_world/merge_nl_gemeente_proxy_phase7.py`)
computes verdicts purely from gate-pass counts and would have returned
`NL_GEMEENTE_PROXY_PHASE7_SUPPORTED` (≥2 COVID-robust, N4 PASS). This audit **manually
overrides** that automated verdict to:

> **`NL_GEMEENTE_PROXY_PHASE7_BLOCKED`**

recorded in `decision.json` (`verdict_override_reason`,
`automated_verdict_before_override`) and `nl_gemeente_proxy_label_summary.json`.

**None of the 121 promoted edges, 97 COVID-robust pairs, or any DEC-066-tier label
(ROBUST_ORIGINAL / FINE_GRAIN_SUPPORTED / EXPLORATORY_FINE_GRAIN) derived from the
gemeente proxy panel may be used as training labels, claims, or Observatory inputs**
until the regression is re-specified to absorb the shared stock-share component
(e.g. COROP-clustered standard errors, COROP×year fixed effects on the weighting term,
or a proxy method that does not multiply by a time-varying, cross-sector-correlated
share).

This satisfies the original DEC-065 specification's `BLOCKED` decision option.

---

## What Is Still Usable

- The **panel construction** itself (reaggregation PASS, leakage PASS, evidence_type
  correctly propagated) remains valid and reusable infrastructure.
- The **diagnostic finding** is reusable evidence against using stock-share-weighted
  disaggregation for any future country/sector proxy panel (BE, AT candidates) without
  first checking for the same structural defect.
- **NL COROP** (8 promoted, 3 COVID-robust, observed_births) is unaffected and remains
  the valid NL baseline at DEC-034/064 scale.

---

## Outputs

| Artefact | Path |
|----------|------|
| Panel builder | `src/data/european_panel/build_nl_gemeente_phase7_panel.py` |
| Merge/label script | `src/modeles/real_world/merge_nl_gemeente_proxy_phase7.py` |
| Raw HPC outputs | `hpc_results/phase7_nl_gemeente_proxy/raw/` (252 files) |
| All edges | `data/processed/phase7_nl_gemeente_proxy/results/all_edges.csv` |
| Promoted (main) | `data/processed/phase7_nl_gemeente_proxy/results/latest.csv` |
| COVID-robust | `data/processed/phase7_nl_gemeente_proxy/results/covid_robust_edges.csv` |
| Decision (overridden) | `data/processed/phase7_nl_gemeente_proxy/results/decision.json` |
| Structural validity diagnostic | `data/processed/phase7_nl_gemeente_proxy/results/structural_validity_diagnostic.json` |
| COROP vs gemeente comparison | `data/processed/phase7_nl_gemeente_proxy/nl_corop_vs_gemeente_proxy_comparison.csv` |
| Label summary (overridden) | `data/processed/phase7_nl_gemeente_proxy/nl_gemeente_proxy_label_summary.json` |
| Tests | `tests/test_dec065_nl_gemeente_proxy_phase7.py` (71/71 PASS) |
| sbatch | `hpc/phase7_sector_precedence/run_phase7_nl_gemeente_proxy_array.sbatch` |

---

## Decision

**`NL_GEMEENTE_PROXY_PHASE7_BLOCKED`**

- NL gemeente proxy Phase 7 results are NOT promoted to any training label.
- Root cause: stock-share weighting in the DEC-063 proxy method injects cross-sector
  correlated noise (coefficient ~10x the genuine COROP births signal) that the
  permutation-based gates cannot distinguish from a real precedence relationship.
- NL COROP (observed, DEC-034/064 scale) remains the valid NL evidence source.
- DEC-068 (cross-country granular training, FR+PT+NL) **must exclude** NL gemeente
  proxy edges until a corrected proxy/regression specification is validated.

---

## Next Steps

| Action | DEC | Status |
|--------|-----|--------|
| Re-specify gemeente regression with COROP-clustered SEs or COROP×year FE on share term, re-test | DEC-065b (proposed) | Open |
| Apply same structural-validity diagnostic to any future BE/AT gemeente-level proxy panel before running Phase 7 | Tracked | Open |
| Cross-country granular training (FR+PT+NL) — proceed with FR/PT only, NL limited to COROP scale | DEC-068 | Open, NL gemeente excluded |
| Apply fine-grain policy to FR/PT label export (unaffected by this finding) | DEC-067 | Open |

---

*HERALD DEC-065 | NL Gemeente Proxy Phase 7 | NL_GEMEENTE_PROXY_PHASE7_BLOCKED | 71/71 tests PASS | structural defect found and documented | 2026-06-17*
