"""
Statistical and economic evidence package for HERALD V3.

Uses existing prediction and internals artifacts. No model training.

Outputs:
  reports/HERALD_V3_STATISTICAL_EVIDENCE_V1.md
  reports/herald_v3_statistical_evidence_v1.json
  reports/herald_v3_dm_tests_v1.csv
  reports/herald_v3_zone_strata_v1.csv
  reports/herald_v3_gamma_stability_v1.csv
  reports/herald_v3_top_neighbors_v1.csv
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

YEARS = [2021, 2022, 2023, 2024]
SEEDS = [0, 7, 42]
KEY_ZONES = {"Paris": 1109, "Lyon": 8421, "Marseille": 9312, "Toulouse": 7625}

OUT_MD = REPORTS / "HERALD_V3_STATISTICAL_EVIDENCE_V1.md"
OUT_JSON = REPORTS / "herald_v3_statistical_evidence_v1.json"
OUT_DM = REPORTS / "herald_v3_dm_tests_v1.csv"
OUT_STRATA = REPORTS / "herald_v3_zone_strata_v1.csv"
OUT_GAMMA = REPORTS / "herald_v3_gamma_stability_v1.csv"
OUT_NEIGHBORS = REPORTS / "herald_v3_top_neighbors_v1.csv"


def wmape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return float(np.abs(y_true - y_pred).sum() / denom) if denom > 0 else np.nan


def normal_p_value(z):
    return math.erfc(abs(z) / math.sqrt(2.0))


def dm_test(loss_a, loss_b):
    """One-step Diebold-Mariano using paired loss differential d=a-b."""
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    d = d[np.isfinite(d)]
    n = len(d)
    mean = float(d.mean())
    std = float(d.std(ddof=1)) if n > 1 else np.nan
    se = std / math.sqrt(n) if std > 0 else np.nan
    stat = mean / se if se and np.isfinite(se) else np.nan
    return {
        "n": n,
        "mean_loss_diff": mean,
        "dm_stat": float(stat),
        "p_value_normal_approx": float(normal_p_value(stat)) if np.isfinite(stat) else np.nan,
    }


def load_predictions():
    ridge = pd.read_csv(PROCESSED / "dynamic_feature_panel_baseline_predictions_v1.csv")
    ridge = ridge[ridge["model"] == "Ridge_AR"].copy()
    ridge = ridge[["target_year", "ZE2020", "y_true", "y_pred"]].rename(columns={"y_pred": "ridge_pred"})

    herald_frames = []
    for seed in SEEDS:
        path = PROCESSED / f"herald_v3_predictions_full_seed_{seed}_v1.csv"
        frame = pd.read_csv(path)
        frame["seed"] = seed
        herald_frames.append(frame)
    herald = pd.concat(herald_frames, ignore_index=True)
    herald_mean = (
        herald.groupby(["target_year", "ZE2020"], as_index=False)
        .agg(y_true=("y_true", "mean"), herald_pred=("y_pred", "mean"))
    )
    merged = herald_mean.merge(ridge, on=["target_year", "ZE2020", "y_true"], how="inner")
    merged["herald_abs_error"] = (merged["y_true"] - merged["herald_pred"]).abs()
    merged["ridge_abs_error"] = (merged["y_true"] - merged["ridge_pred"]).abs()
    merged["herald_ape"] = merged["herald_abs_error"] / merged["y_true"].clip(lower=1.0)
    merged["ridge_ape"] = merged["ridge_abs_error"] / merged["y_true"].clip(lower=1.0)
    merged["herald_weighted_abs"] = merged["herald_abs_error"]
    merged["ridge_weighted_abs"] = merged["ridge_abs_error"]
    return merged, herald


def dm_tests(merged):
    rows = []
    tests = [
        ("absolute_error", "herald_abs_error", "ridge_abs_error"),
        ("absolute_percentage_error", "herald_ape", "ridge_ape"),
        ("wmape_numerator", "herald_weighted_abs", "ridge_weighted_abs"),
    ]
    for name, h_col, r_col in tests:
        out = dm_test(merged[h_col], merged[r_col])
        rows.append({"comparison": "HERALD_full_mean_vs_Ridge_AR", "loss": name, **out})
        for year, group in merged.groupby("target_year"):
            out = dm_test(group[h_col], group[r_col])
            rows.append({"comparison": f"HERALD_full_mean_vs_Ridge_AR_{int(year)}", "loss": name, **out})
    return pd.DataFrame(rows)


def zone_strata(merged):
    panel = pd.read_csv(PROCESSED / "dynamic_stgnn_feature_panel_v1.csv")
    meta = (
        panel[panel["target_year"].isin(YEARS)]
        .groupby("ZE2020", as_index=False)
        .agg(mean_target=("side_establishment_creations_official", "mean"), nb_com=("communes_count", "mean"))
    )
    meta["size_stratum"] = pd.qcut(
        meta["mean_target"],
        q=4,
        labels=["small", "medium_low", "medium_high", "large"],
        duplicates="drop",
    )
    meta["commune_stratum"] = pd.qcut(
        meta["nb_com"],
        q=4,
        labels=["few_communes", "midlow_communes", "midhigh_communes", "many_communes"],
        duplicates="drop",
    )
    data = merged.merge(meta, on="ZE2020", how="left")
    rows = []
    for col in ["size_stratum", "commune_stratum"]:
        for value, group in data.groupby(col, observed=True):
            rows.append({
                "stratification": col,
                "stratum": str(value),
                "n": len(group),
                "zones": group["ZE2020"].nunique(),
                "ridge_wmape": wmape(group["y_true"], group["ridge_pred"]),
                "herald_wmape": wmape(group["y_true"], group["herald_pred"]),
                "delta_wmape": wmape(group["y_true"], group["herald_pred"]) - wmape(group["y_true"], group["ridge_pred"]),
                "relative_gain_pct": 100.0 * (1.0 - wmape(group["y_true"], group["herald_pred"]) / wmape(group["y_true"], group["ridge_pred"])),
            })
    return pd.DataFrame(rows)


def gamma_stability():
    rows = []
    for seed in SEEDS:
        path = PROCESSED / f"herald_v3_internals_full_seed_{seed}_v1.npz"
        data = np.load(path, allow_pickle=True)
        rows.append({
            "seed": seed,
            "gamma_geo": float(data["gamma_geo"][0]),
            "gamma_mob": float(data["gamma_mob"][0]),
            "gamma_mob_minus_geo": float(data["gamma_mob"][0] - data["gamma_geo"][0]),
        })
    return pd.DataFrame(rows)


def top_neighbors(top_k=10):
    nodes = pd.read_csv(PROCESSED / "graph_node_index_core_v0.csv").sort_values("node_idx")
    zones = nodes["ze2020"].astype(int).to_numpy()
    labels = dict(zip(nodes["ze2020"].astype(int), nodes["libze2020"].astype(str)))
    rows = []
    mats = []
    years = None
    for seed in SEEDS:
        path = PROCESSED / f"herald_v3_internals_full_seed_{seed}_v1.npz"
        data = np.load(path, allow_pickle=True)
        mats.append(data["dynamic_adj"])
        years = data["years"].astype(int).tolist()
    A = np.mean(mats, axis=0)
    year_to_idx = {int(year): idx for idx, year in enumerate(years)}
    for year in YEARS:
        matrix = A[year_to_idx[year]]
        for city, ze in KEY_ZONES.items():
            if ze not in zones:
                continue
            zi = int(np.where(zones == ze)[0][0])
            order = np.argsort(matrix[zi])[::-1]
            rank = 0
            for idx in order:
                if int(zones[idx]) == ze:
                    continue
                weight = float(matrix[zi, idx])
                if weight <= 0:
                    continue
                rank += 1
                rows.append({
                    "target_year": year,
                    "source_city": city,
                    "source_ze2020": int(ze),
                    "source_name": labels.get(int(ze), str(ze)),
                    "rank": rank,
                    "neighbor_ze2020": int(zones[idx]),
                    "neighbor_name": labels.get(int(zones[idx]), str(zones[idx])),
                    "weight": weight,
                })
                if rank >= top_k:
                    break
    return pd.DataFrame(rows)


def write_report(dm, strata, gamma, neighbors, merged):
    def md_table(frame):
        frame = frame.copy()
        cols = list(frame.columns)
        lines = [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join(["---"] * len(cols)) + " |",
        ]
        for row in frame.itertuples(index=False):
            vals = []
            for value in row:
                if isinstance(value, float):
                    vals.append(f"{value:.6g}")
                else:
                    vals.append(str(value))
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    summary = {
        "ridge_wmape": wmape(merged["y_true"], merged["ridge_pred"]),
        "herald_wmape": wmape(merged["y_true"], merged["herald_pred"]),
        "delta_wmape": wmape(merged["y_true"], merged["herald_pred"]) - wmape(merged["y_true"], merged["ridge_pred"]),
        "relative_gain_pct": 100.0 * (1.0 - wmape(merged["y_true"], merged["herald_pred"]) / wmape(merged["y_true"], merged["ridge_pred"])),
        "dm_abs_error_p": float(dm[(dm["comparison"] == "HERALD_full_mean_vs_Ridge_AR") & (dm["loss"] == "absolute_error")]["p_value_normal_approx"].iloc[0]),
        "gamma_geo_mean": float(gamma["gamma_geo"].mean()),
        "gamma_mob_mean": float(gamma["gamma_mob"].mean()),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# HERALD V3 Statistical Evidence",
        "",
        "## Overall",
        "",
        f"- Ridge AR WMAPE: `{summary['ridge_wmape']:.6f}`",
        f"- HERALD WMAPE: `{summary['herald_wmape']:.6f}`",
        f"- Relative gain: `{summary['relative_gain_pct']:.2f}%`",
        f"- DM p-value (absolute error, normal approximation): `{summary['dm_abs_error_p']:.3e}`",
        "",
        "## Diebold-Mariano Tests",
        "",
        md_table(dm),
        "",
        "## Zone Strata",
        "",
        md_table(strata),
        "",
        "## Gamma Stability",
        "",
        md_table(gamma),
        "",
        "## Top Adaptive Neighbors",
        "",
        md_table(neighbors.head(80)),
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    merged, _herald = load_predictions()
    dm = dm_tests(merged)
    strata = zone_strata(merged)
    gamma = gamma_stability()
    neighbors = top_neighbors()

    dm.to_csv(OUT_DM, index=False)
    strata.to_csv(OUT_STRATA, index=False)
    gamma.to_csv(OUT_GAMMA, index=False)
    neighbors.to_csv(OUT_NEIGHBORS, index=False)
    write_report(dm, strata, gamma, neighbors, merged)

    print(f"Saved: {OUT_MD}")
    print(f"Saved: {OUT_JSON}")
    print(f"Saved: {OUT_DM}")
    print(f"Saved: {OUT_STRATA}")
    print(f"Saved: {OUT_GAMMA}")
    print(f"Saved: {OUT_NEIGHBORS}")


if __name__ == "__main__":
    main()
