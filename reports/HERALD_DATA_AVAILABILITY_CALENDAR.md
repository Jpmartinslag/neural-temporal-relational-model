# HERALD France — calendrier de disponibilité des données

Date: 2026-05-07  
Statut: version méthodologique vérifiée pour l'audit HERALD-France.

Mise à jour de vérification externe: sources officielles consultées le 2026-05-07.

## Pourquoi ce document existe

Les tests strict ex-ante et target-shuffle vérifient surtout l'absence de fuite directe du target dans
le pipeline d'entraînement. Ils ne suffisent pas à eux seuls pour affirmer qu'une prévision 2026/2027
est un forecast opérationnel.

La question restante est:

> Une variable `t-1` était-elle réellement publiée au moment où la prévision aurait été produite ?

Si oui, elle peut être utilisée dans un forecast.  
Si non, l'exercice devient un nowcast rétrospectif ou une simulation avec information publiée plus tard.

## Résumé exécutif

Le panel `strict_lag_only` est le plus conservateur: il utilise essentiellement les lags SIDE, la
croissance passée et les flags de régime. Il est très utile comme test anti-fuite, mais il dépend de la
disponibilité effective de SIDE 2025 pour produire un forecast 2026.

Le panel `strict_no_source_flags` est le meilleur candidat opérationnel actuel: il retire les flags
`has_*` et conserve les variables `t_minus_1`. Il reste toutefois nécessaire de vérifier la disponibilité
réelle de FLORES, SIDE stocks et URSSAF pour chaque année de forecast.

Le panel complet avec `has_flores_source`, `has_side_stock_source`, `has_urssaf_source` doit rester une
ablation, pas le modèle principal, car ces flags peuvent encoder des régimes de disponibilité de données.

## Fichier machine-readable

Le calendrier détaillé par groupe de variables est ici:

```text
reports/herald_feature_availability_calendar_v1.csv
```

## Décision par source

| Source / groupe | Statut pour backtest 2025 | Statut pour forecast 2026/2027 | Risque |
|---|---|---|---|
| SIDE créations, lags AR | valide en strict ex-ante | valide pour une prévision produite après le 2026-04-14; pas valide pour une prévision produite avant publication SIDE 2025 | faible/moyen |
| SIDE A10 secteurs | valide pour évaluation; prior sectoriel en `t-1` | valide pour une prévision 2026 produite après le 2026-04-14 si le prior utilise 2025 | faible/moyen |
| FLORES `t_minus_1` | utilisable dans le panel observé | FLORES fin 2024 est paru le 2026-03-31, donc utilisable pour une prévision produite le 2026-05-07; FLORES 2025 reste non disponible pour 2027 | moyen |
| SIDE stocks `t_minus_1` | attention: stock 2024 absent pour target 2025 | non disponible pour 2026 avec fichiers actuels | élevé |
| URSSAF annuel `t_minus_1` | utilisable avec retard fort | publication annoncée fin de trimestre + environ 250 jours; trop tardif pour un forecast précoce | élevé |
| URSSAF trimestriel Q1-Q3 `t-1` | méthodologiquement meilleur que l'annuel complet | publication annoncée fin de trimestre + environ 80 jours; Q1-Q3 2025 sont plausiblement disponibles au 2026-05-07 | faible/moyen |
| Flags COVID/rebound | valide | valide si pré-déclaré | faible |
| Flags `has_*source` | à éviter comme modèle principal | à éviter comme modèle principal | moyen |
| Graphe géographique | valide | valide si géographie fixe | faible |
| Graphe mobilité | valide comme prior structurel | valide comme prior structurel, pas comme signal annuel actualisé | faible/moyen |

## Ce que nous pouvons dire maintenant

Formulation défendable:

> Les batteries strict ex-ante réduisent fortement le risque de fuite directe du target. Le modèle ne
> semble pas utiliser le target 2025 dans l'entraînement du fold 2025, et les panels conservateurs retirent
> les signaux les plus ambigus.

Formulation à éviter:

> Le modèle n'a aucun leak et produit un forecast opérationnel totalement validé.

