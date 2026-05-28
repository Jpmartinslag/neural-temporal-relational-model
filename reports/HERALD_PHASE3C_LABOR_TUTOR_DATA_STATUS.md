# HERALD Phase 3C — Labor Tutor Data Status

Generated: 2026-05-27
Permutation seed: 42

## Signal coverage

| Signal | Status | Coverage | ZEs | Years |
| --- | --- | --- | --- | --- |
| `urssaf_employer_estab_growth_tminus1` | available | 100% | 280 | 2012–2025 |
| `urssaf_employer_estab_growth_perm_tminus1` | available | 100% | 280 | 2012–2025 |
| `urssaf_employer_estab_growth_lag2_tminus1` | available | 100% | 280 | 2012–2025 |
| `urssaf_employer_estab_growth_spatial_perm_tminus1` | available | 100% | 280 | 2012–2025 |
| `urssaf_employer_estab_growth_neg_tminus1` | available | 100% | 280 | 2012–2025 |
| `urssaf_employer_estab_growth_pos_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_recovery_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_recovery_perm_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_recovery_lag2_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_recovery_spatial_perm_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_recovery_signed_tminus1` | available | 100% | 280 | 2012–2025 |
| `defm_yoy_tminus1` | available | 100% | 280 | 2012–2025 |
| `activite_partielle_tminus1` | blocked | 0% | 0 | — |
| `activite_partielle_perm_tminus1` | blocked | 0% | 0 | — |

## DEFM data source

- File: `data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv`
- Source: data.gouv.fr — DARES, Inscrits à France Travail par ZE (trimestrielles, brutes)
- URL: https://www.data.gouv.fr/api/1/datasets/r/d723d37a-811a-40d9-991c-c7b587e2e4fa
- Downloaded: 2026-05-26
- Coverage: 1996-T1 – 2026-T1, 335 ZEs (ZE2020 codes)
- Feature: Q4(t-1) / Q2(t-1) per ZE — intra-year recovery ratio (lower = more recovery)
- Leakage: uses only quarters of year t-1 for target_year t. ✓
- COVID note: target_year 2021 uses Q4(2020)/Q2(2020); Q2-2020 was lockdown spike.
  No COVID flag applied (Phase 3C rules). Permutation test will detect spurious signal.

## Blocked signals (no pre-2020 open data available)

### Activité partielle heures consommées

- Source attempted: https://dares.travail-emploi.gouv.fr/donnees/lactivite-partielle
  → Behind Cegedim CAPTCHA, not accessible programmatically.
- data.gouv.fr COVID dataset: only from 2020, regional/departmental level only.
  Insufficient pre-2020 history for training folds 2012–2020. HIGH COVID-flag risk.
- DARES open data API (data.dares.travail-emploi.gouv.fr): no activité partielle dataset.
- Status: BLOCKED. Not included in the 180-run Phase 3C plan.
- To unlock: obtain DARES activité partielle series with ZE or national level 2009–2024
  from a direct contact with DARES or future open data release.

## Leakage audit

- `urssaf_employer_estab_growth_tminus1`: (etabs(t-1) − etabs(t-2)) / etabs(t-2)
  Uses years t-1 and t-2 only for predicting year t. ✓
- `defm_recovery_tminus1`: Q4(t-1) / Q2(t-1) per ZE
  Uses only quarters of year t-1 for predicting year t. ✓
- Permutation: years shuffled with fixed seed, same shuffle for all signals, cross-ZE structure preserved. ✓
- Normalisation (z-score) computed from training fold only in make_sequences_v7. ✓
