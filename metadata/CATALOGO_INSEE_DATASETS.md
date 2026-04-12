# Catalogo INSEE para uso no projeto

Data da catalogacao: 2026-04-08
Diretorio: `/home/jpdark/Downloads/project_recomm/dataset`

## Estado atual

- Total de arquivos `.zip` atuais: 26
- ZIPs corrompidos restantes: 0
- Todos os arquivos listados abaixo passaram em `unzip -t`
- As descricoes abaixo priorizam a fonte oficial na internet:
  - API Melodi do INSEE, quando o dataset possui endpoint
  - documentacao interna do proprio arquivo, quando nao encontrei endpoint publico equivalente
- Complemento territorial adicionado em `data/raw/territorial`

## Siglas principais

- `RP`: Recensement de la population
- `BPE`: Base permanente des equipements
- `BTS`: Base Tous Salaries
- `FILOSOFI`: Fichier localise social et fiscal
- `FLORES`: Fichier localise des remunerations et de l'emploi salarie
- `SIDE`: Systeme d'information sur la demographie d'entreprises
- `COM`: commune
- `EPCI`: etablissement public de cooperation intercommunale
- `UL`: unites legales
- `ET` / `ETAB`: etablissements
- `ENT`: entreprises
- `PRINC`: exploitation principale
- `COMP`: exploitation complementaire
- `LT`: lieu de travail
- `LR`: lieu de residence
- `EQTP`: equivalent temps plein
- `PCS`: categorie socioprofessionnelle

## Inventario principal

