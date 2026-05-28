# HERALD Phase 3C — Missing Data Download Audit

Generated: 2026-05-26

## Summary

| Signal | Config | Status | Outcome |
|--------|--------|--------|---------|
| DEFM cat-A by ZE2020 | C1/C2 | **UNLOCKED** | Downloaded from data.gouv.fr; 100% coverage 2012–2025 |
| Activité partielle heures consommées | C5/C6 | **BLOCKED** | No pre-2020 open data available |

Phase 3C battery now runs **5 configs** (C0–C4) × 10 seeds = **50 runs**.
C5/C6 remain commented out in `regime_plan_configs.sh`.

---

## C1/C2 — DEFM cat-A by ZE2020 ✓ UNLOCKED

### Source

- **URL**: https://www.data.gouv.fr/api/1/datasets/r/d723d37a-811a-40d9-991c-c7b587e2e4fa
- **Dataset name**: Inscrits à France Travail par zone d'emploi (trimestrielles, brutes)
- **Publisher**: DARES (Direction de l'Animation de la Recherche, des Études et des Statistiques)
- **Portal**: data.gouv.fr (official French open data platform)
- **Download date**: 2026-05-26
- **File saved**: `data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv`
- **File size**: ~11.3 MB, 136 345 rows

### File layout

```
Date;Code région;Région;Code zone d'emploi;Zone d'emploi;Type de données;Catégorie;Sexe;Tranche d'âge;Ancienneté;Nombre de demandeurs d'emploi
1997-T3;28;Normandie;2814;Lisieux;Brutes;ABC;Total;Total;Total;5860
```

- **Frequency**: Quarterly (`YYYY-TQ`)
- **Geography**: Zone d'Emploi 2020 codes (same as our panel's `ZE2020` column)
- **Time range**: 1996-T1 → 2026-T1
- **Categories**: A, B, C, D, E, ABC, ABCDE
- **ZEs**: 335 total (280 overlap with panel — full coverage, 0 missing)

### Feature computed

`defm_recovery_tminus1 = Q4(t-1) / Q2(t-1)` per ZE per target year

- Filters: `Catégorie=A`, `Sexe=Total`, `Tranche d'âge=Total`, `Ancienneté=Total`
- Q2 = demandeurs d'emploi end of Q2 (June) of year t-1
- Q4 = demandeurs d'emploi end of Q4 (December) of year t-1
- Lower ratio → more within-year recovery (Q4 < Q2 = fewer unemployed by year-end)
- **Leakage**: uses only year t-1 quarters → no t-year data. ✓

### Coverage

| Metric | Value |
|--------|-------|
| ZEs covered | 280 / 280 |
| Target years | 2012–2025 (all 14) |
| NaN rows | 0 |
| Coverage | 100% |

### COVID note (target_year 2021)

For target_year 2021, the feature uses Q4(2020)/Q2(2020).
- Q2 2020 (April–June): first national lockdown → massive DEFM spike
- Q4 2020 (October–December): partial recovery despite second wave
- The ratio Q4/Q2 may appear as a "strong recovery" signal, COVID-driven not structural

No manual COVID flag applied per Phase 3C rules.
The permutation test (C1 vs C2) will detect if this creates spurious signal.

### Parser

Implemented in `src/data/build_herald_phase3c_labor_tutor_features.py`, function `build_defm_recovery()`.
Invoked automatically when `--defm-path` points to the downloaded file (default path set).

---

## C5/C6 — Activité partielle heures consommées ✗ BLOCKED

### Sources attempted

#### 1. DARES main portal (primary target)

- **URL**: https://dares.travail-emploi.gouv.fr/donnees/lactivite-partielle
- **Result**: blocked by Cegedim.cloud security CAPTCHA — not accessible programmatically
- **Not accessible**: cannot download without interactive browser session

#### 2. DARES open data API

- **URL**: https://data.dares.travail-emploi.gouv.fr/api/explore/v2.1/catalog/datasets
- **Result**: 33 datasets listed; none related to activité partielle
- The DARES open data platform does not publish activité partielle heures consommées

#### 3. data.gouv.fr COVID dataset

- **URL**: https://www.data.gouv.fr/datasets/donnees-relatives-au-dispositif-dactivite-partielle-mis-en-oeuvre-dans-le-cadre-de-lepidemie-de-covid-19/
- **Coverage**: starts 2020 only (COVID emergency measure tracking)
- **Geography**: regional + departmental level; no ZE-level data
- **Verdict**: insufficient pre-2020 history; cannot construct training features for 2012–2019 folds
- **Risk**: HIGH COVID-flag risk — any signal learned from this data would be entirely COVID-era

### Verdict

**BLOCKED.** C5/C6 configs remain commented out. No parser implemented.

### To unlock in the future

1. Obtain DARES heures d'activité partielle series 2009–2024 with annual or quarterly frequency
2. Possible contact: statistiques@dares.travail-emploi.gouv.fr (DARES data contact)
3. Possible source: DARES Résultats publication (annual tables in PDF, requires manual extraction)
4. If data obtained: confirm file layout, then implement `build_activite_partielle()` in
   `src/data/build_herald_phase3c_labor_tutor_features.py` and re-run with `--ap-path`
5. National aggregate acceptable (C5/C6 were designed as global gate, not ZE-level)

---

## Regeneration command

```bash
python3 src/data/build_herald_phase3c_labor_tutor_features.py
# Uses default DEFM_PATH = data/raw/phase3c_labor_tutor/defm_cat_a_ze_raw/defm_ze2020_trim_brut.csv
```

## Post-download audit result

```
python3 hpc/regime/audit_herald_phase3c_labor_tutor_plan.py
# → ✓ Preflight passed. Ready to smoke test.
# → 5 configs × 10 seeds = 50 runs
# → C1/C2 OK, C3/C4 OK, C5/C6 BLOCKED
```

## Updated Phase 3C config table

| Config | Feature | Type | Status |
|--------|---------|------|--------|
| C0 | L5_trainopt baseline | none | OK |
| C1 | DEFM cat-A ZE recovery Q4/Q2 | ZE-level real | **UNLOCKED** |
| C2 | C1 temporal permutation | ZE-level perm | **UNLOCKED** |
| C3 | URSSAF Δcotisants ZE t-1 | ZE-level real | OK (was already unlocked) |
| C4 | C3 temporal permutation | ZE-level perm | OK (was already unlocked) |
| C5 | Activité partielle heures t-1 | global real | BLOCKED |
| C6 | C5 temporal permutation | global perm | BLOCKED |
