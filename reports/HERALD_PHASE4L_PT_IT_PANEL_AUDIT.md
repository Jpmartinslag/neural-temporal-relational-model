# HERALD Phase 4L — PT vs IT Panel Audit (`enterprise_birth` subpanel)

Date: 2026-06-09
Inputs: `data/processed/european_panel/pt_panel.csv`,
`data/processed/european_panel/it_panel.csv`,
`data/processed/european_panel/enterprise_birth_pt_it_panel.csv`
No model trained, no HPC, no pooled WMAPE.

## 1. Documentary comparison

| Dimension | Portugal (INE) | Italy (ISTAT/ASIA via Eurostat) | Match |
|---|---|---|---|
| Statistical unit | enterprise | enterprise | ✅ |
| Population | **total** (incl. no-employee) | **total** (sizeclas TOTAL) | ✅ |
| Birth concept | demographic, economic, from scratch | demographic, economic, from scratch | ✅ |
| Reactivation | 2-year rule | 2-year rule | ✅ |
| Continuity | Eurostat-OECD | Eurostat-OECD | ✅ |
| Mergers/splits/takeovers | excluded | excluded | ✅ |
| Sectors | A10 from INE CAE (available) | not ingested at NUTS3 (NaN + mask 0) | ⚠️ asymmetric |
| Geometry | NUTS3 (25) | NUTS3 (102, Sardinia dropped) | ✅ both NUTS3 (scale differs) |
| Years | 2008–2024 | 2008–2020 | common 2008–2020 |
| 2021 break | EBS scope change (out of common window) | EBS scope change (out of common window) | ✅ not in-window |

**Classification: EQUIVALENT** on the target concept (unit, population, birth
definition, reactivation, continuity, mergers). Asymmetries are in *auxiliary*
features (PT has sector births; IT does not at NUTS3) and in *scale/geometry*
(PT 25 vs IT 102 NUTS3 units → MAUP remains a separate, non-semantic confound).
Numerical similarity was **not** used to establish equivalence.

## 2. Subpanel facts (audited)

| | PT | IT |
|---|---|---|
| Source | INE (0009702/0014098) | Eurostat `bd_size_r3` (V11920), ISTAT/ASIA upstream |
| Concept | enterprise_birth | enterprise_birth |
| Geometry | NUTS3 | NUTS3 |
| Regions | 25 | 102 |
| Years | 2008–2020 | 2008–2020 |
| Rows | 325 | 1326 |
| Target coverage | 100% | 100% |
| Forecast-safe rows | — | 1224 (excludes 2008 first-lag year) |
| Median target (births/region·yr) | 3533 | 1926 |
| Sector A10 | available | NaN + mask 0 |
| Employment tensor | per panel | NaN + mask 0 |

Integrity (computed): 0 duplicate (country, region, year); `lag1 == target[t-1]`
on 1524/1524 checkable rows; both pass the European validator with 0 errors;
node_idx contiguous per country; suppressions/transition handled by dropping the
13 Sardinian NUTS-transition codes (no imputation).

Common window: **2008–2020 (13 years)**. Subpanel hash (`enterprise_birth_pt_it_panel.csv`):
`f537701f8b33589d256f1551a5c8a20b`; `it_panel.csv`: `3f052aa88db20f12e6a1e727051e7cb3`.

## 3. Final gate

| Gate criterion | PT | IT | Result |
|---|:--:|:--:|:--:|
| Same `enterprise_birth` total concept | ✅ | ✅ | PASS |
| ≥7 common years | 13 | 13 | PASS |
| ≥20 territories per country | 25 | 102 | PASS |
| Complete territorial target | 100% | 100% | PASS |
| Causal t-1 lags reconstructible | ✅ | ✅ | PASS |
| Reproducible source | ✅ INE | ✅ Eurostat/ISTAT | PASS |
| 2021 break handled | window ends 2020 | window ends 2020 | PASS |
| Suppressions explicitly masked / no hidden interpolation | ✅ | ✅ (Sardinia dropped) | PASS |

**GATE: PASS.** The PT+IT `enterprise_birth` subpanel is a valid, concept-controlled
2-country panel.

## 4. Answers

- **Does Italy really equal PT?** Yes — EQUIVALENT on the target concept (total
  demographic enterprise births, enterprise unit, Eurostat-OECD). Auxiliary
  sectors/employment and spatial scale differ (not semantic).
- **Common window?** 2008–2020 (13 years).
- **Valid regions?** PT 25, IT 102 (Sardinia's 13 transition codes excluded).
- **Sector data comparable?** No — PT has A10 sector births, IT has none at NUTS3
  in this source. Sectors are NaN+mask for IT; do not compare sector heads.
- **Is PT+IT ready for benchmark?** Yes for a **concept-controlled** transfer
  comparison (per-country WMAPE only). **No** for a strong generalization claim:
  only 2 clean domains — insufficient statistical base.
- **Which third country is still needed?** A third **clean NUTS3** `enterprise_birth`
  country. Best candidates: Spain (ES) once NUTS3 births are assembled (currently
  NUTS2), or another Eurostat `bd_size_r3` country with full NUTS3 births
  (e.g. FR/AT/CZ at NUTS3 via the same total-births indicator) — chosen on
  concept, not proximity.
- **Should Spain stay blocked here?** Yes for this step — ES is concept-equivalent
  but published at NUTS2; its NUTS3 births are not assembled, so it does not enter
  now.
- **Which European alternative could give a clean third NUTS3 domain?** Eurostat
  `bd_size_r3` (V11920 total births, NUTS3) covers many countries 2008–2020 — a
  third clean domain can likely be drawn from it (e.g. **FR**, **AT**, **CZ**, or
  **ES** if NUTS3 is reconstructed), reusing the exact ingest already built for IT.

## 5. Constraints honoured

No training, no HPC, no architecture change, no graphs, no Spain, no pooled WMAPE,
no proximity-as-compatibility, no employer≈total, no fiscal≈demographic, no
overwrite of existing panels (new files only), suppressions never zero-filled.
