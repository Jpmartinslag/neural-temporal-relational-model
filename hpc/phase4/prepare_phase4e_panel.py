"""
Prepare Phase 4E-A training panel from the canonical European panel.

Converts data/processed/european_panel/{country}_panel.csv → HERALD format
and writes to data/processed/phase4e/{country}/:
  panel_ze2020.csv   — HERALD-format panel (NON_PREDICTIVE_FIELDS kept but excluded from features)
  splits.csv         — walk-forward folds
  a10_ze2020.csv     — sector panel (from Phase 4 or Phase 4E European panel)
  adj_identity.csv   — NxN identity adjacency (for Phase 4E-A sanity check)
  adj_mob.csv        — identity (no mobility signal used in 4E-A)

This script is called once per country before training. It is idempotent.

Usage:
    python3 hpc/phase4/prepare_phase4e_panel.py --country nl
    python3 hpc/phase4/prepare_phase4e_panel.py --country fr
    python3 hpc/phase4/prepare_phase4e_panel.py --country all
"""

import argparse
import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]

FRANCE_A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

A10_REMAP = {
    "A": "OQ",
    "BE": "BE",
    "FZ": "FZ",
    "GI": "GI",
    "JZ": "JZ",
    "KZ": "KZ",
    "LZ": "LZ",
    "MN": "MN",
    "OPQ": "OQ",
    "RSU": "RU",
}

_COUNTRIES = {
    "fr": {"n_zones": 280, "year_min": 2012, "year_max": 2024, "eval_start": 2016},
    "nl": {"n_zones": 40,  "year_min": 2015, "year_max": 2025, "eval_start": 2017},
    "be": {"n_zones": 42,  "year_min": 2007, "year_max": 2024, "eval_start": 2010},
    "pt": {"n_zones": 25,  "year_min": 2008, "year_max": 2024, "eval_start": 2010},
}

# Map European panel → HERALD columns
_RENAME = {
    "year":               "target_year",
    "target_births":      "side_establishment_creations_official",
    "lag1_births":        "side_lag_1",
    "lag2_births":        "side_lag_2",
    "lag3_births":        "side_lag_3",
    "growth_1y":          "growth_1y",
    "growth_2y":          "growth_2y",
    "flag_forecast_safe": "feature_forecast_safe",
    "flag_is_covid_year": "is_covid_year",
    "flag_is_rebound_year": "is_post_covid_rebound",
    "stock_lag1":         "side_stock_total_t_minus_1",
    "node_idx":           "node_idx",
}


def _build_identity_adj(n: int, path: Path) -> None:
    mat = np.eye(n, dtype=np.float64)
    df = pd.DataFrame(mat, columns=list(range(n)))
    df.insert(0, "source_idx", list(range(n)))
    df.to_csv(path, index=False)


def _build_splits(year_min: int, year_max: int, eval_start: int, out_path: Path) -> None:
    rows = []
    for target_year in range(eval_start, year_max + 1):
        train_max = target_year - 1
        train_min = year_min
        covid_in = 1 if 2020 < target_year else 0
        rebound  = 1 if target_year == 2021 else 0
        rows.append({
            "fold":           f"fold_{target_year}",
            "target_year":    target_year,
            "train_years_max": train_max,
            "train_years_min": train_min,
            "eval_year":      target_year,
            "covid_in_train": covid_in,
            "is_post_covid_eval": rebound,
            "note":           f"strict ex-ante fold {target_year}",
        })
    pd.DataFrame(rows).to_csv(out_path, index=False)


