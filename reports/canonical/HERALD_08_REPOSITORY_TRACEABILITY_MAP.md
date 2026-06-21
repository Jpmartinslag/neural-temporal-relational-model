# HERALD 08 — Repository Traceability Map

**Created:** 2026-06-18 (canonical consolidation, second-level traceability map).
**Status:** Documentation only. No folder was moved, no file was edited for content
reasons in this document.
**Purpose:** for each top-level area of the repository — what it is, its status, who
should read it, and what must never be cited as a primary source from it.

---

| Folder/file | Function | Status | Who should read it | Do NOT use as primary source for |
|---|---|---|---|---|
| `reports/canonical/` | **Scientific entry point** — 5 numbered canonicals (phases, data, methods, results, dashboard/roadmap) + this traceability layer (06-08) + the consolidation audit | ACTIVE — authoritative synthesis | Everyone, first | Nothing — this is the primary entry point. If a canonical and the decision log disagree, the decision log wins, but the canonical is still where you start. |
| `reports/dashboards/` | Built HTML Observatory dashboards (v0.3→v0.5.1) and their Python builders | ACTIVE (v0.4.1 stable baseline) / candidate (v0.5.1) | Anyone wanting to *see* the data | **Visualization, not a primary scientific source.** A dashboard never recomputes a number — it consumes already-validated exports. Cite the export/builder/DEC behind it, not the dashboard itself, for a number. |
| `reports/bibliography/` | Reference list (25 master refs), BibTeX, reference audit CSV | ACTIVE | Anyone writing the article | Nothing within scope — this is appropriately a primary source for citations |
| `reports/README.md`, `HERALD_ACTIVE_DOCUMENT_INDEX.md`, `HERALD_CURRENT_STATE.md`, `HERALD_METHODOLOGICAL_DECISION_LOG.md`, `HERALD_PROJECT_CHARTER.md`, `HERALD_NAMING_CONVENTIONS.md`, `HERALD_REPORTS_CONSOLIDATION_MAP.md`, `herald_artifact_registry.json` | Control documents kept at the `reports/` root after the 2026-06-18 cleanup | ACTIVE, authoritative | Everyone | N/A — these are themselves authoritative |
| `data/` (raw/interim/processed) | Source panels and exported artefacts | Mixed (per-artefact status) | Anyone running or extending the pipeline | **Any individual file in `data/processed/` without checking `reports/herald_artifact_registry.json` first.** The registry is the only place that says whether a given file is `ACTIVE`, `BLOCKED`, `INVALID_FOR_RELATION_LABELS`, etc. — the file's mere presence in a directory is not evidence of validity. |
| `src/` | Ingestion adapters, model code, export/dashboard builders | ACTIVE | Engineers extending the pipeline | **Claims about what the code "proves."** Code implements a method; whether that method's *output* is validated, partial, or rejected is decided in the DEC log and canonical #4, not by reading the code. A builder existing does not mean its result is promoted. |
| `tests/` | One suite per DEC/phase/dashboard version | ACTIVE | Engineers verifying nothing has drifted | Green tests confirm internal consistency (e.g. "no NaN," "proxy never in relation_edges") — they do **not** confirm a scientific claim is true. A passing test suite is necessary, not sufficient, evidence. |
| `hpc/` | SLURM batch scripts and phase registries, spanning open and closed phases | Mixed — active folder, many individual scripts correspond to CLOSED phases | Engineers re-running or auditing a specific phase | **Any script here without checking the phase name against the decision log first.** A script existing does not mean its branch is open; e.g. graph-temporal/P6 scripts here correspond to CLOSED branches (DEC-029/031). |
| `hpc_results/` | Raw HPC job outputs | **Historical/generated** — mostly from closed/superseded branches (graph-temporal, P6 dual-graph, geographic-graph) | Auditors tracing a specific job ID back to a decision | **Never** as a primary claim source on its own — always cross-reference the DEC entry that interprets the run before treating any number here as current evidence. |
| `docs/` (`docs/architecture/`) | Legacy architecture diagrams removed from the public tree | Removed / historical in git history only | No one starting fresh | The current architecture — use `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` instead |
| `metadata/` | Older data catalogs and dataset notes | Historical, partly superseded | No one starting fresh | Artefact provenance/status — use `reports/herald_artifact_registry.json` instead |
| `.gitignore` | Defines what's tracked vs local-only (incl. the `reports/*.md` root-cleanup policy) | ACTIVE — operational config | Anyone wondering why a file isn't in `git ls-files` | N/A — it's a policy file, not a claims source |
| `README.md` (repository root) | Public entry point: project trajectory summary, link to the 5 canonicals, repository map, test commands | ACTIVE | Everyone, before anything else | A substitute for the canonicals themselves — it summarizes and links, it does not restate every caveat |

---

## Three rules this map exists to enforce

1. **`reports/canonical/` is the scientific entry point.** Everything else is either a
   primary control document already covered above, supporting evidence the canonicals
   cite by DEC number, or historical/generated material that requires cross-referencing
   before use.
2. **Dashboards are visualization, never a primary source.** If a number needs citing,
   trace it back through the dashboard's builder script to the export it consumed, and
   from there to the DEC-* entry that validated it.
3. **Local, unversioned files are not part of the public narrative.** Agent-handoff notes
   (e.g. `CODEX_MEMORY.md`, intentionally gitignored) and any other local-only file never
   enter the scientific record — if a claim only exists in such a file, it does not exist
   for citation purposes until it has a DEC-* entry and a place in a canonical document.

---

## Cross-reference

- Scientific entry point: `reports/canonical/HERALD_0{1..5}_*.md`
- Phase/technique matrix: `reports/canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md`
- Method lineage narrative: `reports/canonical/HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md`
- Per-file consolidation audit: `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`
- Artefact provenance: `reports/herald_artifact_registry.json`
