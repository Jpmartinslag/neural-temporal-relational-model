# HERALD Phase 4 — Batteries HPC Internationales

Batteries SLURM pour la généralisation de HERALD à NL/BE/PT.
Scripts France (Phase 2+3) → `hpc/regime/`. Ne pas mélanger.

---

## Candidat de départ

**France Q7:** `Q7_effectifs_lag1` — features: `side_lag_1`, `growth_1y`, `effectifs_lag1` × A10.
Les batteries Phase 4 testent si la même architecture généralise hors France.

---

## Pays et panneaux

| Pays | Zones | Fenêtre modélisation | Tensor | Q7-equiv |
|------|-------|---------------------|--------|----------|
| **Pays-Bas** | 40 COROP (CR01–CR40) | 2016–2024 | `qtensor_jobs` — CBS employee jobs × SBI-A10 | ✅ oui |
| **Belgique** | 42 arrondissements | 2009–2020 | `qtensor_jobs` — ONSS jobs × NACE-A10 | ✅ oui |
| **Portugal** | 25 NUTS3 (PT_111–PT_300) | 2009–2022 | `sector_births_tensor` — births × CAE-A10 | ⚠️ proxy |

Preflight avant tout lancement: `python3 src/data/phase4_preflight.py`

---

## Structure prévue

```text
hpc/phase4/
├── README.md                           ← ce fichier
├── submit_herald_phase4_nl.sh          ← batterie Pays-Bas
├── submit_herald_phase4_be.sh          ← batterie Belgique
├── submit_herald_phase4_pt.sh          ← batterie Portugal (tensor proxy)
├── smoke_test_phase4_nl.sh             ← smoke test NL (1 seed, 1 epoch)
├── smoke_test_phase4_be.sh             ← smoke test BE
├── smoke_test_phase4_pt.sh             ← smoke test PT
├── audit_phase4_results.py             ← aggrégation + comparaison 4 pays
└── phase4_configs.sh                   ← registre central des configs
```

---

## Configs prévus (par pays)

Chaque pays teste les configs suivantes en parallèle (NL/BE) ou comme variante (PT):

| Config | Description | NL | BE | PT |
|--------|-------------|----|----|-----|
| `baseline_side2` | `side_lag_1 + growth_1y`, no tensor | ✅ | ✅ | ✅ |
| `qtensor_jobs_lag1` | + employment tensor lag1 | ✅ | ✅ | — |
| `sector_births_lag1` | + sector_births_tensor lag1 | — | — | ✅ |
| `no_qtensor_control` | features only, no Q7 | ✅ | ✅ | ✅ |

Seeds: 20 par config. Total estimé: ~4 configs × 20 seeds × 3 pays = ~240 runs.

---

## Protocole de lancement

1. Vérifier preflight: `python3 src/data/phase4_preflight.py`
2. Copier les panels vers le cluster (voir section Transfer)
3. Smoke test: `bash hpc/phase4/smoke_test_phase4_nl.sh` (1 seed, 1 epoch)
4. Vérifier artefacts smoke
5. Submit: `STAMP=$(date +%Y%m%d_%H%M%S) bash hpc/phase4/submit_herald_phase4_nl.sh`
6. Repeat pour BE et PT

---

## Transfer des données vers le cluster

```bash
# Panels Phase 4 (NL/BE/PT)
rsync -av \
  data/external/netherlands/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/netherlands/processed/

rsync -av \
  data/external/belgium/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/belgium/processed/

rsync -av \
  data/external/portugal/processed/ \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/data/external/portugal/processed/
```

## Récupération des résultats

```bash
rsync -av \
  meso-direct:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/<OUT_ROOT>/ \
  hpc_results/<OUT_ROOT>/

python3 hpc/phase4/audit_phase4_results.py --root hpc_results/<OUT_ROOT>
```

---

## Règles

- `OUT_ROOT` unique daté par run.
- Ne jamais réutiliser un `OUT_ROOT` existant.
- Label `sector_births_tensor` obligatoire pour PT — ne jamais écrire `qtensor_jobs` ou `Q7` pour PT.
- Smoke test obligatoire avant tout submit.
- Résultats → `reports/metrics/` après agrégation.
