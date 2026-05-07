# Données HERALD

Ce dossier contient les sources et panels nécessaires à HERALD-France.

## Structure

```text
data/
├── raw/        # sources brutes; généralement non versionnées si lourdes
├── interim/    # tables intermédiaires construites depuis les sources
└── processed/  # panels, graphes et cibles prêts pour entraînement
```

## Fichiers canoniques actuels

Dans `data/processed/`:

- `dynamic_stgnn_feature_panel_through_2025_v1.csv`
- `target_side_establishments_annual_core_through_2025_v1.csv`
- `side_creations_a10_ze2020_through_2025_v1.csv`
- `graph_adjacency_core_v0.csv`
- `graph_adjacency_mobility_v0.csv`
- `graph_edge_index_core_v0.csv`
- `graph_node_index_core_v0.csv`
- `graph_nodes_ze2020_core_v0.csv`

Panels stricts et stress tests:

- `data/processed/strict_exante_20260506/`
- `data/processed/leak_stress_20260507/`

## Règle méthodologique

Pour une prévision opérationnelle, une variable `t-1` ne suffit pas: elle doit aussi être publiée avant
la date de prévision déclarée. Le calendrier à utiliser est:

```text
reports/HERALD_DATA_AVAILABILITY_CALENDAR.md
reports/herald_feature_availability_calendar_v1.csv
```

## Inventaire des sources

Les bruts restent sur le PC local ou sont téléchargés à la demande. Le dépôt conserve la documentation
et les panels dérivés.

- Sources principales à maintenir: `metadata/HERALD_DATASETS_MAIN.md`
- Sources exploratoires/non retenues: `metadata/HERALD_DATASETS_EXPLORATORY.md`
- Politique de mise à jour/API: `metadata/HERALD_DATA_UPDATE_POLICY.md`

## À ne pas présenter comme source canonique

- fichiers de prédiction par seed;
- `.npz` internals;
- panels temporaires générés pour une seule batterie;
- anciens panels avant geo2025 sauf archive explicite.
