# HERALD G1 Sector Data Preflight

**Status:** PASS

The panel is analytical and unlagged. `available_for_forecast_year` makes
the temporal contract explicit. Agriculture is excluded rather than folded
into `OQ`.

## Birth-sector nucleus

| Country | Regions | Years | Complete graph years | Unsupported | Observed | Concept | Region system |
|---|---:|---|---|---|---:|---|---|
| FR | 280 | 2012-2025 | 2012-2025 | none | 100.0% | establishment_creation | ZE2020 |
| NL | 40 | 2007-2025 | 2015-2025 | OQ | 95.3% | local_unit_opening | COROP |
| PT | 25 | 2008-2024 | none | KZ | 100.0% | enterprise_birth | NUTS3 |

## Belgium employment complement

BE contains 42 territories, 9 sectors and years 2008-2024 (100.0% observed).

## Important limitations

- FR, NL and PT use different target concepts and territorial systems.
- Raw birth counts must not be pooled across countries.
- France has aggregate quarterly URSSAF employment in the current repository,
  not a verified territory-by-A10 employment table.
- Belgium is an employment complement, not a birth-sector member of the core.
- A country-year sector with zero total mass is marked unsupported rather
  than interpreted as a verified economic absence.
- PT has no complete nine-sector graph year because `KZ` has zero mass in
  every territory and year; PT is retained in the file but excluded from
  L1/L3 validation until the source definition is resolved.
- `bd_hgnace_r` is a complementary NUTS3 bridge and requires a separate
  crosswalk for ZE2020 and COROP comparisons.

## Outputs

- `birth sector panel`: `data/processed/economic_graph/sector_panel_fr_nl_pt.csv`
- `Belgium employment complement`: `data/processed/economic_graph/employment_panel_be.csv`
- `machine-readable audit`: `data/processed/economic_graph/g1_sector_preflight.json`
