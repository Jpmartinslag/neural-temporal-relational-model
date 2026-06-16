# HERALD: Granular FR/PT/NL Training Contract

**DEC-063 | Gate G10 Artifact**  
**Date:** 2026-06-16  
**Decision:** `GRANULAR_FR_PT_NL_PREFLIGHT_READY`

---

## Purpose

This contract defines what may and may not be done with each evidence layer in the granular FR/PT/NL panel before training, during evaluation, and when reporting results. It is a binding reference for DEC-064 (PT Phase 7), DEC-065 (NL gemeente Phase 7), and any pooled analysis.

---

## Evidence Layers

### Layer 1: France ZE2020 — `observed_births`

| Property | Value |
|----------|-------|
| Column | `observed_births` |
| Evidence type | `observed_births` |
| Source | SIDRE establishment_creation |
| N regions | 280 (ZE2020) |
| Sectors | 8 observable A10 (KZ present) |
| Status | READY |

**Contract:**
- MAY use as training target without special labelling (fully observed)
- MAY compare with other observed layers (PT, NL COROP)
- MAY claim temporal precedence at ZE2020 level
- MUST apply COVID-sensitivity check to all sector-pair labels
- MUST NOT make universal generalisations beyond FR ZE2020 without replication test
- MUST NOT use causal language

---

### Layer 2: Portugal Municipality — `observed_births`

| Property | Value |
|----------|-------|
| Column | `observed_births` |
| Evidence type | `observed_births` |
| Source | INE indicators 0009703 / 0014099, enterprise_birth |
| N regions | 278 (municipality, continental) |
| Sectors | 8 observable A10; KZ structural_absent |
| Status | READY_WITH_LIMITATION |

**Contract:**
- MAY use as training target without special labelling (fully observed)
- MAY compare with FR ZE2020 results; must note different enterprise birth concept
- MAY claim temporal precedence at municipal level
- MUST NOT make claims that depend on KZ (Finance sector): KZ is all-NaN, never imputed
- MUST NOT treat zero KZ entries as real data (sector is excluded by INE definition)
- MUST NOT mix PT with proxy layers in the same evaluation run without `evidence_type` segregation
- MUST NOTE: enterprise_birth (PT) ≠ establishment_creation (FR) ≠ local_unit_opening (NL); pooled claims require a dedicated harmonisation DEC (DEC-066)
- MUST NOT use causal language

---

### Layer 3: Netherlands COROP — `observed_births`

| Property | Value |
|----------|-------|
| Column | `observed_births` |
| Evidence type | `observed_births` |
| Source | CBS 83631NED, OprichtingenVanVestigingen_1 |
| N regions | 40 (COROP) |
| Sectors | 9 observable A10 including KZ (Finance present) |
| Status | READY |

**Contract:**
- MAY use as training target without special labelling (fully observed)
- MAY compare with FR/PT observed layers with concept note
- MAY use as validation reference for gemeente proxy (reaggregation check)
- MUST NOT extrapolate COROP-level results to gemeente level without proxy layer (DEC-065)
- MUST NOT use causal language

---

### Layer 4: Netherlands Gemeente — `proxy_disaggregated_by_stock_share`

| Property | Value |
|----------|-------|
| Column | `estimated_births_gemeente` |
| Evidence type | `proxy_disaggregated_by_stock_share` |
| Proxy method | `corop_births_allocated_by_gemeente_stock_share` |
| Birth source | CBS 83631NED (COROP births) |
| Stock source | CBS 81575NED (gemeente establishment stock) |
| N regions | 355 GMs with crosswalk (60,498 proxy_computed rows, 73%) |
| Sectors | All 9 A10 sectors attempted |
| Status | PROXY — requires separate evaluation path |

**Contract:**
- MUST label column as `estimated_births_gemeente` — NEVER as `observed_births`
- MUST carry `evidence_type = proxy_disaggregated_by_stock_share` in all output files
- MUST report proxy-excluded sensitivity: run evaluation twice — (a) observed-only, (b) proxy-included — and report both
- MUST flag rows with `evidence_status != "proxy_computed"` as non-trainable or explicitly excluded
- MUST NOT treat estimated_births as ground truth without qualification
- MUST NOT report proxy-inclusive results as primary without noted limitations
- MUST NOT use proxy layer for absolute birth count claims at gemeente level
- MUST verify that re-aggregation to COROP preserves observed births identity (max_abs_error ≤ 5.0) on any regeneration
- MUST NOT use causal language
- SHOULD report N proxy_computed / N total and coverage by sector in any evaluation summary

---

## Evaluation Requirements (any run using this panel)

### Required fields in every output row

```
evidence_type        # observed_births | proxy_disaggregated_by_stock_share
evidence_status      # proxy_computed | no_corop_births_data | insufficient_stock_share | missing_gemeente_stock
country              # FR | PT | NL
region_level         # ZE2020 | MUNICIPALITY | COROP | GEMEENTE
```

### Required reporting sections in evaluation outputs

1. **Observed-only results** (FR + PT + NL COROP only; geen proxy)
2. **Proxy-included results** (NL Gemeente added)
3. **Proxy-excluded sensitivity** (observed-only vs proxy-included delta)
4. **KZ note** (PT KZ excluded; NL KZ included; FR KZ included)
5. **Concept alignment note** (establishment_creation ≠ enterprise_birth ≠ local_unit_opening)

---

## Forbidden Actions (all layers)

| Forbidden | Reason |
|-----------|--------|
| Treat `estimated_births_gemeente` as `observed_births` | Core evidence integrity |
| Omit proxy-excluded sensitivity | Prevents masking proxy inflation |
| Use KZ values for PT claims | KZ structural_absent in INE |
| Use causal language | Standard HERALD methodological constraint |
| Pool FR/PT/NL without concept note | Statistical concept heterogeneity |
| Run Phase 7 or neural training without new DEC | DEC-063 scope limit |
| Commit raw CBS API dumps > 2MB | G7 gate |

---

## Reaggregation Identity (mandatory verification on proxy regeneration)

For any regeneration of the proxy:
```
sum(estimated_births_gemeente over gemeenten in COROP) == observed_births_corop
```
Tolerance: max_abs_error ≤ 5.0 AND max_rel_error ≤ 0.001  
Current verified result: max_abs_error = 0.0, max_rel_error = 0.0

Any regeneration producing max_abs_error > 5.0 → gate G4 FAILS → decision = BLOCKED_PROXY_INVALID

---

## Coverage Summary

| Layer | N regions | N obs rows | Proxy coverage |
|-------|-----------|------------|----------------|
| FR ZE2020 | 280 | fully observed | — |
| PT Municipal | 278 | fully observed | — |
| NL COROP | 40 | fully observed | — |
| NL Gemeente | 355 (current) | 82,593 total | 73% proxy_computed |

---

## Next DEC Requirements

| DEC | Precondition |
|-----|-------------|
| DEC-064 (PT Phase 7) | This contract; GRANULAR_FR_PT_NL_PREFLIGHT_READY |
| DEC-065 (NL gemeente Phase 7) | DEC-064 complete; proxy-excluded sensitivity plan |
| DEC-066 (Pooled FR/PT/NL) | DEC-065 complete; concept harmonisation decision |

---

*HERALD DEC-063 Training Contract | GRANULAR_FR_PT_NL_PREFLIGHT_READY | 2026-06-16*
