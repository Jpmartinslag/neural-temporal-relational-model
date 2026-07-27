# HERALD 57 -- France ZE2020 Availability Masks

**Date:** 2026-07-27
**Status:** `AVAILABILITY_MASKS_SEPARATED`
**Decision:** DEC-082
**Stage:** E2 of the delivery sequence fixed in HERALD_56 section 5.

## 0. Why two masks and not one

Observational availability and relational availability are different objects and were
being conflated.

The A10 observational question is "does the panel record a value for this zone, sector and
year". The relational question is "does a relation exist for this family at this decision
year, and if not, why". Merging them would have hidden the fact that the first question is
already fully answered while the second was not asked at all.

This delivery therefore produces one documentary answer (part A) and one artifact
(part B). It produces no model input, no metric, and no claim.

## 1. Part A -- the A10 observational mask is already complete

Verified directly against `data/processed/france_ze2020/fr_ze2020_sector_panel.csv`:

| Property | Value |
|---|---|
| Rows | 35,280 (280 zones x 14 years x 9 sectors) |
| Years | 2012-2025, all 14 present |
| `mask_sector_available = 0` | **0 cells** |
| Observed zeros | **1 cell** |
| Positive cells | **35,279** |

There is no missing-data work at A10. The panel is complete, and its provenance is closed
byte-identically against the official INSEE SIDE source (DEC-076).

The single observed zero is `5218 / 2016 / JZ`. It is completed as zero because the other
eight sectors of that zone-year equal the independent official total, so the zero is an
inferred-but-reconciled observation rather than a gap. No further treatment is required.

**Consequence for the sequence:** the availability work that HERALD_56 anticipated is
almost entirely relational, not observational. Part A is documentation; part B is the
artifact.

Part A still carries a regression test, because these properties are load-bearing for
every later stage -- the sectoral persistence audit, the forecast-derived states, and the
dashboard all assume a complete A10 panel. Five tests fix the shape (35,280 rows, 280
zones, 9 sectors, 14 years, no duplicate zone-year-sector), the integral mask, the positive
count, and the identity of the single zero. A future rebuild cannot introduce a gap or a
second zero without failing them.

## 2. Part B -- the relational availability mask

### 2.1 The defect it removes

Relational unavailability in this repository is expressed as an **absent row**, not as a
flag:

- `fr_ze2020_temporal_relation_signals.csv.gz` has no rows before 2017;
- `fr_ze2020_commuting_strict_ex_ante_edges.csv.gz` has no rows before 2016, and every row
  it does contain carries `data_available = 1`.

A consumer that joins on `decision_year` without counting rows cannot see either gap. More
seriously, a year with zero edges becomes indistinguishable from a year whose relations are
merely weak. DEC-065 is the precedent for the cost of that confusion: an automated gate
counted 121 promoted edges before a structural diagnostic found the proxy method was
injecting correlation unrelated to the phenomenon.

### 2.2 Artifact

| Item | Path |
|---|---|
| Table | `data/processed/france_ze2020/fr_ze2020_relation_availability_mask.csv` |
| Summary | `data/processed/france_ze2020/fr_ze2020_relation_availability_mask_summary.json` |
| Builder | `src/data/france_ze2020/build_fr_ze2020_relation_availability_mask.py` |
| Tests | `tests/test_fr_ze2020_relation_availability_mask.py` (21 tests) |
| Registry | `FR_ZE2020_RELATION_AVAILABILITY_MASK`, `FR_ZE2020_RELATION_AVAILABILITY_MASK_SUMMARY` |

It is a **standalone table**. No canonical artifact is modified. Every input is opened
read-only and its SHA-256 is recorded before and after the run; the builder asserts they
are unchanged, and a test re-checks it independently.

### 2.3 Schema

```text
relation_family
decision_year
availability_status
unavailable_reason
source_snapshot_year
source_release_date
snapshot_age_years
expected_edge_count
actual_edge_count
provenance
```

### 2.4 Status vocabulary

| Status | Meaning | Used by |
|---|---|---|
| `observed` | the relation is observed at its own decision year | **no family** -- see below |
| `carried_forward_from_snapshot` | a real observation exists, from an earlier year, carried forward under a release-aware rule | commuting |
| `derived_available` | the relation is computed from causal lag features, not observed | the three signal families |
| `unavailable` | no relation exists for this family and decision year | see reasons |

`observed` is currently unused, and that is a finding rather than an omission: **no relation
family in this project observes a relation at its own decision year.** Commuting observes,
but always with a lag of four to eight years. The three signal families do not observe at
all -- they correlate causal lag features. The status is retained in the vocabulary because
a future directly observed relation source would need it, and its emptiness is asserted in
the summary (`observed_status_used: false`).

Calling a computed relation `observed` is explicitly forbidden and is enforced by both the
builder and a test.

