# HERALD 62 -- France growth-feature leak, and a pre-registered learned-graph experiment

**Date:** 2026-07-29
**Part A status:** `LEAK_CONFIRMED_FRANCE_NEURAL_LINE_INVALID_FOR_CLAIMS` (DEC-088)
**Part B status:** `PRE_REGISTERED_SPECIFICATION_NOT_YET_EXECUTED` (DEC-089)

Part A reports an executed diagnostic. Part B pre-registers an experiment and was written
before it ran.

---

# Part A -- The growth-feature leak

## A1. What was found

Two feature columns in the France panels are defined using the **target year**:

```text
growth_1y = (y[t] - y[t-1]) / y[t-1]
growth_2y = (y[t] - y[t-2]) / y[t-2]
```

Because `side_lag_1 = y[t-1]` is also a column, the target is recoverable by multiplication:

```text
y[t] = side_lag_1 x (1 + growth_1y)
```

| Check | Legacy panel | `strict_lag_only` panel |
|---|---|---|
| `growth_1y` matches the leaky definition | **3080 / 3080** | **3640 / 3640** |
| matches the causal definition | 0 / 3080 | 0 / 3360 |
| target rebuilt exactly from two columns | **3360 / 3360** | **3640 / 3640** |
| maximum absolute reconstruction error | 2.9e-11 | -- |

The `strict_lag_only` and `strict_no_source_flags` panels were produced by
`hpc/audit/prepare_herald_strict_exante_inputs.py`, whose `RIDGE_LAGS` list includes
`growth_1y` and `growth_2y` and which subsets columns without recomputation
(`out = df[existing(df, cols)].copy()`). The **strict ex-ante battery therefore carried the
leak**, as did the feature set of every model in the family: `feature_columns()` in
`train_herald_v6.py` begins with those five base columns, and `fit_ridge_ar` reads them
directly from the panel.

## A2. Whether the leak is exploited -- measured, not inferred

An algebraic leak is not automatically an exploited one. Both arms were measured on twin
panels **identical except for the two growth columns**.

| Learner | Panel as audited | Causal recompute | Effect of removing the leak |
|---|---:|---:|---|
| Ridge AR | **0.032304** | 0.033939 | none |
| MLP (64,32) | 0.056831 | 0.040479 | **improves** |
| HistGB | 0.364323 | 0.367016 | none |
| **V7 `graph_only`** | **0.019836** | **0.062339** | **3.1x worse** |
| **V7, no fills** | **0.021992** | **0.095615** | **4.3x worse** |

The Ridge figure `0.032304` reproduces the leak audit's reported Ridge exactly, which
validates the protocol.

V7 results: 5 seeds per arm, 800 epochs, `--device cuda`, Slurm jobs `7834174` and
`7834184`, 20/20 tasks COMPLETED. Separation is total -- the worst as-audited seed (0.0240)
is far better than the best causal seed (0.0747).

**The mechanism explains the pattern.** `y = lag1 x (1 + g1)` is a **product**. A linear
model cannot represent it, so Ridge is indifferent. Generic shallow learners did not find
it. V7 can represent products and loses 3-4x when it is removed.

**The ordering inverts.** Under leaky features V7 beats Ridge by 1.6x; under causal features
**Ridge beats V7 by 1.8x** (0.0339 against 0.0623).

## A3. Why prior leak testing did not detect it

The 2026-05-07 audit ran a target-shuffle stress test and concluded no direct leak. That
conclusion was correct **for the leak class it tested** and cannot detect this one.

Shuffling `y[t]` across zones **without recomputing the features** leaves the features
encoding the original `y[t]`. Every model then predicts the original value, and WMAPE
against the shuffled target explodes -- which is what happened, 36.8x to 158x, **including
36.8x for Ridge**. The test proves "the model does not copy the shuffled target". It cannot
prove "the model does not reconstruct the true target from its features".

A second signal was visible and unread: Ridge scored 0.0323 on the legacy panel and 0.0746
on the clean ZE-total panel. The same model, twice as good, purely by changing panel.

**Recorded as a reusable lesson:** a shuffle test must either recompute every derived
feature after shuffling, or be accompanied by a **feature-redefinition test**, which is what
found this.

## A4. Train/serve skew in the 2026/2027 forecast

