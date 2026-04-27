# Catalogue INSEE pour l'utilisation dans le projet

Date de catalogage : 2026-04-08
Répertoire : `/home/jpdark/Downloads/project_recomm/dataset`

## État actuel

- Nombre total de fichiers `.zip` actuels : 26
- Fichiers ZIP corrompus restants : 0
- Tous les fichiers listés ci-dessous ont passé avec succès le test `unzip -t`
- Les descriptions ci-dessous privilégient la source officielle sur internet :
  - API Melodi de l'INSEE, lorsque le jeu de données dispose d'un point de terminaison (endpoint)
  - Documentation interne du fichier lui-même, lorsqu'aucun point de terminaison public équivalent n'a été identifié
- Complément territorial ajouté dans `data/raw/territorial`

## Acronymes principaux

- `RP` : Recensement de la population
- `BPE` : Base permanente des équipements
- `BTS` : Base Tous Salariés
- `FILOSOFI` : Fichier localisé social et fiscal
- `FLORES` : Fichier localisé des rémunérations et de l'emploi salarié
- `SIDE` : Système d'information sur la démographie d'entreprises
- `COM` : Commune
- `EPCI` : Établissement public de coopération intercommunale
- `UL` : Unités légales
- `ET` / `ETAB` : Établissements
- `ENT` : Entreprises
- `PRINC` : Exploitation principale
- `COMP` : Exploitation complémentaire
- `LT` : Lieu de travail
- `LR` : Lieu de résidence
- `EQTP` : Équivalent temps plein
- `PCS` : Catégorie socioprofessionnelle

## Inventaire principal

