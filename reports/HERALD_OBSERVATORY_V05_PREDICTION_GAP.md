# HERALD Observatory v0.5 — Prediction Layer Gap Audit

**Status:** PREDICTION_LAYER_PARTIAL (FR + NL ready; PT gap, no HPC required to close)
**Date:** 2026-06-17
**Scope:** Audits whether a standardized, validated "observed vs expected" prediction
export exists across FR/PT/NL at the granularity used by the Observatory v0.4/v0.5
exports, and what it would take to close any gap. No HPC job was launched to produce
this audit; no model was retrained.

---

## 1. What already exists

`data/processed/herald_observatory_v03/herald_observatory_v03_panel.csv` (45,945 rows,
FR+NL+PT jointly) already contains a real, causal, rolling-origin forecast layer per
`(country, territory_id, sector_id, observation_year)`:

| Column | Meaning |
|---|---|
| `observed_value` | actual value for that territory/sector/year |
| `lag1_value` | previous year's value (used for the persistence baseline) |
| `persistence_forecast` | naive lag-1 baseline |
| `ridge_forecast` | causal rolling-origin AR(1) Ridge forecast (`RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`) |
| `forecast_method`, `forecast_status`, `forecast_evidence_tier` | how/whether a forecast was produced |
| `economic_state`, `velocity`, `acceleration` | derived trend descriptors |

This was built by `src/data/european_panel/build_observatory_export.py` and consumed by
the v0.1–v0.3 Observatory dashboards (`build_observatory_v03.py`). It is **not**
fabricated for this audit — it predates v0.5 by several phases and was already used in a
shipped dashboard (v0.3).

---

## 2. Granularity mismatch — why PT is excluded from v0.5's prediction layer

| Country | v0.3 forecast `region_system` | v0.4/v0.5 granular `region_system` | Match? |
|---|---|---|---|
| FR | `ZE2020` (280 zones) | `ZE2020` (280 zones) | **YES** — same 280 units |
| NL | `COROP` (40 regions) | `COROP` (40 regions) | **YES** — same 40 units |
| PT | `NUTS3` (25 coarse territories) | `MUNICIPALITY` (278 fine territories) | **NO** |

FR and NL forecasts join directly onto the granular territory state panel by
`(country, region_id, sector_a10, year)` because both sources use the *same* region
system at the *same* granularity. PT does not: the only PT forecast that exists today is
at the 25-territory NUTS3 scale (the original v0.1–v0.3 Observatory scope), while the
v0.4/v0.5 granular layer uses the 278-municipality scale introduced by DEC-064 (PT
Municipal Phase 7). There is no row-level correspondence between a NUTS3 forecast and a
municipality — a NUTS3 region aggregates roughly 11 municipalities on average, and
disaggregating a NUTS3-level Ridge forecast down to municipality level would require a
new allocation method (e.g. a stock-share proxy), which is exactly the category of
estimation DEC-065 found structurally invalid for NL gemeente. Re-using that pattern for
PT municipal forecasts would not be a "validated" prediction — it would repeat the
known proxy-injection failure mode, just for a different country.

**This audit picked option (B) from the task brief:** ship the prediction panel only for
the countries/grains where a genuinely validated forecast already exists (FR ZE2020, NL
COROP), and label the gap explicitly rather than fabricate or proxy-disaggregate a PT
municipal forecast.

---

## 3. What the v0.5 dashboard does with this

- `prediction_view.csv` / `.json` (in `data/processed/herald_observatory_v05_narrative/`)
  contains 42,120 rows for FR + NL only (`rules.prediction_layer_countries: ["FR","NL"]`
  in `manifest.json`).
- The dashboard's "Above or below expected?" section shows a banner: *"Validated against
  expectation today for: FR, NL. Portugal is not yet included at this territorial
  detail — see the Prediction Gap report for why and what would be needed."*
