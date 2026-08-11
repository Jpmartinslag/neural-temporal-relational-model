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

---

## 7. Results (DEC-111)

Slurm 7859484, 16 CPUs, 20 seeds, 7 rolling origins. The mean-reversion baseline reproduces
DEC-109 E1 exactly at **0.3910**, confirming the harness is comparable and confirming that the
weaker previous-year-prior form used in a first draft (0.3713) would have flattered the model
by 0.02.

### 7.1 Per-year

| year | meanRev F1 | base F1 | rel F1 | placebo F1 | meanRev rho | base rho | rel rho | placebo rho |
|---|---|---|---|---|---|---|---|---|
| 2019 | 0.4040 | 0.3771 | 0.4217 | 0.4170 | 0.3936 | 0.3713 | 0.3705 | 0.3715 |
| 2020 | 0.3841 | 0.3802 | 0.3683 | 0.3516 | 0.3712 | 0.3117 | 0.3285 | 0.3246 |
| 2021 | 0.3864 | 0.3811 | 0.3809 | 0.3719 | 0.3964 | 0.4096 | 0.3797 | 0.3608 |
| 2022 | 0.3664 | 0.3278 | 0.3557 | 0.3325 | 0.3446 | 0.3614 | 0.3529 | 0.3488 |
| 2023 | 0.3322 | 0.3944 | 0.3504 | 0.3826 | 0.3439 | 0.3822 | 0.3411 | 0.3610 |
| 2024 | 0.4443 | 0.4460 | 0.4528 | 0.4598 | 0.3494 | 0.3591 | 0.3595 | 0.3706 |
| 2025 | 0.4196 | 0.4577 | 0.4704 | 0.4808 | 0.4139 | 0.4462 | 0.4435 | 0.4524 |
| **mean** | **0.3910** | **0.3949** | 0.4000 | 0.3995 | **0.3733** | **0.3774** | 0.3680 | 0.3700 |

Stratified random on the current-year marginal: **0.3343**.

### 7.2 Gates, paired by year with a block bootstrap over the origins

| gate | delta | CI95 | verdict |
|---|---|---|---|
| G-A model - meanRev (F1) | +0.0039 | [-0.0184, +0.0297] | inconclusive |
| G-A model - meanRev (rho) | +0.0041 | [-0.0208, +0.0250] | inconclusive |
| G-C relational - placebo (F1) | **+0.0006** | [-0.0128, +0.0127] | inconclusive |
| G-C relational - placebo (rho) | -0.0020 | [-0.0103, +0.0068] | inconclusive |
| relational - base (F1) | +0.0051 | [-0.0149, +0.0242] | inconclusive |

**No interval excludes zero.** The predictor has no demonstrated advantage over negating last
year's growth, on either task.

**G-B fails again at 20 seeds**: the no-economics synthetic panel scores 0.4523 (phi=1.0) and
0.4509 (phi=2.5) against the real panel's 0.3949.

**G-D delivers**: 17,640 nodes and 25,200 analogy edges exported with `decision_year` per row.

### 7.3 The one live lead did not replicate -- **WITHDRAWN, see DEC-112**

> This section is void. The placebo it relies on was contaminated: it randomised neighbour
> selection but weighted the random neighbours by their true affinity. Corrected, the lead
> replicates at +0.0083. The text below is kept only so the error remains visible.


DEC-109 E7 measured the relational block at **+0.0176** over a matched placebo on a related
configuration, at p=0.42. Under the pre-registered design here -- 20 seeds, distance-weighted
top-50, matched random-neighbour placebo, paired by year -- it is **+0.0006**.

This does not contradict the audit, which reported the result as not established. It confirms
that it was not established. The only live relational lead in the project does not survive its
own pre-registered test.

### 7.4 Standing statement

The predictor is reported as a **measurement protocol with a null result**, per section 6,
fixed before execution. What it establishes:

- a three-state target at this grain is dominated by mean reversion, and the modelling
  apparatus adds nothing detectable to a negated lag;
- ~~a panel containing no economics scores higher than the real one~~ **WITHDRAWN (DEC-112)**:
  the G-B gate fails under every synthetic variant including one with *positive* growth
  autocorrelation, so it does not measure noise reversion. Real lag-1 autocorrelation is -0.367
  against the null's -0.388, refuting "reality contains less";
- the relational block does not separate from a matched placebo.

The graph artifact stands independently under G-D and is the deliverable.
