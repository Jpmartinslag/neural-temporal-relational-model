# Protocole expérimental STGNN v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date : 2026-04-20

## Objectif

Ce document définit le premier protocole expérimental pour passer de la phase data mining / cleaning / baselines vers les premiers modèles graphe-temporels.

L'objectif n'est pas encore de défendre un modèle final. L'objectif est de tester progressivement si l'information temporelle, spatiale et graphe-temporelle apporte un gain réel par rapport aux références déjà validées.

## Position scientifique de départ

Le projet dispose maintenant de quatre éléments solides :

- une cible officielle : créations d'établissements `SIDE` agrégées aux zones d'emploi `ZE2020` ;
- un panel annuel causalement aligné ;
- deux graphes territoriaux : adjacence géographique et mobilité domicile-travail ;
- deux références opérationnelles : `ridge_lag_only` et `persistence`.

La conclusion actuelle reste prudente :

```text
Les signaux locaux existent, mais ils ne sont pas encore assez robustes pour remplacer les baselines simples.
```

Le passage vers les `STGNN` est donc justifié comme expérimentation contrôlée, pas comme conclusion.

## Données d'entrée

Le premier protocole doit partir du paquet forecast-safe :

```text
data/processed/stgnn_tensor_package_extended_forecast_core_v1.npz
```

Structure attendue :

- `X` : variables explicatives par année, zone et variable ;
- `Y` : créations `SIDE` futures ;
- `A_geo` : matrice d'adjacence géographique ;
- `A_mobility` : matrice de mobilité domicile-travail ;
- `Mask` : indicateur de valeurs observées ou imputées.

La règle centrale reste :

```text
features(t) -> target(t+1)
```

Aucune information de l'année cible ne doit intervenir dans l'entraînement, la normalisation, la sélection d'hyperparamètres ou le choix du meilleur modèle.

## Baselines à battre

Chaque expérience doit être comparée aux deux références suivantes :

- `persistence` : référence conservatrice ;
- `ridge_lag_only` : benchmark opérationnel principal.

Un modèle STGNN ne peut pas être présenté comme utile s'il ne dépasse pas ces références avec un comportement stable.

## Ordre expérimental micro vers macro

### Étape 0 — Vérification du paquet tensoriel

But :

- vérifier les formes des tenseurs ;
- vérifier les années d'entrée et de cible ;
- vérifier les masques ;
- vérifier que les graphes ont la même taille que le nombre de zones ;
- vérifier que la normalisation reste limitée au train.

Résultat attendu :

```text
aucun entraînement, seulement une validation de cohérence.
```

### Étape 1 — Modèle temporel sans graphe

But :

- tester si un modèle neural très simple apprend mieux que `ridge_lag_only` sans utiliser de graphe.

Architecture minimale :

- entrée : historique et variables locales par zone ;
- pas de matrice d'adjacence ;
- modèle léger, par exemple MLP temporel ou GRU très contrainte.

Raison :

```text
Si un modèle temporel sans graphe ne bat pas les baselines, le gain STGNN sera difficile à attribuer au graphe.
```

### Étape 2 — Graphe géographique statique

But :

- tester si l'adjacence géographique apporte du signal au-delà du modèle temporel.

Architecture minimale :

- même bloc temporel que l'étape 1 ;
- ajout de `A_geo` ;
- une seule couche graphe ou une agrégation très simple.

Critère :

```text
Le gain doit être mesuré contre l'étape 1, pas seulement contre persistence.
```

### Étape 3 — Graphe de mobilité statique

But :

- tester si la mobilité domicile-travail est plus informative que la proximité géographique.

Architecture minimale :

- même protocole que l'étape 2 ;
- remplacement de `A_geo` par `A_mobility`.

Hypothèse :

```text
La mobilité peut mieux représenter les relations économiques fonctionnelles que la simple frontière spatiale.
```

### Étape 4 — Comparaison multi-graphe

But :

- comparer `A_geo`, `A_mobility` et une combinaison simple des deux graphes.