| Fichier local | Description officielle sur internet | Utilité pour le projet | API / Source officielle |
|---|---|---|---|
| `base-cc-demo-entreprises-2022.zip` | Aucun point de terminaison Melodi public spécifique identifié ; la documentation interne indique la démographie des entreprises et des établissements, les stocks en 2021 et les créations de 2013 à 2022 | Base Excel prête pour l'analyse territoriale par commune et arrondissement municipal | Aucune API cartographiée dans cette itération |
| `DS_BPE_2024_CSV_FR.zip` | `Dénombrement des équipements (commerce, sport, services, santé…)` | Mesurer l'offre territoriale d'équipements et de services | <https://api.insee.fr/melodi/data/DS_BPE_2024> |
| `DS_BPE_EVOLUTION_2024_CSV_FR.zip` | `Évolution du nombre d'équipements et services` | Analyser l'évolution temporelle des équipements par territoire | <https://api.insee.fr/melodi/data/DS_BPE_EVOLUTION_2024> |
| `DS_BTS_SAL_EQTP_SEX_AGE_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et l'âge au niveau communal` | Comparer les salaires du secteur privé par sexe et tranche d'âge | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_AGE_2023> |
| `DS_BTS_SAL_EQTP_SEX_PCS_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et la catégorie socioprofessionnelle au niveau communal` | Comparer les salaires par sexe et catégorie socioprofessionnelle | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_PCS_2023> |
| `DS_FILOSOFI_CC_2021_CSV_FR.zip` | `Principaux indicateurs sur la pauvreté en 2021 : niveau de vie, taux de pauvreté, part des ménages imposés et décomposition du revenu disponible` | Mesurer le revenu, la pauvreté et la structure des revenus des ménages | <https://api.insee.fr/melodi/data/DS_FILOSOFI_CC_2021> |
| `DS_FLORES_A17_2024_CSV_FR.zip` | `Nombre d'établissements et effectifs salariés en 17 grands secteurs` | Évaluer le tissu productif et l'emploi salarié par grands secteurs | <https://api.insee.fr/melodi/data/DS_FLORES_A17_2024> |
| `DS_FLORES_ECONOMIC_SPHERE_2024_CSV_FR.zip` | `Nombre d'établissements selon les sphères de l'économie` | Distinguer l'économie présentielle et productive par territoire | <https://api.insee.fr/melodi/data/DS_FLORES_ECONOMIC_SPHERE_2024> |
| `DS_RP_DIPLOMES_PRINC_2022_CSV_FR.zip` | `Diplômes et Formation` | Profil éducatif de la population résidente | <https://api.insee.fr/melodi/data/DS_RP_DIPLOMES_PRINC_2022> |
| `DS_RP_EMPLOI_LR_COMP_2022_CSV_FR.zip` | `Population active et chômage` | Emploi et chômage au lieu de résidence, avec granularité complémentaire | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_COMP_2022> |
| `DS_RP_EMPLOI_LT_COMP_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Structure de l'emploi au lieu de travail, exploitation complémentaire | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_COMP_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Structure principale de l'emploi au lieu de travail | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR (1).zip` | Même description officielle que le fichier précédent ; il s'agit d'un doublon valide | Sauvegarde/doublon du jeu de données précédent | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_NAVETTES_PRINC_2022_CSV_FR.zip` | `Déplacements domicile-travail` | Mobilité pendulaire, trajets domicile-travail et modes de transport | <https://api.insee.fr/melodi/data/DS_RP_NAVETTES_PRINC_2022> |
| `DS_RP_POPULATION_PRINC_2022_CSV_FR.zip` | `Population` | Volume et structure par âge/sexe de la population résidente | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC_2022> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | Aucun point de terminaison Melodi public correspondant à l'identifiant attendu n'a été trouvé | Créations d'entreprises par géographie, secteur et forme juridique | Catalogue INSEE : <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Idem que ci-dessus | Même thématique que ci-dessus dans une variante alternative du package | Catalogue INSEE : <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip` | `Créations d'entreprises - séries longues` | Séries temporelles longues de créations d'entreprises | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ENT_SERIES> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip` | `Créations d'établissements au niveau communal et supra communal par secteur d'activité (A10) et forme légale` | Créations d'établissements par géographie, secteur et forme juridique | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV.zip` | Même description officielle que le fichier précédent | Même thématique que ci-dessus dans une variante alternative du package | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_STOCKS_ET_COM_2022_CSV.zip` | `Stocks d'établissements par activité (A10)` | Stock d'établissements actifs par secteur d'activité | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2022> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip` | `Stocks d'établissements par activité (A10)` | Stock d'établissements actifs par secteur en 2023 | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV.zip` | Même description officielle que le fichier précédent | Même thématique que ci-dessus dans une variante alternative du package | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip` | `Stocks d'unités légales par activité (A10)` | Stock d'unités légales par secteur d'activité | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV.zip` | Même description officielle que le fichier précédent | Même thématique que ci-dessus dans une variante alternative du package | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Fichier auxiliaire de dictionnaires de codes pour `SIDE_STOCKS_ET_COM` | Décoder `GEO`, `FREQ`, `SIDE_MEASURE`, `TIME_PERIOD`, `ACTIVITY`, `MEASURE` | Aucune API propre ; auxiliaire du jeu de données principal |

## Complément territorial

Dossier : `data/raw/territorial`

Ces fichiers ont été intégrés pour finaliser la couche territoriale du projet.

| Fichier local | Description officielle / Interprétation | Utilité pour le projet | Source officielle |
|---|---|---|---|
| `data/raw/territorial/fonds_ze2020_2026.zip` | Fonds cartographique des zones d'emploi 2020, mis à jour pour la référence 2026 ; contient `com_ze2020_2026.zip` et `ze2020_2026.zip` | Base géographique pour la cartographie et les jointures spatiales des zones d'emploi et des communes | <https://www.insee.fr/fr/statistiques/fichier/4652957/fonds_ze2020_2026.zip> |
| `data/raw/territorial/ZE2020_au_01-01-2026.zip` | Table officielle des zones d'emploi 2020 au 01/01/2026 ; contient `ZE2020_au_01-01-2026.xlsx` | Référentiel tabulaire des zones d'emploi pour le croisement territorial et la nomenclature | <https://www.insee.fr/fr/statistiques/fichier/4652957/ZE2020_au_01-01-2026.zip> |
| `data/raw/territorial/table-appartenance-geo-communes-2020.zip` | Table d'appartenance géographique des communes ; contient `table-appartenance-geo-communes-2020.xlsx` | Relier les communes aux géométries et aux zonages administratifs/statistiques | <https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes-2020.zip> |
| `data/raw/territorial/cog_ensemble_2026_csv.zip` | COG 2026 complet en format CSV ; inclut les tables `v_commune_2026.csv`, `v_departement_2026.csv`, `v_region_2026.csv`, `v_arrondissement_2026.csv` | Référentiel géographique exhaustif pour les codes officiels, l'historique et la normalisation territoriale | <https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip> |

### Note sur les anciennes URL

Les trois URL ci-dessous, initialement fournies, ont renvoyé une erreur `HTTP 500` sur le site de l'INSEE le 08/04/2026, téléchargeant du contenu HTML au lieu du fichier binaire attendu :

- `https://www.insee.fr/fr/statistiques/fichier/4652957/ze2020_shp.zip`
- `https://www.insee.fr/fr/statistiques/fichier/4652957/ze2020_liste_communes.csv`
- `https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes.csv`

En conséquence, les versions officielles actuelles encore disponibles sur le site de l'INSEE ont été maintenues dans le catalogue et le répertoire :

- `fonds_ze2020_2026.zip`
- `ZE2020_au_01-01-2026.zip`
- `table-appartenance-geo-communes-2020.zip`

## Catalogue des API identifiées

### API des jeux de données présents localement

