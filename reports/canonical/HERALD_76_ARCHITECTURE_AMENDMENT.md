# HERALD 76 -- Amendment: the annual regime becomes inferred, not stored

**Date:** 2026-08-11
**Status:** `PRE_REGISTERED_AMENDMENT` (DEC-120). Written before any code.
**Amends:** `HERALD_71` (DEC-116) section 3. HERALD_71 is a historical pre-registration and is
not edited; this file supersedes the parts named below.
**Blocks:** `herald75_dynamic_graph.py` is `BLOCKED_FOR_SCIENTIFIC_EXECUTION`. Its mechanical
corrections stand; its architecture does not.

## 1. What was rejected and why

DEC-116 specified `A_t = topk_softmax(C_prior + U diag(z_t) V^T, k)` with `z_t` a free
parameter, one row per year.

DEC-119 measured the consequence: for the scored year the loss never reaches `z`, so that row
stays at its initialisation and all factors fire at an arbitrary constant when the model makes
the only prediction that counts.

**The precise failure.** The network can still emit a prediction -- the heads run -- but it
cannot infer the **year-specific graph** for an unseen year. The failure therefore lands
exactly on the central claim of the project, *forecasting with a dynamic graph*, and nowhere
else. A free `z_t` is a description of years already seen.

A second consequence closes the option: **the design cannot simultaneously reserve validation
years and learn a free `z` for them**, because reserving a year removes its regime from
training. The owner's instruction to hold two validation years is incompatible with a stored
regime table.

`z_t` as a free parameter is rejected. Not tuned, not regularised -- rejected.

## 2. The annual regime becomes a causal function of the year's own history

```text
c_t = masked_pool( h_pregraph_{<= t} )
z_t = tanh( W c_t + b )
A_t = topk_softmax( gamma * C_t + U diag(z_t) V^T , k )
```

`h_pregraph` is the encoder-and-GRU state computed **before** message passing, which is what
keeps this acyclic: `z_t` determines `A_t`, `A_t` determines the messages, so `z_t` may not
depend on messages. `masked_pool` respects the presence mask, so absent nodes contribute
nothing.

`U` and `V` stay persistent at rank 4. What changes is only how their activation for a given
year is obtained.

**Why `f(x_<=t)` and not `g(z_{t-1})` as primary.** It uses information available at decision
time; it generalises to an unseen year directly; it does not extrapolate a temporal dynamic
from fourteen points; and it introduces no circularity provided `h_pregraph` precedes the
graph. `g(z_{t-1})` is retained as a **declared sensitivity**, not as the primary form, and a
hybrid is admissible only if reported as a third arm.

## 3. Information set, stated exactly

For a step whose target is year `t+1`, the model may read year `t` and earlier and nothing
else. Concretely: features from `Y_{<=t}`, the commuting snapshot whose strict ex-ante interval
contains the decision year, and no quantity derived from `Y_{>t}`.

This is stated as a testable property, not as an intention: perturbing any year after `t` must
leave `z_t`, `A_t` and the step's features bit-identical.

## 4. Train, validate, score -- separated in the loss, not only in metadata

DEC-119 found `n_loss = len(x) - 1`, which excluded only the scored step while the metadata
declared two validation years. The split is now defined by which positions the loss consumes:

| span | use | gradient |
|---|---|---|
| targets `2 .. T-3` | training | yes |
| targets `T-2, T-1` | validation: early stopping and hyperparameter freezing | **none** |
| target `T` | scored once | **none** |

**Refit policy, fixed now.** After hyperparameters are frozen on the validation span, the model
is **not** refitted on train+validation. Refitting would consume the only held-out signal that
justified the choice, and the gain would be unmeasurable. This is a deliberate loss of data in
exchange for an interpretable selection step.

## 5. Parameter budget, recomputed

| component | parameters |
|---|---|
| `U`, 280 x 4 | 1,120 |
| `V`, 280 x 4 | 1,120 |
| regime encoder `W`, 64 x 4, and `b` | 260 |
| `gamma` | 1 |
| **relational path** | **2,501** |

At eval year 2025 the training span carries nine transitions, 22,680 labels:
**9.07 observations per relational parameter**, above the pre-registered minimum of 5.

Two properties worth recording. The budget **no longer grows with the number of years**, since
the year table is gone, so it is constant across folds. And the encoder is shared across years,
which is what makes an unseen year reachable at all.

## 6. Controls, respecified

**Temporal placebo.** With `z_t` inferred, permuting a year-to-row mapping is meaningless. The
placebo instead permutes **which year's history the regime encoder reads**, keeping the target
sequence and the chronology of inputs fixed: `z_t = f(x_{<=sigma(t)})`. If the learned dynamics
survive that, they were not temporal.

**Noise floor.** Negative-binomial resampling of the counts at estimated dispersion, each
replicate passed through the **entire** pipeline including refitting, reported in the same
`1 - corr(A_first, A_last)` unit as the observed movement. `phi` is estimated from the data,
not fixed at 2.5.

**Relational placebo.** Permute node identity in `C_t` at preserved degree and weight
distribution.

**Leave-one-year-out.** Refit dropping each training year in turn; no single year, and
specifically not 2020, may carry the dynamism verdict.

**Out-of-sample precedence.** `A_t` built only from data to `t-1` must help order relations
observed at `t` above a matched random ordering.

The dynamism criterion stays bounded on both sides by quantities the analyst does not choose:
above the noise floor, below the temporal placebo.

## 7. Guards required before implementation

Written first, as in HERALD_75, and each one aimed at the architecture that was just rejected.

1. `z` for the evaluation year is **not** an `nn.Parameter` of shape `[n_years, r]`.
2. Perturbing any year after `t` leaves `z_t` bit-identical.
3. Perturbing `x_t` changes `z_t` -- the encoder is live, not a constant.
4. Validation and scored targets receive **zero gradient**, verified on the parameter deltas,
   not on metadata.
5. `z` for the scored year differs from its initialisation.
6. The temporal placebo permutes only the encoder's reading order, leaving targets and input
   chronology intact.
7. The driver calls the noise floor, shrinkage, band classification and edge events on the
   production path -- verified by call, not by definition.
8. Absence and placebo guards use **heterogeneous** weights and **multiple panels** with a
   paired interval. DEC-119 showed the previous versions passed by construction and by seed:
   uniform present weights collapse the standardisation to zero, and over 20 panels the
   placebo beat the base 12 times.

## 8. Order of work

Specification, then guards against the rejected architecture, then implementation. This order
exists because HERALD_72, 74 and 75 were each mechanically better than the last while three
different definitions were wrong, and a mechanically correct HERALD_76 built on a wrong
definition would be the fourth.
