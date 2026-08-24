# Experiment provenance

Compact map from the project's experimental history to the final, reported state. This is
deliberately short — it is an index into the deep record, not a replacement for it. The deep
record (never deleted, always the tie-breaker on a specific number) is:

- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — every decision, never renumbered or
  deleted, only corrected/superseded explicitly.
- `reports/canonical/` — the phase/spec/result documents kept in this branch because they are
  either final evidence for a number in `RESULTS_AND_LIMITATIONS.md` or a specification an
  active script's own docstring cites. See §7 for what was consolidated out of this folder and
  why, and for where every removed document still lives.
- `reports/herald_artifact_registry.json` — machine-readable per-artefact status.

## 1. Naming

This project's internal, historical experiment identifier is **`HERALD`**, an acronym coined
early in the work. It is not, and has never been, a public or scientific model name. It appears
only as a **legacy internal experiment identifier** — in job directory names (e.g.
`hpc/herald93/`), historical filenames (e.g. `train_herald_v6.py`), git history, decision-log
entries, and the titles of the `reports/canonical/` documents kept for provenance in §7. It does
not appear, and should not be reintroduced, in `README.md` or any other file under `docs/`.

The project's public/scientific name is **Neural Temporal–Relational Model**.

Suggested neutral short forms for **new** code identifiers, not yet applied to existing active
modules (see §5): `temporal_relational_model`, `neural_temporal_relational`, `relation_learner`,
`temporal_encoder`.

The GitHub repository's own name, `territorial-recommender-stgnn-mas`, is a third, unrelated
historical label (from before either name above); renaming the git remote was out of scope for
this cleanup.

## 2. Historical phases → final result, in one line each

| Period | What happened | Where it lands in the final story |
|---|---|---|
| Apr–Jun 2026 | France prediction foundation, European harmonization (PT/IT/AT/NL/BE), graph branches tested and closed (P6 dual graph, graph-temporal, Phase 5 fixed-L2 corrector, geographic queen-contiguity) | Baseline/architecture-search history; none of these branches contributes a current headline number. Kept as tested-and-rejected findings, not gaps. |
| Jun 2026 | Sector precedence graph, Observatory dashboards, PT/NL granular evidence | Descriptive evidence layer; superseded as the project's central question by the Jul–Aug work below |
| Jun–Jul 2026 | France ZE2020 relational layer built up incrementally: candidate relations, a temporal-integrity (leakage) correction, dynamic-graph inputs, a long sequence of relation-scoring/transfer/fusion gates, all failing their pre-registered gates | Establishes, on real French data, that a single sparse relational signal does not reliably identify relations — motivates the multisignal synthetic redesign below |
| Aug 2026 | The known-truth synthetic benchmark: a 280-territory main benchmark and an 80-territory residual diagnostic, temporal representation and composite-signal tests, a relational-scale oracle ladder, a multirelational arm, stage closure, and the frozen visual-evidence archive | **This is the evidence base for `RESULTS_AND_LIMITATIONS.md`.** A final model comparison beyond this stage is specified but explicitly **not run**. |

## 3. Key jobs/commits behind the current results

| Result | Artefact | Commit |
|---|---|---|
| Temporal representation (11–24% error reduction, main benchmark) | `hpc_results/herald94/` | `d94c97c`…`6bbed13` |
| Relational-scale oracle ladder | `hpc_results/herald95/` | `b52ffeb`…`3125e43` |
| Residual diagnostic / all-pairs recovery test | `hpc_results/herald96/` | `3a9e434`…`3ab599b` |
| Stage closure, frozen figures/tables | `reports/final_visual_evidence/` | `ce1a3c8`, `f730e72` |
| Final model comparison (specified, **not run**) | — | spec only, kept: `reports/canonical/HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md` |

## 4. Base branch and what this delivery does and does not include

This branch (`delivery/repository-cleanup`) was created from **`main` at commit `f730e72`**
("docs: close the experimental stage, and build the evidence archive it rests on"). It has
never been merged with `main` and was never intended to be created from anything other than that
one commit.

At the time this branch was created, the repository's primary (non-cleanup) working copy held
several hundred additional modified and untracked paths that were **not** part of `f730e72` — ongoing edits to
`reports/final_visual_evidence/`, new `hpc/herald78…89/` job directories, four actively-edited
`train_herald_{v6,v7,semi_v2,regime_experiment}.py` files, and new France ZE2020 data exports,
among others. **None of that uncommitted work was copied into this branch, automatically or
otherwise**, and the primary worktree itself was never written to by this cleanup.

Consequences worth stating plainly:

- **This branch is a proposed delivery structure, not necessarily the final scientific
  snapshot.** It organizes and documents the repository as it stood at `f730e72`.
- Work committed to `main` after `f730e72` — including whatever the primary worktree's pending
  changes become once committed — is **not** in this branch and will need a deliberate,
  selective merge before this branch is treated as ready to become the delivered repository.
  "Selective" matters here: a blind merge of `main` forward would reintroduce the sprawl this
  cleanup removed, so future work should port specific results and data forward, not resolve a
  merge conflict by taking everything.
- Anyone reviewing this branch should treat it as **"the last commit this repository can point
  to cleanly is `f730e72`"**, not as "this is the final state of the science."

