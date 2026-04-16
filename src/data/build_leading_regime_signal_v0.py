import pandas as pd
import zipfile
import io
import os
import json

def build_leading_signal():
    # Paths
    series_path = 'data/raw/business_demography/side/DS_SIDE_CREA_ENT_SERIES_CSV_FR.zip'
    profile_path = 'data/interim/tables/zone_sectoral_profile_a17_v0.csv'
    output_path = 'data/interim/tables/leading_regime_signal_ze2020_v0.csv'
    quality_report_path = 'reports/leading_regime_signal_quality_v0.json'

    # Check if profile a17 v0 exists (the one with the fix but static 2024)
    # If not, we might need to recreate it briefly or use the history one's 2024 slice
    if not os.path.exists(profile_path):
        hist_profile = pd.read_csv('data/interim/tables/zone_sectoral_profile_history_v0.csv', dtype={'ZE2020': str})
        df_profile = hist_profile[hist_profile['year_profile'] == 2024].drop(columns=['year_profile'])
        df_profile.to_csv(profile_path, index=False)
    else:
        df_profile = pd.read_csv(profile_path, dtype={'ZE2020': str})

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
    df_growth = df_pivot.pct_change(12).dropna()

    # Mapping to A17 weights
    mapping = {
        'weight_a17_AZ': '_T',
        'weight_a17_C1': 'BE',
        'weight_a17_C2': 'BE',
        'weight_a17_C3': 'BE',
        'weight_a17_C4': 'BE',
        'weight_a17_C5': 'BE',
        'weight_a17_DE': 'BE',
        'weight_a17_FZ': 'FZ',
        'weight_a17_GZ': 'GI',
        'weight_a17_HZ': 'GI',
        'weight_a17_IZ': 'GI',
        'weight_a17_JZ': 'JZ',
        'weight_a17_KZ': 'KZ', # Fixed from KTN in original if it was there
        'weight_a17_LZ': 'LZ',
        'weight_a17_MN': 'MN',
        'weight_a17_OQ': 'OQ',
        'weight_a17_RU': 'RU'
    }

    # 3. Project National Shocks to Zones
    signal_rows = []
    for period in df_growth.index:
        growth_vector = df_growth.loc[period]
        for _, row in df_profile.iterrows():
            ze = row['ZE2020']
            exposure = 0
            for profile_col, series_code in mapping.items():
                if series_code in growth_vector and profile_col in row:
                    exposure += row[profile_col] * growth_vector[series_code]
            signal_rows.append({
                'TIME_PERIOD': period,
                'ZE2020': ze,
                'regime_leading_signal': exposure
            })

    df_final_signal = pd.DataFrame(signal_rows)

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_final_signal.to_csv(output_path, index=False)
    print(f"Restored canonical leading signal to {output_path}")

if __name__ == "__main__":
    build_leading_signal()
