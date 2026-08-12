# HERALD 94 — Composite signals and non-linear information: results

**Character:** strictly exploratory. Nothing here licenses a causal, structural or
recommendation claim.
**Specification:** `HERALD_94_COMPOSITE_SIGNAL_SPECIFICATION.md`, written before any result.
**Jobs:** 7865228 (validation), 7865232 (fairness recheck), 7865233 (first grid, retired
seeds), 7865263 (the grid this document reports). Commit `9aba983`, environment `herald-v5`.
**Date:** 2026-08-12.

---

## 1. Headline

Temporal representation adds a great deal. Composite signals add nothing. The non-linear arm
does not beat a well-regularised linear model, and the curvature it does find is present in
the scenario that has no territorial relation at all.

`layer2_authorised = False`. No composite cleared the gate in any scenario containing a
mechanism, and the relational layer is not run.

## 2. What ran

Six scenarios by five seeds, 280 mainland ZE2020 zones, twelve rolling origins, thirty tasks,
all `COMPLETED`, median 1041 s each. Five arms plus a structural-null arm, identical data,
folds, seeds, origins and masks. Twenty-five guards pass; twenty-four mutants, one per
mechanism and none a constant-returning stub, are all killed. Two identical runs agreed
exactly on every arm.

The network has 977 parameters at width 8; the linear arm has 121.

## 3. The four questions

### 3.1 Do the temporal derivations add information? **Yes, substantially.**

The best single feature is `headcount.relative` — year-over-year growth minus the national
component — in every scenario and every seed. Against it, the full 120-column table under a
regularised linear model removes this share of the squared error out of sample:

| scenario | median gain | per seed |
|---|---|---|
| `N0_NULL` | +0.235 | 0.301, 0.235, 0.120, 0.296, 0.135 |
| `N1_LINEAR` | +0.245 | 0.289, 0.245, −0.324, 0.254, 0.100 |
| `N2_NONLINEAR` | +0.215 | 0.317, 0.215, 0.132, 0.154, 0.226 |
| `N3_REGIME` | +0.218 | 0.312, 0.212, 0.177, 0.234, 0.218 |
| `N4_INTERACTION` | +0.240 | 0.240, 0.263, 0.052, 0.240, 0.117 |
| `N5_REDUNDANT` | +0.106 | 0.106, 0.179, 0.097, 0.271, −0.050 |

Roughly a fifth to a quarter of the error, consistently, in every scenario including the
null. **This is a property of the representation, not of any mechanism** — which is exactly
what one should expect, because growth, acceleration, trend, momentum, volatility, regime
and the national component describe a zone's own trajectory and say nothing about its
neighbours.

This answer reversed under the correction described in §5, and the reversal is the single
most important methodological fact in this stage. On the first grid the same quantity was
**negative** in all six scenarios, between −0.02 and −0.10: the full table appeared to lose
to one feature. It did not. The linear arm was under-regularised, selecting penalties between
1 and 100; under the one-standard-error rule it selects 1e3 in seven tasks and 1e4 in
twenty-three. A poorly regularised linear arm made the temporal features look worthless and
would also have flattered every comparison made against it.

### 3.2 Do combinations of the existing signals form a new composite? **No.**

The arm carrying the two product composites `C4` and `C6` — the only two that provably lie
outside the linear span — fails `beats_ridge_linear` in all six scenarios. Its median effect
is *negative* everywhere, between −0.003 and −0.008.

The four composites that are linear functions of existing columns move the linear arm by
−0.008 to −0.016, within the 0.05 tolerance declared for the imputation gap. The pre-declared
structural claim holds: they cannot help, and they do not.

### 3.3 Is there non-linear information the linear combination misses? **Not
demonstrably, and what is there is not an interaction.**

The network beats the linear arm in only 2 or 3 of 5 seeds in every scenario, against a
declared requirement of 4. It fails `holds_in_enough_seeds` in all six. Per-seed gains over
the linear arm remain wide — `N3_REGIME` runs from −2.329 to +0.086 — so even after the
correction the fitting is not stable enough for a median to be read as a finding.

The decisive control settles the question anyway. One factor of each declared product is
permuted across zones within period, preserving every marginal distribution, every
cross-sectional moment and every period effect, destroying only the alignment between the two
factors. The share of the gain that survives:

