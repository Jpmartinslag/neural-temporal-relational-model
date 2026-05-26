# HERALD — Prévision économique territoriale

HERALD (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*) est un modèle
hybride de prévision territoriale pour la France. Il estime les créations d'établissements par zone
d'emploi, puis transforme ces prévisions en cartes de dynamisme, ralentissement, incertitude et
structure sectorielle.

Le dépôt est maintenant organisé autour d'un seul nom public: **HERALD**. Les anciens noms V3, V6,
V7 et Semi désignent des configurations de laboratoire et ne structurent plus la présentation finale.

## État scientifique actuel

Le candidat de travail pour la France est maintenant **HERALD no flags calibré (`L5_trainopt`)**,
issu de la Phase 2R confirmatoire. Il garde le noyau SIDE2, sans flags manuelles, et ajoute une
calibration causale du résidu neural:

- `side_lag_1`;
- `growth_1y`.

Le modèle part d'une base Ridge, apprend une correction résiduelle neuronale, puis estime sur les
années de train combien de cette correction doit être utilisée. Cette calibration n'utilise pas
l'année testée.

Conclusion actuelle:

- pas de fuite directe détectée dans les batteries strict ex-ante et target-shuffle;
- les modèles HERALD battent fortement Ridge AR, ARIMA, LSTM et les STGNN de comparaison sur le panel
  France geo2025;
- la Phase 2H montre que les ajouts macro INSEE/Banque de France testés ne sont pas retenus: ils
  améliorent parfois 2025 mais dégradent 2021 et la moyenne 2021-2025;
- la Phase 2I montre que `side_lag_1 + growth_1y` bat le noyau SIDE5 sur tous les folds 2021-2025;
- la Phase 2J montre que la comparaison propre doit séparer trois lignes: `HERALD flags étendu`
  (contrôle historique plus chargé), `HERALD flags clean` (mêmes entrées SIDE2 + flags) et
  `HERALD no flags` (mêmes entrées SIDE2, régime appris);
- la Phase 2R confirme `L5_trainopt`: WMAPE moyen 2021-2025 = 0.020233, WMAPE 2021 = 0.035020,
  WMAPE 2025 = 0.012525, A10 WMAPE = 0.158238;
- contre `L5_gate_no_auditor`, le gain moyen est -0.000375 avec 17/20 seeds gagnantes et p=0.002818;
- le forecast 2026/2027 est une prévision prospective conditionnelle aux données disponibles le
  2026-05-07, pas une prévision ex-ante au 2026-01-01;
- le graphe est utile pour l'interprétation territoriale: mobilité, connexions économiques et
  reconfiguration pendant les chocs.

## Décision méthodologique en cours: régimes appris

HERALD ne doit pas dépendre durablement de flags explicites comme `is_covid_year` ou
`is_post_covid_rebound`. Ces variables sont utiles comme contrôle de laboratoire, mais elles injectent
un jugement du chercheur dans les entrées du modèle.

La phase actuelle teste donc une transition conservatrice vers des régimes appris:

- contrôle: HERALD avec flags manuelles, pour mesurer le niveau à battre;
- `no_regime`: aucune information de régime;
- `latent_gate`: état latent interne qui module l'arbitrage local/graphe;
- `latent_gate + cp_aux`: même état latent, avec signal auxiliaire de rupture calculé uniquement avec
  les données disponibles avant l'année évaluée.

Le critère est volontairement strict: une variante sans flags manuelles ne devient candidate principale
que si elle égale ou améliore le WMAPE moyen 2021-2025, ne dégrade pas 2025, ne dégrade pas A10, et reste
stable entre seeds. Les architectures plus lourdes de type mixture-of-experts restent en seconde étape.

Les Phases 2A-2I ont montré que les variantes sans flags explicites peuvent être compétitives, mais que
les ajouts de régime, macro ou features longues ne doivent pas être acceptés sans falsification. La
décision actuelle est donc conservatrice: travailler avec `lag1_growth1y`, puis auditer finement la
stabilité entre seeds et les régulateurs internes (`alpha`, `gamma_geo`, `gamma_mob`, latents) avant de
relancer une architecture plus complexe.

Les Phases 2K-2N ont ensuite clarifié la question d'autonomie interne:

- la taille du vecteur latent est un hyperparamètre, pas une preuve de trois régimes économiques;
- les masques globaux hard-concrete/concrete/group-lasso n'ont pas produit de sélection fiable de
  dimension;
- l'auditeur interne conditionné par année est techniquement viable, mais il n'est pas encore un
  candidat global robuste.

