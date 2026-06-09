# HERALD Phase 4J — Canonical Multi-Task Registry Audit

Date: 2026-06-09
Action: rebuild and freeze of the canonical European panel after the Phase 4J
target-semantics correction. **No model trained, no HPC launched.**

```bash
python3 -m src.data.european_panel.build_european_panel \
  --country all --out-dir data/processed/european_panel
```

Build status: **ALL PANELS BUILT SUCCESSFULLY** (PASS with EU-signal coverage
warnings only: `eu_sts_turnover_lag1` and `eu_eei_lag1` remain 0%, unchanged and
expected).

## 1. Registry (per country)

| Country | `flag_target_concept` | `meta_source_label` | Geometry (`meta_region_system`) | Regions | Years | Rows |
|---|---|---|---|---:|---|---:|
| FR | `establishment_creation` | SIDE | ZE2020 | 280 | 2012–2024 | 3640 |
| NL | `local_unit_opening` | CBS | COROP | 40 | 2015–2025 | 440 |
| BE | `vat_first_registration` | StatBel | arrondissement | 42 | 2007–2024 | 756 |
| PT | `enterprise_birth` | INE | NUTS3 | 25 | 2008–2024 | 425 |
| **Combined** | — | — | — | **387** | — | **5261** |

The concept and source labels now match the Phase 4J semantic gate. The metadata
correction propagated through the rebuild; the underlying numeric data is
unchanged (diff is metadata-only: only `flag_target_concept` for NL/BE and
`meta_source_label` for PT changed; France was already correct).

## 2. Validation results

| Check | Result |
|---|---|
| Concepts correct (FR/NL/BE/PT) | PASS — establishment_creation / local_unit_opening / vat_first_registration / enterprise_birth |
| `meta_source_label` correct | PASS — SIDE / CBS / StatBel / INE |
| Geometry correct | PASS — ZE2020 / COROP / arrondissement / NUTS3 |
| Duplicate (country, region, year) | 0 |
| Target NaN where `mask_target=1` | 0 |
| Lag causality `lag1_births == target_births[t-1]` | PASS — 0 mismatches / 4874 checkable rows |
| Trainer uses `flag_target_concept` as a feature | NO — confirmed passthrough metadata only |
| Combined rows | 5261 (= 3640 + 440 + 756 + 425) |

## 3. Panel hashes (frozen, post-rebuild)

| File | rows × cols | md5 |
|---|---|---|
| `france_panel.csv` | 3640 × 43 | `79f8f828e5c2c3a2fe5704e01d9bbaa4` |
| `nl_panel.csv` | 440 × 43 | `ff34d1fb2f1cc582ed779112fa227f9a` |
| `be_panel.csv` | 756 × 43 | `777c198f85228848606b7c93740a24ed` |
| `pt_panel.csv` | 425 × 43 | `061f944445d6067c5b19c7883ef4eb25` |
| `european_panel_all.csv` | 5261 × 43 | `c2d3f16470de4ee682e0044cbf6321fb` |

These panels are already tracked in the project (small, traditionally versioned);
the rebuild commits the metadata-only correction.

## 4. Note on the 4J prediction panel

The Phase 4J experiments use `data/processed/phase4g/joint/panel_ze2020.csv`,
which does **not** carry `flag_target_concept`. Concept labelling for 4J results
is applied at report time via `audit_phase4j_target_aware.py`. The canonical
registry here is the authoritative source of target concepts; the phase4g joint
panel should inherit them on its next rebuild.

## 5. Coverage warnings (unchanged, documented)

- `eu_sts_turnover_lag1`, `eu_eei_lag1`: 0% (blocked sources, per
  `HERALD_PHASE4E_MISSING_DATA_SEARCH.md`).
- BE sector coverage 0% (StatBel has no arrondissement × sector births).
- These are pre-existing and not caused by the rebuild.
