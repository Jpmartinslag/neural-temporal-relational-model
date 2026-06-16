# HERALD DEC-062: Granular Phase 7 Preflight
## PT Municipal Panel Build + NL Gemeente Source Search

**Status:** COMPLETE — 10/10 GATES PASS  
**Decision:** `PT_PANEL_READY_NL_OPEN_DATA_BLOCKED`  
**Date:** 2026-06-16  
**Follows:** DEC-061 (PT_READY_NL_BLOCKED confirmed)

---

## Summary

DEC-062 has three outputs:

1. **PT municipal sector panel** (`pt_municipal_sector_panel.csv`): 278 continental municipalities × 16 years (2008–2023), 8 observable A10 sectors, enterprise births from INE indicators 0009703 (NUTS2013) and 0014099 (NUTS2024).
2. **NL gemeente source search**: Systematic CBS Open Data catalog audit confirms no table with gemeente × births × SBI × ≥6 years exists in open access.
3. **Granular Phase 7 readiness**: FR ZE2020 (280 units) READY; PT continental READY_WITH_LIMITATION (KZ structural_absent); NL gemeente BLOCKED; NL COROP (40 units) READY as fallback.

---

## Part A: DEC-061 Review

DEC-061 reported 297 continental PT municipalities. Correct value is **278**.

| Item | DEC-061 | Corrected (DEC-062) |
|------|---------|---------------------|
| Continental filter | `geocod[0] in ('1','2')` | `geocod[0] == '1'` |
| N municipalities | 297 | 278 |
| Discrepancy source | Açores (prefix 2) included | Açores correctly excluded |

**INE geocod structure (7-character codes):**

- `1XXXXXX` — Continental Portugal (278 municipalities)
- `2XXXXXXX` — Açores archipelago (19 municipalities)
- `3XXXXXXX` — Madeira archipelago (11 municipalities)
- All other formats — national/regional aggregates, filtered out

**NUTS2013 → NUTS2024 geocod transition:** At year 2023, INE changed indicator from 0009703 to 0014099. 176 of 278 continental municipalities received new all-numeric geocods (e.g., `16B1001` → `1910101`). Only 102 municipalities retained their code. Without harmonisation, the panel would contain 454 unique geocods (278 + 176). The `_harmonise_geocods()` function uses municipality name (`geodsg`) as join key to adopt the NUTS2024 canonical geocod throughout all years.

---

## Part B: PT Municipal Sector Panel

**Source:** INE API — indicator 0009703 (2008–2022) + 0014099 (2023)  
**Filter:** `geocod[0] == '1'` (continental Portugal only)  
**Panel dimensions:** 278 municipalities × 16 years = 4,448 rows

### CAE → A10 Mapping

| CAE Section | A10 Bucket | Note |
|-------------|-----------|------|
| A (Agriculture) | OQ | Merged into OQ per HERALD PT convention |
| B, C, D, E | BE | Industry |
| F | FZ | Construction |
| G, H, I | GI | Trade/Transport/Hospitality |
| J | JZ | ICT |
| K (Finance) | — | **Structural absent** — definitionally excluded from INE enterprise births |
| L | LZ | Real estate |
| M, N | MN | Business services |
| O, P, Q | OQ | Public/Education/Health |
| R, S | RU | Arts/Other services |

**KZ status:** `sector_KZ` is `NaN` throughout — structural absence, not observed zeros.

### Missing vs Zero vs Structural Absent

- **Genuine zero** (`valor='0'`): observed year with zero enterprise births → stored as `0.0`
- **Missing/suppressed** (`valor=''` or absent): → stored as `NaN`
- **Structural absent** (KZ): → `NaN` by definition, never `0`

### Sector Coverage

All 8 observable sectors at 100% coverage across all 278 municipalities and 16 years.

| Sector | Coverage |
|--------|----------|
| BE, FZ, GI, JZ, LZ, MN, OQ, RU | 100% |
| KZ | structural_absent |

### Lag and Growth Variables

- `lag1_births`, `lag2_births`: causal lags (t−1, t−2) computed within each municipality
- `growth_1y`: `(target_births[t] − target_births[t−1]) / target_births[t−1]`; `NaN` in first year
- `growth_2y`: analogous over 2-year window
- First observation per municipality has `NaN` growth/lag (no prior year available)

---

## Part C: NL Gemeente Source Search

**Search method:** CBS ODataCatalog systematically scanned (8 search term combinations, 10 pages each). 4 known tables from DEC-061 documented, additional catalog matches probed.

**Criterion for acceptability:** gemeente × births/oprichtingen × SBI/bedrijfstak × ≥6 years

### Known Tables

