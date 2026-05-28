# Batteries HPC HERALD

Ce dossier contient les scripts à envoyer sur le cluster.

## Groupes logiques

```text
hpc/
├── audit/              # strict ex-ante, target-shuffle, leak audit
├── forecast/           # forecast prospectif 2026/2027
├── phase4/             # batteries internationales NL/BE/PT (Phase 4)
├── regime/             # régimes appris, feature minimality, falsifications (France Phase 2+3)
├── validation/         # validation Semi V2 / batteries principales
├── research/           # recherches V7/showdown non principales
├── archive/legacy_runs # scripts historiques V3-V6 et anciennes comparaisons
└── tools/              # transfert et setup cluster
```

## Scripts principaux

- `hpc/audit/submit_herald_strict_exante.sh` — validation anti-fuite strict ex-ante.
- `hpc/audit/submit_herald_leak_stress.sh` — target-shuffle leak stress.
- `hpc/forecast/submit_herald_forecast_2026_2027.sh` — forecast prospectif France.
- `hpc/regime/submit_herald_phase3e_qtensor_arch.sh` — Phase 3E sélection architecture Q7, terminée.
- `hpc/phase4/` — batteries Phase 4 internationales NL/BE/PT (à préparer).

## Phase active

**France (Phase 2+3) — terminée.** Candidat courant: `Q7_effectifs_lag1`, sélectionné en Phase 3E.

```text
reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md
reports/HERALD_CURRENT_MODEL_DECISION_20260527.md
hpc/regime/README.md
```

| Métrique France | Valeur |
|----------------|--------|
| Mean WMAPE 2021-2025 | 0.020398 |
| Std WMAPE (seeds) | 0.001498 |
| WMAPE 2025 | 0.011415 |

**Phase 4 — données prêtes, batteries à préparer.**

Panneaux validés (preflight `python3 src/data/phase4_preflight.py`):

| Pays | Zones | Fenêtre | Tensor | Statut |
|------|-------|---------|--------|--------|
| Pays-Bas | 40 COROP | 2016–2024 | `qtensor_jobs` (employment, CBS) | ✅ HPC-ready |
| Belgique | 42 arrondissements | 2009–2020 | `qtensor_jobs` (employment, ONSS) | ✅ HPC-ready |
| Portugal | 25 NUTS3 | 2009–2022 | `sector_births_tensor` (⚠️ proxy, non Q7) | ✅ HPC-ready |

Prochaine étape: préparer les scripts `hpc/phase4/`.

## Règles

- chaque batterie doit écrire dans un `OUT_ROOT` unique daté;
- aucun script ne doit écraser une batterie précédente;
- les sorties lourdes restent dans `hpc_results/`;
- les métriques publiables doivent ensuite être exportées vers `reports/metrics/`.

Les anciens scripts V3-V6 et comparaisons historiques sont conservés dans `hpc/archive/legacy_runs/`.
