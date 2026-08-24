# Données HERALD

> **Note (2026-08-24):** this file predates the France ZE2020 multisignal panel and the
> synthetic known-truth benchmark. For the current, audited data inventory, read
> [`../docs/DATA_AND_PROVENANCE.md`](../docs/DATA_AND_PROVENANCE.md) first. The content below is
> kept for the earlier (pre-Q7, Phase 2I) panels it still correctly describes.

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

Panels expérimentaux Phase 2H:

- `data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv`
- `data/processed/dynamic_stgnn_feature_panel_phase2h_macro_permuted_v1.csv`
- `data/processed/phase2h_macro_annual_features_v1.csv`

Ces panels ont servi à tester les signaux macro INSEE/Banque de France. Ils sont documentés et
réutilisables, mais ne remplacent pas le panel canonique: la Phase 2H ne retient pas les macro-features
comme entrées principales du modèle actuel.

Couche Atlas/IAT statique:

- `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v0.csv`
- `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v1.csv`
- `data/interim/atlas_iat/static_feature_use_policy.csv`

La couche v1 couvre 306 zones d'emploi et 25 colonnes, sans valeurs nulles. Elle est fermée comme
contexte statique ZE2020 pour overlay post-modèle. Elle ne remplace pas les entrées actuelles de
training HERALD.

## Entrées retenues après Phase 2I

Le candidat propre actuel utilise un noyau annuel SIDE minimal:

- `side_lag_1`;
- `growth_1y`.

Les features SIDE longues (`side_lag_2`, `side_lag_3`, `growth_2y`) restent dans le panel canonique
pour ablations et audit, mais elles ne sont pas retenues dans le candidat `lag1_growth1y`.

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
