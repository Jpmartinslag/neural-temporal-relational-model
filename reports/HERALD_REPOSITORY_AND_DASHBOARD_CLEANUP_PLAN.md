# HERALD — plan de nettoyage, versionnement et dashboard

Date: 2026-05-07

## Objectif

Transformer le dépôt de travail en un projet présentable sous un seul nom public: **HERALD**.

Les anciens noms V3, V6, V7 et Semi restent utiles comme traces de laboratoire, mais ne doivent pas
structurer la présentation scientifique finale. Pour l'article et le dashboard, ils deviennent des
**configurations expérimentales** d'un même modèle HERALD.

## 1. Organisation recommandée des dossiers

Structure cible:

```text
dataset/
├── README.md
├── data/
│   ├── raw/                  # sources brutes, non versionnées si lourdes
│   ├── interim/              # tables construites avant panel final
│   └── processed/            # panels, graphes, cibles canoniques
├── hpc/
│   ├── batteries/            # scripts SLURM de batteries complètes
│   ├── audit/                # leak audit, strict ex-ante, target-shuffle
│   └── forecast/             # forecast 2026/2027
├── reports/
│   ├── methodology/          # calendrier, leak audit, validation
│   ├── dashboards/           # HTML finaux publiables
│   ├── metrics/              # JSON/CSV agrégés légers
│   └── archive/              # V3/V4/V5/V6 historiques
├── src/
│   ├── herald/               # code canonique HERALD
│   ├── baselines/            # Ridge, ARIMA, LSTM, STGNN/DCRNN
│   ├── analysis/             # agrégation, tests statistiques
│   └── dashboard/            # génération du dashboard
└── hpc_results/              # sorties lourdes, non versionnées
```

Règle: `hpc_results/` doit rester une archive de calcul, pas la source principale du dashboard. Le
dashboard final doit lire des fichiers légers exportés dans `reports/metrics/`.

## 2. Renommage public

À faire:

- `train_herald_v6.py`, `train_herald_semi_v2.py`, `train_herald_v7.py` restent en archive technique.
- créer un wrapper public `src/herald/train.py` qui expose les configurations retenues:
  - `herald_main`: panel `strict_no_source_flags`, configuration Semi V2 opérationnelle;
  - `herald_conservative`: panel `strict_lag_only`;
  - `herald_v6_reference`: référence historique;
  - `ridge_ar`, `arima_local`, `lstm_local`, `dcrnn`, `dynamic_stgnn`.
- dans les rapports publics, ne pas dire "V3/V6/V7" comme histoire de versions. Dire:
  - HERALD local-only;
  - HERALD dynamic graph;
  - HERALD semi-supervised;
  - HERALD strict ex-ante.

## 3. Dashboard — ordre narratif recommandé

Le dashboard doit guider la lecture du plus important au plus exploratoire.

### Section A — Résumé exécutif

Cartes/chiffres:

- modèle principal retenu;
- WMAPE 2024/2025;
- comparaison vs Ridge AR;
- statut leak audit;
- statut calendrier de disponibilité;
- forecast 2026/2027 national.

Interprétation en français:

> HERALD estime les créations d'établissements par zone d'emploi et identifie les territoires en
> accélération, ralentissement ou stabilité. Les prévisions 2026/2027 sont conditionnelles aux données
> disponibles le 2026-05-07.

### Section B — Validation scientifique

Graphiques:

- bar chart WMAPE par modèle: Ridge, ARIMA, LSTM, STGNN, HERALD références, HERALD principal;
- courbes par année 2021-2025;
- distribution par seed;
- tableau de wins pairés;
- target-shuffle leak stress.

Ne pas mélanger forecast 2026/2027 avec WMAPE observé.

### Section C — Carte France, une seule carte principale

Une seule carte interactive avec contrôles:

