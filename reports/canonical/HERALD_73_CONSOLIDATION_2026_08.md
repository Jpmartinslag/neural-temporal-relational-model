# HERALD 73 -- Consolidation of DEC-088 to DEC-117

**Date:** 2026-08-11
**Status:** `CONSOLIDATION`. Reports no new measurement.

Thirty decisions across two days, five independent audits, and a large number of retractions.
This file is the single place to read what stands, what fell, and why -- ordered by what a
reader needs, not by when it happened.

## 1. What is established

| finding | evidence | entry |
|---|---|---|
| **A target leak invalidated the France neural line** | `y[t] = side_lag_1 x (1 + growth_1y)` reconstructs the target exactly, 3080/3080 and 3640/3640, max error 2.9e-11 | DEC-088 |
| Exploitation is model-class dependent | Ridge indifferent (0.0323 -> 0.0339, the reconstruction is a product a linear model cannot represent); V7 3.1x worse | DEC-088 |
| The prior leak audit could not have caught it | shuffling `y[t]` without recomputing features leaves the features encoding the original target; Ridge degraded 36.8x there too | DEC-088 |
| V7 at its defaults does not beat simple baselines | 0.0972 against Ridge 0.0727 and persistence 0.0746, 1/7 years, 7 origins, 5 seeds | DEC-090 |
| **V7's learned graph is the prior** | zeroing the learned term reproduces it at r = 0.9994; the "learned deviation" is 98.8% a softmax artifact | DEC-092 |
| The cause is prior dominance, not the smoothness penalty | removing the penalty raises movement only to 1.29%; the prior explains R^2 = 0.9641 | DEC-091 |
| Free structure learning is not identifiable here | five seeds give five graphs, r = 0.695 and 0.704 at two different scales | DEC-091, DEC-094 |
| **Inter-sector influence is not detectable** on any axis reached | A10 creations, A88 employment, legal-form split, and pooling 280 zones per pair | DEC-096, DEC-099 |
| Same-sector diffusion across commuting-linked zones survives | `BE->BE` over four years, +0.19 to +0.38, placebo-passed | DEC-096 |
| Same-sector analogy between territories survives | 0.3761 against the national sector mean's 0.3407, 6/8 years | DEC-099 |
| The unverified mobility prior is the official commuting file | r = +0.9914, addressing the HERALD_09 provenance concern | DEC-092 |
| **Per sector, three sectors are predictable and one is anti-predicted** | JZ +0.066, KZ +0.058, OQ +0.038 (6-7 of 7 origins); BE -0.053 (0/7) | DEC-112 |

## 2. What was retracted, and by whom

Five audits, three of them independent of me. Every retraction below was a claim I had already
written down.

| retracted claim | corrected by | what it actually is |
|---|---|---|
| "V7's deviation is real and dynamic" | my own remeasurement | `adj_delta_by_year` is unnormalised against an adjacency of norm 9.64 |
| "The 3.6% deviation is not optimisation noise" | DEC-092 | 98.8% softmax artifact; seeds agreed because the prior is identical across seeds |
| "Inter-ZE relations move 34.9%" | DEC-096 R3 | below its own Poisson floor of 40.7%; 116.8% accounted for by sampling |
| "Context features are harmful" | DEC-107 | delta 0.0159 against measured protocol noise of 0.012 |
| "Ceiling 0.655" | DEC-107, DEC-109 | a Poisson plug-in reliability reference; overdispersion phi 1.7-4.4 puts the real value at 0.50-0.58 |
| "A panel with no economics beats the real one" | DEC-112, DEC-113 | the null had 7,560 trend parameters fitted with knowledge of the targets; causal refit inverts it |
| "The relational block does not separate from placebo" | DEC-112 | the placebo re-weighted random neighbours by their true affinity; corrected, +0.0083 |
| "The graph is static" | DEC-108 | the implementation could not identify dynamics; it was explicitly penalised for moving |
| "The neural line fails" | DEC-108 | for count reconstruction Ridge is better; Ridge produces no relational structure, so it is not the architectural competitor |
| "V7's defaults are unjustified" | DEC-115 | hidden 64, lr 1e-3, depth 2, Adam all match EconoGNN and MTGNN |

## 3. Methodological defects found in my own work

Recorded because the pattern matters more than any single instance.

1. **A baseline that was never run.** Mean reversion. `corr(g[t-1], g[t]) = -0.32`, and a
   negated lag scores 0.3910 against the best model's 0.3942. The whole modelling apparatus
   was worth +0.003 (DEC-109).
2. **A contaminated control.** The relational placebo randomised neighbour selection and then
   restored identity through the weights. The tell was available and unused: a valid placebo
   cannot beat the no-relational base, and this one did (DEC-112).
3. **A circular criterion.** The 0.90 seed-correlation threshold for "dynamic" was derived
   from the result it judged (DEC-115).
4. **Selection on the evaluation set.** GBM hyperparameters, and K=10 chosen because it scored
   best (DEC-105, DEC-115).
5. **The wrong uncertainty.** Seeds instead of origins, on heavily overlapping folds
   (DEC-107).
6. **Invented constants.** Eleven parameters set by judgement; the +-5% threshold cost 0.0167
   against the Eurostat-OECD-anchored 10% (DEC-115).
7. **Specification and implementation diverging.** HERALD_72 had the right logic in its
   docstrings and four central functions never called (DEC-117).
8. **The same registration lapse twice.** DEC-088..105 and then DEC-114..116 existed only in
   canonical files, absent from this log.

## 4. What the project can defend today

**On the graph.** It is built by deterministic statistical estimation on an official observed
prior, not by a neural network -- and that is a measured conclusion, not a preference: two
attempts at letting a network build it produced a different graph per seed. Two families
survive their placebos.

**On prediction.** A three-state target at this grain is dominated by mean reversion. The
apparatus adds nothing detectable to a negated lag in aggregate, but the aggregate hides real
per-sector heterogeneity, and at the top of the territorial ranking the relational block beats
its own base (Precision@10 +0.0317, 7/7 origins, post-hoc).

**On the architecture.** A linear model is not the competitor, because it produces no
relational structure at all. The relational layer's standing rests on its own placebo-validated
structure, and now on one prediction task where relations demonstrably help.

**What may not be claimed.** A working classifier, a dynamic graph, a model-built graph, any
causal statement, or any automatic recommendation.

## 5. Open, in priority order

1. Rebuild HERALD_72 against the ten corrections of DEC-117 -- target leakage and `model.eval()`
   first, then the pre-registered `U diag(z_t) V^T` at rank 4.
2. Separate the propagation graph (top-k, bounded for identifiability) from the exported graph
   (cut by reliability, so weak-but-real edges survive), with hierarchical shrinkage.
3. Build and run the dynamism tests, which currently exist only as a docstring.
4. Deliver the graph artifact properly: three families, all source zones, `zfill(4)` IDs that
   join to the official commuting file, 2012-2025.
5. Re-run the corrected relational gate of DEC-114 with the DEC-115 amendments.
6. The dashboard.
