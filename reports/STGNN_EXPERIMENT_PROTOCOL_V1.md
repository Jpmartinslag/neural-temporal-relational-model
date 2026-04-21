# Protocole expérimental STGNN v1

Date : 2026-04-21

## Objectif

Mettre à jour le point d'entrée de la phase suivante après promotion de la nouvelle baseline courte :

- `side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1`

Le but reste identique :

- tester si un modèle plus riche apporte un gain réel et stable ;
- sans réouvrir les décisions déjà closes sur les baselines simples.

## Position scientifique de départ

Le projet dispose maintenant de cinq éléments solides :

- une cible officielle `SIDE` agrégée à `ZE2020` ;
- un panel annuel causalement aligné ;
- deux graphes territoriaux prêts mais non validés comme sources de gain simple ;
- une baseline temporelle simple historique : `ridge_lag_nbcom` ;
- une baseline courte promue : `rei_created_baseline`.

Position actuelle :

```text
Le meilleur gain robuste observé jusqu'ici vient d'un signal exogène REI/CFE,
pas d'un usage simple du graphe.
```

## Baselines à battre

Chaque nouvelle expérience doit être comparée au minimum à :

- `persistence`
- `ridge_lag_nbcom`
- `rei_created_baseline`

Hiérarchie :

- `persistence` : garde-fou conservateur
- `ridge_lag_nbcom` : référence temporelle courte précédente
- `rei_created_baseline` : référence opérationnelle principale à battre

## Ce qui est déjà fermé

Ne pas rouvrir, sauf nouvelle source ou nouvelle hypothèse forte :

- blends spatiaux linéaires
- covariables spatiales tabulaires simples
- learned geo linear mixing
- gated linear geo mixing
- minimal nonlinear geo mixing
- minimal GCN geographique direct sur features REI
- residual GCN geographique sur baseline REI
- corrections manuelles globales sur hubs
- énergie légère
- RP employment léger
- BPE/FILOSOFI légers déjà testés

## File d'attente valide

Ordre logique actuel :

1. utiliser `rei_created_baseline` comme référence officielle
2. n'ouvrir un nouveau bloc que s'il apporte une hypothèse réellement différente
3. garder `monthly SITADEL H1 lag` comme backup exogène
4. laisser `SIRENE` et autres familles lourdes pour plus tard

## Si la phase suivante est modèle

Tout nouveau modèle doit :

- battre `rei_created_baseline`
- rapporter WMAPE moyen
- rapporter WMAPE par année
- rapporter comportement sur hubs / non-hubs
- rapporter concentration des gains
- rester causal dans la construction des features
- ne pas réutiliser simplement le même schéma géographique déjà rejeté, sauf changement structurel explicite

## Si la phase suivante est encore feature engineering

Toute nouvelle source doit :

- avoir une couverture exploitable sur les 280 zones
- avoir une construction `lag_1` causalement défendable
- apporter une hypothèse différente de `REI created_n_1`
- être comparée directement à `rei_created_baseline`

## Décision

Le point d'entrée de la prochaine phase est désormais :

```text
rei_created_baseline = side_creations_lag_1 + nb_com + rei_cfe_microentrepreneurs_created_n_1_lag_1
```

La suite du projet doit se construire contre cette référence, pas contre `ridge_lag_only`.

## Mise à jour pratique

Après tests lourds initiaux :

- un `GCN` géographique minimal direct a échoué très fortement ;
- un `residual GCN` géographique au-dessus de la baseline REI a aussi échoué ;
- le graphe n'est donc pas justifié, à ce stade, contre la baseline REI.

Conséquence :

- la baseline opérationnelle reste `rei_created_baseline`
- toute réouverture de la ligne graphe doit venir avec une hypothèse structurelle nouvelle, pas une simple variante locale
