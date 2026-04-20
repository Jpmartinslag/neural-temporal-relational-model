# Storyline de Présentation Dataset vers STGNN v0

Date : 2026-04-20

## Titre Proposé

Construction d'un dataset graphe-temporel pour prédire la dynamique économique des zones d'emploi françaises.

## 1. Problématique

L'objectif du projet est de construire une base territoriale, temporelle et auditée permettant d'étudier l'évolution économique locale.

La question centrale est :

> Peut-on utiliser l'historique économique local, la structure territoriale et les relations entre zones pour prédire la dynamique future de création d'établissements ?

Le projet se place donc avant la phase de recommandation : il construit d'abord un socle de données fiable pour alimenter ensuite des modèles graphe-temporels.

## 2. Dataset principal choisi

Le dataset principal retenu est le dataset officiel `SIDE` de l'Insee sur les créations d'établissements.

Dans le projet, la cible opérationnelle est :

```text
Créations officielles d'établissements SIDE agrégées aux zones d'emploi ZE2020
```

## 3. Pourquoi ce dataset

Le choix de `SIDE` est méthodologiquement central pour quatre raisons.

Premièrement, il mesure directement une dynamique économique : la création d'établissements.

Deuxièmement, il est disponible sur une série annuelle suffisamment longue pour construire des baselines temporelles.

Troisièmement, il est disponible à un niveau territorial fin, ce qui permet une agrégation contrôlée vers les zones d'emploi.

Quatrièmement, il s'agit d'une source officielle, ce qui est important pour l'auditabilité du projet.

## 4. Pourquoi les zones d'emploi ZE2020

L'unité territoriale du projet n'est pas la commune isolée, mais la zone d'emploi `ZE2020`.

Ce choix est économique :

- une zone d'emploi représente un bassin local de travail ;
- elle regroupe des communes liées par des relations fonctionnelles ;
- elle est plus stable et plus pertinente pour étudier l'activité économique territoriale ;
- elle permet de réduire le bruit observé à l'échelle communale.

Dans le modèle, chaque zone d'emploi devient un nœud du graphe.

## 5. Où entre le dataset dans le modèle

Le dataset `SIDE` entre principalement comme variable cible.

Formulation :

```text
Y(i, t+1) = nombre de créations d'établissements dans la zone i à l'année t+1
```

Les variables explicatives sont construites à l'année `t` ou avant.

Cette contrainte est importante : elle évite la fuite temporelle.

## 6. Hypothèse de corrélation recherchée

L'hypothèse de départ est que la création future d'établissements dans une zone dépend de plusieurs dimensions.

### Historique local

Une zone qui crée beaucoup d'établissements aujourd'hui tend à garder une dynamique élevée demain.

C'est pourquoi les variables de retard de la cible sont essentielles.

Exemple :

```text
créations SIDE(t), créations SIDE(t-1), tendance récente
```

### Échelle territoriale

La population et la taille économique d'une zone influencent naturellement le volume de créations.

Une grande zone urbaine n'a pas la même dynamique absolue qu'une zone rurale.

### Signaux physiques locaux

Le projet teste aussi des signaux locaux liés à l'activité physique du territoire :

- construction non résidentielle via `SITADEL` ;
- consommation énergétique non résidentielle ;
- fiscalité locale `REI`, mais placée en quarantaine méthodologique.

L'idée est que l'expansion physique, l'énergie consommée et la base économique locale peuvent indiquer une activité économique future.

### Relations entre zones

Une zone n'existe pas seule.

Deux relations territoriales sont représentées :

- proximité géographique ;
- mobilité domicile-travail.

L'hypothèse est qu'une partie de la dynamique économique peut se propager ou se structurer via ces relations.

## 7. Construction du graphe

Le projet construit deux graphes principaux.

### Graphe géographique

Deux zones sont liées si elles sont spatialement voisines.

Ce graphe représente la proximité territoriale.

### Graphe de mobilité

Deux zones sont liées selon les flux domicile-travail.

