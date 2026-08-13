# HERALD 96 — A Neural Granger / NAVAR arm on a multirelational universe

**Status:** specification, written before any result exists.
**Character:** strictly exploratory, synthetic only. "Relation" means a **directed, temporal,
predictive association**. No causal economic claim is made anywhere in this stage.
**Purpose:** to decide whether this formulation is a technically valid future direction — not
to produce a positive result.
**Date:** 2026-08-13.

---

## 1. Audit: what the previous stages actually established

Four facts were verified in the code and in the recorded results before this specification
was written. Each one constrains the design.

**The temporal baseline removes 11–24 % of the out-of-sample squared error.**
`hpc/herald94/summarize_layer1.py` computes it as the full 120-column table against the best
single feature; the reported medians across six scenarios are +0.106 to +0.245, with
`headcount.relative` the floor in every scenario and every seed. This is by far the largest
effect anywhere in HERALD, and it is entirely local — it describes a zone's own trajectory.

**The current scorer is trained only indirectly, through forecasting.**
`herald93_benchmark.train_neural` optimises `masked_gaussian_nll(output["prediction"], …)`
and nothing else. The scorer receives gradient solely because its edges feed a prediction.
Nothing in the objective asks the graph to be right.

**The model carries a node-only path.** `HeraldMultisignal.__init__` builds a `node_head`
whose output is summed with the relational one (line 567). The docstring's claim that there
is no node-only path refers to the relational *arm* internally. At the model level, a local
path exists, is far stronger than the relational one, and can absorb almost the whole task —
which is why the relational contribution was never forced to carry anything.

**The prior enters the scorer as a value.** `SharedRelationalScorer.forward` concatenates
`prior.unsqueeze(-1)` into its features, and `HeraldMultisignal` registers `prior_weight` as
a buffer for exactly that. Combined with a truth drawn inside the prior, this is what made
HERALD 93's `S0` and `S1` scores indistinguishable.

**Candidates are restricted to the 40 nearest commuting neighbours.**
`candidate_support(prior, k=40)`, in both HERALD 93 and 95. No relation outside commuting can
be found, or even considered, in any earlier stage.

**The relational ceiling at nominal scale is about 2 %.** HERALD 95's oracle, which knows the
true relational term, removes 1.8–2.5 % of the squared error at `1×` (per scenario: +0.0177,
+0.0194, +0.0254). The oracle is exactly zero without a mechanism and rises monotonically
with the scale. So the mechanism is observable and the ceiling is real but low.

### What that audit implies for this stage

Every one of the five design choices below follows from a specific finding above, not from
preference:

| finding | consequence for HERALD 96 |
|---|---|
| baseline removes 11–24 %, relational ceiling ~2 % | the relational arm must predict the **residual**, with the baseline frozen |
| a node-only path absorbs the task | **no node head, no local path** in the relational arm |
| the prior enters the scorer | commuting and similarity may **propose candidates only**, never enter as a value |
| candidates restricted to commuting | supports must be **compared**, including all-pairs |
| scorer trained only via forecasting | the edge score must be a **measured out-of-sample contribution**, not internal attention |

## 2. The multirelational universe

Three families, generated together, with positive and negative comparable pairs inside each:

**A. Commuting-aligned.** Propagation along the observed commuting support, as in v94.

**B. Economic similarity.** Pairs that resemble each other in a latent economic profile,
**independently of distance**. Deliberately includes pairs far apart and with no commuting
flow, so that a commuting-only support provably cannot contain them.

**C. Non-linear complementarity.** The source anticipates the target **only under a regime or
an interaction**: the contribution is gated by the target's own state, so a linear detector
averaging over all periods sees close to nothing.

Constraints, each enforced by a guard:

- no relation is reconstructible from any feature handed to the model. The similarity truth
  is drawn from a latent profile that is never exported; the observable similarity the
  candidate generator uses is a *noisy, causal* estimate of it, sufficient to propose pairs
  and insufficient to identify which are true;
- within each family, positive and negative pairs are matched on the quantities that could
  otherwise separate them trivially;
- `N0` contains none of the three and no hidden propagation.

### Supports compared

| support | content | where |
|---|---|---|
| `commuting_only` | 40 nearest commuting neighbours | 280 and 80 zones |
| `similarity_only` | top-k by causal observable similarity | 280 and 80 zones |
| `typed_union` | commuting ∪ similarity ∪ complementarity candidates, each edge carrying its **type label for reporting only** | 280 and 80 zones |
| `all_pairs` | every ordered pair | **80 zones only**, for cost |

Similarity is computed causally: from observations released before `t`, with the
normalisation fitted on the training window alone. The commuting and similarity weights
**propose** candidates and are never passed to the scorer as values. The model must find the
relation in the trajectories.

## 3. Frozen baseline and the residual target

