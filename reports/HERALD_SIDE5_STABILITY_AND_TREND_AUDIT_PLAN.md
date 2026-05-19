# HERALD — Plan d'audit des 5 features SIDE

Date: 2026-05-18

## Objectif

La Phase 2H montre que le meilleur candidat actuel utilise seulement cinq entrées annuelles SIDE:

- `side_lag_1`;
- `side_lag_2`;
- `side_lag_3`;
- `growth_1y`;
- `growth_2y`.

La prochaine étape doit répondre à deux questions:

1. quelles features sont réellement nécessaires à la stabilité?
2. HERALD apprend-il des tendances interprétables, ou seulement une extrapolation opportuniste?

## Hypothèse de travail

Le modèle pourrait fonctionner parce qu'il combine trois signaux simples:

- niveau récent: `side_lag_1`;
- inertie longue: `side_lag_2`, `side_lag_3`;
- tendance: `growth_1y`, `growth_2y`.

Le graphe et le gate ne doivent pas être présentés comme "intelligents" tant qu'on n'a pas vérifié
comment ils réagissent à ces signaux.

## Audit 1 — Contribution de chaque feature

Batterie minimale recommandée:

| Label | Features retirées | Question |
|---|---|---|
| `side5_full` | aucune | référence `best_simplified` |
| `drop_lag1` | `side_lag_1` | le modèle dépend-il trop du dernier niveau? |
| `drop_lag2` | `side_lag_2` | inertie moyenne utile? |
| `drop_lag3` | `side_lag_3` | mémoire longue utile? |
| `drop_growth1y` | `growth_1y` | tendance courte utile? |
| `drop_growth2y` | `growth_2y` | tendance lissée utile? |
| `lags_only` | `growth_1y`, `growth_2y` | niveaux seuls suffisants? |
| `growth_only` | `side_lag_1`, `side_lag_2`, `side_lag_3` | tendances seules suffisantes? |
| `lag1_growth1y` | `side_lag_2`, `side_lag_3`, `growth_2y` | noyau ultra-minimal viable? |

Critères:

- WMAPE moyen 2021-2025;
- WMAPE par fold;
- A10 WMAPE;
- std entre seeds;
- wins pareados vs `side5_full`.

## Audit 2 — Tendances apprises

Pour chaque seed et fold, calculer:

- corrélation `growth_1y` vs résidu neural;
- corrélation `growth_2y` vs résidu neural;
- corrélation `side_lag_1` vs erreur absolue;
- sensibilité du gate alpha aux tendances;
- sensibilité du graphe dynamique aux tendances.

Sorties attendues:

- table par année;
- table par quintile de taille de zone;
- table par secteur A10;
- top zones où la correction neural contredit la tendance simple.

Interprétation prudente:

- si la correction neural est cohérente avec `growth_1y` et `growth_2y`, HERALD suit la tendance;
- si elle corrige différemment selon le graphe, HERALD ajoute une information territoriale;
- si la correction change fortement selon la seed, ce n'est pas encore une tendance robuste.

## Audit 3 — Régulateurs internes

Variables à suivre:

- `alpha_by_year`: arbitrage local vs graphe;
- `gamma_geo`: poids du prior géographique;
- `gamma_mob`: poids du prior mobilité;
- `latent_step_by_fold`: amplitude des changements de régime interne;
- `adj_delta_by_year`, si disponible: changement du graphe appris.

Questions:

1. alpha augmente-t-il quand la tendance récente devient instable?
2. gamma mobilité reste-t-il dominant dans toutes les seeds?
3. les années 2020-2021 déclenchent-elles un changement latent reproductible?
4. les seeds qui réussissent 2021 ont-elles un profil alpha/latent différent?

## Audit 4 — Stabilité

Comparer les seeds de `best_simplified`.

Repères Phase 2H:

- mean WMAPE: 0.025347;
- std entre seeds: 0.002189;
- WMAPE 2021: 0.036236;
- WMAPE 2025: 0.014990;
- A10 WMAPE: 0.161675.

Seeds extrêmes à inspecter:

- meilleure moyenne: seed 1, WMAPE 0.022173;
- pire moyenne: seed 99, WMAPE 0.029084;
- meilleur 2021: seed 17, WMAPE 2021 0.024899;
- pire 2021: seed 99, WMAPE 2021 0.058341.

Cette dispersion doit être expliquée avant tout claim fort sur "tendance apprise".

## Audit 5 — Falsifications

Tests nécessaires avant conclusion:

- permuter `growth_1y` et `growth_2y` par année;
- garder les lags mais brouiller les tendances;
- garder les tendances mais brouiller `side_lag_1`;
- figer alpha à sa moyenne annuelle;
- figer le graphe dynamique;
- comparer avec Ridge AR sur les mêmes entrées SIDE.

Si HERALD garde sa performance après permutation des tendances, alors il n'utilise probablement pas
les tendances comme on le croit. Si la performance chute fortement, le signal de tendance est réel.

## Décision attendue après audit

Trois issues possibles:

1. `side5_full` reste meilleur et stable: conserver `best_simplified` comme HERALD principal.
2. un noyau plus petit égale `side5_full`: simplifier encore le modèle.
3. une feature stabilise seulement certaines années: utiliser cette information pour expliquer les
   limites, pas pour ajouter une règle manuelle.

Règle: aucune nouvelle flag explicite de crise/rebond. Les améliorations doivent venir de signaux
observables, de régularisation ou de meilleure architecture, pas d'un étiquetage manuel d'événement.
