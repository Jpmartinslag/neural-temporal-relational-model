"""
HERALD Intelligence Layer - Generator
Produces all indicator CSVs from available data.

CONFIGURATION — update these paths when the final HPC battery is ready:
  HERALD_PRED_DIR : folder with herald_*_predictions_total_*_seed_*.csv
  FORECAST_DIR    : folder with herald_forecast_total_*_seed_*.csv
  HERALD_MODEL_TAG: grep pattern to select the right model variant

Current prototype uses the most recent available validated run.
Regenerate after final HPC battery is consolidated.
"""
import pandas as pd
import numpy as np
import os
import glob

BASE = "/home/jpdark/Downloads/project_recomm/dataset"

# ── PATHS TO UPDATE when final run is ready ───────────────────────────────────
# Current: run validated 2026-04-30, 7 seeds, geo2025, observed2025
HERALD_PRED_DIR = "/home/jpdark/Downloads/project_recomm/v6_results_20260430/herald_v6_observed2025_geo2025_7267235/data_processed"
HERALD_PRED_TOTAL_PATTERN = "herald_v6_predictions_total_*_seed_*_v1.csv"
HERALD_PRED_SECTOR_PATTERN = "herald_v6_predictions_sector_*_seed_*_v1.csv"
HERALD_SEED_PARSE = lambda f: int(f.split("_seed_")[-1].replace("_v1.csv", ""))

# Forecast directory (2026-2027 prospective)
FORECAST_DIR = os.path.join(BASE, "hpc_results/herald_forecast_20260506_forecast_after_strict/data_processed")
FORECAST_TOTAL_PATTERN = "herald_forecast_total_lag_only_v6_full_forecast_2026_2027_seed_*_v1.csv"
FORECAST_SECTOR_PATTERN = "herald_forecast_sector_lag_only_v6_full_forecast_2026_2027_seed_*_v1.csv"
FORECAST_SEED_PARSE = lambda f: int(f.split("_seed_")[-1].replace("_v1.csv", ""))
# ─────────────────────────────────────────────────────────────────────────────

OUT_DIR = os.path.join(BASE, "reports/metrics/herald_intelligence")

SECTORS_A10 = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

# ─── LOAD DATA ──────────────────────────────────────────────────────────────

def load_observed():
    df = pd.read_csv(os.path.join(BASE, "data/processed/target_side_establishments_annual_core_through_2025_v1.csv"))
    df = df.rename(columns={"ze2020": "ZE2020"})
    df["ZE2020"] = df["ZE2020"].astype(int)
    return df[["target_year", "ZE2020", "libze2020", "side_establishment_creations_official"]]

def load_observed_a10():
    df = pd.read_csv(os.path.join(BASE, "data/processed/side_creations_a10_ze2020_through_2025_v1.csv"))
    df["ZE2020"] = df["ZE2020"].astype(int)
    return df

def load_v6_predictions():
    """Load HERALD predictions (all seeds), compute mean/std across seeds."""
    dfs = []
    for seed_file in glob.glob(os.path.join(HERALD_PRED_DIR, HERALD_PRED_TOTAL_PATTERN)):
        seed = HERALD_SEED_PARSE(seed_file)
        df = pd.read_csv(seed_file)
        df["seed"] = seed
        dfs.append(df)
    if not dfs:
        raise FileNotFoundError(f"No HERALD prediction files found in {HERALD_PRED_DIR!r}. Update HERALD_PRED_DIR.")
    all_preds = pd.concat(dfs, ignore_index=True)
    agg = all_preds.groupby(["target_year", "ZE2020"]).agg(
        y_true=("y_true", "first"),
        y_pred_mean=("y_pred", "mean"),
        y_pred_std=("y_pred", "std"),
        y_pred_min=("y_pred", "min"),
        y_pred_max=("y_pred", "max"),
        n_seeds=("seed", "count"),
    ).reset_index()
    return agg

def load_v6_sector_predictions():
    dfs = []
    for f in glob.glob(os.path.join(HERALD_PRED_DIR, HERALD_PRED_SECTOR_PATTERN)):
        seed = HERALD_SEED_PARSE(f)
        df = pd.read_csv(f)
        df["seed"] = seed
        dfs.append(df)
    if not dfs:
        return None
    all_preds = pd.concat(dfs, ignore_index=True)
    agg = all_preds.groupby(["target_year", "ZE2020", "sector"]).agg(
        y_true_sector=("y_true_sector", "first"),
        y_pred_sector_mean=("y_pred_sector", "mean"),
        y_pred_sector_std=("y_pred_sector", "std"),
        prop_pred_mean=("prop_pred", "mean"),
    ).reset_index()
    return agg

def load_baselines():
    df = pd.read_csv(os.path.join(BASE, "data/processed/dynamic_feature_panel_baseline_predictions_v1.csv"))
    df["ZE2020"] = df["ZE2020"].astype(int)
    return df

def load_forecast_zone():
    """Load 2026/2027 total forecast (HERALD principal, lag_only panel)."""
    dfs = []
    pattern = os.path.join(FORECAST_DIR, FORECAST_TOTAL_PATTERN)
    for f in glob.glob(pattern):
        seed = FORECAST_SEED_PARSE(f)
        df = pd.read_csv(f)
        df["seed"] = seed
        dfs.append(df)
    if not dfs:
        return None
    all_fc = pd.concat(dfs, ignore_index=True)
    agg = all_fc.groupby(["target_year", "ZE2020"]).agg(
        y_pred_mean=("y_pred", "mean"),
        y_pred_std=("y_pred", "std"),
        ridge_pred_mean=("ridge_pred", "mean"),
        n_seeds=("seed", "count"),
    ).reset_index()
    return agg