| Jeu de données / API | Titre officiel renvoyé par l'API | Statut |
|---|---|---|
| `DS_BPE_2024` | `Dénombrement des équipements (commerce, sport, services, santé…)` | OK |
| `DS_BPE_EVOLUTION_2024` | `Évolution du nombre d'équipements et services` | OK |
| `DS_BTS_SAL_EQTP_SEX_AGE_2023` | `Salaires dans le secteur privé selon le sexe et l'âge au niveau communal` | OK |
| `DS_BTS_SAL_EQTP_SEX_PCS_2023` | `Salaires dans le secteur privé selon le sexe et la catégorie socioprofessionnelle au niveau communal` | OK |
| `DS_FILOSOFI_CC_2021` | `Principaux indicateurs sur la pauvreté en 2021 : niveau de vie, taux de pauvreté, part des ménages imposés et décomposition du revenu disponible` | OK |
| `DS_FLORES_A17_2024` | `Nombre d'établissements et effectifs salariés en 17 grands secteurs` | OK |
| `DS_FLORES_ECONOMIC_SPHERE_2024` | `Nombre d'établissements selon les sphères de l'économie` | OK |
| `DS_RP_DIPLOMES_PRINC_2022` | `Diplômes et Formation` | OK |
| `DS_RP_EMPLOI_LR_COMP_2022` | `Population active et chômage` | OK |
| `DS_RP_EMPLOI_LT_COMP_2022` | `Emploi au lieu de travail` | OK |
| `DS_RP_EMPLOI_LT_PRINC_2022` | `Emploi au lieu de travail` | OK |
| `DS_RP_NAVETTES_PRINC_2022` | `Déplacements domicile-travail` | OK |
| `DS_RP_POPULATION_PRINC_2022` | `Population` | OK |
| `DS_SIDE_CREA_ENT_SERIES` | `Créations d'entreprises - séries longues` | OK |
| `DS_SIDE_CREA_ETAB_COM_2024` | `Créations d'établissements au niveau communal et supra communal par secteur d'activité (A10) et forme légale` | OK |
| `DS_SIDE_STOCKS_ET_COM_2022` | `Stocks d'établissements par activité (A10)` | OK |
| `DS_SIDE_STOCKS_ET_COM_2023` | `Stocks d'établissements par activité (A10)` | OK |
| `DS_SIDE_STOCKS_UL_COM_2023` | `Stocks d'unités légales par activité (A10)` | OK |

### Jeux de données locaux sans point de terminaison Melodi confirmé dans cette itération

| Fichier | Situation |
|---|---|
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | Aucun point de terminaison Melodi public avec l'identifiant attendu n'a été trouvé |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Aucun point de terminaison Melodi public avec l'identifiant attendu n'a été trouvé |
| `base-cc-demo-entreprises-2022.zip` | Fichier hors standard `DS_*` ; sans point de terminaison Melodi cartographié |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Fichier auxiliaire, ne constitue pas un jeu de données principal indépendant |

## API de récupération des jeux de données qui étaient corrompus

Ces deux jeux de données ne sont plus présents sous forme de fichier ZIP local valide, mais l'API a répondu correctement et permet de récupérer les données au format JSON paginé :

| Jeu de données / API | Titre officiel | Point de terminaison (endpoint) |
|---|---|---|
| `DS_RP_EMPLOI_LR_PRINC` | `Population active et chômage` | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC> |
| `DS_RP_POPULATION_COMP` | `Population` | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_COMP> |

Conclusion technique :

- L'intégrité de ces deux jeux de données peut être rétablie via l'API.
- L'extraction native s'effectue au format JSON, et non via le format ZIP original.
- Pour réintégrer ces jeux de données dans le projet, la procédure recommandée consiste à interroger l'API et à procéder à une exportation vers le format CSV.

## Sources officielles utilisées

- Catalogue de l'INSEE : <https://catalogue-donnees.insee.fr/fr/catalogue/recherche>
- Sources territoriales de l'INSEE :
  - <https://www.insee.fr/fr/statistiques/fichier/4652957/fonds_ze2020_2026.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/4652957/ZE2020_au_01-01-2026.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes-2020.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip>
- API Melodi de l'INSEE :
  - <https://api.insee.fr/melodi/data/DS_BPE_2024>
  - <https://api.insee.fr/melodi/data/DS_BPE_EVOLUTION_2024>
  - <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_AGE_2023>
  - <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_PCS_2023>
  - <https://api.insee.fr/melodi/data/DS_FILOSOFI_CC_2021>
  - <https://api.insee.fr/melodi/data/DS_FLORES_A17_2024>
  - <https://api.insee.fr/melodi/data/DS_FLORES_ECONOMIC_SPHERE_2024>
  - <https://api.insee.fr/melodi/data/DS_RP_DIPLOMES_PRINC_2022>
  - <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_COMP_2022>
  - <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_COMP_2022>
  - <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022>
  - <https://api.insee.fr/melodi/data/DS_RP_NAVETTES_PRINC_2022>
  - <https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC_2022>
  - <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ENT_SERIES>
  - <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024>
  - <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2022>
  - <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023>
  - <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023>
  - <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC>
  - <https://api.insee.fr/melodi/data/DS_RP_POPULATION_COMP>
