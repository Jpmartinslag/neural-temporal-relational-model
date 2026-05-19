# HERALD Phase 2H — Audit de minimalité des entrées

Date: 2026-05-18

## Question testée

La Phase 2H a testé une hypothèse simple: avant d'ajouter des signaux macroéconomiques externes,
HERALD devient-il plus robuste quand on réduit les entrées à un noyau SIDE plus parcimonieux?

La batterie compare:

- un noyau SIDE simplifié sans `FLORES`, sans stock SIDE, sans flags de source;
- une variante `minimal_side_only` qui retire aussi le tenseur trimestriel;
- des ajouts macro INSEE et Banque de France;
- les mêmes signaux macro permutés dans le temps comme falsification.

Les flags manuelles de type COVID/rebond sont absentes dans toutes les runs de cette phase.

## Intégrité de la batterie

Runs récupérées localement:

- `phase2h_macro_real`: 100/100 runs;
- `phase2h_macro_permute`: 40/40 runs;
- `phase2h_macro_extra`: 40/40 runs.

Artefacts:

- 180 JSON de métriques;
- 180 CSV de prédictions totales;
- 180 CSV de prédictions sectorielles;
- 180 fichiers metadata;
- 1080 fichiers NPZ internes.

Contrôle CSV vs JSON: 180/180 recalculés, 0 divergence.

## Résultat principal

La meilleure configuration globale est `best_simplified`.

Entrées annuelles:

- `side_lag_1`;
- `side_lag_2`;
- `side_lag_3`;
- `growth_1y`;
- `growth_2y`.

Cette configuration garde le tenseur trimestriel, mais retire les blocs bruités testés:

- pas de `FLORES`;
- pas de stock SIDE;
- pas de flags de source;
- pas de macro externe;
- pas de flags manuelles de régime.

## Tableau de décision

| Configuration | Mean WMAPE | WMAPE 2021 | WMAPE 2025 | A10 WMAPE | Lecture |
|---|---:|---:|---:|---:|---|
| `best_simplified` | 0.025347 | 0.036236 | 0.014990 | 0.161675 | meilleur équilibre global |
| `minimal_side_only` | 0.025532 | 0.034165 | 0.015825 | 0.163050 | proche, meilleur 2021, mais moins bon 2025/A10 |
| `best_climat_affaires` | 0.028161 | 0.053034 | 0.011955 | 0.162403 | améliore 2025, dégrade fortement 2021 |
| `best_bdf_conj_services` | 0.029120 | 0.050575 | 0.011993 | 0.163259 | même profil: 2025 meilleur, moyenne pire |
| `best_insee_bdf_core` | 0.050819 | 0.136004 | 0.011554 | 0.175939 | rejeté: sur-dégrade 2021 |

## Comparaison `best_simplified` vs `minimal_side_only`

`best_simplified` ne domine pas année par année.

| Année | `best_simplified` | `minimal_side_only` | Différence relative de `best_simplified` |
|---|---:|---:|---:|
| 2021 | 0.036236 | 0.034165 | +6.06% |
| 2022 | 0.025891 | 0.025080 | +3.23% |
| 2023 | 0.023962 | 0.024973 | -4.05% |
| 2024 | 0.025655 | 0.027614 | -7.09% |
| 2025 | 0.014990 | 0.015825 | -5.28% |

Lecture: `best_simplified` perd en 2021-2022, gagne en 2023-2025, et reste meilleur sur la moyenne
et sur A10. La victoire est donc un compromis global, pas une domination uniforme.

## Stabilité entre seeds

| Configuration | Mean WMAPE | Std entre seeds |
|---|---:|---:|
| `best_simplified` | 0.025347 | 0.002189 |
| `minimal_side_only` | 0.025532 | 0.003520 |
| `best_climat_affaires` | 0.028161 | 0.002422 |

`best_simplified` est plus stable que `minimal_side_only`, mais il ne gagne pas toutes les seeds:
`minimal_side_only` gagne 6/10 seeds sur le WMAPE moyen. La différence moyenne reste faible
et doit être interprétée comme un choix de robustesse pratique.

## Lecture des régulateurs internes

Pour `best_simplified`:

- `gamma_mob` moyen: 0.909;
- `gamma_geo` moyen: 0.050;
- `alpha_2025` moyen: 0.455.

Interprétation: le signal de mobilité reste très dominant dans le graphe, même quand les entrées
annuelles sont réduites au noyau SIDE. Le modèle n'est donc pas seulement un extrapolateur local:
il garde une correction territoriale structurée par le graphe.

Alpha moyen par année:

| Année | Alpha moyen |
|---|---:|
| 2019 | 0.524 |
| 2020 | 0.457 |
| 2021 | 0.580 |
| 2022 | 0.465 |
| 2023 | 0.432 |
| 2024 | 0.488 |
| 2025 | 0.455 |

Le saut d'alpha en 2021 indique que le modèle change bien son arbitrage local/graphe autour de la
transition post-2020. Cela ne suffit pas encore à prouver qu'il comprend un régime économique au sens
causal; c'est un signal interne à auditer.

## Décision méthodologique

Décision actuelle:

1. conserver `best_simplified` comme candidat HERALD propre pour la France;
2. ne pas intégrer les signaux macro dans le modèle principal pour l'instant;
3. garder les runs macro comme preuve négative utile: le signal externe améliore parfois 2025 mais
   n'apporte pas de robustesse moyenne;
4. concentrer la prochaine étape sur l'audit des 5 features SIDE et des régulateurs internes.

## Artefacts

- Audit combiné: `hpc_results/phase2h_combined_audit/PHASE2H_COMBINED_AUDIT.md`
- Table par run: `hpc_results/phase2h_combined_audit/phase2h_runs_long.csv`
- Résumé par configuration: `hpc_results/phase2h_combined_audit/phase2h_summary_by_label.csv`
