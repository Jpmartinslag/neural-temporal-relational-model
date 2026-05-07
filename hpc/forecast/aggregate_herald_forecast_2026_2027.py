#!/usr/bin/env python3
"""Aggregate prospective HERALD 2026/2027 forecasts.

No WMAPE is computed here because future years have no observed target.  The
script reports forecast-comparison diagnostics: national aggregate, delta vs
ridge-only, seed uncertainty, model consensus, and territorial acceleration.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, default=None)
    args = parser.parse_args()

    data_dir = args.root / "data_processed"
    paths = sorted(data_dir.glob("herald_forecast_total_*_v1.csv"))
    if not paths:
        raise SystemExit(f"No forecast CSVs found in {data_dir}")

    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    needed = {"panel_key", "model", "seed", "target_year", "ZE2020", "y_pred", "ridge_pred"}
    missing = needed - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")

    # National aggregates by panel/model/year/seed.
    nat_seed = (
        df.groupby(["panel_key", "model", "target_year", "seed"], as_index=False)
        .agg(national_pred=("y_pred", "sum"), national_ridge=("ridge_pred", "sum"))
    )
    nat = (
        nat_seed.groupby(["panel_key", "model", "target_year"], as_index=False)
        .agg(
            mean_pred=("national_pred", "mean"),
            std_pred=("national_pred", "std"),
            min_pred=("national_pred", "min"),
            max_pred=("national_pred", "max"),
            mean_ridge=("national_ridge", "mean"),
        )
    )
    nat["delta_vs_ridge"] = nat["mean_pred"] - nat["mean_ridge"]
    nat["pct_vs_ridge"] = 100.0 * nat["delta_vs_ridge"] / nat["mean_ridge"].replace(0, pd.NA)

    # Consensus uncertainty by ZE: dispersion across seeds for each model.
    ze_unc = (
        df.groupby(["panel_key", "model", "target_year", "ZE2020"], as_index=False)
        .agg(mean_pred=("y_pred", "mean"), std_pred=("y_pred", "std"))
    )
    top_unc = (
        ze_unc.sort_values("std_pred", ascending=False)
        .groupby(["panel_key", "model", "target_year"])
        .head(15)
    )

    # Acceleration between 2026 and 2027, per ZE and model.
    wide = ze_unc.pivot_table(
        index=["panel_key", "model", "ZE2020"],
        columns="target_year",
        values="mean_pred",
    ).reset_index()
    accel = wide.dropna(subset=[2026, 2027]).copy() if {2026, 2027}.issubset(wide.columns) else pd.DataFrame()
    if not accel.empty:
        accel["delta_2027_vs_2026"] = accel[2027] - accel[2026]
        accel["pct_2027_vs_2026"] = 100.0 * accel["delta_2027_vs_2026"] / accel[2026].replace(0, pd.NA)
        top_accel = accel.sort_values("delta_2027_vs_2026", ascending=False).groupby(["panel_key", "model"]).head(15)
        top_decel = accel.sort_values("delta_2027_vs_2026", ascending=True).groupby(["panel_key", "model"]).head(15)
    else:
        top_accel = pd.DataFrame()
        top_decel = pd.DataFrame()

    out_json = args.out_json or args.root / "reports/forecast_2026_2027_summary.json"
    out_csv = args.out_csv or args.root / "reports/forecast_2026_2027_national.csv"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    nat.to_csv(out_csv, index=False)
    top_unc.to_csv(args.root / "reports/forecast_2026_2027_top_uncertain_zones.csv", index=False)
    if not top_accel.empty:
        top_accel.to_csv(args.root / "reports/forecast_2026_2027_top_acceleration_zones.csv", index=False)
        top_decel.to_csv(args.root / "reports/forecast_2026_2027_top_deceleration_zones.csv", index=False)

    payload = {
        "n_files": len(paths),
        "n_rows": int(len(df)),
        "panels": sorted(df["panel_key"].unique().tolist()),
        "models": sorted(df["model"].unique().tolist()),
        "years": sorted(int(x) for x in df["target_year"].unique()),
        "national": nat.to_dict(orient="records"),
        "outputs": {
            "national_csv": str(out_csv),
            "top_uncertain_zones_csv": str(args.root / "reports/forecast_2026_2027_top_uncertain_zones.csv"),
            "top_acceleration_zones_csv": str(args.root / "reports/forecast_2026_2027_top_acceleration_zones.csv"),
            "top_deceleration_zones_csv": str(args.root / "reports/forecast_2026_2027_top_deceleration_zones.csv"),
        },
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"files={len(paths)} rows={len(df)}")
    print(f"saved={out_json}")
    print(f"saved={out_csv}")


if __name__ == "__main__":
    main()
