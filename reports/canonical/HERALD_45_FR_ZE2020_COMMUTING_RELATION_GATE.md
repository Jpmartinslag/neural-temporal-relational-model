# HERALD 45 -- France ZE2020 commuting-relation gate

**Date:** 2026-07-22  
**Status:** `GATE_FAILED_RAW_WEIGHTING_REJECTED`  
**Decision:** `DEC-074`

## 1. Question

Do official, release-aware commuting relations carry transferable
territorial-sector information beyond time availability, random endpoints,
unweighted topology, reversed direction, and the previously retained
trajectory-similarity relation?

This is a linear relation gate. It does not train a neural graph encoder.

## 2. Fixed evaluation contract

The target and protocol are unchanged from HERALD_40--43:

- target: externally observed future top-3 sector entry over three years;
- evaluation years: 2020, 2021, 2022;
- five ZE-disjoint folds;
- seeds 42--46;
- training labels admitted only after the full three-year horizon matures;
- standardized logistic regression;
- primary metric: `NDCG@3`;
- identical candidate populations across paired views.

Seeds vary stochastic placebos. Deterministic views are checked for exact
agreement across seeds and counted once per year-fold in paired gate summaries;
seed repetitions are not treated as independent evidence.

## 3. Relation representation

For each ZE-sector node and decision year, the strict commuting matrix
`W_t` aggregates five already-observed node features:

```text
outgoing profile = W_t X_t
incoming profile = column_normalize(W_t)' X_t
```

The five inputs are sector count, sector share, sector rank, lagged sector
growth, and dominant-sector flag. The relation block also contains outgoing
degree, maximum weight, weight entropy, incoming degree, incoming weight sum,
and a separate availability mask.

Lagged sector growth is aggregated only over finite, mask-observed neighbours.
Its outgoing and incoming available-weight shares are retained as separate
features; a missing or infinite growth is never interpreted as an observed
zero.

This occurs before prediction. It is not a residual correction.

## 4. Views

| View | What it tests |
|---|---|
| `node_only` | temporal-sector baseline |
| `commuting_availability_only` | whether a release-period flag alone explains a lift |
| `commuting_real` | official directed weighted commuting semantics |
| `commuting_endpoint_randomized` | same source/year weights and target multiset, false destinations without self-loops |
| `commuting_uniform_weights` | real topology without commuting intensity |
| `commuting_reversed_direction` | workplace-to-residence instead of residence-to-workplace |
| `trajectory_similarity_reference` | surviving DEC-070 similarity family under the same target/folds |
| `commuting_target_shuffled` | false training labels |

## 5. Pre-registered gate

`commuting_real` passes only if all conditions hold:

1. positive mean NDCG@3 lift over `commuting_availability_only`;
2. positive mean lift and at least 60% paired wins over randomized endpoints;
3. positive mean lift over uniform weights;
4. positive mean lift over reversed direction;
5. positive mean lift over the trajectory-similarity reference;
6. positive degradation relative to target shuffle;
7. identical train/test populations, finite metrics, mature labels, and zero ZE overlap.

A failure rejects this representation under this target and protocol. It does
not reject commuting as an economic relation generally.

## 6. Decision rule

A pass authorizes only a small pre-prediction dual temporal/commuting encoder.
It does not validate a dynamic GNN, causal influence, automatic recommendation,
or policy action.

A failure blocks neural integration and requires inspecting whether commuting
must be sector-conditioned, flow-thresholded, or used under a different
auditable relational objective.

## 7. Execution

Smoke job `7780919` stopped before model fitting on one infinite lagged-growth
input and unavailable 2025 lagged growth. This exposed a missing-value handling
bug in the new relation aggregator. The implementation was corrected to use
the canonical mask plus a finite-value check and to emit neighbour-availability
shares. No metric was observed and the pre-registered gate is unchanged.

The execution smoke was repeated after the correction. Job `7780923`
completed exit `0:0` in 29 seconds with zero stderr. It was used only as an
execution check; its one-seed/one-year metrics are not evidence.

## 8. Fixed-run audit

The final run used commit `6da99d4` on Meso job `7780933` and completed exit
`0:0` in 2 minutes 45 seconds. Peak reported RSS was 482,912 KiB and stderr was
empty.

- 600 metric rows: 8 views x 5 seeds x 3 years x 5 ZE folds;
- zero duplicate view/seed/year/fold keys;
- zero non-finite metrics and zero train/test ZE overlap;
- one claim status across every row;
- identical train/test populations across paired views;
- deterministic views were identical across seeds and contribute 15
  independent year-fold pairs, not 75;
- stochastic endpoint and target placebos contribute 75 paired evaluations.

Checksums of the collected, gitignored outputs:

| Output | SHA-256 |
|---|---|
| metrics | `ef88c7e1969e269abb8970c27ada5cb127a230ebe2cad8ffb039adeed29fb262` |
| summary | `0273c2a6d63e122908a4032ae572571ebaddb3b9e964c1c50a70e190a2eab58d` |
| gate | `cf27d97dd63c613d01c36de0689ca2ca8555bb4b37909aca39b3e56dcf195ea9` |

## 9. Result

| View | Mean NDCG@3 |
|---|---:|
| `node_only` | 0.600963 |
| `commuting_availability_only` | 0.600211 |
| `trajectory_similarity_reference` | 0.606771 |
| `commuting_endpoint_randomized` | 0.608295 |
| `commuting_reversed_direction` | 0.611046 |
| `commuting_real` | 0.615354 |
| `commuting_uniform_weights` | **0.635586** |
| `commuting_target_shuffled` | 0.459723 |

The weighted real relation had positive mean lift over node-only (+0.014391),
availability-only (+0.015143), randomized endpoints (+0.007059; 62.7% paired
wins), reversed direction (+0.004309), trajectory similarity (+0.008584), and
shuffled targets (+0.155631). It failed the pre-registered uniform-weight
condition: -0.020231 mean NDCG@3 and 26.7% wins over the same real topology with
uniform weights.

The apparent weighted-relation lift was not temporally uniform. Against
node-only it was negative in 2020 (-0.007620), positive in 2021 (+0.054875),
and negative in 2022 (-0.004082). The gate therefore fails independently of
the uniform-weight result.

## 10. Decision

`commuting_real` does not pass DEC-074. Raw origin-normalized commuting
intensity is rejected for neural integration under this target and
representation.

The uniform-topology result is a candidate observation, not a validated graph
claim: this gate did not include a matched uniform-weight endpoint placebo.
The next admissible test is therefore topology-only real versus topology-only
randomized endpoints, followed by pre-registered weight transforms such as
log, square-root, rank, or capped weights only if topology survives. No neural
encoder, causal claim, or recommendation is authorized by this result.