def load_forecast_sector():
    dfs = []
    pattern = os.path.join(FORECAST_DIR, FORECAST_SECTOR_PATTERN)
    for f in glob.glob(pattern):
        seed = FORECAST_SEED_PARSE(f)
        df = pd.read_csv(f)
        df["seed"] = seed
        dfs.append(df)
    if not dfs:
        return None
    all_fc = pd.concat(dfs, ignore_index=True)
    agg = all_fc.groupby(["target_year", "ZE2020", "sector"]).agg(
        y_pred_total_mean=("y_pred_total", "mean"),
        y_pred_sector_mean=("y_pred_sector", "mean"),
        prop_pred_mean=("prop_pred", "mean"),
    ).reset_index()
    return agg

def load_graph():
    edges = pd.read_csv(os.path.join(BASE, "data/processed/graph_edges_ze2020_core_v0.csv"))
    adj_mob = pd.read_csv(os.path.join(BASE, "data/processed/graph_adjacency_mobility_v0.csv"))
    nodes = pd.read_csv(os.path.join(BASE, "data/processed/graph_nodes_ze2020_core_v0.csv"))
    nodes["ze2020"] = nodes["ze2020"].astype(int)
    return edges, adj_mob, nodes

# ─── COMPUTE INDICATORS ─────────────────────────────────────────────────────

def compute_historical_stats(obs):
    """Mean, std, growth per zone over 2012-2020 (pre-covid baseline)."""
    hist = obs[obs["target_year"].between(2012, 2020)].copy()
    stats = hist.groupby("ZE2020").agg(
        hist_mean=("side_establishment_creations_official", "mean"),
        hist_std=("side_establishment_creations_official", "std"),
        hist_min=("side_establishment_creations_official", "min"),
        hist_max=("side_establishment_creations_official", "max"),
        libze2020=("libze2020", "first"),
    ).reset_index()
    # Growth trend: 2017-2020 vs 2012-2016
    pre = hist[hist["target_year"].between(2012, 2016)].groupby("ZE2020")["side_establishment_creations_official"].mean()
    post = hist[hist["target_year"].between(2017, 2020)].groupby("ZE2020")["side_establishment_creations_official"].mean()
    stats = stats.merge(
        (((post - pre) / pre.replace(0, np.nan)) * 100).rename("hist_growth_trend_pct").reset_index(),
        on="ZE2020", how="left"
    )
    return stats

def compute_national_percentiles(v6_preds, obs, year=2025):
    """National distribution for a given year."""
    obs_yr = obs[obs["target_year"] == year]["side_establishment_creations_official"]
    pred_yr = v6_preds[v6_preds["target_year"] == year]["y_pred_mean"]
    national_stats = {
        "obs_national_mean": obs_yr.mean(),
        "obs_national_p10": obs_yr.quantile(0.10),
        "obs_national_p25": obs_yr.quantile(0.25),
        "obs_national_p50": obs_yr.quantile(0.50),
        "obs_national_p75": obs_yr.quantile(0.75),
        "obs_national_p90": obs_yr.quantile(0.90),
        "pred_national_mean": pred_yr.mean(),
    }
    return national_stats

def compute_herald_error(v6_preds, baselines):
    """
    Historical error per zone.

    Alignment rule: HERALD vs Ridge comparison uses ONLY years where both have
    predictions. herald_wmape_all uses all available HERALD years; the
    comparative herald_wmape_aligned uses only the Ridge intersection.
    """
    ridge = baselines[baselines["model"] == "Ridge_AR"].copy()
    ridge_years = sorted(ridge["target_year"].unique())
    herald_years = sorted(v6_preds["target_year"].unique())
    shared_years = sorted(set(ridge_years) & set(herald_years))

    # HERALD error — all validated years (for reference)
    v6_all = v6_preds.copy()
    v6_all["ape"] = np.abs(v6_all["y_pred_mean"] - v6_all["y_true"]) / v6_all["y_true"].replace(0, np.nan) * 100
    herald_err_all = v6_all.groupby("ZE2020").agg(
        herald_wmape_all=("ape", "mean"),
        herald_n_years=("target_year", "count"),
    ).reset_index()

    # HERALD error — aligned years only (same as Ridge)
    v6_aligned = v6_preds[v6_preds["target_year"].isin(shared_years)].copy()
    v6_aligned["ape"] = np.abs(v6_aligned["y_pred_mean"] - v6_aligned["y_true"]) / v6_aligned["y_true"].replace(0, np.nan) * 100
    herald_err_aligned = v6_aligned.groupby("ZE2020").agg(
        herald_wmape_aligned=("ape", "mean"),
    ).reset_index()

    # Ridge error — aligned years
    ridge["ape"] = np.abs(ridge["y_pred"] - ridge["y_true"]) / ridge["y_true"].replace(0, np.nan) * 100
    ridge_err = ridge.groupby("ZE2020").agg(
        ridge_wmape=("ape", "mean"),
        ridge_n_years=("target_year", "count"),
    ).reset_index()

    err = herald_err_all.merge(herald_err_aligned, on="ZE2020", how="left")
    err = err.merge(ridge_err, on="ZE2020", how="left")
    # Comparison uses aligned years only
    err["herald_vs_ridge_pct"] = (err["herald_wmape_aligned"] - err["ridge_wmape"]) / err["ridge_wmape"].replace(0, np.nan) * 100
    # Expose shared years info for transparency
    err["comparison_years"] = str(shared_years)
    err["herald_only_years"] = str([y for y in herald_years if y not in shared_years])
    # Convenience alias used downstream
    err["herald_wmape"] = err["herald_wmape_all"]
    err["comparison_status"] = np.where(
        err["ridge_n_years"].notna() & (err["ridge_n_years"] > 0),
        "comparable_ridge_ar",
        "herald_only_no_baseline"
    )
    return err