`build_future_panel_rows` recomputes growth **causally** for future years
(`growth_1y = lag1/lag2 - 1`), while training and evaluation read the leaky panel column.

The model was therefore trained where `growth_1y` means "the change that will happen" and
served where it means "the change that already happened". Two different quantities in the
same input position. The 2026/2027 projections are not merely unvalidated -- they were
produced by a model operating outside its training regime.

Separately: those years **cannot be scored**. SIDE 2025 was published 2026-04-14 and the
panels end at 2025; calendar-year 2026 data publishes around April 2027.

## A5. Consequences

- The France neural line -- V6, V7, Semi SSL/noSSL, the Q0-Q12 family, Phase 2B/2H/2L/3/3E,
  SIDE5 -- is **`INVALID_FOR_CLAIMS`** as forecast evidence. `PENDING_REAUDIT` closes here
  with proof rather than suspicion.
- The `effectifs` versus `masse` preference reported in the Q7 audit is **weakened, not
  saved**: it was a comparison made where the model was largely reading the answer. It is a
  lead, not a result.
- Nothing in the clean ZE2020 line is affected: it never used these columns.

---

# Part B -- Pre-registered learned-graph experiment

**Written before execution. No metric from it exists.**

## B1. Why reopening is justified under the contract

DEC-081 Q3 permits another model experiment only on an exogenous sectoral structure
surviving a matched placebo. This experiment does not satisfy that clause and instead
invokes the reopening route: **a materially different situation established by new
evidence.**

Part A invalidates the evidence base on which the France neural line was assessed. Every
prior conclusion about that line -- positive and negative -- rested on panels containing a
reconstructable target. That is new information, not a change of preference, and it is what
justifies re-testing rather than re-tuning.

## B2. The question

> With the growth features defined causally, does a neural model with a dynamic graph beat
> persistence and Ridge on next-year A10 establishment creations -- and does the graph it
> learns correspond to anything real?

Two questions, deliberately separated. The second does not depend on the first.

## B3. Architecture decision, and why not free structure learning

The project owner's requirement is that **the model builds the graph**, not the analysts,
because a hand-built graph encodes arbitrary choices (top-5, three-year minimum, a
correlation threshold) that nothing justifies.

Free structure learning is nonetheless rejected here: 280 zones give 78,120 possible
directed edges against roughly 3,900 observations. DEC-046 already classified NRI/GTS-style
structure learning as `FUTURE_ONLY` for this reason and asked for T >= 25; the panel has 14
years. A model given that freedom will find structure that is not there, and this is
arithmetic rather than opinion.

**Adopted: an auditable prior plus a learned deviation** -- what V7 already does. The prior
stops being an analyst's parameter and becomes an official statistic; the deviation is the
model's own. Evidence that V7's deviation is real and dynamic already exists: it weights
mobility 0.926 against geography 0.156, and `adj_delta_by_year` peaks at 1.22 and 1.14 in
2020 and 2021.

> **Retraction, added 2026-08-10 (see Part C, C4 and C4b).** The second half of the sentence above is
> withdrawn. `adj_delta_by_year` is an unnormalised Frobenius norm of the year-to-year
> difference; the adjacency itself has norm ~9.64, so a peak of 1.22 is roughly 7% relative
> movement, not evidence of a dynamic graph. Measured as correlation, the learned adjacency
> moves 0.06% between 2019 and 2025 (r = 0.9994). The mobility-over-geography weighting is
> confirmed (0.918 against 0.146) and stands. **The claim that the deviation is dynamic does
> not.**

## B4. Variants, frozen

All use causally recomputed `growth_1y` and `growth_2y`.

| Variant | Prior adjacency | Purpose |
|---|---|---|
| `V-base` | current `graph_adjacency_core_v0` + `graph_adjacency_mobility_v0` | the corrected baseline of the existing line |
| `V-official` | official INSEE commuting (DEC-073), release-aware | replaces two files whose generator is **not found in the tree** (`HERALD_09`: provenance unverified) with an audited source |
| `V-free` | none; adjacency learned from scratch | the owner's pure version, run **as a falsification of B3's warning**, not as a candidate |

## B5. Protocol

