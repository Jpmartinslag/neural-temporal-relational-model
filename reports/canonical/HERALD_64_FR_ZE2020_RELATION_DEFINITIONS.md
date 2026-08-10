# HERALD 64 -- What a node is, what an edge is, and what a relation must survive

**Date:** 2026-08-10
**Status:** `PRE_REGISTERED_DEFINITIONS_AND_PROTOCOL_NOT_YET_EXECUTED` (DEC-095)

Written before any estimation code exists. This file defines the objects; it reports no
measurement.

---

## 1. Why definitions come before estimation

`HERALD_62` and `HERALD_63` closed the forecasting line with three refutations
(DEC-090, DEC-091, DEC-094). None of them tested the relational layer, and section 10b of
`HERALD_63` records that explicitly so the negatives are not read across.

The relational layer nonetheless cannot be strengthened as it stands, because three
inconsistencies make its contents non-comparable.

### 1.1 Family names disagree between the catalogue and the availability mask

| catalogue (`fr_ze2020_exploratory_relation_signals.csv`, 6,215 rows) | mask (`fr_ze2020_relation_availability_mask.csv`) |
|---|---|
| `ze_to_ze_similarity` (5,769) | `ze_similarity` |
| `ze_to_ze_same_sector_signal` (102) | `cross_ze_same_sector` |
| `intra_ze_sector_interaction` (64) | `intra_ze_sector` |
| `ze_sector_specialization` (280) | **absent from the mask** |
| -- | `sector_to_sector_comovement` -- never constructed, 14/14 unavailable |
| -- | `temporal_precedence_signal` -- never constructed, 14/14 unavailable |

DEC-082 required a layer to render only where the mask says the relation exists. With names
that do not match, that rule cannot be enforced.

### 1.2 The catalogue is 93% resemblance

5,769 of 6,215 rows are `ze_to_ze_similarity`. The micro layer -- interaction between sectors
inside a zone -- holds **64 rows**, the thinnest family present.

### 1.3 Three node types coexist without a hierarchy

`ZE2020`, `Setor`, and `ZE2020xSetor` all appear as node types, with no rule stating how
they relate.

## 2. The node

**One atomic node: `ZE x sector`.** 280 x 9 = 2,520 nodes per year.

Everything else is an aggregation of it, and is defined as such rather than as a separate
type:

| view | definition |
|---|---|
| zone | sum over the 9 sectors of that zone |
| national sector | sum over the 280 zones for that sector |

This is also the unit the product requires: *construction in Lyon* is a node; neither "Lyon"
nor "construction" is.

## 3. The edge

### 3.1 Four things are currently called a relation; two are edges

| candidate | what it asserts | admitted as an edge |
|---|---|---|
| **flow** | people live in A and work in B | **yes** -- physically real, observed, official |
| **temporal precedence** | A moves, then B moves | **yes** -- directed and falsifiable |
| co-movement | A and B rise and fall together | **candidate only**, must pass its null |
| similarity | A and B resemble each other | **no** |

Similarity is reclassified. Two zones resembling each other asserts nothing about interaction
between them -- they may never have exchanged anything. It becomes a **node attribute**
("this node resembles those"), retaining the information while removing the false implication
carried by drawing a line between them.

Consequence: the edge catalogue drops from 6,215 to roughly 450. The similarity rows are
**reclassified, not deleted**, and the decision is reversible.

### 3.2 Weight, unit, and null

No weight is admitted without a declared unit and a declared null. A correlation of 0.8
between two short series is unremarkable, and a weight without its null cannot be read.

| family | weight | unit | null it is tested against |
|---|---|---|---|
| `flow` | commuter share of origin workers | fraction | none -- observed, not inferred |
| `precedence` | partial correlation (section 4) | dimensionless, [-1, 1] | years shuffled within each series |
| `comovement` | correlation of growth | dimensionless, [-1, 1] | zone-matched random pairs of equal volume |

## 4. Precedence, defined concretely

The estimator must not repeat the identification failure of DEC-091 and DEC-094, where a
neural model was asked to learn one parameter per edge and five seeds disagreed
(0.695 and 0.704). The fix is the same one that made `HERALD_63` arithmetically sound, applied
correctly this time: **pool across zones instead of estimating per edge.**

Precedence is estimated at the **sector-pair** level, pooled over the 280 zones:

```text
P_t[s, r] = partial correlation of  g[i, s, t]  with  g[i, r, t+1]
            given  g[i, r, t],  taken across the 280 zones i
```