Il manque encore la validation du calendrier réel de publication.

Après vérification externe, pour une prévision produite **le 2026-05-07**, le calendrier est défendable
pour les signaux suivants:

- SIDE créations 2025 et A10 2025: disponibles depuis le 2026-04-14.
- FLORES fin 2024: disponible depuis le 2026-03-31.
- URSSAF trimestriel Q1-Q3 2025: compatible avec la règle de mise à jour fin de trimestre + environ 80 jours.
- Graphe géographique et graphe mobilité: utilisables comme priors structurels.

Les signaux suivants restent à exclure ou à traiter comme manquants/imputés:

- SIDE stocks 2024/2025: non disponibles dans la diffusion actuelle; les stocks vont jusqu'à 2023.
- URSSAF annuel 2025: mise à jour trop tardive pour un forecast précoce, sauf si la date exacte de diffusion est vérifiée.
- `has_*source`: ne doit pas être utilisé dans le modèle principal.

## Règle proposée pour le papier

Définir trois protocoles séparés:

1. **Backtest observé**: toutes les données historiques sont disponibles, mais le split reste walk-forward.
2. **Strict ex-ante rétrospectif**: features limitées à `t-1`, scaler/imputer fit uniquement sur train,
   target du fold exclu de la loss.
3. **Forecast opérationnel**: seules les variables publiées avant une date de prévision déclarée sont autorisées.

Pour 2026/2027, le rapport doit indiquer explicitement la date de prévision:

```text
date de prévision = YYYY-MM-DD
```

Puis lister les sources autorisées à cette date.

## Décision pratique pour HERALD-France

Tant que les dates officielles ne sont pas vérifiées:

- modèle principal pour leak audit: `strict_no_source_flags`;
- modèle ultra-conservateur de contrôle: `strict_lag_only`;
- éviter de présenter le panel complet avec `has_*` comme modèle principal;
- présenter forecast 2026/2027 comme **prévision prospective conditionnelle aux données disponibles au 2026-05-07**, pas comme forecast produit avant le début de 2026.

Après vérification, la formulation recommandée devient:

> HERALD produit une prévision prospective 2026/2027 conditionnelle à l'information disponible au
> 2026-05-07. Elle n'est pas une prévision ex-ante au 2026-01-01. Le panel principal doit exclure les
> flags de disponibilité `has_*source` et documenter explicitement l'absence de stocks SIDE après 2023.

## Vérifications restantes

1. Vérifier la date exacte du dernier trimestre URSSAF disponible dans le fichier local utilisé.
2. Construire un panel `forecast_2026_operational_cutoff_YYYYMMDD` qui exclut automatiquement toute feature non publiée à la date choisie.
3. Documenter la date de prévision retenue dans chaque tableau de forecast.

## Sources officielles vérifiées

- INSEE SIDE créations d'entreprises et d'établissements 2012-2025: publication du 2026-04-14, <https://www.insee.fr/fr/statistiques/2021271>.
- INSEE SIDE stocks d'unités légales et d'établissements économiquement actifs 2014-2023: publication du 2025-11-06, <https://www.insee.fr/fr/statistiques/8655223>.
- INSEE FLORES caractéristiques des établissements fin 2024: publication du 2026-03-31, <https://www.insee.fr/fr/statistiques/8956736>.
- URSSAF trimestriel par zone d'emploi: mise à jour annoncée fin de trimestre + environ 80 jours, <https://open.urssaf.fr/explore/dataset/effectifs-salaries-et-masse-salariale-du-secteur-prive-par-zone-demploi/api/>.
- URSSAF annuel par zone d'emploi: mise à jour annoncée fin de trimestre + environ 250 jours, <https://open.urssaf.fr/explore/dataset/nombre-etab-effectifs-salaries-et-masse-salariale-secteur-prive-zones-emploi/>.

## Conclusion

Le risque de leak direct est traité par les batteries strict ex-ante et target-shuffle.  
Le risque restant est un risque de **timing de publication**. C'est ce calendrier qui transforme
une bonne validation rétrospective en protocole de forecast opérationnel publiable.