Combinaisons autorisées au départ :

- moyenne pondérée fixe ;
- concaténation de deux sorties graphe ;
- attention multi-graphe seulement si les étapes 2 et 3 montrent déjà un signal.

Règle :

```text
Pas d'attention complexe si les graphes simples ne montrent aucun gain.
```

### Étape 5 — STGNN léger

But :

- tester une architecture réellement graphe-temporelle, mais encore contrainte.

Contraintes :

- peu de paramètres ;
- early stopping causal ;
- pas de tuning global sur toute la fenêtre de test ;
- résultats rapportés année par année ;
- comparaison contre toutes les étapes précédentes.

## Métriques obligatoires

Chaque expérience doit produire :

- WMAPE moyen ;
- WMAPE par année ;
- WMAPE par groupe de volume territorial ;
- réduction d'erreur absolue contre `persistence` ;
- réduction d'erreur absolue contre `ridge_lag_only` ;
- nombre de zones améliorées et dégradées ;
- concentration du gain dans les plus grandes zones ;
- comportement sur 2021, 2022, 2023 et 2024.

## Critères de promotion

Un modèle ne peut être promu que s'il respecte toutes les conditions suivantes :

- WMAPE moyen inférieur à `ridge_lag_only` ;
- aucune dégradation annuelle catastrophique ;
- gain non concentré uniquement dans Paris ou quelques grandes zones ;
- comportement explicable par groupe de volume ;
- aucune utilisation de `REI` tant que son statut de publication/vintage n'est pas résolu ;
- normalisation et sélection uniquement sur le train ;
- protocole reproductible par script.

## Ce qu'il ne faut pas faire

Ne pas commencer par :

- un STGNN profond ;
- une architecture multi-graphe avec attention complexe ;
- des embeddings appris sans baseline intermédiaire ;
- une optimisation massive d'hyperparamètres sur quatre années de test ;
- un modèle utilisant `REI` dans les premières expériences.

Ces choix rendraient le résultat difficile à défendre, même si le score numérique semblait bon.

## Première tâche technique recommandée

Créer un script de vérification et d'expérience minimale :

```text
src/data/evaluate_stgnn_micro_baselines_v0.py
```

Ce script doit d'abord produire seulement :

- chargement du paquet tensoriel forecast-safe ;
- validation des shapes ;
- reconstruction des baselines `persistence` et `ridge_lag_only` dans le même format que le futur STGNN ;
- export d'un rapport court.

Nom de rapport recommandé :

```text
reports/archive/2026_04_22_top_level_cleanup/STGNN_MICRO_BASELINES_V0.md
```

Nom de métriques recommandé :

```text
reports/stgnn_micro_baselines_metrics_v0.json
```

## Tâche à déléguer à Gemini

Demander à Gemini une revue indépendante avant d'implémenter l'architecture :

```text
Audit le protocole STGNN v0 du dépôt actuel. Vérifie si l'ordre expérimental micro -> macro est défendable scientifiquement, si les critères de promotion sont suffisants, et si le paquet forecast-safe contient des variables qui pourraient encore introduire une fuite temporelle. Ne propose pas d'architecture complexe avant d'avoir validé les baselines minimales. Base-toi uniquement sur les artefacts actuels du dépôt : PROJECT_STATE_INDEX_V0.md, BASELINE_PHASE_CLOSURE_DECISION_V0.md, STGNN_TENSOR_PACKAGE_SIDE_TARGET_CORE_V0.md, stgnn_tensor_package_extended_forecast_core_quality_v1.json et STGNN_EXPERIMENT_PROTOCOL_V0.md.
```

## Décision

Le projet peut commencer la phase STGNN, mais seulement sous forme de protocole progressif.

La première victoire scientifique ne sera pas "un STGNN marche".

La première victoire scientifique sera :

```text
Nous avons testé proprement si le graphe apporte une information supplémentaire par rapport aux baselines temporelles fortes.
```
