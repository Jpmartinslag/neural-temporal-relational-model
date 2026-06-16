# HERALD DEC-065 DRAFT: NL Gemeente Proxy Phase 7

**Status:** DRAFT — not yet authorised  
**Precondition:** DEC-064 HPC run complete + authorisation for DEC-065  
**Date:** 2026-06-16

---

## Purpose

DEC-065 will run Phase 7 sector precedence at NL gemeente level using the stock-share proxy panel built in DEC-063. This is methodologically distinct from DEC-064 (PT observed): the target variable is `estimated_births_gemeente` (proxy), not observed births.

---

## Key Constraints (Non-Negotiable)

1. **Proxy label mandatory:** column `evidence_type = proxy_disaggregated_by_stock_share` must be present in all outputs. Never label as `observed_births`.

2. **Run separately from FR/PT:** no pooled FR+PT+NL_gemeente evaluation without a dedicated harmonisation DEC.

3. **Comparison gate:** NL gemeente proxy must reproduce NL COROP observed signal before any gemeente-level claim is made. If COROP-aggregated proxy results diverge from COROP observed (DEC-034), the gemeente analysis is inconclusive.

4. **Sensitivity analysis required (three-track evaluation):**
   - Track A — observed-only (FR + PT + NL COROP)
   - Track B — proxy-included (adds NL gemeente)
   - Track C — proxy-excluded sensitivity (Track A vs Track B delta)

5. **Coverage gate:** only `evidence_status = proxy_computed` rows enter the Phase 7 study (60,498 rows, 73% of proxy panel).

6. **No causal language.**

---

## Evidence Context

| Source | Concept | N units | Evidence type |
|--------|---------|---------|--------------|
| CBS 83631NED | local_unit_opening | 40 COROP (observed) | observed_births |
| CBS 83631NED × 81575NED | stock-share disaggregation | 355 gemeente | proxy_disaggregated_by_stock_share |

Proxy formula:
```
share_gm = stock_gm_sector / sum(stock within COROP for sector×year)
estimated_births_gm = observed_births_corop × share_gm
```
Reaggregation identity: `sum(estimated_births_gm over COROP) == observed_births_corop`  
Verified at DEC-063: max_abs_error = 0.0.

---

## COROP Validation Gate (mandatory pre-condition)

Before any gemeente claim:

**Gate CG1:** Run Phase 7 on the reaggregated proxy panel (sum gemeente proxy by COROP → should match COROP observed panel). If Phase 7 results on reaggregated proxy match Phase 7 results on COROP observed (within tolerance), the proxy allocation is internally consistent.

**Gate CG2:** Promoted pairs in NL COROP (DEC-034: 3 COVID-robust edges) must appear in reaggregated proxy analysis with consistent signs. If signs reverse, the proxy is structurally inconsistent.

**Gate CG3:** In the full gemeente analysis, all promoted relations must be confirmed in the COROP-level analysis first. A gemeente-level "new" relation not visible at COROP is either a disaggregation artefact or a genuine granularity effect — must be labelled explicitly.

---

## Proposed Gates (to be finalised before any run)

| Gate | Description | Blocking? |
|------|-------------|-----------|
| Q1 | Panel has evidence_type=proxy_disaggregated_by_stock_share | Yes |
| Q2 | Only proxy_computed rows used (no NaN births) | Yes |
| Q3 | Reaggregation to COROP within tolerance | Yes |
| Q4 | COROP observed vs COROP-aggregated-proxy concordance ≥ threshold | Yes |
| Q5 | FR/PT observed-only track runs separately | Yes |
| Q6 | Three-track sensitivity analysis produced | Yes |
| Q7 | Permutation control degrades signal | Yes |
| Q8 | No causal language | Yes |
| Q9 | Proxy-excluded sensitivity delta documented | Yes |
| Q10 | Report distinguishes observed-only vs proxy-included results | Yes |

---

## Stock-Share Allocation Sensitivity

An alternative proxy method could use employment share instead of establishment stock share. This is not yet available (no employment data at gemeente×SBI level in open CBS data). If available:
- Alternative: `share_gm = employment_gm / sum(employment within COROP)`
- Compare with stock-share: concordance of top-ranked gemeente per COROP
- If concordance < 70%, proxy method choice materially affects results → report uncertainty

---

## What This DEC Cannot Claim

- That gemeente associations are observed (they are proxy-dependent)
- That gemeente-level promoted relations equal COROP-level relations (granularity effects possible)
- That NL results are directly comparable to FR/PT without harmonisation DEC
- Any causal interpretation

---

## Prerequisites Before Authorisation

1. DEC-064 HPC run complete (PT results final)
2. Decision on threshold calibration (current |β|≥0.10 may exclude all PT/NL effects — DEC-066?)
3. Decision on three-track evaluation framework
4. Explicit authorisation from project owner

---

*HERALD DEC-065 DRAFT | NL Gemeente Proxy Phase 7 | Not yet authorised | 2026-06-16*
