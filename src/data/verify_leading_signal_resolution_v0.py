import pandas as pd
import numpy as np
import os

def verify_resolution():
    # Paths
    leading_signal_path = 'data/interim/tables/leading_regime_signal_ze2020_v0.csv'
    side_target_path = 'data/processed/target_side_establishments_annual_core_v0.csv'

    # 1. Load Leading Signal
    df_leading = pd.read_csv(leading_signal_path, dtype={'ZE2020': str})
    # Aggregate monthly signal to annual for comparison with annual target
    df_leading['year'] = df_leading['TIME_PERIOD'].str[:4].astype(int)
    # We take the mean signal of the year as the annual 'regime' indicator
    df_annual_leading = df_leading.groupby(['ZE2020', 'year'])['regime_leading_signal'].mean().reset_index()

    # 2. Load SIDE Target and calculate growth
    df_side_long = pd.read_csv(side_target_path, dtype={'ze2020': str})
    df_side_wide = df_side_long.pivot(index='ze2020', columns='target_year', values='side_establishment_creations_official')

    growth_rows = []
    years = sorted(df_side_wide.columns.unique())
    for i in range(1, len(years)):
        curr = years[i]
        prev = years[i-1]
        for ze in df_side_wide.index:
            growth = (df_side_wide.loc[ze, curr] / df_side_wide.loc[ze, prev]) - 1
            growth_rows.append({'ZE2020': ze, 'year': curr, 'actual_growth': growth})

    df_actual_growth = pd.DataFrame(growth_rows)

    # 3. Merge and Correlate
    df_compare = df_annual_leading.merge(df_actual_growth, on=['ZE2020', 'year'])

    print("### leading_regime_signal vs Actual SIDE Growth ###")
    for year in sorted(df_compare['year'].unique()):
        df_year = df_compare[df_compare['year'] == year]
        corr = df_year['regime_leading_signal'].corr(df_year['actual_growth'])
        print(f"Year {year}: Correlation = {corr:.4f} | Avg Signal = {df_year['regime_leading_signal'].mean():.2%} | Avg Growth = {df_year['actual_growth'].mean():.2%}")

    global_corr = df_compare['regime_leading_signal'].corr(df_compare['actual_growth'])
    print(f"\nGlobal Correlation: {global_corr:.4f}")

    # 4. Success Criteria
    # If correlation is significantly positive (> 0.4) in years of regime shift (2021, 2024), it's a success.
    print("\n### Conclusion ###")
    if global_corr > 0.4:
        print("SUCCESS: The leading signal has strong correlation with local growth.")
    elif global_corr > 0.1:
        print("PARTIAL SUCCESS: The signal shows positive correlation, much better than ICA (-0.15).")
    else:
        print("FAILURE: The signal is still weak. Sectoral weights or national series might need adjustment.")

if __name__ == "__main__":
    verify_resolution()
