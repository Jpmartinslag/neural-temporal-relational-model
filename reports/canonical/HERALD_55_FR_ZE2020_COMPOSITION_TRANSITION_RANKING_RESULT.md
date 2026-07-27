# HERALD 55 - France ZE2020 composition-transition ranking result

**Date:** 2026-07-27  
**Decision:** DEC-080  
**Status:** `COMPLETE_GATE_FAIL_TRANSITION_RANKING_SPECIFICATION_CLOSED`

## 1. Question

The pre-registered test asked whether a small nonlinear model can rank sectors
inside a held-out ZE2020 by the magnitude of their next-year share change and
recover the direction of that change from the complete current and lagged
sector composition.

This is a transition-representation diagnostic. It uses no inferred relation
edge and is not a validated dynamic graph-neural model, causal analysis, or
territorial recommendation system.

## 2. Execution and integrity

- Meso smoke: job `7782514`, exit `0:0`, 1m12s
- Meso full array: job `7782532`, five tasks, all exit `0:0`
- runtime per seed: 33m52s--36m52s
- maximum resident memory per task: 231--238 MiB
- stderr: empty for every task
- seeds: 42--46
- evaluation years: 2017--2024
- five fixed ZE-disjoint folds
- views: ten
- metric rows: 2,000
- comparisons per view: 200
- duplicate metric keys: zero
- null or non-finite metrics: zero
- complete nine-sector groups: confirmed
- identical evaluation targets across views: confirmed
- train/test ZE overlap: zero
- maximum training decision year: exactly `t-1`
- convergence: 200/200 for every fitted view

The source panel remains untouched. Training labels are mature at decision
time, and the held-out `t+1` target is used only for evaluation.

## 3. Aggregate result

Higher NDCG, precision, and sign accuracy are better. Lower MAE is better.

| View | NDCG@3 | Precision@3 | Signed MAE | Top-3 MAE | Top-3 sign accuracy |
|---|---:|---:|---:|---:|---:|
| `past_delta` | 0.647044 | 0.472619 | 0.019375 | 0.031822 | 0.395833 |
| `mlp_target_history_only` | 0.635467 | 0.468006 | **0.011908** | **0.021821** | **0.654048** |
| `mlp_joint` | 0.623920 | 0.455923 | 0.012712 | 0.022030 | 0.634464 |
| `mlp_current_only` | 0.613522 | 0.449048 | 0.012367 | 0.022220 | 0.630357 |
| `mlp_temporal_shuffle` | 0.606185 | 0.441280 | 0.012588 | 0.022410 | 0.627054 |
| `zero_change` | 0.582830 | 0.461458 | 0.012233 | 0.024365 | 0.000000 |
| `ridge_joint` | 0.579403 | 0.452232 | 0.012358 | 0.024138 | 0.512500 |
| `mlp_target_shuffle` | 0.570215 | 0.421012 | 0.013200 | 0.024397 | 0.536548 |
| `mlp_sector_shuffle` | 0.553724 | 0.404435 | 0.012628 | 0.024190 | 0.526577 |
| `random_ranking` | 0.477927 | 0.335298 | 0.796278 | 0.799907 | 0.500298 |

The random control is graded as a ranking control. Its arbitrary score scale
makes its MAE non-comparable and it is not used for the signed-error claim.

## 4. Registered gates

| Condition | Result | Decision |
|---|---:|---|
| temporal, target, sector-group, and ZE-split integrity | all true | PASS |
| beat `past_delta` | lift `-0.023124`; 32.0% wins | **FAIL** |
| beat `ridge_joint` | lift `+0.044517`; 55.0% wins | **FAIL** |
| beat target-history-only MLP | lift `-0.011547`; 43.5% wins | **FAIL** |
| beat current-only MLP | lift `+0.010398`; 61.0% wins | PASS |
| degrade under sector shuffle | lift `+0.070196`; 88.0% wins | PASS |
| degrade under temporal shuffle | lift `+0.017735`; 65.5% wins | PASS |
| degrade under target shuffle | lift `+0.053705`; 73.5% wins | **FAIL** |
| sign accuracy above past delta and Ridge | 0.634464 vs 0.395833/0.512500 | PASS |
| beat all substantive controls by evaluation year | 0/8 years | **FAIL** |
| seed-level NDCG coefficient of variation at most 20% | 0.47% | PASS |

Every registered condition was required, so the global gate fails.

The result is seed-stable: `mlp_joint` NDCG ranges from 0.620545 to 0.628666.
However, it remains below `past_delta` and target-history-only MLP in every
seed. It exceeds all four substantive controls in no evaluation year.

## 5. Interpretation

The positive sector- and temporal-shuffle gaps show that the nonlinear model
uses the identities of the composition and its temporal ordering. Its higher
mean NDCG than matched Ridge is consistent with some nonlinear predictive
structure, although the paired recurrence threshold is not met.

That structure is not sufficient to justify the joint transition
representation:

- repeating the latest sector change ranks transition magnitudes better;
- the target sector's own history ranks better and has lower signed error;
- the full MLP does not beat Ridge often enough across paired comparisons;
- target-shuffle degradation is below the registered recurrence threshold;
- the joint advantage does not recur against all controls by year.

The most defensible conclusion is therefore partial. Time and sector identity
carry non-random predictive information, and a nonlinear model extracts some
of it, but the added cross-sector composition does not provide robust
incremental transition-ranking value beyond direct sector history in this
specification.

DEC-080 is closed. Reopening requires a materially different, economically
defined objective or relation representation, not tuning this MLP on the same
result. No dynamic-GNN, structural-causality, automatic-recommendation, or
policy claim is authorized.

## 6. Artifacts

```text
hpc_results/fr_ze2020_transition_ranking_full_20260724_185913/
```

The directory is collected locally, gitignored, and retained outside the
canonical source tree. Combined-output SHA-256 checksums:

```text
metrics  fe3559881eb0fb67a6b7576453b7cae6fd4d4617feadd4c0ab8382fca06a7f3d
summary  e738c0d46ad7fef6951a6e77e5de52226a10970e2c32a8ab8111e9aa88a39906
gate     8fee1ed524f6c356e2f7faa53190eb953ad8a7dcf153075b647aa019d3186fca
```
