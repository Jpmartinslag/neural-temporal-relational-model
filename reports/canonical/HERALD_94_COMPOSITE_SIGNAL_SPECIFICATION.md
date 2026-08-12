# HERALD 94 — Temporal representation, composite signals, and non-linear information

**Status:** specification, written before any result exists.
**Character:** strictly exploratory. Nothing in this stage licenses a causal, structural or
recommendation claim.
**Date:** 2026-08-12.

---

## 0. What this stage asks, and what it does not

Four questions, in order of dependency:

1. Do the temporal derivations — growth, acceleration, causal trend, momentum, volatility,
   regime, national component — add information beyond the level?
2. Do combinations of the existing signals form a new composite signal?
3. Does that composite carry **non-linear** information, absent both from the isolated
   signals and from a regularised linear combination of them?
4. Does that information help identify dynamic territorial associations?

The experiment must be able to answer *no* to any of them. It is not assumed that the
composite exists. A negative or middling result is a result and is documented as such.

### Why the questions are separated this way

HERALD 93 established two facts that constrain this design and are the reason the stage is
built in two layers rather than one.

**Fact one.** No method beat persistence on one-step log-growth (best skill `+0.0001`,
Graphical Granger). Log-growth at horizon one in this panel is dominated by measurement
noise; the autocorrelation lives in the level. A relational experiment built on that target
measures the ceiling of the target, not the ceiling of the method.

**Fact two.** HERALD's edge ranking in `S0_NULL` was statistically indistinguishable from
its ranking in `S1_SHARED` (AUPRC 0.7228 against 0.7254). Its apparent advantage over NRI
and Granger was the commuting prior echoed back through the scorer's `prior_ij` pair
feature, not a discovery. The truth is drawn inside the prior, so ranking by the prior
alone already scores above prevalence.

Consequently:

- **Layer 1** tests the instrument — questions 1, 2 and 3 — with **no graph at all**. It is
  a per-zone forecasting and information problem. If a composite carries no information
  about a zone's own future, it cannot carry information about that zone's relations, and
  no relational experiment is warranted.
- **Layer 2** tests question 4, and runs **only if Layer 1 passes**. It projects the prior
  out of the scorer before scoring, so that echoing the support is worth nothing.

## 1. Scope

Signals, from the existing panel: private salaried headcount; gross payroll; employer
establishments; localised unemployment rate; establishment creations. Active stock is
admitted only where the universe is semantically compatible with the signal it is combined
with; it is **not** used as a denominator for SIDE creations, because the two universes do
not coincide and the resulting "creation rate" would be an artefact of the mismatch. This
prohibition is enforced by a guard, not by convention.

Territory: the 280 mainland ZE2020 zones, Corsica excluded. The dashboard is not touched.

## 2. Temporal representation

For each signal `s`, zone `i` and decision period `t`, every feature is computed from
observations **released on or before `t`**. The panel is a retrospective final vintage with
one release date per source, so "released" means the publication lag has elapsed, and the
temporal index is checked by guard, not assumed.

The simulation and the panel share a quarterly grid; annual signals are observed at Q4.
Year-over-year differences therefore use lag 4 for every signal, which also removes
seasonality from the difference rather than modelling it.

Let `y_{s,i,t} = log(x_{s,i,t})` for count and volume signals, and the logit for the
unemployment rate. All features below are functions of `y` up to `t`:

| feature | definition | dim |
|---|---|---|
| `level` | `y_t` | 1 |
| `growth` | `y_t − y_{t−4}` | 1 |
| `acceleration` | `growth_t − growth_{t−4}` | 1 |
| `trend` | OLS slope of `y` on time over the last 12 released periods | 1 |
| `momentum` | `growth_t − mean(growth_{t−7..t})` | 1 |
| `volatility` | standard deviation of `growth_{t−7..t}` | 1 |
| `regime` | one-hot over {expansion, deceleration, contraction, recovery} | 4 |
| `national` | cross-zone mean of `growth_t` at period `t` | 1 |
| `relative` | `growth_t − national_t` | 1 |

Regime is defined by the sign pair `(growth, acceleration)`: expansion `(g>0, a≥0)`,
deceleration `(g>0, a<0)`, contraction `(g<0, a≤0)`, recovery `(g<0, a>0)`. It is a
deterministic function of two features already in the table, so it adds no information to a
model that can form products — which is precisely why the regime-conditioned composites
below are the interesting ones and the regime one-hot alone is not.

Eleven features per signal, five signals: 55 columns.

