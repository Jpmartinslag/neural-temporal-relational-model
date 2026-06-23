# HERALD 15 — France ZE2020 Data Treatment Pipeline

**Scope of this document:** the France / ZE2020 **data layer only** — raw
ingestion, territorial/temporal normalization, the 280-zone methodological
scope, and the clean treated panel. It does **not** cover training, model
evaluation, the dashboard, or `hpc_results/` — those are untouched by this
pass and are out of scope here. See `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
and `HERALD_10_CODE_PATH_MAP.md` for the full-project equivalents.

**Created:** 2026-06-23, as part of a data-cleanup pass distinct from the
methodological-closure audit captured in the project's other reports. This
document and the panel it describes are new; no pre-existing file,
training script, or dashboard was modified to produce them.

---

## 1. Current state — file inventory

Status vocabulary used in this table only (distinct from, and narrower than,
`reports/herald_artifact_registry.json`'s vocabulary):
`RAW_CANONICAL`, `INTERIM_CANONICAL`, `PROCESSED_CANONICAL`,
`MODEL_INPUT_FUTURE`, `LEGACY_DO_NOT_USE`, `LOCAL_ONLY`,
`UNKNOWN_REVIEW_REQUIRED`.

| File | Role | Generator | Consumer(s) | Status | Note |
|---|---|---|---|---|---|
| `data/interim/mappings/commune_to_ze2020_2026.csv` | Official commune (CODGEO) → ZE2020 mapping, 34,875 communes, 306 zones | not traced in this pass (likely INSEE nomenclature import) | `build_dynamic_stgnn_feature_panel_v1.py`, this pass's new builder (indirectly, via the interim table below) | RAW_CANONICAL | 306 is the raw/full nomenclature count, before any methodological filter |
| `data/interim/tables/side_communal_creations_official_2012_2024_v0.csv` | Commune × year INSEE SIDE creation counts (enterprise + establishment), already joined to ZE2020/region | **no generator script found in the current tree** | `src/data/france_ze2020/build_fr_ze2020_clean_panel.py` (new, this pass) | INTERIM_CANONICAL | UNKNOWN_REVIEW_REQUIRED for provenance only — content independently verified consistent (see section 4) |
| `data/raw/business_demography/side/*.zip` (DS_SIDE_*, TAB_SIDE_*) | Raw INSEE SIDE establishment/enterprise stock & creation extracts | INSEE downloads | `build_dynamic_stgnn_feature_panel_v1.py` (subset: `DS_SIDE_STOCKS_ET_COM_2023_CSV.zip`) | RAW_CANONICAL | Most files in this directory are not read by any builder found in this pass — flagged, not removed |
| `data/raw/employment/flores/*.zip` (TD_FLORES_*, DS_FLORES_*) | Raw INSEE FLORES establishment/salaried-jobs extracts, commune (TD, 2016-2021) and ZE2020 (DS, 2022-2023) format | INSEE downloads | `build_dynamic_stgnn_feature_panel_v1.py` pipeline A | RAW_CANONICAL | |
| `data/raw/employment/urssaf/urssaf_etab_emploi_ze_annual_raw.csv` | Raw URSSAF employer/employment/payroll by ZE × year | URSSAF download | `build_dynamic_stgnn_feature_panel_v1.py` pipeline A2 | RAW_CANONICAL | |
| `data/processed/target_side_establishments_annual_core_v0.csv` | Official SIDE establishment-creation target, ZE2020 × year, 280 zones, 2012-2024 | **no `.py` committed alongside it** (commit `bbd2d49`, data-only) | `build_dynamic_stgnn_feature_panel_v1.py` pipeline C; cross-checked by the new builder | UNKNOWN_REVIEW_REQUIRED (generator) / PROCESSED_CANONICAL (content, verified) | Values match this pass's independent re-derivation exactly (diff 0.0) |
| `data/processed/target_side_establishments_annual_core_through_2025_v1.csv` | Same as above, extended to 2025 | `src/modeles/integrate_side_2025_for_herald_v6.py` | `build_dynamic_stgnn_feature_panel_v1.py`-adjacent (V6 track) | PROCESSED_CANONICAL | 2025 raw commune-level source not located in this pass; not reconciled against the new builder |
| `data/processed/flores_panel_ze2020_annual_v1.csv` | FLORES features, t-1 lag, ZE2020 × year | `build_dynamic_stgnn_feature_panel_v1.py` pipeline A | pipeline C (same script) | LEGACY_DO_NOT_USE (naming only — content itself is causal/t-1, no defect found) | |
| `data/processed/side_stocks_lagged_ze2020_annual_v1.csv` | SIDE stock features, t-1 lag, ZE2020 × year | `build_dynamic_stgnn_feature_panel_v1.py` pipeline B | pipeline C (same script) | LEGACY_DO_NOT_USE (naming only) | |
| `data/processed/side_creations_a10_ze2020_v1.csv` | A10 sector-level SIDE creations, ZE2020 × year | not traced in this pass | `france_adapter.py` | UNKNOWN_REVIEW_REQUIRED | Sector-level panel — out of scope for this pass (see section 9) |
| `data/processed/dynamic_stgnn_feature_panel_v1.csv` | Legacy unified FR feature panel, 280 ZE2020 × 2012-2024 | `build_dynamic_stgnn_feature_panel_v1.py` pipeline C | `train_herald_v3..v7.py`, `scripts/02_ridge_ar_official.py`, `france_adapter.py`, several `src/analyse/*` scripts | **LEGACY_DO_NOT_USE as a source for new data work** (still actively consumed by training — see section 5) | Contains the confirmed `growth_1y`/`growth_2y` target leak — section 5 |
| `metadata/dynamic_stgnn_walk_forward_splits_v1.csv` | Walk-forward fold boundaries (2021-2024) | `build_dynamic_stgnn_feature_panel_v1.py` pipeline D | training scripts | LEGACY_DO_NOT_USE (naming only) | Content itself (year boundaries) is not leaky |
| `src/data/european_panel/adapters/france_adapter.py` | Converts the legacy FR panel to the European canonical schema | — | `build_european_panel.py` | LOCAL_ONLY to the European-panel track (out of scope) | Reads `growth_1y`/`growth_2y` AS-IS from the legacy panel, but they are unconditionally overwritten downstream (next row) |
| `src/data/european_panel/build_european_panel.py` (`enforce_causal_growth`) | Recomputes `growth_1y`/`growth_2y` from `lag1..3_births` only | — | writes `data/processed/european_panel/france_panel.csv` | LOCAL_ONLY (out of scope) | Confirmed causally safe for the FR European-panel output — see section 5 |
| **`data/processed/france_ze2020/fr_ze2020_clean_panel.csv`** | **New canonical FR ZE2020 treated panel** | **`src/data/france_ze2020/build_fr_ze2020_clean_panel.py`** (new) | none yet (first stage; future model-input builder will consume it) | **PROCESSED_CANONICAL — current entry point** | This pass's deliverable |

Out of scope, listed only for completeness, **not touched**: `src/modeles/train_herald_*.py`, `src/modeles/train_temporal_baselines_v1.py`, `src/modeles/train_dynamic_stgnn_models_v1.py`, `src/modeles/train_herald_semi_v1.py`, `src/analyse/evaluate_dynamic_feature_panel_baselines_v1.py`, `src/analyse/analyze_herald_v3_statistical_evidence.py`, `scripts/02_ridge_ar_official.py`, `src/analyse/archive_legacy_for_herald_focus.py`, `src/modeles/integrate_side_2025_for_herald_v6.py`, the dashboard, `hpc_results/`, Italy/Austria adapters.

---

## 2. Naming

The new pipeline uses neutral, content-describing names, per the project's
own naming-conventions policy (`reports/HERALD_NAMING_CONVENTIONS.md` section
0 — `STGNN`/`MAS` must not be used as current identity):

| Concept | Name used | Avoided |
|---|---|---|
| Builder script | `src/data/france_ze2020/build_fr_ze2020_clean_panel.py` | `*_stgnn_*`, `*_v6_*` |
| Canonical output | `data/processed/france_ze2020/fr_ze2020_clean_panel.csv` | `dynamic_stgnn_feature_panel*` |
| This document | `HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md` | any "STGNN pipeline" wording |

No existing file was renamed or deleted. Legacy `dynamic_stgnn_*` files stay
exactly where they are, under their existing names, marked
`LEGACY_DO_NOT_USE` (for new work) in section 1 above — they remain real,
in-use inputs to the current Q7 training track, which is unchanged by this
pass.

---

## 3. Canonical panel schema

`data/processed/france_ze2020/fr_ze2020_clean_panel.csv` — 3,640 rows (280
zones × 13 years), 8 columns:

| Column | Type | Meaning |
|---|---|---|
| `ze2020` | string, zero-padded, always 4 characters (e.g. `"0051"`) | INSEE Zone d'Emploi 2020 code. **Must be read with `dtype={"ze2020": str}`** — a naive `pd.read_csv` will infer it as an integer and silently drop the leading zero (see `tests/test_fr_ze2020_clean_panel.py::test_ze2020_zero_stripped_if_read_without_dtype`, which documents this as an expected gotcha, not a bug to fix — CSV cannot store a string-vs-int type hint). |
| `ze2020_label` | string | Human-readable zone name (e.g. `"Bourg-en-Bresse"`). Documented metadata, not used for joins. |
| `year` | integer | Calendar year, 2012-2024. No alternate name (`annee`/`date`/`t`). |
| `establishment_creations` | float | INSEE SIDE official *créations d'établissements*, summed from commune level. This is the value used historically as the model target (`TARGET_COL` in `train_herald_v6.py`). |
| `enterprise_creations` | float | INSEE SIDE official *créations d'entreprises*, summed from commune level. A distinct INSEE concept from establishment creations — kept as a second observed value, not a duplicate. |
| `communes_count` | integer | Number of communes aggregated into this zone for this year. Documented metadata (zone composition can shift slightly year to year due to commune mergers). |
| `mask_establishment_creations_available` | 0/1 | 1 if `establishment_creations` is non-null for this row. |
| `mask_enterprise_creations_available` | 0/1 | 1 if `enterprise_creations` is non-null for this row. |

No `node_id`/`node_idx` numeric index is included — there is no model
consumer yet at this stage (see section 9). One should be added as a
**separate** column only when a model-input builder needs it; the rule from
this pass forward is: never conflate it with `ze2020`.

No sector dimension yet (see section 9).

---

## 4. The 306 → 280 ZE2020 selection — verified mechanism

This is a **deliberate methodological scope filter, not data loss**.

- The raw INSEE commune→ZE2020 nomenclature (`commune_to_ze2020_2026.csv`)
  covers **306** zones across all of France including overseas departments.
- The canonical FR panel — both the pre-existing
  `target_side_establishments_annual_core_v0.csv` and this pass's new
  `fr_ze2020_clean_panel.csv` — covers **280** zones: **continental
  /metropolitan France, excluding Corsica and the overseas departments
  (DOM)**.
- Verified exclusion list (INSEE region codes, 2-digit zero-padded): `94`
  (Corse, 7 zones), `01` (Guadeloupe, 5), `02` (Martinique, 6), `03`
  (Guyane, 3), `04` (La Réunion, 4), `06` (Mayotte, 1) — **26 zones
  excluded, 306 − 26 = 280**, confirmed by direct set comparison between the
  raw mapping and the existing target panel, and reproduced independently by
  `build_fr_ze2020_clean_panel.py`'s `EXCLUDED_REGION_CODES` filter (output
  verified: 280 zones, matches exactly).
- All 26 excluded zones are fully contained in their excluded region (no
  zone straddles an excluded and an included region), so the filter is a
  clean, unambiguous yes/no per zone — not a partial/fuzzy cut.
- **What is not documented elsewhere:** no DEC-* entry or report found in
  this repository states *why* Corsica and the DOM are excluded (it is not
  flagged as a data-quality problem anywhere either). This pass records the
  *mechanism* precisely (region-code exclusion) and reports honestly that
  the *rationale* is not traceable in the current decision log — it is left
  as a methodological choice inherited from the existing 280-zone target
  panel, not invented or assumed by this pass.
- The canonical output explicitly states its zone count: `ze2020.nunique()
  == 280` is asserted by `tests/test_fr_ze2020_clean_panel.py::test_panel_has_280_ze2020_zones`.

---

## 5. Leakage audit — data layer

**Confirmed finding, code-level, in `src/modeles/build_dynamic_stgnn_feature_panel_v1.py`,
`pipeline_c_unified`:**

```python
target["growth_1y"] = target.groupby("ZE2020")["side_establishment_creations_official"].pct_change(1)
target["growth_2y"] = target.groupby("ZE2020")["side_establishment_creations_official"].pct_change(2)
```

`side_establishment_creations_official` **is the target column itself**
(`TARGET_COL` in `train_herald_v6.py`). `pct_change(1)` at row `t` computes
`(target[t] − target[t−1]) / target[t−1]` — i.e. `growth_1y[t]` is a
deterministic function of `target[t]`. Any model reading this column as a
feature can algebraically recover the target from it
(`target[t] = target[t−1] · (1 + growth_1y[t])`). This is a same-row
target-derived feature, not a `t−1` lag feature — independent of how
train/test splits are drawn.

This column is read directly as a Ridge feature in
`scripts/02_ridge_ar_official.py` (`SPAT_COLS = ["side_lag_1", "growth_1y"]`,
commented `# vars to spatially aggregate (forecast-safe)` — that comment is
incorrect for `growth_1y`). This feeds the Q7 headline result
(`HERALD_Q7_FRANCE_RESULT` in `reports/herald_artifact_registry.json`),
which already carries a `PENDING_REAUDIT` status for exactly this kind of
dependency. **This finding sharpens that existing flag with a concrete
mechanism for the French track specifically** — it does not contradict it,
and this pass does not alter the registry's `HERALD_Q7_FRANCE_RESULT` entry,
since amending a training-result claim is out of scope here (training is
explicitly excluded from this pass).

Separately, the **same legacy file's** `feature_forecast_safe` column is
hardcoded to `1` for every row (`pipeline_c_unified`, `target["feature_forecast_safe"] = 1`)
— not a real per-row QC signal.

**The European-panel track is already fixed for this exact bug pattern.**
`src/data/european_panel/build_european_panel.py::enforce_causal_growth()`
unconditionally recomputes `growth_1y`/`growth_2y` from `lag1_births`/
`lag2_births`/`lag3_births` (strictly `t−1` and earlier) for any adapter
output that has those lag columns — confirmed present and triggered for
France, so `data/processed/european_panel/france_panel.csv`'s `growth_1y`/
`growth_2y` are causally safe, even though `france_adapter.py` reads the
leaky raw values from the legacy file before the override is applied. This
matches the documented Phase 4E fix for the **same** bug pattern found in
the old `ingest_*.py` European-track scripts.

**This pass's new canonical panel (`fr_ze2020_clean_panel.csv`) contains no
growth, no lag, and no derived-from-target column of any kind** — it carries
only the two raw observed values and their availability masks. There is
nothing to leak. Growth features, if built in a future modeling stage, must
use only lags:

```
growth_1y_safe = (lag_1 - lag_2) / lag_2
growth_2y_safe = (lag_1 - lag_3) / lag_3
```

— never the current year's own observed value.

---

## 6. Availability masks

At this stage the panel is purely observed/aggregated (no imputation, no
fabricated values). Two masks are included:

| Mask | Meaning |
|---|---|
| `mask_establishment_creations_available` | 1 if `establishment_creations` is non-null for this zone-year |
| `mask_enterprise_creations_available` | 1 if `enterprise_creations` is non-null for this zone-year |

In the current source data both masks are 1 for all 3,640 rows (full
observed coverage 2012-2024 for all 280 zones) — the masks exist so that any
future gap (e.g. a later year with partial INSEE release) is flagged
explicitly rather than silently producing a `NaN` or a fabricated fill value.
No `mask_lag_*_available` masks exist yet because no lag features exist yet
(see section 9).

---

## 7. Tests

`tests/test_fr_ze2020_clean_panel.py` (12 tests, all passing) covers:
schema column set, `ze2020` zero-padded-string invariant (plus the
documented CSV dtype gotcha), `year` integer type, 280-zone count, full
2012-2024 year coverage, no duplicate zone×year rows, no `stgnn`/
`growth_1y`/`growth_2y`/`feature_forecast_safe`/`has_urssaf_source`/
`node_idx` columns, mask columns carry real (non-constant-disguised) 0/1
signal, territorial join against the raw commune mapping without int/string
mixing, and an exact-value regression check against the pre-existing
official target panel (max abs diff `0.0` across 3,640 matched rows).

`tests/test_herald_artifact_registry.py` (13 tests, all passing after this
pass's two new registry entries — `PANEL_FR_ZE2020_CLEAN_TREATED` and
`FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL`, see `reports/herald_artifact_registry.json`).

---

## 8. Plain-language summary

1. **What raw data enters?** Commune-level INSEE SIDE establishment/enterprise
   creation counts, already joined to the official ZE2020 nomenclature
   (`data/interim/tables/side_communal_creations_official_2012_2024_v0.csv`).
2. **What script treats it?** `src/data/france_ze2020/build_fr_ze2020_clean_panel.py`.
3. **What gets standardized?** Territorial codes are forced to a 4-character
   zero-padded string; years to plain integers; the methodological 280-zone
   scope is applied explicitly (not implicitly); column names are renamed to
   describe content (`establishment_creations`, not `side_establishment_creations_official`
   or a generic `value`).
4. **Why 306 → 280?** Continental/metropolitan France, excluding Corsica and
   the overseas departments — see section 4. A deliberate, reproducible
   scope filter, not missing data.
5. **Which treated file is canonical?** `data/processed/france_ze2020/fr_ze2020_clean_panel.csv`.
6. **Which files are legacy?** `data/processed/dynamic_stgnn_feature_panel_v1.csv`
   and its siblings (`flores_panel_ze2020_annual_v1.csv`,
   `side_stocks_lagged_ze2020_annual_v1.csv`,
   `dynamic_stgnn_walk_forward_splits_v1.csv`) — still actively used by Q7
   training, not deleted, but not the source for any new data-treatment work.
7. **What columns exist in the canonical panel?** See section 3.
8. **What does each column mean?** See section 3.
9. **What is explicitly NOT done yet at this stage?**
   - No sector-level (A10) panel built yet (`side_creations_a10_ze2020_v1.csv`
     exists but its lineage was not re-derived in this pass).
   - No growth/lag/model features of any kind — those belong to a future
     modeling-input stage, and must use the lag-only formulas in section 5.
   - No model-ready file (`fr_ze2020_model_ready_panel.csv`) — not created.
   - The 2025 extension (`target_side_establishments_annual_core_through_2025_v1.csv`)
     was not reconciled against this pass's raw-commune re-derivation; this
     panel stops at 2024, matching the raw source's actual coverage.
   - No claim about model performance, causality, or readiness is made by
     this document.

---

## 9. Recommended next step (as of this section's original writing)

Only after this data layer is reviewed: build a separate, explicitly-named
model-input stage (e.g. `fr_ze2020_model_ready_panel.csv`) that adds
lag-only features (`growth_1y_safe`, `growth_2y_safe`, `lag_1`, `lag_2`,
`lag_3`) on top of this panel, plus `mask_lag_*_available` columns — never by
editing this panel in place, and never by reintroducing
`dynamic_stgnn_feature_panel_v1.csv` as a primary source.

**Done — see section 10 below.**

---

## 10. Step 3 — Model-ready causal panel

**Input:** `data/processed/france_ze2020/fr_ze2020_clean_panel.csv` (section
3 schema, read-only — confirmed byte-identical before and after this step by
`tests/test_fr_ze2020_model_ready_panel.py::test_clean_panel_input_not_modified_by_this_stage`).

**Output:** `data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv`
(3,640 rows, same 280 zones × 2012-2024 grain, 15 columns), built by
`src/data/france_ze2020/build_fr_ze2020_model_ready_panel.py`.

**Columns added on top of the clean panel:**

| Column | Meaning |
|---|---|
| `observed_value` | Copy of `establishment_creations` from the clean panel — the single target value used at this stage (kept separate from `enterprise_creations` to avoid ambiguity about which series the future model targets). |
| `target_variable` | Constant string `"establishment_creations"` — documents which clean-panel column `observed_value` came from. |
| `lag_1` / `lag_2` / `lag_3` | `observed_value` of the same `ze2020`, 1/2/3 years earlier (`groupby("ze2020")["observed_value"].shift(1/2/3)`). `NaN` for the first 1/2/3 years of each zone's series (2012-2014) — not filled. |
| `growth_1y_safe` | `(lag_1 - lag_2) / lag_2` — both terms strictly t-1 and earlier. |
| `growth_2y_safe` | `(lag_1 - lag_3) / lag_3` — both terms strictly t-1 and earlier. |
| `mask_observed_available` / `mask_lag_1_available` / `mask_lag_2_available` / `mask_lag_3_available` | 1 if the corresponding value is non-null for this row, else 0. |
| `node_id` | Integer 0-279, assigned by sorting the 280 distinct `ze2020` values ascending. Stable/deterministic; additive only — `ze2020` remains the join key, `node_id` never replaces it. |

**Why `growth_1y_safe`/`growth_2y_safe` are causal:** both formulas read only
`lag_1`, `lag_2`, `lag_3` — values already shifted to `t-1`/`t-2`/`t-3` — and
never `observed_value` of the current row. This is the opposite construction
from the legacy `growth_1y`/`growth_2y` columns audited in section 5
(`pct_change()` directly on the target column itself, i.e. same-row
target-derived). `tests/test_fr_ze2020_model_ready_panel.py::test_growth_1y_safe_does_not_reconstruct_current_year_value`
checks this explicitly: solving `lag_1 * (1 + growth_1y_safe)` recovers
`lag_1` itself (last year's value), never the current row's
`observed_value`.

**Why `dynamic_stgnn_feature_panel_v1.csv` is still not used as a source:**
same reason as section 5 — its `growth_1y`/`growth_2y` are leaky and its
`feature_forecast_safe` flag is a hardcoded constant, not real signal.
`build_fr_ze2020_model_ready_panel.py` reads only the clean panel from this
pass; `tests/test_fr_ze2020_model_ready_panel.py::test_builder_does_not_read_legacy_dynamic_stgnn_panels`
asserts the builder's executable code contains no reference to
`dynamic_stgnn_feature_panel` (the module docstring is allowed to name it,
to document the exclusion).

**Masking, not fabrication:** 2012 rows have `lag_1/2/3 = NaN` and
`mask_lag_*_available = 0` for every zone (no prior year exists in the
panel). 2013 rows have `lag_1` available but `lag_2/3` still `NaN`/0. 2014
adds `lag_2`. 2015 is the first year with all three lags and both growth
features populated. No early year was dropped and no missing lag was filled
with zero, mean, or forward-fill — verified by
`test_masks_reflect_lag_availability_at_panel_start` and
`test_no_nan_silently_filled_where_mask_says_unavailable`.

**What this stage explicitly does NOT do:** no training, no model
evaluation, no sector dimension, no graph/network structure, no
`is_covid_year`/`is_post_covid_rebound`/`feature_forecast_safe`/
`has_urssaf_source` columns (all checked absent by
`test_no_forbidden_columns`). This panel is the base for a future training
stage — building, running, or evaluating that model is a separate task, not
performed here.

**Tests:** `tests/test_fr_ze2020_model_ready_panel.py` (13 tests, all
passing) — schema, `ze2020` zero-padded-string invariant, 280-zone count,
`node_id` determinism/coverage/non-replacement of `ze2020`, the Alençon
(`0051`) lag/growth worked example for 2012-2015, mask correctness at the
start of the panel, no forbidden columns, no read of the legacy STGNN panel,
and byte-identical clean-panel input. Combined with the existing
`tests/test_fr_ze2020_clean_panel.py` (12 tests) and
`tests/test_herald_artifact_registry.py` (13 tests): 38 tests pass across
the full FR ZE2020 data pipeline plus the artifact registry.

**Registry:** `PANEL_FR_ZE2020_MODEL_READY_CAUSAL` added to
`reports/herald_artifact_registry.json`, alongside the existing
`PANEL_FR_ZE2020_CLEAN_TREATED` and `FR_DYNAMIC_STGNN_LEGACY_FEATURE_PANEL`
entries.

**Next step (still not done):** train/evaluate a model against this panel —
explicitly out of scope for this pass. The recommended follow-up is to audit
`train_herald_v6.py`/`train_herald_v7.py` and `scripts/02_ridge_ar_official.py`
for whether they can be pointed at `fr_ze2020_model_ready_panel.csv` instead
of the legacy leaky panel, as a separate, reviewed task.
