# BPE 2020 Hard Search V0

Date: 2026-04-11

## Objective

Find a usable national `BPE 2020 Ensemble` file to close the last temporal-depth gap in the annual panel.

## Confirmed Historical Identifier

The historical `DoReMIFaSol` catalogue confirms the exact former Insee reference:

- `BPE_ENS`
- `date_ref = 2020-01-01`
- `lien = https://www.insee.fr/fr/statistiques/fichier/3568629/bpe20_ensemble_csv.zip`
- `fichier_donnees = bpe20_ensemble.csv`
- `md5 = cb6d338744040af5e3cbe2d3b27ccead`
- `size = 5147269`

This is useful as a reference, but the live Insee URL now returns `404`.

## Sources Checked

### Insee

- `https://www.insee.fr/fr/metadonnees/source/operation/s2027/bases-donnees-ligne`
- `https://www.insee.fr/fr/statistiques/fichier/3568629/bpe20_ensemble_csv.zip`
- `https://www.insee.fr/fr/statistiques/fichier/3568638/bpe20_ensemble_xy_csv.zip`

Result:

- official documentation confirms the existence of `BPE 2020 Ensemble`
- direct historical data URL is no longer alive

### DoReMIFaSol Historical Catalogue

Checked old commits of `InseeFrLab/DoReMIFaSol`:

- commit `1b6397db07b5fe1022ccb50b25eef1bfb628ad23`
- commit `64b3a1b6847422b07a872be04b39991f55c479dc`

Result:

- confirms the exact Insee historical URL and checksum
- does not provide a surviving mirror of the file

### Internet Archive

Checked CDX snapshots for:

- `https://www.insee.fr/fr/statistiques/fichier/3568629/bpe20_ensemble_csv.zip`
- `https://www.insee.fr/fr/statistiques/fichier/3568638/bpe20_ensemble_xy_csv.zip`

Result:

- no archived `200` snapshot was found

### data.gouv.fr

Checked:

- `https://www.data.gouv.fr/datasets/base-permanente-des-equipements`
- resource `63a7a69c-0155-4a8e-a73b-2009ee92eda2`

Downloaded candidate:

- `data/raw/temporal_depth/bpe/data_gouv_bpe_2020_candidate.csv`

Validation result:

- file size: `156M`
- schema: `Année`, `Code INSEE`, `Nombre`, equipment labels
- contained years: `2011`, `2012`
- `2020` rows: `0`

Decision:

- reject as `BPE 2020` source
- despite the `2020-08-19` data.gouv resource date, its content is not `BPE 2020`

## Rejected Local Candidates

- `bpe20_ensemble_csv.zip`: HTML error page saved as `.zip`
- `bpe19_bfc.zip`: regional `BPE 2019` shapefile for Bourgogne-Franche-Comté
- `bpe-ensemble.csv`: multi-year table with `2011` and `2012`, not `2020`
- `data_gouv_bpe_2020_candidate.csv`: data.gouv/Huwise resource, also only `2011` and `2012`

## Current Status

`BPE 2020 Ensemble` remains unresolved.

What is known:

- the exact historical file name was `bpe20_ensemble_csv.zip`
- the expected internal data file was `bpe20_ensemble.csv`
- the expected checksum was `cb6d338744040af5e3cbe2d3b27ccead`
- the old Insee URL is no longer alive
- no verified mirror was found in this search

## Practical Consequence

The project should not mark `BPE 2020` as closed until a file containing `AN = 2020`, `DEPCOM`, `TYPEQU`, and `NB_EQUIP` is obtained.

If the file cannot be recovered, the next defensible option is to proceed without `BPE 2020` and document it as an unavailable historical source.
