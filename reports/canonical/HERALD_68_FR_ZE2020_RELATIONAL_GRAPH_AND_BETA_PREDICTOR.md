# HERALD 68 -- Relational graph artifact and beta predictor

**Date:** 2026-08-11
**Sections 1-6:** `PRE_REGISTERED` (DEC-110). Written before the code existed.

## 1. Purpose

Deliver two objects the project needs and does not yet have as artifacts:

1. a **typed, per-year relational graph** over `ZE2020 x A10` nodes, built only from families
   that survived their placebos;
2. a **beta predictor** whose relational contribution is measured correctly.

"Beta" is meant literally: this establishes a foundation and a measurement protocol for
doctoral continuation, not a deployable model. Nothing here is expected to overturn DEC-109.

## 2. Every correction from DEC-107 and DEC-109 is binding here

| defect | correction applied |
|---|---|
| anti-persistence null never run (E1) | **`-g[t-1]` rank-matched is the primary baseline**, not persistence |
| no-economics null never run (E2) | matched synthetic panel is a **standing gate**, not an afterthought |
| random floor from previous year's prior (E3) | current-year marginal, ~0.3336 |
| Poisson ceiling assumed (E4) | negative-binomial with estimated phi; reported as a **reference**, never a ceiling |
| seeds used as uncertainty (DEC-107.3) | **paired-by-year deltas + block bootstrap over the 7 origins**; seeds only for reproducibility |
| relational block weakly encoded (DEC-107.5, E7) | top-50 same-sector, **distance-weighted**, neighbour affinity retained |
| relational block never tested on the standing config (E7) | it is the primary test here |
| pooled mean hides training-size trend (E6) | per-year table always reported alongside |

## 3. The graph

Nodes: `ZE2020 x A10`, 2,520 per year, 2012-2025.

Edges, typed, only families that passed their gates:

| family | source | weight | provenance |
|---|---|---|---|
| `flow` | official commuting, release-aware | commuter share | observed, DEC-073 |
| `diffusion` | same-sector precedence across commuting-linked zones | partial correlation | DEC-096, placebo-passed |
| `analogy` | same-sector trajectory similarity between zones | trajectory correlation | DEC-099 A1, placebo-passed |

Excluded by their own gates: `comovement` (window-fragile), inter-sector influence
(DEC-096, DEC-099), similarity as an interaction edge (DEC-095/098 chain).

Exported as `nodes.csv` and `edges.csv` with a `decision_year` column, so every edge is
reproducible from data available at that year.

## 4. The predictor and its two tasks

**Task A -- three-state classification.** Retained for continuity with DEC-100..106, and
scored against the mean-reversion null, not persistence.

**Task B -- within-sector cross-zone ranking.** *Which zones will this sector grow in?* This
is the live finding of DEC-109 (Spearman 0.379, and >= 0.31 in all seven years), it is the
product question, and it does not pass through a +-5% band whose choice moves the score by
0.061.

Both tasks: GBM, class-balanced where applicable, own history plus optionally the relational
block, 7 rolling origins 2019-2025, 20 seeds.

## 5. Gates

**G-A -- beat mean reversion.** The model must beat `-g[t-1]` rank-matched, on paired-by-year
deltas with a block bootstrap CI over the 7 origins excluding zero. Beating a stratified coin
is not evidence.

**G-B -- beat the no-economics null.** The same pipeline on a matched synthetic panel
(per-cell quadratic log-trend, negative-binomial with estimated phi, same class balance) must
score **no higher** than on the real panel. Current status from DEC-109: **fails**, 0.3942
against 0.4624. Reported either way.

**G-C -- the relational block must separate from its placebo.** Real neighbours against
matched random neighbours: same K, same summary statistics, same sector constraint. Paired by
year, block bootstrap CI. This is the test E7 showed was never run; DEC-109 measured +0.0176
at p=0.42 on a related configuration.

**G-D -- the graph must be usable without the predictor.** The exported artifact must render
edge counts per family per year against the availability mask, independent of any model
result. A relational layer that only exists inside a model is not a deliverable.

## 6. Reporting

`HERALD_62` B7 applies. In addition, fixed now: **if G-A or G-C fail, the graph artifact is
still delivered under G-D**, and the predictor is reported as a measurement protocol with a
null result rather than withdrawn. The doctoral argument rests on the protocol and the
delimited architecture, not on this model working.
