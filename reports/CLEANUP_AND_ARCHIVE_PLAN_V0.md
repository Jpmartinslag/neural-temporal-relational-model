# Cleanup And Archive Plan v0

Data: 2026-04-20

## Objective

Reduce repository ambiguity after the baseline phase closure without losing methodological traceability.

This plan defines classification rules before moving, archiving, ignoring, or deleting any artifact.

## Current Position

The baseline phase is closed.

Operational decisions:

- target: official `SIDE` establishment creations aggregated to `ZE2020`
- primary benchmark: `ridge_lag_only`
- conservative baseline: `persistence`
- `REI`: quarantined
- SITADEL and energy: diagnostic local signals
- residual and activation rules: diagnostic only
- STGNN: next experimental family, not a validated architecture

## Cleanup Principles

1. Do not delete raw data.
2. Do not delete methodological evidence.
3. Do not keep exploratory reports in the main reading path.
4. Keep all canonical decisions discoverable from `PROJECT_STATE_INDEX_V0.md`.
5. Keep generated prediction dumps out of Git when they are large and reproducible.
6. Prefer archiving over deletion unless the file is clearly temporary.
7. Preserve enough evidence to defend the data mining and cleaning phase in a presentation or thesis.

## Classification Categories

### Canonical Reading

Files needed to understand the current project state.

Criteria:

- describes current target, benchmark, graph, tensor, or closure decision
- used as entry point for future work
- not superseded by a newer decision report

Expected examples:

- `PROJECT_STATE_INDEX_V0.md`
- `BASELINE_PHASE_CLOSURE_DECISION_V0.md`
- `PROJECT_JOURNEY.md`
- target audit reports
- canonical artifact registry

### Diagnostic Archive

Files useful for auditability, but not part of the main reading path.

Criteria:

- explains why a candidate was accepted, rejected, or quarantined
- records exploratory experiments
- supports a decision but is not the decision itself

Expected examples:

- residual diagnostics
- activation diagnostics
- local feature audits
- source search reports
- temporal mismatch reports

### Deprecated Or Superseded

Files whose conclusions were replaced by later reports.

Criteria:

- older target proxy reports after official `SIDE` adoption
- older graph/build plans after implementation
- older preliminary readiness reports superseded by closure decisions

Handling:

- archive, do not delete immediately
- keep path discoverable only if needed for historical traceability

### Environment Or Process

Files documenting setup, workflow, naming, or contribution rules.

Criteria:

- not scientific evidence
- useful for reproducibility or developer onboarding

Expected examples:

- environment setup
- naming conventions
- versioning policy
- scan workflow

### Regenerable Ignored

Large or line-level outputs that can be reproduced by scripts.

Criteria:

- prediction rows
- raw converted intermediate dumps
- large model-output tables not intended for human review

Handling:

- add to `.gitignore`
- keep compact reports and quality summaries versioned

## Proposed Folder Structure

No files should be moved until classification is reviewed.

Target structure:

```text
reports/
  PROJECT_STATE_INDEX_V0.md
  BASELINE_PHASE_CLOSURE_DECISION_V0.md
  PROJECT_JOURNEY.md
  ...

reports/archive/
  diagnostics/
  deprecated/
  source_search/
  process/
```

Alternative if we want fewer nested folders:

```text
reports/archive/
  01_diagnostics/
  02_deprecated/
  03_source_search/
  04_process/
```

## Candidate Canonical Reading Set

Initial proposed root-level reading set:

- `PROJECT_STATE_INDEX_V0.md`
- `BASELINE_PHASE_CLOSURE_DECISION_V0.md`
- `PROJECT_JOURNEY.md`
- `PROJECT_EXPLANATIONS.md`
- `TARGET_PROXY_SIDE_AUDIT_DECISION_V0.md`
- `TARGET_SIDE_ESTABLISHMENTS_ANNUAL_CORE_V0.md`
- `SIDE_TARGET_BASELINES_CORE_V0.md`
- `LOCAL_CANDIDATE_FEATURES_AUDIT_V0.md`
- `ACTIVATION_RULE_DIAGNOSTICS_CORE_V0.md`
- `EXTENDED_CORE_VERIFICATION_SUMMARY_V0.md`
- `STGNN_READINESS_AND_ARCHITECTURE_DECISION_V0.md`

This set should be reduced further after the classification audit.

## Candidate Canonical Data Artifacts

Initial proposed operational artifacts:

- `data/processed/target_side_establishments_annual_core_v0.csv`
- `data/processed/extended_panel_core_v0.csv`
- `data/processed/graph_nodes_ze2020_core_v0.csv`
- `data/processed/graph_edges_ze2020_core_v0.csv`
- `data/processed/graph_adjacency_core_v0.csv`
- `data/processed/mobility_adjacency_row_normalized_core_v0.csv`
- `data/processed/stgnn_tensor_package_extended_forecast_core_v1.npz`
- `metadata/canonical_artifacts_v0.csv`

## Candidate Diagnostic Data Artifacts

- residual diagnostics
- activation diagnostics
- local feature candidate tables
- REI CFE diagnostic table
- energy candidate table
- target proxy vs official SIDE comparison

## Files Not To Promote

Do not promote these to canonical without a new methodological decision:

- REI-backed residual outputs
- activation rule outputs using `min_prior_years=1`
- old proxy target as final target
- prediction dumps ignored by `.gitignore`
- nowcast/diagnostic tensors as forecast-safe artifacts

## Cleanup Workflow

1. Generate classification proposal.
2. Review ambiguous files manually.
3. Update `canonical_artifacts_v0.csv`.
4. Move archived reports in one commit.
5. Update links in `PROJECT_STATE_INDEX_V0.md`.
6. Run lightweight checks.
7. Commit with an English message.

## Safety Checks Before Moving Files

Before any archive move:

```bash
git status --short
git grep -n "FILE_NAME_TO_MOVE"
```

After moving:

```bash
git status --short
git diff --check
```

## Open Questions

- Should archived reports keep their original names or receive archive prefixes?
- Should diagnostics remain in `reports/` until the first STGNN experiment is complete?
- Should old target-proxy reports be archived now or after presentation materials are drafted?
- Should JSON quality reports be archived with their Markdown reports or kept beside them in root `reports/`?

## Current Recommendation

Do not move files yet.

First obtain a full classification audit of:

- `reports/`
- `data/processed/`
- `metadata/`

Then execute archive moves in a dedicated cleanup commit.
