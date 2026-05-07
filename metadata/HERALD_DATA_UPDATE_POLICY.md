# HERALD — politique de mise à jour des données

Date: 2026-05-07

## Principe

HERALD doit fonctionner avec un calendrier explicite. Pour chaque forecast, on déclare une date de
prévision et on autorise seulement les sources publiées avant cette date.

Exemple actuel:

```text
date de prévision = 2026-05-07
```

Le forecast 2026/2027 produit aujourd'hui est donc conditionnel aux données disponibles à cette date.

## Calendrier de maintenance

| Fréquence | Sources | Action |
|---|---|---|
| Mensuelle | vérifier nouvelles publications URSSAF / SITADEL si intégrées | télécharger si disponible, reconstruire features rapides |
| Trimestrielle | URSSAF trimestriel | reconstruire tensors quarterly et forecast opérationnel |
| Annuelle | SIDE créations, SIDE A10, FLORES, SIDE stocks | reconstruire panel annuel, splits, backtests et dashboard |
| À changement de nomenclature | ZE2020, COG, géométries | reconstruire mappings, graphes et cartes |

## Pipeline cible d'extraction

```text
download raw -> validate checksum/schema -> build interim -> build processed -> run audit -> train -> export dashboard metrics
```

## Ce qui doit être automatisé

- téléchargement des sources INSEE/URSSAF quand endpoint stable existe;
- journal de version des sources;
- contrôle de colonnes attendues;
- contrôle des années disponibles;
- contrôle de couverture des 280 zones d'emploi;
- génération automatique du calendrier de disponibilité.

## Ce qui reste manuel au début

- validation des changements méthodologiques INSEE/URSSAF;
- décision d'intégrer une nouvelle source exploratoire;
- interprétation économique des nouvelles connexions du graphe;
- passage d'A10 vers A17/A20.

## Sorties à publier dans le dépôt

À versionner:

- panels canoniques légers;
- graphes canoniques;
- métriques agrégées;
- calendrier de disponibilité;
- dashboards HTML offline.

À garder local / hors Git:

- ZIP bruts;
- logs de téléchargement;
- CSV de prédictions par seed;
- NPZ internes lourds;
- archives HPC.

