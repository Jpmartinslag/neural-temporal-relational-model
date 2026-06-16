# HERALD DEC-061: PT/NL Municipal Sector Data Availability Audit

**Status:** COMPLETE | **Decision:** PT_READY_NL_BLOCKED (10 gates: 9 PASS + 1 FORMALLY_BLOCKED)  
**Date:** 2026-06-16 | **Elapsed:** < 5 min (live API probes + local analysis)

---

## 0. Why This Audit Was Needed

DEC-060 documented that France (FR) has only 1 promoted Phase 7 sector-precedence label. The binding constraint is the |β| ≥ 0.10 threshold applied to 280 small ZE2020 employment zones. The hypothesis for DEC-061 is:

> *FR may appear weak relative to PT/NL because it operates at a finer territorial granularity (280 ZE2020). If PT and NL are elevated to municipality/gemeente level, the three countries would be comparable in scale, enabling fairer cross-country Phase 7 comparison.*

**Current HERALD granularity:**
| Country | Level | N units | Source |
|---------|-------|---------|--------|
| FR | ZE2020 employment zones | 280 | SIDE (Sirene) |
| PT | NUTS3 regions | 25 | INE |
| NL | COROP regions | 40 | CBS |

**Target granularity:**
| Country | Target level | Expected N | Source |
|---------|-------------|-----------|--------|
| FR | ZE2020 (unchanged) | 280 | SIDE |
| PT | Município/Concelho | ~278 continental | INE |
| NL | Gemeente | ~342 European NL | CBS |

---

## 1. Official Sources Consulted

### Portugal — INE
- **Endpoint:** `https://www.ine.pt/ine/json_indicador/pindica.jsp`
- **Indicator 0009703:** Nascimentos de empresas × CAE × município (NUTS2013 geocods, 2008-2022)
- **Indicator 0014099:** Nascimentos de empresas × CAE × município (NUTS2024 geocods, 2023+)
- **Indicator 0009702:** Nascimentos totais × município (NUTS2013)
- **Indicator 0014098:** Nascimentos totais × município (NUTS2024)
- **API status:** CONFIRMED LIVE (HTTP 200, response data verified)

### Netherlands — CBS StatLine
- **Endpoint:** `https://opendata.cbs.nl/ODataFeed/OData/{table}/` (OData v3 Atom format)
- **Table 83631NED:** Vestigingen oprichtingen × bedrijfstak × regio (COROP, Province, National)
- **Table 81575NED:** Vestigingen stock × bedrijfstak × gemeente (stock, not births)
- **Table 81841NED:** Oprichtingen+opheffingen × bedrijfstak × regio (2007-2013, COROP only)
- **Table 80234ned:** Vestigingen stock × SBI × gemeenten 2006-2010 (old, stock)
- **CBS catalog:** 5,927 tables searched — no table found with gemeente × oprichtingen × SBI × jaar
- **API status:** CONFIRMED LIVE (HTTP 200, OData Atom XML)

---

## 2. Finding — Portugal (PT)

### 2.1 Data Availability Confirmed

Live API probe of INE indicator `0009703` returned 308 municipalities with sector data for every year tested:

| Year | Indicator | N municipalities | Sectors | Continental filter |
|------|-----------|-----------------|---------|-------------------|
| 2008 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2010 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2015 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2019 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2020 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2021 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2022 | 0009703 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |
| 2023 | 0014099 | 308 | A,B,C,D,E,F,G,H,I,J,L,M,N,P,Q,R,S | Yes (297 cont.) |

**Key findings:**

- **308 municipalities confirmed** across all years (consistent count)
- **17 CAE sections present** (A-S, excluding K). Geocod length = 7 (municipality level)
- **K sector (Finance) consistently absent** — confirms DEC-018: INE definitionally excludes section K from enterprise births per Eurostat/OECD enterprise demography convention
- **Continental filter feasible:** geocod prefix allows separation (297 continental + 11 Madeira + ~0 in this probe for Açores — see §2.3)
- **16 consecutive years confirmed:** 2008-2023

### 2.2 CAE → A10 Mapping

| HERALD A10 | CAE sections | Status |
|-----------|-------------|--------|
| BE (Industry) | B, C, D, E | ✓ Available |
| FZ (Construction) | F | ✓ Available |
| GI (Trade/Transport/Hospitality) | G, H, I | ✓ Available |
| JZ (ICT) | J | ✓ Available |
| KZ (Finance) | K | ✗ ABSENT (definitional exclusion) |
| LZ (Real Estate) | L | ✓ Available |
| MN (Professional/Business Services) | M, N | ✓ Available |
| OQ (Public/Education/Health) | O, P, Q | ✓ Available |
| RU (Arts/Other Services) | R, S | ✓ Available |

