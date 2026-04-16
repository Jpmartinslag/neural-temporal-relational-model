import pandas as pd
import zipfile
import os
import json

def build_population_history_annual():
    # Paths
    pop_path = 'data/raw/population/DS_POPULATIONS_HISTORIQUES_CSV_FR.zip'
    mapping_path = 'data/interim/mappings/commune_to_ze2020_2026.csv'
    output_path = 'data/interim/tables/population_history_annual_ze2020_v0.csv'
    quality_report_path = 'reports/population_history_annual_quality_v0.json'

    print(f"Reading Population History from {pop_path}...")

    # 1. Read Mapping
    df_mapping = pd.read_csv(mapping_path, dtype={'CODGEO': str, 'ZE2020': str})

    # 2. Read Population Data
    # Columns: "FREQ";"GEO";"GEO_OBJECT";"POPREF_MEASURE";"TIME_PERIOD";"OBS_VALUE"
    with zipfile.ZipFile(pop_path) as z:
        with z.open('DS_POPULATIONS_HISTORIQUES_data.csv') as f:
            df_pop = pd.read_csv(f, sep=';', dtype={'GEO': str, 'TIME_PERIOD': int, 'OBS_VALUE': float})

    # Filter for Municipal Population (PMUN) at Commune level
    mask = (df_pop['GEO_OBJECT'] == 'COM') & (df_pop['POPREF_MEASURE'] == 'PMUN')
    df_filtered = df_pop[mask][['GEO', 'TIME_PERIOD', 'OBS_VALUE']]

    # 3. Aggregate to ZE2020
    df_joined = df_filtered.merge(df_mapping[['CODGEO', 'ZE2020']], left_on='GEO', right_on='CODGEO', how='inner')
    df_ze_pop = df_joined.groupby(['ZE2020', 'TIME_PERIOD'])['OBS_VALUE'].sum().reset_index()

    # Pivot to have years as columns
    df_pivot = df_ze_pop.pivot(index='ZE2020', columns='TIME_PERIOD', values='OBS_VALUE')

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_pivot.to_csv(output_path)
    print(f"Saved annual population history to {output_path}")

    # 4. Quality Report
    quality = {
        "zones_count": len(df_pivot),
        "years_covered": sorted(df_ze_pop['TIME_PERIOD'].unique().tolist()),
        "total_population_2023": float(df_ze_pop[df_ze_pop['TIME_PERIOD'] == 2023]['OBS_VALUE'].sum())
    }

    with open(quality_report_path, 'w') as f:
        json.dump(quality, f, indent=4)
    print(f"Saved quality report to {quality_report_path}")

if __name__ == "__main__":
    build_population_history_annual()
