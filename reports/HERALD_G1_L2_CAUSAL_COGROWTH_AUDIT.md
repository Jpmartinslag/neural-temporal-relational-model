# HERALD G1-L2 Causal Co-Growth Graph Audit

**Decision:** `PASS`
**Layer:** `L2_same_sector_cross_territory_cogrowth`

L2 edges connect territory pairs within the same sector based on
Pearson correlation of their past sector growth rates over a rolling
window of 5 years.  Only data from observation_year
<= t-1 is used (causal temporal protocol).

## PT KZ note

PT sector KZ is structurally absent from INE indicator 0009703 (section K not published in enterprise demography statistics). This is a verified definitional exclusion per DEC-015. PT participates in L2 with 8 sectors.

## Validation (full window including 2020)

| Country | Sectors | Eval years | Stability | Temporal q | Territory q | LOYO | Stable edges | Pass |
|---|---|---|---:|---:|---:|---|---:|---|
| FR | 9 | 2017-2026 | 0.7824 | 0.0050 | 0.0050 | True | 13 | True |
| NL | 9 | 2012-2026 | 0.7893 | 0.0050 | 0.0050 | True | 19 | True |
| PT | 8 | 2013-2025 | 0.7778 | 0.0050 | 0.0050 | True | 22 | True |

Countries passing: 3/2 required.

## COVID sensitivity (2020 excluded from all windows)

| Country | Eval years | Stability | Temporal q | Territory q | Pass |
|---|---|---:|---:|---:|---|
| FR | 2017-2026 | 0.7102 | 0.0050 | 0.0050 | True |
| NL | 2012-2026 | 0.7418 | 0.0050 | 0.0050 | True |
| PT | 2013-2025 | 0.7130 | 0.0050 | 0.0050 | True |

## Scope

- PASS validates L2 co-growth as an analytically stable layer.
- Correlation edges are statistical associations, not economic causality.
- Granger predictability must not be inferred from Pearson co-growth.
- L4 mobility and L5 geography remain unvalidated.
- This result does not authorize GNN training, forecast integration
  or economic recommendation.
- Dashboard work remains deferred per DEC-014.
