# HERALD 51 - France ZE2020 product-space entry-density result

**Date:** 2026-07-24  
**Decision:** DEC-078  
**Status:** `COMPLETE_GATE_FAIL_ENTRY_DENSITY_REPRESENTATION_CLOSED`

## 1. Question

The pre-registered test asked whether leakage-safe product-space density at
year `t` ranks next-year entry into ZE-sector RCA specialization better than
target-sector prevalence, the target sector's current RCA, and matched
semantic placebos.

This is an association and predictive-ranking test. It is not a causal test.

## 2. Execution and integrity

- Meso job: `7781384`
- runtime: 4m23s
- exit code: `0:0`
- stderr: empty
- peak resident memory: 125,316 KiB
- decision years: 2012--2024
- seeds: 42--46
- five fixed ZE-disjoint folds
- candidates per seed: 17,196
- next-year entries per seed: 2,611
- metric rows: 2,275, with 325 rows for each of seven views
- duplicate metric keys: zero
- train/test ZE overlap: zero
- candidate populations: identical across views
- finite outputs: complete

The candidate and positive counts exactly reproduce the support-only preflight
registered before the relation score was inspected. Current-year RCA and
specialization states use only year `t`; only the evaluation label reads
specialization at `t+1`.

The deterministic real and marginal views repeat across the five random seeds.
Those repetitions do not constitute independent evidence and are not used as
such: they leave the aggregate means, paired win rates, and yearly decisions
unchanged. Seeds vary only the registered random and shuffled controls.

## 3. Aggregate result

Higher NDCG@3 is better.

| View | Mean NDCG@3 | Precision@3 | Hit rate@3 | Average precision |
|---|---:|---:|---:|---:|
| `target_rca` | 0.776262 | 0.212235 | 0.512653 | 0.392790 |
| `product_space_density` | 0.767135 | 0.214727 | 0.513986 | 0.267455 |
| `target_prevalence` | 0.760431 | 0.213323 | 0.510913 | 0.296949 |
| `target_shuffled_density` | 0.709616 | 0.203776 | 0.494981 | 0.241103 |
| `random_score` | 0.472311 | 0.146378 | 0.386492 | 0.169644 |
| `randomized_product_space` | 0.469713 | 0.148274 | 0.387652 | 0.153909 |
| `sector_shuffled_density` | 0.469566 | 0.162758 | 0.417059 | 0.139708 |

Product-space density clearly exceeds the random and semantic structure
placebos. It has only a small aggregate lift over target-sector prevalence
(`+0.006704`) and loses to the target sector's own current RCA
(`-0.009128`).

## 4. Registered gates

| Condition | Result | Decision |
|---|---:|---|
| finite outputs, complete views/populations, zero ZE overlap | all true | PASS |
| positive mean NDCG@3 lift over `target_prevalence` | +0.006704 | PASS |
| positive mean NDCG@3 lift over `target_rca` | -0.009128 | FAIL |
| beat randomized product space in at least 60% of pairs | 98.8%; lift +0.297422 | PASS |
| beat sector-shuffled density in at least 60% of pairs | 100%; lift +0.297569 | PASS |
| target shuffle loses in at least 80% of pairs | 81.5% | PASS |
| beat both marginal controls in at least 9/13 years | 4/13 | FAIL |

The four years in which density exceeds both marginal controls are 2017, 2018,
2019, and 2022. The registered gate requires every condition, so the final
decision is a failure.

## 5. Interpretation

The placebos show that the observed sector identities and ZE specialization
composition contain non-random structure. They do not show that product-space
density adds useful entry-ranking information beyond a sector's current
distance from the RCA specialization threshold. Current target RCA remains the
stronger and simpler control overall, and the density advantage over both
marginals is not recurrent across years.

Therefore:

- the tested France ZE2020 product-space entry-density representation is closed;
- it is not authorized as a new relation or neural representation layer;
- DEC-017 is not reopened or reinterpreted;
- this result does not reject every possible sector relation or learning task;
- reopening requires a materially different economic object and a new
  pre-registered decision, not threshold or metric tuning on this result;
- no dynamic graph-neural, causal, automatic recommendation, or policy claim is
  authorized.

## 6. Artifacts

```text
hpc_results/fr_ze2020_product_space_entry_density_20260723_193332/
```

The result directory is collected locally, gitignored, and retained outside
the canonical source tree. SHA-256 checksums:

```text
metrics  da9f5d4f25b5d8c19285564edcbd8d15ad3b11eb30bbae6f485180b301858cb9
summary  ec79c04811c0de245c06be93674f3628aec71817a7daf485a82319bde5012e38
gate     38858fa28a5faa4f65b2fb0a4e486f2f35175e1a12cb36a7fac7a17a254a5a4f
```
