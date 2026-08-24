# Reproducibility

## Environment

Python 3.12 (tested on 3.12.3). No `environment.yml`/conda file exists; use a virtual
environment and `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`torch` is commented out in `requirements.txt` — it is only needed for the
`src/modeles/synthetic/` and `src/modeles/real_world/` research track (the relation-learning
experiments behind the known-truth synthetic benchmark, `hpc_results/herald93/` through
`herald98/`), not for the minimal example or the fast test suites below. Install it separately
(`pip install torch`) if you need that track.

`geopandas`/`shapely`/`fiona`/`pyogrio` are needed for territorial-geometry code (PT
municipality shapes, ZE2020 boundaries) and for full test collection; they pull in GDAL and
can be the slowest part of the install.

This was verified in a fresh venv during this cleanup: `pip install -r requirements.txt` plus
`torch` gives a clean `pytest tests/ --collect-only` (**2826 tests collected, 0 errors**).

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
2826 tests collected, 0 errors (with `torch` and the `geopandas` stack installed).

## Reproducing the frozen headline results

The numbers in `RESULTS_AND_LIMITATIONS.md` come from HPC job artefacts already committed
under `hpc_results/herald93/`, `herald94/`, `herald95/`, `herald96/`, plus the France ZE2020
job families under `hpc_results/` and `data/processed/france_ze2020/`. They are **not**
recomputed by a local script — they are read and re-derived from the committed artefacts by:

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

- **Local / this repository**: baselines, the fast test suites above, and any script this
  branch's kept code-path traceability map classifies as active without an `hpc/` counterpart
  (`reports/canonical/`, the code path map document — see `EXPERIMENT_PROVENANCE.md` §7 for
  which documents were kept and why).
- **HPC (SLURM, Mésocentre)**: the dynamic-graph training, relation-objective, and known-truth
  synthetic benchmark runs (`hpc_results/herald93/` through `herald98/`). Submission scripts
  live under `hpc/<phase>/`; **none of them were (re)launched by this cleanup** — the committed
  `hpc_results/` artefacts are the frozen output of runs already completed. See
  `reports/canonical/` (kept HPC/results map, `EXPERIMENT_PROVENANCE.md` §7) for which job
  produced which result.

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
`EXPERIMENT_PROVENANCE.md` §4 for what that base does and does not include). **Date:**
2026-08-25. **Environment:** fresh venv, `pip install -r requirements.txt` plus `torch`
(§ "Environment" above).

| # | Check | Status | Detail |
|---|---|---|---|
| 1 | Markdown links in `README.md` + `docs/*.md` resolve | PASS | Checked every `](...)` link against the filesystem |
| 2 | Personal filesystem paths in public docs | PASS | None found |
| 3 | Secrets/tokens (AWS keys, private-key headers, Slack/GitHub tokens, hardcoded passwords) | PASS | None found in `README.md`/`docs/*.md` |
| 4 | Legacy model name in `README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/RESULTS_AND_LIMITATIONS.md` | PASS | Zero occurrences |
| 5 | Legacy model name in `docs/DATA_AND_PROVENANCE.md`, `docs/REPRODUCIBILITY.md` | PASS | Occurrences are limited to real, still-existing technical paths (e.g. `hpc_results/herald93/`), none presenting it as a current name |
| 6 | "frugal"/"frugality" in public docs | PASS | Zero occurrences |
| 7 | Five signal frequencies vs. the protected report's `tab:five-signal-construction` | PASS | Verified line-by-line against `Report_project.tex`; corrected employment, payroll, and unemployment from an earlier incorrect "Annual" to "Quarterly" |
| 8 | 280-territory vs. 80-territory protocol separation | PASS | `RESULTS_AND_LIMITATIONS.md` §0 table added; every subsequent section states which protocol a number belongs to |
| 9 | `./scripts/run_minimal_example.sh` | PASS | 12/12 |
| 10 | `pytest tests/ --collect-only` (2826 tests) | PASS | 0 errors |
| 11 | Fast local suites (DEC-060→066, artifact registry) | PASS | 356 passed / 10 skipped, and 13 passed |
| 12 | Broken references after archiving 55 `reports/canonical/` documents | PASS | Zero test/code/registry-test dependency on the archived files (verified before archiving, re-verified by check #10 after) |
| 13 | Checksums of the 4 protected directories, before vs. after this pass | 3× PASS, 1 informational | `reports/final_visual_evidence/`, `reports/results_evidence_selection/`, and `Pesquisa_stage/report_present/presentation/` are byte-identical. `Pesquisa_stage/report_present/report/` changed again during this session — **not from this branch** (no `Write`/`Edit`/write-capable `Bash` call ever targeted it); it reflects someone else's concurrent editing of the report, reported here rather than silently absorbed |
| 14 | `tests/run_guards_no_pytest.py` | NOT RUN | Fails at the branch's base commit with a pre-existing missing-module error, unrelated to this cleanup (§ "What was NOT run" above) |
| 15 | Full non-collection execution of all 2826 tests | NOT RUN | Several suites are HPC-scale; collection-only used instead (check #10) |
| 16 | HPC re-submission / cluster-dependent reproduction | NOT RUN | No cluster access from this environment |

**Limitations of this validation:** it covers the documents and code paths this cleanup touched
plus the fast/collection-level test surface; it does not re-run the HPC jobs behind the reported
numbers (those are read from committed artefacts, per "Reproducing the frozen headline results"
above), and it does not constitute a fresh peer review of the underlying science.
