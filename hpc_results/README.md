# Résultats HPC HERALD

Ce dossier est une archive de calcul. Il peut contenir beaucoup de fichiers lourds, logs, CSV de
prédiction et `.npz` internes. Il ne doit pas être la structure principale du projet.

## Runs récents importants

- `herald_strict_exante_20260506_night_final/` — audit strict ex-ante, 120 runs.
- `herald_leak_stress_20260507_target_shuffle/` — target-shuffle leak stress.
- `herald_forecast_20260506_forecast_after_strict/` — forecast 2026/2027.
- `herald_semi_v2_final_20260504/` — dashboard Semi V2 stable.
- `herald_semi_total_253_geo2025/` — ancienne batterie complète geo2025.

## Règle

À conserver dans Git seulement si léger et utile:

- README;
- JSON de métriques agrégées;
- dashboard HTML offline final;
- petits fichiers de synthèse.

À éviter dans Git:

- CSV de prédictions par seed;
- `.npz` internals;
- logs `.out` / `.err`;
- archives brutes de transfert.

Les sorties nécessaires au dashboard final doivent être exportées vers `reports/metrics/` et
`reports/dashboards/`.
