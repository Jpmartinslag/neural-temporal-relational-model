# HERALD DEC-063: Granular FR/PT/NL Evidence Model

**Status:** COMPLETE — 10/10 GATES PASS  
**Decision:** `GRANULAR_FR_PT_NL_PREFLIGHT_READY`  
**Date:** 2026-06-16  
**Follows:** DEC-062 (PT_PANEL_READY_NL_OPEN_DATA_BLOCKED)

---

## Summary

DEC-063 organises the evidence base for running HERALD's sector-precedence analysis (Phase 7) at municipal/gemeente granularity across three countries. It clarifies what is **observed**, what is a **proxy**, and what is **forbidden** before any training or evaluation begins.

| Country | System | N units | Evidence type | Source |
|---------|--------|---------|--------------|--------|
| FR | ZE2020 | 280 | observed_births | SIDRE establishment_creation |
| PT | MUNICIPALITY_CONTINENTE | 278 | observed_births | INE 0009703/0014099 enterprise_birth |
| NL | COROP | 40 | observed_births | CBS 83631NED local_unit_opening |
| NL | GEMEENTE_PROXY | 355 | proxy_disaggregated_by_stock_share | CBS 83631NED × 81575NED |

---

## Part A: Evidence Level Documentation

### France (ZE2020)

