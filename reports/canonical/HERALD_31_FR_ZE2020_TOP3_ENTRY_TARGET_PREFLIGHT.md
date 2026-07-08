# HERALD 31 -- France ZE2020 Top-3 Entry Target Preflight

**Status:** `TARGET_PREFLIGHT_READY`.

This document records the first preflight for the next relation objective after
`HERALD_30` showed that the current descriptive relation embeddings are weak for
ZE2020 x sector ranking.

## 1. Question

The preflight asks:

```text
Can HERALD train a stricter target aligned with exploratory recommendation:
which ZE2020 x sector pairs enter the future top-3 growth set, instead of simply
describing existing relations?
```

This is a target-audit step only. It is not a trained model, not a dynamic-GNN
claim, not a causal analysis, and not an automatic recommendation system.

## 2. Script

```text
src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py
```

The script reads:

```text
data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
```

It writes nothing by default. If `--output-dir` is provided, it writes only
regenerable preflight summaries under that directory:

```text
fr_ze2020_top3_entry_target_preflight_summary_v1.csv
fr_ze2020_top3_entry_target_preflight_by_year_v1.csv
fr_ze2020_top3_entry_target_preflight_run_v1.json
```

## 3. Target Definition

For ZE `z`, sector `s`, and decision year `t`:

```text
future_top3_growth_hy_label(z,s,t) = 1
```

if sector `s` is among the top-3 sectors by observed future growth inside ZE
`z` over horizon `h`.

The stricter entry target is:

```text
future_top3_entry_hy_label(z,s,t) =
  1 if future_top3_growth_hy_label(z,s,t) = 1
       and current_top3_sector_share_label(z,s,t) = 0
       and future growth is available
  0 otherwise
```

where:

```text
current_top3_sector_share_label(z,s,t) = 1
```

if sector `s` is already among the top-3 sectors by current share in ZE `z` at
decision year `t`.

This target is closer to the project objective than the previous descriptive
relation layer because it asks about **movement into a future opportunity set**,
not only whether two nodes look related.

## 4. Local Preflight Result

Command:

```text
python3 src/modeles/france_ze2020/audit_fr_ze2020_top3_entry_target.py
```

Summary:

| Horizon | Eligible rows | Eligible years | Future top-3 rows | Entry rows | Entry rate |
|---:|---:|---|---:|---:|---:|
| 1 year | 27,717 | 2014-2024 | 9,248 | 6,806 | 0.2456 |
| 3 years | 22,677 | 2014-2022 | 7,567 | 5,700 | 0.2514 |

Reading:

- the target is not too rare;
- the 3-year target has valid decision years through 2022 only, because 2023
  and 2024 do not yet have full future observations;
- the 3-year target is the better next training target because it matches the
  ranking/recommendation horizon and avoids the missing-future years.

## 5. Decision

`HERALD_30` found the current relation embeddings weak for ranking:

```text
relation-only checks: ~0.373-0.375 NDCG@3
no-relation MLP control: ~0.5272 NDCG@3
```

`HERALD_31` therefore does not promote the current relation layer. It authorizes
only a next **target-aligned** model attempt:

```text
learn temporal-relational representations for future_top3_entry_3y_label
```

instead of training another model around descriptive edge existence or visual
compatibility.

## 6. Required Next Model Gate

The next model must compare at least:

```text
no relation features
temporal + sector features
target-aligned relation objective
shuffled relation placebo
temporal shuffle
sector shuffle
```

Promotion remains blocked unless the target-aligned relation objective improves
over the no-relation control and degrades under the relevant placebos.

## 7. Claim Policy

Allowed:

```text
HERALD has a valid retrospective target for testing exploratory ZE2020 x sector
entry into future top-3 growth sets.
```

Forbidden:

```text
HERALD recommends sectors.
HERALD has validated a dynamic GNN.
HERALD has proven causal influence between ZEs or sectors.
The top-3 entry target is a policy recommendation.
```

## 8. Tests

```text
tests/test_fr_ze2020_top3_entry_target.py
```

The tests check:

- top-3 entry label semantics;
- zero-padded ZE2020 IDs;
- future mask handling;
- no forbidden recommendation/causal output columns;
- real-panel availability, including 3-year decision-year cutoff at 2022.
