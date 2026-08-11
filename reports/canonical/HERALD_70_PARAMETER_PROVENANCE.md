# HERALD 70 -- Parameter provenance: what has a source and what I invented

**Date:** 2026-08-11
**Status:** `AUDIT_OF_OWN_CHOICES` (DEC-115)

Raised by the project owner: *with what basis did you set those values?* The answer, for most
of them, was my own judgement. This file separates the parameters that trace to published
sources from the ones that do not, and records where my invented value differs from the
literature value in a direction that mattered.

## 1. Parameters that DO have a source -- and where I was wrong to call them arbitrary

`train_herald_v7.py` defaults were described in DEC-090 and DEC-109 as "leak-era defaults,
never tuned". That is **incorrect for the core architecture parameters**, which match the
domain reference:

| parameter | V7 | source value | source |
|---|---|---|---|
| `hidden-dim` | 64 | 64 hidden channels | EconoGNN, best configuration |
| `lr` | 1e-3 | 1e-3 | EconoGNN; MTGNN `learning_rate` 0.001 |
| graph conv depth | 2 | 2 layers | EconoGNN; MTGNN `gcn_depth` 2 |
| optimiser | Adam | Adam | EconoGNN |
| top-k sparsification (the mechanism) | `topk_sparse_softmax` | "only the top K scores per row are kept to ensure sparsity" | MTGNN |

**Correction to DEC-109 item 7 and to my own framing:** the criticism that these were unjustified
is withdrawn for `hidden-dim`, `lr`, depth and optimiser. What was never tuned on the causal
panel is a separate and still-valid point; that is about search, not about provenance.

## 2. Parameters where the literature value differs from mine, and it mattered

### 2.1 Top-k -- both my values are wrong, in opposite directions

MTGNN uses `subgraph_size = 20` on `num_nodes = 207`, i.e. **k/N = 9.7%**. Scaled to the 280
zones per sector here, the literature-anchored value is **k ~ 28**.

| where | my value | k/N | against MTGNN's 9.7% |
|---|---|---|---|
| V7 `--top-k` | 10 of 280 | 3.6% | **2.7x too sparse** |
| HERALD_68 analogy | 50 of 280 | 17.9% | **1.8x too dense** |
| HERALD_69 primary (chosen from a sweep) | 10 | 3.6% | still 2.7x too sparse |

This is not academic. DEC-113 measured the relational effect against a corrected placebo at
K=5 +0.0031, **K=10 +0.0094**, K=20 -0.0013, K=50 +0.0026. The literature value sits at k~28,
between the two worst-performing settings I tested, and **K=10 -- the one I was about to
pre-register as primary in HERALD_69 -- was selected because it scored best, not because it has
a source.** That is selection on the outcome, the same defect DEC-105 9.1 recorded for the GBM
hyperparameters.

**Correction to HERALD_69:** K must be reported across the full sweep including **k = 28**, and
no single K may be designated primary on the basis of its score.

### 2.2 Temporal window -- 4 has no source, 5 does

`W_TRAJ = 4` in the analogy encoder was mine. EconoGNN's winning configuration uses **five
temporal windows**. MTGNN's `seq_in_len = 12` is 12 five-minute traffic steps and does not
transfer to annual data.

### 2.3 State threshold -- +-5% has no source, and the sourced value scores better

The Eurostat-OECD Manual on Business Demography defines a high-growth enterprise as **average
annualised growth above 20% over three years**, reduced to **10%** for international reporting;
the 10% figure is a legal requirement of the EU Business Statistics Implementing Regulation.

I used **+-5%**, described in HERALD_67 1 as chosen "with no justification beyond being round".

DEC-105 9.2 measured: +-3% 0.3794, **+-5% 0.3963**, **+-10% 0.4130**, terciles 0.4404.

**The threshold with a legal basis scores 0.0167 higher than the one I invented.** My arbitrary
choice was, measurably, suppressing the result. This is the clearest instance of the project
owner's objection being correct.

Caveat that must travel with any use of the 10% figure: the Eurostat-OECD definition applies to
*enterprises with 10+ employees over a three-year window*, not to a zone-sector cell year on
year. It is an anchor, not a transfer.

## 3. Parameters that still have no source

Listed so they are not mistaken for grounded choices. Each must either acquire a citation or be
reported as a sensitivity sweep rather than a fixed value.

| parameter | value | status |
|---|---|---|
| gate "5 of 7 years" | 5/7 | invented |
| seed-correlation threshold for "dynamic" | 0.90 | **invented and circular** -- derived from arm A's own 0.9967 |
| FLORES sector floor | median >= 50 employees | invented |
| top-k for the product metric | Precision@10 | invented |
| "deltas below 0.02 do not count" | 0.02 | measured protocol noise, but the rule was mine |
| number of lags | 2 | selected on the evaluation years |
| `huber-delta` | 300.0 | scale-dependent, no source; EconoGNN is a classifier and offers none |
| `smooth-lambda` | 0.01 | no source, and DEC-091 showed it is the term that froze the graph |

The 0.90 dynamism threshold is the worst of these: **the criterion was derived from the result
it was used to judge.** Every dynamism verdict resting on it -- DEC-091 arm D, DEC-094 G4 -- is
circular and must be re-stated against an externally motivated criterion.

## 4. Consequences

1. **HERALD_69 is amended before execution**: K swept including k=28; no K primary by score.
2. **The state threshold moves to 10%** as the anchored primary, with +-5%, +-20% and terciles
   as the declared sensitivity, and the Eurostat-OECD caveat of section 2.3 attached.
3. **The analogy window moves to 5**, matching EconoGNN.
4. **DEC-109 item 7's characterisation of V7's defaults is corrected** per section 1.
5. **All dynamism verdicts resting on the 0.90 threshold are marked circular** pending an
   external criterion.

## 5. Sources

- EconoGNN: *A graph neural network framework for temporal economic resilience insights*,
  PLOS One, <https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0343683>;
  internal reading in `reports/HERALD_ECONOGNN_TRANSFERABILITY_AUDIT.md`.
- MTGNN: Wu et al., *Connecting the Dots: Multivariate Time Series Forecasting with Graph
  Neural Networks*, KDD 2020, <https://arxiv.org/abs/2005.11650>; defaults read from the
  reference implementation `train_multi_step.py`.
- GConvGRU: Seo et al., *Structured Sequence Modeling with Graph Convolutional Recurrent
  Networks*, <https://arxiv.org/abs/1612.07659>.
- High-growth definition: Eurostat *Glossary: High-growth enterprise* and *High-growth
  enterprises - statistics*,
  <https://ec.europa.eu/eurostat/statistics-explained/index.php/Glossary:High-growth_enterprise>;
  OECD, *Understanding Firm Growth*, 2021.
