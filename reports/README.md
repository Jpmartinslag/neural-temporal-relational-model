# Rapports HERALD

Ce dossier contient les rapports méthodologiques, métriques légères et dashboards publiables.

## Documents principaux

- `HERALD_LEAK_AUDIT_FINAL_20260507.md` — audit anti-fuite.
- `HERALD_DATA_AVAILABILITY_CALENDAR.md` — calendrier réel de disponibilité des sources.
- `HERALD_REPOSITORY_AND_DASHBOARD_CLEANUP_PLAN.md` — plan de nettoyage et dashboard.
- `HERALD_PREDICTION_INTERPRETATION_METHODS.md` — usages économiques des prédictions.
- `HERALD_SEMI_V2_VALIDATION_BATTERY.md` — protocole de validation Semi V2.
- `HERALD_V7_RESEARCH_PLAN.md` — pistes de recherche, non modèle principal.

## Règle de présentation

Les sous-dossiers `herald_v3/`, `herald_v6/` et `archive/` sont historiques. Pour un lecteur externe,
ils doivent être lus comme des ablations/configurations internes de HERALD, pas comme des modèles
concurrents.

## Organisation cible

```text
reports/
├── methodology/   # leak audit, calendrier, protocole scientifique
├── metrics/       # JSON/CSV agrégés légers pour dashboard
├── dashboards/    # HTML offline final
└── archive/       # résultats historiques
```

La migration vers cette structure doit se faire sans supprimer les rapports existants.

## Artefacts publics actuels

- Dashboard: `reports/dashboards/herald_france_dashboard_offline.html`
- Forecast: `reports/metrics/herald_forecast_2026_2027_summary.json`
- Forecast national: `reports/metrics/herald_forecast_2026_2027_national.csv`
- Leak stress: `reports/metrics/herald_leak_stress_prediction_invariance.json`