def compute_growth_indicators(v6_preds, obs, forecast_zone, hist_stats):
    """
    Core growth indicators for the intelligence layer.
    Focus on 2025 (last observed) and 2026 (next forecast).
    """
    # Observed growth 2024->2025
    obs_2024 = obs[obs["target_year"] == 2024][["ZE2020", "side_establishment_creations_official"]].rename(columns={"side_establishment_creations_official": "obs_2024"})
    obs_2025 = obs[obs["target_year"] == 2025][["ZE2020", "side_establishment_creations_official"]].rename(columns={"side_establishment_creations_official": "obs_2025"})

    # Predicted 2025
    pred_2025 = v6_preds[v6_preds["target_year"] == 2025][["ZE2020", "y_pred_mean", "y_pred_std"]].rename(
        columns={"y_pred_mean": "pred_2025_mean", "y_pred_std": "pred_2025_std"})

    # Forecast 2026/2027
    if forecast_zone is not None:
        fc_2026 = forecast_zone[forecast_zone["target_year"] == 2026][["ZE2020", "y_pred_mean", "y_pred_std", "ridge_pred_mean"]].rename(
            columns={"y_pred_mean": "fc_2026_mean", "y_pred_std": "fc_2026_std", "ridge_pred_mean": "fc_2026_ridge"})
        fc_2027 = forecast_zone[forecast_zone["target_year"] == 2027][["ZE2020", "y_pred_mean", "y_pred_std"]].rename(
            columns={"y_pred_mean": "fc_2027_mean", "y_pred_std": "fc_2027_std"})
    else:
        fc_2026 = pd.DataFrame(columns=["ZE2020", "fc_2026_mean", "fc_2026_std", "fc_2026_ridge"])
        fc_2027 = pd.DataFrame(columns=["ZE2020", "fc_2027_mean", "fc_2027_std"])

    df = obs_2024.merge(obs_2025, on="ZE2020").merge(pred_2025, on="ZE2020", how="left")
    if len(fc_2026):
        df = df.merge(fc_2026, on="ZE2020", how="left").merge(fc_2027, on="ZE2020", how="left")
    df = df.merge(hist_stats[["ZE2020", "hist_mean", "hist_std", "libze2020"]], on="ZE2020", how="left")

    # Growth rates
    df["obs_growth_2024_2025_pct"] = (df["obs_2025"] - df["obs_2024"]) / df["obs_2024"].replace(0, np.nan) * 100
    df["pred_growth_vs_hist_pct"] = (df["pred_2025_mean"] - df["hist_mean"]) / df["hist_mean"].replace(0, np.nan) * 100

    if "fc_2026_mean" in df.columns:
        df["fc_growth_2025_2026_pct"] = (df["fc_2026_mean"] - df["obs_2025"]) / df["obs_2025"].replace(0, np.nan) * 100
        df["fc_acceleration_2026_vs_hist_pct"] = (df["fc_2026_mean"] - df["hist_mean"]) / df["hist_mean"].replace(0, np.nan) * 100
        df["fc_uncertainty_cv"] = df["fc_2026_std"] / df["fc_2026_mean"].replace(0, np.nan)
    if "fc_2027_mean" in df.columns:
        df["fc_growth_2026_2027_pct"] = (df["fc_2027_mean"] - df.get("fc_2026_mean", np.nan)) / df.get("fc_2026_mean", pd.Series(np.nan, index=df.index)).replace(0, np.nan) * 100

    # National context (2025)
    nat_mean_obs = df["obs_2025"].mean()
    nat_std_obs = df["obs_2025"].std()
    df["obs_2025_vs_national_pct"] = (df["obs_2025"] - nat_mean_obs) / nat_mean_obs * 100
    df["obs_2025_national_rank"] = df["obs_2025"].rank(ascending=False).astype(int)
    df["obs_2025_percentile"] = df["obs_2025"].rank(pct=True) * 100

    if "fc_2026_mean" in df.columns:
        nat_mean_fc = df["fc_2026_mean"].mean()
        df["fc_2026_vs_national_pct"] = (df["fc_2026_mean"] - nat_mean_fc) / nat_mean_fc * 100
        df["fc_2026_national_rank"] = df["fc_2026_mean"].rank(ascending=False).astype(int)
        df["fc_2026_percentile"] = df["fc_2026_mean"].rank(pct=True) * 100

    return df

