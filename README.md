# Dataset graphe-temporel ZE2020

Ce dépôt construit un dataset territorial, temporel et auditable pour étudier la dynamique économique des zones d'emploi françaises (`ZE2020`).

L'objectif immédiat n'est pas de présenter une architecture finale, mais de construire un socle de données robuste pour entraîner et évaluer ensuite des modèles graphe-temporels, notamment des `STGNN`.

## Question du projet

La question centrale est :

```text
Peut-on prédire la dynamique future de création d'établissements dans les zones d'emploi françaises à partir de leur historique local, de signaux territoriaux et de relations entre zones ?
```

Le projet est donc structuré autour de trois éléments :

- une cible économique officielle ;
- un panel annuel par zone d'emploi ;
- des graphes représentant les relations territoriales.

## Dataset principal

La cible principale est issue de `SIDE`, la source officielle Insee des créations d'établissements.

Dans le projet, elle est agrégée au niveau `ZE2020` :

```text
Y(i, t+1) = créations d'établissements SIDE dans la zone d'emploi i à l'année t+1
```

Les variables explicatives utilisées pour prédire `t+1` doivent être disponibles à l'année `t` ou avant. Cette contrainte préserve l'ordre temporel et limite le risque de fuite d'information.

## Pourquoi ZE2020

La zone d'emploi est l'unité territoriale retenue parce qu'elle représente un bassin économique fonctionnel.

Elle est plus pertinente qu'une commune isolée pour analyser :

- les dynamiques locales d'emploi et d'activité ;
- les effets de taille territoriale ;
- les relations entre zones voisines ;
- les flux domicile-travail.

Dans la phase STGNN, chaque zone d'emploi devient un nœud du graphe.

## Sources et signaux testés

Le dataset combine plusieurs familles de signaux :

- `SIDE` : cible officielle et historique autorégressif ;
- `SITADEL` : construction et surfaces autorisées ou commencées ;
- `SDES Énergie` : consommation énergétique non résidentielle ;
- `REI CFE` : fiscalité locale, conservée comme diagnostic mais non promue à cause des risques de délai de publication et de révision ;
- graphes territoriaux : adjacence géographique et mobilité domicile-travail.

L'hypothèse testée est que les créations futures d'établissements dépendent à la fois de l'inertie locale, de signaux physiques d'activité et des interactions entre zones.

## État méthodologique actuel

Les résultats actuels montrent que la persistance locale est une référence très forte.

Le benchmark opérationnel actuel reste `ridge_lag_only`, avec `persistence` comme référence conservatrice. Les signaux locaux comme `SITADEL` et l'énergie contiennent du signal, mais ce signal n'est pas encore assez stable pour être présenté comme une conclusion définitive.

Les règles résiduelles et d'activation sont conservées comme diagnostics de stress-test, pas comme baseline finale.

## Passage vers STGNN

Le passage vers les `STGNN` est justifié par la forme naturelle des données :

```text
zones x années x variables
```

avec plusieurs matrices de relation entre zones :

```text
A_geo
A_mobility
```

Le premier objectif STGNN sera de vérifier si une architecture graphe-temporelle apprend mieux que les références causales :

- l'inertie temporelle ;
- les effets locaux non linéaires ;
- les interactions entre zones ;
- les régimes de rupture économique.

## Fichiers à lire en premier

- `reports/PROJECT_STATE_INDEX_V0.md`
- `reports/PROJECT_JOURNEY.md`
- `reports/PRESENTATION_DATASET_STGNN_STORYLINE_V0.md`
- `reports/BASELINE_PHASE_CLOSURE_DECISION_V0.md`
- `reports/STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md`
- `metadata/canonical_artifacts_v0.csv`

## Artefacts principaux

- Cible officielle : `data/processed/target_side_establishments_annual_core_v0.csv`
- Panel et variables explicatives : `data/processed/extended_panel_core_v0.csv`
- Graphe géographique : `data/processed/graph_adjacency_core_v0.csv`
- Graphe de mobilité : `data/processed/mobility_adjacency_row_normalized_core_v0.csv`
- Tensor forecast-safe : `data/processed/stgnn_tensor_package_extended_forecast_core_v1.npz`
- Tensor nowcast Q1 : `data/processed/stgnn_tensor_package_extended_nowcast_q1_core_v1.npz`
- Tensor diagnostic : `data/processed/stgnn_tensor_package_extended_diagnostic_core_v1.npz`

## Hygiène du dépôt

Les dossiers et fichiers suivants ne font pas partie du flux scientifique principal :

- `data/raw/` : sources brutes locales ;
- `scan_output/` : sorties de scan régénérables ;
- `.venv/` : environnement Python local ;
- `.codex/`, `AGENTS.md`, `CLAUDE.md` : fichiers locaux d'agents ;
- PDFs posés à la racine : documentation locale non versionnée.

Les rapports historiques ne sont pas supprimés. Ils sont classés dans `reports/archive/` afin de garder la traçabilité sans encombrer la lecture principale.
