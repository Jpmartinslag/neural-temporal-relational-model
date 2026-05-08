# HERALD France — plan final du dashboard

Date: 2026-05-07

## Objectif

Le dashboard final doit presenter HERALD comme un modele unique, utilisable pour
une presentation scientifique et comme base d'un futur app territorial. Il doit
eviter l'accumulation de cartes et transformer les resultats en une lecture
progressive:

1. comprendre ce que HERALD utilise;
2. verifier que le protocole est propre;
3. comparer la performance;
4. visualiser le reel vs predit;
5. explorer la France avec une carte unique;
6. expliquer les secteurs A10;
7. expliquer le graphe appris;
8. separer le forecast 2026/2027;
9. documenter les limites methodologiques.

## Structure cible

### 1. Resume executif

Afficher seulement les indicateurs essentiels:

- WMAPE 2025 HERALD;
- WMAPE 2025 Ridge AR;
- gain relatif HERALD vs Ridge;
- nombre de seeds;
- sceau court: "strict ex-ante + target-shuffle: aucun leak direct detecte".

### 2. Donnees et protocole walk-forward

Objectif: rendre visible que chaque annee est testee comme une annee future.

Afficher:

- table train/test par fold;
- entrees du modele: historique local, A10, mobilite, geographie, regime;
- cible: creations d'etablissements par zone d'emploi;
- avertissement: forecast et backtest observe sont separes.

### 3. Performance HERALD vs baselines

Graphiques:

- WMAPE par annee 2021-2025;
- HERALD vs Ridge AR, ARIMA, LSTM, DCRNN, Dynamic STGNN;
- distribution par seed;
- tableau wins/deltas si disponible.

Regle: ne pas reconstruire des volumes de baselines a partir de WMAPE. Les
volumes ne doivent etre affiches que si les CSV de prediction existent.

### 4. Reel vs predit

Afficher:

- reel INSEE vs HERALD France entiere;
- real vs predit par zone seulement apres clic sur la carte;
- erreur absolue dans le hover;
- annees 2021-2025 quand la Run 2 est disponible.

### 5. Carte territoriale unique

Une seule carte doit concentrer l'exploration spatiale.

Modes noyau visibles par defaut:

- reel observe;
- predit HERALD;
- erreur absolue;
- erreur relative.

Modes avances, caches dans un panneau "analyse avancee":

- croissance;
- acceleration;
- incertitude;
- graphe ON/OFF.

Definitions obligatoires pour chaque mode:

| Mode | Formule | Unite | Fenetre | Denominateur |
| --- | --- | --- | --- | --- |
| Reel observe | `y_obs[t,z]` | creations | annee choisie | aucun |
| Predit HERALD | `y_hat[t,z]` | creations | annee choisie | aucun |
| Erreur absolue | `abs(y_hat[t,z] - y_obs[t,z])` | creations | annee choisie | aucun |
| Erreur relative | `abs(y_hat[t,z] - y_obs[t,z]) / max(y_obs[t,z], eps)` | % | annee choisie | volume reel |
| Croissance | `(y_obs[t,z] - y_obs[t-1,z]) / max(y_obs[t-1,z], eps)` | % | t-1 -> t | volume reel t-1 |
| Acceleration | `growth[t,z] - growth[t-1,z]` | points de % | deux transitions | croissance precedente |
| Incertitude | `std_seed(y_hat[t,z]) / max(mean_seed(y_hat[t,z]), eps)` | coefficient de variation | annee choisie | prediction moyenne |

Controles:

- annee;
- metrique;
- secteur A10;
- densite des aretes du graphe: faible / moyenne / forte.

Regle d'ergonomie: remplacer le trio `top-k + opacite + seuil` par un seul
controle de densite. Les parametres fins peuvent rester dans un panneau avance,
mais ne doivent pas etre l'interface par defaut.

Au clic sur une zone:

- reel vs predit;
- A10 reel vs predit;
- connexions apprises de la zone;
- message court d'interpretation;
- niveau de confiance.

## Graphe appris: interpretation critique

Le graphe ne doit pas etre une deuxieme carte. Il doit etre une couche optionnelle
sur la carte principale et un bloc analytique sans carte dupliquee.

Le bloc graphe est obligatoire seulement si les NPZ/internals du modele principal
sont disponibles. Sinon, afficher explicitement:

```text
Graphe appris non disponible pour cette execution; seul le prior de mobilite est
affiche.
```

### Table "Pourquoi cette connexion ?"

Pour chaque top arete:

- zone origine;
- zone destination;
- poids appris;
- rang;
- distance geographique;
- force de mobilite pendulaire;
- similarite de croissance;
- stabilite entre seeds;
- annees d'apparition;
- interpretation critique:
  - coherente avec mobilite;
  - coherente avec proximite;
  - connexion apprise non evidente;
  - a verifier.

