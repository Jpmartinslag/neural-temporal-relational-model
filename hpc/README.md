# Batteries HPC HERALD

Ce dossier contient les scripts à envoyer sur le cluster.

## Groupes logiques

```text
hpc/
├── audit/              # strict ex-ante, target-shuffle, leak audit
├── forecast/           # forecast prospectif 2026/2027
├── regime/             # régimes appris, feature minimality, falsifications
├── validation/         # validation Semi V2 / batteries principales
├── research/           # recherches V7/showdown non principales
├── archive/legacy_runs # scripts historiques V3-V6 et anciennes comparaisons
└── tools/              # transfert et setup cluster
```

## Scripts principaux

- `hpc/audit/submit_herald_strict_exante.sh` — validation anti-fuite strict ex-ante.
- `hpc/audit/submit_herald_leak_stress.sh` — target-shuffle leak stress.
- `hpc/forecast/submit_herald_forecast_2026_2027.sh` — forecast prospectif France.
- `hpc/regime/submit_herald_phase2h_macro.sh` — Phase 2H macro/falsification, terminée.
- `hpc/regime/submit_herald_phase2i_side5.sh` — Phase 2I SIDE feature ablations, terminée.
- `hpc/validation/submit_herald_semiv2_validation.sh` — batterie de validation Semi V2.

## Phase active

La dernière phase terminée est Phase 2I. Le candidat courant est HERALD SIDE2 `lag1_growth1y`, documenté
dans:

```text
reports/HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md
reports/HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md
hpc/regime/README.md
```

La prochaine phase prévue est l'audit des régulateurs internes et l'overlay Atlas/IAT post-modèle,
sans ajouter de nouvelles features au training principal avant validation.

## Règles

- chaque batterie doit écrire dans un `OUT_ROOT` unique daté;
- aucun script ne doit écraser une batterie précédente;
- les sorties lourdes restent dans `hpc_results/`;
- les métriques publiables doivent ensuite être exportées vers `reports/metrics/`.

Les anciens scripts V3-V6 et comparaisons historiques sont conservés dans `hpc/archive/legacy_runs/`.
