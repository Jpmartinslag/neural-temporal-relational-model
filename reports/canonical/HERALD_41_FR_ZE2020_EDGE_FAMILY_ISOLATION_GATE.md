# HERALD 41 -- France ZE2020 edge-family isolation gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
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
