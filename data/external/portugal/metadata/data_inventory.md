# Portugal — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-27  
**Status:** preliminary — pending download/access verification for GEP data

---

## 1. Enterprise Births (TARGET variable)

| Item | Detail |
|------|--------|
| Source | INE — Estatísticas das empresas / demografia de empresas |
| URL | https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_base_dados |
| Portal | https://dados.gov.pt/en/datasets/numero-de-empresas/ |
| Format | CSV (Open Data, CC BY 4.0) |
| Years | **Historical series from ~1990** for some indicators; 2008+ confirmed usable |
| Geographic | **Municipal level (308 municípios)** + NUTS2/NUTS3 |
| Sectors | CAE Rev. 3 (Portuguese NACE equivalent, fully compatible with NACE Rev.2 → A10) |
| Concept | Empresas constituídas (company formations) — enterprise births |

### Important note on territory

INE also defines "zonas de emprego" (employment zones) — check availability:
- If INE zonas de emprego (23 zones) available: preferred (closer to France ZE concept)
- If only municípios (308): use municípios with note; aggregation to zonas de emprego if mapping available
- Preflight point 2 must verify and choose explicitly

### Dados.gov.pt datasets

- `Número de empresas` (N.º) by NUTS 2013 + CAE Rev. 3 + legal form — CC BY 4.0
- `Nascimentos de empresas em sectores de alta e média-alta tecnologia` (CAE Rev. 3) — available
- INE indicators extend to municipal level (Divisão CAE Rev. 3) per search results

---

## 2. Employment / Q-Tensor (GEP — Quadros de Pessoal)

| Item | Detail |
|------|--------|
| Source | GEP — Gabinete de Estratégia e Planeamento (MTSSS) |
| Full name | Quadros de Pessoal (Personnel Tables) |
| URL | https://www.gep.mtsss.gov.pt/quadros-de-pessoal |
| Years | **1985–2022** (recent years TBD — see access note) |
| Geographic | Establishment level → aggregable to **município × CAE sector** |
| Sectors | CAE Rev. 3 |
| Concept | Annual declaration by all firms with employees: headcount + wages per establishment |
| Access | Download available; **recent years (2022+) may require formal request** |

### Access risk

GEP historically released Quadros de Pessoal as public downloads. However, recent years (2022, 2023) may be under embargo or require a formal data request to the ministry. **Verify before committing calendar.**

If recent data unavailable:
- Use through 2021 only → walk-forward window may be shortened
- Document in preflight point 5

### Wage data

Quadros de Pessoal includes "remuneração" (wage mass) at establishment level → direct equivalent of URSSAF masse salariale.

---

## 3. Geographic Units & Adjacency

### Option A — 308 municípios

| Item | Detail |
|------|--------|
| Source | INE — CAOP (Carta Administrativa Oficial de Portugal) |
| URL | https://www.ine.pt/ (CAOP download) |
| Format | Shapefile / GeoJSON |
| N | 308 municípios (continental) |

308 units is significantly more than ZE France (306) and COROP NL (40) or arrond. BE (43). Spatial graph will be much larger. Computation cost higher.

### Option B — 23 zonas de emprego INE

| Item | Detail |
|------|--------|
| Source | INE classification of employment zones |
| N | ~23 zones (continental Portugal) |
| Status | **Verify existence and boundaries** — may be NUTS3-equivalent |

23 zones = much smaller spatial graph, more comparable to BE (43) and NL (40). Preferred if data available at this granularity.

**Preflight point 2 is critical for Portugal**: must choose 308 vs 23 before any pipeline build.

---

## 4. Preflight Risk Assessment

| Point | Status | Notes |
|-------|--------|-------|
| 1. TARGET | ⚠ Document | Empresa (legal entity) vs estabelecimento (physical). Differs from France. |
| 2. TERRITORY | ⚠ CRITICAL | Choose: 308 municípios OR 23 zonas de emprego. Decision before pipeline. |
| 3. SECTOR | ✓ | CAE Rev. 3 → NACE Rev.2 → A10. Direct mapping. |
| 4. COVERAGE | ✓ | INE series from 1990+, 2008 covered. |
| 5. Q_TENSOR | ⚠ Access TBD | Quadros de Pessoal available but recent years (2022+) may need formal request. |
| 6. TIGHTNESS | ✓ | Annual declarations published ~18 months lag → use T-1 data for predicting T. |

**Decision risk:** Moderate. Territory choice (point 2) and GEP access (point 5) are the two open questions.