| Table ID | Title | Verdict | Reason |
|----------|-------|---------|--------|
| 83631NED | Vestigingen en oprichtingen; bedrijfstak, regio | COROP_ONLY | No gemeente level — only COROP (40), province, national |
| 81575NED | Vestigingen van bedrijven; bedrijfstak, gemeente | STOCK_ONLY | Stock (bestand), not births/oprichtingen |
| 81841NED | Oprichtingen en opheffingen; bedrijfstak, regio | COROP_ONLY | No gemeente level; period 2007–2013 only |
| 80234ned | Vestigingen; SBI, gemeenten 2006–2010 | STOCK_ONLY | Stock data; period too short |

**Result:** 0 acceptable open-data tables found.

**NL Decision:** `NL_GEMEENTE_OPEN_DATA_BLOCKED`

**Note on absence:** "No open-data source found" does not mean no data exists. CBS Microdata (ABR — Algemeen Bedrijfsregister) contains gemeente × SBI × oprichtingen at quarterly granularity. Access requires a formal application via an affiliated academic institution through the CBS Research Data Center. This constitutes a path forward for a future DEC.

---

## Part D: Granular Phase 7 Readiness

| Country | System | N Units | Status | Limitation |
|---------|--------|---------|--------|-----------|
| FR | ZE2020 | 280 | READY | None |
| PT | MUNICIPALITY_CONTINENTE | 278 | READY_WITH_LIMITATION | KZ structural_absent |
| NL | COROP (fallback) | 40 | READY | Lower granularity |
| NL | GEMEENTE | 342 | BLOCKED | No open data births × SBI |

**Granularity comparison — FR vs PT:**
- FR ZE2020: 280 zones d'emploi
- PT municipal: 278 concelhos continentais
- Comparable granularity — difference of 2 units

**KZ limitation for PT:** Finance sector (K) is definitionally excluded from INE enterprise births (all registered enterprises, not openings in finance). This sector is structurally absent across all countries in HERALD. KZ absence does not prevent Phase 7 — sector-precedence analysis operates on the 8 observable sectors, and cross-country comparison remains valid as KZ is absent in FR and NL as well.

**Cross-country concept note (non-causal):** FR uses `establishment_creation`, PT uses `enterprise_birth`, NL uses `local_unit_opening`. These are associated with but not identical to each other. Harmonisation for cross-country pooling requires a dedicated DEC before any pooled analysis.

---

## Part E: Gates H1-H10

**GATE_VERSION:** DEC-062-v1  
**Result:** 10/10 PASS

| Gate | Description | Verdict |
|------|-------------|---------|
| H1 | DEC-061 review complete; continental filter corrected | PASS |
| H2 | PT panel built (CSV + manifest, >1000 rows) | PASS |
| H3 | Continental filter = geocod[0]=='1'; no Açores/Madeira | PASS |
| H4 | 8 observable A10 sectors; KZ = structural_absent | PASS |
| H5 | Missing/zero/structural_absent distinction documented | PASS |
| H6 | CBS catalog searched (≥4 tables, ≥5 search terms) | PASS |
| H7 | NL decision conservative; no stock promoted; no COROP as gemeente | PASS |
| H8 | Readiness JSON covers FR, PT, NL | PASS |
| H9 | No unauthorized model training; no full Phase 7 run | PASS |
| H10 | Manifests contain URLs, indicator IDs, query params | PASS |

---

## Outputs

| File | Description |
|------|-------------|
| `data/processed/european_panel/pt_municipal_sector_panel.csv` | PT panel (4448 rows) |
| `data/processed/european_panel/pt_municipal_sector_panel_manifest.json` | Build manifest |
| `data/processed/granular_phase7_preflight/dec061_review.json` | DEC-061 discrepancy review |
| `data/processed/granular_phase7_preflight/nl_gemeente_source_candidates.csv` | NL CBS table verdicts |
| `data/processed/granular_phase7_preflight/nl_gemeente_source_search.json` | NL search full results |
| `data/processed/granular_phase7_preflight/granular_phase7_readiness.json` | Per-country readiness |
| `data/processed/granular_phase7_preflight/dec062_gates.json` | H1-H10 gate results |

---

## Prohibitions Compliance

- **Não treinar modelo neural**: No model training. ✓
- **Não rodar Phase 7 completa**: No Phase 7 run. ✓
- **Não usar stock como substituto de birth**: 81575NED rejected as STOCK_ONLY. ✓
- **Não usar linguagem causal**: No causal language used. ✓
- **Não commitar raw grande**: Only processed CSV committed; raw INE responses not committed. ✓
- **Não promover relações novas**: No relation promotion. ✓
- **Não assumir 'não achei no CBS' = inexistência**: CBS Microdata path documented. ✓

---

## Next Steps (requires new DEC)

1. **DEC-063**: Run Phase 7 sector-precedence analysis at PT municipal level (278 municipalities, 8 sectors, enterprise births)
2. **DEC-064**: CBS Microdata ABR access application for NL gemeente × births × SBI
3. **DEC-065** (optional): Concept harmonisation protocol for cross-country pooling of FR/PT/NL enterprise births

---

*HERALD DEC-062 | Granular Phase 7 Preflight | PT READY · NL OPEN DATA BLOCKED*
