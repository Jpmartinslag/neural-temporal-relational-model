# France ZE2020 Top-3 Entry HPC

HPC package for the HERALD_33 top-3 entry falsification batch.

This batch is exploratory only:

- no causal claim;
- no automatic recommendation;
- no dynamic-GNN/model promotion by submission alone.

Default design:

```text
4 scenarios x 5 seeds = 20 Slurm tasks
scenarios = full_control temporal_shuffle sector_shuffle target_shuffle
seeds     = 42 43 44 45 46
target    = future_top3_entry_3y_label
years     = 2017..2022
```

Submitter is dry-run by default:

```bash
bash hpc/france_ze2020_top3_entry/submit_fr_ze2020_top3_entry_hpc.sh
```

Real submission requires:

```bash
bash hpc/france_ze2020_top3_entry/submit_fr_ze2020_top3_entry_hpc.sh --confirm-submit
```
