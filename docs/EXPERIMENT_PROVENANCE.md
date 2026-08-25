# Experiment provenance

Compact map from the project's experimental history to the final, reported state. This is
deliberately short — it is an index into the deep record, not a replacement for it. The deep
record (never deleted, always the tie-breaker on a specific number) is:

- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — every decision, never renumbered or
  deleted, only corrected/superseded explicitly.
- `reports/canonical/` — the phase/spec/result documents kept in this branch because they are
  either final evidence for a number in `RESULTS_AND_LIMITATIONS.md` or a specification an
  active script's own docstring cites. See §8 for what was consolidated out of this folder and
  why, and for where every removed document still lives.
- `reports/herald_artifact_registry.json` — machine-readable per-artefact status.

## 1. Naming

This project's internal, historical experiment identifier is **`HERALD`**, an acronym coined
early in the work. It is not, and has never been, a public or scientific model name. It appears
only as a **legacy internal experiment identifier** — in job directory names (e.g.
`hpc/herald93/`), historical filenames (e.g. `train_herald_v6.py`), git history, decision-log
entries, and the titles of the `reports/canonical/` documents kept for provenance in §8. It does
not appear, and should not be reintroduced, in `README.md` or any other file under `docs/`.

The project's public/scientific name is **Neural Temporal–Relational Model**.

The public entrypoint, `scripts/run_temporal_relational_model.py`, keeps this boundary by
construction: it imports the internal `herald93_benchmark` module (a real, necessary, provenance
path) but never prints or documents that name anywhere a user reads — verified by a dedicated
test, `tests/test_model_smoke_entrypoint.py::test_cli_help_carries_no_legacy_internal_name`.

The GitHub repository's own name, `territorial-recommender-stgnn-mas`, is a third, unrelated
historical label (from before either name above); renaming the git remote was out of scope for
this cleanup.

## 2. The canonical model implementation

**File:** `src/modeles/france_ze2020/herald93_benchmark.py` (774 lines), generator
`src/data/synthetic/generate_france_multisignal_v92.py` (507 lines), driven by
`hpc/herald93/run_model_benchmark.py`. This is the implementation the main-benchmark numbers in
`docs/RESULTS_AND_LIMITATIONS.md` §0–§3 (11–24% temporal-representation gain, +0.0001 best
forecast skill, edge recovery at chance) come from, and it is the module the neutral entrypoint
(`scripts/run_temporal_relational_model.py`) calls. It was not chosen for having the highest
version number — verified directly, component by component:

