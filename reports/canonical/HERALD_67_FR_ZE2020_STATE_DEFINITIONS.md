# HERALD 67 -- Noise-derived state definitions

**Date:** 2026-08-10
**Sections 1-4:** `PRE_REGISTERED` (DEC-106). Written before the code existed.

## 1. Why the definition is the most consequential choice in the pipeline

DEC-105 measured that moving the state boundary across +-3%, +-5%, +-10% and terciles changes
macro-F1 from 0.3794 to 0.4404. That **0.061 range is three times the largest modelling effect
in DEC-100 to DEC-105**, and roughly five times the 0.012 protocol noise.

The +-5% band was chosen by the analyst with no justification beyond being round. For a product
whose entire output is the label *grows / stagnates / declines*, an arbitrary label makes an
arbitrary product.

## 2. States derived from counting noise, not from a round number

Under a Poisson count model the standard deviation of the year-on-year difference is
approximately `sqrt(y_{t-1} + y_t)`. A change is called real only when it exceeds what counting
fluctuation alone would produce:

```text
d      = y_t - y_{t-1}
sigma  = sqrt(y_{t-1} + y_t + 1)        # +1 keeps sigma defined at zero counts
z      = d / sigma

grows      z >=  1.96
declines   z <= -1.96
stagnates  otherwise
```

A zone-sector with 20 creations needs a far larger relative change than one with 2,000 before
it is called growth. That is not a limitation being worked around; it is the truthful statement
that in a small cell we cannot distinguish growth from fluctuation.

The threshold stops being an analyst's parameter and becomes a property of the data. `1.96` is
the conventional two-sided 95% value and is fixed here.

**Consequence that must be reported, not hidden.** State now correlates with cell size: large
cells are labelled grows/declines more often, small cells stagnates more often. This is correct
behaviour and it changes the class balance relative to DEC-100. Section 5 reports the resulting
balance and the recomputed noise ceiling, which is **not** the 0.655 of DEC-102 -- that figure
belongs to the +-5% definition alone.

## 3. Derived states

Each is defined on the same noise scale, so none reintroduces an arbitrary constant.

| state | definition |
|---|---|
| **accelerates** | `z_t > z_{t-1}` and both exceed 1.96 in absolute value |
| **decelerates** | `z_t < z_{t-1}` and both exceed 1.96 |
| **reverses** | `sign(z_t) != sign(z_{t-1})` and both exceed 1.96 |
| **prolonged stability** | `|z| < 1.96` for three consecutive years |

Reversal is separated from deceleration deliberately. DEC-091 and DEC-096 both recorded
sign-flipping edges being read as structure; a state vocabulary that conflates "slowing" with
"turning" would repeat that error at the product level.

## 4. Gates

**T1 -- the definition must not be self-fulfilling.** The noise-derived labels are recomputed on
Poisson resamples of the panel. The flip rate must be **lower** than the 27.5% measured at +-5%
in DEC-102. If a noise-aware definition is not more stable under noise than an arbitrary one,
it has no claim on being better.

**T2 -- the model must be re-run from scratch.** Every figure in DEC-100 to DEC-105 belongs to
the +-5% definition and none carries over. The standing configuration (GBM, class-balanced,
2 lags, untuned) is re-scored against the new labels, its own random baseline and its own
ceiling.

**T3 -- size confounding must be quantified.** Report macro-F1 separately for cells above and
below the median size. A model that only works on large cells is a different product from one
that works everywhere, and the difference must be visible rather than averaged away.

`HERALD_62` B7 applies: results are reported whichever way they fall.