def _build_a10_from_european(eu_panel: pd.DataFrame, country: str, zones: list, years: list) -> pd.DataFrame:
    """Build a10_ze2020.csv from sector_* columns in European panel (unlagged — t)."""
    sectors = ["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
    sec_eu = [f"sector_{s}" for s in sectors]

    eu_panel = eu_panel.copy()
    ze_col = "ZE2020_int"  # already computed by caller

    rows = []
    for _, row in eu_panel.iterrows():
        rec = {"ZE2020": int(row[ze_col]), "target_year": int(row["year"])}
        total = 0.0
        for i, s in enumerate(sectors):
            col = f"sector_{s}"
            v = float(row[col]) if col in eu_panel.columns and not pd.isna(row[col]) else 0.0
            rec[s] = v
            total += v
        rec["total"] = total
        rows.append(rec)

    a10 = pd.DataFrame(rows)
    a10 = a10[["ZE2020","target_year"] + sectors + ["total"]]
    return a10


def _build_a10_from_long_qtensor(qtensor: pd.DataFrame, zone_to_ze: dict, value_col: str) -> pd.DataFrame:
    qt = qtensor.copy()
    qt["ZE2020"] = qt["zone_id"].map(zone_to_ze)
    qt["france_a10"] = qt["a10"].map(A10_REMAP)
    qt = qt.dropna(subset=["ZE2020", "france_a10"]).copy()
    qt["ZE2020"] = qt["ZE2020"].astype(int)

    agg = (
        qt.groupby(["ZE2020", "target_year", "france_a10"], as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: "val"})
    )
    pivot = (
        agg.pivot_table(
            index=["ZE2020", "target_year"],
            columns="france_a10",
            values="val",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )
    pivot.columns.name = None
    for sector in FRANCE_A10_SECTORS:
        if sector not in pivot.columns:
            pivot[sector] = 0.0
    pivot["total"] = pivot[FRANCE_A10_SECTORS].sum(axis=1)
    return pivot[["ZE2020", "target_year"] + FRANCE_A10_SECTORS + ["total"]].sort_values(
        ["target_year", "ZE2020"]
    )


def prepare_country(country: str) -> None:
    cfg = _COUNTRIES[country]
    out_dir = BASE / "data/processed/phase4e" / country
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[{country.upper()}] Preparing Phase 4E-A panel → {out_dir}")

    # ── 1. Read European panel ────────────────────────────────────────────
    # France adapter writes "france_panel.csv"; others write "{country}_panel.csv"
    name = "france" if country == "fr" else country
    eu_path = BASE / f"data/processed/european_panel/{name}_panel.csv"
    if not eu_path.exists():
        raise FileNotFoundError(f"European panel missing: {eu_path}")
    eu = pd.read_csv(eu_path)
    print(f"  European panel: {eu.shape}")

    # ── 2. Compute ZE2020 column (HERALD zone identifier) ────────────────
    if country == "fr":
        eu["ZE2020_int"] = eu["region_id"].astype(int)
    else:
        eu["ZE2020_int"] = eu["node_idx"] + 1  # ZE2020 in Phase 4 was 1-based for intl

    # ── 3. Rename to HERALD format ────────────────────────────────────────
    panel = eu.rename(columns={k: v for k, v in _RENAME.items() if k in eu.columns}).copy()
    panel["ZE2020"] = eu["ZE2020_int"]
    panel["side_enterprise_creations_official"] = panel["side_establishment_creations_official"]

    # Source availability flags (all zero for European panel — no FLORES/SIDE/URSSAF)
    panel["has_flores_source"]     = 0
    panel["has_side_stock_source"] = 0
    panel["has_urssaf_source"]     = 0

    # Fill stock NaN with 0 (structural absence, not measurement error)
    if "side_stock_total_t_minus_1" in panel.columns:
        panel["side_stock_total_t_minus_1"] = panel["side_stock_total_t_minus_1"].fillna(0.0)
    else:
        panel["side_stock_total_t_minus_1"] = 0.0

    # Keep is_covid_year / is_post_covid_rebound for walk-forward metadata only
    # (they are in NON_PREDICTIVE_FIELDS and excluded from features by the wrapper)
    for col in ["is_covid_year", "is_post_covid_rebound"]:
        if col not in panel.columns:
            panel[col] = 0

    herald_cols = [
        "ZE2020", "target_year", "node_idx",
        "side_establishment_creations_official",
        "side_enterprise_creations_official",
        "side_lag_1", "side_lag_2", "side_lag_3",
        "growth_1y", "growth_2y",
        "has_flores_source", "has_side_stock_source", "has_urssaf_source",
        "feature_forecast_safe",
        "is_covid_year", "is_post_covid_rebound",
        "side_stock_total_t_minus_1",
        "mask_target", "mask_sector_a10", "mask_employment",
        "mask_tensor", "mask_eu_signals",
        "flag_target_concept", "flag_has_national_employment",
        "flag_has_eurostat_bd",
        "eu_employment_rate_lag1", "eu_unemployment_rate_lag1",
        "eu_sts_turnover_lag1", "eu_esi_lag1", "eu_eei_lag1",
        "eu_credit_standards_lag1", "eu_gdp_growth_lag1",
    ]
    panel = panel[[c for c in herald_cols if c in panel.columns]]
    panel = panel.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)

    panel_path = out_dir / "panel_ze2020.csv"
    panel.to_csv(panel_path, index=False)
    print(f"  panel_ze2020.csv: {panel.shape}  (feature_forecast_safe=1: {(panel['feature_forecast_safe']==1).sum()})")

    # ── 4. Splits ─────────────────────────────────────────────────────────
    splits_path = out_dir / "splits.csv"
    _build_splits(cfg["year_min"], cfg["year_max"], cfg["eval_start"], splits_path)
    splits = pd.read_csv(splits_path)
    print(f"  splits.csv: {len(splits)} folds ({splits['target_year'].min()}–{splits['target_year'].max()})")

    # ── 5. Identity adjacency (Phase 4E-A: no spatial graph) ─────────────
    n = cfg["n_zones"]
    adj_geo_path = out_dir / "adj_geo.csv"
    adj_mob_path = out_dir / "adj_mob.csv"
    _build_identity_adj(n, adj_geo_path)
    _build_identity_adj(n, adj_mob_path)
    print(f"  adj_identity: {n}×{n}")

    # ── 6. A10 sector panel ───────────────────────────────────────────────
    a10_dst = out_dir / "a10_ze2020.csv"
    if country == "fr":
        # FR/PT: build from European panel sector columns (unlagged version = births in year t)
        # The trainer applies sector_lag1 internally; provide the unlagged A10.
        # For FR: reconstruct from existing a10 source
        src_a10 = BASE / "data/processed/side_creations_a10_ze2020_v1.csv"
        a10 = pd.read_csv(src_a10)
        a10 = a10[a10["target_year"].between(cfg["year_min"], cfg["year_max"])].copy()
        a10.to_csv(a10_dst, index=False)
        print(f"  a10_ze2020.csv: copied from source ({len(a10)} rows)")
    elif country == "pt":
        emp_qtensor = BASE / "data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv"
        if emp_qtensor.exists():
            qt = pd.read_csv(emp_qtensor)
            zone_to_ze = dict(zip(eu["region_id"], eu["ZE2020_int"]))
            a10 = _build_a10_from_long_qtensor(qt, zone_to_ze, "jobs")
            a10 = a10[a10["target_year"].between(cfg["year_min"], cfg["year_max"])].copy()
            a10.to_csv(a10_dst, index=False)
            print(f"  a10_ze2020.csv: Eurostat employment tensor ({len(a10)} rows)")
        else:
            src_a10 = BASE / "data/processed/phase4/pt/a10_ze2020.csv"
            a10 = pd.read_csv(src_a10)
            a10.to_csv(a10_dst, index=False)
            print(f"  a10_ze2020.csv: copied births proxy ({len(a10)} rows) ⚠ proxy, not employment")
    else:
        # NL/BE: prefer the country employment tensor, rebuilt from processed
        # long data so Phase 4E uses newly extended years instead of stale
        # Phase 4A materialised A10 files.
        qtensor_path = {
            "nl": BASE / "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv",
            "be": BASE / "data/external/belgium/processed/belgium_qtensor_jobs_panel.csv",
        }[country]
        if qtensor_path.exists():
            qt = pd.read_csv(qtensor_path)
            zone_to_ze = dict(zip(eu["region_id"], eu["ZE2020_int"]))
            a10 = _build_a10_from_long_qtensor(qt, zone_to_ze, "jobs")
            a10 = a10[a10["target_year"].between(cfg["year_min"], cfg["year_max"])].copy()
            a10.to_csv(a10_dst, index=False)
            print(f"  a10_ze2020.csv: employment tensor ({len(a10)} rows)")
        else:
            # Fallback: uniform sector proportions
            zones_in_panel = sorted(panel["ZE2020"].unique())
            years_in_panel = sorted(panel["target_year"].unique())
            sectors = ["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
            rows = []
            for z in zones_in_panel:
                yr_target = panel[panel["ZE2020"]==z]["side_establishment_creations_official"]
                for y, yr_val in zip(years_in_panel, yr_target):
                    rec = {"ZE2020": z, "target_year": y}
                    for s in sectors:
                        rec[s] = float(yr_val) / 9 if not pd.isna(yr_val) else 0.0
                    rec["total"] = float(yr_val) if not pd.isna(yr_val) else 0.0
                    rows.append(rec)
            pd.DataFrame(rows).to_csv(a10_dst, index=False)
            print(f"  a10_ze2020.csv: uniform fallback ({len(rows)} rows)")

    print(f"  [{country.upper()}] Done → {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Phase 4E-A panels from European canonical panel.")
    parser.add_argument("--country", choices=list(_COUNTRIES) + ["all"], default="all")
    args = parser.parse_args()

    targets = list(_COUNTRIES) if args.country == "all" else [args.country]
    for c in targets:
        prepare_country(c)

    print("\nAll Phase 4E-A panels prepared.")


if __name__ == "__main__":
    main()