| Component | Confirmed as | Where |
|---|---|---|
| Temporal encoder | `TemporalEncoder` — per-signal dilated causal Conv1d (kernel 3, dilations 1 and 2), GELU, over an 8-period window; matches `Report_project.tex`'s architecture description | `herald93_benchmark.py:402-431` |
| Relational learner | `SharedRelationalScorer` — one shared function for every candidate pair, no per-pair or per-zone parameter, LayerNorm before scoring; feeds `HeraldMultisignal`'s dynamic message-passing with a straight-through top-k | `herald93_benchmark.py:455-484, 497-572` |
| Candidate-support handling | `candidate_support()` restricts every method (including the classical and the two other neural baselines) to the same commuting-derived support; never a label, never scored for credit on its own | `herald93_benchmark.py:128-142` |
| Forecast output | `output["prediction"] = node + relational` — a local (node-only) term plus a relational (message-passing) term, explicitly summed and both exposed | `herald93_benchmark.py:566-572` |
| Connection-score output | `output["edge_weight"]` — a softmax-normalised score per candidate pair, competing within each target zone's incoming set | `herald93_benchmark.py:535-542` |
| Loss | `masked_gaussian_nll` — masked Gaussian negative log-likelihood on log-growth, one learned scale per signal, identical objective for every neural arm (`herald`, `mtgnn`, `nri`) so no arm gets a better-specified likelihood | `herald93_benchmark.py:661-666`, confirmed identical across arms by `tests/test_herald93_guards.py::test_h20_*` |
| No-mechanism control | `SCENARIOS = ("S0_NULL", "S1_SHARED")` — `S0_NULL` has no relational effect anywhere and is the false-positive floor; exposed by the entrypoint's neutral `--scenario no-mechanism` | `herald93_benchmark.py` module scope; `run_model_benchmark.py` task grid |
| Widths evaluated | `DEFAULT_HIDDEN = 64`; `FORBIDDEN_WIDTH = 256` refused by every model's own constructor (`ValueError`); confirmed refused by `tests/test_herald93_guards.py::test_h21_width_256_is_refused` | `herald93_benchmark.py:55-56, 402-402, 513-514, 586-587, 626-627` |
| Seeds | `FINAL_SEEDS = (9401, 9402, 9403, 9404, 9405)` in the generator, disjoint by assertion from `CALIBRATION_SEEDS` (9301–9320) and `FAIR_SEEDS` (9501–9520); confirmed disjoint and confirmed as the seeds actually used by `run_model_benchmark.py`'s task grid, by `tests/test_herald93_guards.py::test_h6_*` | `generate_france_multisignal_v92.py:65-70` |
| File used for the final results | `hpc/herald93/run_model_benchmark.py` — its `run_task()` is called directly by the neutral entrypoint; not a copy, not a reimplementation | verified by import (see §3) |
| Imports / dependencies | `numpy`, `torch` (optional at import time, required to run any neural arm); no dependency on any of the pre-Q7 `train_herald_{v3…v7,semi_v1,semi_v2,regime_experiment}.py` files or the `herald78…89` architecture-iteration chain — confirmed by grep, zero matches (§9) | `herald93_benchmark.py:42-49` |

**Auxiliary modules needed to run it:** `src/data/synthetic/generate_france_multisignal_v92.py`
(the generator; also depends on nothing outside itself), and, only for the wider Aug-2026
evidence chain this implementation is part of (not needed to run the model itself):
`herald92_multisignal_oracle.py` (oracle diagnostic, duplicate-signal control used by a guard),
`herald94_temporal_features.py` + `herald94_composite.py` (composite-signal arm, its own
generator `generate_france_multisignal_v94.py`), `herald95_scale_ladder.py` (relational-scale
oracle ladder), `herald96_neural_granger.py` (residual/multirelational arm, its own generator
`generate_multirelational_v96.py`). All of the above are already tracked in this branch.

**Corresponding tests:** `tests/test_herald93_guards.py` (23 guards: leakage, masks/absence,
graph mechanics, fairness between arms — 22/23 pass, see "Validation record (this delivery)" in
`docs/REPRODUCIBILITY.md` for the one pre-existing exception) and
`tests/run_herald93_mutations.py` (22 targeted mutants, 22/22 killed). Both were already tracked
and untouched by this pass; `tests/test_model_smoke_entrypoint.py` (new, this pass) guards the
entrypoint specifically.

**Historical internal identifiers this implementation is filed under:** `herald93` (job/module
identifier), `HERALD_93_MODEL_EVALUATION_AND_COMPARISON.md` (its specification/result document,
kept in `reports/canonical/`, §8). Neither appears in the public entrypoint's `--help` or in any
`docs/*.md` file as the model's name.

## 3. Historical phases → final result, in one line each

| Period | What happened | Where it lands in the final story |
|---|---|---|
| Apr–Jun 2026 | France prediction foundation, European harmonization (PT/IT/AT/NL/BE), graph branches tested and closed (P6 dual graph, graph-temporal, Phase 5 fixed-L2 corrector, geographic queen-contiguity) | Baseline/architecture-search history; none of these branches contributes a current headline number. Kept as tested-and-rejected findings, not gaps. |
| Jun 2026 | Sector precedence graph, Observatory dashboards, PT/NL granular evidence | Descriptive evidence layer; superseded as the project's central question by the Jul–Aug work below |
| Jun–Jul 2026 | France ZE2020 relational layer built up incrementally: candidate relations, a temporal-integrity (leakage) correction, dynamic-graph inputs, a long sequence of relation-scoring/transfer/fusion gates, all failing their pre-registered gates | Establishes, on real French data, that a single sparse relational signal does not reliably identify relations — motivates the multisignal synthetic redesign below |
| Aug 2026 | The known-truth synthetic benchmark (§2) | **This is the evidence base for `RESULTS_AND_LIMITATIONS.md`.** A final model comparison beyond this stage is specified but explicitly **not run**. |

