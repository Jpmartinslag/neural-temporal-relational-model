# HERALD Economic Observatory v0.1 — Data Contract

**Version:** 0.1
**Created:** 2026-06-12
**Decision:** DEC-030 (Observatory v0.1 authorized)
**Generator:** `src/data/european_panel/build_observatory_export.py`
**Output:** `data/processed/herald_observatory_v01/`

---

## Purpose

This document defines the schema, field semantics, causal-safety guarantees, and
permitted/forbidden claims for the HERALD Observatory v0.1 unified data export.
The export assembles validated components (persistence/Ridge forecasting, economic
state labels, evidence tier metadata) into a single per-territory × per-year table.

---

## Output Files

| File | Description |
|------|-------------|
| `herald_observatory_v01_panel.csv` | Primary export (1963 rows) |
| `herald_observatory_v01_manifest.json` | Provenance, statistics, causal-safety flags |
| `herald_observatory_v01_summary.json` | Per-country statistics and WMAPE |

---

## Schema (per row)

| Column | Type | Description |
|--------|------|-------------|
| `country` | str | ISO 2-letter country code (AT, IT, PT) |
| `territory_id` | str | Internal territory identifier (e.g. PT_111) |
| `meta_nuts3_code` | str | Eurostat NUTS3 code (e.g. PT111) |
| `territory_name` | str | Human-readable territory name |
| `observation_year` | int | Year of the observed and forecast value |
| `sector_id` | str | "AGGREGATE" in v0.1 (sector-level extension is v0.2) |
| `observed_value` | float | Observed enterprise births for this territory-year |
| `persistence_forecast` | float | Prior-year observed value as naive baseline forecast (NaN if no prior year) |
| `ridge_forecast` | float | Rolling-origin Ridge forecast using lag1_births as feature (NaN for early years) |
| `forecast_lower` | float | Lower uncertainty bound — **NaN in v0.1** (method not selected) |
| `forecast_upper` | float | Upper uncertainty bound — **NaN in v0.1** (method not selected) |
| `economic_state` | str | Economic state label (see taxonomy below) |
| `velocity` | float | Year-on-year fractional change: (y_t − y_{t-1}) / y_{t-1} |
| `acceleration` | float | Change in velocity: velocity_t − velocity_{t-1} |
| `g1_l2_available` | int | 1 if country has validated G1-L2 co-growth field (DEC-019/020); else 0 |
| `sector_graph_available` | int | **Always 0.** Sector→sector graph not yet implemented |
| `evidence_tier` | str | Evidence classification for this row (see taxonomy below) |
| `data_source` | str | Source label from the harmonized panel (INE, Eurostat, etc.) |

---

## Economic State Taxonomy

States are derived from the observed time series only (not from forecasts). They are
descriptive labels, not predictions.

| State | Condition |
|-------|-----------|
| `insufficient_history` | No prior-year value available (year=2008 for most territories) |
| `stagnation` | \|delta_t\| ≤ 3% (near-zero annual change) |
| `growth` | delta_t > 3% and prior year was not declining |
| `acceleration` | delta_t > 3% and growing faster than prior year |
| `deceleration` | delta_t < -3% but prior year was growing (positive→negative) |
| `decline` | delta_t < -3% and prior year was also declining |
| `recovery` | delta_t > 3% but prior year was declining (negative→positive) |

Where `delta_t = (y_t − y_{t-1}) / y_{t-1}`.

Counts in v0.1: stagnation=550, decline=491, deceleration=266, recovery=209,
acceleration=202, insufficient_history=151, growth=94 (total=1963).

---

## Evidence Tier Taxonomy

| Tier | Meaning |
|------|---------|
| `validated_loco` | Row is from the Phase 4N LOCO-validated harmonized panel (flag_forecast_safe=1) |
| `pending_reaudit` | Row has results but causal pipeline audit is not yet complete (France Q7 WMAPE) |
| `exploratory` | Result exists but methodology is exploratory, not promoted |
| `not_available` | No validated result available for this territory-year |

---

## Causal-Safety Guarantees

1. **No target leakage:** `growth_1y[t]` (leaky in Phase 4A/4D) is NOT used. Only
   `lag1_births` (= `target_births[t-1]`) is used as a Ridge feature.
2. **Rolling-origin:** For each territory-year pair (r, t), the Ridge model is trained
   on observations (r, t') where t' < t. The forecast for year t does not use any
   data from year t.
3. **Persistence:** `persistence_forecast[t] = observed_value[t-1]`. Strictly causal.
4. **Uncertainty intervals:** NaN in v0.1. Method selection (conformal or bootstrap)
   is required before intervals can be published.

---

## G1-L2 Availability Flag

| Country | `g1_l2_available` | Justification |
|---------|:-----------------:|---------------|
| PT | 1 | G1-L2 PASS (DEC-019/020) |
| FR | 1 | G1-L2 PASS (DEC-019/020) — not in this panel |
| NL | 1 | G1-L2 PASS (DEC-019/020) — not in this panel |
| IT | 0 | G1-L2 not validated for Italy |
| AT | 0 | G1-L2 not validated for Austria |

---

## Permitted Claims from this Export

- "The harmonized PT/IT/AT panel covers 151 mainland NUTS3 territories, 2008–2020."
- "Persistence WMAPE (all years, not rolling eval): AT ~0.080, IT ~0.059, PT ~0.143."
- "Economic state labels are descriptive, derived from observed data, not from forecasts."
- "G1-L2 co-growth field is validated for PT (DEC-019/020); not validated for IT/AT."

---

## Forbidden Claims from this Export

| Forbidden claim | Reason |
|-----------------|--------|
| "HERALD v0.1 forecasts beyond 2020" | Panel ends at 2020 |
| "Ridge WMAPE matches Phase 4N WMAPE 0.0874" | Phase 4N used a different eval protocol and features |
| "France results are validated" | France WMAPE 0.0204 is PENDING_REAUDIT; France not in this panel |
| "Sector-level economic states are available" | sector_id = AGGREGATE only in v0.1 |
| "Uncertainty intervals are available" | forecast_lower/upper = NaN |
| "G1-L2 provides predictive improvement" | G1-L2 is an associative analytical layer only (DEC-019) |
| "Sector graph is available" | sector_graph_available = 0 always |
| "Economic states are forecast results" | States are descriptive labels from observed series |

---

## v0.2 Extensions (Not Yet Implemented)

- Sector-level rows for FR/NL/PT (from `sector_panel_fr_nl_pt.csv`)
- France integration after causal pipeline audit of WMAPE 0.0204 is complete
- Uncertainty intervals (conformal or bootstrap, to be selected via DEC-*)
- Sector→sector graph layer (simple auditable method, to be designed via DEC-*)
- NL and BE integration

---

## Regeneration

```bash
python3 src/data/european_panel/build_observatory_export.py
```

Requires: `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv`
Tests: `pytest tests/test_observatory_export.py -v`
