#!/usr/bin/env python3
"""Prepare France-compatible HERALD panels for Phase 4 international countries.

For each country, outputs to data/processed/phase4/{country}/:
  panel_ze2020.csv       — main panel, ZE2020 = integer zone index (1..N)
  a10_ze2020.csv         — A10 sector panel, wide format, France columns
  splits.csv             — walk-forward splits (same format as France)
  adj_geo.csv            — identity geographic adjacency (no boundary data)
  adj_mob.csv            — identity mobility adjacency (no commuting data)
  zone_mapping.csv       — integer zone index → original zone_id

Usage:
    python3 hpc/phase4/prepare_phase4_panel.py --country nl
    python3 hpc/phase4/prepare_phase4_panel.py --country be
    python3 hpc/phase4/prepare_phase4_panel.py --country pt
    python3 hpc/phase4/prepare_phase4_panel.py --country all
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent.parent

# A10 sectors in France format (column order matches train_herald_v6.py)
FRANCE_A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

# International A10 → France A10 mapping
# A (agriculture) is merged into OQ as the closest "other" sector
A10_REMAP = {
    "A":   "OQ",   # agriculture → merge into public/other (absent from France births)
    "BE":  "BE",
    "FZ":  "FZ",
    "GI":  "GI",
    "JZ":  "JZ",
    "KZ":  "KZ",
    "LZ":  "LZ",
    "MN":  "MN",
    "OPQ": "OQ",
    "RSU": "RU",
}

COUNTRY_CFG = {
    "nl": {
        "births_file":  BASE / "data/external/netherlands/processed/netherlands_births_panel.csv",
        "stock_file":   BASE / "data/external/netherlands/processed/netherlands_stock_panel.csv",
        "qtensor_file": BASE / "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv",
        "qtensor_col":  "jobs",
        "eval_start":   2017,
        "eval_end":     2024,
        "train_min":    2016,
        "covid_year":   2020,
    },
    "be": {
        "births_file":  BASE / "data/external/belgium/processed/belgium_births_panel.csv",
        "stock_file":   BASE / "data/external/belgium/processed/belgium_stock_panel.csv",
        "qtensor_file": BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv",
        "qtensor_col":  "jobs",
        "eval_start":   2010,
        "eval_end":     2020,
        "train_min":    2009,
        "covid_year":   2020,
    },
    "pt": {
        "births_file":  BASE / "data/external/portugal/processed/portugal_births_panel_nuts3.csv",
        "stock_file":   BASE / "data/external/portugal/processed/portugal_stock_panel_nuts3.csv",
        "qtensor_file": BASE / "data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv",
        "qtensor_col":  "births",
        "eval_start":   2010,
        "eval_end":     2022,
        "train_min":    2009,
        "covid_year":   2020,
    },
}


def make_zone_mapping(zones: list[str]) -> pd.DataFrame:
    """Map original zone_id → integer ZE2020 (1-based)."""
    return pd.DataFrame({
        "zone_id": sorted(zones),
        "ZE2020": range(1, len(zones) + 1),
    })


def build_main_panel(births: pd.DataFrame, stock: pd.DataFrame,
                     mapping: pd.DataFrame) -> pd.DataFrame:
    """Build France-format main panel from births + stock panels."""
    zm = mapping.set_index("zone_id")["ZE2020"]

    # Lookup: (ze_int, year) → births value for lag computation
    births_lookup: dict[tuple[int, int], float] = {}
    for _, br in births.iterrows():
        ze_int = int(zm[br["zone_id"]])
        y_val = float(br["y"]) if pd.notna(br["y"]) else np.nan
        births_lookup[(ze_int, int(br["target_year"]))] = y_val

    rows = []
    for _, r in births.iterrows():
        ze = int(zm[r["zone_id"]])
        ty = int(r["target_year"])
        lag1 = float(r["side_lag_1"]) if pd.notna(r["side_lag_1"]) else np.nan
        lag2 = births_lookup.get((ze, ty - 2), np.nan)
        lag3 = births_lookup.get((ze, ty - 3), np.nan)
        g1y = float(r["growth_1y"]) if pd.notna(r["growth_1y"]) else np.nan
        # growth_2y = (lag1 / lag3 - 1), matching France v6 convention
        if pd.notna(lag1) and pd.notna(lag3) and lag3 != 0:
            g2y = float(lag1 / lag3 - 1.0)
        else:
            g2y = np.nan
        row = {
            "ZE2020": ze,
            "target_year": ty,
            "node_idx": ze - 1,
            "side_establishment_creations_official": float(r["y"]) if pd.notna(r["y"]) else np.nan,
            "side_enterprise_creations_official": float(r["y"]) if pd.notna(r["y"]) else np.nan,
            "side_lag_1": lag1,
            "side_lag_2": lag2,
            "side_lag_3": lag3,
            "growth_1y": g1y,
            "growth_2y": g2y,
            # Flag columns — all 0: no France-specific sources
            "has_flores_source": 0,
            "has_side_stock_source": 0,
            "has_urssaf_source": 0,
            "feature_forecast_safe": 1,
            # COVID flags
            "is_covid_year": 0,
            "is_post_covid_rebound": 0,
        }
        rows.append(row)

    panel = pd.DataFrame(rows)

    # Add stock as side_stock_total_t_minus_1 using the previous observed year.
    stock_lookup: dict[tuple[int, int], float] = {}
    for _, sr in stock.iterrows():
        ze_int = int(zm[sr["zone_id"]])
        stock_lookup[(ze_int, int(sr["target_year"]))] = float(sr["stock"])

    panel["side_stock_total_t_minus_1"] = panel.apply(
        lambda r: stock_lookup.get((int(r["ZE2020"]), int(r["target_year"]) - 1), np.nan),
        axis=1,
    )

    panel = panel.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    return panel


def build_a10_panel(qtensor: pd.DataFrame, mapping: pd.DataFrame,
                    qtensor_col: str) -> pd.DataFrame:
    """Build France-format A10 panel from long-format qtensor."""
    zm = mapping.set_index("zone_id")["ZE2020"]
    qt = qtensor.copy()
    qt["ZE2020"] = qt["zone_id"].map(zm).astype(int)
    qt["france_a10"] = qt["a10"].map(A10_REMAP)
    qt = qt.dropna(subset=["france_a10"])

    # Aggregate (in case A merges into OQ)
    agg = (qt.groupby(["ZE2020", "target_year", "france_a10"])[qtensor_col]
           .sum()
           .reset_index()
           .rename(columns={qtensor_col: "val"}))

    pivot = agg.pivot_table(
        index=["ZE2020", "target_year"],
        columns="france_a10",
        values="val",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    pivot.columns.name = None

    for s in FRANCE_A10_SECTORS:
        if s not in pivot.columns:
            pivot[s] = 0.0

    pivot["total"] = pivot[FRANCE_A10_SECTORS].sum(axis=1)
    cols = ["ZE2020", "target_year"] + FRANCE_A10_SECTORS + ["total"]
    pivot = pivot[cols].sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
    return pivot


def build_splits(cfg: dict, years_all: list[int]) -> pd.DataFrame:
    """Build walk-forward splits in France format."""
    eval_start = cfg["eval_start"]
    eval_end   = cfg["eval_end"]
    train_min  = cfg["train_min"]
    covid_year = cfg["covid_year"]

    rows = []
    for ty in range(eval_start, eval_end + 1):
        covid_in_train = 1 if covid_year < ty else 0
        is_post_covid = 1 if ty == covid_year + 1 else 0
        rows.append({
            "fold": f"fold_{ty}",
            "target_year": ty,
            "train_years_max": ty - 1,
            "train_years_min": train_min,
            "eval_year": ty,
            "covid_in_train": covid_in_train,
            "is_post_covid_eval": is_post_covid,
            "note": f"strict ex-ante fold {ty}",
        })
    return pd.DataFrame(rows)


def build_identity_adjacency(n: int) -> pd.DataFrame:
    """Build NxN identity adjacency matrix in France CSV format."""
    mat = np.eye(n, dtype=float)
    df = pd.DataFrame(mat, columns=list(range(n)))
    df.insert(0, "source_idx", list(range(n)))
    return df


def prepare_country(country: str) -> None:
    cfg = COUNTRY_CFG[country]
    out_dir = BASE / f"data/processed/phase4/{country}"
    out_dir.mkdir(parents=True, exist_ok=True)

    births  = pd.read_csv(cfg["births_file"])
    stock   = pd.read_csv(cfg["stock_file"])
    qtensor = pd.read_csv(cfg["qtensor_file"])

    zones = sorted(births["zone_id"].unique())
    n = len(zones)
    mapping = make_zone_mapping(zones)
    mapping.to_csv(out_dir / "zone_mapping.csv", index=False)
    print(f"[{country.upper()}] {n} zones mapped")

    panel = build_main_panel(births, stock, mapping)
    panel.to_csv(out_dir / "panel_ze2020.csv", index=False)
    print(f"[{country.upper()}] panel_ze2020.csv: {len(panel)} rows")

    a10 = build_a10_panel(qtensor, mapping, cfg["qtensor_col"])
    a10.to_csv(out_dir / "a10_ze2020.csv", index=False)
    print(f"[{country.upper()}] a10_ze2020.csv: {len(a10)} rows")

    years_all = sorted(births["target_year"].unique().tolist())
    splits = build_splits(cfg, years_all)
    splits.to_csv(out_dir / "splits.csv", index=False)
    print(f"[{country.upper()}] splits.csv: {len(splits)} folds "
          f"({splits['target_year'].min()}–{splits['target_year'].max()})")

    adj = build_identity_adjacency(n)
    adj.to_csv(out_dir / "adj_geo.csv", index=False)
    adj.to_csv(out_dir / "adj_mob.csv", index=False)
    print(f"[{country.upper()}] adj_{n}x{n}_identity.csv written (geo + mob)")

    print(f"[{country.upper()}] Done → {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", choices=["nl", "be", "pt", "all"], default="all")
    args = parser.parse_args()
    targets = list(COUNTRY_CFG.keys()) if args.country == "all" else [args.country]
    for c in targets:
        prepare_country(c)


if __name__ == "__main__":
    main()
