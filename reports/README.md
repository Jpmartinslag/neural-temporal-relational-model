# Reports

Start from the repository root, not from this folder:

1. [`../README.md`](../README.md)
2. [`../docs/PROJECT_OVERVIEW.md`](../docs/PROJECT_OVERVIEW.md)
3. [`../docs/DATA_AND_PROVENANCE.md`](../docs/DATA_AND_PROVENANCE.md)
4. [`../docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md)
5. [`../docs/RESULTS_AND_LIMITATIONS.md`](../docs/RESULTS_AND_LIMITATIONS.md)
6. [`../docs/EXPERIMENT_PROVENANCE.md`](../docs/EXPERIMENT_PROVENANCE.md)

Those six documents are the required reading path. Everything below is the deep record behind
them — provenance and technical/historical detail, not a second entry point.

## `canonical/` — technical and historical record

97 phase/spec/result documents were audited for real dependents (active code, the protected
report's own citations, the artifact registry, this repository's own public docs) and
consolidated to 41; the other 56 are archived, not deleted — full per-file classification,
checksums, and justification, plus what was kept and why, are in
`../docs/EXPERIMENT_PROVENANCE.md` §8. Do not start reading here. Use it to trace a specific
number or decision back to its specification/result document once the public docs above have
pointed you at it — `docs/EXPERIMENT_PROVENANCE.md` §2 and §4 do exactly that for the numbers
in `RESULTS_AND_LIMITATIONS.md`.

## Control documents

- `HERALD_METHODOLOGICAL_DECISION_LOG.md` — every methodological decision, never renumbered or
  deleted, only corrected/superseded explicitly. The ultimate tie-breaker for a specific number.
- `herald_artifact_registry.json` — machine-readable per-artefact status.
- `HERALD_CURRENT_STATE.md`, `HERALD_ACTIVE_DOCUMENT_INDEX.md`,
  `HERALD_REPORTS_CONSOLIDATION_MAP.md`, `HERALD_PROJECT_CHARTER.md`,
  `HERALD_NAMING_CONVENTIONS.md` — earlier-pass control documents, superseded as the reading
  entry point by the 6 documents above but kept for their own provenance value; read them
  together with the decision log, not as standalone current-state claims.

## Protected — do not edit, regenerate, or recompile

- `final_visual_evidence/` — frozen figures/tables the report and presentation read directly.
- `results_evidence_selection/` — curated evidence selection for the report's Results section.

Both are still being edited outside this branch; see `../docs/EXPERIMENT_PROVENANCE.md` §11 for
what was and wasn't synchronized here, and why.

## Dashboards

Current candidate: `dashboards/herald_observatory_v051_narrative_dashboard.html`. Dashboard
lineage (which version is stable vs. exploratory) is documented in
`canonical/HERALD_92_EXPERIMENTAL_CLOSURE_AND_REPORT_HANDOFF.md` and the decision log, not
inferred from the filename.

## Policy

Do not add a new root-level phase report. New work needs a decision-log entry and should either
update one of the 6 public documents or land as a clearly scoped `canonical/` artefact cited
from `docs/EXPERIMENT_PROVENANCE.md`.
