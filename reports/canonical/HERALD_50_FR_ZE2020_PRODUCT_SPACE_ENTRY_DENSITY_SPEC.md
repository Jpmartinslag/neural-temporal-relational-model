# HERALD 50 - France ZE2020 product-space entry-density gate

**Date:** 2026-07-23  
**Decision:** DEC-078  
**Status:** `COMPLETE_GATE_FAIL_SEE_HERALD_51`

## 1. Prior-work boundary

DEC-017/G1-L1 already tested whether an RCA co-specialization graph was more
stable than temporal and configuration nulls. France failed because stable
sector prevalence reproduced the observed graph. That stability test must not
be rerun or reinterpreted.

DEC-078 asks a different question: whether product-space density calculated at
year `t` ranks new ZE-sector specializations at `t+1` better than marginal
prevalence and matched semantic placebos.

## 2. Fixed population and label

Input:

```text
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
```

For ZE `z`, sector `s`, and year `t`:

```text
RCA(z,s,t) = sector share inside z / national share of sector s
specialized(z,s,t) = 1[RCA(z,s,t) >= 1]
entry(z,s,t+1) = 1[specialized(z,s,t)=0 and specialized(z,s,t+1)=1]
```

Only sectors with `specialized(z,s,t)=0` are ranking candidates. The 2026-07-23
support-only preflight found 17,196 eligible rows and 2,611 entries across all
280 ZEs and decision years 2012--2024. No relation score was inspected before
this registration.

## 3. Leakage-safe product-space density

Use five fixed ZE-disjoint folds. For each decision year and held-out fold:

1. estimate the 9 x 9 Hidalgo-Hausmann proximity matrix only from the other
   four folds at year `t`;
2. calculate density for each held-out ZE and non-specialized target sector;
3. evaluate the observed entry label at `t+1`.

```text
density(z,s,t) =
  sum_j proximity(j,s,t) * specialized(z,j,t)
  ------------------------------------------------
  sum_j proximity(j,s,t),  j != s
```

The held-out ZE never contributes to its own proximity matrix. No value from
`t+1` enters a score.

## 4. Fixed views

| View | Purpose |
|---|---|
| `product_space_density` | registered economic relation score |
| `target_prevalence` | marginal fraction of training ZEs specialized in target sector |
| `target_rca` | target sector's own current RCA, still below one |
| `randomized_product_space` | same proximity weights with sector identities reassigned |
| `sector_shuffled_density` | real proximity with held-out ZE specialization identities shuffled |
| `target_shuffled_density` | real density evaluated against labels shuffled across ZEs within year/sector |
| `random_score` | random ranking control |

Random views use seeds 42--46. No threshold, RCA cutoff, view, or metric may be
changed after the full result is observed.

## 5. Evaluation

- decision years: 2012--2024;
- five ZE-disjoint folds;
- seeds: 42--46;
- ranking group: held-out ZE x decision year;
- primary metric: NDCG@3;
- secondary metrics: precision@3, hit rate@3, and average precision;
- identical candidates for every view;
- association/relatedness language only.

## 6. Registered gate

All conditions are required:

1. complete finite outputs, identical populations, and zero train/test ZE
   overlap;
2. `product_space_density` has higher mean NDCG@3 than both
   `target_prevalence` and `target_rca`;
3. it beats `randomized_product_space` in at least 60% of paired
   seed/year/fold comparisons with positive mean lift;
4. it beats `sector_shuffled_density` in at least 60% of paired comparisons
   with positive mean lift;
5. `target_shuffled_density` loses in at least 80% of paired comparisons;
6. real density exceeds both marginal controls in at least 9 of the 13
   evaluation years.

## 7. Decision boundary

A pass would show only that a leakage-safe product-space density contains
transferable ranking information for next-year specialization entry. It would
authorize design of one small representation layer using this score.

A failure closes this entry-density representation for France ZE2020. It does
not prove that all sector relations are absent.

Neither outcome validates a dynamic graph-neural model, structural causality,
automatic territorial recommendation, or policy action.

## 8. Post-execution pointer

Meso job `7781384` executed this specification without changing its population,
views, metrics, or thresholds. The registered gate failed. The frozen result
and interpretation are recorded separately in
`HERALD_51_FR_ZE2020_PRODUCT_SPACE_ENTRY_DENSITY_RESULT.md`.
