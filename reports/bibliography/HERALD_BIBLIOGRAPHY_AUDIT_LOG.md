# HERALD Bibliography Audit Log

**Date:** 2026-06-21
**Scope:** Bibliography hygiene only — `reports/bibliography/`. No scientific claim,
DEC entry, or methodology text was altered. This log records the classification of
every reference in `HERALD_REFERENCES_MASTER.md` (R-001 to R-051, pre-audit) plus the
two satellite files (`herald_references.bib`, `herald_graph_temporal_references.bib`)
and their audit CSVs.

## Method

1. Cross-checked every `R-0xx` key and every `.bib` key against where it is actually
   cited in the **currently git-tracked** `reports/` tree (`git ls-files reports/`).
   Files removed from the git index in the 2026-06-18 consolidation (e.g.
   `HERALD_POST_DEC045_ARCHITECTURE_RESEARCH.md`, the dynamic-economic-graph literature
   review, etc.) are real and recoverable via git history, but are not part of the
   tracked tree this audit cleans.
2. For every reference, checked whether the DOI/arXiv ID/URL resolves to a real,
   matching primary source (publisher page, ACM/IEEE/Oxford/Wiley DOI resolver, arXiv
   abstract page, or official GitHub/OpenReview page), via WebSearch/WebFetch.
3. Cross-checked the decision log (`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`),
   the canonical docs (`reports/canonical/HERALD_0{3,8}_*.md`,
   `HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`, `HERALD_DEEP_REPORT_AUDIT.md`,
   `HERALD_14_WORKTREE_DECISION_AUDIT.md`), and `HERALD_CURRENT_STATE.md` for explicit
   reliance on the bibliography.

## Result summary

- **51 references audited, 49 kept (2 removed as exact duplicates), 0 removed as
  unverifiable/hallucinated.**
- Repository policy (`HERALD_03_METHODS_AND_ARCHITECTURE.md` §4c,
  `HERALD_08_REPOSITORY_TRACEABILITY_MAP.md`) explicitly designates the master
  reference list as kept, citable raw material for the article — not a per-claim
  citation index tied 1:1 to canonical text. This is why most entries are
  `KEEP_VERIFIED_BACKGROUND` (literature-review scope) rather than
  `KEEP_VERIFIED_USED` (directly cited by name in a tracked report).

## Removed (REMOVE_DUPLICATE)

| Removed key | Reason |
|---|---|
| R-050 (`hou2022graphmae`, Axis 15) | Exact duplicate of R-036 (Axis 13) — same paper (Hou et al. 2022, GraphMAE, KDD 2022), same BibTeX key. The Axis-15-specific usage note ("secondary option for relation embedding pretraining if weak labels are insufficient") was merged into R-036's "Used in project" field rather than discarded. |
| R-051 (`nie2022patchtst`, Axis 15) | Exact duplicate of R-037 (Axis 13) — same paper (Nie et al. 2023, PatchTST, ICLR 2023), same underlying work under a different key spelling. The Axis-15-specific usage note was merged into R-037's "Used in project" field. |

Both duplicates were genuine, verifiable papers — the issue was redundant entries, not
hallucination. Removing them only deduplicates; no citation pointer elsewhere in the
tracked tree referenced `R-050` or `R-051` by number (only `HERALD_REFERENCES_MASTER.md`
itself used these numbers), so no other file needed editing.

## Reclassified UNVERIFIED → VERIFIED_PRIMARY (9 entries)

All nine references flagged `UNVERIFIED` in the file (with the note "DOI/reference to be
confirmed") were checked against their publisher or proceedings page on 2026-06-21 and
confirmed to be real, correctly cited works. None were hallucinated.

| Key | Title (short) | Verified via |
|---|---|---|
| `shojaie2022granger` (R-010) | Granger Causality: A Review and Recent Advances | Annual Reviews publisher page |
| `audretsch2002growth` (R-016) | Growth Regimes over Time and Space | Taylor & Francis (Regional Studies) |
| `anselin1988spatial` (R-017) | Spatial Econometrics: Methods and Models | Springer/Kluwer DOI record |
| `moran1950spatial` (R-018) | Notes on Continuous Stochastic Phenomena | JSTOR / Oxford Academic (Biometrika) |
| `jain2019attention` (R-019) | Attention Is Not Explanation | ACL Anthology (N19-1357) |
| `neffke2011regions` (R-020) | How Do Regions Diversify over Time? | Wiley Online Library (Economic Geography) |
| `acemoglu2012economy` (R-021) | The Network Origins of Aggregate Fluctuations | Econometric Society / Wiley (Econometrica) |
| `blondel2008louvain` (R-022) | Fast Unfolding of Communities in Large Networks | IOPscience (J. Stat. Mech.) |
| `page1954cusum` (R-025) | Continuous Inspection Schemes | Oxford Academic (Biometrika) |

## Spot-checked, confirmed real (no status change needed)

- `econognn2026` (R-008, EconoGNN, PLOS ONE 2026) — confirmed via PLOS ONE article page
  and PMC mirror. This is a genuinely recent (April 2026) real publication, not a
  hallucination despite the future-looking year; current date is 2026-06-21.

## Usage cross-check against the tracked tree

- `HERALD_REFERENCES_MASTER.md` itself is the only tracked file that cites individual
  `R-0xx` numbers. The decision log (`HERALD_METHODOLOGICAL_DECISION_LOG.md`) references
  the bibliography file as a unit twice: once for DEC-027 (graph-temporal architecture
  preflight, citing `herald_graph_temporal_references.bib` +
  `HERALD_GRAPH_TEMPORAL_REFERENCE_AUDIT.csv` directly — this is the citable background
  for the now-closed graph-temporal branch, DEC-029/DEC-031), and once for DEC-046
  (research-only architecture survey, "18 verified references, R-026 to R-042").
- `HERALD_14_WORKTREE_DECISION_AUDIT.md` independently documents the Axis 15 addition
  (R-043→R-051) as tied to DEC-057 (weak-supervision references for the real-relation
  fine-tuning work in DEC-058/DEC-059).
- `herald_graph_temporal_references.bib` / `HERALD_GRAPH_TEMPORAL_REFERENCE_AUDIT.csv`
  are not cited by key anywhere else in the tracked tree, but are explicitly named as
  the evidence files for DEC-027 in the decision log — kept as
  `KEEP_VERIFIED_BACKGROUND` (they justify why the graph-temporal/GConvGRU/EvolveGCN-H
  branch was opened and, in DEC-031, closed).
- No reference in either `.bib`/CSV pair was found unused-and-unverifiable; none were
  removed beyond the two Markdown duplicates above.

## Files touched in this audit

- `reports/bibliography/HERALD_REFERENCES_MASTER.md` (deduplicated R-050/R-051, fixed 9
  stale `UNVERIFIED` statuses to `VERIFIED_PRIMARY`, updated the metrics table)
- `reports/bibliography/HERALD_BIBLIOGRAPHY_AUDIT_LOG.md` (this file, new)

No other file in the repository was modified. `herald_references.bib`,
`HERALD_REFERENCE_AUDIT.csv`, `herald_graph_temporal_references.bib`, and
`HERALD_GRAPH_TEMPORAL_REFERENCE_AUDIT.csv` were audited and found consistent —
no edits were necessary in those four files.
