# HERALD 98 — Specification for the final model comparison

**Status: NOT RUN. No number from this comparison exists.** This document is written before
any result, for review. Nothing here may be cited as a finding, and no threshold in it may be
moved after a result is seen.

**Prerequisite:** explicit authorisation. The stage is frozen by HERALD 97 and DEC-146; this
specification is the first thing that would unfreeze it.

---

## 1. What this comparison is for

Three questions have been confused throughout the literature this project draws on, and
separating them is the point of the design:

- **A — temporal prediction.** Which method forecasts better than persistence, under one
  population and one protocol?
- **B — usefulness of territorial context.** Does the context of other zones improve the
  forecast *after* the local trajectory has been used?
- **C — relational recovery.** Does the method recover the true edges above chance?

A method may win A and fail C. HERALD 93 established that every method tested does exactly
that, and the final comparison exists to state it once, cleanly, on a single harder benchmark
rather than across four protocols that do not line up.

---

## 2. The benchmark

**One universe, not four.** The comparison runs on the HERALD 96 multirelational generator
scaled to **280 zones**, at `relational_scale = 1.0`, because it is the only benchmark in the
project where the truth is not drawn inside the commuting support:

| property | value |
|---|---|
| zones | 280 |
| periods | 1998Q1–2025Q4, quarterly, with the French release lags and breaks |
| signals | five, with their real availability windows and masks |
| scenarios | `M0_NULL` (no propagation) and `M1_MULTIRELATIONAL` |
| relation families | commuting-aligned, economic similarity, regime-gated complementarity |
| true edges | 140 per family, of which two thirds lie outside the commuting support |
| seeds | **9971–9975**, never generated before |
| origins | twelve rolling origins, identical for every method |
| folds | expanding-window, five contiguous blocks, one-standard-error rule |

`M0_NULL` is not optional and is not a smaller run: it carries the same seeds, the same
origins and the same budget. A method's score there is the single most informative number the
comparison produces.

**Why not also re-run the HERALD 93 universe.** It would double the cost to answer a question
already answered, and its prevalence of 0.70 makes recovery metrics hard to read. The HERALD 93
results stand as they are and are cited, not recomputed.

---

## 3. The three axes

### Axis A — temporal prediction

| arm | what it is | receives a graph? |
|---|---|---|
| Persistance | last observed growth | no |
| AR-Ridge | autoregressive ridge on the signal's own lags | no |
| Granger régularisé | graphical Granger by Lasso | learns one |
| Représentation temporelle | the validated 120-column table under a regularised linear model (HERALD 94) | no |
| MTGNN | graph-temporal forecaster that learns its adjacency | learns one |
| HERALD | the proposal | learns one |

**Question:** which method forecasts better than persistence under the same population and
protocol?

### Axis B — usefulness of territorial context

| arm | what it isolates |
|---|---|
| baseline temporel sans graphe | the floor: the local trajectory alone |
| commuting fixe | a graph that is given, not learned |
| Granger | a learned sparse graph, classical |
| MTGNN | a learned graph from a forecasting objective |
| NRI | a learned graph from a relational objective |
| HERALD | the proposal |
| Neural Granger résiduel | the additive per-source arm, **only if** it can be run on the same target |

**Question:** does the context of other zones improve the forecast after the local trajectory?

**The compatibility condition on the last row is binding.** The HERALD 96 arm predicts a
residual after a frozen local baseline. If the axis is run on raw growth, that arm is either
adapted to the same target or reported in a separate table with its own baseline — never
listed alongside the others with a different target. A footnote does not fix a target mismatch.

### Axis C — relational recovery

Arms: Granger/Lasso, MTGNN, NRI, HERALD, Neural Granger. Against: **oracle**, **null
scenario**, **prevalence**, and **permuted graphs** (derangement and degree-matched).

**Question:** does the method recover the true edges above chance?

---

## 4. Experimental fairness — fixed before execution

Identical for every method, and enforced by guards rather than intention:

- the same generated data, cell for cell;
- the same five signals and the same availability masks;
- the same temporal window and the same twelve origins;
- the same expanding-window folds and the same selection rule;
- the same five seeds;
- the same target, per axis;
- the same candidate supports where a support applies;
- the same causal information: nothing released after the decision date reaches any design;
- **no method receives the truth** — not the adjacency, not the latent state, not the
  relational component, not the edge labels;
- **no method receives information the others do not**;
- identical metrics, computed by one shared function;
- either an equal compute budget per method, or an explicit cost comparison reported beside
  every performance number.

**Declared asymmetries.** Some methods learn a graph and some are handed one. That is a
difference in kind, not in quality, and the two are reported in **separate categories**:

