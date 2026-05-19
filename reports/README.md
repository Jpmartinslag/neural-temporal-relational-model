# Rapports HERALD

Ce dossier contient les rapports méthodologiques, métriques légères et dashboards publiables.

## Documents principaux

- `HERALD_LEAK_AUDIT_FINAL_20260507.md` — audit anti-fuite.
- `HERALD_DATA_AVAILABILITY_CALENDAR.md` — calendrier réel de disponibilité des sources.
- `HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md` — ancienne décision: noyau SIDE 5 features, macro non retenu.
- `HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md` — décision actuelle: noyau SIDE2 (`side_lag_1`, `growth_1y`).
- `HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md` — prochaine phase: tester si la dimension latente
  3 est nécessaire ou si elle conditionne trop le modèle.
- `HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md` — prochaine étape: stabilité, tendances et régulateurs internes.
- `ATLAS_IAT_STATIC_LAYER_AUDIT.md` — couche statique Atlas/IAT ZE2020 pour overlay post-modèle.
- `ATLAS_IAT_TO_HERALD_EXPERIMENT_PLAN.md` — protocole d'intégration Atlas/IAT, sans injection directe non auditée.
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
- Dashboard audit Phase 2I: `reports/figures/herald_phase2i_side5_audit_dashboard.html`
- Forecast: `reports/metrics/herald_forecast_2026_2027_summary.json`
- Forecast national: `reports/metrics/herald_forecast_2026_2027_national.csv`
- Leak stress: `reports/metrics/herald_leak_stress_prediction_invariance.json`

## Résultat méthodologique actuel

Le candidat de travail actuel est HERALD SIDE2 `lag1_growth1y`: deux features annuelles SIDE
(`side_lag_1`, `growth_1y`) avec graphe et tenseur trimestriel. Il améliore le noyau SIDE5 sur tous
les folds 2021-2025 et réduit aussi l'erreur A10. Les signaux macro testés en Phase 2H restent
exploratoires: ils améliorent certains folds, mais ne passent pas le critère global de robustesse.

La couche Atlas/IAT v1 est fermée comme contexte statique ZE2020. Elle sert d'abord à l'overlay
post-modèle et à l'interprétation, pas au training HERALD principal.

## Prochaine phase: dimension latente de régime

La discussion méthodologique à documenter pour le papier est la suivante: un vecteur latent de taille
3 n'autorise pas à dire que HERALD a découvert trois vagues ou trois réactions économiques. C'est une
capacité architecturale. La prochaine batterie doit donc tester `latent_dim = 1, 2, 3, 4, 5` et une
version auto-régularisée qui apprend quelles dimensions garder.

La question technique associée est importante: dans `learned_regime_gate_sector_enhanced`, le latent
agit surtout sur l'arbitrage local/graphe (`alpha`). Dans les variantes `learned_regime_both*`, il
peut aussi modifier le graphe dynamique `A_t`. Les deux cas doivent être séparés dans les claims.
