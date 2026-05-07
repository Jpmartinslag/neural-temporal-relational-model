# Batteries HPC HERALD

Ce dossier contient les scripts à envoyer sur le cluster.

## Groupes logiques

```text
hpc/
├── audit/              # strict ex-ante, target-shuffle, leak audit
├── forecast/           # forecast prospectif 2026/2027
├── validation/         # validation Semi V2 / batteries principales
├── research/           # recherches V7/showdown non principales
├── archive/legacy_runs # scripts historiques V3-V6 et anciennes comparaisons
└── tools/              # transfert et setup cluster
```

## Scripts principaux

- `hpc/audit/submit_herald_strict_exante.sh` — validation anti-fuite strict ex-ante.
- `hpc/audit/submit_herald_leak_stress.sh` — target-shuffle leak stress.
- `hpc/forecast/submit_herald_forecast_2026_2027.sh` — forecast prospectif France.
- `hpc/validation/submit_herald_semiv2_validation.sh` — batterie de validation Semi V2.

## Règles

- chaque batterie doit écrire dans un `OUT_ROOT` unique daté;
- aucun script ne doit écraser une batterie précédente;
- les sorties lourdes restent dans `hpc_results/`;
- les métriques publiables doivent ensuite être exportées vers `reports/metrics/`.

Les anciens scripts V3-V6 et comparaisons historiques sont conservés dans `hpc/archive/legacy_runs/`.
