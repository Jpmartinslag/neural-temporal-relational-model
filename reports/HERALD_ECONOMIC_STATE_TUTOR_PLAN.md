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

## Hypothèse reformulée

Ajouter un module d'état économique causal et continu, mais avec une réaction locale hétérogène:

```text
indicateurs de conjoncture
  -> état économique compact
  -> gate contextualisé par zone
  -> calibration locale du résidu HERALD
```

Ce module ne doit pas fournir de flags manuelles comme `COVID` ou `rebond`. Il doit produire des
scores continus, calculés avec des données disponibles avant l'année testée.

La distinction importante est la suivante:

- **shrinkage global**: un même facteur réduit le résidu pour toutes les zones;
- **réaction hétérogène**: le contexte macro est combiné avec l'état local de chaque ZE, puis le modèle
  décide zone par zone combien de correction neurale garder.

Phase 2R motive cette piste, mais ne la prouve pas encore. Les variantes globales améliorent certains
points et en dégradent d'autres; cela suggère que le problème peut être spatialement asymétrique. La
batterie suivante doit tester cette hypothèse directement.

## Signaux candidats

Priorité méthodologique:

1. climat des affaires INSEE / Banque de France;
2. indicateur de retournement ou composite leading indicator;
3. nowcast ou activité macro courante, si millésime causal vérifiable;
4. divergence macro vs SIDE: activité générale en baisse, créations d'établissements qui résistent
   ou repartent.

Les signaux doivent être peu nombreux. Plus de features directement dans HERALD n'est pas l'objectif.

## Intégration modèle

Point d'insertion proposé:

```text
alpha_local_i = f(h_local_i, h_graph_i, latent_t, tutor_state_t)
residual_i    = alpha_local_i * residual_i
prediction_i  = ridge_i + calibrated_residual_i
```

En code, cela revient à ajouter `tutor_state_t` dans l'entrée du gate local, en l'expansant à toutes
les zones:

```python
tutor_context = tutor_state_t.unsqueeze(0).expand(N, -1)
alpha_input = torch.cat([
    h_local,
    h,
    r_alpha.unsqueeze(0).expand(N, -1),
    graph_disp,
    torch.abs(h_norm - h_local_norm),
    tutor_context,
], dim=-1)
```

La variante doit être nommée explicitement, par exemple `tutor_heterogeneous_gate`, pour ne pas la
confondre avec un simple shrinkage macro global.

## Bateria minimale

Comparer contre `L5_trainopt`:

| Label | Test |
|---|---|
| `T0_l5_trainopt` | référence Phase 2R |
| `T1_state_feature` | état économique ajouté comme feature compacte |
| `T2_state_shrink` | état économique module le shrinkage global du résidu |
| `T3_state_latent_align` | état économique régularise doucement le latent |
| `T4_state_permute` | falsification temporelle |
| `T5_tutor_hetero_gate` | état économique injecté dans le gate local par ZE |
| `T6_tutor_hetero_permute` | même mécanisme que T5, mais état économique permuté |

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
- si `T5` gagne, `T6` doit perdre ou au moins se dégrader clairement.

## Claim autorisé si cela fonctionne

> HERALD apprend les relations territoriales locales; un état économique causal fournit un contexte
> de conjoncture qui aide à moduler localement la correction résiduelle dans les années rares.

## Claim interdit à ce stade

- HERALD comprend seul tous les régimes économiques;
- le module est un agent autonome;
- un indicateur macro isolé suffit à prévoir les crises;
- 2021 est résolu si le gain vient uniquement d'une sélection post-hoc.
- le contexte macro explique toutes les différences entre territoires.

## Mise à jour après Block A

Le premier bloc `phase3_tutor_gate_block_a` n'a pas soutenu l'hypothèse du gate hétérogène avec
`climat_affaires_emploi`: le contrôle permuté (`T6`) a battu le gate réel (`T5`). Cela bloque le
passage à une cross-attention: un mécanisme plus expressif ne serait pas défendable tant que le signal
tuteur ne bat pas sa falsification temporelle.

La suite devient donc `phase3b_tutor_signal_screen`: même architecture simple, mais signaux macro
isolés un par un, chacun avec son contrôle permuté. Objectif: déterminer si le problème vient du
mécanisme ou du choix du signal tuteur.
