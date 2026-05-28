# Dashboards HERALD France

Ce dossier contient les dashboards HTML présentables du modèle HERALD France.

## Dashboard principal

```text
herald_france_dashboard.html
```

Statut:

- dashboard principal de présentation;
- version de travail à actualiser avec la décision Phase 3E;
- Plotly est chargé par CDN dans cette version de travail;
- la carte et le graphe utilisent `geo` natif Plotly, sans tuiles Mapbox externes;
- comparaison principale cible: HERALD no flags `Q7_effectifs_lag1`, HERALD no flags `Q0_real`,
  HERALD flags clean, HERALD flags extended, Ridge AR, ARIMA, LSTM, DCRNN et Dynamic STGNN;
- les résultats globaux, par année, par zone et A10 doivent privilégier la Phase 3E pour HERALD
  no flags lorsque les artefacts complets sont disponibles;
- le diagramme de modèle doit présenter SIDE clean + Ridge + correction résiduelle + régime appris
  + q_tensor `effectifs_salaries_cvs` lag1, sans claim de découverte autonome complète.

Version légère:

```text
herald_france_dashboard_offline.html
```

Cette version contient Plotly embarqué mais n'a pas été régénérée après la Phase 2R. Elle doit être
traitée comme historique jusqu'à reconstruction complète.

## Règle

Le dashboard public doit séparer clairement:

- candidat principal: `HERALD no flags Q7` (`Q7_effectifs_lag1`);
- référence no-flags précédente: `HERALD no flags Q0` (`Q0_real`);
- contrôles: `HERALD flags clean`, `HERALD flags extended`, Ridge et autres baselines.

Les phrases doivent rester prudentes: montrer les résultats confirmatoires, éviter les formulations
qui donnent l'impression que le modèle a découvert seul un régime économique complet.

Lecture Phase 3E:

- `Q7_effectifs_lag1` est le candidat par défaut: pas le meilleur score brut, mais le meilleur
  compromis stabilité/simplicité/interprétation.
- `Q6_lag1` a le meilleur WMAPE moyen, mais garde les deux canaux q_tensor.
- `Q12_effectifs_lag1_a10guard` a le meilleur A10, mais ajoute une complexité peu utile globalement.
- Ne pas affirmer un effet local ZE fort du q_tensor: la falsification spatiale reste seulement
  modérée.