**Absence never becomes zero.** Zero is a legitimate value of a growth rate; using it to
mean "missing" would make a stagnant zone indistinguishable from an unpublished one, and
every arm here is linear or near-linear in its inputs, so the two would receive the same
response. Missingness is resolved in three declared steps, in order:

1. **carried forward within the zone**, from the last period at which the feature could be
   computed. Mixed frequency requires this rather than merely permitting it: the annual
   signals live at Q4 of a quarterly grid, so at Q1 the most recent employer establishment
   count is the one published at the previous Q4, and it is genuinely the best information
   available at that date. The availability channel is 1 only where the value is **fresh**,
   so a carried reading is distinguishable from a current one;
2. **cross-sectional median at that period**, for cells with no history to carry — the head
   of a series, before its observation window opens;
3. only a feature absent in **every** zone at that period becomes zero, and there its
   availability channel is zero too, which is what marks it absent.

Composites are formed **before** imputation, so that a product of two carried values is
flagged as such by its factors' channels rather than presented as fresh. Methodological breaks (2021–2023 for the
employment signals, 2018 for unemployment) and the COVID years are carried as calendar
indicators, exogenous and identical across zones, so that no method can read them as a
territorial event.

## 3. Composite signals

A small, pre-declared set, each with an economic reading stated **before** the results:

| id | definition | reading (hypothesis, not finding) |
|---|---|---|
| `C1` | `growth(payroll) − growth(headcount)` | wage per head |
| `C2` | `growth(headcount) − growth(establishments)` | employees per establishment |
| `C3` | `growth(creations)_{t−4}` against `growth(establishments)_t` | creations preceding stock |
| `C4` | `growth(headcount) × (−growth(unemployment))` | employment rising while unemployment falls |
| `C5` | `acceleration(payroll) − acceleration(headcount)` | wage intensity turning |
| `C6` | `growth(payroll) × regime(headcount)` (4 columns) | wages conditioned by employment regime |

No other combinations are generated. Exhaustive products of 55 columns would be a search,
not a hypothesis, and its best result would be a selection artefact.

**A fact that sharpens the whole test.** `C1`, `C2`, `C3` and `C5` are *linear* functions of
columns already in the feature table. A regularised linear model spanning that table
therefore contains them exactly, and they cannot improve it by even one unit of loss. Only
`C4` and `C6` are products, and only products can lie outside that span. So the question
"is the composite non-linear?" is not a matter of interpretation here: if a gain appears at
all beyond the linear arm, it must come from `C4`, `C6`, or an interaction the non-linear
arm found on its own. This is checked, not assumed: a guard asserts that adding `C1`, `C2`,
`C3`, `C5` to the ridge changes its out-of-sample loss by less than a declared tolerance.

**One qualification, found while building the guard and recorded before any result.** The
containment is exact only in cells where nothing was imputed. Composites are formed before
the missingness rules run, so in a carried or median-filled cell the composite and the
difference of the two imputed columns are two different numbers. Measured over all cells the
residual is about one per cent of the composite's own spread; restricted to zones where every
base column is fresh it is below `1e-6`, which is the claim in its exact form. The guard
therefore tests exactness on fully observed zones, and the tolerance on the linear-composite
arm's effect is set at 0.05 to cover the imputation gap. That gap is not an effect, and the
distinction matters: without it a one per cent artefact of the ridge penalty could have been
read as the named composites carrying information.

## 4. The arms

The target is the next-period year-over-year log-growth of the primary signal, evaluated
out of sample on rolling origins. Five arms, identical data, folds, seeds, origins and
masks:

| arm | model | purpose |
|---|---|---|
| `best_single` | one feature, chosen on the training folds only | the floor a composite must clear |
| `ridge_linear` | ridge over all 55 features | the linear span |
| `ridge_composite` | ridge over 55 features ∪ {`C4`, `C6`} | do the *named* interactions carry it? |
| `mlp_nonlinear` | one hidden layer, width 8, tanh | any smooth interaction |
| `duplicated` | ridge over 55 features with the best feature repeated | capacity control |

`best_single` is selected inside the training window and then frozen. Selecting it on the
evaluation origins would give the floor an advantage no other arm has and would make a
failure to beat it uninterpretable.

**Regularisation is selected identically for every arm**, on expanding-window folds inside
the training window: the training periods are cut into five contiguous blocks, and each fold
fits on the blocks before a block and validates on that block. The ridge penalty and the
network's weight decay and stopping epoch are all chosen this way, on the same folds, by the
same rule. Nothing is ever selected on the evaluation origins.