Formulation autorisee:

> HERALD utilise cette relation comme signal predictif.

Formulation interdite:

> Cette zone cause la croissance de l'autre zone.

### Graphiques canoniques de modele graphe

Ajouter un bloc scientifique, sans carte supplementaire:

- distribution des poids des aretes;
- top weighted degree par zone;
- evolution temporelle de `adj_delta`;
- gamma mobilite vs gamma geographie;
- stabilite des aretes entre seeds;
- ablation HERALD vs controle sans graphe;
- erreur par degre/connectivite.
- heatmap agregee des poids par cluster territorial, jamais la matrice 280x280
  brute dans l'interface principale.

Chaque graphique doit avoir une phrase:

- pourquoi on le montre;
- comment le lire;
- ce qui constitue une evidence forte;
- limite methodologique.

Exemple:

> Ce graphique montre si HERALD concentre l'information dans quelques connexions
> fortes ou diffuse le signal sur de nombreuses relations faibles.

## Secteurs A10

Objectif: montrer que le modele peut expliquer les dynamiques economiques par
secteur, sans surestimer la precision sectorielle.

Afficher au minimum:

- selecteur annee;
- selecteur zone;
- selecteur secteur;
- volumes reels vs predits;
- WMAPE par secteur;
- erreur absolue par secteur;
- variance inter-seeds par secteur;
- support statistique: volume reel et nombre de zones actives;
- secteurs qui tirent la croissance;
- secteurs avec plus grand ecart.

Regle: toujours afficher le reel avec le predit.

Ajouter si possible:

- correlation de rang Spearman entre top secteurs reels et top secteurs predits;
- avertissement si un secteur a faible support ou forte variance inter-seeds.

## Forecast 2026/2027

Doit etre separe visuellement des backtests observes.

Titre obligatoire:

```text
Prevision prospective — non encore observee
```

Afficher:

- prediction nationale HERALD;
- comparaison Ridge AR;
- top zones acceleration;
- top zones deceleration;
- incertitude entre seeds;
- date de coupure des donnees visible dans tous les graphiques;
- avertissement calendrier:
  - prediction conditionnelle aux donnees disponibles au 2026-05-07;
  - pas forecast ex-ante au 2026-01-01.

Regles strictes:

- ne jamais afficher WMAPE pour 2026/2027;
- ne jamais melanger 2026/2027 avec les graphiques de performance observee;
- tout titre de graphique prospectif doit contenir "non encore observe".

## Audit methodologique

Afficher compactement:

- strict ex-ante;
- target-shuffle;
- calendrier reel de disponibilite;
- aucun leak direct detecte;
- ne pas ecrire "zero leak";
- risque residuel: timing de publication des sources.

## Donnees attendues de la Run 2

Avant implementation finale:

- confirmer 10 seeds;
- confirmer folds 2021, 2022, 2023, 2024, 2025;
- confirmer memes donnees pour HERALD et baselines;
- confirmer JSON, CSV, NPZ presents;
- verifier pas d'overwrite;
- verifier logs sans erreur fatale.

## Fichiers auxiliaires a produire

Quand les donnees finales seront disponibles:

```text
reports/metrics/herald_dashboard/graph_edges_explained.csv
reports/metrics/herald_dashboard/graph_edge_stability.csv
reports/metrics/herald_dashboard/zone_growth_metrics.csv
reports/metrics/herald_dashboard/zone_a10_metrics.csv
reports/metrics/herald_dashboard/forecast_rankings.csv
```

## Validation du dashboard final

Checklist:

- aucun plot vide;
- aucun nom interne V3/V6/V7/Semi visible;
- carte unique fonctionnelle;
- graphe ON/OFF fonctionnel;
- modes de carte avec formule, unite, fenetre et denominateur documentes;
- aucun volume comparatif de baseline sans CSV de prediction reel;
- couverture folds/seeds/annees verifiee automatiquement;
- stabilite des aretes entre seeds presente si le graphe appris est affiche;
- ablation avec/sans graphe presente si un claim predictif du graphe est formule;
- A10 avec volume reel, volume predit, WMAPE, erreur absolue et variance
  inter-seeds;
- texte en francais;
- real et predit toujours distingues;
- forecast separe de backtest;
- JavaScript valide;
- HTML offline ouvrable sans internet pour Plotly;
- pas de Mapbox/tuiles externes obligatoires.

## Decision

Ne pas reconstruire lourdement le dashboard avant la fin de la Run 2. La bonne
sequence est:

1. recuperer Run 2;
2. auditer les fichiers;
3. generer les fichiers auxiliaires;
4. appliquer cette structure;
5. regenerer HTML online/offline;
6. verifier visuellement.
