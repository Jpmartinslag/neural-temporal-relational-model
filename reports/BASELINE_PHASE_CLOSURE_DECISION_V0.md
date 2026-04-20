# Baseline Phase Closure Decision v0

Data: 2026-04-20

## Objective

Close the current data mining, cleaning, target audit, and baseline validation phase before project cleanup and first graph-temporal model experiments.

This document freezes what is operational, what remains diagnostic, and what must not be claimed as a validated result.

## Closed Decisions

| Topic | Decision | Status |
| :--- | :--- | :--- |
| Target | Official `SIDE` establishment creations aggregated to `ZE2020` | Operational target |
| Former proxy target | Historical audit/comparison only | Not final ground truth |
| Main benchmark | `ridge_lag_only` | Operational benchmark |
| Conservative baseline | `persistence` | Operational baseline |
| Geographic graph | Available structural graph | Context/diagnostic |
| Mobility graph | Available economic graph | Context/diagnostic |
| REI fiscal features | Quarantined | Not usable in canonical baselines |
| SITADEL features | Useful diagnostic local signal | Not promoted |
| Energy features | Useful diagnostic local signal | Not promoted |
| Fixed no-REI residual | Exploratory residual baseline | Not operational |
| No-REI activation rule | Stress-test diagnostic | Not operational |
| STGNN | Next experiment family | Not a conclusion |

## Operational Baselines

Current operational references:

- `ridge_lag_only`: primary benchmark to beat.
- `persistence`: conservative baseline and sanity check.

Reasoning:

- Both are simple, causally interpretable, and do not depend on quarantined features.
- The residual and activation experiments revealed useful signals, but failed robustness criteria needed for promotion.
- Complex graph-temporal models must first prove improvement over these baselines.

## Diagnostic Results Not Promoted

### REI-Backed Residuals

REI-backed residual results were numerically strong, but are invalidated for current operational use.

Reasons:

- Publication-lag and vintage-risk concerns remain unresolved.
- A 2024 aggregation bug caused double counting when aggregate fiscal columns appeared alongside subcomponents.
- The extraction code has been corrected, but the timing/vintage issue is still open.

Decision:

- Keep REI as a candidate under methodological quarantine.
- Do not use REI in canonical baselines or first STGNN experiments.

### No-REI Fixed Residual

The best fixed no-REI residual improved the mean WMAPE but remained unstable.

Decision:

- Keep it as an exploratory diagnostic.
- Do not treat it as the operational benchmark.

### No-REI Activation Rule

The best no-REI activation rule reached a strong aggregate WMAPE, but failed robustness.

Observed issue:

- Threshold trace is anchored after the 2021 shock.
- LOYO threshold range is `0.0917`, above the project criterion of `0.05`.
- The rule improves aggregate volume groups, but worsens against persistence in 2022 and 2023.
- The rule behaves like a stress-test selector, not a stable economic regime detector.

Decision:

- Keep as stress-test diagnostic only.
- Do not promote as operational baseline.

## Graph Status

The project has two observed graphs ready for future experiments:

- geographic adjacency graph
- mobility graph

Current interpretation:

- They are valid structural inputs.
- Simple spatial averaging and linear graph usage did not yet provide enough robust predictive gain.
- Graph-temporal models are therefore justified as experiments, not as already-proven requirements.

## Acceptance Criteria For Next Modeling Phase

Any future STGNN or graph-temporal experiment must report:

- WMAPE against `ridge_lag_only`
- WMAPE against `persistence`
- per-year WMAPE
- volume-stratified WMAPE
- absolute error reduction vs both operational baselines
- concentration risk of error reduction
- explicit feature timing class
- no use of REI unless its timing/vintage status is resolved

Promotion criteria:

- mean WMAPE improvement over `ridge_lag_only`
- no catastrophic yearly degradation
- positive or explainable behavior across volume groups
- methodologically causal feature construction
- no hidden selection on test years

## Next Step

The next project step is cleanup and archival.

Cleanup should happen after this closure decision, because the project now has a clear separation between:

- canonical operational artifacts
- diagnostic artifacts
- quarantined features
- deprecated exploratory outputs

After cleanup, first model experiments should proceed from micro to macro:

1. temporal non-graph model
2. static graph model with geographic graph
3. static graph model with mobility graph
4. simple graph-temporal model
5. richer STGNN only if earlier stages justify it

## Final Closure Statement

The data mining and baseline phase produced a defensible annual `ZE2020` target panel, auditable graph inputs, and causally checked baselines.

The current scientific position is conservative:

- the operational benchmark remains simple;
- local diagnostic signals exist but are not yet robust selectors;
- complex graph-temporal modeling is now allowed as the next experiment, not as a validated solution.
