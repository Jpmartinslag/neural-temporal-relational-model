# Dashboards HERALD France

Ce dossier contient les dashboards HTML présentables du modèle HERALD France.

## Dashboard principal

```text
herald_france_dashboard_offline.html
```

Statut:

- dashboard principal de présentation;
- Plotly est embarqué dans le HTML offline;
- la carte et le graphe utilisent `geo` natif Plotly, sans tuiles Mapbox externes;
- comparaison principale: HERALD vs Ridge AR, ARIMA, LSTM, DCRNN, Dynamic STGNN et naive lag-1;
- les contrôles internes ne sont pas présentés comme modèles concurrents;
- les contrôles internes apparaissent uniquement dans le bloc de validation méthodologique.

Version légère:

```text
herald_france_dashboard.html
```

Cette version charge Plotly via CDN et sert surtout au développement local.

## Règle

Le dashboard public doit parler de **HERALD** comme modèle unique. Les anciennes variantes
de laboratoire ne doivent pas apparaître comme des modèles concurrents. Les contrôles internes
servent seulement à documenter la robustesse méthodologique.
