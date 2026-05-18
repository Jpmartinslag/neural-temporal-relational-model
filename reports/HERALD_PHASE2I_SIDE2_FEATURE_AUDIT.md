# HERALD Phase 2I — audit du noyau SIDE2

Date: 2026-05-18  
Racine des résultats: `hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1/`

## Question testée

La Phase 2I teste si HERALD devient plus stable et plus précis avec moins d'entrées annuelles SIDE.
L'hypothèse est simple: les lags longs et les croissances redondantes peuvent ajouter du bruit au lieu
d'aider le modèle à apprendre les tendances territoriales.

La batterie compare 9 politiques de features, 10 seeds chacune, soit 90 runs. Les variantes restent
strictes: pas de flags manuelles de crise/rebond et pas de source flags.

## Résultat principal

Le meilleur candidat est `lag1_growth1y`, c'est-à-dire seulement:

- `side_lag_1`;
- `growth_1y`.

Ce candidat devient le noyau propre actuel de HERALD pour la suite des analyses. Il remplace le noyau
SIDE5 comme candidat principal, tout en gardant SIDE5 comme référence d'ablation.

| Configuration | Mean WMAPE 2021-2025 | WMAPE 2021 | WMAPE 2022 | WMAPE 2023 | WMAPE 2024 | WMAPE 2025 | A10 WMAPE | Std seeds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `side5_full` | 0.024830 | 0.035664 | 0.025320 | 0.023720 | 0.024576 | 0.014871 | 0.161696 | 0.001996 |
| `lag1_growth1y` | 0.021323 | 0.034885 | 0.019440 | 0.017894 | 0.021389 | 0.013004 | 0.156384 | 0.001764 |

## Amélioration vs SIDE5

| Métrique | Gain relatif |
|---|---:|
| Mean WMAPE 2021-2025 | -14.13% |
| WMAPE 2021 | -2.18% |
| WMAPE 2022 | -23.22% |
| WMAPE 2023 | -24.56% |
| WMAPE 2024 | -12.97% |
| WMAPE 2025 | -12.55% |
| A10 WMAPE | -3.29% |
| Std entre seeds | -11.6% |

Le test pairé contre `side5_full` donne 9 victoires sur 10 seeds pour le WMAPE moyen, avec
`p_mean = 0.009766`. Le gain n'est donc pas seulement une moyenne tirée par une seed isolée.

## Lecture des features

- `side_lag_1` est indispensable: il porte le niveau récent de créations.
- `growth_1y` est indispensable: il porte la dynamique courte.
- `side_lag_2` et `growth_2y` sont redondants ou bruités dans cette configuration.
- `side_lag_3` a un signal mixte, mais il n'est pas nécessaire dans le meilleur candidat.
- Les variantes `lags_only` et `growth_only` échouent fortement: HERALD a besoin à la fois du niveau
  récent et de la croissance courte.

## Régimes et régulateurs appris

Pour `lag1_growth1y`, les diagnostics internes indiquent:

- `alpha_2021_mean = 0.524773`;
- `alpha_2025_mean = 0.451963`;
- `gamma_geo_mean = 0.09710`;
- `gamma_mob_mean = 0.92019`;
- `gamma_mob / gamma_geo = 9.476725`;
- `latent_step_2020_2021_mean = 1.624547`;
- `latent_step_2020_2021_std = 0.340312`.

Interprétation: le modèle apprend une transition latente 2020-2021 plus nette avec deux signaux SIDE
qu'avec le noyau SIDE5. Il s'appuie beaucoup plus sur le prior de mobilité que sur le prior
géographique pur. Le résultat reste une lecture prédictive, pas une preuve causale.

## Décision

Décision actuelle: **HERALD SIDE2 (`side_lag_1 + growth_1y`) devient le candidat propre de travail**.

À écrire dans le papier ou le dashboard:

> HERALD n'a pas besoin d'un grand nombre de variables annuelles SIDE pour améliorer ses prévisions. Le
> noyau le plus robuste dans cette batterie est composé du niveau récent (`side_lag_1`) et de la
> croissance courte (`growth_1y`). Les lags supplémentaires et la croissance à deux ans dégradent la
> stabilité ou ajoutent du bruit.

## Artefacts

- Audit strict: `hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1/reports/audit_phase2i_side5/PHASE2I_SIDE5_AUDIT.md`
- Dashboard de synthèse: `reports/figures/herald_phase2i_side5_audit_dashboard.html`
- CSV de synthèse: `hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1/reports/audit_phase2i_side5/phase2i_summary_by_label.csv`