### 2.5 Unavailable reasons

| Reason | Meaning |
|---|---|
| `source_not_released` | the upstream source had not been published by the decision year |
| `insufficient_history` | the causal feature the relation derives from lacks enough non-null years at the decision year |
| `not_constructed` | the family is documented as planned but was never built |

### 2.6 Contents

84 classified cells: 6 families x 14 decision years, with no cell left unclassified.

| Family | Status | Reason | Years | Cells |
|---|---|---|---|---|
| `commuting_strict_ex_ante` | `carried_forward_from_snapshot` | -- | 2016-2025 | 10 |
| `commuting_strict_ex_ante` | `unavailable` | `source_not_released` | 2012-2015 | 4 |
| `ze_similarity` | `derived_available` | -- | 2017-2025 | 9 |
| `ze_similarity` | `unavailable` | `insufficient_history` | 2012-2016 | 5 |
| `cross_ze_same_sector` | `derived_available` | -- | 2017-2025 | 9 |
| `cross_ze_same_sector` | `unavailable` | `insufficient_history` | 2012-2016 | 5 |
| `intra_ze_sector` | `derived_available` | -- | 2017-2025 | 9 |
| `intra_ze_sector` | `unavailable` | `insufficient_history` | 2012-2016 | 5 |
| `sector_to_sector_comovement` | `unavailable` | `not_constructed` | 2012-2025 | 14 |
| `temporal_precedence_signal` | `unavailable` | `not_constructed` | 2012-2025 | 14 |

Aggregate: `unavailable` 47, `derived_available` 27, `carried_forward_from_snapshot` 10.
Reasons: `not_constructed` 28, `insufficient_history` 15, `source_not_released` 4.

The last two families are recorded deliberately. HERALD_20 section 2 documented
`sector_to_sector_comovement` and `temporal_precedence_signal` as planned and explicitly
not populated -- the first because mixing Phase 7's country grain with ZE2020 grain would
require a reconciliation decision that does not exist, the second because no signed
lagged-precedence test has been run at ZE2020 grain. Listing them keeps the mask honest
about planned-but-absent structure instead of omitting them silently.

### 2.7 The two gaps, with their mechanisms proved rather than asserted

**Commuting, 2012-2015 -- `source_not_released`.** The earliest official INSEE flow
snapshot observes 2012 and was released `2015-06-25`. Under the release-aware rule of
DEC-073, a decision taken in 2012, 2013, 2014 or 2015 could not have used it. The builder
of the commuting artifact already computes this and reports the four years as unavailable;
this mask makes it a row rather than an omission. Snapshot ages for the available years run
from four to eight years, across two generations: decision years 2016-2020 use the 2012
snapshot (27,675 edges each) and 2021-2025 use the 2017 snapshot (27,683 edges each).

**Signal families, 2012-2016 -- `insufficient_history`.** Traced to the builders, not
inferred from the output:

1. `build_fr_ze2020_temporal_relation_signals.py` derives `ze_similarity` from
   `similarity_matrix_for_year(panel, year, ZE_MIN_HISTORY_YEARS)` with
   `ZE_MIN_HISTORY_YEARS = 3`, which is `pivot.T.corr(min_periods=3)` over history
   restricted to years **strictly less than** the decision year.
2. The similarity feature is `SIMILARITY_FEATURE = "growth_1y_safe"`, whose first non-null
   year in `fr_ze2020_model_ready_panel.csv` is **2014** (verified: `lag_1` starts 2013,
   `lag_2` and `growth_1y_safe` start 2014, `growth_2y_safe` starts 2015).
3. Three non-null prior years therefore first exist at decision year **2017**
   (2014, 2015, 2016).
4. The two sector families follow the same mechanism through
   `train_fr_ze2020_sector_graph_prototype.py`, which pivots `sector_growth_lag_1` and
   applies `corr(min_periods=MIN_HISTORY_YEARS)` with the same value of 3;
   `sector_growth_lag_1` also has its first non-null year at 2014.

The derived first year of 2017 matches the observed first year of the artifact exactly. A
test asserts that the recorded provenance names all three components of the mechanism
(`2014`, `min_periods=3`, `2017`), so the reason cannot silently degrade into an assertion.

### 2.8 Availability is not emptiness

The distinction the mask exists to protect is enforced, not merely documented:

- an `unavailable` cell means the relation does not exist for that family and year, by
  source or by construction;
- an available cell with `actual_edge_count = 0` would be *silent emptiness*, a different
  and worse condition. The builder **fails closed** on it, and a test constructs that exact
  row to confirm the failure fires.

Additional fail-closed checks: every family x year cell must exist exactly once; every cell
must be classified; every `unavailable` row must carry a valid reason; no available row may
carry a reason; and the structural expectation must match the actual count wherever a
documented formula exists.

