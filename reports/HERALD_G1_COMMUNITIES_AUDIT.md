# HERALD G1 Community Detection Audit

**Decision:** `FAIL`
**COVID sensitivity:** `COVID_SENSITIVE`

Communities are calculated on a symmetric top-k=5 L2 graph rebuilt
from causal sector-growth windows. Observed and null graphs use the
same Louvain restart budget. Nulls are reconstructed from permuted
growth series; node relabeling is not used.

## Main validation

| Country | Years | Nodes | Edges | Communities | Modularity | AMI | Mod temp q | Mod terr q | AMI temp q | AMI terr q | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| FR | 2017,2018,2019,2020,2021,2022,2023,2024,2025,2026 | 280.0 | 939.5 | 10.40 | 0.3934 | 0.0394 | 0.5400 | 0.4200 | 0.0400 | 0.0720 | False |
| NL | 2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026 | 40.0 | 138.5 | 5.00 | 0.3042 | 0.0847 | 1.0000 | 1.0000 | 0.4800 | 0.7440 | False |
| PT | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025 | 25.0 | 85.5 | 3.77 | 0.2784 | 0.2936 | 0.5867 | 0.0720 | 0.0400 | 0.0400 | False |

## COVID sensitivity

The observation year 2020 is removed from every rolling window, while
evaluation year 2020 remains because its window uses only pre-COVID data.

| Country | Years | Modularity | AMI | Pass |
|---|---|---:|---:|---|
| FR | 2017,2018,2019,2020,2021,2022,2023,2024,2025,2026 | 0.4020 | 0.0421 | False |
| NL | 2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026 | 0.3026 | 0.1419 | False |
| PT | 2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025 | 0.2788 | 0.2452 | False |

## Scope

- PASS requires modularity and consecutive-year AMI to exceed both null families after BH/FDR.
- Communities are statistical co-growth clusters, not production districts.
- Positive top-k sparsification is fixed before evaluation and applied identically to nulls.
- No GNN, forecast improvement, causal relation or recommendation is validated here.
