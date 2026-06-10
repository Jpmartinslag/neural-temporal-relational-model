# HERALD G1-L2 Causal Co-Growth Graph Audit

**Decision:** `PASS`
**COVID classification:** `COVID_ROBUST`
**Layer:** `L2_same_sector_cross_territory_cogrowth`

L2 edges connect territory pairs within the same sector based on
Pearson correlation of their past sector growth rates over a rolling
window of 5 years (min 4 periods).
Only observation_year <= t-1 is used (causal temporal protocol).

## PT KZ note

PT sector KZ is structurally absent from INE indicator 0009703 (section K not published in enterprise demography statistics). Verified definitional exclusion per DEC-018. PT participates in L2 with 8 sectors.

## COVID sensitivity note

COVID sensitivity excludes observation year 2020 from all windows. eval_year=2020 is retained: its window covers [2015..2019] which predates the shock. Windows spanning 2020 lose one year but remain >= 4 periods. Classification: COVID_ROBUST.

## Validation (full window, 2020 included as observation year)

Gate: temporal q ≤ 0.05, territory q ≤ 0.05, LOYO direction pass, ≥ 1 stable bootstrap edge.

| Country | Sectors | Eval years | Stability | Temporal q | Territory q | LOYO | Stable edges | Pass |
|---|---|---|---:|---:|---:|---|---:|---|
| FR | 9 | 2017-2026 | 0.7824 | 0.0050 | 0.0050 | True | 13 | True |
| NL | 9 | 2012-2026 | 0.7893 | 0.0050 | 0.0050 | True | 19 | True |
| PT | 8 | 2013-2025 | 0.7778 | 0.0050 | 0.0050 | True | 22 | True |

Countries passing: 3/2 required.

## COVID sensitivity (2020 excluded from observation windows)

eval_year=2020 is retained (window covers pre-COVID years). Windows containing 2020 lose that year but remain ≥ min_periods. Same full gate applied.

| Country | Eval years | Gaps | Stability | Temporal q | Territory q | LOYO | Stable edges | Pass |
|---|---|---|---:|---:|---:|---|---:|---|
| FR | 2017-2026 | 2020 | 0.7440 | 0.0050 | 0.0050 | True | 11 | True |
| NL | 2012-2026 | 2020 | 0.7622 | 0.0050 | 0.0050 | True | 19 | True |
| PT | 2013-2025 | 2020 | 0.7379 | 0.0050 | 0.0050 | True | 22 | True |

## Scope

- PASS validates L2 co-growth as an analytically stable layer.
- Correlation edges are statistical associations, not economic causality.
- Granger predictability must not be inferred from Pearson co-growth.
- L4 mobility and L5 geography remain unvalidated.
- This result does not authorize GNN training, forecast integration
  or economic recommendation.
- Dashboard work remains deferred per DEC-014.