def compute_graph_dependency(adj_mob, nodes):
    """
    Compute territorial dependency indicators from the mobility PRIOR matrix.

    Important: this uses the static commuting-flow prior (INSEE recensement,
    ~2016-2019), NOT the dynamic adjacency learned by HERALD. To use the
    learned graph, extract `dynamic_adj[-1]` from the HERALD internals NPZ
    (key: `dynamic_adj`, shape: [T, 280, 280], last slice = most recent year).
    Until that extraction is implemented, results are labeled `graph_source:
    mobility_prior` and must not be described as "poids appris par HERALD".
    """
    node_order = nodes["ze2020"].values

    mob_matrix = adj_mob.drop(columns=["source_idx"]).values.astype(float)
    # Build a lookup for node index → ze2020 code
    idx_to_ze = {i: int(ze) for i, ze in enumerate(node_order)}

    records = []
    for i, ze in enumerate(node_order):
        row = mob_matrix[i].copy()
        self_weight = float(mob_matrix[i, i])
        row[i] = 0  # exclude self for neighbor ranking
        top_idx = np.argsort(row)[::-1][:5]
        top_weights = row[top_idx]
        top_ze = [idx_to_ze.get(j, -1) for j in top_idx]
        top_names = []
        for tz in top_ze:
            name_row = nodes[nodes["ze2020"] == tz]["libze2020"]
            top_names.append(name_row.values[0] if len(name_row) else str(tz))

        total_out = row.sum()
        top3_weight = row[top_idx[:3]].sum()
        concentration = float(top3_weight / total_out) if total_out > 0 else 0.0

        records.append({
            "ZE2020": int(ze),
            "graph_source": "mobility_prior",  # NOT the learned graph — see docstring
            "self_weight": self_weight,
            "top1_ze": top_ze[0] if top_ze else None,
            "top1_name": top_names[0] if top_names else None,
            "top1_weight": float(top_weights[0]) if len(top_weights) else None,
            "top2_ze": top_ze[1] if len(top_ze) > 1 else None,
            "top2_name": top_names[1] if len(top_names) > 1 else None,
            "top2_weight": float(top_weights[1]) if len(top_weights) > 1 else None,
            "top3_ze": top_ze[2] if len(top_ze) > 2 else None,
            "top3_name": top_names[2] if len(top_names) > 2 else None,
            "top3_weight": float(top_weights[2]) if len(top_weights) > 2 else None,
            "total_outflow": float(total_out),
            "top3_concentration": concentration,
            "graph_dependency_high": concentration > 0.5,
            "learned_adj_status": "pending",  # extract from NPZ dynamic_adj[-1] when ready
        })
    return pd.DataFrame(records)

def compute_sector_opportunity(v6_sector, obs_a10, fc_sector, hist_stats):
    """Sector opportunity/concentration per zone."""
    # National A10 growth 2020->2025
    obs_a10_nat = obs_a10.groupby("target_year")[SECTORS_A10].sum()
    nat_2020 = obs_a10_nat.loc[2020] if 2020 in obs_a10_nat.index else None
    nat_2025 = obs_a10_nat.loc[2025] if 2025 in obs_a10_nat.index else None

    records = []
    zones = obs_a10["ZE2020"].unique()

    for ze in zones:
        zone_a10 = obs_a10[obs_a10["ZE2020"] == ze].set_index("target_year")

        # Historical sector shares (2019-2020 avg)
        hist_a10 = obs_a10[obs_a10["ZE2020"] == ze]
        hist_a10 = hist_a10[hist_a10["target_year"].between(2017, 2020)]
        if len(hist_a10) == 0:
            continue

        hist_shares = hist_a10[SECTORS_A10].mean()
        hist_total = hist_shares.sum()
        hist_shares_pct = (hist_shares / hist_total * 100) if hist_total > 0 else hist_shares * 0

        # Herfindahl (sectoral concentration)
        shares_normed = hist_shares / hist_total if hist_total > 0 else hist_shares
        herfindahl = (shares_normed ** 2).sum()

        # Recent sector growth (2022->2025)
        a10_2022 = zone_a10.loc[2022][SECTORS_A10] if 2022 in zone_a10.index else None
        a10_2025 = zone_a10.loc[2025][SECTORS_A10] if 2025 in zone_a10.index else None

        sector_growth = {}
        if a10_2022 is not None and a10_2025 is not None:
            for s in SECTORS_A10:
                base = a10_2022[s]
                growth = (a10_2025[s] - base) / base * 100 if base > 0 else np.nan
                sector_growth[f"growth_{s}_pct"] = growth

        # National sector growth context
        nat_growth = {}
        if nat_2020 is not None and nat_2025 is not None:
            for s in SECTORS_A10:
                base = nat_2020[s]
                ng = (nat_2025[s] - base) / base * 100 if base > 0 else np.nan
                nat_growth[s] = ng

        # Dominant sectors
        dominant = hist_shares_pct.nlargest(3).index.tolist()
        dominant_share = hist_shares_pct.nlargest(3).sum()

        # Forecast sector signal (2026)
        fc_signal = {}
        if fc_sector is not None:
            fc_ze_2026 = fc_sector[(fc_sector["ZE2020"] == ze) & (fc_sector["target_year"] == 2026)]
            if len(fc_ze_2026) > 0:
                for _, row in fc_ze_2026.iterrows():
                    fc_signal[f"fc_prop_{row['sector']}"] = row["prop_pred_mean"]

        rec = {
            "ZE2020": int(ze),
            "herfindahl_hist": float(herfindahl),
            "sectoral_concentration_high": herfindahl > 0.25,
            "dominant_sector_1": dominant[0] if len(dominant) > 0 else None,
            "dominant_sector_2": dominant[1] if len(dominant) > 1 else None,
            "dominant_sector_3": dominant[2] if len(dominant) > 2 else None,
            "dominant_3_share_pct": float(dominant_share),
        }
        rec.update({f"hist_share_{s}_pct": float(hist_shares_pct.get(s, np.nan)) for s in SECTORS_A10})
        rec.update(sector_growth)
        rec.update({f"nat_growth_{s}_pct": float(nat_growth.get(s, np.nan)) for s in SECTORS_A10})
        rec.update(fc_signal)

        records.append(rec)

    return pd.DataFrame(records)