- **Concept:** establishment_creation (SIDRE)
- **Level:** ZE2020 (zones d'emploi), 280 units
- **Evidence type:** observed_births
- **Sectors:** 8 observable A10 sectors (FR has observed KZ)
- **Status:** READY — reference layer, Phase 7 already run
- **Known limitation:** Only 1 robust Phase 7 label (RU→MN, COVID-sensitive; see DEC-060)

### Portugal (Municipal Continental)

- **Concept:** enterprise_birth (INE indicators 0009703 / 0014099)
- **Level:** Municipality (continental), 278 units
- **Evidence type:** observed_births
- **Sectors:** 8 observable A10 sectors; **KZ structural_absent** (Finance definitionally excluded from INE enterprise births)
- **Status:** READY_WITH_LIMITATION (KZ absent)
- **Comparable granularity to FR:** 278 vs 280 units

### Netherlands (COROP — observed)

- **Concept:** local_unit_opening (CBS 83631NED, metric: OprichtingenVanVestigingen_1)
- **Level:** COROP (40 regions)
- **Evidence type:** observed_births
- **Sectors:** 9 observable A10 sectors including KZ (Finance present)
- **Status:** READY — lower granularity but fully observed
- **Note:** 83631NED confirmed COROP-only (0 GM codes in RegioS dimension)

### Netherlands (Gemeente — proxy)

- **Concept:** enterprise_birth proxy (NOT observed)
- **Level:** gemeente (355 GMs with current COROP crosswalk; 128 historical GMs unmatched)
- **Evidence type:** proxy_disaggregated_by_stock_share
- **Proxy method:** corop_births_allocated_by_gemeente_stock_share
- **Sources:**
  - Birth source: CBS 83631NED (COROP × SBI × year, observed)
  - Stock source: CBS 81575NED (gemeente × SBI × year, Vestigingen_1 = stock)
  - Crosswalk: CBS 84721NED (gemeente→COROP current vintage)
- **Coverage:** 60,498 proxy_computed rows (73%) out of 82,593 total
- **Reaggregation check:** PASS — re-aggregating proxy by COROP recovers observed births exactly (max absolute error = 0.0)
- **FORBIDDEN:** treating estimated_births_gemeente as observed births

---

## Part B: NL Gemeente Ingest Pipeline

### Step 1: Crosswalk (84721NED)
- Source: CBS gemeente classification table
- 355 current-vintage GM→CR mappings
- Code_8 = COROP code, Naam_9 = COROP name
- Limitation: 128 historical GMs (pre-merger municipalities) not in current crosswalk

### Step 2: Gemeente Stock (81575NED)
- Metric: Vestigingen_1 (establishment stock — NOT births)
- 483 GMs × 19 SBI sections × 19 years (2007–2025) = 9177 rows (wide format)
- SBI section → A10 mapping identical to existing NL COROP pipeline
- Evidence type: observed_stock (never births)

### Step 3: COROP Births (83631NED, existing)
- Already processed in `netherlands_sector_births_cbs_83631NED_corop_a10.csv`
- 40 CORPs × 9 A10 sectors × 19 years = 6,840 rows

### Step 4: Proxy Computation
- For each COROP × A10 × year:
  - `share_gm = stock_gm / sum(stock within COROP)`
  - `estimated_births_gm = observed_births_corop × share_gm`
- If stock total = 0 or NaN: `estimated_births = NaN`, `evidence_status = insufficient_stock_share`
- If no COROP mapping: `evidence_status = no_corop_births_data`

### CBS API Limitations Documented
- 81575NED: 10,000-row query limit; filters `startswith(RegioS,'GM') AND Perioden eq '{year}JJ00' AND (SBI OR-chain)` stay within limit (9177 rows per year call)
- 83631NED: Year+SBI combined filter returns <10k rows (COROP-level only)
- Both tables: no `odata.nextLink` pagination — use per-year or per-section calls

---

## Part C: Training Eligibility Matrix

See `data/processed/european_panel/granular_fr_pt_nl_training_matrix.csv`

| Country | System | Target | Observed | Proxy |
|---------|--------|--------|----------|-------|
| FR | ZE2020 | observed_births (establishment_creation) | ✓ | ✗ |
| PT | MUNICIPALITY_CONTINENTE | observed_births (enterprise_birth) | ✓ | ✗ |
| NL | COROP | observed_births (local_unit_opening) | ✓ | ✗ |
| NL | GEMEENTE_PROXY | estimated_births_gemeente (PROXY) | ✗ | ✓ |

**Cross-country concept alignment (non-causal note):** FR uses `establishment_creation`, PT uses `enterprise_birth`, NL uses `local_unit_opening`. These are associated but not identical across national statistical frameworks. Pooled analysis requires a dedicated harmonisation DEC.

---

## Part D: Reaggregation Verification

**Mathematical identity:** If proxy is constructed correctly, summing gemeente proxy births within a COROP must recover the original COROP births exactly.

**Result:** PASS — max absolute error = 0.0, max relative error = 0.0.

This is expected: `sum(births_corop × share_gm) = births_corop × sum(share_gm) = births_corop × 1.0`

---

## Gates G1-G10

**GATE_VERSION:** DEC-063-v1

| Gate | Description | Verdict |
|------|-------------|---------|
| G1 | All source files exist (83631NED, 81575NED, crosswalk, proxy) | PASS |
| G2 | 83631NED confirmed 0 GM codes, ≥40 CR codes | PASS |
| G3 | 81575NED metric = Vestigingen_1, evidence_type = observed_stock | PASS |
| G4 | Proxy re-aggregates to COROP births (reaggregation error = 0.0) | PASS |
| G5 | FR and PT panels have no proxy evidence_type | PASS |
| G6 | PT sector_KZ = all NaN (structural_absent), no zeros | PASS |
| G7 | No raw API dumps >2MB committed | PASS |
| G8 | 66/66 tests pass | PASS |
| G9 | No causal language in manifests or report | PASS |
| G10 | Report, contract, CODEX_MEMORY, registry updated | PASS |

---

## Outputs

| File | Type | Rows |
|------|------|------|
| `data/processed/european_panel/nl_gemeente_corop_crosswalk.csv` | Crosswalk | 355 |
| `data/processed/european_panel/nl_gemeente_stock_panel.csv` | Stock (wide) | 9,177 |
| `data/processed/european_panel/nl_gemeente_stock_manifest.json` | Manifest | — |
| `data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv` | Proxy (long) | 82,593 |
| `data/processed/european_panel/nl_gemeente_birth_proxy_manifest.json` | Manifest | — |
| `data/processed/european_panel/granular_fr_pt_nl_training_matrix.csv` | Eligibility | 4 |
| `data/processed/european_panel/dec063_gates.json` | Gate results | — |

---

## Prohibitions Compliance

- **Não treinar modelo neural**: No training. ✓
- **Não rodar Phase 7 completa**: No Phase 7 run. ✓
- **Não usar stock como substituto de birth sem nova DEC**: Stock used only as share denominator in proxy; birth source remains 83631NED; proxy is clearly labelled. ✓
- **Não usar linguagem causal**: No causal language used. ✓
- **Não commitar raw grande**: No large raw API dumps committed; API parameters in manifests. ✓
- **Não promover relações novas**: No relation promotion. ✓
- **Não assumir 'não achei no CBS' = inexistência**: CBS Microdata ABR path documented in DEC-062. ✓

---

## Next Steps (requires new DEC)

1. **DEC-064**: Run Phase 7 sector-precedence at PT municipal level (278 municipalities)
2. **DEC-065**: Run Phase 7 at NL gemeente level using proxy — separate from observed results; proxy-excluded sensitivity analysis required
3. **DEC-066**: Cross-country concept harmonisation before pooled FR/PT/NL training

---

*HERALD DEC-063 | Granular FR/PT/NL Evidence Model | GRANULAR_FR_PT_NL_PREFLIGHT_READY*