| scenario | surviving share | declared ceiling |
|---|---|---|
| `N0_NULL` | **0.993** | 0.30 |
| `N4_INTERACTION` | **0.501** | 0.30 |

Essentially all of it survives in the null and half of it in the scenario built around a
product. On the first grid the surviving share was *above one* — destroying the alignment
made the network better, which is what one would see if those columns were contributing noise
and the shuffle acted as regularisation. Under either grid the conclusion is the same: **what
the network gains is not an interaction between the signals.**

The interaction ranking agrees, and it is exact rather than an attribution heuristic. For one
hidden layer `∂²f/∂x_j∂x_k = Σ_h a_h · (−2 tanh(u_h)(1 − tanh²(u_h))) · w_hj w_hk`. Ranked by
mean absolute value over the evaluation rows in `N4_INTERACTION`, the strongest pairs are:

| first | second | strength |
|---|---|---|
| `available[50]` | `available[59]` | 1.50e−4 |
| `available[35]` | `available[50]` | 1.13e−4 |
| `available[52]` | `available[59]` | 1.08e−4 |
| `headcount.trend` | `available[50]` | 9.97e−5 |

The strongest interactions the fitted network contains are between **publication-availability
channels**, at a magnitude of `1e−4`, which is numerically negligible. No pair of economic
features appears near the top. The network did not find an economic interaction; it found
almost no interaction at all.

### 3.4 Does any of it help identify dynamic territorial associations? **No, and the null
scenario is why.**

`N0_NULL` carries no relational loading. The network's median gain over the linear arm there
is +0.0345 — larger than in `N1_LINEAR` (+0.0043) and comparable to `N4_INTERACTION`
(+0.0309), the two scenarios built to reward exactly this kind of model. `no_gain_in_null_
scenario` fails in every scenario containing a mechanism, on **both** grids and on both smoke
seeds.

Whatever curvature the network finds is present when there is no territorial relation to
find. It is therefore not evidence of one, and Layer 2 is not authorised.

## 4. Ablations

Refitting the network with one signal's twelve columns removed, inheriting the main fit's
regularisation so that exactly one thing changes. Share of squared error lost:

| removed | `N0_NULL` | `N1_LINEAR` | `N4_INTERACTION` |
|---|---|---|---|
| headcount | −0.845 | −0.485 | −0.585 |
| unemployment | −0.161 | −0.185 | −0.172 |
| payroll | −0.138 | −0.093 | −0.097 |
| creations | −0.190 | +0.001 | −0.164 |
| establishments | −0.157 | +0.023 | −0.017 |

Headcount dominates, which is unremarkable — it is the target's own signal. What matters is
that **the profile is the same in the null scenario as in the mechanism scenarios**. If the
model were using the signals to reconstruct a territorial relation, removing a signal that
measures the propagated component would cost more where that propagation exists. It does not.

## 5. Methodological validity and controls against spurious conclusions

Nine defects were found and corrected, seven before any scientific run and two after the
first grid. They are recorded here because two of them would have changed the reported
answers.

**Found by the guards and the mutation audit, before any run.** A generator branch sat inside
an `elif` chain and never fired, so `N0_NULL` and `N5_REDUNDANT` silently kept `N4`'s split
components and each differed from `N1` in two ways at once. The causality guard's premise was
wrong — a feature at a given period legitimately depends on the vintage, because of the
release lag — and once corrected it had to act on the untruncated panel, since passing through
the released view masked the future before the feature functions saw it and a mutant reading
the whole series survived. The span guard had 38 fully observed zones against 61 regressors,
so least squares reproduced any column exactly and it passed a composite mutated into a
product. A mutant raising the regime gate's constant removed no mechanism, because the gate
is normalised and the normalisation divides the constant back out.

**Found by exercising the summariser on synthetic payloads, before submission.** The
duplicated-channel control was measured against the single-feature floor, which the
duplicated arm beats for reasons having nothing to do with duplication.