- **Rolling origin over 2019-2025**: seven evaluation years, not the two the strict battery
  used. Two points cannot separate "the model learns as history accumulates" from "2025 is
  an easier year" -- and persistence, which learns nothing, improves 33% from 2024 to 2025,
  so that confound is real and measured.
- 5 seeds per variant per year.
- Baselines on identical populations: `persistence`, `ridge_ar`.
- Causal integrity: every prediction for `t` uses only data through `t-1`, verified by the
  target-mutation test of DEC-084 -- **not** by target shuffle alone, per A3.

## B6. Gate, pre-registered

**Forecast gate.** A variant is designated only if it beats **both** persistence and Ridge
on aggregate WMAPE **and** in at least **5 of 7** years, with no A10 sector regressing more
than 10% against the better baseline. Ties count against the challenger.

**Learning-slope test**, answering the owner's hypothesis. Fit a linear trend to each
model's yearly WMAPE across the seven origins. The claim "the neural model improves as
history accumulates" is supported only if its slope is negative **and** steeper than
persistence's, with the sign stable across seeds. Persistence improving in parallel
falsifies the claim.

**Graph-correspondence test**, and this is the part that does not depend on forecast gain.
The learned adjacency is compared against the **audited relational layer the model never
saw** -- official commuting edges and the `ze_similarity` family:

| Outcome | Reading |
|---|---|
| learned graph agrees with official commuting above a matched random baseline | convergent evidence from two independent routes |
| disagrees but is stable across seeds and years | a structure of its own; a finding to investigate, not to interpret economically yet |
| varies with seed | optimisation noise, and demonstrated as such |

Controls: node permutation, temporal shuffle, seed stability. Agreement is measured against
a **matched random adjacency of the same density**, since any two graphs overlap somewhat.

## B7. Reporting rule, fixed before results

Agreed with the project owner in advance, because the temptation arises only afterwards:

> If the forecast gate fails, the learned relations and the predictions may be reported as a
> **direction for future work**. The failure of the gate must be stated explicitly in the
> same place. Framing a negative result as an open direction is legitimate; omitting that it
> failed is not.

This applies equally to the learning-slope and graph-correspondence tests.

## B8. What a pass would and would not authorize

A pass authorizes describing a neural model with a dynamic graph, evaluated causally over
seven origins, that beats both baselines on this target. It does **not** authorize a causal
claim, an automatic recommendation, or extending the result beyond France ZE2020 x A10.

A failure closes the corrected France neural line for forecasting and leaves the learned
graph as an open question, reportable under B7.

## B9. Cross-reference

- Contract and Q3: `HERALD_56`, DEC-081.
- Engine and the target-mutation test: `HERALD_58`, DEC-084.
- Eight closed relational gates: DEC-069 to DEC-080.
- Structure learning deferred for short T: DEC-046.
- Official commuting provenance: DEC-073, `HERALD_44`.
- Adjacency files with unverified provenance: `HERALD_09`, `HERALD_16` section 4.1.
- Prior leak audit: `reports/HERALD_LEAK_AUDIT_FINAL_20260507.md`.
- Publication calendar: `reports/HERALD_DATA_AVAILABILITY_CALENDAR.md`.

---

# Part C -- Executed results, and a pre-registered dynamism ablation

**Date:** 2026-08-10
**C1-C4 status:** `EXECUTED` (DEC-090)
**C5 status:** `PRE_REGISTERED_NOT_YET_EXECUTED` (DEC-091), written before any C5 metric existed.

Source: Slurm `7834211` (10 tasks) and `7834221` (5 tasks), causal panel, 7 rolling origins
2019-2025, 5 seeds, `--device cuda`, 30/30 COMPLETED. **Executed by the meso copy of
`train_herald_v7.py` (653 lines, md5 `117bd1a705fc9b2052413f9dba6fae11`), not the
1041-line working-tree copy** (md5 `fa68d3157d94c9c2a70de8de5e64c3e5`). The graph
construction and smoothing paths were verified identical between the two before any
conclusion below was drawn.

## C1. Forecast gate -- FAILED

Mean WMAPE per evaluation year:

| model | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | mean |
|---|---|---|---|---|---|---|---|---|
| `ridge_only` | 0.0438 | 0.1150 | 0.0604 | 0.0861 | 0.1359 | 0.0302 | 0.0377 | **0.0727** |
| persistence | 0.1319 | 0.0396 | 0.1432 | 0.0337 | 0.0357 | 0.0826 | 0.0554 | **0.0746** |
| `graph_only` | 0.0645 | 0.1305 | 0.0840 | 0.1554 | 0.1199 | 0.0810 | 0.0452 | **0.0972** |
| `fixed_alpha_0.5` | 0.0497 | 0.1307 | 0.1046 | 0.1376 | 0.1294 | 0.1043 | 0.0518 | 0.1012 |

`graph_only` loses to both baselines on aggregate and wins 1/7 years against Ridge, 4/7
against persistence. The B6 gate required beating both, plus 5/7. **Failed.**

## C2. Learning slope -- does not distinguish the neural model

Persistence WMAPE equals the year-over-year change magnitude by construction, so it doubles
as an objective difficulty index for each year. Both learners' errors *fall* as the year
gets less stable (`r = -0.588` Ridge, `-0.583` neural): they are specialists of unstable
years, and persistence wins the three flattest years (2020, 2022, 2023).

| model | raw time slope | slope after controlling for year difficulty |
|---|---|---|
| `graph_only` | -0.0043 /yr | **-0.0106 /yr** (5/5 seeds negative) |
| `ridge_only` | -0.0040 /yr | **-0.0105 /yr** (5/5 seeds negative) |

The improvement over time is real and survives the difficulty control -- **and is identical
for a linear model refitted each year.** It reflects accumulating training data, not the
dynamic graph. The B6 criterion required the neural slope to be steeper than persistence's
(-0.0090 raw); it is not.

## C3. Ex-ante blending -- the neural weight goes to zero on its own

Convex blends with `w` fitted **only on years strictly before `t`**, evaluated 2021-2025:

| blend | mean WMAPE | beats best single model |
|---|---|---|
| `ridge + persistence` | **0.0679** | 1/5 years |
| persistence alone | 0.0701 | -- |
| Ridge alone | 0.0700 | -- |
| `neural + persistence` | 0.0718 | 0/5 years |
| `neural + ridge` | 0.0728 | 0/5 years |

In `neural + ridge` the fitted weight on the neural model is **0.00 in 2023, 2024 and 2025**.
An automatic procedure with no access to the test year discards it. No blend containing the
neural model beats its own components.

## C4. The learned graph -- stable, but static, and mostly the prior

| measure | value |
|---|---|
| R^2 of [geo, mobility] priors explaining the learned adjacency | **0.9641** |
| learned deviation as share of variance | **0.0359** |
| seed stability of the full adjacency (pairwise r) | 0.9967 - 0.9993 |
| seed stability of the **residual** deviation (pairwise r) | **+0.9834** (min +0.9696) |
| adjacency correlation 2019 -> 2025 | **0.9994** |
| residual correlation, consecutive years | 0.999 everywhere except **0.959** (2020->21) and **0.954** (2021->22) |

Two findings, opposite in sign:

- **Positive.** The 3.6% deviation is *not* optimisation noise. Five independent seeds
  converge on the same structure (r = 0.983), and it shifts measurably in exactly the
  2020-2022 window. This passes the B6 seed-stability control.
- **Negative.** The graph is 96% the prior it was given, and it does not move.
  **"The model builds the graph" is not supported by this implementation**; it inherits one.

Correspondence against *independent* official commuting (DEC-073) could not be run: the
mobility prior is already commuting-derived and the residual is orthogonal to it by
construction (`r = -0.0000`, matched-random null sd 0.0036). That test remains open.

### C4b. Why the graph is static -- the architecture, not the territory

The loss contains an explicit temporal-smoothness penalty on the adjacency
(meso copy, lines 192-193 and 356):

```python
delta_sq  = torch.sum((A_t - A_prev) ** 2)
regime_weight = torch.tanh(reg_delta)
smooth_term  = smooth_term + delta_sq * (1.0 - regime_weight)
...
loss = ... + args.smooth_lambda * graph_losses["smooth_term"]   # default 0.01
```

The model is penalised for changing the graph, with the penalty released only when the
regime vector moves -- which is why the sole observed movement sits in 2020-2022.

An independent measurement rules out the alternative explanation that inter-ZE relations are
simply stable. Building an observed ZE x ZE relation matrix from A10 composition similarity
(cosine over 9 sector shares, from `y_true_sector`, outside the model entirely):