where `g` is the log1p growth of section `HERALD_63` 3.2.

Conditioning on `g[i, r, t]` is not optional: without it the statistic measures the target's
own autocorrelation and every pair looks connected.

| | parameters | observations per parameter |
|---|---|---|
| per-edge (rejected, DEC-091/094) | 78,120 or 2,520^2 | << 1 |
| **sector-pair, pooled over zones** | **81 per year** | **280** |

Two variants are estimated per year, giving the micro and macro views of section 5:

- `P_intra` -- source and target in the **same** zone;
- `P_cross` -- source in zone `i`, target in zone `j != i`, each pair weighted by the
  official commuting `C[i,j]` of DEC-073, release-aware.

**Naming discipline.** This is *conditional temporal association*. It is not causality, and
the word will not appear beside it. DEC-081 Q2 governs.

## 5. Micro to macro

The macro view is not a separate layer with its own rules. It is the same object summed:

```text
macro_edge(A -> B)  =  sum over sectors s, r  of  micro_edge((A,s) -> (B,r))
```

One definition, two scales. A macro edge can always be opened to show the sector pairs
composing it, which is what makes the macro view explainable by the micro view rather than
asserted alongside it.

## 6. Reconciled family names, binding from here

| canonical name | node types | direction | status |
|---|---|---|---|
| `flow` | ZE x sector -> ZE x sector, via `C[i,j]` | directed | observed |
| `precedence_intra` | same zone, sector to sector | directed | to be estimated |
| `precedence_cross` | across zones, sector to sector | directed | to be estimated |
| `comovement` | ZE x sector -> ZE x sector | undirected | candidate |
| `similarity` | **node attribute**, not an edge | -- | reclassified |
| `specialization` | **node attribute**, not an edge | -- | reclassified |

The mask entries `sector_to_sector_comovement` and `temporal_precedence_signal`, both
`unavailable` for all 14 years because they were never constructed, are the two this
specification builds. The mask must be regenerated against these canonical names, and any
layer whose name does not appear above does not render (DEC-082).

## 7. Gates, pre-registered

**R1 -- placebo, per family.** Each family is estimated a second time on data whose temporal
order is destroyed (years shuffled independently within each zone-sector series, preserving
every marginal). A family is admitted only if its surviving-edge count exceeds the shuffled
count **at the same threshold**, in at least **5 of 7** years. Families failing R1 are
excluded from the catalogue and from any figure.

**R2 -- seed and subsample stability.** Estimation is deterministic, so there is no seed. In
its place: re-estimate on 10 disjoint halves of the zones. An edge is admitted only if its
sign is stable in `>= 8/10` splits. This is the reproducibility check that DEC-091 and
DEC-094 failed, in the form available to a deterministic estimator.

**R3 -- noise floor for the 34.9% figure.** `HERALD_62` C4b measured observed inter-ZE
relations moving 34.9% over 2019-2025 and flagged that no noise floor had been estimated.
Before that number is used in any report, the same statistic is computed on Poisson resamples
of each cell at its observed mean. The reportable movement is the excess over that floor.

**R4 -- multiplicity.** 81 sector pairs x 7 years x 2 variants = 1,134 tests. Benjamini-Hochberg
control at q = 0.10, applied per year, fixed now rather than after seeing which edges survive.

## 8. What a pass authorises

A pass authorises describing a per-year, directed, placebo-surviving relational structure
over France ZE2020 x A10, at two scales, with declared weights and nulls.

It does **not** authorise: any causal claim, any automatic recommendation, any statement that
a neural model built this graph -- section 4 states plainly that a deterministic estimator
does -- or any forecasting claim. Whether these relations improve forecasting is a separate
question, deliberately deferred, and it is answered by feeding them to a predictor and
measuring, not by asserting.

## 9. Cross-reference

- Forecasting line closed: `HERALD_62` C1-C7, `HERALD_63` section 10, DEC-088 to DEC-094.
- Scope note that these results do not touch the relational layer: `HERALD_63` 10b.
- Availability mask and its rendering rule: `HERALD_57`, DEC-082.
- Commuting provenance and release-aware rule: DEC-073; empirical confirmation at r = 0.9914
  in `HERALD_62` C7a.
- Association versus causality: `HERALD_56`, DEC-081 Q2.
- Dashboard that will render the surviving layers: `HERALD_60`, DEC-087.