| Arquivo local | Descricao oficial na internet | Para que serve no projeto | API / fonte oficial |
|---|---|---|---|
| `base-cc-demo-entreprises-2022.zip` | Nao identifiquei endpoint Melodi publico especifico; a documentacao interna do arquivo indica demografia de empresas e estabelecimentos, estoques em 2021 e criacoes de 2013 a 2022 | Base Excel pronta para analise territorial por commune e arrondissement municipal | Sem API mapeada nesta rodada |
| `DS_BPE_2024_CSV_FR.zip` | `Dénombrement des équipements (commerce, sport, services, santé…)` | Medir oferta territorial de equipamentos e servicos | <https://api.insee.fr/melodi/data/DS_BPE_2024> |
| `DS_BPE_EVOLUTION_2024_CSV_FR.zip` | `Évolution du nombre d'équipements et services` | Analisar evolucao temporal de equipamentos por territorio | <https://api.insee.fr/melodi/data/DS_BPE_EVOLUTION_2024> |
| `DS_BTS_SAL_EQTP_SEX_AGE_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et l'âge au niveau communal` | Comparar salarios do setor privado por sexo e faixa etaria | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_AGE_2023> |
| `DS_BTS_SAL_EQTP_SEX_PCS_2023_CSV_FR.zip` | `Salaires dans le secteur privé selon le sexe et la catégorie socioprofessionnelle au niveau communal` | Comparar salarios por sexo e categoria ocupacional | <https://api.insee.fr/melodi/data/DS_BTS_SAL_EQTP_SEX_PCS_2023> |
| `DS_FILOSOFI_CC_2021_CSV_FR.zip` | `Principaux indicateurs sur la pauvreté en 2021 : niveau de vie, taux de pauvreté, part des ménages imposés et décomposition du revenu disponible` | Medir renda, pobreza e estrutura do rendimento dos domicilios | <https://api.insee.fr/melodi/data/DS_FILOSOFI_CC_2021> |
| `DS_FLORES_A17_2024_CSV_FR.zip` | `Nombre d'établissements et effectifs salariés en 17 grands secteurs` | Medir tecido produtivo e emprego assalariado por grandes setores | <https://api.insee.fr/melodi/data/DS_FLORES_A17_2024> |
| `DS_FLORES_ECONOMIC_SPHERE_2024_CSV_FR.zip` | `Nombre d'établissements selon les sphères de l'économie` | Separar economia presentielle e productive por territorio | <https://api.insee.fr/melodi/data/DS_FLORES_ECONOMIC_SPHERE_2024> |
| `DS_RP_DIPLOMES_PRINC_2022_CSV_FR.zip` | `Diplômes et Formation` | Perfil educacional da populacao residente | <https://api.insee.fr/melodi/data/DS_RP_DIPLOMES_PRINC_2022> |
| `DS_RP_EMPLOI_LR_COMP_2022_CSV_FR.zip` | `Population active et chômage` | Emprego e desemprego no lugar de residencia, com granularidade complementar | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_COMP_2022> |
| `DS_RP_EMPLOI_LT_COMP_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Estrutura do emprego no lugar de trabalho, exploracao complementar | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_COMP_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR.zip` | `Emploi au lieu de travail` | Estrutura principal do emprego no lugar de trabalho | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_EMPLOI_LT_PRINC_2022_CSV_FR (1).zip` | Mesma descricao oficial do arquivo anterior; e uma duplicata valida | Backup/duplicata do dataset anterior | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LT_PRINC_2022> |
| `DS_RP_NAVETTES_PRINC_2022_CSV_FR.zip` | `Déplacements domicile-travail` | Mobilidade pendular, deslocamento casa-trabalho e modos de transporte | <https://api.insee.fr/melodi/data/DS_RP_NAVETTES_PRINC_2022> |
| `DS_RP_POPULATION_PRINC_2022_CSV_FR.zip` | `Population` | Volume e estrutura etaria/sexo da populacao residente | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_PRINC_2022> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | Nao encontrei endpoint Melodi publico correspondente ao identificador esperado nesta rodada | Criacoes de empresas por geografia, setor e forma legal | Catalogo INSEE: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Nao encontrei endpoint Melodi publico correspondente ao identificador esperado nesta rodada | Mesmo tema acima em outra variante do pacote | Catalogo INSEE: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche> |
| `DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip` | `Créations d'entreprises - séries longues` | Series temporais longas de criacoes de empresas | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ENT_SERIES> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV_FR.zip` | `Créations d'établissements au niveau communal et supra communal par secteur d'activité (A10) et forme légale` | Criacoes de estabelecimentos por geografia, setor e forma juridica | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_CREA_ETAB_COM_2024_CSV.zip` | Mesma descricao oficial do arquivo anterior | Mesmo tema acima em outra variante do pacote | <https://api.insee.fr/melodi/data/DS_SIDE_CREA_ETAB_COM_2024> |
| `DS_SIDE_STOCKS_ET_COM_2022_CSV.zip` | `Stocks d'établissements par activité (A10)` | Estoque de estabelecimentos ativos por setor | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2022> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip` | `Stocks d'établissements par activité (A10)` | Estoque de estabelecimentos ativos por setor em 2023 | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_ET_COM_2023_CSV.zip` | Mesma descricao oficial do arquivo anterior | Mesmo tema acima em outra variante do pacote | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_ET_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip` | `Stocks d'unités légales par activité (A10)` | Estoque de unidades legais por setor | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `DS_SIDE_STOCKS_UL_COM_2023_CSV.zip` | Mesma descricao oficial do arquivo anterior | Mesmo tema acima em outra variante do pacote | <https://api.insee.fr/melodi/data/DS_SIDE_STOCKS_UL_COM_2023> |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Arquivo auxiliar de dicionarios de codigo para `SIDE_STOCKS_ET_COM` | Decodificar `GEO`, `FREQ`, `SIDE_MEASURE`, `TIME_PERIOD`, `ACTIVITY`, `MEASURE` | Sem API propria; auxiliar do dataset principal |

## Complemento territorial

Pasta: [data/raw/territorial](/home/jpdark/Downloads/project_recomm/dataset/data/raw/territorial)

Esses arquivos foram adicionados para completar a camada territorial do projeto.

| Arquivo local | Descricao oficial / interpretacao | Para que serve no projeto | Fonte oficial |
|---|---|---|---|
| `data/raw/territorial/fonds_ze2020_2026.zip` | Fundo cartografico das zones d'emploi 2020, atualizado para referencia 2026; contem `com_ze2020_2026.zip` e `ze2020_2026.zip` | Base geografica para mapas e joins espaciais de zones d'emploi e comunas | <https://www.insee.fr/fr/statistiques/fichier/4652957/fonds_ze2020_2026.zip> |
| `data/raw/territorial/ZE2020_au_01-01-2026.zip` | Tabela oficial das zones d'emploi 2020 ao estado de 01/01/2026; contem `ZE2020_au_01-01-2026.xlsx` | Referencial tabular das zones d'emploi para cruzamento territorial e nomenclatura | <https://www.insee.fr/fr/statistiques/fichier/4652957/ZE2020_au_01-01-2026.zip> |
| `data/raw/territorial/table-appartenance-geo-communes-2020.zip` | Tabela de pertencimento geografico das comunas; contem `table-appartenance-geo-communes-2020.xlsx` | Relacionar comunas a geometrias e zonagens administrativas/estatisticas | <https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes-2020.zip> |
| `data/raw/territorial/cog_ensemble_2026_csv.zip` | COG 2026 completo em CSV; contem tabelas como `v_commune_2026.csv`, `v_departement_2026.csv`, `v_region_2026.csv`, `v_arrondissement_2026.csv` | Referencial geografico completo para codigos oficiais, historico e normalizacao territorial | <https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip> |

### Observacao sobre as URLs antigas

As tres URLs abaixo, fornecidas inicialmente, retornaram `HTTP 500` no site do INSEE em 2026-04-08 e salvaram HTML em vez do arquivo real:

- `https://www.insee.fr/fr/statistiques/fichier/4652957/ze2020_shp.zip`
- `https://www.insee.fr/fr/statistiques/fichier/4652957/ze2020_liste_communes.csv`
- `https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes.csv`

