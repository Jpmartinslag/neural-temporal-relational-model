# HERALD 81 — Known-truth benchmark results and architectural finding

Date: 2026-08-11
Runs: HERALD 79 `7860475`; outcome-calibrated HERALD 80 `7860492`

## Execution integrity

Both six-scenario arrays completed 6/6 tasks with exit code `0:0`; all twelve
stderr files are empty. HERALD 79/80 passed 15/15 guards and killed 15/15
deliberate mutants. Heavy truth and seed artifacts remain on `meso`; aggregate
CSVs and JSON are mirrored under `hpc_results/herald79/run_7860475` and
`hpc_results/herald80/run_7860492`.

## Why HERALD 79 was not decisive

Post-run effect audit showed that the graph change called strong contributed
only 3.61% of growth RMS. Medium contributed 0.83% and native 0.19%. HERALD 79
therefore could not serve honestly as an end-to-end strong positive control.
Its result was preserved, and HERALD 80 prospectively calibrated the effective
outcome contribution before refitting.

## Calibrated result

| Scenario | True graph/prior SD | Effective outcome ratio | Added-edge F1 | Dated-event F1 | Dense-D corr. | Delta F1 vs permuted prior | Forecast F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| macro null | 0 | 0 | 0 | 0 | 0 | 0 | 0.5605 |
| static prior | 0 | 0 | 0 | 0 | 0 | 0 | 0.5605 |
| native | 0.015 | 0.050 | 0.0455 | 0.0003 | 0.000002 | +0.0262 | 0.5607 |
| medium | 0.100 | 0.2496 | 0.0148 | 0 | -0.000001 | -0.0396 | 0.5759 |
| medium noisy | 0.100 | 0.2496 | 0.0128 | 0 | -0.000011 | -0.0411 | 0.5657 |
| strong | 0.300 | 0.6258 | 0.0179 | 0.0001 | -0.000003 | -0.0533 | 0.5637 |

Values are medians over five optimisation seeds. Recovery has no dose response,
dense deviations are uncorrelated with truth, dated-event recovery is
effectively zero, and the correctly identified prior loses to the permuted
prior in medium and strong conditions. The model's learned deviation/prior SD
ratio remains about 0.013--0.015 in every scenario, including the nulls.

The injected relation remains measurable after count sampling. In the strong
scenario it changes 12.0% of three-state labels, correlates 0.218 with observed
growth, and adds 0.0315 macro-F1 to a latent oracle relative to the same latent
predictor without the relational component. It is not merely a large hidden
tensor with no observable consequence.

## The architectural finding

The current parameterisation is

`D[t] = U diag(z[t]) V.T`, with unit-norm columns in U/V and `|z_r[t]| <= 1`.

The known truth requires the following maximum factor amplitudes:

| Scenario | Required max `|z|` | Current bound | Representable? |
|---|---:|---:|:---:|
| native | 2.56 | 1 | no |
| medium | 17.07 | 1 | no |
| strong | 51.22 | 1 | no |

Thus even the native known-truth path is outside the model class. Normalising
both persistent factors and bounding z solved scale non-identifiability by
removing the amplitude the deviation needs. The approximately 1.4% ceiling and
near-perfect prior reproduction in the French run are therefore structural,
not merely bad optimisation or evidence that France contains no relational
signal.

This benchmark does not prove that a correctly parameterised model would
recover French relations. It proves that the present HERALD 78 cannot be used
to decide that question.

## Placebo finding

On every true dynamic path, the legacy endpoint statistic returned `p=1.0`.
The prospectively declared adjacent-path roughness returned `p=0.005`; on both
static truths it returned `p=1.0`. The legacy P1 is invalid for smooth monotonic
dynamics because it measures only first-versus-last distance: true endpoints
are deliberately far apart, while random permutations usually choose two
closer interior years.

The corrected statistic is necessary but not sufficient. It also returned
`p=0.005` for learned paths in all 5/5 seeds of both null scenarios. It detects
temporal smoothness, including smoothness imposed by the recurrent model; it
does not by itself establish true relations. It must be paired with known-null
false positives, identity recovery and matched relational controls.

## Benchmark limitation found

The calibrated `macro_null` and `static_prior` outputs are identical because
the residual used to preserve paired shocks retained the static-prior component
in both. This invalidates only the intended comparison between no graph and a
static observed graph. Both remain valid nulls for *dynamic deviations*, and
the strong positive-control/representability finding is unaffected. A successor
generator must export the innovations directly instead of reconstructing them
from a static-prior residual.

## Decision

HERALD 78 remains a valid execution and a negative result for its own model
class, but it is not a fair test of whether dynamic economic relations exist in
the French data. The next architecture needs an explicit identifiable amplitude,
for example

`D[t] = U diag(softplus(a) * z[t]) V.T`,

with U/V still column-normalised, z still bounded and `a` persistent. This adds
four relational parameters at rank four and separates factor identity from
effect magnitude.

Before returning to France:

1. generate truth exactly inside the amended model class;
2. include a deterministic/Poisson clean positive control, followed by the NB
   noise curve;
3. require dense-deviation and dated-event recovery, not forecast improvement;
4. calibrate the adjacent-path placebo jointly with identity recovery and null
   false-positive counts;
5. only after known-truth recovery, rerun the French experiment as a new,
   explicitly labelled specification rather than rewriting HERALD 78.

The known-truth strategy therefore worked: it found both a broken temporal
statistic and a structural amplitude restriction before either could be blamed
on the real data.
