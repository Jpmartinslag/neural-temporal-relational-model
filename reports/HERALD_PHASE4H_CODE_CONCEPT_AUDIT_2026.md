# HERALD Phase 4H - Code and Concept Audit

Date: 2026-06-08

## Verdict

**BLOCKED for a graph-transfer or strict zero-shot claim.**

The completed Phase 4H-A remains useful as a negative diagnostic: the pooled
neural residual does not transfer to a held-out country and the source-fitted
Ridge is substantially better. However, the experiment does not yet test the
scientific claim "graph correction transfers to a new country".

No evidence was found that a larger or more complex architecture is the right
next step. Recent 2025-2026 work instead supports stronger domain selection,
structural compatibility checks, lightweight models, and explicit handling of
distribution shift.

## Confirmed findings

### F1 - Critical: the temporal falsification is not fold-safe

`prepare_phase4g_joint_panel.py` reverses the complete 2015-2024 sequence of EU
signals before walk-forward evaluation. Consequently, in the 2018 fold:

| Training row | Signal copied from |
|---:|---:|
| 2015 | 2024 |
| 2016 | 2023 |
| 2017 | 2022 |

The control therefore injects future macroeconomic values into early training
folds. It cannot support a causal comparison between `eu_real` and `eu_perm`.
This is especially relevant to the anomalous Portugal result.

Required correction: generate the falsification inside each fold using only
years available up to `train_max`, or replace it with a causal stale-signal
control such as an additional lag. Do not reuse `panel_eu_perm.csv` for causal
claims.

### F2 - Critical: Phase 4H-A did not test graph transfer

The runner selects `fixed_graph`, while both `adj_geo.csv` and `adj_mob.csv`
are identity matrices. In `HERALDv7Residual`, `fixed_graph` computes:

```text
A_t = 0.5 * I + 0.5 * I = I
m_t = msg_proj(A_t @ e_t) = msg_proj(e_t)
```

There is no exchange of information between territories or countries. The
"graph branch" is only another node-wise transformation. Static learned
adjacency parameters are not used by this variant.

Valid conclusion: Phase 4H-A tests transfer of a shared recurrent residual
network over territorial series.

Invalid conclusion: Phase 4H-A tests transfer of graph structure or spatial
message passing.

Required correction: before any graph-transfer claim, use a sparse,
forecast-safe graph with non-diagonal edges and add controls for identity,
edge permutation, and no-message passing.

### F3 - High: residual shrinkage is selected in-sample

`_residual_shrinkage_lambda()` evaluates lambda on predictions from the same
source observations used to fit the neural residual. The target year is
unseen, so this is temporally causal, but it is not model selection on
unseen source domains or unseen years. It predictably selects values close to
one and over-trusts the neural correction.

The post-hoc safety audit confirms:

| Forecast | Country-balanced WMAPE |
|---|---:|
| Ridge, alpha=0 | 0.092576 |
| 5% neural correction | 0.093077 |
| 20% neural correction | 0.097982 |
| Full neural correction, alpha=1 | 0.167146 |

No positive residual weight beats Ridge globally. Only Portugal has a tiny
diagnostic minimum at alpha=0.10, which cannot be selected using held-out
targets.

Required correction: select residual weight using nested leave-one-source-
country-out validation, or make Ridge the zero-shot fallback. In-sample
`train_opt` must not be described as domain-robust selection.

### F4 - Medium: two incompatible WMAPE aggregations are reported

The model JSON reports the arithmetic mean of yearly WMAPEs. The LOCO auditor
computes one pooled WMAPE over all territory-year rows. These metrics assign
different weights to years.

Example for Portugal `eu_real`:

| Aggregation | HERALD | Ridge |
|---|---:|---:|
| Pooled rows | 0.152712 | 0.117145 |
| Mean yearly WMAPE | 0.165746 | 0.130927 |

The scientific conclusion is unchanged, but tables are not directly
comparable. One primary metric must be fixed, with the other reported as a
sensitivity metric.

### F5 - Medium: "zero-shot" needs a precise protocol label

The held-out country is excluded from fitted feature preprocessing, Ridge
training, and neural loss. This part is implemented correctly.

However, its historical target series remains available through lag features,
and per-zone target standard deviations are computed from its past target
history. This is legitimate for forecasting a new country with observed
history, but it is not a cold-start country with no target observations.

Recommended name:

**parameter zero-shot / target-history-available LOCO forecasting**

For strict cold-start generalization, target-country normalization must not use
its historical target values and lag-based inputs would need a different
contract.

### F6 - Medium: model capacity and optimization are not aligned with short T

The neural component is trained for 800 epochs with hidden dimension 64 on
only 3-9 usable annual training steps per fold. Country balancing prevents
France from dominating the objective, but it does not prevent source-domain
memorization or unstable residual extrapolation.

The result pattern is consistent with negative transfer, not with insufficient
capacity:

- deterministic Ridge dominates every neural seed in every held-out country;
- the neural correction magnitude is large relative to the target;
- shrinking the correction monotonically worsens the balanced result.

## Checks that passed