| category | arms | what its numbers mean |
|---|---|---|
| graphe donné | commuting fixe | an upper reference for what a fixed prior buys |
| graphe appris | Granger, MTGNN, NRI, HERALD, Neural Granger | comparable among themselves |
| aucun graphe | persistance, AR-Ridge, représentation temporelle | the floor |

A method with a given graph is never ranked against one that must find it.

**Widths.** 32, 64 and 128 only. 256 is refused by the constructors themselves and a guard
asserts it. No hyperparameter search: regularisation is selected per task on training folds by
the one-standard-error rule, which is a documented procedure, not a search.

**Seeds.** 9971–9975, generated for the first time. If any diagnosis requires reading their
out-of-sample error, they are retired and replaced, as 9701–9705 were in HERALD 94. There is
one repetition and no third grid.

---

## 5. Metrics

**Prediction**

- MSE, or the deviance appropriate to the signal's likelihood;
- MAE;
- skill against persistence;
- temporal stability: the spread across the twelve origins, not only their median;
- cost: seconds, peak memory, parameter count.

**Relations**

- AUPRC, always printed beside its own prevalence;
- edge F1 at a budget equal to the number of true edges in the support;
- dense correlation between scores and the true adjacency;
- response to intensity: the same measurement at 0.5×, 1× and 2×;
- the difference between the relational scenario and the null scenario;
- stability across seeds and across origins;
- recovery **inside** and **outside** the commuting support, reported separately.

---

## 6. Gates, declared now

A method may be reported as recovering relations only if **all** of these hold:

1. AUPRC exceeds its own prevalence by at least 0.05 in `M1`;
2. and does **not** exceed it in `M0_NULL`;
3. edge F1 ≥ prevalence + 0.10;
4. dense correlation ≥ 0.30;
5. the measurement is monotone across 0.5×, 1× and 2×;
6. stability across seeds ≥ 0.90;
7. the permuted-graph controls do not reproduce the result.

A method may be reported as beating persistence only if its median skill is positive and
positive in at least four of five seeds.

France is opened to relational output only if a method passes all seven gates **and** its
out-of-commuting recovery passes them separately. Nothing less is promotion.

---

## 7. Estimated cost

Scaled from measured HERALD 93 and HERALD 96 costs. Pairs grow roughly as the square of the
zone count for the dense supports, and the neural arms' cost grows roughly linearly in pairs.

| arm | measured | at 280 zones, per task | tasks | estimated total |
|---|---:|---:|---:|---:|
| Persistance | 1.4 s @280 | 2 s | 10 | 20 s |
| AR-Ridge | — | 5 s | 10 | 50 s |
| Représentation temporelle | 1 040 s @280 (H94) | 1 050 s | 10 | 2.9 h |
| Granger / Lasso | 5.5 s @280 | 8 s | 10 | 80 s |
| MTGNN @64 | 110 s @280 | 130 s | 10 | 22 min |
| NRI @64 | 326 s @280 | 380 s | 10 | 63 min |
| HERALD @32/@64/@128 | 348 / 323 / 1 367 s @280 | idem | 30 | 3.4 h |
| Neural Granger, union typée | 166 s @80, 3 208 paires | ≈ 700 s | 10 | 1.9 h |
| Neural Granger, navettes | 145 s @80, 2 762 paires | ≈ 600 s | 10 | 1.7 h |
| contrôles permutés (Axe C) | — | as the arm | 20 | ≈ 2 h |

**Total ≈ 16 h of CPU across roughly 130 array tasks**, comfortably parallel: one Slurm array
of 130 tasks at 1 CPU each finishes in the wall-clock time of its longest task, about 25
minutes, plus queueing. Peak memory stays under 1 GB per task, as measured.

`all_pairs` at 280 zones would be 78 120 ordered pairs and is **not** in the plan: it is kept
as an 80-zone diagnostic, where HERALD 96 already showed that containing every true edge does
not produce recovery.

---

## 8. Deliverables

One summary JSON per axis with the gate outcomes; three tables matching T04/T05 of the visual
archive; the figures the archive already specifies, regenerated against the new numbers; a
results document in `reports/canonical/`; and a DEC recording the decision on France.

Guards and mutants are written **before** submission, run inside the first task of every array
under `set -e`, and every mutant reinstates a concrete defect rather than stubbing a function.

---

## 9. What this comparison cannot settle

It runs on a synthetic panel. A negative result constrains what may be claimed about France; it
does not describe France. It uses one horizon and one primary target per axis. And it inherits
the ceiling HERALD 95 measured: on raw growth the whole relational mechanism is worth about 2 %
of squared error, so even a method that recovered it perfectly would win by two per cent. The
residual target of Axis B is where the larger prize — about 10 % — sits, and that is why the
axis exists.