| | 2019 -> 2025 | movement |
|---|---|---|
| observed relations | r = 0.6514 | **34.9%** |
| model adjacency | r = 0.9994 | **0.06%** |

A factor of roughly 580. **Two caveats, stated because they are not yet controlled:** the
observed matrix is a different relation definition from the model's commuting-prior
attention, and no noise floor has been estimated for small ZEs, so part of the 34.9% may be
sampling variation. Neither can account for two orders of magnitude, and the direction is
unambiguous.

A second structural gap: the adjacency is **ZE x ZE only**, 280 nodes, with no sector
dimension. `sector_proportions` is a separate `(280, 9)` tensor that never enters the graph.
Sector-to-sector relations are therefore not modelled at all.

## C5. Dynamism ablation -- pre-registered, written before execution

Slurm `7834544`, 10 tasks, causal panel, same 7 origins, 5 seeds, `variant=graph_only`.

| arm | `--smooth-lambda` | `--prior-strength-init` |
|---|---|---|
| A (reference, reuses `7834211`) | 0.01 | 1.0 |
| B | **0** | 1.0 |
| D | **0** | **0.1** |

A third arm disabling the regime valve was specified and then **dropped before launch, not
after seeing results**: the loss term is `smooth_lambda * smooth_term`, so at
`smooth_lambda = 0` the valve has no effect and that arm is arithmetically identical to B.

**Both quantities are reported for every arm**, and the two questions are separate:

1. **Does it move?** Adjacency correlation 2019 -> 2025, against the observed 0.6514 benchmark.
2. **Does it help?** WMAPE under the unchanged C1 gate: beat persistence *and* Ridge on
   aggregate, and in >= 5 of 7 years, no A10 sector regressing more than 10%.

**Noise control, fixed in advance.** Releasing the penalty over 78,120 possible directed
edges with ~3,900 observations is the risk DEC-046 flagged. Movement counts as structure
only if seed-pairwise correlation of the adjacency stays **>= 0.90**, the threshold used
because arm A reaches 0.9967. Below it, the movement is reported as optimisation noise.

**Interpretation, fixed in advance so it cannot be chosen afterwards:**

| moves | forecast improves | reading |
|---|---|---|
| yes | yes | dynamic graph supported; C1 reopens |
| yes | no | the rigidity was load-bearing; a real negative result about the problem |
| no | either | the penalty was not the binding constraint; look to the prior's 96% dominance |
| yes, seeds disagree | either | optimisation noise, reported as such |

B7 continues to apply to every outcome above.

## C6. C5 results -- executed

**Status:** `DYNAMISM_ABLATION_FAILED_PENALTY_NOT_BINDING` (DEC-091 result).
Slurm `7834544`, 20/20 tasks COMPLETED. Written after C5's criteria were fixed.

### Movement and seed stability

| arm | r 2019 -> 2025 | movement | seed-pairwise r | verdict under C5 |
|---|---|---|---|---|
| A (`smooth=0.01`) | 0.9994 | 0.06% | 0.9967 | static |
| B (`smooth=0`) | 0.9871 | **1.29%** | 0.9303 | static |
| D (`smooth=0`, `prior=0.1`) | 0.9796 | **2.04%** | **0.6951** | **noise** |
| observed benchmark | 0.6514 | **34.86%** | -- | -- |

### Forecast, against each baseline separately

Persistence 0.0746, `ridge_only` 0.0727.

| arm | aggregate | wins vs persistence | wins vs Ridge |
|---|---|---|---|
| A | 0.0972 | 4/7 | 1/7 |
| B | **0.0921** | 4/7 | 1/7 |
| D | 0.1006 | 4/7 | 0/7 |

No arm passes the gate.

### Reading, taken from the C5 table without modification

Arm B lands on **"no movement, either forecast"**: removing the smoothness penalty raises
movement 20-fold yet leaves it 27x short of the observed benchmark, so the penalty was
**not the binding constraint**. The prior's 96.4% dominance of the softmax is.

Arm D lands on **"moves, seeds disagree"**: weakening the prior does free the graph further,
and the five seeds then converge on *different* structures (r = 0.695, below the 0.90
threshold fixed in C5). This is the DEC-046 risk measured rather than assumed -- with 14
years and 280 nodes, structure learned from a weakened prior is not reproducible.

