# Reproducibility

## Environment

Python 3.12 (tested on 3.12.3). No conda/system dependency is required. Three tiers, from
smallest to most exactly pinned:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt                    # data prep + baselines only
pip install -r requirements-neural.txt              # + the neural model, torch pinned to ~=2.13.0
# or, to match the exact environment this branch's smoke/guard suite was validated in:
pip install -r environment-neural-validated.txt     # every package pinned exactly
```

- **`requirements.txt`** — enough for `scripts/run_minimal_example.sh` (data preparation and
  the persistence/Ridge baselines). No neural dependency.
- **`requirements-neural.txt`** — superset, adds `torch` for
  `scripts/run_model_smoke.sh`/`scripts/run_temporal_relational_model.py`. `torch` is capped at
  `~=2.13.0`, the line this branch's own smoke and guard suite were actually validated against
  — loosely pinned like the rest of this file would let `pip install` silently pull a future,
  never-validated release, which is exactly what this cap exists to prevent.
- **`environment-neural-validated.txt`** — a full `pip freeze` snapshot of the environment this
  branch's neural tests actually ran in (67 packages, exact versions). Use this when you need
  the closest possible match to "what was tested here," not just "what should work."

`geopandas`/`shapely`/`fiona`/`pyogrio` are needed for territorial-geometry code (PT
municipality shapes, ZE2020 boundaries) and for full test collection; they pull in GDAL and
can be the slowest part of the install.

**Cluster environment** (what the reported headline numbers in `RESULTS_AND_LIMITATIONS.md`
actually ran under) — read directly from a committed task artifact
(`results/selected/main_benchmark/tasks/*.json`'s own `"environment"` field, not assumed):
Python 3.10.20, numpy 2.2.6, torch 2.6.0+cu124 (a CUDA build; the cluster used a GPU node, this
repository's own validation does not). This is documented as a **reference**, not installed by
any `requirements*.txt` here — see "Numeric tolerances" below for what that gap does and does
not affect.

Verified in a fresh venv during this pass: `pip install -r requirements.txt -r
requirements-neural.txt` gives a clean `pytest tests/ --collect-only` (**2848 tests collected, 0
errors**) and a fully passing, deterministic (5/5 repeated runs identical)
`scripts/run_model_smoke.sh`.

## Numeric tolerances

Two different claims, two different tolerances:

- **`tests/test_selected_benchmark_provenance.py`** re-derives reported numbers from committed
  artefacts (JSON reads and medians over already-computed per-task values) — it never retrains
  a model, so it is **not** affected by the local-vs-cluster environment gap above. Tolerances
  there are tight (`1e-6` for exact re-aggregation of a value already in the artefact, `1e-3` to
  `2e-2` for cross-artefact comparisons against a number written in prose in
  `RESULTS_AND_LIMITATIONS.md`, e.g. "0.0194" or "11% to 24%").
- **`tests/test_herald93_guards.py`**, **`tests/run_herald93_mutations.py`**, and
  `scripts/run_model_smoke.sh` train a real (small) model fresh, in whatever local environment
  runs them. Their assertions are about **qualitative** properties (a gradient is exactly zero
  vs. clearly nonzero; a value is finite; two runs with the same seed are bit-identical; a
  candidate set behaves as documented) — not about matching a specific decimal reported
  elsewhere. **Bit-for-bit numeric equality between the local and cluster environments is not
  promised anywhere in this repository**, and no test asserts it.

## Minimal reproducible example

The FR ZE2020 baseline is the smallest end-to-end path that runs entirely from data already
committed to the repository (no download, no HPC):

```bash
./scripts/run_minimal_example.sh
# equivalent to: python3 -m pytest tests/test_fr_ze2020_baselines.py -q
# 12 passed
```

It trains and evaluates the persistence and Ridge(lag-only) baselines on
`data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv` via
`src/modeles/france_ze2020/train_fr_ze2020_baselines.py`. This is intentionally the *baseline*,
not the full relational model — the relational/dynamic-graph training scripts
(`src/modeles/france_ze2020/train_fr_ze2020_dynamic_graph_ranker.py` and neighbours) need the
larger dynamic-graph edge tables (already committed, 10-60MB each — see
`DATA_AND_PROVENANCE.md` §6) and are slower; run them directly if you need the full model, not
just the baseline.

To run the script directly instead of through its test:

```bash
python3 src/modeles/france_ze2020/train_fr_ze2020_baselines.py --help
```

## Fast test suites

```bash
# Observatory suites (~30-40s for the heaviest one)
python3 -m pytest tests/test_observatory_v04_granular_evidence_policy.py -q
python3 -m pytest tests/test_observatory_v05_narrative_dashboard.py -q
python3 -m pytest tests/test_observatory_v051_narrative_dashboard.py -q   # ~38s, 103 tests

# DEC-060 -> DEC-066 decision suites (verified in this cleanup: 356 passed, 10 skipped, ~3s)
python3 -m pytest tests/test_dec060_france_relation_audit.py tests/test_dec061_municipal_granularity.py \
  tests/test_dec062_granular_preflight.py tests/test_dec064_pt_municipal_phase7.py \
  tests/test_dec065_nl_gemeente_proxy_phase7.py tests/test_dec066_threshold_calibration.py -q

# Artifact registry (verified in this cleanup: 13 passed)
python3 -m pytest tests/test_herald_artifact_registry.py -q
```

## Full test collection

There is no single recommended root `pytest tests/` run for the *full* suite — some tests are
HPC-scale (minutes) and the root also collects the synthetic/real-world research track, which
needs `torch`. To sanity-check that nothing is broken without running everything:

```bash
python3 -m pytest tests/ --collect-only -q
```

This only imports every test module; it does not execute them. Verified during this cleanup:
2848 tests collected, 0 errors (with `torch` and the `geopandas` stack installed).

## Reproducing the frozen headline results

The numbers in `RESULTS_AND_LIMITATIONS.md` come from HPC job artefacts. For the main
280-territory benchmark, the minimal necessary subset is versioned in this repository at
`results/selected/main_benchmark/` (see its own README and `manifest.json` for exactly what was
selected and why); `hpc_results/herald94/`, `herald95/`, `herald96/` are committed in full. They
are **not** recomputed by a local script — they are read and re-derived from the committed
artefacts by:

```bash
python3 -m pytest tests/test_selected_benchmark_provenance.py -v
```

which fails if any documented number no longer matches its artefact (best forecast skill, edge
recovery at prevalence, the no-relation-control disqualification, the 11-24% temporal gain, both
protocols' oracle values, and the all-pairs-at-prevalence result). A second, independent
read-only path over the same kind of evidence for the report's own figures:

```bash
python3 reports/final_visual_evidence/scripts/audit_stage.py
```

(this is a read-only audit script over `reports/final_visual_evidence/provenance/stage_audit.json`
and the `hpc_results/` artefacts; it does not write into `reports/final_visual_evidence/` unless
you also run `make_all.py`, which is protected — see the note below).

**Do not run `reports/final_visual_evidence/scripts/make_all.py` or anything under
`reports/results_evidence_selection/scripts/` as part of routine reproduction.** Both
directories are the frozen source of the figures/tables actually used by the report and
presentation (`Pesquisa_stage/report_present/`); regenerating them is a report-editing action,
not a repository-reproducibility one, and is out of scope for this document.

## Seeds

Rolling-origin evaluation and the synthetic benchmark use independent runs across 5 seeds in the
main benchmark and 5 further seeds in the residual diagnostic (`RESULTS_AND_LIMITATIONS.md` §0);
seeds are fixed and recorded in the corresponding job's artefact JSON under `hpc_results/`, not
derived from wall-clock time or randomness at run time.

## HPC vs. local

- **Local / this repository**: baselines, the fast test suites above, and any script
  `reports/canonical/HERALD_10_CODE_PATH_MAP.md` classifies as active without an `hpc/`
  counterpart (see `EXPERIMENT_PROVENANCE.md` §8 for which documents were kept and why).
- **HPC (SLURM, Mésocentre)**: the dynamic-graph training, relation-objective, and known-truth
  synthetic benchmark runs (`hpc_results/herald93/` through `herald98/`). Submission scripts
  live under `hpc/<phase>/`; **none of them were (re)launched by this cleanup** — the committed
  `hpc_results/` artefacts are the frozen output of runs already completed. See
  `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md` for which job produced which result.

## What was NOT run in this cleanup, and why

- `reports/final_visual_evidence/scripts/make_all.py`, `tests/test_visual_evidence.py` — would
  write into the protected `reports/final_visual_evidence/` tree; not run to avoid touching
  protected files even transiently, even though the script is documented as idempotent.
- `tests/run_guards_no_pytest.py` — fails at HEAD (`f730e72`) with
  `ModuleNotFoundError: No module named 'src.modeles.france_ze2020.herald76_dynamic_graph'`.
  This is a **pre-existing condition**, not a regression from this cleanup: the primary
  worktree shows this file as actively being edited (uncommitted), and the missing module is
  presumably part of that in-progress work. Confirm with whoever is editing it before relying
  on this guard.
- The full, unfiltered `pytest tests/` (executing, not just collecting, all 2826 tests) — not
  run end-to-end; several suites are HPC-scale. Collection-only was used instead to confirm
  nothing is structurally broken (§ "Full test collection" above).

## Validation record (this delivery)

**Branch:** `delivery/repository-cleanup`. **Base commit:** `f730e72` on `main` (see
`EXPERIMENT_PROVENANCE.md` §5 for what that base does and does not include — this is a proposed
delivery structure, not necessarily the final scientific snapshot). **Date:** 2026-08-25.
**Environment:** fresh venv, `pip install -r requirements.txt -r requirements-neural.txt` (local,
CPU; Python 3.12.3 / torch 2.13.0 — see `requirements-neural.txt` / `environment-neural-validated.txt`
for how this compares to the cluster's own recorded environment).

Four statuses are used, and none is presented as another: `PASS`, `FAIL`,
`EXPECTED_SCIENTIFIC_FAIL` (the condition reproduces an already-documented, pre-existing
scientific limitation — never used for a technical defect), `NOT RUN` (never counted as a pass).

**Code and tests**

| # | Check | Status | Detail |
|---|---|---|---|
| 1 | `pytest tests/ --collect-only` (full test collection) | PASS | 2848 tests collected, 0 errors |
| 2 | `./scripts/run_minimal_example.sh` | PASS | 12/12, ~1s |
| 3 | `./scripts/run_model_smoke.sh` (neural model smoke, full) | PASS (script exit 0) | ~2m45s total, no SLURM, no download; the script's own exit code depends only on the technical rows below |
| 4 | Smoke repeated twice, same seed | PASS | Forecast, connection scores, and gradients bit-identical (`scripts/run_model_smoke.sh` step 4, and `test_determinism_same_seed_same_config`) |
| 5 | Technical execution guards (`tests/test_herald93_guards.py`) | PASS — `TECHNICAL_EXECUTION: 22/22` | Leakage, masks/absence, graph mechanics, fairness between arms; stable across 5 repeated fresh-process runs after the thread-pinning fix this pass added |
| 6 | Scientific recovery gate (`test_h23`, same file) | `EXPECTED_SCIENTIFIC_FAIL` in this environment — **environment-sensitive, see note below** | Scorer-vs-consuming-head gradient ratio falls under threshold after extended training — reproduces, at smoke scale, the full-scale disqualification already reported in `RESULTS_AND_LIMITATIONS.md` Sec.3. Reported as `SCIENTIFIC_RECOVERY_GATE`, separate from and never gating `TECHNICAL_EXECUTION`. Stable within this environment (FAIL in 5/5 repeated runs after the same fix), but not stable across environments — see below |
| 7 | Mutation testing (`tests/run_herald93_mutations.py`) | PASS | 22/22 targeted mutants killed — every technical guard proven to actually catch the defect it names |
| 8 | Temporal-encoder gradient tests | PASS | `test_h14` (every per-signal encoder branch), `test_h15` (fusion never zeroes a signal), `test_gradients_are_nonzero_in_every_component` |
| 9 | Relational-learner gradient/mechanics tests | PASS | `test_h9` (no self-loops), `test_h12` (no node-only path), `test_h13` (top-k does not block gradient), `test_h17`/`test_h18` (herald/NRI/MTGNN share one candidate set) |
| 10 | Temporal-causality (no-leakage) tests | PASS | `test_h1` (no future period reaches a view), `test_h2` (release dates gate inputs), `test_h5` (view is reconstructible from published signals alone) |
| 11 | No-mechanism (`S0_NULL`) control | PASS | `test_no_mechanism_scenario_does_not_explode` and the smoke script's own `no-mechanism` run: finite MAE, finite skill, finite gradients |
| 12 | Anti-substitution guards on the entrypoint | PASS | `tests/test_model_smoke_entrypoint.py`, 12/12 — confirms the run used the real dynamic-graph model (not persistence/sparse_var/mtgnn/nri), confirms `--help` never leaks the legacy name, confirms the technical/scientific classification cannot silently change, confirms two different seeds give different connection scores |
| 13 | Benchmark provenance reconstruction | PASS | `tests/test_selected_benchmark_provenance.py`, 10/10 — rederives best forecast skill, edge recovery at prevalence, the no-relation-control disqualification, the 11-24% temporal gain, both protocols' oracle values, and the all-pairs-at-prevalence result from committed artefacts; fails if artefact and documentation diverge |
| 14 | `tests/test_herald_artifact_registry.py` | PASS | 13/13 |
| 15 | Import verification | PASS | `pytest --collect-only` imports every test module including all new files this pass added; every `importlib` load in the entrypoint and its guards succeeds (rows 1-13) |
| 16 | `tests/run_guards_no_pytest.py` | NOT RUN | Fails at the branch's base commit with a pre-existing missing-module error, unrelated to this cleanup |
| 17 | Full non-collection execution of all 2848 tests | NOT RUN | Several suites are HPC-scale; collection-only used instead (row 1) |
| 18 | HPC re-submission / cluster-dependent reproduction | NOT RUN | No cluster access from this environment |

### Scientific recovery gate — environment sensitivity

`SCIENTIFIC_RECOVERY_GATE` (`test_h23`) is a small, deliberately sensitive diagnostic that
retrains the model for extra epochs at smoke scale and checks whether the relational scorer
keeps receiving usable gradient relative to the head consuming it. Its outcome has been observed
to depend on the PyTorch build:

- **FAIL** in the validated local environment this repository documents (Python 3.12.3,
  torch 2.13.0 — see `environment-neural-validated.txt`), stable across 5 repeated runs. Row 6
  above reports this run.
- **PASS** under an independently reproduced run on PyTorch 2.9.1, with `TECHNICAL_EXECUTION`
  still 22/22 and mutation testing still fully killed in that same run.

Neither observation changes the scientific conclusion in `docs/RESULTS_AND_LIMITATIONS.md` Sec.3,
which is derived from the frozen full-scale benchmark artifacts under
`results/selected/main_benchmark/`, not from this smoke-scale diagnostic. This gate is exactly
what it is documented to be: a small, environment-sensitive scientific probe, run at a scale and
epoch count chosen for a CPU smoke test rather than for statistical power. Do not treat a PASS
here as evidence the full-scale disqualification was wrong, and do not treat a FAIL here as
independent proof of it — read `docs/RESULTS_AND_LIMITATIONS.md` Sec.3 for the actual evidence.
`TECHNICAL_EXECUTION` passing is the only hard requirement for the smoke script to exit 0;
`SCIENTIFIC_RECOVERY_GATE` is reported, in either direction, never gated on, and never silently
dropped (row 12, `tests/test_model_smoke_entrypoint.py`, asserts the classification itself cannot
change). Thresholds, seeds, and the model were not altered to produce either outcome.

**Documentation**

| # | Check | Status | Detail |
|---|---|---|---|
| 19 | Markdown links in `README.md` + `docs/*.md` resolve | PASS | Checked every `](...)` link against the filesystem |
| 20 | Legacy model name on the public surface | PASS | Zero occurrences in `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/RESULTS_AND_LIMITATIONS.md`, and in the entrypoint's own `--help` (test row 12). Remaining occurrences in `docs/DATA_AND_PROVENANCE.md`/`docs/REPRODUCIBILITY.md` are real, still-existing technical paths only |
| 21 | Five signal frequencies vs. the protected report's own construction table | PASS | Verified line-by-line against `Report_project.tex` |
| 22 | 280-territory vs. 80-territory protocol separation | PASS | `RESULTS_AND_LIMITATIONS.md` §0 table; every subsequent section states which protocol a number belongs to; `all_pairs` scoped explicitly to the 80-territory diagnostic only (§4 header) |
| 23 | Results and limitations coherent with what was actually run | PASS | Cross-checked against test rows 5-13 and the reconstruction test (row 13) |
| 24 | Commands documented actually work as documented | PASS | Every command block in `README.md`/`docs/REPRODUCIBILITY.md` was run verbatim this session |
| 25 | Environment documentation matches what was installed | PASS | `environment-neural-validated.txt` is a direct `pip freeze` of the venv these tests ran in, not a separate claim |
| 26 | Manifests match files on disk | PASS | `test_manifest_matches_the_selected_files_on_disk` (part of row 13) |
| 27 | Files cited in docs actually exist | PASS | Covered by row 19 plus a manual pass over non-markdown-link path citations |

**Security**

| # | Check | Status | Detail |
|---|---|---|---|
| 28 | Secrets/tokens (AWS keys, private-key headers, Slack/GitHub tokens, hardcoded passwords) | PASS | None found in `README.md`/`docs/*.md`/`results/selected/main_benchmark/*.md`/`requirements*.txt`/`environment-neural-validated.txt` |
| 29 | Personal filesystem paths in public docs | PASS | None found |
| 30 | Large data added this pass | PASS (none added) | `results/selected/main_benchmark/` is 300KB; the two synced visual-evidence files are under 1MB combined; nothing else was added |
| 31 | Temporary files / caches committed | PASS | None staged; `.venv/`, `__pycache__/`, `.pytest_cache/` remain gitignored |
| 32 | File permissions | PASS | No mode changes beyond the two `chmod +x` on `scripts/*.sh`/`.py`, both intentional and necessary |

**Scientific coherence (adversarial falsification attempts)**

| # | Claim tested | Status | Evidence |
|---|---|---|---|
| 33 | The smoke executes the real model, not a substitute | PASS | Row 12: `capabilities.graph_kind == "dynamic"`, unique to the proposed model |
| 34 | The temporal encoder receives gradient | PASS | Row 8 |
| 35 | The relational learner receives gradient | PASS | Row 9 |
| 36 | Forecast and connection scores are produced, and reported, separately | PASS | `output["prediction"]` and `output["edge_weight"]` are distinct fields; `test_h19` asserts a perfect forecast cannot satisfy the recovery gate |
| 37 | Documented results can be rederived from committed artefacts | PASS | Row 13 |
| 38 | The no-mechanism scenario remains a real control | PASS | Row 11; `test_h10` additionally confirms a frozen/static score gets no credit on the typed-event metric |
| 39 | No French score is presented as a validated relation | PASS | Row 20-class scan plus manual re-read of `docs/RESULTS_AND_LIMITATIONS.md` §8 and `PROJECT_OVERVIEW.md` |
| 40 | `all_pairs` belongs only to the 80-territory protocol | PASS | `docs/PROJECT_OVERVIEW.md` candidate-relations table and `RESULTS_AND_LIMITATIONS.md` §4 both scope it explicitly; `T04_models_compared.md` (280-territory) does not include it |
| 41 | The scientific failure (row 6) was not hidden as a technical success | PASS | Reported under a distinct `SCIENTIFIC_RECOVERY_GATE` label, in the smoke script's own stdout, gated by a dedicated test (row 12) that fails if the classification silently reverts |

**Limitations of this validation:** it covers the documents and code paths this cleanup touched,
the neural smoke/guard surface, and the fast/collection-level test surface; it does not re-run
the HPC jobs behind the reported headline numbers (those are read from committed artefacts, per
"Reproducing the frozen headline results" above), it does not exactly match the cluster's pinned
dependency versions, and it does not constitute a fresh peer review of the underlying science.