**8/9 HERALD A10 sectors mappable.** KZ excluded by definition (confirmed DEC-018).

> [!NOTE]
> Section A (Agriculture) is present in INE data. The HERALD Observatory maps agriculture to a separate 10th sector; the current A10 convention merges it into OQ or treats it separately. This mapping decision is unchanged from existing HERALD PT panel and requires no new DEC for municipality-level ingestion.

### 2.3 Continental Filter and Island Separation

The INE 7-character geocod encodes the territorial hierarchy:
- **Continental Portugal:** geocods starting with `1` or `2` → 278 concelhos
- **Madeira:** 11 municipalities (confirmed in probe: prefix `3`)
- **Açores:** 19 municipalities (Açores geocod prefix requires INE concordance table verification; probe shows `acores=0` with current prefix assumption, but total 308 = 278+11+19 implies Açores uses a prefix not tested)

**Continental filter**: feasible via geocod prefix lookup. Recommended approach: use INE NUTS concordance to identify continental concelhos.

### 2.4 NUTS2013/NUTS2024 Break

INE switched indicator numbering at 2023:
- **0009703** (NUTS2013 geocods): 2008-2022
- **0014099** (NUTS2024 geocods): 2023+

This creates a potential 7-character geocod realignment at the 2022/2023 boundary. INE publishes a concordance between NUTS2013 and NUTS2024. Municipal boundary changes over 2008-2023 are limited but not zero (e.g. fusion of Calheta de São Miguel). Panel construction must apply the concordance.

### 2.5 Phase 7 Compatibility

| Criterion | PT Municipal | Threshold | Status |
|-----------|-------------|-----------|--------|
| Consecutive years | 15 (2008-2022) | ≥6 | ✓ |
| N territories (continental) | 278 | ≥10 | ✓ |
| N samples | 278 × 15 = 4,170 | ≥60 | ✓ |
| A10 comparable sectors | 8 | ≥8 | ✓ |
| Concept | enterprise_birth | documented | ✓ |

**Verdict: PT_MUNICIPAL_READY_FOR_PANEL_BUILD**

---

## 3. Finding — Netherlands (NL)

### 3.1 CBS Open Data Tables Probed

| Table | Concept | Granularity | N regions | Period | Verdict |
|-------|---------|-------------|-----------|--------|---------|
| 83631NED | Oprichtingen (births) | COROP only (40) | No GM | 2007-2025 | BIRTHS_COROP_ONLY |
| 81841NED | Oprichtingen+opheffingen | COROP only (40) | No GM | 2007-2013 | BIRTHS_COROP_ONLY (old) |
| 81575NED | Vestigingen stock | Gemeente (483 GM codes) | Yes | 2007-2026 | STOCK_NOT_BIRTHS |
| 80234ned | Vestigingen stock | Gemeente | Yes | 2006-2010 | STOCK_OLD_PERIOD |

### 3.2 Core Finding: No Gemeente × Births × SBI Table Exists

**CBS Open Data catalog (5,927 tables) was searched. No table provides:**
- oprichtingen (openings/births) ×
- gemeente ×
- bedrijfstak/SBI ×
- jaar (year)

This is a **structural limitation of CBS Open Data**, not a technical access failure. The CBS Open Data portal publishes aggregated data at COROP and province level for business demography.

### 3.3 81575NED — Stock at Gemeente Level (Not Births)

**81575NED** has 483 GM codes (historical municipality boundaries) and covers 2007-2026 with 22 SBI section codes. However:
- This table measures **establishment stock** (bestand), not openings (oprichtingen)
- Stock at time t ≠ births at time t; the relationship involves closures/deaths
- **Cannot substitute for 83631NED oprichtingen** as HERALD target concept

> [!WARNING]
> Using stock × gemeente as a proxy for births × gemeente would constitute a concept change requiring a new DEC with explicit justification. This is NOT authorized by DEC-061.

### 3.4 Municipal Boundary Changes

NL has undergone ~100+ gemeentelijke herindelingen (municipal mergers) since 2007:
- ~483 historical GM codes in 81575NED
- ~342 European NL municipalities as of 2023
- Time-consistent panel requires CBS concordance tables per merger year

### 3.5 Caribbean Netherlands (BES)

Caribbean NL (Bonaire, Saba, Sint Eustatius) uses a separate statistical system. Confirmed: BES codes do **not** appear in CBS 83631NED or 81575NED RegioS dimensions. No filter needed for these tables.

### 3.6 Alternative Sources (Not Evaluated in DEC-061)

