import pandas as pd
import os
import json

def build_sitadel_surface():
    input_path = 'data/raw/external/sitadel/Donnees-annuelles-communales-Locaux.2026-04.csv'
    mapping_path = 'data/interim/mappings/commune_to_ze2020_2026.csv'
    output_path = 'data/interim/tables/sitadel_surface_ze2020_v0.csv'
    quality_report_path = 'reports/sitadel_surface_quality_v0.json'

    print("Loading mapping...")
    df_mapping = pd.read_csv(mapping_path, dtype={'CODGEO': str, 'ZE2020': str})

    print(f"Loading SITADEL data from {input_path}...")
    # Skip the first row which is the human-readable header, keep the second row as header
    df = pd.read_csv(input_path, sep=';', skiprows=1, dtype={'COMM': str, 'ANNEE': int})

    # Filter non-residential total
    df_filtered = df[df['DESTINATION'] == 'Ensemble des locaux non-residentiels'].copy()

    # Handle NaNs and string representations of numbers in surfaces
    for col in ['SDP_AUT', 'SDP_COM']:
        if df_filtered[col].dtype == object:
            df_filtered[col] = pd.to_numeric(df_filtered[col].str.replace(',', '.'), errors='coerce')

    df_filtered['SDP_AUT'] = df_filtered['SDP_AUT'].fillna(0.0)
    df_filtered['SDP_COM'] = df_filtered['SDP_COM'].fillna(0.0)

    # Merge with ZE2020 mapping
    df_joined = df_filtered.merge(df_mapping[['CODGEO', 'ZE2020']], left_on='COMM', right_on='CODGEO', how='inner')

    # Aggregate by ZE2020 and ANNEE
    df_ze = df_joined.groupby(['ZE2020', 'ANNEE'])[['SDP_AUT', 'SDP_COM']].sum().reset_index()
    df_ze = df_ze.rename(columns={'ANNEE': 'year', 'SDP_AUT': 'sitadel_surface_autorisee', 'SDP_COM': 'sitadel_surface_commencee'})

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_ze.to_csv(output_path, index=False)
    print(f"Saved SITADEL surfaces to {output_path}")

    # Quality Report
    quality = {
        "years_available": sorted(df_ze['year'].unique().tolist()),
        "zones_count": int(df_ze['ZE2020'].nunique()),
        "total_rows": len(df_ze)
    }

    with open(quality_report_path, 'w') as f:
        json.dump(quality, f, indent=4)

if __name__ == "__main__":
    build_sitadel_surface()
