# HERALD 77 -- Second amendment: closing the seven defects DEC-121 found

**Date:** 2026-08-11
**Status:** `PRE_REGISTERED_AMENDMENT` (DEC-122). Written before any implementation.
**Amends:** `HERALD_76` (DEC-120) sections 2, 3, 4, 5, 6 and 7. HERALD_71 and HERALD_76 are
historical pre-registrations and are not edited.

DEC-121 confirmed the architectural direction -- an inferred `z_t` -- and found four defects in
the specification and eight guards that a defective implementation could pass. Each is closed
below. Where a decision is reversed, the earlier one is named.

## 1. The task, declared

**Rolling one-step-ahead forecasting, recomputed after each year is observed.** Under that task
reading `Y_t` to predict `Y_{t+1}` is causal, and `Y_t` having been the previous step's target
is not leakage because at decision time `t` it is observed.

This does **not** extend to recursive multi-year forecasting: after the first horizon `Y_t` is
no longer observed and the information set argument fails. Any multi-year claim requires its
own specification.

## 2. `masked_pool`, defined

```text
c_t = sum_{i,s} m_{t,i,s} * h_pregraph_{t,i,s}  /  max(1, sum_{i,s} m_{t,i,s})
```

A masked **mean over nodes at the current step**. The GRU supplies temporal memory, so the pool
does not run over time as well.

Sum pooling is rejected: it would confound the regime with the number of present nodes.
Pooling again over `h_1..h_t` is rejected: it would double the history and make the regime's
scale depend on fold length.

## 3. Recurrent feedback, decided

**Primary: `h_pregraph_t = GRU(x_t, h_pregraph_{t-1})` and nothing else.** Messages from any
step never enter the pre-graph state.

A variant in which `message_{t-1}` feeds `h_pregraph_t` has no algebraic circularity, the
dependence being lagged, but it is a different object: an autoregressive graph system that can
amplify its own errors. It is admitted only as a **declared sensitivity arm**, never as the
primary.

## 4. The temporal placebo, rebuilt

`HERALD_76` section 6 specified `z_t = f(x_<=sigma(t))`. That is **withdrawn**: where
`sigma(t) > t` the placebo reads the future, and a bijection with `sigma(t) <= t` for every `t`
is only the identity, so the construction does not exist.

Replaced by two controls that do:

**P1 -- retrospective regime permutation.** Compute every `z_t` causally, then permute the
`z` vectors across years for the analysis only. The model is never run forward with a permuted
regime, so no information set is violated. This asks: *do the learned regimes explain their own
years better than they explain other years?*

**P2 -- pre-declared circular shift**, `z_t <- z_{(t+d) mod T}` for a fixed `d` chosen before
execution. This one **is** deliberately non-causal and is reported as an upper bound, labelled
as such, never as a matched control.

The dynamism criterion keeps its two-sided form: above the noise floor, below P1.

## 5. Folds, budget and accounting

**Evaluation starts at 2021.** At rank 4 the observations per relational parameter are 3.02 in
2019 and 4.03 in 2020, below the minimum of 5 that HERALD_71 section 4 set. Rather than lower
the rank for two folds or abandon the rule, the two underpowered origins are dropped. **Five
origins, 2021-2025**, and the loss of two is reported, not hidden.

**Both parameter counts are reported, always.**

| count | value at 2025 | observations per parameter |
|---|---|---|
| relational path (`U`, `V`, `W`, `b`, `gamma`) | 2,501 | 9.07 |
| full model including encoder, GRU, message layers, heads | ~36,553 | 0.62 |

Counting only the relational path describes the adjacency's explicit capacity. It is **not** a
proof of identifiability for a model whose encoder and GRU are trained jointly and produce
`c_t`. DEC-121 called the single figure selective accounting and it was.

## 6. Refit, reversed

`HERALD_76` section 4 fixed no-refit. **That is reversed.**

Primary: train on the training span; select the epoch on validation; freeze every choice;
reinitialise; refit on train + validation for the frozen number of epochs; score the held-out
year exactly once. The scored year is untouched throughout, so its independence is intact;
what is given up is a validation estimate of the refitted model, not the validity of the score.
With fourteen years this is the better use of the data.

No-refit becomes the declared sensitivity. The chosen policy applies identically to every
placebo, every resample and every control arm.

## 7. Guards, rebuilt against the mutants that passed

Each replacement names the mutant that defeated the previous version.

| guard | defeated by | replacement |
|---|---|---|
| g1 | table transposed to `[rank, n_years]`, or a buffer | build the model at 14 and at 20 years; require identical `state_dict` keys and shapes; forbid any parameter **or buffer** whose dimension depends on `n_years` |
| g2 | encoder reading one step ahead | pass a **prefix** `Y[:t+1]`, so the future is structurally unreachable; if the full panel must be passed, perturb **every** year after `t` for **every** `t` and require `z_t`, `A_t` and features bit-identical |
| g4 | `corrupt_heldout` as a no-op; CUDA tolerance | the test builds both target tensors itself, instantiates one initialisation, and compares **loss and gradient vectors before any optimiser step** -- no reliance on a flag the audited code implements, and no accumulated non-determinism |
| g5 | constant encoder differing from init | keep, but measure `z_init` from the model before training rather than accepting it from the export; retained only in combination with g3 |
| g6 | `run_fold` ignoring the plan | integration spy: replace `regime_encoder` with a recorder, run `run_fold(shuffle=True)`, assert targets and input chronology unchanged and that the **recorded reads** follow the permutation |
| g7 | names in a docstring | runtime spies: wrap each control so it counts calls and returns a sentinel; assert the count and that the sentinel reaches the exported report. Extend coverage to the temporal placebo, relational placebo, leave-one-year-out, precedence and seed stability, none of which g7 looked for |
| g8 absence | the old classifier, because `C` was never passed | run the **production path** and capture the actual argument to `classify_edges`; assert it equals the learned deviation and differs from `gamma*prior + deviation` |
| g8 placebo | a placebo identical to the base | two independent conditions: **structural validity** (node identity changed, degree preserved, weight multiset preserved, a minimum share of edges moved) **and** no systematic advantage (paired multi-panel interval) |
| budget | a driver reporting 2,501 | count real parameters by name prefix from the model, not from a dictionary the driver returns |

**Only `g3` survives unchanged**, and only for the defect it targets: it does not show that the
regime responds to anything economically meaningful, which is the job of the scientific gates.

## 8. Still to be defined before implementation

Listed so a fourth mechanically-correct implementation on a still-incomplete definition is not
possible. None of these may be chosen during coding.

Validation metric, patience and the epoch-selection rule; initialisation and normalisation of
`U`, `V`, `W`; whether `gamma` is constrained non-negative; factor alignment across seeds given
that sign, permutation and scale are unidentified; a mandatory prior-versus-deviation scale
diagnostic; the estimator for `phi` using training years only; the number of negative-binomial
resamples and the quantile defining the floor; the number of placebo draws and the approval
rule; the relational placebo's exact construction; the leave-one-year-out threshold; the
precedence metric and its matching; `shrink`'s counts and prior mean; the band thresholds; the
formal separation of the propagation top-k from the exported dense graph; the tie policy in
top-k; seed stability of the mutations themselves; the joint state/magnitude loss weight; and
the architecture and budget of the `g(z_{t-1})` and hybrid arms.

## 9. Process defect, third occurrence

DEC-120 was committed in its canonical file with no entry in the decision log, as happened for
DEC-088..105 and DEC-114..116. Binding from here: **a canonical file that declares a DEC number
is committed together with its log entry, in the same commit.**
