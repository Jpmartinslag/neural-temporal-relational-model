import pandas as pd
import numpy as np
import zipfile
import os

def build_mobility_adjacency():
    # Paths
    mobility_path = 'data/raw/temporal_depth/rp/base-flux-mobilite-domicile-lieu-travail-2021-csv.zip'
    mapping_path = 'data/interim/mappings/commune_to_ze2020_2026.csv'
    node_index_path = 'data/processed/graph_node_index_core_v0.csv'
    output_path = 'data/processed/graph_adjacency_mobility_v0.csv'

    # 1. Load Mappings
    df_mapping = pd.read_csv(mapping_path, dtype={'CODGEO': str, 'ZE2020': str})
    df_nodes = pd.read_csv(node_index_path, dtype={'ze2020': str})
    core_ze = set(df_nodes['ze2020'])
    ze_to_idx = {ze: idx for idx, ze in enumerate(df_nodes['ze2020'])}

    # 2. Load Mobility and Aggregate
    flux_data = []
    with zipfile.ZipFile(mobility_path) as z:
        with z.open('base-flux-mobilite-domicile-lieu-travail-2021.csv') as f:
            # NBFLUX_C21_ACTOCC15P is the weight
            for chunk in pd.read_csv(f, sep=';', dtype={'CODGEO': str, 'DCLT': str, 'NBFLUX_C21_ACTOCC15P': float}, chunksize=500000):
                # Map Residence
                chunk = chunk.merge(df_mapping[['CODGEO', 'ZE2020']], on='CODGEO', how='inner')
                chunk = chunk.rename(columns={'ZE2020': 'ZE_RES'})
                # Map Workplace
                chunk = chunk.merge(df_mapping[['CODGEO', 'ZE2020']], left_on='DCLT', right_on='CODGEO', how='inner')
                chunk = chunk.rename(columns={'ZE2020': 'ZE_WORK'}).drop(columns=['CODGEO_y'])

                # Filter for core zones and exclude self-loops
                mask = (chunk['ZE_RES'].isin(core_ze)) & (chunk['ZE_WORK'].isin(core_ze)) & (chunk['ZE_RES'] != chunk['ZE_WORK'])
                flux_data.append(chunk[mask][['ZE_RES', 'ZE_WORK', 'NBFLUX_C21_ACTOCC15P']])

    df_flux = pd.concat(flux_data)
    df_ze_flux = df_flux.groupby(['ZE_RES', 'ZE_WORK'])['NBFLUX_C21_ACTOCC15P'].sum().reset_index()

    # 3. Build Matrix
    n = len(df_nodes)
    adj = np.zeros((n, n))

    for _, row in df_ze_flux.iterrows():
        i = ze_to_idx[row['ZE_RES']]
        j = ze_to_idx[row['ZE_WORK']]
        adj[i, j] = row['NBFLUX_C21_ACTOCC15P']

    # Symmetrize (optional, but for mobility usually we want undirected or directed.
    # Let's keep it directed for now: from RES to WORK).

    # Row-normalize
    row_sums = adj.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    adj_norm = adj / row_sums

    # 4. Save
    # We save in the same format as geographic adjacency
    df_out = pd.DataFrame(adj_norm)
    df_out.index.name = 'source_idx'
    df_out.to_csv(output_path)

    print(f"Saved mobility adjacency matrix to {output_path}")
    print(f"Matrix shape: {adj_norm.shape}")
    print(f"Mean connections per node: {(adj_norm > 0).sum() / n:.2f}")

if __name__ == "__main__":
    build_mobility_adjacency()