Les Phases 2O-2Q ont déplacé la lecture du projet: le résultat robuste n'est pas une auto-régulation
forte de la dimension latente. Le résultat robuste est la **correction résiduelle calibrée**. Phase 2R
a ensuite figé les candidats et confirmé ce point.

La prochaine hypothèse de recherche est plus ciblée: un **module d'état économique** causal et continu,
fondé sur des indicateurs reconnus de conjoncture/retournement, pour aider les mouvements rares
comme choc, rebond, accélération et décélération. Cette hypothèse doit être testée contre
`L5_trainopt`, avec permutation temporelle et séparation stricte train/test.

## Structure

```text
dataset/
├── data/          # données brutes, intermédiaires et panels/graphes canoniques
├── hpc/           # batteries SLURM, audits et forecasts à lancer sur cluster
├── hpc_results/   # sorties lourdes de calcul; non source principale du projet
├── reports/       # rapports méthodologiques, métriques légères et dashboards finaux
├── src/           # code modèle, baselines, analyses et génération de dashboard
└── docs/          # documentation externe ou notes longues
```

Voir les READMEs locaux dans chaque dossier pour savoir quoi versionner et quoi régénérer.

## Entrées du modèle

Le candidat principal actuel utilise, par zone d'emploi:

- deux features annuelles SIDE: `side_lag_1`, `growth_1y`;
- tenseur trimestriel et graphe territorial;
- secteurs A10 comme objectif sectoriel auxiliaire.

Les blocs annuels ou exploratoires suivants existent dans le dépôt mais ne sont pas retenus comme
entrées principales après les Phases 2H-2I:

- variables annuelles URSSAF hors tenseur trimestriel;
- caractéristiques FLORES;
- stock SIDE;
- signaux macro INSEE/Banque de France;
- signaux de régime manuels.

Ils restent utiles pour audit, ablations et comparaison, pas pour le modèle propre actuel.

## Sorties

Le pipeline produit:

- prévisions par zone d'emploi;
- prévisions sectorielles A10;
- cartes d'erreur et d'incertitude;
- indicateurs d'accélération, ralentissement et dynamisme territorial;
- diagnostics de graphe: connexions, poids mobilité/géographie, changements temporels;
- forecast prospectif 2026/2027.

## Commandes principales

Les batteries longues sont prévues pour le cluster et vivent dans `hpc/`.

```bash
# Audit strict ex-ante
bash hpc/audit/submit_herald_strict_exante.sh

# Forecast 2026/2027
bash hpc/forecast/submit_herald_forecast_2026_2027.sh

# Dashboard HERALD stable
python3 src/visualisation/generate_herald_semi_v2_dashboard.py
```

## Documents clés

- `reports/HERALD_LEAK_AUDIT_FINAL_20260507.md`
- `reports/HERALD_DATA_AVAILABILITY_CALENDAR.md`
- `reports/HERALD_REPOSITORY_AND_DASHBOARD_CLEANUP_PLAN.md`
- `reports/HERALD_PREDICTION_INTERPRETATION_METHODS.md`
- `reports/HERALD_REGIME_DISCOVERY_BATTERY.md`
- `reports/HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md`
- `reports/HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md`
- `reports/HERALD_LATENT_REGIME_DIMENSION_BATTERY_PLAN.md`
- `reports/HERALD_AUTO_REGULATION_HYPOTHESIS_AUDIT.md`
- `reports/HERALD_PHASE2L_LATENT_DIM_FINE_AUDIT.md`
- `reports/HERALD_PHASE2M_AUTOREG_AUDIT.md`
- `reports/HERALD_PHASE2O_2P_2Q_PLAN.md`
- `reports/HERALD_PHASE2O_2P_2Q_AUDIT.md`
- `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md`
- `reports/HERALD_ECONOMIC_STATE_TUTOR_PLAN.md`
- `reports/HERALD_REPOSITORY_CLEANUP_20260526.md`
- `reports/HERALD_SIDE5_STABILITY_AND_TREND_AUDIT_PLAN.md`
- `reports/REPOSITORY_CLEANUP_20260519.md`
- `reports/ATLAS_IAT_STATIC_LAYER_AUDIT.md`
- `metadata/HERALD_DATASETS_MAIN.md`
- `metadata/HERALD_DATASETS_EXPLORATORY.md`
- `metadata/HERALD_DATA_UPDATE_POLICY.md`
- `reports/dashboards/herald_france_dashboard.html`

## Règle de présentation

Pour le papier, l'application et le dashboard, dire **HERALD**. Les variantes internes restent des
configurations expérimentales utilisées pour prouver la robustesse du modèle, pas une histoire de
versions successives.