## 4. Key jobs/commits and their canonical documents

| Result | Artefact | Canonical document (kept, §8) | Commit |
|---|---|---|---|
| Main-benchmark model evaluation and comparison (§2) | `hpc_results/herald93/` — **not yet mirrored into git**, see §11 | `HERALD_93_MODEL_EVALUATION_AND_COMPARISON.md` | scripts/tests committed `36ede89` |
| Temporal representation (11–24% error reduction) | `hpc_results/herald94/` | `HERALD_94_COMPOSITE_SIGNAL_SPECIFICATION.md`, `HERALD_94_COMPOSITE_SIGNAL_RESULTS.md` | `d94c97c`…`6bbed13` |
| Relational-scale oracle ladder | `hpc_results/herald95/` | `HERALD_95_RELATIONAL_SCALE_LADDER.md` | `b52ffeb`…`3125e43` |
| Residual diagnostic / all-pairs recovery test | `hpc_results/herald96/` | `HERALD_96_NEURAL_GRANGER_SPECIFICATION.md`, `HERALD_96_NEURAL_GRANGER_RESULTS.md` | `3a9e434`…`3ab599b` |
| Stage closure, frozen figures/tables | `reports/final_visual_evidence/` | `HERALD_92_EXPERIMENTAL_CLOSURE_AND_REPORT_HANDOFF.md`, `HERALD_97_STAGE_CLOSURE_AND_VISUAL_EVIDENCE.md` | `ce1a3c8`, `f730e72` |
| Final model comparison (specified, **not run**) | — | `HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md` | spec only |

## 5. Base branch and what this delivery does and does not include

This branch (`delivery/repository-cleanup`) was created from **`main` at commit `f730e72`**
("docs: close the experimental stage, and build the evidence archive it rests on"). It has
never been merged with `main` and was never intended to be created from anything other than that
one commit.

At the time this branch was created, the repository's primary (non-cleanup) working copy held
several hundred additional modified and untracked paths that were **not** part of `f730e72`.
**None of that uncommitted work was copied into this branch, automatically or otherwise**, and
the primary worktree itself was never written to by this cleanup — see §9 for the read-only
audit of exactly what those paths are, and §2 for confirmation that the canonical model needed
none of them.

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

## 6. What was and wasn't renamed, and why

The public surface (`README.md`, `docs/*.md`) uses **Neural Temporal–Relational Model** and does
not present `HERALD` as the current name. The public entrypoint (§2) is the one place the
naming boundary had to be enforced in *running code*, not just in prose, and it now is,
guarded by a test.

Renaming active code identifiers (module/class/function names across ~200 `src/` files
containing `herald`) was **not done** in this pass. A grep-verified check during the archival
step found that files the project's own repository-traceability documentation labels
"historical" are in fact still imported by active modules and covered by active tests. Given
that, a blanket or even a "safe subset" rename right before delivery was judged higher-risk than
valuable without a full call-graph pass and matching test updates. Recorded as `REVIEW_REQUIRED`
in the cleanup's external inventory for a future pass with more time budget.

## 7. Experiments discarded or invalidated, and why

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
| `herald78…89` architecture-iteration chain (pre-`herald93`) | Superseded by the `herald93_benchmark.py` implementation in §2; still uncommitted in the primary worktree (§9), not part of this branch |

