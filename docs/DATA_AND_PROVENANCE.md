# Data and provenance

This document covers what data the project uses, where it comes from, what is derived, and
what is intentionally not versioned in git. For the deeper, file-by-file classification this
summarizes, see `reports/canonical/HERALD_09_DATA_ASSET_MAP.md` and
`reports/herald_artifact_registry.json` (the machine-readable manifest — check an artefact's
status there before trusting it).

## 1. French sources

| Indicator | Publisher | Frequency | Period | Territories | Evidence type |
|---|---|---|---|---|---|
| Private-sector employment | Urssaf | Annual | 1998–2024 | 280 | Observed |
| Private-sector payroll | Urssaf | Annual | 1998–2024 | 280 | Observed |
| Employing establishments | Urssaf | Annual | 1998–2024 | 280 | Observed |
| Local unemployment rate | Insee | Annual | 2003–2025 | 280 | Observed |
| Local unemployment rate, adjusted | Insee | Quarterly | 2003–2026 | 280 | Observed |
| Private-sector employment, adjusted | Urssaf | Quarterly | 1998–2026 | 280 | Observed |
| New establishments | Sirene / SIDE | Annual | 2012–2025 | 280 | Observed |
| Establishments | Flores | Annual | 2017–2024 | 280 | Observed (99.3% coverage) |
| Active-establishment stock | SIDE | Annual | 2014–2024 | 280 | Observed |

Territorial unit: **ZE2020 employment zone** (INSEE definition), mainland France, Corsica
excluded in this phase. A territory-period cell is counted once even when a source publishes
several sector rows; a missing observation is never silently replaced by zero — it is carried
as an explicit availability flag (see `PROJECT_OVERVIEW.md`, "causal temporal representation").

Full table with cell counts and sector-entry counts: `reports/final_visual_evidence/tables/T01_sources_and_periods.{csv,md}`.

## 2. Transformations

- All features are computed causally: only information published on or before the decision
  date is used (see `reports/HERALD_DATA_AVAILABILITY_CALENDAR.md` /
  `reports/herald_feature_availability_calendar_v1.csv` for the publication-lag calendar
  behind this rule).
- The temporal representation (level, growth, acceleration, trend, momentum, volatility,
  regime, national/relative components, availability flag) is built by
  `src/data/france_ze2020/build_fr_ze2020_temporal_relation_signals.py` and consumed by
  `src/data/france_ze2020/build_fr_ze2020_sector_ranking_panel.py`.
- Candidate relations are built by dedicated scripts, kept separate from the temporal panel:
  commuting (`src/data/france_ze2020/build_fr_ze2020_commuting_edges.py`,
  `build_fr_ze2020_commuting_strict_ex_ante_edges.py`), similarity/complementarity and the
  dynamic-graph edge bundle (`src/data/france_ze2020/build_fr_ze2020_dynamic_graph_inputs.py`,
  `build_fr_ze2020_dynamic_edge_variants.py`).
- The canonical model-ready panel is `data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv`,
  built by `src/data/france_ze2020/build_fr_ze2020_model_ready_panel.py` — this is the file the
  minimal reproducible example reads (see `REPRODUCIBILITY.md`).

## 3. Synthetic known-truth data

The synthetic benchmark generates **280 artificial zones calibrated to reproduce French
marginal statistics** (not real French data), with a **known relational graph** built from
three relation families and a controllable relational-scale parameter. Because the true graph
is known by construction, this is the only dataset on which relation *recovery* (not just
forecast accuracy) can be measured. Generator and provenance:
`reports/final_visual_evidence/scripts/fig_synthetic.py`,
`reports/final_visual_evidence/provenance/figures_synthetic.json`, and the specification/result
pair `reports/canonical/HERALD_93_MODEL_EVALUATION_AND_COMPARISON.md` /
`HERALD_96_NEURAL_GRANGER_RESULTS.md` / `HERALD_97_STAGE_CLOSURE_AND_VISUAL_EVIDENCE.md`.
**Synthetic results must never be presented as, or averaged with, French results** — see
`RESULTS_AND_LIMITATIONS.md`.

## 4. Derived / processed files worth knowing about

- `data/processed/france_ze2020/` — the France ZE2020 panel family (model-ready panel, sector
  panel, temporal relation signals, dynamic-graph node/edge tables, exploratory relation
  signals). Several of the dynamic-graph edge tables are large (10-60MB) `.csv`/`.csv.gz` files
  already committed to git; see §6.
- `data/processed/herald_observatory_v0{1,2,3,4,4_granular,5,51}*/` — dashboard export layers.
  Only `manifest.json` is meant to be treated as a stable reference; the large CSV/HTML exports
  in the same folders are regenerable build output.
- `data/external/*/raw/` — raw ingestion caches, gitignored, regenerated on demand by the
  matching `src/data/ingest_*`/`build_*` script. Never edited by hand.
- `data/interim/` — intermediate tables (URSSAF communal creations, policy/ZRR/ZAN tables,
  population history) feeding the France ZE2020 build. Several files here are large (5-48MB)
  and already committed; see §6.

## 5. What is intentionally not versioned

Per `.gitignore`: archive/binary formats (`*.zip`, `*.xlsx`, `*.pdf`, …), Python/Node caches,
model checkpoints (`*.pt`, `*.ckpt`, `*.pth`), `data/raw/*` except
`data/raw/employment/` (the one raw file small and stable enough to keep), and various ephemeral
scan/log outputs. Raw source downloads otherwise live only on the machine that fetched them or
on the cluster; the repository keeps the ingestion script and the derived panel, not the raw
download, as the reproducible unit.

## 6. Large files already committed — flagged, not removed

A handful of already-git-tracked files are large derived data or dashboards, most notably:

- `data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges*.csv(.gz)` (10–61MB each)
- `data/interim/policy/policy_commune_status_v0.csv` (~48MB), `data/interim/tables/side_communal_creations_official_2012_2024_v0.csv` (~24MB)
- `reports/dashboards/*.html` (10–20MB, data embedded inline for a single-file static dashboard)
- `hpc_results/final_model_comparison_20260429/.../*.html` (~40MB, inside an already-archived historical job — see `EXPERIMENT_PROVENANCE.md`)

These were **not removed** in this cleanup pass: they are already in git history (removing them
from the current tree would not shrink a clone without a history rewrite, which was out of
scope and not authorized), and several are read directly by active builders. They are flagged
here as a candidate for Git LFS or external storage in a future pass — see
`EXPERIMENT_PROVENANCE.md`, "open items."

## 7. Legacy per-country source catalogs

`metadata/HERALD_DATASETS_MAIN.md` (sources actively maintained),
`metadata/HERALD_DATASETS_EXPLORATORY.md` (sources explored, not retained), and
`metadata/HERALD_DATA_UPDATE_POLICY.md` (update/API policy) predate the France ZE2020 focus and
are kept for the European harmonization work (PT/IT/AT/NL/BE panels, `src/data/european_panel/`)
that the France-specific tables above do not cover.
