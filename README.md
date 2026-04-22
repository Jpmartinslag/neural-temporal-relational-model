# Dataset graphe-temporel ZE2020

Ce dépôt construit un socle territorial, temporel et auditable pour un système de recommandation territoriale multi-agent centré sur les zones d'emploi françaises (`ZE2020`).

La position méthodologique canonique du projet est définie dans [reports/METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md).

Le rôle immédiat du dépôt est de fournir le backbone de données et d'expérimentation d'une architecture `STGNN`. La prévision de créations d'établissements n'est pas le produit final : c'est la tâche supervisée intermédiaire utilisée pour apprendre des représentations territoriales spatio-temporelles qui alimenteront ensuite la recommandation territoriale multi-agent.

## Question du projet

La question centrale n'est pas seulement prédictive. Elle est :

```text
Peut-on apprendre une représentation spatio-temporelle des dynamiques économiques territoriales en ZE2020, suffisamment utile pour servir de backbone à un système de recommandation territoriale multi-agent ?
```

La prévision de créations d'établissements fournit aujourd'hui l'interface supervisée la plus propre pour tester ce backbone.

## Dataset principal

La cible supervisée principale est issue de `SIDE`, la source officielle Insee des créations d'établissements.

Dans le projet, elle est agrégée au niveau `ZE2020` :

```text
Y(i, t+1) = créations d'établissements SIDE dans la zone d'emploi i à l'année t+1
```

Les variables explicatives utilisées pour prédire `t+1` doivent être disponibles à l'année `t` ou avant. Cette contrainte préserve l'ordre temporel, limite la fuite d'information et garde la tâche de backbone causalement défendable.

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
- `REI CFE` : signal exogène retenu dans le benchmark actuel ;
- `SITADEL` : construction et surfaces autorisées ou commencées ;
- `SDES Énergie` : consommation énergétique non résidentielle ;
- graphes territoriaux : adjacence géographique et mobilité domicile-travail.

L'hypothèse de travail est que les créations futures d'établissements dépendent à la fois de l'inertie locale, de signaux d'activité et des interactions entre zones, et qu'une `STGNN` peut mieux intégrer ces dimensions qu'un benchmark tabulaire simple.

## État méthodologique actuel

Le benchmark opérationnel officiel n'est plus la baseline temporelle courte historique. Le benchmark actuel à battre est :

- `side_creations_lag_1`
- `nb_com`
- `rei_cfe_microentrepreneurs_created_n_1_lag_1`

La meilleure baseline validée à ce stade est `Ridge + REI`, avec un `mean WMAPE ~= 6.699`.

Lecture correcte :

- cette baseline est un benchmark de comparaison ;
- elle n'est pas le produit final du projet ;
- les premiers essais graphe simples ayant échoué ne suffisent pas à invalider le choix méthodologique `STGNN`.

## Passage vers STGNN

Le passage vers les `STGNN` reste l'axe central du projet parce que la structure naturelle des données est :

```text
zones x années x variables
```

avec plusieurs matrices de relation entre zones :

```text
A_geo
A_mobility
```

La prochaine étape correcte n'est pas de chercher "encore un meilleur modèle simple". C'est de construire une `STGNN` petite mais méthodologiquement sérieuse comme backbone, puis de vérifier si elle apprend mieux que les baselines tabulaires :

- l'inertie temporelle ;
- les effets locaux non linéaires ;
- les interactions entre zones ;
- les régimes de rupture économique.

## Fichiers à lire en premier

- `reports/METHODOLOGICAL_POSITIONING_V0.md`
- `reports/PROJECT_STATE_INDEX_V0.md`
- `reports/PROJECT_JOURNEY.md`
- `reports/PRESENTATION_DATASET_STGNN_STORYLINE_V0.md`
- `reports/BASELINE_PHASE_CLOSURE_DECISION_V1.md`
- `reports/STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md`
- `metadata/canonical_artifacts_v0.csv`

## Artefacts principaux

- Cible officielle : `data/processed/target_side_establishments_annual_core_v0.csv`
- Panel et variables explicatives : `data/processed/extended_panel_core_v0.csv`
- Graphe géographique : `data/processed/graph_adjacency_core_v0.csv`
- Graphe de mobilité : `data/processed/mobility_adjacency_row_normalized_core_v0.csv`
- Tensor forecast-safe : `data/processed/stgnn_tensor_package_extended_forecast_with_rei_core_v0.npz`
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
