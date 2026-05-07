# HERALD — Prévision économique territoriale

HERALD (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*) est un modèle
hybride de prévision territoriale pour la France. Il estime les créations d'établissements par zone
d'emploi, puis transforme ces prévisions en cartes de dynamisme, ralentissement, incertitude et
structure sectorielle.

Le dépôt est maintenant organisé autour d'un seul nom public: **HERALD**. Les anciens noms V3, V6,
V7 et Semi désignent des configurations de laboratoire et ne structurent plus la présentation finale.

## État scientifique actuel

Le modèle principal pour la France est la configuration HERALD strict ex-ante / no-source-flags. Elle
retire les indicateurs ambigus de disponibilité des sources et sépare clairement backtest, audit
anti-fuite et forecast prospectif.

Conclusion actuelle:

- pas de fuite directe détectée dans les batteries strict ex-ante et target-shuffle;
- les modèles HERALD battent fortement Ridge AR, ARIMA, LSTM et les STGNN de comparaison sur le panel
  France geo2025;
- le forecast 2026/2027 est une prévision prospective conditionnelle aux données disponibles le
  2026-05-07, pas une prévision ex-ante au 2026-01-01;
- le graphe est utile pour l'interprétation territoriale: mobilité, connexions économiques et
  reconfiguration pendant les chocs.

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

HERALD utilise, par zone d'emploi:

- historique SIDE/INSEE de créations d'établissements;
- trajectoire récente de croissance;
- secteurs A10;
- emploi et masse salariale URSSAF;
- caractéristiques FLORES;
- graphes géographique et mobilité domicile-travail;
- flags de régime économique prédéfinis.

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
- `metadata/HERALD_DATASETS_MAIN.md`
- `metadata/HERALD_DATASETS_EXPLORATORY.md`
- `metadata/HERALD_DATA_UPDATE_POLICY.md`
- `reports/dashboards/herald_france_dashboard_offline.html`

## Règle de présentation

Pour le papier, l'application et le dashboard, dire **HERALD**. Les variantes internes restent des
configurations expérimentales utilisées pour prouver la robustesse du modèle, pas une histoire de
versions successives.
