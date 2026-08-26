# INSEE dataset catalog

Cataloged 2026-04-08. Consolidates two earlier duplicate versions of this file (Portuguese and
French) into one English document — no content was dropped, only the explanatory prose was
translated. Official INSEE dataset titles stay in French, quoted, as published by the source;
that is deliberate, not an oversight.

## Status at cataloging time

- 26 `.zip` files on hand, 0 corrupted (every file passed `unzip -t`).
- Each description below prefers the INSEE Melodi API endpoint when the dataset has one, and
  the file's own internal documentation otherwise.
- A territorial-reference complement was added under `data/raw/territorial`.

## Acronyms

| Acronym | Meaning |
|---|---|
| `RP` | Recensement de la population (population census) |
| `BPE` | Base permanente des équipements (facilities/amenities database) |
| `BTS` | Base Tous Salariés (all-employees wage database) |
| `FILOSOFI` | Fichier localisé social et fiscal (localized social/fiscal file) |
| `FLORES` | Fichier localisé des rémunérations et de l'emploi salarié (localized wages/employment file) |
| `SIDE` | Système d'information sur la démographie d'entreprises (enterprise demography system) |
| `COM` | Commune |
| `EPCI` | Établissement public de coopération intercommunale (inter-municipal cooperation body) |
| `UL` | Unités légales (legal units) |
| `ET` / `ETAB` | Établissements (establishments) |
| `ENT` | Entreprises (enterprises) |
| `PRINC` | Exploitation principale (primary release) |
| `COMP` | Exploitation complémentaire (complementary release) |
| `LT` | Lieu de travail (place of work) |
| `LR` | Lieu de résidence (place of residence) |
| `EQTP` | Équivalent temps plein (full-time equivalent) |
| `PCS` | Catégorie socioprofessionnelle (socio-professional category) |

## Main inventory

| Local file | Official description (source language) | Use in this project | API / official source |
|---|---|---|---|
| `base-cc-demo-entreprises-2022.zip` | No specific public Melodi endpoint identified; the file's own documentation covers enterprise/establishment demography, 2021 stocks, and 2013-2022 creations | Excel base for territorial analysis by commune and arrondissement | No API mapped in this pass |
| `DS_BPE_2024_CSV_FR.zip` | `Dénombrement des équipements (commerce, sport, services, santé…)` | Measure territorial supply of facilities and services | <https://api.insee.fr/melodi/data/DS_BPE_2024> |
| `DS_BPE_EVOLUTION_2024_CSV_FR.zip` | `Évolution du nombre d'équipements et services` | Track facility/service counts over time by territory | <https://api.insee.fr/melodi/data/DS_BPE_EVOLUTION_2024> |
| `DS_BTS_SAL_EQTP_SEX_AGE_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et l'âge au niveau communal` | Compare private-sector wages by sex and age band | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_AGE_2023> |
| `DS_BTS_SAL_EQTP_SEX_PCS_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et la catégorie socioprofessionnelle au niveau communal` | Compare wages by sex and occupational category | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_PCS_2023> |
| `DS_FILOSOFI_CC_2021_CSV_FR.zip` | `Principaux indicateurs sur la pauvreté en 2021…` | Household income, poverty, and income structure | <https://api.insee.fr/melodi/data/DS_FILOSOFI_CC_2021> |
| `DS_FLORES_A17_2024_CSV_FR.zip` | `Nombre d'établissements et effectifs salariés en 17 grands secteurs` | Productive fabric and salaried employment by broad sector | <https://api.insee.fr/melodi/data/DS_FLORES_A17_2024> |
| `DS_FLORES_ECONOMIC_SPHERE_2024_CSV_FR.zip` | `Nombre d'établissements selon les sphères de l'économie` | Separate presential vs. productive economy by territory | <https://api.insee.fr/melodi/data/DS_FLORES_ECONOMIC_SPHERE_2024> |
| `DS_RP_DIPLOMES_PRINC_2022_CSV_FR.zip` | `Diplômes et Formation` | Educational profile of the resident population | <https://api.insee.fr/melodi/data/DS_RP_DIPLOMES_PRINC_2022> |
| `DS_RP_EMPLOI_LR_COMP_2022_CSV_FR.zip` | `Population active et chômage` | Employment/unemployment at place of residence, complementary breakdown | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_COMP_2022> |
| `DS_RP_EMPLOI_LT_COMP_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Employment structure at place of work, complementary breakdown | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_COMP_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Employment structure at place of work, primary breakdown | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR (1).zip` | Same official description as above; a valid duplicate | Backup/duplicate of the previous dataset | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_NAVETTES_PRINC_2022_CSV_FR.zip` | `Déplacements domicile-travail` | Commuting mobility and transport modes | <https://api.insee.fr/melodi/data/DS_RP_NAVETTES_PRINC_2022> |
| `DS_RP_POPULATION_PRINC_2022_CSV_FR.zip` | `Population` | Resident population volume and age/sex structure | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC_2022> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | No public Melodi endpoint found for the expected identifier in this pass | Enterprise creations by geography, sector, legal form | INSEE catalog: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Same as above | Same theme, alternate package variant | INSEE catalog: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip` | `Créations d'entreprises - séries longues` | Long time series of enterprise creations | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ENT_SERIES> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip` | `Créations d'établissements au niveau communal et supra communal par secteur d'activité (A10) et forme légale` | Establishment creations by geography, sector, legal form | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV.zip` | Same official description as above | Same theme, alternate package variant | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_STOCKS_ET_COM_2022_CSV.zip` | `Stocks d'établissements par activité (A10)` | Active-establishment stock by sector | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2022> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip` | `Stocks d'établissements par activité (A10)` | Active-establishment stock by sector, 2023 | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV.zip` | Same official description as above | Same theme, alternate package variant | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip` | `Stocks d'unités légales par activité (A10)` | Legal-unit stock by sector | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV.zip` | Same official description as above | Same theme, alternate package variant | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Auxiliary code-dictionary file for `SIDE_STOCKS_ET_COM` | Decode `GEO`, `FREQ`, `SIDE_MEASURE`, `TIME_PERIOD`, `ACTIVITY`, `MEASURE` | No own API; auxiliary to the main dataset |

