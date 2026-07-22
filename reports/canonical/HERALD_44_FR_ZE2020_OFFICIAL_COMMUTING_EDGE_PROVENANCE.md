# HERALD 44 -- France ZE2020 official commuting-edge provenance

**Date:** 2026-07-22  
**Status:** `RELATION_SOURCE_READY_NOT_MODEL_INPUT`  
**Decision:** `DEC-073`

## 1. Question

Can the unverified legacy France mobility matrix be replaced by a reproducible,
directed ZE2020 relation source with explicit economic meaning and temporal
availability?

The relation tested here is not generic similarity. It is the estimated number
of employed residents of source ZE `i` whose declared workplace is in target
ZE `j`. It measures commuters, not trip frequency.

## 2. Legacy audit

`data/processed/graph_adjacency_mobility_v0.csv` remains forbidden. Its
generator is absent. A temporary reconstruction from the official 2017 source,
with self-flows removed and rows normalized, is highly similar but not
identical:

- Pearson correlation over the 280 x 280 matrix: `0.99145`;
- mean absolute difference: `0.00057`;
- maximum absolute difference: `0.19498`;
- the largest discrepancies include flows towards Paris and Marseille.

Similarity does not recover provenance. The old matrix remains historical and
is not read by the new builder.

## 3. Official sources

| Observation | Release | Source geography | Raw rows | INSEE product |
|---:|---:|---:|---:|---|
| 2012 | 2015-06-25 | 2014-01-01 | 1,022,879 | commune residence-to-workplace flows |
| 2017 | 2020-12-09 | 2020-01-01 | 955,878 | commune residence-to-workplace flows |
| 2023 | 2026-06-25 | 2026-01-01 | 1,003,647 | commune residence-to-workplace flows |

Every URL and SHA-256 is pinned in
`src/data/france_ze2020/build_fr_ze2020_commuting_edges.py` and repeated in
`fr_ze2020_commuting_edge_summary.json`. Commune changes are resolved with
the official INSEE COG 2026 event file. Paris, Lyon, and Marseille
arrondissements are collapsed to their parent commune before the ZE2020 join.

## 4. Construction

For snapshot `s`, commune flow `f_uvs`, source commune `u`, and workplace
commune `v`:

```text
F_ijs = sum f_uvs, for u in ZE i and v in ZE j
```

Three non-interchangeable weights are retained:

```text
origin_worker_share       = F_ijs / all workers resident in ZE i
origin_in_scope_share     = F_ijs / workers from ZE i with a workplace in the 280-ZE scope
origin_interze_share      = F_ijs / cross-ZE workers from ZE i, for i != j
```

`origin_interze_share` sums to one across non-self targets for each source and
snapshot. Self-flows remain explicit and receive
`origin_interze_share = 0`; a later graph builder must decide whether to use
them as self-loops.

## 5. Two temporal clocks

Observation year and publication availability are not treated as the same
thing.

| Snapshot | Observation-time validity | Strict ex-ante validity |
|---:|---:|---:|
| 2012 | 2013--2017 | 2016--2020 |
| 2017 | 2018--2023 | 2021--2026 |
| 2023 | 2024 onward | 2027 onward |

The strict ex-ante clock starts in the year after publication because the
annual decision is assumed to be made before a mid-year release. Therefore the
2023 snapshot is descriptive for 2024--2025 but is forbidden as a strict
ex-ante input for those years.

## 6. Output audit

Meso job `7780907` completed in 33 seconds with exit `0:0` and empty stderr.

- output: 86,568 directed edge-snapshot rows;
- 280/280 source and target ZEs in every snapshot;
- source code resolution coverage: 99.966% (2012), 99.978% (2017), 99.999% (2023);
- in-scope pair share of national flow: 95.943% (2012), 95.692% (2017), 95.461% (2023);
- 8/8 direct tests pass in the Meso `herald-v5` environment;
- raw caches are regenerable and gitignored;
- the compressed edge table is regenerable and not tracked;
- the small provenance summary is tracked.

## 7. Source cautions

INSEE states that:

- the quantity is a number of commuters, not a number of trips;
- collection is spread across years, so incoming and outgoing flows are not
  always observed at the same date;
- small flows below 200 should be treated as orders of magnitude;
- temporal comparisons are safer at five-year intervals, or six years for the
  2019-to-2023 transition;
- the 2023 release contains a known uncorrected workplace-coding anomaly for
  Maxey-sur-Vaise.

The output therefore includes
`aggregated_flow_below_200_caution`, while the snapshot-level anomaly is
recorded in the provenance summary. No local correction is invented.

## 8. Decision

Decision: `OFFICIAL_COMMUTING_RELATION_SOURCE_READY`.

This authorizes a separate builder that assigns the latest strictly available
snapshot to each decision year and lifts ZE-to-ZE commuting relations to the
ZE-sector graph. It does not authorize using observation-time availability in
a strict ex-ante claim, training a neural encoder, claiming causal influence,
or producing an automatic recommendation.

The next gate must compare strict ex-ante commuting edges against:

1. no relation edges;
2. matched randomized endpoints;
3. the existing trajectory-similarity relation;
4. commuting weights with direction removed.

Only a relation family that separates from its matched placebos may enter a new
pre-prediction representation experiment.