- année: 2021, 2022, 2023, 2024, 2025, 2026, 2027;
- couche:
  - réel;
  - prédit;
  - erreur absolue;
  - erreur relative;
  - accélération;
  - décélération;
  - incertitude entre seeds.
- modèle: Ridge, HERALD référence, HERALD principal.

Important: utiliser une palette qui ne donne pas l'impression que "bleu = parfait". Pour l'erreur,
préférer une palette séquentielle neutre: clair = faible erreur, foncé = forte erreur.

### Section D — Secteurs A10

Visualisation recommandée:

- carte principale avec sélection d'un secteur A10;
- barres empilées par zone sélectionnée;
- top zones par croissance sectorielle;
- erreur sectorielle par A10;
- comparaison HERALD vs baseline sectoriel lag-1.

Éviter de dessiner tous les secteurs simultanément dans chaque zone: cela devient illisible. La bonne
interface est "un secteur sélectionné à la fois" + détail au clic.

### Section E — Graphe économique

Graphiques:

- carte des connexions top-k filtrables par année;
- filtre intra-région / inter-région;
- poids mobilité vs géographie;
- connexions nouvelles/stables/disparues;
- adj_delta par année pour chocs COVID/rebound et 2025.

Chaque connexion doit être interprétée comme **association structurelle apprise**, pas causalité.

### Section F — Forecast 2026/2027

Graphiques:

- prévision nationale;
- carte de croissance prévue;
- top 20 zones en accélération;
- top 20 zones en ralentissement;
- incertitude par seed;
- comparaison avec Ridge forecast.

Texte obligatoire:

> Prévision prospective conditionnelle aux données disponibles le 2026-05-07. Ce n'est pas une
> prévision produite au 2026-01-01.

## 4. Indicateurs économiques dérivés des prédictions

À calculer après la faxine:

- **indice de dynamisme territorial**: croissance prévue normalisée par la tendance historique locale;
- **indice d'accélération**: forecast minus lag-1 / lag-1;
- **indice de refroidissement**: baisse prévue persistante sur 2 ans;
- **indice de surprise**: écart HERALD - Ridge AR;
- **indice d'incertitude**: écart interquartile entre seeds;
- **indice sectoriel A10**: croissance prévue par secteur et zone;
- **indice réseau**: centralité dans les connexions apprises;
- **indice de dépendance territoriale**: part de l'information venant du graphe vs local.

Ces indicateurs sont plus utiles pour un dashboard/app que le WMAPE brut.

## 5. Annexes possibles au graphe

Pour découvrir de nouvelles tendances économiques, le graphe HERALD peut être enrichi par:

- mobilité domicile-travail actualisée;
- proximité ferroviaire / temps de trajet;
- structure sectorielle A10/A17;
- densité d'établissements employeurs;
- emploi salarié et masse salariale URSSAF;
- population active et démographie;
- tension immobilière / construction SITADEL;
- zones politiques publiques: QPV, ZRR, ZAN;
- centralité métropolitaine et périphérie productive;
- similarité de trajectoires historiques entre zones.

Chaque annexe doit être testée comme prior ou feature séparée, jamais ajoutée sans ablation.

## 6. Règles de versionnement Git

À versionner:

- code source;
- scripts HPC propres;
- fichiers de configuration;
- panels/graphes canoniques si taille raisonnable;
- rapports méthodologiques;
- métriques agrégées légères;
- dashboard HTML offline final.

À exclure:

- `.npz` internals lourds;
- prédictions CSV par seed si régénérables;
- logs HPC bruts;
- archives téléchargées;
- multiples dashboards expérimentaux.

## 7. Ordre de travail

1. Auditer les fichiers non commités.
2. Séparer résultats lourds et artefacts publiables.
3. Créer nomenclature publique HERALD.
4. Exporter métriques légères depuis les batteries existantes.
5. Adapter le dashboard stable, sans réécrire le bundle Plotly.
6. Vérifier tous les textes en français.
7. Mettre à jour README.
8. Commit + push.

