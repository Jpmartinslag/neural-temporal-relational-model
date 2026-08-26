# Exploratory or secondary datasets — France pipeline

Date: 2026-05-07

These datasets were collected or considered, but do not yet structure the main model. They should
stay documented so they are not lost, without cluttering the scientific narrative.

## Useful but non-primary candidates

| Source | Current file | Potential | Risk / reason for caution |
|---|---|---|---|
| BPE facilities/amenities | `data/interim/tables/bpe_commune_2024.csv`; `bpe_evolution_commune_2019_2024_geo2025.csv` | services, amenities, local attractiveness | mostly structural; risk of low annual predictive value |
| FILOSOFI income | `data/interim/tables/filosofi_commune_2020.csv`; `filosofi_commune_2021.csv` | socio-economic context | slow release cadence; not a very dynamic signal |
| Population / census | `rp_population_commune_2021.csv`; `rp_population_commune_2022.csv`; `population_history_annual_ze2020_v0.csv` | size normalization, demographic context | can dominate through a size effect if not properly normalized |
| Employment at place of residence/work | `rp_emploi_*` | labor-market structure | slow census cadence; not conjunctural |
| SITADEL construction | `sitadel_monthly_*`; `sitadel_surface_*` | leading territorial signal, real estate/construction | watch the monthly cutoff; potentially very useful but not yet canonical |
| Energy | `energy_consumption_ze2020_v0.csv` | indirect productive activity | source heterogeneity and publication lags |
| ZRR/QPV/ZAN public-policy zoning | `data/interim/policy/*` | territorial policy reading, app/recommendation use | do not use without an ablation; risk of overreaching causal interpretation |
| A17 sectoral | `zone_sectoral_profile_a17_v0.csv`; `zone_sectoral_profile_history_v0.csv` | finer sectoral granularity than A10 | complicates the sector head; test only after A10 is robust |
| Historical REI / CFE | `rei_cfe_ze2020_v0.csv` | historical benchmark | methodological break vs. SIDE; keep in quarantine |

## Promotion rule

An exploratory source only becomes primary if:

1. its publication date is known;
2. it can be aligned to geo2025/ZE2020;
3. it improves a metric or an interpretable indicator in a dedicated ablation;
4. it does not turn a forecast into a hidden nowcast;
5. it carries a clear economic reading.

## Future priority

Recommended order:

1. Monthly SITADEL with a clean cutoff;
2. BPE/FILOSOFI/population as slow context;
3. Public-policy zoning for interpretation, not as a primary predictor;
4. A17/A20 only once A10 is stable.
