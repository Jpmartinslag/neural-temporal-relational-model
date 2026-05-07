# HERALD — datasets principaux à maintenir

Date: 2026-05-07

Ce document liste les sources réellement importantes pour HERALD-France. Les fichiers bruts peuvent
rester sur la machine locale; le dépôt doit conserver la trace, les scripts et les panels dérivés
nécessaires à la reproductibilité.

## Règle générale

- Les datasets bruts lourds restent hors Git.
- Les panels propres, graphes et cibles canoniques peuvent être versionnés si leur taille reste
  raisonnable.
- Chaque source doit avoir une fréquence de mise à jour et une date de disponibilité documentées.
- Pour un forecast, une variable `t-1` n'est autorisée que si elle est publiée avant la date de
  prévision.

## Sources canoniques

| Source | Rôle dans HERALD | Fichiers dérivés actuels | Mise à jour | Action |
|---|---|---|---|---|
| SIDE créations d'établissements | cible principale et lags AR | `data/processed/target_side_establishments_annual_core_through_2025_v1.csv`; `data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv` | annuelle | automatiser téléchargement dès nouvelle publication INSEE |
| SIDE A10 créations | cible/prior sectoriel | `data/processed/side_creations_a10_ze2020_through_2025_v1.csv` | annuelle | mettre à jour avec SIDE créations |
| Graphes ZE2020 géographie | prior spatial fixe et cartographie | `graph_adjacency_core_v0.csv`; `graph_edges_ze2020_core_v0.csv`; `graph_nodes_ze2020_core_v0.csv`; `graph_node_index_core_v0.csv` | rare, à chaque changement de géographie | garder stable pour comparabilité; reconstruire seulement si nomenclature change |
| Graphe mobilité domicile-travail | prior de connexions économiques | `graph_adjacency_mobility_v0.csv` | lent, selon recensement / mobilité INSEE | documenter millésime; reconstruire si nouvelle matrice fiable disponible |
| FLORES établissements / emploi salarié | contexte productif local | `data/processed/flores_panel_ze2020_annual_v1.csv` | annuelle avec retard | vérifier disponibilité avant forecast; utiliser surtout `t_minus_1` |
| URSSAF trimestriel emploi / masse salariale | signal conjoncturel rapide | `data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv`; tensors quarterly | trimestrielle, fin de trimestre + ~80 jours | prioritaire pour extraction régulière; ne pas utiliser Q4 si cutoff ne le permet pas |
| SIDE stocks établissements / unités légales | contexte stock économique | `data/processed/side_stocks_lagged_ze2020_annual_v1.csv` | annuelle mais actuellement jusqu'à 2023 | traiter comme manquant après 2023; ne pas forcer comme signal courant |
| Splits walk-forward | protocole d'évaluation | `metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv` | à chaque extension d'année | conserver et versionner |

## Sources brutes à conserver localement

Ces sources peuvent rester sur le PC local ou être téléchargées à la demande:

- ZIP SIDE créations / établissements 2012-2025;
- ZIP SIDE A10;
- ZIP SIDE stocks;
- ZIP FLORES;
- fichiers URSSAF open data;
- fichiers territoriaux INSEE ZE2020/COG;
- archives de téléchargement et logs.

Elles ne doivent pas être commitées si elles sont lourdes ou facilement récupérables.

## Fréquence d'extraction recommandée

| Source | Fréquence pratique | Usage |
|---|---|---|
| URSSAF trimestriel | mensuelle ou trimestrielle | signaux rapides, forecast opérationnel |
| SIDE créations/A10 | annuelle après publication INSEE | cible, backtest, forecast année suivante |
| FLORES | annuelle après publication | contexte économique `t-1` |
| SIDE stocks | annuelle, si nouveau millésime publié | contexte structurel |
| Géographie ZE/COG | annuelle ou lors de changement de nomenclature | jointures, cartes |
| Mobilité domicile-travail | quand nouveau millésime fiable existe | graphe structurel |

## À exposer via API plus tard

Pour une application, il faudra préparer une couche d'accès qui met à jour:

- les observations SIDE;
- les prévisions HERALD;
- les indicateurs dérivés par zone;
- les géométries simplifiées;
- les connexions top-k du graphe;
- les métadonnées de disponibilité des sources.

La première API ne doit pas servir les bruts INSEE. Elle doit servir des tables propres et auditées.