## 5. What was and wasn't renamed, and why

The public surface (`README.md`, `docs/*.md`) uses **Neural Temporal–Relational Model** and does
not present `HERALD` as the current name.

Renaming active code identifiers (module/class/function names across ~200 `src/` files
containing `herald`) was **not done** in this pass. A grep-verified check during the archival
step found that files the project's own repository-traceability documentation labels
"historical" are in fact still imported by active modules and covered by active tests. Given
that, a blanket or even a "safe subset" rename right before delivery was judged higher-risk than
valuable without a full call-graph pass and matching test updates. Recorded as `REVIEW_REQUIRED`
in the cleanup's external inventory for a future pass with more time budget.

## 6. Experiments discarded or invalidated, and why

| Branch | Verdict |
|---|---|
| P6 dynamic dual graph | Fails all 7 pre-registered gate criteria |
| Graph-temporal (GConvGRU/EvolveGCN-H) | Closed, local S1-FR run failed |
| Phase 5 fixed-L2 residual corrector | Not supported |
| Geographic queen-contiguity graph | Refuted under the current protocol (Italy, p=0.19/0.32) |
| ARDECO-extended FR Ridge | Closed exploration |
| France single-signal relation gates (transition transfer, edge-family isolation, similarity nonlinear transfer, bottleneck fusion, commuting relation/topology gates, context-conditioned sector relation, product-space entry density, temporal bipartite reconstruction, composition transition ranking) | Each fails its pre-registered gate |
| Six declared composite economic signals | All negative, none adds information |
| Declared multisignal-complementarity mechanism | Not supported (median −0.07 percentage points) |
| France WMAPE headline figure from the pre-Q7 architecture search | Flagged for re-audit, potential causal-feature leakage; not usable as a headline claim |
| A pre-Q7 P6 sector-label artefact | Sector names in that file don't match the tensor's actual sector IDs; kept only as historical record, never for interpretation |

Full DEC-numbered detail for every row above: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`.
None of these are reopened by this cleanup — reopening any of them requires a new decision-log
entry.

## 7. `reports/canonical/` consolidation (this pass)

`reports/canonical/` held **97** phase/spec/result documents before this pass — the
"many historical steps" surface this cleanup targeted. Each was audited for real dependents
(active code docstrings, the artifact registry, the protected report's own writing-memory
citations, and this delivery's 5 public docs) before any decision was made; none was kept or
removed on the strength of its filename alone.

**42 kept, 55 archived.**

| Kept because | Count | Examples |
|---|---|---|
| Cited by the protected report's own writing/methodology notes as final evidence | 11 | the documents behind the temporal-integrity correction, the sectoral-persistence and ranking-gap audits, and the full closure chain for the known-truth benchmark |
| Cited by an active, currently-tested script's own docstring as its specification | 27 | the France ZE2020 data-treatment, training-plan, HPC-spec, dynamic-graph, and availability-mask documents still read by scripts this branch's tests exercise |
| Repository/data/code/HPC traceability maps this delivery's own docs cite | 4 | the four maps this cleanup itself used to classify every directory and script in the repository |

The 55 archived documents are **not deleted**: full copies with checksums live outside the repo
at `_delivery_cleanup_archive/2026-08-24/reports/canonical/` (recoverable independently of git),
and every one of them remains in this branch's git history (`git log --diff-filter=D -- <path>`,
or `git show <commit>:<path>` against any commit before the removal). They fall into two groups:

- **Superseded** — represented by one of the 5 public `docs/*.md` documents, by the newer
  Aug-2026 evidence chain (§2), or by this cleanup's own record (the project-phase, data-
  provenance, methods, results, dashboard-roadmap, phase-technique-matrix, and method-lineage
  overviews; the two prior organizational-backlog/worktree-audit documents; and the two
  documents auditing an *earlier* consolidation pass, now themselves superseded by this one).
- **Historical only** — individual spec/result documents for a relation-scoring gate, transfer
  probe, or architecture amendment that failed its pre-registered test and has no active code or
  report citation pointing at it. Its DEC-numbered verdict is preserved in the decision log
  either way (§6); the long-form write-up is what moved to archive.

Full per-file classification (path, disposition, justification, checksum):
`_delivery_cleanup_archive/2026-08-24/CANONICAL_ARCHIVED_MANIFEST.csv` and
`INVENTORY_AND_CLASSIFICATION.md`, both outside this repository.

No test was altered to make this consolidation possible — the dependency audit found zero test
files that `open()` or import a `reports/canonical/*.md` path; docstring/comment mentions were
treated as real dependencies (kept) precisely so that no test would need to change.

## 8. Other open items from this cleanup (need a human decision)

See `_delivery_cleanup_archive/2026-08-24/INVENTORY_AND_CLASSIFICATION.md` for the full list
(kept outside the repo). In short: the four actively-edited `train_herald_*.py` files were left
untouched (§4); large already-committed data/dashboard blobs were flagged, not moved; the
active-code renaming in §5 was deferred; and one supporting file
(`reports/HERALD_DATA_AVAILABILITY_CALENDAR.md`, cited by an earlier version of
`DATA_AND_PROVENANCE.md`) turned out to be untracked/local-only and was removed from that
citation rather than left as a broken link — it was never part of any commit this branch is
based on.