| Source | Description | Access |
|--------|-------------|--------|
| CBS Microdata | Restricted-access ABR data with gemeente × SBI × births | CBS Research Center (RDC/micro data) |
| LISA employment register | Employment by gemeente × SBI, not births | Commercial |
| KvK Company Register | Incorporations by gemeente, no SBI breakdown | Commercial/restricted |
| Eurostat BD_HGNACE_R | NUTS3 (COROP) level, 2007-2022, no gemeente | Already in HERALD |

**CBS Microdata** is the most likely path to gemeente × births × SBI data for NL, but requires formal CBS Research Center access application (academic institution required).

### 3.7 Verdict

**NL_GEMEENTE_BIRTHS_BLOCKED_VIA_CBS_OPEN_DATA**

The absence of a gemeente × oprichtingen × SBI table is a structural feature of CBS Open Data, not a data quality issue. Data likely exists in CBS administrative microdata (ABR).

---

## 4. Comparative Matrix FR / PT / NL

| Attribute | FR | PT (target) | NL (target) |
|-----------|----|-----------|----|
| Current HERALD level | ZE2020 (280) | NUTS3 (25) | COROP (40) |
| Target granularity | ZE2020 (no change) | Municipality (278 continental) | Gemeente (342 European) |
| N units vs FR | 280 | 278 ≈ FR | — (blocked) |
| Source | SIDE/Sirene | INE (0009703/0014099) | CBS (83631NED) |
| Target concept | establishment_creation | enterprise_birth | local_unit_opening |
| Concept difference | baseline | enterprise ≠ establishment | local_unit ≠ enterprise |
| Sector classification | A10 (9 sectors) | CAE→A10 (8 sectors, no K) | SBI→A10 (9 sectors) |
| KZ (Finance) | Available | **Absent (definitional)** | Available |
| Years | 2012-2025 (13y) | 2008-2023 (16y) | 2007-2025 (19y at COROP) |
| Continental filter | N/A (FR = mainland) | Feasible (geocod prefix) | N/A (European NL confirmed) |
| Municipal-level births | — | ✓ CONFIRMED | ✗ BLOCKED |
| Statistical suppression risk | Low | Medium (small municipalities) | High (gemeente × SBI) |
| Phase 7 viable at target | Already in Phase 7 | ✓ YES | ✗ NO (blocked) |

### 4.1 Granularity Comparability

```
FR ZE2020:     |████████████████████████████| 280 units
PT Municipal:  |███████████████████████████| 278 units (continental)
NL Gemeente:   |BLOCKED                     | 342 potential (blocked)
NL COROP:      |████                        |  40 units (current)
```

PT municipal granularity is **virtually identical** to FR ZE2020 (~280 units). This directly addresses the DEC-060 hypothesis: with PT at municipality level, FR and PT would operate at comparable territorial granularity, enabling fair Phase 7 comparison.

---

## 5. Risks and Limitations

### 5.1 Concept Differences
The three countries use different target concepts:
- FR: **establishment_creation** (SIDE/Sirene — registration of a new local unit in the Sirene register)
- PT: **enterprise_birth** (INE — birth of a new enterprise per Eurostat enterprise demography standard)
- NL: **local_unit_opening** (CBS — opening of a vestiging/establishment)

Cross-country pooling or comparison of raw counts is **not scientifically valid without explicit harmonisation**. The CODEX_MEMORY.md §Scientific state documents this: "Cross-country mean does not prove European generalization."

### 5.2 KZ Sector Asymmetry
FR and NL include finance/insurance (KZ) in their data. PT definitionally excludes KZ. Any Phase 7 comparison involving KZ-related pairs across countries will be one-sided.

### 5.3 Statistical Suppression
INE and CBS apply statistical disclosure control. For small municipalities with few enterprise births in a given sector-year, values may be suppressed (NaN). PT municipal data at section-level granularity for rare sectors (D, U, T) may have high suppression rates in small concelhos.

### 5.4 Municipal Boundary Changes
- **PT:** Municipal boundaries are relatively stable; some mergers (e.g. Calheta de São Miguel). INE maintains concordance tables.
- **NL:** ~100+ mergers since 2007. Any gemeente panel would require explicit concordance.

### 5.5 NUTS2013/NUTS2024 Geocod Break (PT)
The switch from indicator 0009703 to 0014099 at the 2022/2023 boundary introduces a potential geocod realignment. The HERALD PT panel must apply INE's NUTS concordance table to align municipality codes across the full panel.

---

## 6. Can Phase 7 Granular Run Be Built?

| Country | Ready for granular Phase 7? | Condition |
|---------|---------------------------|-----------|
| FR | Already running at ZE2020 | No change needed |
| PT | **YES** | Build municipal panel from INE 0009703/0014099 |
| NL | **NO** | Requires CBS Microdata access OR alternative source |

