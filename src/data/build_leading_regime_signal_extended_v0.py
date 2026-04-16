import pandas as pd
import zipfile
import io
import os
import json
from pathlib import Path

def build_leading_signal_extended():
    # Paths
    series_path = 'data/raw/business_demography/side/DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip'
    profile_path = 'data/interim/tables/zone_sectoral_profile_history_v0.csv'
    output_path = 'data/interim/tables/leading_regime_signal_extended_v0.csv'
    quality_report_path = 'reports/leading_regime_signal_extended_quality_v0.json'

    print(f"Reading SIDE series from {series_path}...")

    # 1. Read National Series
    with zipfile.ZipFile(series_path) as z:
        with z.open('DS_SIDE_CREA_ENT_SERIES_data.csv') as f:
            df_series = pd.read_csv(f, sep=';', dtype={'TIME_PERIOD': str, 'OBS_VALUE': float})

    # Filter for national adjusted total series
    mask = (
        (df_series['GEO_OBJECT'] == 'FRANCE') &
        (df_series['SEASONAL_ADJUST'] == 'Y') &
        (df_series['LEGAL_FORM'] == '_T') &
        (df_series['FREQ'] == 'M')
    )
    df_filtered = df_series[mask][['ACTIVITY', 'TIME_PERIOD', 'OBS_VALUE']]

    # 2. Pivot and Calculate Growth (YoY)
    df_pivot = df_filtered.pivot(index='TIME_PERIOD', columns='ACTIVITY', values='OBS_VALUE')
    df_growth = df_pivot.pct_change(12)

    # 3. Load Zone Sectoral Profile History
    df_profile_hist = pd.read_csv(profile_path, dtype={'ZE2020': str})

    # Mapping to A17 weights (Extended/Corrected)
    mapping = {
        'weight_a17_AZ': '_T',
        'weight_a17_C1': 'C',
        'weight_a17_C2': 'C',
        'weight_a17_C3': 'C',
        'weight_a17_C4': 'C',
        'weight_a17_C5': 'C',
        'weight_a17_DE': 'BE',
        'weight_a17_FZ': 'FZ',
        'weight_a17_GZ': 'G',
        'weight_a17_HZ': 'H',
        'weight_a17_IZ': 'I',
        'weight_a17_JZ': 'JZ',
        'weight_a17_KZ': 'KZ',
        'weight_a17_LZ': 'LZ',
        'weight_a17_MN': 'MN',
        'weight_a17_OQ': 'OQ',
        'weight_a17_RU': 'RU'
    }

    # 4. Calculate signals for different horizons
    df_growth['year'] = df_growth.index.str[:4].astype(int)
    df_growth['month'] = df_growth.index.str[5:7].astype(int)

    horizons = {
        'jan_mar': [1, 2, 3],
        'jan_jun': [1, 2, 3, 4, 5, 6],
        'jan_sep': [1, 2, 3, 4, 5, 6, 7, 8, 9],
        'jan_dec': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }

    all_signals = []

    for yr in sorted(df_growth['year'].unique()):
        available_profiles = df_profile_hist['year_profile'].unique()
        # Strictly T-1 or earlier
        past_profiles = [y for y in available_profiles if y < yr]
        if not past_profiles:
            continue # No valid non-leaking profile

        best_profile_yr = max(past_profiles)
        df_profile = df_profile_hist[df_profile_hist['year_profile'] == best_profile_yr]
        actual_mapping = {k: v for k, v in mapping.items() if k in df_profile.columns}

        for h_name, months in horizons.items():
            df_h_growth = df_growth[(df_growth['year'] == yr) & (df_growth['month'].isin(months))].mean()
            growth_vector = df_h_growth.drop(['year', 'month'])

            if growth_vector.isnull().any(): continue

            for _, row in df_profile.iterrows():
                ze = row['ZE2020']
                exposure = 0
                for profile_col, series_code in actual_mapping.items():
                    if series_code in growth_vector:
                        exposure += row[profile_col] * growth_vector[series_code]

                all_signals.append({
                    'year': yr,
                    'ZE2020': ze,
                    'horizon': h_name,
                    'regime_leading_signal': exposure,
                    'profile_year_used': best_profile_yr
                })

    df_final_signal = pd.DataFrame(all_signals)

    # Lagged Version (Full year T-1 used to predict T)
    df_dec = df_final_signal[df_final_signal['horizon'] == 'jan_dec'].copy()
    df_dec['year'] = df_dec['year'] + 1
    df_dec['horizon'] = 'lag_1_full'

    df_final_signal = pd.concat([df_final_signal, df_dec])

    # Pivot
    df_output = df_final_signal.pivot_table(
        index=['year', 'ZE2020'],
        columns='horizon',
        values='regime_leading_signal'
    ).reset_index()

    df_output = df_output.rename(columns={
        'jan_mar': 'regime_signal_jan_mar',
        'jan_jun': 'regime_signal_jan_jun',
        'jan_sep': 'regime_signal_jan_sep',
        'jan_dec': 'regime_signal_jan_dec',
        'lag_1_full': 'regime_signal_lag_1'
    })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_output.to_csv(output_path, index=False)
    print(f"Saved extended multi-horizon leading signals to {output_path}")

    # Quality Report
    quality = {
        "years_count": int(df_output['year'].nunique()),
        "first_year": int(df_output['year'].min()),
        "last_year": int(df_output['year'].max()),
        "profile_mapping_logic": "strictly uses profile of T-1 or earlier for signal of year T"
    }
    with open(quality_report_path, 'w') as f:
        json.dump(quality, f, indent=4)

if __name__ == "__main__":
    build_leading_signal_extended()