A single contiguous tail was the first design, and it was wrong in a way worth recording,
because it would have decided the study's headline result inside the fitting procedure. The
training window ends on 2020–2022 — COVID and the methodological breaks — so a lone tail fold
asks which penalty best fits an atypical era. On the pilot it ranked the network's five
weight decays in exactly the reverse of their true out-of-sample order, choosing the one that
overfitted hardest and turning a network that beat the ridge by 22 % into one that lost to it
by 26 %. Ridge barely noticed, its error being flat across its penalty grid; the network was
destroyed by it. The fix is structural — several blocks, spread across the window, asking the
question the evaluation actually poses — and it was verified on a smoke seed, never on a
final one. Every calibration decision in this stage was taken on seeds 9601–9602; the final
seeds 9701–9705 were not looked at before the grid ran.

### Why an MLP, and not a kernel

The hypothesis is that the target depends on the features through **thresholds and
interactions**. Three candidates were considered.

Kernel ridge with an RBF kernel fits any smooth function, but the design matrix has
`280 × ~100 = 2.8 × 10^4` rows per scenario, so the kernel is `10^9` entries — infeasible at
the grid size, before considering that it yields no per-feature marginal effect and so
cannot satisfy the explainability obligation of §7.

Gradient boosting fits interactions well but its response surface is piecewise constant, so
`∂f/∂x_j` is zero almost everywhere and the marginal effects requested in §7 would be
step artefacts of the split points rather than properties of the signal.

A one-hidden-layer network `f(x) = Σ_h a_h σ(w_h' x + b_h) + c` with `σ = tanh` is chosen
for three reasons, all mathematical rather than empirical:

1. **It nests the linear arm exactly.** Replacing `σ` by the identity gives
   `f(x) = (Σ_h a_h w_h)' x + const`, a linear function. The comparison `mlp_nonlinear`
   against `ridge_linear` is therefore a *nested-model* comparison: the non-linear arm can
   represent everything the linear arm can, so any deficit is optimisation and any surplus
   is curvature. Two unrelated model families would not permit that reading.
2. **Marginal effects are analytic.** `∂f/∂x_j = Σ_h a_h σ'(u_h) w_{hj}`, evaluated at any
   point, exactly and cheaply. Partial-effect curves are obtained by sweeping one coordinate
   with the rest held at their medians, with no surrogate model in between.
3. **Interactions are analytic and second-order exact.** For a single hidden layer,
   `∂²f/∂x_j ∂x_k = Σ_h a_h σ''(u_h) w_{hj} w_{hk}`, with `σ''(u) = −2 tanh(u) sech²(u)`.
   Averaging `|∂²f/∂x_j∂x_k|` over the evaluation sample ranks interactions directly from
   the fitted parameters. The question "which components create the gain" is answered by a
   closed-form quantity, not by an attribution heuristic.

Width 8 and one layer are fixed in advance. This is not an architecture search; §12 of the
governing instruction forbids one, and a wider net would trade the very tractability that
motivates the choice.

## 5. Synthetic validation, before anything else

Scenarios with known truth, generated by `generate_france_multisignal_v94`, which reuses
v92's territory, marginals, masks, breaks and observation models unchanged and replaces only
the propagation link:

| scenario | link | what it tests |
|---|---|---|
| `N0_NULL` | none | the false-positive floor |
| `N1_LINEAR` | `A_t @ centred(z_t)` | v92's mechanism, unchanged |
| `N2_NONLINEAR` | `A_t @ rectify(centred(z_t))` | only expansions propagate |
| `N3_REGIME` | `ρ(regime_i(t)) · (A_t @ centred(z_t))` | the receiver's own regime gates the transfer |
| `N4_INTERACTION` | `A_t @ (u_t ⊙ v_t)` | the propagated quantity is a product of two components |
| `N5_REDUNDANT` | as `N1`, all signals sharing one measurement noise | the duplicated channel |

`N2` uses `rectify(z) = max(z, 0) − E[max(z, 0)]`, re-centred so that the scenario does not
also shift the mean. It is not a linear function of `z` and no linear model in `z` can
represent it; that is the point.

`N3` gates the loading by the receiving zone's own regime, derived from its own observable
growth, so the mechanism is discoverable in principle from observables alone.

`N4` propagates `u ⊙ v` where `u` and `v` are two independent latent components, each
measured by a different subset of signals. Neither subset alone identifies the product. This
is the only scenario in which a non-linear composite of *distinct signals* is the unique
route to the mechanism, and it is therefore the scenario that can confirm or refute
hypothesis 3 in its strongest form.

