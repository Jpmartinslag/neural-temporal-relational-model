# Raw External Inventory v0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-16

## Purpose

Track which external raw files have actually been processed, partially processed, or left pending.
This prevents overstating conclusions from only a subset of downloaded data.

## Summary

| Family | Status | Files | Size MB |
| :--- | :--- | ---: | ---: |
| `energy` | `not_processed` | 14 | 74.89 |
| `energy` | `processed_subset` | 1 | 73.19 |
| `rei` | `not_processed_xlsx_or_legacy` | 41 | 3039.41 |
| `rei` | `processed_subset` | 2 | 31.26 |
| `sitadel` | `not_processed` | 10 | 98.70 |
| `sitadel` | `processed` | 1 | 85.65 |
| `sitadel` | `too_heavy_pending` | 3 | 4299.68 |

## Priority Queue

| Priority | Status | Size MB | File | Reason |
| :--- | :--- | ---: | :--- | :--- |
| `high` | `too_heavy_pending` | 3195.77 | `data/raw/external/sitadel/Donnees-mensuelles-communales-Locaux.2026-03.csv` | 3GB monthly communal data may provide stronger temporal signals |
| `high` | `not_processed_xlsx_or_legacy` | 127.16 | `data/raw/external/rei/REI-2018-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `high` | `not_processed_xlsx_or_legacy` | 124.49 | `data/raw/external/rei/REI-2020-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `high` | `not_processed_xlsx_or_legacy` | 120.04 | `data/raw/external/rei/REI-2019-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `high` | `not_processed_xlsx_or_legacy` | 109.67 | `data/raw/external/rei/REI-2022-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `high` | `not_processed_xlsx_or_legacy` | 105.41 | `data/raw/external/rei/REI-2021-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `high` | `not_processed` | 34.39 | `data/raw/external/energy/Donnees-locales-de-consommation-denergie-periode-2008-2017-electricite.2017-12.csv` | can extend energy temporal depth before 2018 |
| `high` | `not_processed` | 15.43 | `data/raw/external/energy/Donnees-locales-de-consommation-denergie-periode-2008-2017-gaz.2017-12.csv` | can extend energy temporal depth before 2018 |
| `high` | `not_processed` | 12.64 | `data/raw/external/energy/Données locales de consommation d'électricité, de gaz naturel et de chaleur et de froid (période 2008-2017).zip` | can extend energy temporal depth before 2018 |
| `high` | `not_processed` | 0.92 | `data/raw/external/energy/Donnees-locales-de-consommation-denergie-periode-2008-2017-chaleur-et-froid.2017-12.csv` | can extend energy temporal depth before 2018 |
| `medium` | `too_heavy_pending` | 828.82 | `data/raw/external/sitadel/Liste-des-autorisations-durbanisme-creant-des-logements.2026-04.csv` | event-level permits may help but require aggregation design |
| `medium` | `too_heavy_pending` | 275.09 | `data/raw/external/sitadel/Liste-des-autorisations-durbanisme-creant-des-locaux-non-residentiels.2026-04.csv` | event-level permits may help but require aggregation design |
| `medium` | `not_processed_xlsx_or_legacy` | 112.49 | `data/raw/external/rei/REI-2015-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 111.25 | `data/raw/external/rei/REI-2013-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 109.99 | `data/raw/external/rei/REI-2014-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 109.25 | `data/raw/external/rei/REI-2016-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 103.77 | `data/raw/external/rei/REI-2008-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 99.07 | `data/raw/external/rei/REI-2007-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 98.27 | `data/raw/external/rei/REI-2006-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 89.98 | `data/raw/external/rei/REI-2017-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 87.82 | `data/raw/external/rei/REI-2001-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 87.66 | `data/raw/external/rei/REI-2000-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 87.50 | `data/raw/external/rei/REI-2005-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 86.78 | `data/raw/external/rei/REI-1999-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 84.14 | `data/raw/external/rei/REI-2002-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 80.38 | `data/raw/external/rei/REI-2004-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 76.77 | `data/raw/external/rei/REI-1997-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 73.33 | `data/raw/external/rei/REI-2003-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 71.76 | `data/raw/external/rei/REI-1996-fichier-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |
| `medium` | `not_processed_xlsx_or_legacy` | 70.33 | `data/raw/external/rei/REI-2012-fichier-notice-trace.zip` | requires controlled conversion/extraction before REI can be evaluated over time |

## Current Interpretation

- Current negative results for SITADEL, REI, and Energy apply only to processed subsets and raw lagged-level forms.
- The largest unprocessed item is the SITADEL monthly communal file, which may contain stronger short-term dynamics.
- REI is mostly unprocessed historically because older files require controlled XLSX extraction/conversion.
- Energy pre-2018 is unprocessed and may matter for temporal depth.