**Two selection defects, and the reason there were two.** The network's regularisation was
first chosen on a single contiguous tail of the training window. That tail is 2020–2022 —
COVID and the methodological breaks — so it asks which penalty best fits an atypical era, and
on the pilot it ranked the five weight decays in exactly the reverse of their true
out-of-sample order. Expanding-window folds fixed the ranking but not the level: the folds
span different economic eras, their losses differ by more than the gap between neighbouring
candidates, and the mean is dominated by whichever era is easiest. Every catastrophic fit in
the first grid selected the weakest decay on offer, with an unambiguous signature — `N1`
seed 9704 reached 0.00221 in sample against 0.01594 out. Both arms now use the
one-standard-error rule.

**Why the first grid's seeds were retired.** That diagnosis required reading the
out-of-sample errors of 9701–9705. A seed whose evaluation error has been seen is a
calibration seed whatever it was originally called, and cannot judge the correction its own
diagnosis produced. Those five are declared `RETIRED_SEEDS`, a guard forbids their reuse, and
the reported grid ran on 9801–9805, generated for the first time. The first grid is preserved
unmodified at `hpc_results/herald94/tasks_mean_rule_retired_seeds`. This was the single
repetition the protocol permits; there is no third grid.

**A penalty grid must not be truncated at the point of selection.** The ridge grid was
extended to 1e5 and whether the selection reaches the largest value is reported. It does not:
the maximum selected is 1e4. The same test was added to the network's epoch budget.

**What the correction changed, and what it did not.** It reversed the answer to §3.1 — the
temporal features add a fifth of the error rather than losing to a single feature — and it
removed the catastrophic fits. It did not change either finding that matters for the
territorial question: the null scenario gained at least as much as the mechanism scenarios on
both grids and both smoke seeds, and the gain survived the destruction of its own interaction
on both.

## 6. Limitations

The evaluation target is year-over-year log-growth at horizon one. HERALD 93 established that
this quantity is close to measurement noise in this panel; a relational signal may exist at
longer horizons or in levels with an explicit trend model, and this study does not test that.

The network remains unstable across seeds even after the correction, with per-seed gains
ranging over three units in one scenario. A more robust optimiser, or an ensemble across
initialisations, might narrow that; neither was tried, because trying alternatives until one
succeeded is a search and the protocol forbids it.

The composites tested are six declared ones, not an exhaustive set. A composite outside that
list could carry information. What this study establishes is that the six economically
motivated ones do not, and that a network free to form any smooth interaction among the
underlying features finds none of consequence either.

The synthetic panel imitates French marginals, autocorrelations, dispersion, masks, release
lags and breaks, but it is synthetic. A negative result here constrains what can be claimed
about France; it does not describe France.

## 7. Registers, kept apart

**Mathematical findings.** The temporal representation removes 11–24 % of the out-of-sample
squared error relative to the best single feature. The six declared composites do not improve
a regularised linear model. A one-hidden-layer network does not beat that model in enough
seeds to clear the declared threshold, its strongest exact interactions are between
publication-availability channels at magnitude `1e−4`, and the gain it does show survives the
destruction of the alignment it was supposed to depend on. Its advantage is as large in a
scenario with no relational mechanism as in scenarios with one.

**Economic hypotheses** — plausible, unverified, and not to be reported as findings. The
non-linearity that exists may live in the measurement process rather than in the economy:
counts are drawn around `exp(level)` and zone volumes span a factor of thousands, so log-growth
is far noisier in small zones and the optimal predictor should shrink more where the level is
low. That is an interaction between level and growth which a linear model cannot express. The
ablation profile being identical in the null and mechanism scenarios is consistent with it.
This is a hypothesis about the *instrument*, and it was not tested here.

**Economic interpretation.** None is offered. Nothing in this stage identifies an economic
relation between territories, so there is nothing for a domain specialist to interpret yet.

## 8. France

Not applied. Layer 2 is not authorised, so no relational output exists to carry over, and no
learned structure from this stage may be presented as an association, a precedence or a
territorial pattern.

The stage does license one narrow, non-relational statement, and only as a hypothesis to be
tested on the real panel rather than as a result: a causal temporal representation of the
existing signals — growth, acceleration, trend, momentum, volatility, regime, national
component — predicts a zone's own next-year growth materially better than any single one of
them, under a linear model with a properly selected penalty. That concerns a zone's own
trajectory and says nothing whatever about its neighbours.
