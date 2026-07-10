# France ZE2020 top-3 entry relation-lift HPC

Purpose: test whether the HERALD_36 target-aligned relation-lift features survive
the same falsification structure used for HERALD_34/35.

This package is exploratory only:

- no final model promotion;
- no causal claim;
- no automatic recommendation claim;
- no overwrite of canonical processed data.

Dry run:

```bash
bash hpc/france_ze2020_top3_entry_lift/submit_fr_ze2020_top3_entry_lift_hpc.sh
```

Real submit:

```bash
bash hpc/france_ze2020_top3_entry_lift/submit_fr_ze2020_top3_entry_lift_hpc.sh --confirm-submit
```

Audit after collection:

```bash
python hpc/france_ze2020_top3_entry_lift/audit_fr_ze2020_top3_entry_lift_hpc_results.py \
  hpc_results/fr_ze2020_top3_entry_lift_<RUN_ID> \
  --out hpc_results/fr_ze2020_top3_entry_lift_<RUN_ID>/fr_ze2020_top3_entry_lift_hpc_audit_report.json
```
