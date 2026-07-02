# France ZE2020 Dynamic Graph HPC

HPC launcher for the HERALD_25 dynamic graph ranker smoke and falsification block.

This is exploratory only:

- no causal claim;
- no automatic recommendation;
- no validated dynamic graph model claim;
- no overwrite of canonical input CSVs.

Default target:

```text
target_horizon=1
seeds=42..46
edges=data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges.csv
```

To test the expanding edge-memory graph, export:

```bash
export FR_ZE2020_DYNAMIC_GRAPH_EDGES=data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
```

Submit scripts are dry-run by default. Real submission requires `--confirm-submit`.
