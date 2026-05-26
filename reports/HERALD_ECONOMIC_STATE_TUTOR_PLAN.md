# HERALD Economic State Tutor — Plan de test

## Point de départ

Phase 2R confirme une lecture sobre:

- candidat principal: `L5_trainopt`;
- entrées: `side_lag_1` + `growth_1y`;
- mécanisme confirmé: Ridge + correction résiduelle neurale + calibration train-only;
- limite restante: mouvements rares, surtout choc/rebond et changements rapides de tendance.

Le résultat ne prouve pas une auto-régulation complète. Il montre qu'un frein causal sur le résidu
améliore la robustesse. La prochaine hypothèse doit donc agir sur l'état économique observé, pas sur
une nouvelle grille large de variantes internes.

## Hypothèse

Ajouter un module d'état économique causal et continu:

```text
indicateurs de conjoncture -> état économique compact -> calibration du résidu HERALD
```

Ce module ne doit pas fournir de flags manuelles comme `COVID` ou `rebond`. Il doit produire des
scores continus, calculés avec des données disponibles avant l'année testée.

## Signaux candidats

Priorité méthodologique:

1. climat des affaires INSEE / Banque de France;
2. indicateur de retournement ou composite leading indicator;
3. nowcast ou activité macro courante, si millésime causal vérifiable;
4. divergence macro vs SIDE: activité générale en baisse, créations d'établissements qui résistent
   ou repartent.

Les signaux doivent être peu nombreux. Plus de features directement dans HERALD n'est pas l'objectif.

## Bateria minimale

Comparer contre `L5_trainopt`:

| Label | Test |
|---|---|
| `T0_l5_trainopt` | référence Phase 2R |
| `T1_state_feature` | état économique ajouté comme feature compacte |
| `T2_state_shrink` | état économique module le shrinkage du résidu |
| `T3_state_latent_align` | état économique régularise doucement le latent |
| `T4_state_permute` | falsification temporelle |

## Critères

Ne pas retenir une variante si elle:

- améliore seulement 2021 mais dégrade la moyenne;
- fonctionne aussi bien avec `T4_state_permute`;
- dépend d'une information publiée après le fold testé;
- ressemble à une flag manuelle déguisée.

Critère de lecture:

- moyenne 2021-2025 non inférieure à `L5_trainopt`;
- 2021 et A10 non dégradés au-delà d'une marge définie avant le run;
- shrinkage/confiance varie dans des années économiquement plausibles;
- résultat pairé et bootstrap, pas seulement meilleur seed.

## Claim autorisé si cela fonctionne

> HERALD apprend les relations territoriales locales; un état économique causal fournit un contexte
> de conjoncture pour calibrer la correction résiduelle dans les années rares.

## Claim interdit à ce stade

- HERALD comprend seul tous les régimes économiques;
- le module est un agent autonome;
- un indicateur macro isolé suffit à prévoir les crises;
- 2021 est résolu si le gain vient uniquement d'une sélection post-hoc.
