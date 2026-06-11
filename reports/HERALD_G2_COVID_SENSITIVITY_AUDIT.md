# HERALD G2 COVID Sensitivity Audit

**Date:** 2026-06-11  
**Decision:** `COVID_SENSITIVE` globally; `COVID_ROBUST` only for FR  
**Scope:** G2 aggregate temporal-Jaccard signal; no individual-edge claim

## Protocol

Two complete corrected-control runs were executed with identical parameters:
199 N1 temporal permutations, 199 N2 row-wise territory permutations, seeds
42/137, top-k=5, rolling window 5 and minimum 4 observations.

- Main scenario: `observation_year=2020` included.
- Sensitivity scenario: only `observation_year=2020` excluded from rolling
  windows. `available_for_forecast_year=2020` remains because its window uses
  pre-2020 observations.

COVID receives no feature, loss, metric or sampling weight. The only difference
between scenarios is whether the 2020 observation participates in later
rolling windows.

## Country Decisions

| Country | Sectors passing with 2020 | Sectors passing without 2020 | Changed sectors | Classification |
|---|---:|---:|---|---|
| FR | 9/9 | 9/9 | none | `COVID_ROBUST` |
| NL | 4/9 | 5/9 | BE, LZ, RU | `COVID_SENSITIVE` |
| PT | 4/8 | 0/8 | BE, GI, JZ, LZ | `COVID_SENSITIVE` |

The global 2/3 gate passes in both scenarios, but not with the same countries:
FR+PT pass when 2020 is included; FR+NL pass when it is excluded. Therefore,
there is no COVID-robust two-country replication.

## Metric Changes

Mean change after excluding observation year 2020:

| Country | Delta M1 consecutive Jaccard | Delta M2 pairwise Jaccard |
|---|---:|---:|
| FR | -0.0228 | -0.0090 |
| NL | -0.0008 | -0.0029 |
| PT | -0.0198 | -0.0130 |

Seven of 26 country-sector decisions change. The detailed p/q values and metric
changes are in `g2_covid_comparison.csv`.

## G1-L2 versus G2

These results are not contradictory:

| Evidence | Object | Metric | Interpretation |
|---|---|---|---|
| G1-L2 (about 0.78) | Dense matrices containing all territory-pair Pearson weights | Correlation/stability of dense weight vectors | The overall weight field changes smoothly |
| G2 M1/M2 (0.06-0.28) | Sparse binary top-k=5 graphs per sector | Jaccard identity of selected edges | The identity of strongest links is volatile |

G1-L2 must not be described as proving stable individual edges. G2 explicitly
rejects that claim.

## Authorized Claims

- FR has aggregate temporal coherence above both null families that is robust
  to including or excluding observation year 2020.
- NL and PT results are COVID-sensitive under the pre-registered country gate.
- Dense co-growth weight structure and sparse top-k edge identity measure
  different properties.

## Prohibited Claims

- COVID caused any graph change.
- NL or PT has a generally validated temporal signal.
- Individual top-k edges are stable.
- The graph encodes economic causality or supports recommendation.

