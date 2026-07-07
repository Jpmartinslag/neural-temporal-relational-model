# France ZE2020 Relation Objective HPC

HPC falsification batch for the HERALD_27 relation objective.

Purpose:

- compare the local compatibility learner against deterministic relation formulas;
- repeat across seeds and relation controls;
- audit lift over formula baselines and degradation under temporal/sector placebos.

This is exploratory only:

- no causal claim;
- no automatic recommendation;
- no validated dynamic graph model claim;
- no overwrite of canonical input CSVs.

Default batch:

```text
seeds=42..46
target=new_relation
node_feature_lag=1
eval_years=2017..2025
feature_family=sector_position_no_rank
pair_feature_mode=compatibility_only
```

Submit scripts are dry-run by default. Real submission requires `--confirm-submit`.
