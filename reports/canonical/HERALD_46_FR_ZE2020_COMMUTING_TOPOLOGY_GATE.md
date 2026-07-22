# HERALD 46 -- France ZE2020 commuting-topology gate

**Date:** 2026-07-22  
**Status:** `GATE_FAILED_TOPOLOGY_SEMANTICS_NOT_ISOLATED`  
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

Smoke job `7780941` completed exit `0:0` in 22 seconds with empty stderr. It
was used only to verify execution.

The fixed run used commit `3a239f9` on Meso job `7780944`. It completed exit
`0:0` in 2 minutes 22 seconds, peak reported RSS 362,068 KiB, with empty
stderr.

- 525 metric rows: 7 views x 5 seeds x 3 years x 5 ZE folds;
- zero duplicate view/seed/year/fold keys;
- zero non-finite metrics and zero train/test ZE overlap;
- identical paired populations and one conservative claim status;
- 15 independent deterministic year-fold pairs;
- 75 seed/year/fold pairs for stochastic endpoint and target placebos.

Checksums of the collected, gitignored outputs:

| Output | SHA-256 |
|---|---|
| metrics | `06b5a50a79e61204a5343dab63a9ea132d0a78e5653330b4c725954032624d3d` |
| summary | `d2141d2ef9772ef7b8ec8127b0b21d6c0140a5b5145f36871f94d5d00ab88311` |
| gate | `b1b5f1a791a2c261c447640d2482a47ad97a5db21f1cfa4aa8336dce00c95d30` |

## 7. Result

| View | Mean NDCG@3 |
|---|---:|
| `commuting_topology_degree_only` | 0.599555 |
| `commuting_availability_only` | 0.600211 |
| `node_only` | 0.600963 |
| `commuting_topology_reversed_uniform` | 0.624605 |
| `commuting_topology_real_uniform` | 0.635586 |
| `commuting_topology_endpoint_randomized_uniform` | **0.643529** |
| `commuting_topology_target_shuffled` | 0.455371 |

Real uniform topology exceeded node-only (+0.034622), availability-only
(+0.035375), degree-only (+0.036031), reversed direction (+0.010981), and
shuffled targets (+0.180215). It failed the decisive matched endpoint placebo:
-0.007943 mean NDCG@3 and 37.3% paired wins.

The real-minus-randomized endpoint delta was +0.006551 in 2020, -0.005617 in
2021, and -0.024763 in 2022. Four of five seed-level mean deltas were negative.

## 8. Decision

DEC-075 fails. The apparent gain from uniform neighbour aggregation is not
attributable to the official destination semantics under this representation;
randomized destinations performed better on aggregate.

This closes the proposed weight-transform gate and blocks neural integration
of the current commuting graph. The result does not reject commuting data in
general. A future reopening would require a materially different, economically
identified representation, such as sector-conditioned flows or a task directly
linked to labour mobility, with a new pre-registration. No neural, causal,
dynamic-graph, or recommendation claim is authorized.