def compute_opportunity_risk_scores(growth_df, err_df, graph_df, sector_df, obs):
    """
    Opportunity and risk scores.
    Percentile-based approach to avoid arbitrary weights.
    Components normalized to [0, 1] via percentile rank.
    """
    err_cols = ["ZE2020", "herald_wmape", "herald_wmape_all", "herald_wmape_aligned",
                "herald_n_years", "ridge_wmape", "ridge_n_years", "herald_vs_ridge_pct",
                "comparison_years", "herald_only_years", "comparison_status"]
    df = growth_df.merge(err_df[[c for c in err_cols if c in err_df.columns]], on="ZE2020", how="left")
    df = df.merge(graph_df[["ZE2020", "top3_concentration", "self_weight"]], on="ZE2020", how="left")
    df = df.merge(sector_df[["ZE2020", "herfindahl_hist"]], on="ZE2020", how="left")

    def prank(series, ascending=True):
        """Percentile rank, NaN → median."""
        s = series.fillna(series.median())
        if ascending:
            return s.rank(pct=True)
        else:
            return 1 - s.rank(pct=True)

    # ── OPPORTUNITY SCORE ──────────────────────────────────────────────────
    # High score = zone shows strong predicted growth, low uncertainty, beats baseline
    components_opp = {}

    # 1. Local growth trend vs historical mean (fc_2026 vs hist_mean)
    if "fc_acceleration_2026_vs_hist_pct" in df.columns:
        components_opp["c_local_trend"] = prank(df["fc_acceleration_2026_vs_hist_pct"], ascending=True)
    elif "pred_growth_vs_hist_pct" in df.columns:
        components_opp["c_local_trend"] = prank(df["pred_growth_vs_hist_pct"], ascending=True)
    else:
        components_opp["c_local_trend"] = 0.5

    # 2. Differential vs national mean
    if "fc_2026_vs_national_pct" in df.columns:
        components_opp["c_national_diff"] = prank(df["fc_2026_vs_national_pct"], ascending=True)
    elif "obs_2025_vs_national_pct" in df.columns:
        components_opp["c_national_diff"] = prank(df["obs_2025_vs_national_pct"], ascending=True)
    else:
        components_opp["c_national_diff"] = 0.5

    # 3. Advantage vs Ridge baseline (positive = HERALD sees more than Ridge)
    if "fc_2026_ridge" in df.columns and "fc_2026_mean" in df.columns:
        components_opp["c_vs_baseline"] = prank(df["fc_2026_mean"] - df["fc_2026_ridge"], ascending=True)
    else:
        components_opp["c_vs_baseline"] = 0.5

    # 4. HERALD historical reliability (penalty: low WMAPE = good = high score)
    components_opp["c_reliability"] = prank(df["herald_wmape"].fillna(df["herald_wmape"].median()), ascending=False)

    # 5. Uncertainty penalty (low std = good)
    if "fc_uncertainty_cv" in df.columns:
        components_opp["c_low_uncertainty"] = prank(df["fc_uncertainty_cv"].fillna(df["fc_uncertainty_cv"].median()), ascending=False)
    else:
        components_opp["c_low_uncertainty"] = 0.5

    comp_df = pd.DataFrame(components_opp, index=df.index)
    weights_opp = {
        "c_local_trend": 0.30,
        "c_national_diff": 0.20,
        "c_vs_baseline": 0.15,
        "c_reliability": 0.20,
        "c_low_uncertainty": 0.15,
    }
    df["opportunity_score_raw"] = sum(comp_df[k] * v for k, v in weights_opp.items())
    df["opportunity_score"] = df["opportunity_score_raw"].rank(pct=True) * 100

    for k in comp_df.columns:
        df[f"opp_{k}"] = comp_df[k]

    # ── RISK SCORE ────────────────────────────────────────────────────────
    # High score = zone shows decline signals or high uncertainty
    components_risk = {}

    # 1. Forecast deceleration 2026 vs 2025
    if "fc_growth_2025_2026_pct" in df.columns:
        components_risk["c_deceleration"] = prank(df["fc_growth_2025_2026_pct"], ascending=False)  # negative growth → high risk
    else:
        components_risk["c_deceleration"] = 0.5

    # 2. Historical volatility
    components_risk["c_volatility"] = prank(df["hist_std"].fillna(df["hist_std"].median()), ascending=True)

    # 3. Sectoral concentration (single-sector dependency)
    components_risk["c_concentration"] = prank(df["herfindahl_hist"].fillna(df["herfindahl_hist"].median()), ascending=True)

    # 4. Graph over-dependence on few poles
    components_risk["c_graph_dep"] = prank(df["top3_concentration"].fillna(0.5), ascending=True)

    # 5. HERALD uncertainty (high std = high risk)
    if "fc_uncertainty_cv" in df.columns:
        components_risk["c_uncertainty"] = prank(df["fc_uncertainty_cv"].fillna(df["fc_uncertainty_cv"].median()), ascending=True)
    else:
        components_risk["c_uncertainty"] = 0.5

    # 6. Historical HERALD error (high error = low confidence)
    components_risk["c_herald_error"] = prank(df["herald_wmape"].fillna(df["herald_wmape"].median()), ascending=True)

    comp_risk_df = pd.DataFrame(components_risk, index=df.index)
    weights_risk = {
        "c_deceleration": 0.30,
        "c_volatility": 0.15,
        "c_concentration": 0.15,
        "c_graph_dep": 0.10,
        "c_uncertainty": 0.20,
        "c_herald_error": 0.10,
    }
    df["risk_score_raw"] = sum(comp_risk_df[k] * v for k, v in weights_risk.items())
    df["risk_score"] = df["risk_score_raw"].rank(pct=True) * 100

    for k in comp_risk_df.columns:
        df[f"risk_{k}"] = comp_risk_df[k]

    # Flags
    df["has_forecast_2026"] = "fc_2026_mean" in df.columns and df["fc_2026_mean"].notna().any()
    df["baseline_ridge_ar_status"] = np.where(df["ridge_wmape"].notna(), "disponible_2021_2024", "absent")
    # ARIMA/LSTM/STGNN baselines: pending final HPC battery, not definitively absent
    df["baseline_arima_status"] = "pending_hpc_battery"
    df["baseline_lstm_status"] = "pending_hpc_battery"
    df["baseline_stgnn_ext_status"] = "pending_hpc_battery"
    df["learned_graph_status"] = "pending_npz_extraction"  # extract from dynamic_adj NPZ
    # Scores are exploratory until weights are calibrated against observed events
    df["score_status"] = "exploratoire_poids_non_calibres"

    df["opportunity_tier"] = pd.cut(df["opportunity_score"], bins=[0, 25, 50, 75, 100], labels=["faible", "modérée", "élevée", "très élevée"], right=True)
    df["risk_tier"] = pd.cut(df["risk_score"], bins=[0, 25, 50, 75, 100], labels=["faible", "modéré", "élevé", "très élevé"], right=True)

    return df