`expected_edge_count` is populated only where such a formula exists --
`ze_similarity` keeps the top five positive correlations per zone and repeats each pair
across nine sectors, giving 280 x 5 x 9 = 12,600 per available year, which matches the
artifact. The two sector families select over available pairs with no documented closed
form, so their expectation is left **blank, meaning unknown**, rather than back-filled from
the output they are supposed to check. Blank is never zero anywhere in this table.

### 2.9 Input guards: the builder must not invent a reason

The first implementation classified *any* commuting year without rows as
`source_not_released`. That is only true through 2015. Had the artifact been truncated or
corrupted, the build would have passed and the table would have asserted something false
about INSEE rather than reporting a missing row -- a fabricated provenance claim, which is
worse than the absent-row defect this artifact exists to fix. Three input guards now run
before any row is emitted:

| Guard | Rejects |
|---|---|
| `validate_commuting_input`: required-year coverage | a missing decision year from 2016 onward. Absence is a release fact only through 2015; later absence is truncation or corruption and fails |
| `validate_commuting_input`: pre-release rows | a row dated at or before 2015, when no snapshot had been released |
| `validate_commuting_input`: per-year uniqueness | mixed `observation_year`, `source_release_date`, `snapshot_age_years` or `availability_mode` inside one decision year, where `first` would otherwise silently attribute one snapshot; also any `data_available != 1` or any mode other than `strict_ex_ante_release_aware` |
| `validate_signal_input`: family drift | a relation family present in the input but absent from the builder's iterated tuple, which would vanish from the mask unclassified; and a known family missing from the input |

The unavailable branch additionally re-asserts the year bound at the point of emission, so
the reason cannot be attached to a truncated year even if `build_mask` is called directly.

Each guard has a mutation test that constructs the exact defective input and confirms the
failure fires, through both the validator and the full `build_mask` path. Adding the guards
did not change the artifact: it is byte-identical to the version produced before them.

## 3. E2 finding, recorded and deliberately not fixed here

`data/processed/france_ze2020/fr_ze2020_dynamic_graph_splits.csv` assigns the split role
`warmup_or_train` to decision years 2012 and 2013, with 2,520 nodes each. Per section 2.6,
**no relational edge exists for any family in those years.**

What is confirmed is exactly this: the splits include years without edges. The impact is
**not** established. Whether any consumer treated an edgeless year as a year of weak
relations, and whether any past metric was affected, requires auditing each consumer of the
splits file individually. That audit is a separate delivery and must not be folded into
this one.

Recorded here so the finding is not lost, and so that no future work reuses the splits file
without first resolving it.

A related asymmetry, noted for the same reason: within the available years,
`intra_ze_sector` carries 20 relations per year against 12,600 for each of the other two
families, a ratio of 630 to 1. This is a different quantity from the imbalance reported in
DEC-069 (257,823 / 426 / 211), which counted accumulated expanding-window edge memory
rather than annual snapshots. Both are recorded; neither is interpreted here.

## 4. What this delivery does not do

- It does not modify any canonical artifact.
- It does not produce a model input. The summary carries
  `claim_status = availability_provenance_only_not_model_input`.
- It does not fix the splits file.
- It does not evaluate whether any relation carries predictive value.
- It does not authorize an HPC job, a training run, or a reopening of any closed branch.

## 5. Verification

| Check | Result |
|---|---|
| Builder run | 84 rows, 6 families, 0 unclassified cells |
| Determinism | identical SHA-256 across two independent output directories |
| Canonical inputs unchanged | SHA-256 equal before and after, asserted in builder and re-tested |
| Tests | 35 passed (`tests/test_fr_ze2020_relation_availability_mask.py`) |
| Fail-closed on output | silent emptiness, missing classification, and reason-less unavailability each raise |
| Fail-closed on input | truncated commuting year, pre-release row, mixed per-year metadata, and signal-family drift each raise, verified by mutation tests through both the validator and `build_mask` |
| Part A regression | 5 tests fix the A10 shape, integral mask, positive count, and the identity of the single zero |
| Numeric formatting | counts written as integers via nullable `Int64`; blank means unknown, never zero |

The repository-wide `pytest tests` run reports 20 collection errors, all
`ModuleNotFoundError: No module named 'torch'` in unrelated synthetic and graph-temporal
modules. That is an environment gap, not an E2 result. Note that `python3` on this machine
lacks pandas; the working interpreter is `python3.10`.

## 6. Cross-reference

- Contract and delivery sequence: `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`.
- Decision: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`, DEC-082.
- Commuting provenance and the release-aware rule: DEC-073, `HERALD_44`.
- A10 source provenance closure: DEC-076, `HERALD_47`.
- Leakage-safe relation snapshots: `HERALD_38`.
- Families documented as not constructed: `HERALD_20` section 2.
- Proxy-availability precedent: DEC-065.
