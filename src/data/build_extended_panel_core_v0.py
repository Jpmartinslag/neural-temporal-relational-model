import pandas as pd
import numpy as np
import os

def build_extended_panel():
    # Paths
    pop_path = 'data/interim/tables/population_history_annual_ze2020_v0.csv'
    side_target_path = 'data/processed/target_side_establishments_annual_core_v0.csv'
    regime_path = 'data/interim/tables/leading_regime_signal_extended_v0.csv'
    node_index_path = 'data/processed/graph_node_index_core_v0.csv'
    adj_geo_path = 'data/processed/graph_adjacency_core_v0.csv'
    adj_mob_path = 'data/processed/graph_adjacency_mobility_v0.csv'
    profile_hist_path = 'data/interim/tables/zone_sectoral_profile_history_v0.csv'
    stock_hist_path = 'data/interim/tables/establishment_stock_history_v0.csv'
    sitadel_path = 'data/interim/tables/sitadel_surface_ze2020_v0.csv'

    output_path = 'data/processed/extended_panel_core_v0.csv'

    # 1. Load Node Index
    df_nodes = pd.read_csv(node_index_path, dtype={'ze2020': str})

    # 2. Load and Melt Population
    df_pop = pd.read_csv(pop_path, dtype={'ZE2020': str})
    df_pop_melted = df_pop.melt(id_vars='ZE2020', var_name='year', value_name='population')
    df_pop_melted['year'] = df_pop_melted['year'].astype(int)

    # 3. Load SIDE Target
    df_side = pd.read_csv(side_target_path, dtype={'ze2020': str})

    # 4. Load Regime Signals
    df_regime = pd.read_csv(regime_path, dtype={'ZE2020': str})

    # 5. Load Sectoral Profile History
    df_profile_hist = pd.read_csv(profile_hist_path, dtype={'ZE2020': str})

    # 6. Load Stock History
    df_stock_hist = pd.read_csv(stock_hist_path, dtype={'ZE2020': str})

    # 7. Load SITADEL surfaces. They are used only with a lag to avoid using
    # construction permissions from the same target year.
    df_sitadel = pd.read_csv(sitadel_path, dtype={'ZE2020': str})

    # 8. Create Base Grid (2012-2024)
    years = range(2012, 2025)
    grid = []
    for yr in years:
        df_yr_nodes = df_nodes.copy()
        df_yr_nodes['year'] = yr
        grid.append(df_yr_nodes)
    df_base = pd.concat(grid)

    # 9. Merge features
    # Target
    df_base = df_base.merge(
        df_side[['ze2020', 'target_year', 'side_establishment_creations_official']],
        left_on=['ze2020', 'year'],
        right_on=['ze2020', 'target_year'],
        how='left'
    ).drop(columns=['target_year'])

    # Regime Signals
    df_base = df_base.merge(df_regime, left_on=['ze2020', 'year'], right_on=['ZE2020', 'year'], how='left').drop(columns=['ZE2020'])

    # Historical Profile
    available_profile_yrs = sorted(df_profile_hist['year_profile'].unique())
    profile_merge_list = []
    for yr in years:
        past_p_yrs = [y for y in available_profile_yrs if y < yr]
        if not past_p_yrs: continue
        best_p_yr = max(past_p_yrs)
        df_p = df_profile_hist[df_profile_hist['year_profile'] == best_p_yr].copy()
        df_p['year'] = yr
        profile_merge_list.append(df_p)

    if profile_merge_list:
        df_profiles_to_merge = pd.concat(profile_merge_list).rename(columns={'ZE2020': 'ze2020'})
        df_base = df_base.merge(df_profiles_to_merge, on=['ze2020', 'year'], how='left')

    # `year_profile` is audit metadata, not an economic predictor.
    if 'year_profile' in df_base.columns:
        df_base = df_base.drop(columns=['year_profile'])

    # Stock
    df_stock_to_merge = df_stock_hist.copy()
    df_stock_to_merge['year_to_merge'] = df_stock_to_merge['year'] + 1
    df_base = df_base.merge(
        df_stock_to_merge[['ZE2020', 'year_to_merge', 'stock']],
        left_on=['ze2020', 'year'],
        right_on=['ZE2020', 'year_to_merge'],
        how='left'
    ).drop(columns=['ZE2020', 'year_to_merge']).rename(columns={'stock': 'stock_lag_1'})

    # SITADEL lagged local construction pressure.
    df_sitadel_to_merge = df_sitadel.copy()
    df_sitadel_to_merge['year_to_merge'] = df_sitadel_to_merge['year'] + 1
    df_base = df_base.merge(
        df_sitadel_to_merge[
            [
                'ZE2020',
                'year_to_merge',
                'sitadel_surface_autorisee',
                'sitadel_surface_commencee',
            ]
        ],
        left_on=['ze2020', 'year'],
        right_on=['ZE2020', 'year_to_merge'],
        how='left',
    ).drop(columns=['ZE2020', 'year_to_merge']).rename(
        columns={
            'sitadel_surface_autorisee': 'sitadel_surface_autorisee_lag_1',
            'sitadel_surface_commencee': 'sitadel_surface_commencee_lag_1',
        }
    )

    # 9. Add Lagged Features
    df_base = df_base.sort_values(['ze2020', 'year'])
    df_base['side_creations_lag_1'] = df_base.groupby('ze2020')['side_establishment_creations_official'].shift(1)

    # Population Lags
    df_base = df_base.merge(df_pop_melted, left_on=['ze2020', 'year'], right_on=['ZE2020', 'year'], how='left').drop(columns=['ZE2020'])
    df_base['pop_lag_1'] = df_base.groupby('ze2020')['population'].shift(1)
    df_base['pop_lag_2'] = df_base.groupby('ze2020')['population'].shift(2)
    df_base = df_base.drop(columns=['population'])

    # 10. Spatial Lags (Geo and Mobility)
    def calculate_spatial_lag(df, adj_path, feat_col, out_col):
        adj_df = pd.read_csv(adj_path)
        # Handle index for mobility (it's columns 0..279)
        if 'source_idx' in adj_df.columns:
            adj_matrix = adj_df.set_index('source_idx').to_numpy()
        else:
            adj_matrix = adj_df.to_numpy()

        adj_sum = adj_matrix.sum(axis=1, keepdims=True)
        adj_sum[adj_sum == 0] = 1.0
        adj_norm = adj_matrix / adj_sum

        all_lags = []
        for yr in df['year'].unique():
            df_yr = df[df['year'] == yr].sort_values('node_idx').copy()
            vals = df_yr[feat_col].to_numpy()
            vals_clean = np.where(np.isfinite(vals), vals, 0.0)
            spatial_lag = adj_norm @ vals_clean
            df_yr[out_col] = spatial_lag
            all_lags.append(df_yr)
        return pd.concat(all_lags)

    # Calculate Geo Spatial Lag
    df_base = calculate_spatial_lag(df_base, adj_geo_path, 'side_creations_lag_1', 'side_creations_spatial_lag_1')
    # Calculate Mobility Spatial Lag
    df_base = calculate_spatial_lag(df_base, adj_mob_path, 'side_creations_lag_1', 'side_creations_mobility_lag_1')

    # 11. Final Cut
    df_base = df_base[df_base['year'] >= 2018].copy()

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_base.to_csv(output_path, index=False)

    print(f"Saved extended panel (v5) with mobility and lagged SITADEL features to {output_path}")
    print(f"Observations: {len(df_base)}")

if __name__ == "__main__":
    build_extended_panel()
