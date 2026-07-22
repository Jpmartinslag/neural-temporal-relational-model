# HERALD 46 -- France ZE2020 commuting-topology gate

**Date:** 2026-07-22  
**Status:** `PRE_REGISTERED_NOT_RUN`  
**Decision:** `DEC-075`

## 1. Motivation

DEC-074 rejected raw origin-normalized commuting intensity because the same
official topology with uniform weights achieved higher NDCG@3. That result does
not validate topology: the prior endpoint placebo retained raw weights and was
not matched to the winning uniform representation.

## 2. Fixed question

Does official commuting topology carry transferable ZE-sector information when
both the real graph and randomized-endpoint placebo use uniform outgoing
weights?

The target, 2020--2022 evaluation years, three-year maturity rule, five
ZE-disjoint folds, seeds 42--46, logistic regression, and NDCG@3 remain
unchanged from DEC-074.

## 3. Views

| View | Isolated question |
|---|---|
| `node_only` | no commuting information |
| `commuting_availability_only` | release-period availability only |
| `commuting_topology_degree_only` | availability and real topology statistics, without neighbour profiles |
| `commuting_topology_real_uniform` | real destinations, uniform outgoing weights, neighbour profiles |
| `commuting_topology_endpoint_randomized_uniform` | false destinations with matched uniform weights and preserved edge multiplicity |
| `commuting_topology_reversed_uniform` | reversed official direction with uniform weights |
| `commuting_topology_target_shuffled` | false training labels |

All relation features remain mask-aware. Missing and infinite lagged growth is
excluded from the weighted neighbour mean and represented by an explicit
available-weight share.

## 4. Pre-registered gate

The real uniform topology passes only if it has:

1. positive mean NDCG@3 lift over node-only and availability-only;
2. positive lift over degree-only, showing value beyond topology summaries;
3. positive lift and at least 60% paired wins over matched uniform randomized
   endpoints;
4. positive lift over reversed uniform direction;
5. positive degradation relative to target shuffle;
6. identical finite populations, mature labels, and zero ZE overlap.

Deterministic seed repetitions are counted once per year-fold. Stochastic
endpoint and target placebos retain seed-specific pairs.

## 5. Decision rule

A pass retains official commuting topology as an input candidate and authorizes
only a separate pre-registered weight-transform gate. A failure closes this
topology representation under the current target. Neither outcome authorizes a
neural encoder, dynamic-graph claim, causal interpretation, or recommendation.

## 6. Execution

Pending.
