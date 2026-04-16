import pandas as pd
import zipfile
import io
import os
import json
import glob

def build_zone_sectoral_profile_history():
    # Paths
    mapping_path = 'data/interim/mappings/commune_to_ze2020_2026.csv'
    output_path = 'data/interim/tables/zone_sectoral_profile_history_v0.csv'
    quality_report_path = 'reports/zone_sectoral_profile_quality_v0.json'

    # Read mapping
    df_mapping = pd.read_csv(mapping_path, dtype={'CODGEO': str, 'ZE2020': str})

    # 1. Process 2024 (Long Format)
    flores_2024_path = 'data/raw/employment/flores/DS_FLORES_A17_2024_CSV_FR.zip'
    print(f"Processing 2024 from {flores_2024_path}...")

    chunks = []
    with zipfile.ZipFile(flores_2024_path) as z:
        with z.open('DS_FLORES_A17_2024_data.csv') as f:
            for chunk in pd.read_csv(f, sep=';', dtype={'GEO': str, 'TIME_PERIOD': int, 'OBS_VALUE': float}, chunksize=500000):
                mask = (
                    (chunk['GEO_OBJECT'] == 'COM') &
                    (chunk['FLORES_MEASURE'] == 'UNIT_LOC') &
                    (chunk['LEGAL_FORM_WITH_PUBLIC'] == '1T9X7') &
                    (chunk['NUMBER_EMPL'] == '_T')
                )
                chunks.append(chunk[mask][['GEO', 'ACTIVITY', 'OBS_VALUE']])

    df_2024_raw = pd.concat(chunks)
    df_2024_raw = df_2024_raw[df_2024_raw['ACTIVITY'] != '_T'] # Exclude total

    df_2024_joined = df_2024_raw.merge(df_mapping[['CODGEO', 'ZE2020']], left_on='GEO', right_on='CODGEO', how='inner')
    df_2024_ze = df_2024_joined.groupby(['ZE2020', 'ACTIVITY'])['OBS_VALUE'].sum().reset_index()
    df_2024_total = df_2024_ze.groupby('ZE2020')['OBS_VALUE'].sum().reset_index().rename(columns={'OBS_VALUE': 'total_establishments'})
    df_2024_ze = df_2024_ze.merge(df_2024_total, on='ZE2020')
    df_2024_ze['weight'] = df_2024_ze['OBS_VALUE'] / df_2024_ze['total_establishments']

    df_2024_profile = df_2024_ze.pivot(index='ZE2020', columns='ACTIVITY', values='weight').fillna(0)
    df_2024_profile.columns = [f"weight_a17_{c}" for c in df_2024_profile.columns]
    df_2024_profile['total_establishments'] = df_2024_total.set_index('ZE2020')['total_establishments']
    df_2024_profile['year_profile'] = 2024

    # 2. Process Historical (Wide Format)
    historical_files = {
        2017: 'data/raw/employment/flores/TD_FLORES2017_NA17_TREF_NBETAB_CSV.zip',
        2018: 'data/raw/employment/flores/TD_FLORES2018_NA17_TREF_NBETAB_CSV.zip',
        2019: 'data/raw/employment/flores/TD_FLORES2019_NA17_TREF_NBETAB_CSV.zip',
        2020: 'data/raw/employment/flores/TD_FLORES2020_NA17_TREF_NBETAB_CSV.zip',
        2021: 'data/raw/employment/flores/TD_FLORES2021_NA17_TREF_NBETAB_csv.zip'
    }

    profiles = [df_2024_profile.reset_index()]

    for yr, path in historical_files.items():
        print(f"Processing {yr} from {path}...")
        csv_name = os.path.basename(path).replace('_CSV.zip', '.csv').replace('_csv.zip', '.csv')

        with zipfile.ZipFile(path) as z:
            with z.open(csv_name) as f:
                df_yr = pd.read_csv(f, sep=';', dtype={'CODGEO': str})

        # Columns are ET_AZ, ET_DE, ET_C1, etc. and ET_TOT
        # We want the ET_XX columns (excluding ET_TOT and subgroups like ET_XX_0sal)
        cols = [c for c in df_yr.columns if c.startswith('ET_') and '_' not in c[3:] and c != 'ET_TOT']
        df_yr_filtered = df_yr[['CODGEO', 'ET_TOT'] + cols]

        df_yr_joined = df_yr_filtered.merge(df_mapping[['CODGEO', 'ZE2020']], on='CODGEO', how='inner')
        df_ze = df_yr_joined.groupby('ZE2020')[['ET_TOT'] + cols].sum().reset_index()

        # Calculate weights
        for c in cols:
            activity = c[3:] # ET_AZ -> AZ
            df_ze[f"weight_a17_{activity}"] = df_ze[c] / df_ze['ET_TOT']

        df_profile_yr = df_ze[['ZE2020', 'ET_TOT'] + [f"weight_a17_{c[3:]}" for c in cols]]
        df_profile_yr = df_profile_yr.rename(columns={'ET_TOT': 'total_establishments'})
        df_profile_yr['year_profile'] = yr
        profiles.append(df_profile_yr)

    df_all_profiles = pd.concat(profiles, ignore_index=True)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_all_profiles.to_csv(output_path, index=False)
    print(f"Saved historical profiles to {output_path}")

    # Quality Report (on the latest)
    quality = {
        "years_available": sorted(df_all_profiles['year_profile'].unique().tolist()),
        "zones_count": int(df_all_profiles['ZE2020'].nunique()),
        "total_rows": len(df_all_profiles)
    }
    with open(quality_report_path, 'w') as f:
        json.dump(quality, f, indent=4)

if __name__ == "__main__":
    build_zone_sectoral_profile_history()