- Held-out country rows are removed from Ridge fitting.
- Annual feature imputer and scaler are fitted on source countries only.
- Held-out country masks are zeroed before neural training.
- Output files contain only the held-out country.
- Manual COVID/rebound flags are excluded and regime vectors are zero.
- Quarterly tensor is zero in Phase 4H-A.
- Country-specific residual heads are disabled.
- Feature growth variables use the corrected causal construction from Phase 4E.

## Evidence from 2025-2026 literature

### Structural compatibility before transfer

Li et al. (2026), *Rethinking Time Series Domain Generalization via
Structure-Stratified Calibration*, argue that global alignment across
structurally incompatible dynamical systems creates spurious correspondence
and negative transfer. This directly matches the observed HERALD failure:
France, Belgium, Netherlands, and Portugal should not automatically share one
unconditional residual map.

Implication: estimate compatibility between country/territory dynamics before
sharing residual corrections. Do not align all countries globally by default.

Source: https://arxiv.org/abs/2603.02756

### Unified representations still need domain-specific adaptation

Wang et al. (ICML 2025) separate unified cross-domain representation learning
from domain-specific adaptive transfer. Their result does not justify adding a
large foundation model here, but it confirms that one shared representation
without an adaptation or selection mechanism is conceptually incomplete.

Source: https://proceedings.mlr.press/v267/wang25ci.html

### Lightweight models remain scientifically credible

Si et al. (ICML 2025) show that an explicitly lightweight correlation model can
outperform larger forecasting architectures with a small fraction of DLinear's
parameters. Ke et al. (CoLLAs 2025) provide a theoretical account of cases
where attention models fail to generalize while a linear residual model
succeeds.

Implication: Ridge winning Phase 4H is not an embarrassment or a reason to add
capacity. It is evidence that the neural correction needs a stronger admission
test.

Sources:

- https://proceedings.mlr.press/v267/si25a.html
- https://proceedings.mlr.press/v280/ke25a.html

### OOD STGNN work assumes a real graph and explicit shift handling

STRAP (NeurIPS 2025) addresses spatio-temporal OOD through retrieval of
compatible historical and structural patterns. Samen (IJCAI 2025) explicitly
models concept shift through inferred environments. Neither supports treating
identity adjacency as evidence of graph transfer.

Sources:

- https://arxiv.org/abs/2505.19547
- https://www.ijcai.org/proceedings/2025/392

### Zero-shot graph transfer requires invariant input semantics

STAGE (ICML 2025) formalizes zero-shot graph transfer by representing
statistical dependencies that remain invariant across attribute domains,
rather than relying on absolute feature values or node identities.

Implication: HERALD should transfer relative, normalized territorial dynamics
and structural relationships, not node-specific parameters or globally aligned
absolute residuals.

Source:
https://www.cs.purdue.edu/homes/ribeirob/pdf/Shen2025_STAGE.pdf

## Recommended next experiment

Do not launch a larger architecture yet.

1. Freeze the zero-shot baseline as source-fitted Ridge.
2. Replace the non-causal reverse-time control with a fold-safe control.
3. Standardize the primary metric as country-balanced mean yearly WMAPE.
4. Build a nested LOCO selector:
   - outer loop: one held-out country for final evaluation;
   - inner loop: hold out each remaining source country;
   - admit a neural/graph residual only if it improves the inner worst-country
     result over Ridge.
5. Use a small correction family:
   - Ridge only;
   - local residual with hidden dimensions 4, 8, or 16;
   - sparse functional graph residual with non-diagonal edges;
   - each with residual weights 0, 0.05, 0.10, 0.20.
6. Keep the final outer country untouched until the selector is fixed.

This design tests the actual scientific hypothesis: a graph residual is useful
only when source-domain evidence predicts that it will transfer.

## Claim status after this audit

| Claim | Status |
|---|---|
| Causal t-1 annual forecasting pipeline | Supported |
| Pooled multi-country fit can improve in-domain performance | Supported |
| Shared neural residual transfers zero-shot | Rejected by Phase 4H-A |
| EU signals transfer robustly to unseen countries | Not supported |
| Graph correction transfers to unseen countries | Not tested |
| Ridge is the safest current zero-shot model | Supported |
| Larger STGNN should be tried next | Not supported |

## Implemented correction: Phase 4H-B

The corrected protocol was implemented after this audit:

- fold-local `source_year_permute` EU control that never copies target/future
  years into source training rows;
- country exclusions generalized to support nested validation;
- inner selector minimizes worst-source-country mean yearly WMAPE over
  residual weights `{0, 0.05, 0.10, 0.20}`;
- final outer-country model receives the selected fixed weight without reading
  outer targets;
- primary metric standardized as mean yearly WMAPE, with pooled WMAPE retained
  as sensitivity analysis;
- real block-diagonal geographic graph and degree/topology-preserving
  within-country permutation control;
- identity, real geography, and permuted geography are separate variants;
- neural capacity reduced from hidden dimension 64 to 16 for the short annual
  panel.

Remote smoke test:

- outer country: Netherlands;
- control: fold-safe EU permutation with identity graph;
- inner countries: France, Belgium, Portugal;
- selected residual weight: `0.0`;
- final mean yearly WMAPE: `0.069821`;
- status: PASS.
