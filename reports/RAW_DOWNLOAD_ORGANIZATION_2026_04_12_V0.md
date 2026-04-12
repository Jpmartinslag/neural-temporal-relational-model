# Raw Download Organization 2026-04-12 v0

## Summary

- `kept_root`: 3
- `moved`: 210
- `moved_name_collision`: 1
- `removed_duplicate`: 11

## Rule

Only root-level raw/download files were moved or removed. Processed, interim, report, metadata and source-code trees were not cleaned by this script.
A file was removed only when an identical copy was already present at the destination or when it was a byte-identical duplicate of a preferred root file.

## Manifest

- `metadata/raw_download_organization_2026_04_12_v0.csv`


## Post-Organization Duplicate Cleanup

Removed 4 additional byte-identical duplicates inside `data/raw` after the root cleanup:

- `data/raw/temporal_depth/bpe/bpe-ensemble.csv` duplicated `data/raw/temporal_depth/bpe/data_gouv_bpe_2020_candidate.csv`.
- `data/raw/temporal_depth/bpe/BPE_evol_1924_description_sources.html` duplicated the copy in `data/raw/temporal_depth/bpe/docs/`.
- `data/raw/temporal_depth/bpe/BPE_evol_1924_precautions_utilisation_TYPEQU.html` duplicated the copy in `data/raw/temporal_depth/bpe/docs/`.
- `data/raw/temporal_depth/bpe/BPE_evol_1924_liste_a_plat_TYPEQU.html` duplicated the copy in `data/raw/temporal_depth/bpe/docs/`.

## Mislabelled BPE File

Moved `data/raw/temporal_depth/bpe/DS_BPE_2023_CSV_FR__root_duplicate.zip` to `data/raw/temporal_depth/bpe/rejected/DS_BPE_2023_CSV_FR_mislabelled_2024_rejected.zip` because its archive members are `DS_BPE_2024_metadata.csv` and `DS_BPE_2024_data.csv`, not BPE 2023.
