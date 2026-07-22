# HERALD 41 -- France ZE2020 edge-family isolation gate

**Date:** 2026-07-22  
**Status:** `PROBE_RUN_COMPLETE_GATE_PASS_LIMITED`  
**Decision:** `DEC-070`

## 1. Question

Is transferable sector-transition information concentrated in a specific edge
family, and is it hidden when the three families are aggregated together?

HERALD_40 established that the external transition target is learnable but the
mixed relation-change representation does not separate from semantic placebos.
It did not establish that edge-count imbalance caused the failure.

## 2. Fixed contract

The following remain unchanged from HERALD_40:

- canonical dynamic nodes and expanding edge memory;
- `future_top3_entry_3y_label` among sectors outside the current top 3;
- horizon-aware label maturity;
- evaluation years 2020--2022;
- five deterministic ZE-disjoint folds and seeds 42--46;
- standardized logistic regression;
- `NDCG@3` as primary metric.

No neural model, new edge builder, legacy panel, or legacy adjacency input is
introduced.

## 3. Family blocks

Each edge family is passed independently through the existing audited graph
aggregation helper. Every block contains the same incoming/outgoing weight,
signal, stability, and count summaries plus their year-over-year changes.
Columns are family-prefixed before blocks are combined. Standard scaling is fit
on training rows only.

Tested real variants:

| Variant | Included family blocks |
|---|---|
| `ze_similarity_only` | `ze_similarity` |
| `cross_ze_same_sector_only` | `cross_ze_same_sector` |
| `intra_ze_sector_only` | `intra_ze_sector` |
| `economic_sector_balanced` | cross-ZE same-sector + intra-ZE sector |
| `all_families_balanced` | all three separate blocks |

This is feature-block balancing, not edge duplication, synthetic oversampling,
or evidence weighting by hand.

## 4. Controls

Every real variant is compared with a matched endpoint-randomized version built
from the same family or family set. `economic_sector_balanced` is additionally
compared with a within-ZE-year sector shuffle. `node_only` remains the common
non-graph control.

## 5. Gate

A family or balanced combination passes only if it:

1. has positive mean `NDCG@3` lift over `node_only`;
2. has positive mean lift over its matched randomized-endpoint control;
3. beats that placebo in at least 60% of paired seed-year-fold comparisons;
4. for `economic_sector_balanced`, degrades under sector shuffle;
5. preserves identical populations, finite metrics, horizon maturity, and zero
   ZE overlap.

A passing block may enter a later minimal nonlinear temporal encoder. This gate
does not authorize a dynamic-GNN, causal, or recommendation claim.

## 6. Execution audit

Smoke job `7780869` completed first. Full Meso job `7780874` completed in 6
minutes 48 seconds with exit `0:0` and empty stderr.

- 5 seeds, evaluation years 2020--2022, and 5 ZE-disjoint folds;
- 12 views, 900 metric rows, and 75 paired seed-year-fold keys;
- identical train, test, and positive populations across every view;
- zero ZE overlap and all metrics finite;
- claim status fixed to
  `edge_family_isolation_probe_exploratory_not_recommendation`.

Feature coverage confirmed that the families were not accidentally empty. Over
2020--2022, active node-year rows numbered 7,560 for `ze_similarity`, 149 for
`cross_ze_same_sector`, and 116 for `intra_ze_sector`.

## 7. Results

| View | Mean NDCG@3 | Mean AP |
|---|---:|---:|
| `node_only` | 0.60096 | 0.53709 |
| `ze_similarity_only` | 0.60677 | 0.53289 |
| `ze_similarity_only__endpoint_randomized` | 0.60231 | 0.52574 |
| `cross_ze_same_sector_only` | 0.60014 | 0.53641 |
| `intra_ze_sector_only` | 0.60096 | 0.53709 |
| `economic_sector_balanced` | 0.60014 | 0.53641 |
| `all_families_balanced` | 0.60691 | 0.53263 |
| `all_families_balanced__endpoint_randomized` | 0.60229 | 0.52532 |

`ze_similarity_only` produced:

- `+0.00581` mean NDCG@3 over node-only;
- `+0.00446` over its endpoint-randomized control;
- 62.7% paired wins over that endpoint placebo.

The all-family block also passed, but added only `+0.00013` NDCG@3 beyond ZE
similarity alone. The sector-economic block did not beat node-only or its
endpoint placebo. Its small degradation under sector shuffle does not compensate
for those failures.

## 8. Decision

Decision: `ZE_SIMILARITY_BLOCK_AUTHORIZED_FOR_MINIMAL_NONLINEAR_PROBE`.

The surviving evidence is narrow: time-respecting changes in ZE-similarity
structure add a small, repeatable within-ZE ranking signal beyond node history
and randomized endpoints. They do not improve global average precision over
node-only. The sparse same-sector and intra-ZE sector families are not promoted.

The next authorized step is a minimal nonlinear temporal probe using only:

1. canonical node history;
2. the isolated `ze_similarity` family block;
3. the same ZE-disjoint target, folds, endpoint placebo, and node-only control.

No additional edge family, recommendation layer, or dynamic-GNN claim is
authorized by this result.
