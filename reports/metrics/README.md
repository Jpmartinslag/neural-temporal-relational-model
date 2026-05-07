# Métriques HERALD publiables

Ce dossier contient les métriques légères utilisées par les rapports et dashboards.

## Fichiers actuels

- `herald_forecast_2026_2027_summary.json` — synthèse forecast 2026/2027.
- `herald_forecast_2026_2027_national.csv` — forecast national agrégé.
- `herald_leak_stress_prediction_invariance.json` — audit target-shuffle.

## Règle

Les fichiers lourds par seed restent dans `hpc_results/`. Après chaque batterie, exporter ici seulement:

- agrégats par modèle;
- agrégats par année;
- métriques de leak audit;
- forecast national et par zone si nécessaire au dashboard;
- indicateurs économiques dérivés.