Por isso, no catalogo e no diretorio foram mantidas as versoes oficiais atuais ainda disponiveis no INSEE:

- `fonds_ze2020_2026.zip`
- `ZE2020_au_01-01-2026.zip`
- `table-appartenance-geo-communes-2020.zip`

## Catalogo das APIs identificadas

### APIs de datasets presentes localmente

| Dataset/API | Titulo oficial retornado pela API | Status |
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

### Datasets locais sem endpoint Melodi confirmado nesta rodada

| Arquivo | Situacao |
|---|---|
| `DS_SIDE_CREA_ENT_COM_2024_CSV_FR.zip` | Nao encontrei endpoint Melodi publico com o identificador esperado |
| `DS_SIDE_CREA_ENT_COM_2024_CSV.zip` | Nao encontrei endpoint Melodi publico com o identificador esperado |
| `base-cc-demo-entreprises-2022.zip` | Arquivo fora do padrao `DS_*`; sem endpoint Melodi mapeado |
| `Listes de codes DS_SIDE_STOCKS_ET_COM.zip` | Arquivo auxiliar, nao e um dataset principal independente |

## APIs de recuperacao de datasets que estavam corrompidos

Estes dois datasets nao estao mais presentes como ZIP valido local, mas a API respondeu corretamente e permite recuperar os dados em JSON paginado:

| Dataset/API | Titulo oficial | Endpoint |
|---|---|---|
| `DS_RP_EMPLOI_LR_PRINC` | `Population active et chômage` | <https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC> |
| `DS_RP_POPULATION_COMP` | `Population` | <https://api.insee.fr/melodi/data/DS_RP_POPULATION_COMP> |

Conclusao tecnica:

- Sim, esses dois podem ser recuperados via API
- A recuperacao natural e em JSON, nao no mesmo ZIP original
- Se voce quiser repor esses datasets no projeto, o caminho correto e consumir a API e exportar para CSV

## Fontes oficiais usadas

- Catalogo do INSEE: <https://catalogue-donnees.insee.fr/fr/catalogue/recherche>
- Fontes territoriais do INSEE:
  - <https://www.insee.fr/fr/statistiques/fichier/4652957/fonds_ze2020_2026.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/4652957/ZE2020_au_01-01-2026.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/7671844/table-appartenance-geo-communes-2020.zip>
  - <https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip>
- API Melodi do INSEE:
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
