# Netherlands — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-27  
**Status:** preliminary — pending download verification

---

## 1. Enterprise Births (TARGET variable)

### Option A — Births at province level (CBS 83631NED)

| Item | Detail |
|------|--------|
| Source | CBS StatLine — Vestigingen van bedrijven; oprichtingen, bedrijfstak, regio |
| Table ID | 83631NED |
| URL | https://www.cbs.nl/nl-nl/cijfers/detail/83631NED |
| Format | CSV via StatLine open API |
| Years | 2007–2025 (2007+ definitive through 2024) |
| Geographic | **Province only (12 provinces)** — NOT COROP |
| Sectors | SBI 2008 (compatible with NACE Rev.2 / A10) |
| Concept | New establishment births (oprichtingen vestigingen) |

**CRITICAL GAP**: births only at province (12), not COROP (40). Cannot disaggregate province births to COROP without assumptions.

### Option B — Stock YoY difference at COROP (CBS 81578NED)

| Item | Detail |
|------|--------|
| Source | CBS StatLine — Vestigingen van bedrijven; bedrijfstak, regio |
| Table ID | 81578NED |
| URL | https://opendata.cbs.nl/statline/#/CBS/nl/dataset/81578NED/table |
| Format | CSV via StatLine open API |
| Years | 2007–2026 |
| Geographic | **40 COROP regions** + province + landsdelen |
| Sectors | SBI 2008 |
| Concept | **Stock** (not births). ΔStock(t, t-1) = gross proxy for net flows. |

ΔStock = births − deaths (net). Not pure births. Acceptable as proxy if deaths % is stable and documented.

### Option C — Municipality stock (CBS 81575NED) → COROP aggregate

| Item | Detail |
|------|--------|
| Table ID | 81575NED |
| Geographic | Municipality (350+) → aggregable to COROP via CBS region table |
| Concept | Stock. ΔStock at municipality → aggregate to COROP proxy. |
| Years | 2007–2026 |

### Recommended strategy

Use **81578NED ΔStock at COROP** as target proxy. Document in preflight point 1: "target = net establishment flow (births − deaths), not pure births." Validate against national births from 83631NED to confirm proxy is acceptable (deaths should be ~15-25% of births, stable over time).

---

## 2. Employment / Q-Tensor (CBS)

### Option A — Employee jobs by work region (CBS 85481NED)

| Item | Detail |
|------|--------|
| Source | CBS StatLine — Werknemersbanen en reisafstand; woon- en werkregio |
| Table ID | 85481NED |
| URL | https://opendata.cbs.nl/#/CBS/nl/dataset/85481NED/table |
| Format | CSV via StatLine API |
| Geographic | COROP-level (40 regions) for work region |
| Concept | Employee jobs (werknemersbanen) by work COROP |
| Sectors | TBD — verify if sector (SBI) breakdown available |

**Action**: verify if 85481NED has SBI sector breakdown at COROP level (may be commute cross-tab without sector detail).

### Option B — Establishment size class × COROP (CBS 81644NED)

| Item | Detail |
|------|--------|
| Table ID | 81644NED |
| URL | https://data.overheid.nl/dataset/192-vestigingen-van-bedrijven--grootte--rechtsvorm--bedrijfstak--regio |
| Geographic | COROP regions |
| Sectors | SBI 2008 |
| Concept | Establishments by **size class** (number of employees) × COROP × sector. Indirect employment proxy. |

Can compute: employment = sum(size_class_midpoint × count) by COROP × sector. Rough but available.

### Option C — Regional Employment Survey (CBS Regionale Werkgelegenheid)

| Item | Detail |
|------|--------|
| Source | CBS Regionale Werkgelegenheid survey |
| Geographic | Municipality (aggregable to COROP) |
| Sectors | SBI 2008 |
| Concept | Direct employed persons count per establishment + municipality |
| Access | CBS website — download format TBD |

### Recommended strategy

Try **85481NED** first (direct employee jobs by COROP). If no sector breakdown → use **81644NED** (size class proxy). Document choice in preflight.

---

## 3. Geographic Units & Adjacency

| Item | Detail |
|------|--------|
| Target unit | 40 COROP regions |
| Geometries | CBS COROP boundaries (open data) |
| URL | https://www.cbs.nl/werkgelegenheid |
| Format | GeoJSON / Shapefile |
| Adjacency | Queen contiguity via geopandas.sjoin |

CBS publishes annual regional boundary files: "Gebieden in Nederland 20XX" (e.g., 86247NED for 2026).

---

## 4. Preflight Risk Assessment

| Point | Status | Notes |
|-------|--------|-------|
| 1. TARGET | ⚠ Document | ΔStock proxy not pure births. Explain and validate. |
| 2. TERRITORY | ✓ | 40 COROP = functional labor markets, comparable to ZE. |
| 3. SECTOR | ✓ | SBI 2008 → NACE Rev.2 → A10 mapping direct (EU-harmonized). |
| 4. COVERAGE | ✓ | 2007+ available, covers 2008 crisis. |
| 5. Q_TENSOR | ⚠ Verify | Sector breakdown at COROP level needs confirmation (85481NED or 81644NED). |
| 6. TIGHTNESS | ✓ | Stock measured Jan 1 each year → lag1 = prior Jan 1 = published before target year. |

**Decision risk:** Low, but target variable is proxy (ΔStock). Must be explicitly declared in preflight point 1.