- The map's "Above / below expected" view mode is available for all three countries (it
  reads from the same lookup), but for PT it will correctly show "No prediction
  available" per cell — never a fabricated number, never a bare NaN.

---

## 4. What would be needed to close the gap (not authorised, not executed here)

Two non-exclusive paths, **neither requiring HPC retraining**:

1. **Re-run `build_observatory_export.py`'s Ridge/persistence forecast directly on the
   PT municipal panel** (`data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv`,
   278 municipalities × ~15 years × 8 sectors). This is the same AR(1) Ridge code already
   used for FR/NL, just pointed at a different input panel — pure data engineering, CPU
   seconds, no GPU/HPC needed. This would produce a genuinely observed-grain PT
   municipal forecast (no proxy disaggregation involved) and should be the preferred
   path if a PT prediction layer at municipal grain is wanted.
2. **Keep PT prediction only at NUTS3** and surface it as a separate, coarser-grain
   panel in a future dashboard iteration, explicitly labelled with its own (coarser)
   territorial scope rather than joined onto the municipal map.

Both are scoped as follow-up work; this audit does not implement either. The current
v0.5 dashboard takes the safe default: show what is validated, label what is missing,
fabricate nothing.

---

## 5. Decision

`PREDICTION_LAYER_PARTIAL` — FR and NL have a validated, ready-to-use observed-vs-expected
layer wired directly into v0.5. PT does not, for a structural (not effort) reason: its
only existing forecast is at a coarser, incompatible granularity. Closing the gap is a
data-engineering task (re-run the existing Ridge/persistence forecast script against the
PT municipal panel), not a modeling or HPC task.

---

*HERALD Observatory v0.5 Prediction Gap Audit | PREDICTION_LAYER_PARTIAL | 2026-06-17*

---

## 6. v0.5.1 correction — gap CLOSED

**Status update (2026-06-17, v0.5.1):** `CLOSED`.

Path (1) from §4 above was implemented exactly as scoped: the same causal
persistence/Ridge AR(1) forecasting code already used for FR ZE2020 / NL
COROP (`build_observatory_export.py._rolling_ridge_forecasts`,
`RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`) was re-run directly against the PT
municipal panel (`data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv`,
278 municipalities × 16 years × 8 observable A10 sectors; KZ structurally
absent for every row, per DEC-064/DEC-018) by a new dedicated script,
`src/data/european_panel/build_pt_municipal_prediction_layer.py`.

PT municipal forecast generated via causal persistence/Ridge on observed municipal panel; no proxy, no HPC.

Output: `data/processed/herald_observatory_v051_narrative/pt_municipal_prediction_view.csv`
(40,032 rows: 28,974 `valid_forecast`, 6,610 `insufficient_history`, 4,448
`structural_absent` — exactly the KZ rows). An explicit leakage check
(`_assert_no_leakage`) verifies, for every `valid_forecast` row, that
`persistence_forecast` equals the prior year's `observed_value` in the
source panel — i.e. the forecast at year *t* never uses *t* or later data.
This check passed for all 28,974 valid-forecast rows on the run used for
this correction.

The PT municipal forecast is integrated into the unified
`prediction_view.csv`/`.json` built by
`src/data/european_panel/build_observatory_v051_narrative_exports.py`
alongside FR ZE2020 / NL COROP, using the same schema
(`country, region_id, region_system, sector_a10, sector_name, year,
observed_value, expected_value, difference, trend_state, forecast_method,
forecast_status, forecast_evidence_tier, available`). PT KZ rows are always
`available=False` (asserted in the exports builder).

This closes the gap described in §2–§5 above for the v0.5.1 dashboard
(`reports/dashboards/herald_observatory_v051_narrative_dashboard.html`).
The v0.5 dashboard is untouched and remains `PREDICTION_LAYER_PARTIAL` as
originally shipped — this correction applies to v0.5.1 only.

See `reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md` for the full
point-by-point correction record.
