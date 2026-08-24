# Experiment provenance

Compact map from the project's experimental history to the final, reported state. This is
deliberately short — it is an index into the deep record, not a replacement for it. The deep
record (never deleted, always the tie-breaker on a specific number) is:

- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — every decision, DEC-001 → DEC-146+, never
  renumbered or deleted, only corrected/superseded explicitly.
- `reports/canonical/` — 97 numbered documents, one per phase/audit/spec/result. Kept in full
  in git history and in the current tree; not required reading to understand the current state
  (that's what this document and `RESULTS_AND_LIMITATIONS.md` are for), but the citable source
  for a specific number's method and controls.
- `reports/herald_artifact_registry.json` — machine-readable per-artefact status.

## 1. Naming map

| Historical identifier | Current status | Where it may still appear |
|---|---|---|
| **HERALD** (*Heterogeneous Economic Relational Adaptive Learning for territorial Dynamics*) | Legacy internal experiment identifier. Not the public/scientific name. | Job directory names (`hpc/herald9X/`, `hpc_results/herald9X/`), historical filenames (`train_herald_v6.py`), git history, `reports/canonical/HERALD_*.md` titles, the decision log. **Not** in `README.md`, `docs/*.md`, or `package.json`. |
| **Neural Temporal–Relational Model** | Current public/scientific name | `README.md`, `docs/*.md`, the report and presentation (`Pesquisa_stage/report_present/`) |
| `temporal_relational_model`, `neural_temporal_relational`, `relation_learner`, `temporal_encoder` | Suggested neutral short forms for **new** code identifiers | Not yet applied to existing active modules — see §4 |
| GitHub repository name `territorial-recommender-stgnn-mas` | Historical, unrelated to either name above | Git remote URL only; renaming the remote was out of scope for this cleanup |

`HERALD` job/experiment identifiers (e.g. `herald93`, `herald_phase4e_b`, DEC-* numbers) are
kept exactly as-is inside `hpc/`, `hpc_results/`, and the decision log, because rewriting them
would destroy the traceability between a reported number and the job that produced it. They are
internal experiment identifiers, not the model's name, and should be read as such.

## 2. Historical phases → final result, in one line each

| Period | What happened | Where it lands in the final story |
|---|---|---|
| Apr–Jun 2026 | France prediction foundation (Q7 architecture selection), European harmonization (PT/IT/AT/NL/BE), graph branches tested and closed (P6 dual graph, graph-temporal GConvGRU/EvolveGCN-H, Phase 5 fixed-L2 corrector, geographic queen-contiguity) | Baseline/architecture-search history; none of these branches contributes a current headline number. Kept as tested-and-rejected findings, not gaps. |
| Jun 2026 | Sector precedence graph (Phase 7), Observatory dashboards v0.3→v0.5.1, PT/NL granular evidence | Current descriptive evidence layer; still valid but superseded as the project's central question by the Jul–Aug work below |
| Jun–Jul 2026 | France ZE2020 relational layer built up incrementally: candidate relations, temporal-integrity correction (leakage fix), dynamic-graph inputs, a long sequence of relation-scoring/transfer/fusion gates (DEC-069→080), all failing pre-registered gates | Establishes, on real French data, that a single sparse relational signal does not reliably identify relations — motivates the multisignal synthetic redesign below |
| Aug 2026 | HERALD 93–98: the known-truth synthetic benchmark, temporal representation + composites, the relational-scale ladder (oracle), the multirelational/Neural Granger arm, stage closure and the frozen visual-evidence archive | **This is the evidence base for `RESULTS_AND_LIMITATIONS.md`.** DEC-146 freezes it; `HERALD_98` (final model comparison) is specified but explicitly **not run**. |

Full narrative version: `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` (written
2026-06-18 — accurate up to that date; read together with the Aug 2026 rows above, which
postdate it).

## 3. Key jobs/commits behind the current results

| Result | Artefact | Commit |
|---|---|---|
| Temporal representation (11–24% error reduction) | `hpc_results/herald94/` | `d94c97c`…`6bbed13` |
| Relational-scale ladder / oracle | `hpc_results/herald95/` | `b52ffeb`…`3125e43` |
| Multirelational / Neural Granger arm, `all_pairs` diagnostic | `hpc_results/herald96/` | `3a9e434`…`3ab599b` |
| Stage closure, frozen figures/tables | `reports/final_visual_evidence/` | `ce1a3c8`, `f730e72` |
| Final model comparison (specified, **not run**) | — | spec only: `reports/canonical/HERALD_98_FINAL_MODEL_COMPARISON_SPECIFICATION.md` |

## 4. What was and wasn't renamed, and why

The public surface (`README.md`, `docs/*.md`, `package.json` name/description) uses **Neural
Temporal–Relational Model** and does not present `HERALD` as the current name.

Renaming active code identifiers (module/class/function names across ~200 `src/` files
containing `herald`) was **not done** in this pass. During the archival step of this cleanup, a
grep-verified check found that files the project's own `HERALD_10_CODE_PATH_MAP.md` labels
"historical" are in fact still imported by active modules and covered by active tests (e.g.
`src/modeles/phase5/rolling_origin.py` and `manifest.py` are used well outside the closed Phase
5 branch). Given that, a blanket or even a "safe subset" rename right before delivery was judged
higher-risk than valuable without a full call-graph pass and matching test updates. This is
recorded as `REVIEW_REQUIRED` in the cleanup's inventory
(`_delivery_cleanup_archive/2026-08-24/INVENTORY_AND_CLASSIFICATION.md`, outside this repo) for
a future pass with more time budget.

## 5. Experiments discarded or invalidated, and why

| Branch | Verdict | DEC |
|---|---|---|
| P6 dynamic dual graph | `DUAL_GRAPH_S1_FAIL`, all 7 gate criteria fail | DEC-029 |
| Graph-temporal (GConvGRU/EvolveGCN-H) | `S1_FR_FAIL` | DEC-031 |
| Phase 5 fixed-L2 residual corrector | `NOT_SUPPORTED` | DEC-023 |
| Geographic queen-contiguity graph | Refuted under current protocol (Italy, p=0.19/0.32) | DEC-008/009 |
| ARDECO-extended FR Ridge | Closed exploration | — |
| France single-signal relation gates (DEC-069→080: transition transfer, edge-family isolation, similarity nonlinear transfer, bottleneck fusion, commuting relation/topology gates, context-conditioned sector relation, product-space entry density, temporal bipartite reconstruction, composition transition ranking) | Each fails its pre-registered gate | DEC-069→080 |
| Six declared composite economic signals | All negative, none adds information | DEC-142 (`HERALD_94`) |
| Declared multisignal-complementarity mechanism | Not supported (median −0.07pp) | `HERALD_91` |
| HERALD Q7 France WMAPE 0.0204 | `PENDING_REAUDIT` — potential causal-feature leakage; **not usable as a headline claim** | Phase 3E/2R |
| P6 `learned_sector_edges.csv` sector labels | `INVALID_FOR_INTERPRETATION` — labels don't match the tensor's actual `sector_id`s; file kept for historical record only | Charter §6 |

None of these are reopened by this cleanup. Reopening any of them requires a new DEC-* entry
per `reports/HERALD_PROJECT_CHARTER.md` §8.

## 6. Open items from this cleanup (need a human decision)

See `_delivery_cleanup_archive/2026-08-24/INVENTORY_AND_CLASSIFICATION.md` §5 for the full list
(kept outside the repo, not part of this delivery branch). In short: a deeper per-file audit of
`reports/canonical/HERALD_01…91.md` and the untracked root `reports/*.md` files was not
attempted; four actively-edited `train_herald_{v6,v7,semi_v2,regime_experiment}.py` files were
left untouched; large already-committed data/dashboard blobs were flagged, not moved; and the
active-code renaming in §4 above was deferred.