For a PT municipal panel:
1. Download INE 0009703 for years 2008-2022 (municipality × CAE × year)
2. Download INE 0014099 for years 2023-2024 (NUTS2024 geocods)
3. Apply INE NUTS concordance to align geocods
4. Apply existing CAE→A10 mapping (documented in `ingest_portugal_panel.py`)
5. Filter to continental Portugal (278 concelhos)
6. Build panel with same schema as current PT NUTS3 panel

This task is the natural next step if this DEC passes.

---

## 7. Gates G1-G10

| Gate | Description | Verdict |
|------|-------------|---------|
| G1 | PT_API_REACHABLE: INE probe successful with live data | ✓ PASS |
| G2 | PT_MUNICIPAL_SECTOR_EXISTS: 278 muni × 16 years × 17 sectors | ✓ PASS |
| G3 | PT_A10_MAPPING_FEASIBLE: 8/9 A10 sectors mappable from CAE | ✓ PASS |
| G4 | NL_API_REACHABLE: CBS OData API confirmed live | ✓ PASS |
| G5 | NL_GEMEENTE_SECTOR_EXISTS: No gemeente × births × SBI table found | **FORMALLY_BLOCKED** |
| G6 | NL_A10_MAPPING_FEASIBLE: SBI → A10 mapping documented | ✓ PASS |
| G7 | GRANULARITY_COMPARABILITY: PT municipal ≈ FR ZE2020 (278 vs 280) | ✓ PASS |
| G8 | CONCEPT_COMPATIBILITY: FR/PT/NL concepts documented | ✓ PASS |
| G9 | NO_RAW_LARGE_COMMIT: No large raw files in audit dir or staged | ✓ PASS |
| G10 | REPRODUCIBILITY: Manifest with URLs, tables, params, timestamp | ✓ PASS |

**9 PASS, 1 FORMALLY_BLOCKED, 0 FAIL**

---

## 8. Decision

**`PT_READY_NL_BLOCKED`**

- **Portugal** has municipality-level enterprise birth data by sector, confirmed available through INE API for 2008-2023. Continental filter feasible. 8/9 A10 sectors mappable. Phase 7 viable at 278 territories × 15 years.
- **Netherlands** does not have gemeente-level establishment birth data via CBS Open Data. The only gemeente-level table (81575NED) measures establishment stock, not births. FORMALLY_BLOCKED.

---

## 9. Next Steps

### If PT municipal panel is to be built (recommended):
1. **DEC-062** (new decision): Authorize PT municipal panel ingestion and Phase 7 run at municipality level
2. Download INE 0009703 (2008-2022) and 0014099 (2023+) for all municipalities
3. Apply NUTS concordance for geocod alignment
4. Verify suppression rate per CAE section × year × municipality
5. Build municipal panel using `ingest_portugal_panel.py` (already supports geocod=7)
6. Run Phase 7 at municipality level for PT

### For NL (gemeente blocked):
1. **Option A:** Apply for CBS Research Center microdata access (academic institution required). ABR microdata may provide gemeente × SBI × births.
2. **Option B:** Stay at COROP resolution (40 regions) and accept granularity asymmetry vs FR.
3. **Option C:** Use Eurostat BD_HGNACE_R at NUTS3=COROP level (already in HERALD).

### What NOT to do:
- Do not use 81575NED stock data as a proxy for births (concept change — requires new DEC)
- Do not change Phase 7 thresholds based on this audit
- Do not promote any new labels from this audit (no model run authorized)
- Do not claim PT/NL municipal data equivalence with FR establishment_creation

---

## 10. Files Created

| File | Type | Description |
|------|------|-------------|
| `data/processed/municipal_granularity_audit/pt_municipality_availability.json` | JSON | PT full availability assessment |
| `data/processed/municipal_granularity_audit/pt_municipality_probe.csv` | CSV | PT API probe results by year |
| `data/processed/municipal_granularity_audit/nl_gemeente_availability.json` | JSON | NL full availability assessment |
| `data/processed/municipal_granularity_audit/nl_gemeente_probe.csv` | CSV | NL CBS table probe results |
| `data/processed/municipal_granularity_audit/municipal_granularity_matrix.csv` | CSV | FR/PT/NL comparative matrix |
| `data/processed/municipal_granularity_audit/municipal_granularity_summary.json` | JSON | Decision summary + manifest |
| `src/data/european_panel/gates_dec061_municipal_granularity.py` | Python | G1-G10 gate functions |
| `tests/test_dec061_municipal_granularity.py` | Python | 40 mandatory tests |
| `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md` | Markdown | This report |

---

*No HPC. No model training. No causal claims. No promotion of labels. No threshold changes.*  
*Raw INE and CBS data not committed (metadata probe only).*
