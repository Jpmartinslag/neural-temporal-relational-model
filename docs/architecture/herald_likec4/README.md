# Architecture HERALD avec LikeC4

Ce dossier contient une visualisation navigable de l'architecture **Ridge AR vs HERALD**.

LikeC4 permet de changer de granularité:

- vue générale HERALD France;
- comparaison Ridge AR vs HERALD;
- détail Ridge AR;
- détail HERALD;
- détail graphe dynamique;
- couche HERALD Intelligence v0.

## Commandes

Depuis la racine du dépôt:

### Option recommandée pour ouvrir directement

```text
reports/architecture/herald_architecture_interactive.html
```

Cette version est un HTML autonome: elle s'ouvre directement dans le navigateur,
sans serveur local.

### LikeC4 dynamique

```bash
npm run likec4:dev
```

Puis ouvrir l'URL affichée par LikeC4.

Pour générer un site statique:

```bash
npm run likec4:build
```

Sortie attendue:

```text
reports/architecture/herald_likec4/
```

## Fichier principal

```text
docs/architecture/herald_likec4/herald.c4
```

## Lecture méthodologique

Ridge AR est le contrôle linéaire:

```text
lags locaux + growth -> imputation -> standardisation -> Ridge(alpha=1)
```

HERALD est le modèle hybride:

```text
HERALD = Ridge AR + correction résiduelle neurale + graphe dynamique + A10
```

La couche **HERALD Intelligence v0** n'est pas une IA supplémentaire. Elle est
une couche exploratoire de post-traitement des sorties HERALD.