Full DEC-numbered detail for every row above: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`.
None of these are reopened by this cleanup — reopening any of them requires a new decision-log
entry.

## 8. `reports/canonical/` consolidation

`reports/canonical/` held **97** phase/spec/result documents before the previous pass — the
"many historical steps" surface this cleanup targeted. Each was audited for real dependents
(active code docstrings by full filename **and** by short `HERALD_NN` id, the artifact registry,
the protected report's own writing-memory citations, and this delivery's 5 public docs) before
any decision was made; none was kept or removed on the strength of its filename alone.

**42 kept, 55 archived — re-verified this pass, no document removed just to shrink the count.**
Every one of the 42 was re-checked against the categories the task defines
(`REQUIRED_MACHINE_DEPENDENCY`, `REQUIRED_FINAL_EVIDENCE`, "required by the artifact registry,"
"necessary to interpret a frozen identifier") and confirmed to satisfy at least one:

| Kept because | Count | Examples |
|---|---|---|
| Cited by the protected report's own writing/methodology notes as final evidence | 11 | the documents behind the temporal-integrity correction, the sectoral-persistence and ranking-gap audits, and the full closure chain for the known-truth benchmark (§4) |
| Cited by an active, currently-tested script's own docstring as its specification | 27 | the France ZE2020 data-treatment, training-plan, HPC-spec, dynamic-graph, and availability-mask documents still read by scripts this branch's tests exercise |
| Repository/data/code/HPC traceability maps this delivery's own docs cite | 4 | `HERALD_08_REPOSITORY_TRACEABILITY_MAP.md`, `HERALD_09_DATA_ASSET_MAP.md`, `HERALD_10_CODE_PATH_MAP.md`, `HERALD_11_HPC_AND_RESULTS_MAP.md` — the four maps this cleanup itself used to classify every directory and script in the repository, cited directly in `DATA_AND_PROVENANCE.md` and `REPRODUCIBILITY.md` |

The 55 archived documents are **not deleted**: full copies with checksums live outside the repo
at `_delivery_cleanup_archive/2026-08-24/reports/canonical/` (recoverable independently of git),
and every one of them remains in this branch's git history (`git log --diff-filter=D -- <path>`,
or `git show <commit>:<path>` against any commit before the removal). They fall into two groups:

- **Superseded** — represented by one of the 5 public `docs/*.md` documents, by the newer
  Aug-2026 evidence chain (§4), or by this cleanup's own record.
- **Historical only** — individual spec/result documents for a relation-scoring gate, transfer
  probe, or architecture amendment that failed its pre-registered test and has no active code or
  report citation pointing at it. Its DEC-numbered verdict is preserved in the decision log
  either way (§7); the long-form write-up is what moved to archive.

Full per-file classification (path, disposition, category, justification, checksum):
`_delivery_cleanup_archive/2026-08-24/CANONICAL_CLASSIFICATION.csv`, outside this repository.

No test was altered to make this consolidation possible — the dependency audit found zero test
files that `open()` or import a `reports/canonical/*.md` path; docstring/comment mentions were
treated as real dependencies (kept) precisely so that no test would need to change.

## 9. Read-only audit of the primary worktree's pending changes

The primary worktree (outside this branch, never written to by this cleanup) holds 383
modified/untracked paths at the time of this audit. Classified by cluster, without moving or
touching any of them:

| Cluster | Files | Classification | Needed for this delivery? |
|---|---|---|---|
| `reports/final_visual_evidence/*`, `reports/results_evidence_selection/*` | ~145 | `REPORT_OR_PRESENTATION_DEPENDENCY` / `CONCURRENT_USER_WORK` | Protected, not touched — see §11 |
| `src/modeles/train_herald_{v6,v7,semi_v2,regime_experiment}.py` | 4 | `CONCURRENT_USER_WORK` / `LEGACY_EXPERIMENT` | No — audited in §10 |
| `src/modeles/france_ze2020/herald{78,79,80,82,83,84,85,87,88,89}*.py`, matching `hpc/herald{78,79,80,83,84,85,87,88,89}/`, matching `tests/test_herald{78…89}*guards.py` and `tests/run_herald{78…89}*mutations.py` | ~30 | `LEGACY_EXPERIMENT` | No — pre-`herald93` architecture iterations; `herald93_benchmark.py` imports none of them (verified by grep, §2) |
| `hpc/phase4/*` (new audit/config/run scripts) | ~55 | `LEGACY_EXPERIMENT` | No — historical Phase 4 sub-steps, already superseded (§7) |
| `hpc_results/herald{78,79,80,84,85,88,89,90,91,92,93}/`, `hpc_results/herald_phase4*`, `hpc_results/smoke_phase4*`, `hpc_results/fr_ze2020_*` (single-signal chain outputs), `hpc_results/dual_graph_s1/`, `hpc_results/phase10_synthetic_lagged/`, `hpc_results/phase7_pt_municipal/` | ~85 | `GENERATED_LARGE_RESULT` | Partially — `hpc_results/herald93/` specifically backs the main-benchmark numbers already cited in `docs/RESULTS_AND_LIMITATIONS.md` and is flagged, not copied, in §11 |
| `data/external/austria/`, `data/external/eurostat_business_demography/`, `data/processed/european_panel/at_panel.csv` and related Austria/third-country enterprise-birth files, `data/external/italy/processed/*` (modified) | ~10 | `UNRELATED_COUNTRY_EXPERIMENT` | No — European-panel harmonization work, unrelated to the France ZE2020 neural model |
| `data/processed/dual_graph_pilot_all_folds/`, `data/processed/graph_temporal_s1/folds_observed/`, `data/processed/graph_temporal_v2/` | 3 dirs | `LEGACY_EXPERIMENT` / `GENERATED_LARGE_RESULT` | No — outputs of closed branches (§7) |
| `data/processed/france_ze2020/*_v1.csv` (baseline/exploratory/multisource/neural-relational/sector-graph/urssaf outputs, 25 files) | 25 | `REVIEW_REQUIRED` | Not for the model (§2 needs none of them); possibly `REQUIRED_FINAL_EVIDENCE` for the report's French Appendix — not verified this pass, left for a future targeted check rather than guessed at |
| `hpc/phase4/run_herald_phase4e_a2_wrapper.py` (modified), `reports/HERALD_CURRENT_STATE.md` (modified), `reports/canonical/HERALD_{17,18,20,77}*.md` (modified) | 6 | `CONCURRENT_USER_WORK` | No — pre-existing files under active edit; not read for content, only their path was seen in `git status` |
| `src/data/france_ze2020/{build_fr_ze2020_long_panel,fetch_fr_ze2020_raw_sources,fr_ze2020_sources,report_fr_ze2020_coverage,validate_urssaf_regional_aggregation}.py`, `src/data/ingest_eurostat_enterprise_birth_panel.py`, `src/data/european_panel/{adapters/at_adapter,preflight_enterprise_birth_candidates}.py`, `src/modeles/herald_fold_controls.py` | 9 | `REVIEW_REQUIRED` (`REQUIRED_FINAL_DATA_PIPELINE` candidate) | No — confirmed by grep that nothing in the model/generator/test chain in §2 imports any of them; data-pipeline work for a different part of the project, out of scope for this step |
| `README.md` (modified, primary worktree's own copy), `reports/dashboards/*.html` (modified) | 3 | `CONCURRENT_USER_WORK` | No |

**Selective incorporation result: zero files copied from the primary worktree into this branch.**
The canonical model, its generator, its guard suite, and its mutation suite (§2) were already
fully committed at `f730e72`; nothing the primary worktree is still editing was needed to build
the entrypoint or the smoke test. This was verified, not assumed — see the import-dependency
grep referenced in §2's last row.

## 10. The four actively-edited training files

| File | Participates in the final implementation (§2)? | Imported by it? | Used by any test? | Status |
|---|---|---|---|---|
| `src/modeles/train_herald_v6.py` | No | No | No | `LEGACY_EXPERIMENT`, pre-Q7 architecture search; under active edit in the primary worktree |
| `src/modeles/train_herald_v7.py` | No | No | No | Same |
| `src/modeles/train_herald_semi_v2.py` | No | No | No | Same |
| `src/modeles/train_herald_regime_experiment.py` | No | No | No | Same |

None of the four is imported by `herald93_benchmark.py`, `generate_france_multisignal_v92.py`,
`hpc/herald93/run_model_benchmark.py`, or any test in §2 (confirmed by grep). They are fully
superseded by the neutral entrypoint for anyone wanting to run "the model." They were **not**
renamed or removed, per instruction, because they are under active edit in the primary worktree;
none of the three needs (final implementation, test dependency, or public entrypoint) requires
touching them. They remain an internal historical dependency only insofar as `git blame`/history
still traces through them — no current script imports them.

## 11. Report and presentation resources — pending gate, not a failure

`reports/final_visual_evidence/`, `reports/results_evidence_selection/`, the report, the
presentation, TikZ diagrams, and the PDFs/PNGs they use were **not touched, copied, or
synchronized** in this pass — they are still being edited by the user (§9). This is a
**deliberate, pending gate**, not an omission: once the report and presentation are frozen, a
future pass should selectively pull the final versions of whichever figures/tables/captions
changed since `f730e72` into this branch (they are already git-tracked at `f730e72`; only the
*newer, uncommitted* versions in the primary worktree are outstanding). Also outstanding for the
same reason: `hpc_results/herald93/` (§4) is not yet mirrored into git the way `herald94-96` were
in commit `ce1a3c8` — the *derived* tables (`reports/final_visual_evidence/tables/T04*.md`,
`T05*.md`) are already committed and protected, but their *raw* per-task provenance currently
exists only in the primary worktree. Do not present this branch as containing the final,
frozen visual/report evidence until this gate is closed.

## 12. Large blobs already committed

No git history rewrite, LFS migration, or removal was performed — this is a list and a
recommendation only, per instruction.

| Path | Size | Type | Current use | Recommendation |
|---|---|---|---|---|
| `data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges*.csv(.gz)` (9 files) | 10–61MB each, ~230MB total | Derived edge tables | Inputs to the now-closed single-signal relation-gate chain (§7); **not** read by the canonical model in §2 | Retire from the current tree in a future pass, or Git LFS if any still-active script needs them |
| `data/interim/policy/{policy_commune_status,zan_consumption_communes,zrr_historique_communes}_v0.csv` | 17–48MB, ~83MB total | Interim policy/zoning tables | Feeds descriptive French context, not the neural model | Keep (not easily re-downloaded); Git LFS candidate in a future migration |
| `data/external/netherlands/raw/cbs/81578NED_corop.csv` | 42MB | Raw external ingestion cache | Should typically be gitignored per `data/README.md`'s own policy; committed here as an exception | Retire from the current tree in a future pass — regenerable via `src/data/ingest_netherlands_panel.py` |
| `reports/dashboards/*.html` (4 files: `fr_ze2020_dashboard_mvp`, `herald_observatory_v051_narrative`, `herald_observatory_v05_narrative`, `herald_observatory_v03`) | 9–20MB each, ~65MB total | Single-file static dashboards with embedded data | Currently linked from `README.md`/canonical docs as the visualization layer | Git LFS candidate; the README's own "next step" already proposes a modular, non-monolithic redesign |
| `data/processed/herald_observatory_v04_granular/granular_territory_state_panel.csv` | 25MB | Dashboard export | Regenerable build output, currently committed | Keep for now, or generate-on-demand in a future dashboard redesign |
| `data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv` | 17MB | Derived panel | Feeds the NL gemeente proxy result, which is **blocked** for relation labels (a documented, closed finding) | Keep (small enough, and the blocked status itself is citable evidence) |
| `data/processed/france_ze2020/{fr_ze2020_sector_ranking_panel,fr_ze2020_dynamic_graph_nodes}.csv` | 14–15MB each | Derived panels | Same closed single-signal chain as the edge tables above | Same recommendation |
| `data/processed/phase7_nl_gemeente_proxy/nl_gemeente_phase7_panel.csv` | 10MB | Derived panel | Same NL gemeente proxy (blocked) result | Keep |

None of these were required to build the entrypoint or the smoke test in §2 — the synthetic
generator creates its own panel in memory and reads nothing from `data/`.
