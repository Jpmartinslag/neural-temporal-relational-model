# HERALD Economic Observatory — Data Contract

**Version:** aggregate v0.1.1 + sector v0.2
**Updated:** 2026-06-12
**Decision:** DEC-032
**Generator:** `src/data/european_panel/build_observatory_export.py`

## Products

| Product | Scope | Rows | Output |
|---|---|---:|---|
| v0.1.1 aggregate | PT/IT/AT, 151 NUTS3, 2008–2020 | 1,963 | `data/processed/herald_observatory_v01/herald_observatory_v011_*` |
| v0.2 sector | FR/NL/PT, 345 territories, 9 sectors | 45,945 | `data/processed/herald_observatory_v02/herald_observatory_v02_*` |

The CSV panels are regenerable and stay outside Git. Their manifests and
summaries are small provenance artefacts suitable for version control.

## Shared Key And Schema

The unique key is:

`country × territory_id × observation_year × sector_id`

Core fields:

- identity: `country`, `territory_id`, `meta_nuts3_code`,
  `territory_name`, `region_system`, `sector_id`, `sector_label`;
- semantics: `target_concept`, `source_label`;
- observations: `observed_value`, `lag1_value`, `velocity`,
  `acceleration`, `economic_state`;
- forecasts: `persistence_forecast`, `ridge_forecast`,
  `forecast_lower`, `forecast_upper`, `forecast_method`,
  `forecast_status`;
- evidence: `data_evidence_tier`, `forecast_evidence_tier`,
  `graph_evidence_tier`;
- masks: `structural_mask`, `observation_mask`;
- graph availability: `territorial_graph_available`,
  `sector_graph_available`;
- quality: `data_quality_flags`.

Evidence is deliberately separated. Membership in a validated dataset does not
automatically validate a forecast or graph claim.

## Economic States

States are deterministic descriptions of observations, not predictions.

| State | Definition |
|---|---|
| `insufficient_history` | Current/prior observation unavailable or denominator invalid |
| `stagnation` | Absolute annual growth ≤ 3% |
| `growth` | Positive growth >3%, without a clear acceleration/deceleration pattern |
| `acceleration` | Positive growth >3% and faster than the prior positive growth rate |
| `deceleration` | Positive growth >3%, but slower than the prior positive growth rate |
| `decline` | Current annual growth <−3%, including a transition from growth to contraction |
| `recovery` | Positive growth >3% following prior decline |

This corrects the former v0.1 definition that called a positive-to-negative
transition “deceleration”. A sector may decelerate while still growing.

## Evidence Tiers

### Data

- `harmonized_enterprise_birth`
- `observed_national_sector_panel`
- `structural_absence`
- `missing_observation`

### Forecast

- `exploratory_rolling_origin`
- `causal_persistence_only`
- `unavailable`

### Graph

- `supported_association_field`
- `structural_absence`
- `not_available`

`supported_association_field` means that G1-L2 exists as a same-sector,
cross-territory association field. It does not mean predictive improvement or
causality.

## Causal-Safety Contract

1. Persistence at year `t` is the observed value at `t-1`.
2. Ridge at year `t` is fitted only on earlier pairs and uses only the `t-1`
   observed value.
3. State, velocity and acceleration use at most `t`, `t-1` and `t-2`
   observations. They are descriptive and are not used as same-year forecast
   features.
4. Structural absence and missing observations remain distinct, masked and
   `NaN`, never economic zero. PT/KZ is structural; unavailable NL/OQ years are
   missing observations.
5. Forecast intervals remain `NaN`; no uncertainty method is promoted yet.
6. `sector_graph_available=0` in both products. Sector-to-sector influence is
   not implemented.
7. No P6 learned graph or pending France Q7 output is consumed.

## Product-Specific Scope

### Aggregate v0.1.1

- Countries: PT, IT, AT.
- `sector_id=AGGREGATE`.
- Forecast evidence is separate from Phase 4N panel evidence.
- No territorial graph is attached to aggregate rows.

### Sector v0.2

- FR: 280 ZE2020, 2012–2025.
- NL: 40 COROP, 2007–2025.
- PT: 25 NUTS3, 2008–2024.
- Nine A10-compatible business sectors.
- PT `KZ` is structurally absent and remains masked.
- Unsupported NL `OQ` years are missing observations, not structural absence.
- National concepts remain heterogeneous; no pooled-country claim is allowed.

## Permitted Claims

- The Observatory now exposes observed territorial-sector trajectories and
  deterministic state labels for FR/NL/PT.
- The exports provide causal persistence and exploratory AR(1) Ridge point
  baselines.
- G1-L2 availability identifies an existing analytical association layer.

## Forbidden Claims

- Sector-to-sector influence is implemented.
- The point forecasts are promoted scientific results.
- Uncertainty intervals are available.
- G1-L2 improves prediction or identifies structural causality.
- National sector targets may be pooled as equivalent.
- Economic states are forecasts.

## Regeneration

```bash
python3 -m src.data.european_panel.build_observatory_export --mode all
python3 -m pytest -q tests/test_observatory_export.py
```
