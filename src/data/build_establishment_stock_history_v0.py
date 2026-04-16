import pandas as pd
import zipfile
import os
import json

def build_establishment_stock_history():
    # Paths
    side_stocks_2022_path = 'data/raw/business_demography/side/DS_SIDE_STOCKS_ET_COM_2022_CSV.zip'
    side_stocks_2023_path = 'data/raw/business_demography/side/DS_SIDE_STOCKS_ET_COM_2023_CSV.zip'
    flores_stocks_path = 'data/interim/tables/zone_sectoral_profile_history_v0.csv'
    mapping_path = 'data/interim/mappings/commune_to_ze2020_2026.csv'
    output_path = 'data/interim/tables/establishment_stock_history_v0.csv'

    # 1. Load FLORES Stock (2017-2021)
    df_flores = pd.read_csv(flores_stocks_path, dtype={'ZE2020': str})
    df_flores_stock = df_flores[['ZE2020', 'year_profile', 'total_establishments']].copy()
    df_flores_stock = df_flores_stock.rename(columns={'year_profile': 'year', 'total_establishments': 'stock'})
    df_flores_stock = df_flores_stock[df_flores_stock['year'] < 2022]

    # 2. Load SIDE Stock
    df_mapping = pd.read_csv(mapping_path, dtype={'CODGEO': str, 'ZE2020': str})

    side_data = []

    # 2022 File
    with zipfile.ZipFile(side_stocks_2022_path) as z:
        with z.open('DS_SIDE_STOCKS_ET_COM_data.csv') as f:
            for chunk in pd.read_csv(f, sep=';', dtype={'GEO': str, 'TIME_PERIOD': int, 'OBS_VALUE': float}, chunksize=500000):
                mask = (chunk['GEO_OBJECT'] == 'COM') & (chunk['ACTIVITY'] == '_T') & (chunk['TIME_PERIOD'] == 2022)
                side_data.append(chunk[mask][['GEO', 'TIME_PERIOD', 'OBS_VALUE']])

    # 2023 File
    with zipfile.ZipFile(side_stocks_2023_path) as z:
        with z.open('DS_SIDE_STOCKS_ET_COM_2023_data.csv') as f:
            for chunk in pd.read_csv(f, sep=';', dtype={'GEO': str, 'TIME_PERIOD': int, 'OBS_VALUE': float}, chunksize=500000):
                mask = (chunk['GEO_OBJECT'] == 'COM') & (chunk['ACTIVITY'] == '_T') & (chunk['TIME_PERIOD'] == 2023)
                side_data.append(chunk[mask][['GEO', 'TIME_PERIOD', 'OBS_VALUE']])

    df_side_raw = pd.concat(side_data)
    df_side_joined = df_side_raw.merge(df_mapping[['CODGEO', 'ZE2020']], left_on='GEO', right_on='CODGEO', how='inner')
    df_side_ze = df_side_joined.groupby(['ZE2020', 'TIME_PERIOD'])['OBS_VALUE'].sum().reset_index()
    df_side_ze = df_side_ze.rename(columns={'TIME_PERIOD': 'year', 'OBS_VALUE': 'stock'})

    # 3. Combine
    df_total_stock = pd.concat([df_flores_stock, df_side_ze], ignore_index=True)
    df_total_stock = df_total_stock.sort_values(['ZE2020', 'year'])

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_total_stock.to_csv(output_path, index=False)
    print(f"Saved stock history to {output_path}")
    print(f"Years covered: {sorted(df_total_stock['year'].unique())}")

if __name__ == "__main__":
    build_establishment_stock_history()