Ce graphe représente une relation économique fonctionnelle, souvent plus informative qu'une simple frontière géographique.

## 8. Résultats actuels

Les premiers résultats montrent que la prédiction n'est pas triviale.

### Baseline conservatrice

La persistance est très forte :

```text
Y(i, t+1) ≈ Y(i, t)
```

Cela signifie que le passé immédiat explique déjà une grande partie du futur.

### Benchmark opérationnel

Le benchmark actuel est `ridge_lag_only`.

Il utilise principalement l'historique de la cible.

Ce benchmark est simple, causal et difficile à battre.

### Features locales

Les variables locales comme SITADEL et énergie contiennent du signal, mais ce signal est instable.

Résultat important :

- `SITADEL` semble utile dans certains régimes de rupture ;
- l'énergie apporte un signal physique mais pas encore assez robuste ;
- `REI` donne des résultats intéressants, mais il reste en quarantaine à cause du risque de délai de publication et de révisions.

### Règle d'Activation Résiduelle

Une règle expérimentale avec SITADEL a obtenu un bon score moyen, mais elle a échoué aux tests de robustesse.

Conclusion :

```text
La règle est conservée comme diagnostic, pas comme baseline opérationnelle.
```

## 9. Lecture scientifique des résultats

Le résultat principal n'est pas encore "un modèle final".

Le résultat principal est plutôt :

> Nous avons construit un dataset graphe-temporel auditable et identifié un benchmark fort que les futurs modèles devront dépasser.

La difficulté observée est elle-même informative :

- la dynamique territoriale est fortement inertielle ;
- les signaux locaux existent mais sont bruités ;
- les relations spatiales simples ne suffisent pas encore ;
- un modèle plus expressif doit être testé, mais seulement avec un protocole strict.

## 10. Passage vers STGNN

Le passage vers les STGNN est motivé par la structure naturelle des données.

Les données ont trois dimensions :

```text
zones × années × variables
```

Et les zones sont reliées par des graphes :

```text
A_geo
A_mobility
```

Le modèle STGNN pourra donc tester si une architecture graphe-temporelle apprend mieux :

- l'inertie temporelle ;
- les effets locaux ;
- les interactions entre zones ;
- les dynamiques non linéaires.

## 11. Entrée prévue pour le STGNN

Le paquet tensoriel contient :

```text
X : variables explicatives par année et par zone
Y : créations SIDE futures
A_geo : matrice d'adjacence géographique
A_mobility : matrice de mobilité
Mask : indicateur de données observées ou imputées
```

La présence du mask est importante :

```text
0 dans le tenseur standardisé signifie moyenne du train, pas absence réelle.
```

Le modèle doit donc savoir distinguer une valeur observée d'une valeur imputée.

## 12. Protocole Expérimental Prévu

Le passage vers STGNN doit se faire progressivement.

Ordre prévu :

1. modèle temporel sans graphe ;
2. modèle avec graphe géographique ;
3. modèle avec graphe de mobilité ;
4. modèle graphe-temporel simple ;
5. STGNN plus riche seulement si les étapes précédentes le justifient.

Chaque modèle devra être comparé à :

- `persistence` ;
- `ridge_lag_only`.

## 13. Critère de validation

Un futur modèle ne sera considéré utile que s'il montre :

- une amélioration du WMAPE moyen ;
- pas de dégradation catastrophique sur une année ;
- une amélioration cohérente par groupe de volume territorial ;
- aucune fuite temporelle ;
- une interprétation compatible avec les données économiques.

## 14. Message final pour la présentation

Le projet ne prétend pas encore avoir validé une architecture finale.

Il établit d'abord un socle rigoureux :

- une cible officielle ;
- une unité territoriale économique ;
- des graphes territoriaux ;
- des variables explicatives auditables ;
- des baselines fortes ;
- un protocole de validation sans fuite temporelle.

La phase suivante consiste à tester si les STGNN peuvent dépasser ces baselines en capturant des dépendances temporelles et territoriales que les modèles linéaires ne capturent pas encore.
