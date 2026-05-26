# Dashboards HERALD France

Ce dossier contient les dashboards HTML présentables du modèle HERALD France.

## Dashboard principal

```text
herald_france_dashboard.html
```

Statut:

- dashboard principal de présentation;
- version Phase 2R confirmatoire;
- Plotly est chargé par CDN dans cette version de travail;
- la carte et le graphe utilisent `geo` natif Plotly, sans tuiles Mapbox externes;
- comparaison principale: HERALD no flags calibré, HERALD no flags meilleur mean, HERALD flags clean,
  HERALD flags extended, Ridge AR, ARIMA, LSTM, DCRNN et Dynamic STGNN;
- les résultats globaux, par année, par zone et A10 proviennent de la Phase 2R lorsque disponible;
- le diagramme de modèle présente Ridge + correction résiduelle + calibration, sans claim de régime
  économique autonome.

Version légère:

```text
herald_france_dashboard_offline.html
```

Cette version contient Plotly embarqué mais n'a pas été régénérée après la Phase 2R. Elle doit être
traitée comme historique jusqu'à reconstruction complète.

## Règle

Le dashboard public doit séparer clairement:

- candidat principal: `HERALD no flags calibré` (`L5_trainopt`);
- compromis: `HERALD no flags meilleur mean` (`HC5_trainopt`);
- contrôles: `HERALD flags clean`, `HERALD flags extended`, Ridge et autres baselines.

Les phrases doivent rester prudentes: montrer les résultats confirmatoires, éviter les formulations
qui donnent l'impression que le modèle a découvert seul un régime économique complet.