## Territorial complement

Folder: `data/raw/territorial`. Added to complete the project's territorial reference layer.

| Local file | Official description / interpretation | Use in this project | Official source |
|---|---|---|---|
| `fonds_ze2020_2026.zip` | Cartographic base for the 2020 employment zones, updated to the 2026 reference; contains `com_ze2020_2026.zip` and `ze2020_2026.zip` | Geographic base for maps and spatial joins of employment zones and communes | <https://www.insee.fr/fr/statistiques/fichier/4652957/fonds_ze2020_2026.zip> |
| `ZE2020_au_01-01-2026.zip` | Official 2020 employment-zone table as of 2026-01-01; contains `ZE2020_au_01-01-2026.xlsx` | Tabular reference for territorial crosswalks and nomenclature | <https://www.insee.fr/fr/statistiques/fichier/4652957/ZE2020_au_01-01-2026.zip> |
| `table-appartenance-geo-communes-2020.zip` | Commune geographic-membership table; contains `table-appartenance-geo-communes-2020.xlsx` | Link communes to geometries and administrative/statistical zonings | <https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes-2020.zip> |
| `cog_ensemble_2026_csv.zip` | Full 2026 official geographic code (COG) set in CSV; includes `v_commune_2026.csv`, `v_departement_2026.csv`, `v_region_2026.csv`, `v_arrondissement_2026.csv` | Complete geographic reference for official codes, history, and territorial normalization | <https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip> |

**On the original URLs:** three URLs supplied initially returned `HTTP 500` from the INSEE site
on 2026-04-08 and saved HTML instead of the actual file:
`.../4652957/ze2020_shp.zip`, `.../4652957/ze2020_liste_communes.csv`,
`.../7671844/table-appartenance-geo-communes.csv`. The current official replacements above were
kept instead.

## API catalog

### Datasets on hand with a confirmed Melodi endpoint

| Dataset / API | Official title returned by the API | Status |
|---|---|---|
| `DS_BPE_2024` | `Dénombrement des équipements (commerce, sport, services, santé…)` | OK |
| `DS_BPE_EVOLUTION_2024` | `Évolution du nombre d'équipements et services` | OK |
| `DS_BTS_SAL_EQTP_SEX_AGE_2023` | `Salaires dans le secteur privé selon le sexe et l'âge au niveau communal` | OK |
| `DS_BTS_SAL_EQTP_SEX_PCS_2023` | `Salaires dans le secteur privé selon le sexe et la catégorie socioprofessionnelle au niveau communal` | OK |
| `DS_FILOSOFI_CC_2021` | `Principaux indicateurs sur la pauvreté en 2021…` | OK |
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

### On hand without a confirmed Melodi endpoint

| File | Situation |
|---|---|
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | No public Melodi endpoint found with the expected identifier |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Same |
| `base-cc-demo-entreprises-2022.zip` | Outside the `DS_*` naming pattern; no Melodi endpoint mapped |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Auxiliary file, not an independent primary dataset |

### Datasets recoverable via API despite a missing local ZIP

| Dataset / API | Official title | Endpoint |
|---|---|---|
| `DS_RP_EMPLOI_LR_PRINC` | `Population active et chômage` | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC> |
| `DS_RP_POPULATION_COMP` | `Population` | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_COMP> |

Both are recoverable via the API; the natural extraction is paginated JSON, not the original ZIP.
To restore them, query the API and export to CSV.

## Official sources

- INSEE catalog: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche>
- INSEE territorial sources: see the four URLs in "Territorial complement" above.
- INSEE Melodi API: see the endpoint column throughout this document.
