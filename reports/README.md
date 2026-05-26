# Rapports HERALD

Ce dossier contient les rapports méthodologiques, métriques légères et dashboards publiables.

## Documents principaux

- `HERALD_LEAK_AUDIT_FINAL_20260507.md` — audit anti-fuite.
- `HERALD_DATA_AVAILABILITY_CALENDAR.md` — calendrier réel de disponibilité des sources.
- `HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` — audit confirmatoire actuel: HERALD no flags calibré,
  contrôles flags, Ridge et références.
- `HERALD_ECONOMIC_STATE_TUTOR_PLAN.md` — prochaine hypothèse: état économique causal pour les
  mouvements rares.
- `HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md` — ancienne décision: noyau SIDE 5 features, macro non retenu.
- `HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md` — décision actuelle: noyau SIDE2 (`side_lag_1`, `growth_1y`).
- `HERALD_PHASE2O_2P_2Q_PLAN.md` / `HERALD_PHASE2O_2P_2Q_AUDIT.md` — batteries exploratoires
  qui ont mené au choix confirmatoire.
- `HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md` — phase exploratoire: dimension latente et limites
  de l'auto-régulation structurelle.
- `HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md` — stabilité, tendances et régulateurs internes.
- `ATLAS_IAT_STATIC_LAYER_AUDIT.md` — couche statique Atlas/IAT ZE2020 pour overlay post-modèle.
- `ATLAS_IAT_TO_HERALD_EXPERIMENT_PLAN.md` — protocole d'intégration Atlas/IAT, sans injection directe non auditée.
- `HERALD_REPOSITORY_AND_DASHBOARD_CLEANUP_PLAN.md` — plan de nettoyage et dashboard.
- `REPOSITORY_CLEANUP_20260519.md` — nettoyage effectif du dépôt avant la prochaine batterie.
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
- Dashboard Phase 2R: `reports/dashboards/herald_france_dashboard.html`
- Résumé Phase 2R: `reports/metrics/herald_phase2r_summary.csv`
- Pairé Phase 2R: `reports/metrics/herald_phase2r_paired_vs_l5_gate.csv`
- Forecast: `reports/metrics/herald_forecast_2026_2027_summary.json`
- Forecast national: `reports/metrics/herald_forecast_2026_2027_national.csv`
- Leak stress: `reports/metrics/herald_leak_stress_prediction_invariance.json`

## Résultat méthodologique actuel

Le candidat principal actuel est `L5_trainopt`: HERALD sans flags manuelles, deux signaux annuels
SIDE (`side_lag_1`, `growth_1y`), graphe interne, correction résiduelle neuronale, puis calibration
du résidu estimée uniquement sur les années de train.

Phase 2R confirme le gain par rapport au même modèle sans calibration (`L5_gate_no_auditor`):
WMAPE moyen 0.020233 contre 0.020608, 17/20 seeds gagnantes, p=0.002818, IC bootstrap 95%
[-0.000575, -0.000170]. La lecture prudente est: la calibration du résidu améliore la robustesse.
Ce n'est pas une preuve que le modèle a découvert seul un régime économique complet.

`HC5_trainopt` reste une variante utile: meilleure moyenne brute (0.020094) et meilleur 2025
(0.011853), mais avec un coût en 2021. Elle doit être présentée comme un compromis, pas comme le
candidat principal.

La couche Atlas/IAT v1 est fermée comme contexte statique ZE2020. Elle sert d'abord à l'overlay
post-modèle et à l'interprétation, pas au training HERALD principal.

## Prochaine phase: état économique

La prochaine hypothèse n'est pas d'ajouter un gros modèle ou plus de features directement. L'idée à
tester est un module d'état économique: un résumé causal, continu et parcimonieux de signaux externes
reconnus (climat des affaires, indicateurs de retournement, nowcast/activité), utilisé pour calibrer
la correction résiduelle et aider les années rares.

Cette phase devra rester falsifiable: version temporellement permutée, séparation stricte train/test,
et comparaison contre `L5_trainopt`. L'objectif est d'aider les mouvements rares sans transformer un
indicateur macro en flag manuelle déguisée.