The model never receives: the true graph, edge labels, the generator's latent variables, or
commuting as a discovery feature. Commuting enters only afterwards, as an external
comparison, and never as a scorer input in Layer 2 — the correction of HERALD 93's defect.

Relation births and deaths are inherited from v92's regime calendar, which moves weight
inside the support at the documented French breakpoints.

## 6. Controls

The composite is compared against, and must survive:

| control | construction | expected if the gain is real |
|---|---|---|
| best single feature | §4 | composite strictly better |
| linear combination | `ridge_linear` | composite strictly better |
| duplicated signal | best feature repeated | no gain |
| shuffled signals | signal identities permuted across zones | gain destroyed |
| destroyed temporal alignment | features permuted across periods within zone | gain destroyed |
| shuffled endpoints | source/target permuted (Layer 2 only) | gain destroyed |
| `N0_NULL` | no mechanism | no gain, no discovery |
| **interaction destroyed** | one factor of each product permuted across zones **within period**, preserving its marginal distribution and its period effect | gain destroyed while marginals survive |

The last control is the decisive one for hypothesis 3. Permuting a factor within period
leaves every marginal distribution, every cross-sectional moment and every period effect
untouched, and destroys only the alignment between the two factors. A gain that survives it
was never an interaction.

### Declared gate

The composite is called informative only if **all** hold:

1. out-of-sample loss below `best_single`, median across seeds and origins;
2. out-of-sample loss below `ridge_linear`;
3. the improvement holds out of sample, not only in training;
4. it holds in at least 4 of 5 seeds and in at least 8 of 12 origins;
5. it disappears under the interaction-destroyed control;
6. no gain in `N0_NULL`;
7. `duplicated` shows no gain.

Thresholds and seeds are fixed here, before submission, and are not edited after a result
is seen.

## 7. Mathematical explainability

The obligation of this stage is to explain the composite's behaviour **mathematically**. An
economic interpretation is not delivered here and is not the deliverable.

For each composite that clears §6, produced from the fitted parameters:

- the exact transformation, written as a formula;
- the signals and features entering it;
- weights, analytic gradients `∂f/∂x_j`, marginal effects and per-component importance;
- the response to each feature with the others held fixed;
- the interactions responsible for the gain, ranked by mean `|∂²f/∂x_j∂x_k|`;
- behaviour split by regime;
- ablation removing one signal at a time;
- temporal stability across origins;
- uncertainty across seeds and sensitivity to the training window.

Partial-effect curves and two-dimensional interaction surfaces are produced for the ranked
top pairs.

Three registers are kept strictly apart, and the report labels every statement with one:

1. **Mathematical finding** — "the interaction between payroll acceleration and employment
   growth added information out of sample."
2. **Economic hypothesis** — "this may represent a change in labour intensity." Plausible,
   unverified, and written **before** the results where the composite was declared, so that
   it cannot be reverse-engineered from what was found.
3. **Economic interpretation** — deferred to an economist or a domain specialist. Not
   produced here.

No economic explanation is invented after observing a result.

## 8. Models, Layer 2

Only if Layer 1 passes, and with the same folds, origins, seeds, masks and observables:
local baseline; Granger/Lasso linear; the selected non-linear method; HERALD; NRI; MTGNN.
Hidden widths 32, 64 and 128 only. Width 256 is not run.

The scorer no longer receives `prior_ij`. The candidate support still restricts *which*
pairs may be scored — that is a territorial constraint, not information about which of them
is true — but the ranking within the support must be produced from the residual after the
prior is projected out. This makes echoing the support worth exactly zero and is the direct
correction of the HERALD 93 defect.

## 9. Order of execution

1. Audit the current code.
2. Write this specification. *(done at this point)*
3. Implement the temporal features.
4. Implement one linear and one non-linear composite arm.
5. Guards and mutation testing.
6. Validate against observable oracles.
7. Smoke.
8. Full synthetic.
9. France, only if the synthetic passes and `N0_NULL` stays controlled.

After each block, verify that the code executes the mechanism this document describes.

## 10. French result, if authorised

Retrospective and exploratory. Permitted vocabulary: association; temporal precedence;
incremental information; non-linear pattern; predictive impact. Forbidden: causality; proven
economic influence; structural dependence; definitive territorial recommendation.

## 11. Deliverables

Canonical specification and DEC entry; code and tests; guards and mutants; control results;
a table of individual signals, linear composite and non-linear composite; ablations; the
mathematical explanation; economic hypotheses explicitly labelled as such; limitations; a
short report text; a lay explanation; commits, pushes and job identifiers.