def generate_french_explanation(row, sector_df, graph_df):
    """Generate French narrative explanation for a zone."""
    ze = row["ZE2020"]
    name = row.get("libze2020", str(ze))
    opp_tier = str(row.get("opportunity_tier", "?"))
    risk_tier = str(row.get("risk_tier", "?"))

    parts = []

    # Opportunity signal
    if "fc_2026_percentile" in row and pd.notna(row["fc_2026_percentile"]):
        pct = row["fc_2026_percentile"]
        fc_val = row.get("fc_2026_mean", np.nan)
        hist = row.get("hist_mean", np.nan)
        if pd.notna(pct) and pd.notna(fc_val):
            if pd.notna(hist) and hist > 0:
                diff_hist = (fc_val - hist) / hist * 100
                sign = "supérieure" if diff_hist > 0 else "inférieure"
                parts.append(
                    f"HERALD prévoit {fc_val:.0f} créations en 2026 (p{pct:.0f} national), "
                    f"{abs(diff_hist):.1f}% {sign} à la moyenne historique de la zone."
                )
            else:
                parts.append(f"HERALD prévoit {fc_val:.0f} créations en 2026 (p{pct:.0f} national).")

    # Uncertainty
    if "fc_uncertainty_cv" in row and pd.notna(row["fc_uncertainty_cv"]):
        cv = row["fc_uncertainty_cv"]
        if cv < 0.05:
            parts.append("L'incertitude entre seeds est faible.")
        elif cv < 0.10:
            parts.append("L'incertitude entre seeds est modérée.")
        else:
            parts.append("L'incertitude entre seeds est élevée — signal à considérer comme exploratoire.")

    # Sector signal
    if sector_df is not None:
        ze_sec = sector_df[sector_df["ZE2020"] == ze]
        if len(ze_sec) > 0:
            row_sec = ze_sec.iloc[0]
            dom1 = row_sec.get("dominant_sector_1", None)
            dom2 = row_sec.get("dominant_sector_2", None)
            if dom1 and dom2:
                parts.append(f"Le signal sectoriel est porté principalement par {dom1} et {dom2}.")
            elif dom1:
                parts.append(f"Le signal sectoriel est concentré sur {dom1}.")

    # Graph dependency
    if graph_df is not None:
        ze_g = graph_df[graph_df["ZE2020"] == ze]
        if len(ze_g) > 0:
            row_g = ze_g.iloc[0]
            top1 = row_g.get("top1_name", None)
            conc = row_g.get("top3_concentration", 0)
            if top1 and conc > 0.6:
                parts.append(f"La zone présente une forte dépendance au pôle {top1} (concentration mobilité top3 = {conc:.2f}).")

    # HERALD error
    wmape = row.get("herald_wmape", np.nan)
    if pd.notna(wmape):
        if wmape < 5:
            parts.append(f"L'erreur historique HERALD est faible (WMAPE = {wmape:.1f}%).")
        elif wmape < 10:
            parts.append(f"L'erreur historique HERALD est modérée (WMAPE = {wmape:.1f}%).")
        else:
            parts.append(f"L'erreur historique HERALD est élevée (WMAPE = {wmape:.1f}%) — prudence recommandée.")

    # Baseline comparison
    if "fc_2026_ridge" in row and pd.notna(row.get("fc_2026_ridge")):
        ridge = row["fc_2026_ridge"]
        fc = row.get("fc_2026_mean", np.nan)
        if pd.notna(fc):
            diff = (fc - ridge) / ridge * 100
            sign = "au-dessus" if diff > 0 else "en dessous"
            parts.append(f"HERALD est {abs(diff):.1f}% {sign} de la baseline Ridge AR.")

    # Conclusion
    if opp_tier in ["élevée", "très élevée"] and risk_tier in ["faible", "modéré"]:
        parts.append(f"→ Score d'opportunité {opp_tier}, risque {risk_tier}: zone candidate à l'opportunité.")
    elif risk_tier in ["élevé", "très élevé"]:
        parts.append(f"→ Score de risque {risk_tier}: zone à surveiller.")
    else:
        parts.append(f"→ Score d'opportunité {opp_tier}, risque {risk_tier}.")

    arima_status = row.get("baseline_arima_status", "pending_hpc_battery")
    if arima_status != "disponible":
        parts.append(f"Note: baselines ARIMA/LSTM {arima_status} — comparaison actuelle limitée à Ridge AR.")

    return " ".join(parts)

# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    obs = load_observed()
    obs_a10 = load_observed_a10()
    v6_preds = load_v6_predictions()
    v6_sector = load_v6_sector_predictions()
    baselines = load_baselines()
    forecast_zone = load_forecast_zone()
    forecast_sector = load_forecast_sector()
    edges, adj_mob, nodes = load_graph()

    print(f"  obs: {len(obs)} rows, zones={obs['ZE2020'].nunique()}, years={sorted(obs['target_year'].unique())}")
    print(f"  v6_preds: {len(v6_preds)} rows, years={sorted(v6_preds['target_year'].unique())}")
    print(f"  baselines: {baselines['model'].unique()}")
    print(f"  forecast: {len(forecast_zone) if forecast_zone is not None else 'None'} rows")
    print(f"  graph nodes: {len(nodes)}, edges: {len(edges)}")

    print("\nComputing indicators...")

    hist_stats = compute_historical_stats(obs)
    err_df = compute_herald_error(v6_preds, baselines)
    graph_df = compute_graph_dependency(adj_mob, nodes)
    sector_df = compute_sector_opportunity(v6_sector, obs_a10, forecast_sector, hist_stats)
    growth_df = compute_growth_indicators(v6_preds, obs, forecast_zone, hist_stats)
    scores_df = compute_opportunity_risk_scores(growth_df, err_df, graph_df, sector_df, obs)

    # ── OUTPUT 1: GROWTH RANKING ──────────────────────────────────────────
    print("\nGenerating zone_growth_ranking.csv...")
    cols_growth = [
        "ZE2020", "libze2020",
        "obs_2025", "obs_2025_vs_national_pct", "obs_2025_percentile", "obs_2025_national_rank",
        "obs_growth_2024_2025_pct", "hist_mean", "pred_growth_vs_hist_pct",
    ]
    if "fc_2026_mean" in scores_df.columns:
        cols_growth += ["fc_2026_mean", "fc_2026_std", "fc_2026_ridge",
                        "fc_growth_2025_2026_pct", "fc_acceleration_2026_vs_hist_pct",
                        "fc_2026_vs_national_pct", "fc_2026_percentile", "fc_2026_national_rank"]
    cols_growth += ["herald_wmape", "ridge_wmape", "opportunity_score", "opportunity_tier"]

    growth_out = scores_df[[c for c in cols_growth if c in scores_df.columns]].copy()
    if "fc_2026_mean" in growth_out.columns:
        growth_out = growth_out.sort_values("fc_2026_percentile", ascending=False)
    else:
        growth_out = growth_out.sort_values("obs_2025_percentile", ascending=False)
    growth_out.to_csv(os.path.join(OUT_DIR, "zone_growth_ranking.csv"), index=False)
    print(f"  Saved {len(growth_out)} zones")

    # ── OUTPUT 2: DECELERATION RANKING ───────────────────────────────────
    print("Generating zone_deceleration_ranking.csv...")
    if "fc_growth_2025_2026_pct" in scores_df.columns:
        dec_out = scores_df[scores_df["fc_growth_2025_2026_pct"] < 0][[
            "ZE2020", "libze2020", "obs_2025",
            "fc_2026_mean", "fc_growth_2025_2026_pct",
            "fc_2026_percentile", "hist_mean",
            "risk_score", "risk_tier", "herald_wmape", "fc_uncertainty_cv"
        ] if "fc_2026_mean" in scores_df.columns else ["ZE2020", "libze2020", "obs_2025", "risk_score", "risk_tier", "herald_wmape"]].copy()
        dec_out = dec_out.sort_values("fc_growth_2025_2026_pct", ascending=True)
    else:
        dec_out = scores_df[["ZE2020", "libze2020", "obs_growth_2024_2025_pct", "risk_score", "risk_tier"]].sort_values("obs_growth_2024_2025_pct")
    dec_out.to_csv(os.path.join(OUT_DIR, "zone_deceleration_ranking.csv"), index=False)
    print(f"  Saved {len(dec_out)} zones (decelerating)")

    # ── OUTPUT 3: UNCERTAINTY RANKING ────────────────────────────────────
    print("Generating zone_uncertainty_ranking.csv...")
    if "fc_uncertainty_cv" in scores_df.columns:
        unc_cols = ["ZE2020", "libze2020", "fc_2026_mean", "fc_2026_std", "fc_uncertainty_cv",
                    "pred_2025_std", "herald_wmape", "risk_score"]
        unc_out = scores_df[[c for c in unc_cols if c in scores_df.columns]].copy()
        unc_out = unc_out.sort_values("fc_uncertainty_cv", ascending=False)
    else:
        unc_cols = ["ZE2020", "libze2020", "pred_2025_std", "herald_wmape"]
        unc_out = scores_df[[c for c in unc_cols if c in scores_df.columns]].copy()
        unc_out = unc_out.sort_values("herald_wmape", ascending=False)
    unc_out.to_csv(os.path.join(OUT_DIR, "zone_uncertainty_ranking.csv"), index=False)
    print(f"  Saved {len(unc_out)} zones")

    # ── OUTPUT 4: SECTOR OPPORTUNITY A10 ─────────────────────────────────
    print("Generating zone_sector_opportunity_a10.csv...")
    sec_out = sector_df.copy()
    sec_out = sec_out.merge(scores_df[["ZE2020", "libze2020", "opportunity_score", "risk_score"]], on="ZE2020", how="left")
    sec_out.to_csv(os.path.join(OUT_DIR, "zone_sector_opportunity_a10.csv"), index=False)
    print(f"  Saved {len(sec_out)} zones")

    # ── OUTPUT 5: GRAPH DEPENDENCY ───────────────────────────────────────
    print("Generating zone_graph_dependency.csv...")
    graph_out = graph_df.merge(
        scores_df[["ZE2020", "libze2020", "opportunity_score", "risk_score", "risk_c_graph_dep" if "risk_c_graph_dep" in scores_df.columns else "risk_score"]].rename(columns={"risk_c_graph_dep": "risk_graph_component"}),
        on="ZE2020", how="left"
    )
    graph_out.to_csv(os.path.join(OUT_DIR, "zone_graph_dependency.csv"), index=False)
    print(f"  Saved {len(graph_out)} zones")

    # ── OUTPUT 6: ALERTS ─────────────────────────────────────────────────
    print("Generating zone_alerts.csv...")
    alerts = []

    for _, row in scores_df.iterrows():
        ze = row["ZE2020"]
        name = row.get("libze2020", str(ze))

        # Alert: strong deceleration forecast
        if "fc_growth_2025_2026_pct" in row and pd.notna(row["fc_growth_2025_2026_pct"]):
            if row["fc_growth_2025_2026_pct"] < -5:
                cv = row.get("fc_uncertainty_cv", np.nan)
                alerts.append({
                    "ZE2020": ze, "libze2020": name,
                    "alert_type": "deceleration_forecast",
                    "severity": "high" if row["fc_growth_2025_2026_pct"] < -10 else "medium",
                    "value": round(row["fc_growth_2025_2026_pct"], 2),
                    "unit": "pct_growth_2025_2026",
                    "confidence": "low" if pd.notna(cv) and cv > 0.10 else "moderate_to_high",
                    "description": f"Prévision de décroissance {row['fc_growth_2025_2026_pct']:.1f}% (2025→2026)",
                })

        # Alert: high uncertainty
        if "fc_uncertainty_cv" in row and pd.notna(row["fc_uncertainty_cv"]):
            if row["fc_uncertainty_cv"] > 0.10:
                alerts.append({
                    "ZE2020": ze, "libze2020": name,
                    "alert_type": "high_uncertainty",
                    "severity": "medium",
                    "value": round(row["fc_uncertainty_cv"], 4),
                    "unit": "cv_seeds",
                    "confidence": "exploratory",
                    "description": f"Forte incertitude entre seeds (CV = {row['fc_uncertainty_cv']:.3f})",
                })

        # Alert: high HERALD error historically
        if "herald_wmape" in row and pd.notna(row["herald_wmape"]):
            if row["herald_wmape"] > 15:
                alerts.append({
                    "ZE2020": ze, "libze2020": name,
                    "alert_type": "high_historical_error",
                    "severity": "medium",
                    "value": round(row["herald_wmape"], 2),
                    "unit": "wmape_pct",
                    "confidence": "any_forecast_exploratory",
                    "description": f"WMAPE historique élevé ({row['herald_wmape']:.1f}%) — prévision exploratoire",
                })

        # Alert: high opportunity (positive signal)
        if row.get("opportunity_tier") in ["élevée", "très élevée"]:
            alerts.append({
                "ZE2020": ze, "libze2020": name,
                "alert_type": "opportunity_signal",
                "severity": "positive",
                "value": round(row.get("opportunity_score", np.nan), 1),
                "unit": "opportunity_score_percentile",
                "confidence": "low" if not row.get("baselines_available", True) else "moderate_to_high",
                "description": f"Opportunité {row['opportunity_tier']} (score p{row.get('opportunity_score', 0):.0f})",
            })

    alerts_df = pd.DataFrame(alerts)
    if len(alerts_df):
        alerts_df = alerts_df.sort_values(["severity", "ZE2020"])
    alerts_df.to_csv(os.path.join(OUT_DIR, "zone_alerts.csv"), index=False)
    print(f"  Saved {len(alerts_df)} alerts across {alerts_df['ZE2020'].nunique() if len(alerts_df) else 0} zones")

    # ── OUTPUT 7: RECOMMENDATION SCORES ──────────────────────────────────
    print("Generating zone_recommendation_scores.csv...")
    score_cols = [
        "ZE2020", "libze2020",
        "opportunity_score", "opportunity_tier",
        "risk_score", "risk_tier",
        "score_status",  # exploratoire_poids_non_calibres
        "opp_c_local_trend", "opp_c_national_diff", "opp_c_vs_baseline",
        "opp_c_reliability", "opp_c_low_uncertainty",
        "risk_c_deceleration", "risk_c_volatility", "risk_c_concentration",
        "risk_c_graph_dep", "risk_c_uncertainty", "risk_c_herald_error",
        "herald_wmape_all", "herald_wmape_aligned", "herald_n_years",
        "ridge_wmape", "ridge_n_years", "herald_vs_ridge_pct",
        "comparison_years", "herald_only_years",
        "baseline_ridge_ar_status", "baseline_arima_status",
        "baseline_lstm_status", "baseline_stgnn_ext_status",
        "learned_graph_status",
    ]
    if "fc_2026_mean" in scores_df.columns:
        score_cols += ["fc_2026_mean", "fc_2026_std", "fc_2026_ridge",
                       "fc_2026_percentile", "fc_growth_2025_2026_pct"]

    rec_out = scores_df[[c for c in score_cols if c in scores_df.columns]].copy()
    rec_out = rec_out.sort_values("opportunity_score", ascending=False)

    # Add French explanation
    rec_out["explication_fr"] = rec_out.apply(
        lambda row: generate_french_explanation(row, sector_df, graph_df), axis=1
    )

    rec_out.to_csv(os.path.join(OUT_DIR, "zone_recommendation_scores.csv"), index=False)
    print(f"  Saved {len(rec_out)} zones with scores and French explanations")

    print("\n✓ All outputs generated in:", OUT_DIR)
    print("\nSummary:")
    print(f"  Total zones: {len(rec_out)}")
    if "opportunity_tier" in rec_out.columns:
        print(f"  Opportunity tiers:\n{rec_out['opportunity_tier'].value_counts()}")
    if "risk_tier" in rec_out.columns:
        print(f"  Risk tiers:\n{rec_out['risk_tier'].value_counts()}")

if __name__ == "__main__":
    main()