1. Fit the HERALD 94 temporal baseline — level, growth, acceleration, trend, momentum,
   volatility, regime, national component, masks, breaks — on the training window.
2. **Freeze it completely.** Its parameters take no gradient during relational training, and
   a guard checks the parameter vector is bit-identical before and after.
3. The relational target is the residual:

   `residual[t+1] = observed[t+1] − baseline_local[t+1]`

   computed with the baseline's own frozen prediction, never refitted at an origin.
4. During relational training there is **no node head, no direct local path, and no baseline
   update**. The only route from input to prediction passes through another zone.

This is the structural correction to the third audit finding. If the arm cannot beat zero on
the residual, it has found nothing, and no local skill can disguise that.

## 4. The Neural Granger / NAVAR arm

Small, fixed and interpretable. No architecture search; width fixed in advance; 256 never
run.

1. Every source zone produces a **separate contribution** to each target zone.
2. The target's residual prediction is the **sum** of the contributions arriving at it —
   additive by construction, which is what makes a contribution attributable.
3. The contribution is produced by a **shared function** conditioned on the source's and the
   target's own histories, so there is no free per-pair parameter and no zone identity.
4. **Group penalty** over each source's contribution vector, so useless sources are switched
   off rather than shrunk unevenly.
5. **The edge score is the measured out-of-sample contribution of the source**, not internal
   attention. Concretely: the magnitude of that source's contribution to that target on held
   out origins. This is the direct correction of the fifth audit finding — HERALD 93's score
   was an internal quantity that never had to correspond to anything.
6. **Multi-horizon training at 1, 2 and 4 steps.** At one step the target's own history
   explains most of what is explainable; longer horizons force the arm to carry information
   the local baseline cannot.
7. The functional form, or the contribution's response to its input, is reported.

### Compared against

`granger_lasso` (linear, existing), `herald_scorer` (the current arm, unchanged),
`neural_granger` (residual, per-source non-linear), `navar_additive` (the additive variant,
sharing the same implementation where it genuinely coincides — no artificial duplication).

## 5. Oracles first — the stopping condition

Before any neural training, and per family:

- the mechanism is observable **in the residual target**;
- a true oracle beats the frozen baseline;
- the oracle responds monotonically across `0×`, `1×`, `2×`;
- `N0` shows exactly no gain.

**If the oracle fails, the stage stops there** and reports that the instrument cannot evaluate
the model. HERALD 95 established this discipline and it is not optional: without a working
oracle, a model's failure is uninterpretable.

## 6. Metrics

Residual out-of-sample gain; AUPRC against prevalence; edge F1; dense correlation; typed
births and deaths; stability across seeds; **recovery of edges outside commuting,
specifically**; gain per relation family; behaviour in `N0`; monotone response across `0×`,
`1×`, `2×`; multi-step performance. Cost and parameter count for every arm.

### An out-of-commuting relation counts as recovered only if

1. it is **absent from the commuting-only support**;
2. it is found by the all-pairs or typed-union arm;
3. it survives controls with shuffled endpoints and shuffled time;
4. it holds in at least **4 of 5** seeds;
5. it does **not** appear in `N0`.

All five, or it does not count. Fixed here, before execution.

## 7. Interpretation matrix

Declared before the results, applied as written:

| observation | reading |
|---|---|
| all-pairs recovers, union does not | the candidate generation is the problem |
| union recovers out-of-commuting relations | the multirelational direction is supported on synthetic |
| Neural Granger recovers, HERALD does not | the problem is HERALD's objective and scorer |
| both recover | compare frugality and stability |
| oracle passes, no model recovers | identification remains the bottleneck |
| `N0` produces relations | the method is invalid for discovery |
| only commuting is recovered | no evidence for non-local economic discovery |

## 8. Guards and mutants

Absence of future; the baseline is genuinely frozen; no node-only path; the residual is
computed correctly; the prior weight does not enter the scorer; out-of-commuting relations
exist in the synthetic truth; the model is able to consider them; all pairs really are
considered in the reduced synthetic; the group penalty acts on source contributions;
shuffling a source destroys its contribution; `N0` contains no hidden propagation; births and
deaths are typed; different arms execute different code; determinism; the same seeds and the
same paired worlds.

Mutants remove the real mechanism. None returns a fixed metric.

## 9. Execution order

Local validation → guards and mutants on the cluster → smoke (`N0`, one commuting relation,
one economic relation outside commuting, one non-linear interaction, one seed) → if the smoke
is technically valid, five final seeds → France only after the synthetic result.

## 10. France

Only if the synthetic recovers relations outside commuting, with `N0` controlled and
sufficient stability. Even then, retrospective and exploratory, using: predictive
association; temporal precedence; candidate relation; incremental contribution. Never:
causality, proven influence, or a definitive territorial recommendation.
