# Dynamic Feature Panel Baseline — V1

Walk-forward evaluation of Ridge baselines with FLORES t-1 and SIDE stocks t-1.

## WMAPE by model and year

model|2021|2022|2023|2024
Ridge_AR|0.0673|0.0862|0.0777|0.036
Ridge_AR_FLORES|0.0797|0.0759|0.1188|0.0545
Ridge_AR_FLORES_SIDE_URSSAF|0.1099|0.0635|0.0619|0.0931
Ridge_AR_SIDE_stocks|0.0908|0.0324|0.0589|0.118
Ridge_AR_URSSAF|0.0696|0.1332|0.1507|0.0835


## Delta vs Ridge autoregressivo (WMAPE, negative = improvement)

model|2021|2022|2023|2024
Ridge_AR|0.0|0.0|0.0|0.0
Ridge_AR_FLORES|0.0123|-0.0103|0.0412|0.0185
Ridge_AR_FLORES_SIDE_URSSAF|0.0426|-0.0227|-0.0158|0.0571
Ridge_AR_SIDE_stocks|0.0234|-0.0538|-0.0188|0.082
Ridge_AR_URSSAF|0.0023|0.047|0.0731|0.0475


## Approval decisions

### Ridge_AR_FLORES → ❌ REJECTED
  - rule1_improves_mean_2021_2024: False
  - rule2_no_strong_2022_2024_degradation: False
  - rule3_gain_without_2021: False
  - rule4_forecast_safe: True
  - mean_wmape_2021_2024: 0.08222
  - mean_wmape_2022_2024: 0.083075
  - delta_mean_vs_ar: 0.015426

### Ridge_AR_SIDE_stocks → ❌ REJECTED
  - rule1_improves_mean_2021_2024: False
  - rule2_no_strong_2022_2024_degradation: False
  - rule3_gain_without_2021: False
  - rule4_forecast_safe: True
  - mean_wmape_2021_2024: 0.075015
  - mean_wmape_2022_2024: 0.069767
  - delta_mean_vs_ar: 0.008221

### Ridge_AR_URSSAF → ❌ REJECTED
  - rule1_improves_mean_2021_2024: False
  - rule2_no_strong_2022_2024_degradation: False
  - rule3_gain_without_2021: False
  - rule4_forecast_safe: True
  - mean_wmape_2021_2024: 0.109255
  - mean_wmape_2022_2024: 0.122456
  - delta_mean_vs_ar: 0.04246

### Ridge_AR_FLORES_SIDE_URSSAF → ❌ REJECTED
  - rule1_improves_mean_2021_2024: False
  - rule2_no_strong_2022_2024_degradation: False
  - rule3_gain_without_2021: False
  - rule4_forecast_safe: True
  - mean_wmape_2021_2024: 0.082102
  - mean_wmape_2022_2024: 0.072821
  - delta_mean_vs_ar: 0.015308

## Improvement share (% zones better than AR)

  - Ridge_AR_FLORES_year2021: 53.6%
  - Ridge_AR_FLORES_year2022: 66.1%
  - Ridge_AR_FLORES_year2023: 32.1%
  - Ridge_AR_FLORES_year2024: 40.7%
  - Ridge_AR_SIDE_stocks_year2021: 62.5%
  - Ridge_AR_SIDE_stocks_year2022: 91.1%
  - Ridge_AR_SIDE_stocks_year2023: 51.8%
  - Ridge_AR_SIDE_stocks_year2024: 20.7%
  - Ridge_AR_URSSAF_year2021: 48.6%
  - Ridge_AR_URSSAF_year2022: 27.1%
  - Ridge_AR_URSSAF_year2023: 10.4%
  - Ridge_AR_URSSAF_year2024: 27.1%
  - Ridge_AR_FLORES_SIDE_URSSAF_year2021: 41.1%
  - Ridge_AR_FLORES_SIDE_URSSAF_year2022: 72.5%
  - Ridge_AR_FLORES_SIDE_URSSAF_year2023: 47.1%
  - Ridge_AR_FLORES_SIDE_URSSAF_year2024: 15.4%

## Conclusions

- **Ridge_AR_FLORES**: does NOT enter V1 (Δ mean WMAPE = +0.0154)
- **Ridge_AR_SIDE_stocks**: does NOT enter V1 (Δ mean WMAPE = +0.0082)
- **Ridge_AR_URSSAF**: does NOT enter V1 (Δ mean WMAPE = +0.0425)
- **Ridge_AR_FLORES_SIDE_URSSAF**: does NOT enter V1 (Δ mean WMAPE = +0.0153)

## Methodological notes

- COVID 2020 retained in training with `is_covid_year=1` flag.
- Approval requires gain in mean 2022-2024 (rule 3) to guard against 2021 rebound bias.
- All features are t-1 lagged (forecast-safe, INSEE lag ≥6 months for FLORES).
- Zone_Sectoral excluded (leakage confirmed, δ=-85%).
- SIRENE excluded (quarantine).