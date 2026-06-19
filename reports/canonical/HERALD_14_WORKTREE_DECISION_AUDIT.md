# HERALD 14 — Worktree Decision Audit

**Created:** 2026-06-18 (decision audit over the uncommitted worktree state recorded in
`reports/canonical/HERALD_13_ORGANIZATION_BACKLOG.md`).
**Status:** Documentation only. Nothing was moved, renamed, deleted, `git add`'d,
`git rm`'d, reset, or checked out to produce this audit. No dashboard, model, dataset,
or HPC file was modified.
**Method:** `git status --short` for inventory; `git diff -- <path>` for every tracked
modified file; `du -sh`/`find`/`ls`/`head` for untracked folders (no large dataset
opened in full); `sed -n` on script/test headers and imports only (no test executed).
**Purpose:** turn the raw worktree-dirty inventory into a per-group decision so a human
can act (or explicitly defer) without re-deriving this analysis.

---

## Key finding worth flagging before the table

Several scripts that produce **already-cited, already-frozen DEC results** are not in
the git index at all — only their output reports/exports were ever committed. Most
notably: `data/processed/sector_precedence_results/` (the raw Phase 7 HPC bundle behind
DEC-034) was **entirely untracked**, as are the builder scripts for G1-L1 (DEC-017),
G1-observable, and the closed-branch P6 dual-graph target/tensor builders. This is a
traceability gap, not a new scientific finding — the numbers themselves are unaffected
(they're already

frozen in the decision log), but reproducing them from a fresh clone currently would not
have been possible. This was `HIGH` risk for the sector-precedence group specifically,
`MEDIUM` for the others.

**Resolved 2026-06-19 (sector precedence only):** `data/processed/sector_precedence_results/`
is now committed. Resolving it surfaced one correction: the original phrasing of this
finding conflated two different artifacts. `sector_precedence_results/` is the **raw**
Phase 7 run (DEC-034): 25 main-promoted edges (FR=1/NL=8/PT=16), 12 of which are
COVID-robust (FR=0/NL=3/PT=9). The "20 edges, FR=9/NL=8/PT=3" figure that earlier drafts
of this audit cited belongs to a **different, already-tracked** file —
`data/processed/herald_observatory_v04_granular/granular_relation_edges.csv` (the
DEC-066 fine-grain-relabeled export). Both are real and both are correctly cited
elsewhere; they must not be conflated. See the resolved row in the table below. The
G1-L1/observable and dual-graph rows remain open (`COMMIT_AFTER_TESTS`, not yet acted on).

Separately: the Italy/Austria group is not just a re-run — `git diff` shows the Italy
panel's **column order changed** (`region_name`/`year` swapped) via a new shared
`decode_jsonstat` utility, and the IT/AT adapters gained a **mainland-vs-island
territorial-scope split** (excluding Sicily/Sardinia from "mainland") that does not
correspond to any existing DEC entry. The underlying birth/stock *values* are unchanged
(verified by diffing specific rows) — only column order and scope-filtering logic
changed. This looks like genuine in-progress work toward extending Path H, not noise,
and should not be committed without a new DEC covering the territorial-scope decision.

---

## Decision matrix