**Neither arm authorises the term "dynamic graph".**

### What is established, stated positively

1. Inter-ZE relations move ~35% over 2019-2025; they are **not** stable (C4b).
2. This architecture moves 1.3% with its brake fully released.
3. The cause is prior dominance in `topk_sparse_softmax(raw + prior_logits, top_k)`,
   not the temporal penalty.
4. Releasing the prior yields seed-unstable structure.

Point 4 answers the design question directly: **on this data, the model cannot build the
graph on its own reproducibly.** That is a measured limit, reportable under B7, and it
bounds what any future variant on 14 years of ZE2020 can claim.

### Note on provenance

An arm disabling the regime valve was specified in C5 and dropped before launch on the
arithmetic that `smooth_lambda = 0` nullifies `smooth_term` entirely. Two launch failures
preceded the successful run (`7834514`, `7834529`): Slurm `--output` pointed at node-local
`/tmp`, and the meso copy lacks `--smooth-regime-source`. Neither altered the registered
arms A/B/D.

## C7. Graph-correspondence test, and a retraction of C4's positive finding

**Status:** `NO_MEASURABLE_LEARNED_GRAPH_CONTENT` (DEC-092). Executed 2026-08-10.

Official commuting: `fr_ze2020_commuting_edges.csv.gz` (DEC-073), observation year 2017
(latest with `observation_year <= 2018`), self-loops and unavailable rows dropped,
`origin_interze_share` as weight, 27,683/27,683 edges mapped onto the 280 model nodes.

### C7a. The unverified prior is empirically the official source

| pair | correlation |
|---|---|
| mobility prior vs official commuting | **+0.9914** |
| geo prior vs official commuting | +0.6539 |
| learned adjacency vs official commuting | +0.9578 |

`HERALD_09` flagged `graph_adjacency_mobility_v0.csv` as having a generator not found in the
tree. This does not establish provenance, but it is strong empirical evidence that the file
is the audited commuting source. Recorded as a partial resolution of that concern.

### C7b. The correspondence signal is a softmax artifact

Correlating the learned deviation with the part of official commuting not explained by the
priors gives `-0.3403`, z = -87 against a matched-random null, same sign in 5/5 seeds. That
null rules out chance but **not** the row-normalising `topk_sparse_softmax`, which compresses
high values and can induce negative correlation mechanically.

The control rebuilds the adjacency with the learned gammas and **the learned term set to
zero** -- `topk_sparse_softmax(0.146*log(geo+1e-6) + 0.918*log(mob+1e-6), k=10)`, no training
whatsoever:

| | corr with official residual |
|---|---|
| trained model | -0.3403 |
| **prior only, zero learning** | **-0.3376** |
| **attributable to learning** | **-0.0027** |

### C7c. Retraction of C4's positive finding

| | |
|---|---|
| corr(trained adjacency, prior-only softmax) | **+0.9994** |
| corr(learned residual, prior-only residual) | **+0.9882** |

C4 recorded as its one positive result that the 3.6% deviation was "not optimisation noise"
because five seeds converged on it (r = 0.983). **That reading is withdrawn.** The deviation
is 98.8% the nonlinearity of the top-k softmax acting on the prior. The seeds agree because
the prior is identical across seeds, not because they learned the same structure. Seed
agreement was treated as evidence of learning when it was absence of variation in the input.

After 800 epochs, the adjacency is reproducible to r = 0.9994 with the learned term zeroed.
**The graph carries no measurable learned content**, and the B6 correspondence table does not
apply -- there is no deviation to compare against anything.

### C7d. Consequence for the reopened line

Combined with C6, the corrected France neural line closes with:

- no forecast gain over persistence or Ridge (C1, C6);
- no learning signal distinguishable from a refitted linear model (C2);
- zero weight in ex-ante blends (C3);
- a graph that is the prior, does not move, and contains no learned content (C4b, C6, C7).

B7 still governs how this is written up: the learned relations and predictions may be
presented as a direction for future work, provided the failure is stated in the same place.
What may **not** be claimed is a dynamic graph, a model-built graph, or convergent validation
against official commuting.