| Group | Paths | Git state | Approx. size | Phase/DEC (likely) | Category | Scientific status | Risk | Recommended action | Justification | Suggested future command |
|---|---|---|---|---|---|---|---|---|---|---|
| Italy IT adapter + IT panels | `data/external/italy/processed/italy_births_panel_nuts3.csv`, `italy_ingest_manifest.json`, `src/data/ingest_italy_panel.py`, `src/data/european_panel/adapters/it_adapter.py`, `data/processed/european_panel/it_panel.csv` | modified (tracked) | small (CSV <1MB) | Path H / DEC-005, extends toward a new mainland-scope decision | DATA + CODE | PARTIAL (values unchanged, schema + scope logic changed) | **HIGH** | `REQUIRES_NEW_DEC` | Column order changed and a new "Italian mainland" territorial scope (Sicily/Sardinia excluded) was introduced with no corresponding DEC; values themselves verified unchanged by spot-diff | Pre-register a DEC for the mainland-scope decision before committing; then `git add` + run `tests/test_*italy*` |
| Austria AT panels (new) | `data/external/austria/`, `src/data/european_panel/adapters/at_adapter.py` (untracked), `data/processed/european_panel/at_panel.csv`, `enterprise_birth_pt_it_at_mainland_panel.csv`, `enterprise_birth_pt_it_at_mainland_summary.json`, `enterprise_birth_third_country_preflight.json` | mixed (mostly untracked) | small (60K external + small CSVs) | Extends Path H beyond the existing PT/IT/AT-via-DEC-005 panel into a 3-country "mainland" subpanel | DATA + CODE | PARTIAL (in progress, not yet a DEC) | **HIGH** | `REQUIRES_NEW_DEC` | Same root cause as the Italy row — AT is being added to a new "mainland" Path H variant not yet decided; bundle with the Italy DEC | Same DEC as above; do not commit ahead of it |
| Eurostat business demography (raw cache) | `data/external/eurostat_business_demography/` | untracked | 191M | Feeds DEC-038 coverage work / the AT/IT extension above | DATA | n/a (raw cache) | LOW | `ADD_TO_GITIGNORE` | Raw ingestion cache, regenerable from `src/data/ingest_eurostat_enterprise_birth_panel.py`; matches the existing `.gitignore` pattern for `data/external/*/raw/` in spirit | Add `data/external/eurostat_business_demography/` (or its raw subfolder) to `.gitignore` |
| `nuts3_2021_eurostat.geojson` | `data/external/nuts3_2021_eurostat.geojson` | untracked | 7.2M | Geometry input, likely for the mainland-scope split above | DATA | n/a | LOW | `ADD_TO_GITIGNORE` or `KEEP_LOCAL_ONLY` | Geometry input file, regenerable from the Eurostat source; not a processed/canonical export | Confirm regeneration script, then gitignore |
| Eurostat JSON-stat decoder (new utility) | `src/data/european_panel/eurostat_jsonstat.py`, `tests/test_eurostat_jsonstat.py` | untracked, bundled pair | tiny | Generic utility behind the Italy fix above | CODE + TEST | ACTIVE (utility) | MEDIUM | `COMMIT_AFTER_TESTS` | Code+test bundle exists together; this is a clean, generic, well-tested utility — but committing it alongside the Italy adapter change implicitly endorses the scope change, so sequence it after the DEC above | `pytest tests/test_eurostat_jsonstat.py -q`, then `git add src/.../eurostat_jsonstat.py tests/test_eurostat_jsonstat.py` |
| Sector precedence results (Phase 7 DEC-034 raw HPC bundle) | `data/processed/sector_precedence_results/`, `hpc/phase7_sector_precedence/configs/full_run.json` | was untracked, **now committed** | 1.9M data + 1 small config | DEC-033/034 — raw source: 25 main promoted (FR=1/NL=8/PT=16), 12 COVID-robust (FR=0/NL=3/PT=9) | RESULT + HPC config | **VALID** (`SECTOR_PRECEDENCE_PROTOTYPE_READY`), own audit PASS, commit_sha verified in repo history, 0 NaN/Inf among promoted rows, 0 NL gemeente proxy presence | RESOLVED (was HIGH) | `RESOLVED_COMMITTED` | Verified internally consistent (own `audit_report.json` PASS) and externally consistent (commit_sha `3665f53` exists, matches a real "implement signed sector precedence graph" commit); `tests/test_phase7_hpc_assets.py` + `tests/test_sector_precedence_graph.py` (47 tests) pass | Committed: `17e3b97` |
| G1-L1 / G1-observable builders (source for an already-cited DEC-017 result) | `src/data/european_panel/build_g1_l1_sector_graph.py`, `build_g1_observable_graph.py`, `tests/test_g1_l1_sector_graph.py`, `tests/test_g1_observable_graph.py` — **now committed (code+tests only)** | code+tests committed; outputs remain untracked | code+tests: 34K total. Outputs (NOT committed, regenerable): `g1_l1_sector/` 64K, `g1_observable/` 4.9M, `g2_preflight/` 2.0M, `sector_panel_fr_nuts3.csv` 1.9M | DEC-017 (`NOT_SUPPORTED`), G0/G1 contract | CODE + TEST (committed) / RESULT (outputs, kept local) | **CLOSED / `NOT_SUPPORTED` — unchanged.** This commit adds reproducibility of *why* it was rejected, it does not reopen the branch, promote a result, or alter any gate/claim | RESOLVED (was MEDIUM) | `RESOLVED_COMMITTED_CODE_TESTS` | Verified: no absolute paths, no NL gemeente/proxy reference, no dashboard dependency, writes confined to `data/processed/economic_graph/{g1_l1_sector,g1_observable}/`; 4 unit tests per script (22 total incl. registry) pass on pure functions with no I/O | `pytest tests/test_g1_l1_sector_graph.py tests/test_g1_observable_graph.py -q` → 22 passed; outputs intentionally left untracked/regenerable |
| Dual graph (P6) — data | `data/processed/dual_graph_pilot_all_folds/`, `dual_graph_preflight/`, `dual_graph_tensors/`, `hpc_results/dual_graph_s1/` | untracked | ~9.3M (488K+32K+6.3M+2.5M) | DEC-029, `DUAL_GRAPH_S1_FAIL` | DATA (RESULT) | **CLOSED_FAIL — unchanged** | LOW | `KEEP_LOCAL_ONLY` | Per Charter §8, this branch is closed — no reuse without a new DEC. Regenerable from the now-committed code; not needed in git | None — left untracked/regenerable by design |
| Dual graph (P6) — code + tests | `src/data/european_panel/build_dual_graph_tensors.py`, `audit_dual_graph_targets.py`, `tests/test_dual_graph_targets.py`, `tests/test_dual_graph_tensors.py` | was untracked, **now committed (code+tests only)** | code+tests: 48K total | DEC-029, `DUAL_GRAPH_S1_FAIL` | CODE + TEST | **CLOSED_FAIL — unchanged.** Commit is rastreability of *why* it failed, not a reopening | RESOLVED (was MEDIUM/part of the row above) | `RESOLVED_COMMITTED_CODE_TESTS` | Verified: no absolute paths, no NL gemeente/proxy/dashboard reference, writes confined to `data/processed/dual_graph_{tensors,preflight}/`, causal contract explicit in the audit script's docstring; 72 tests pass (incl. registry) | `pytest tests/test_dual_graph_targets.py tests/test_dual_graph_tensors.py -q` → 72 passed. **Known follow-up gap:** `build_dual_graph_tensors.py` imports `prepare_ardeco` from `src/modeles/run_ardeco_ridge_fr.py`, which is **still untracked** (separate ARDECO bundle, open `COMMIT_AFTER_TESTS` row below) — a fresh clone would fail this import until that bundle is also committed; tests pass here only because the file exists locally |
| Graph-temporal outputs | `data/processed/graph_temporal_s1/folds_observed/`, `data/processed/graph_temporal_v2/` | untracked | ~12M | DEC-031, `S1_FR_FAIL` | DATA (RESULT) | **CLOSED_FAIL** | LOW | `KEEP_LOCAL_ONLY` | Closed branch; the result is already frozen and cited (canonical #4/#10). This is regenerable tensor data, no code found untracked alongside it in this pass | None — leave as-is or add to `.gitignore` explicitly |
| Synthetic benchmark outputs | `data/processed/synthetic_benchmark/{convergence_probe,diagnostic,full,ofat,phase10_pilot,phase11_pilot,phase12_pilot,phase13_pilot,phase14_convergence_v2,phase15_stable_objective,sensitivity_smoke}/` | untracked | 4.7M | DEC-039→DEC-059 research track | DATA (RESULT) | **PARTIAL** (research track) | LOW | `ADD_TO_GITIGNORE` / `KEEP_LOCAL_ONLY` | Regenerable from `src/modeles/synthetic/`; the headline numbers (AUC=0.690, 0.611, 0.500, etc.) are already frozen in the decision log and canonicals — raw run outputs don't need to live in git | Add `data/processed/synthetic_benchmark/` to `.gitignore` if not already covered |
| Real weak-label / DEC-059 outputs | `data/processed/real_dec059_results/all_window_scores.csv`, `data/processed/real_weak_label_results/weak_label_scores.csv` | untracked | small (~108K combined) | DEC-058/059, `REAL_WEAK_LABEL_TUNING_PARTIAL` | RESULT | **PARTIAL** | MEDIUM | `COMMIT_AFTER_TESTS` | Small files, directly back the 0.438/0.500 sign-concordance figures now precisely cited in canonical #3/#4 after the deep-audit gap fix — worth committing for traceability of that specific correction | Confirm against `tests/test_dec059_*.py` if present, then commit |
| `hpc/phase4/` untracked scripts (audit_*, run_*, configs, sbatch/sh) | ~50 files under `hpc/phase4/` | untracked | 1.3M | DEC-006/007/008/009 sub-phases (4E-F, 4G, 4G-B/C, 4H-B/LOCO, 4I-A, 4N, 4O-B/C, 4P, 4Q) | HPC (CODE) | Mixed: ACTIVE (4N, 4O) / **CLOSED_FAIL** (4P, 4Q) / historical (4G/4H/4I) | MEDIUM | `COMMIT_AFTER_TESTS` | These are the actual job scripts behind already-cited DEC-006→009 results; same traceability concern as the sector-precedence gap, scoped to HPC submission scripts rather than data | `pytest tests/test_phase4o_spatial.py tests/test_phase4p_italy_spatial_lag.py tests/test_phase4q_italy_spatial_durbin.py -q`, then commit script+test bundles per sub-phase |
| `hpc_results/` (~30 untracked job-output folders, e.g. `herald_phase4*_be/nl/pt*`, `smoke_phase4*`, `dual_graph_s1/`, `phase10_synthetic_lagged/`, `phase7_pt_municipal/`) | see `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md` for the full per-job classification | untracked | **2.4G total** | Spans DEC-001→DEC-065 per canonical #11 | HPC (RESULT) | Mixed: VALID / CLOSED_FAIL / HISTORICAL/superseded per job (see #11) | LOW (none of it is the *only* copy of a cited number — manifests/decisions are already in `data/processed/`) | `ADD_TO_GITIGNORE` | 2.4 GB is too large to track; canonical #11 already has the per-job interpretation, so losing raw logs from git doesn't lose any traceability already captured there | Confirm `.gitignore` covers `hpc_results/**/*.npz`, `*.csv`, `*.err`, `*.out` as already declared; audit any folder slipping through |
| `scripts/` (new untracked dir) | `scripts/prepare_task_manifest.py`, `audit_sector_precedence_results.py`, `merge_sector_precedence_results.py` | untracked | tiny | Phase 7 tooling | CODE (UTILITY) | ACTIVE (utility) | LOW | `COMMIT_AFTER_TESTS` | Small, named utility scripts directly tied to Phase 7 (sector precedence) result preparation/audit — same traceability family as the sector_precedence_results gap | Confirm no test references these directly, then commit as utility scripts |
| Untracked tests with no corresponding code | (all bundled pairs above are accounted for — no orphan test found in this pass) | — | — | — | TEST | — | — | — | Every untracked test in this worktree was matched 1:1 to an untracked or modified source module above; none should be committed alone | — |
| `train_herald_v6.py`, `train_herald_v7.py`, `train_herald_semi_v2.py`, `train_herald_regime_experiment.py` (modified) | pre-Q7 HISTORICAL_EXPERIMENT scripts per canonical #10 | modified (tracked) | 15-119 line diffs each | predates DEC log; superseded by Q7 | CODE | HISTORICAL (superseded) | MEDIUM | `HUMAN_REVIEW_REQUIRED` | Real new functionality added (e.g. V6 gained a `fit_zone_mask` parameter for Ridge fitting) to scripts that are otherwise superseded — needs a human to say whether this is intentional revival/experimentation or accidental scope creep | Review diff with whoever is doing this work before any commit decision |
| Observatory v0.5/v0.5.1 manifest timestamps | `data/processed/herald_observatory_v051_narrative/manifest.json`, `herald_observatory_v05_narrative/manifest.json` | modified (tracked) | trivial (`generated_at` timestamp only) | DEC-067/068 | DASHBOARD (manifest) | Unaffected (cosmetic) | LOW | `DO_NOT_TOUCH_DASHBOARD_YET` | Only the `generated_at` ISO timestamp differs — a harmless re-run artifact — but per the hard rule for this task, no dashboard-adjacent file is touched, including its manifest, until the modular redesign work begins | None now |
| Observatory dashboard HTML files | `reports/dashboards/herald_observatory_v051_narrative_dashboard.html`, `herald_observatory_v05_narrative_dashboard.html` | modified (tracked) | 1-line diff each (likely an embedded timestamp/hash) | DEC-067/068 | DASHBOARD | Unaffected (cosmetic) | LOW | `DO_NOT_TOUCH_DASHBOARD_YET` | Explicit hard rule for this task | None now |
| Bibliography additions | `reports/bibliography/HERALD_REFERENCES_MASTER.md` | was modified, **now committed** | +97/-3 lines, pure addition (9 new refs R-043→R-051) | DEC-057 (Axis 15, weak supervision references: Snorkel, Group DRO, IRM, co-teaching, PU learning, signed/directed GNN, GraphMAE, PatchTST) | DOC | VALID (reference material) | LOW | `RESOLVED_COMMITTED` | Verified single hunk, purely additive (no deletions), format matches existing entries exactly, metrics table (Total/PREPRINT/Axes counts) updated consistently with the 9 additions, no local paths/personal notes/disguised methodology | Committed: see Part 4 |
| `src/data/european_panel/build_nl_gemeente_phase7_panel.py`, `preflight_enterprise_birth_candidates.py`, `src/data/ingest_eurostat_enterprise_birth_panel.py`, `src/modeles/herald_fold_controls.py`, `src/modeles/run_ardeco_ridge_fr.py` (+ matching tests `test_ardeco_fr_extension.py`, `test_ardeco_ridge_fr.py`, `test_build_fr_nuts3_sector_panel.py`) | untracked, mostly bundled with their tests | small | DEC-063/065 (NL gemeente), DEC-038 (Eurostat coverage), ARDECO closed exploration | CODE + TEST | Mixed: ACTIVE (NL gemeente, Eurostat ingestion) / CLOSED (ARDECO) | MEDIUM (raised from low priority: `run_ardeco_ridge_fr.py` is now also a hard import dependency of the already-committed `build_dual_graph_tensors.py` — see the dual-graph row above) | `COMMIT_AFTER_TESTS` | Same traceability-gap pattern: source code behind already-cited DEC-063/065/038 results is untracked. ARDECO scripts are closed-exploration but still deserve a code+test commit for audit trail, and `run_ardeco_ridge_fr.py` specifically should be prioritized next to close the dual-graph import gap | `pytest tests/test_ardeco_fr_extension.py tests/test_ardeco_ridge_fr.py tests/test_build_fr_nuts3_sector_panel.py -q`, then commit each bundle — prioritize `run_ardeco_ridge_fr.py` + `test_ardeco_ridge_fr.py` |

---

## Summary counts

| Recommended action | Count of groups |
|---|---|
| `REQUIRES_NEW_DEC` | 2 (Italy mainland-scope, Austria mainland Path H) |
| `RESOLVED_COMMITTED` | 2 (sector precedence results + Phase 7 config, 2026-06-19; bibliography additions, 2026-06-19) |
| `RESOLVED_COMMITTED_CODE_TESTS` | 2 (G1-L1/observable builders + tests, 2026-06-19; dual-graph builders + tests, 2026-06-19 — both with outputs intentionally left untracked) |
| `COMMIT_AFTER_TESTS` | 5 (hpc/phase4 scripts, real weak-label outputs, eurostat decoder, NL gemeente/ARDECO/Eurostat-ingestion bundle) — top-level `scripts/` symlinks excluded: they embed an absolute local path (`/home/jpdark/...`) and would break on any other clone. ARDECO (`run_ardeco_ridge_fr.py`) now priority within this group — see dual-graph row's known follow-up gap |
| `ADD_TO_GITIGNORE` | 4 (Eurostat business demography raw, NUTS3 geojson, synthetic_benchmark outputs, hpc_results) |
| `KEEP_LOCAL_ONLY` | 2 (dual-graph data, graph-temporal data) |
| `DO_NOT_TOUCH_DASHBOARD_YET` | 2 (dashboard HTML, narrative manifests) |
| `HUMAN_REVIEW_REQUIRED` | 1 (train_herald_v6/v7/semi/regime new functionality) |

## What this audit deliberately does not do

- It does not run any test (`pytest`) against the untracked code — that is the
  recommended *next* action per row, not something performed here.
- It does not stage, commit, or gitignore anything itself.
- It does not open any dataset's full content — only headers/schemas/diffs.
- It does not propose reopening any CLOSED_FAIL branch.

---

## Cross-reference

- Raw inventory (pre-decision): `reports/canonical/HERALD_13_ORGANIZATION_BACKLOG.md`
- Data structure: `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
- Code structure: `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
- HPC structure: `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md`
- Phase-level status: `reports/canonical/HERALD_12_FINAL_PHASE_MAP.md`
