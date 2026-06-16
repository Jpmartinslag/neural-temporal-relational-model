"""
DEC-063: Build NL gemeente birth proxy panel.

Method: Allocate COROP-level observed births (83631NED) to gemeente level
using gemeente establishment stock shares (81575NED).

For each COROP × A10 sector × year:
    share_gm = stock_gm_sector / sum(stock within COROP for that sector-year)
    estimated_births_gm = observed_births_corop_sector * share_gm

Evidence type: proxy_disaggregated_by_stock_share
This is NOT observed births. Never treat as such.

Verification: re-aggregating proxy by COROP must recover observed_births
within floating-point tolerance.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parents[3]
PANEL_DIR = REPO_ROOT / "data/processed/european_panel"

IN_COROP_BIRTHS = (
    REPO_ROOT / "data/external/netherlands/processed/"
    "netherlands_sector_births_cbs_83631NED_corop_a10.csv"
)
IN_STOCK = PANEL_DIR / "nl_gemeente_stock_panel.csv"
IN_CROSSWALK = PANEL_DIR / "nl_gemeente_corop_crosswalk.csv"

OUT_PROXY = PANEL_DIR / "nl_gemeente_birth_proxy_panel.csv"
OUT_MANIFEST = PANEL_DIR / "nl_gemeente_birth_proxy_manifest.json"

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]

PROXY_METHOD = "corop_births_allocated_by_gemeente_stock_share"
EVIDENCE_TYPE = "proxy_disaggregated_by_stock_share"
SOURCE_BIRTH_TABLE = "83631NED"
SOURCE_STOCK_TABLE = "81575NED"

# Tolerance for COROP re-aggregation check (relative)
REAG_TOL_REL = 0.001   # 0.1%
REAG_TOL_ABS = 5.0     # 5 units absolute (for small COROP sectors)


def load_corop_births() -> pd.DataFrame:
    """Load existing processed COROP births panel."""
    df = pd.read_csv(IN_COROP_BIRTHS)
    # Convert to long format: zone_id, target_year, sector, births
    id_vars = ["zone_id", "target_year"]
    value_vars = [s for s in A10_SECTORS if s in df.columns]
    long = df.melt(id_vars=id_vars, value_vars=value_vars,
                   var_name="sector_a10", value_name="observed_births_corop")
    long = long.rename(columns={"zone_id": "cr_code", "target_year": "year"})
    long["cr_code"] = long["cr_code"].astype(str).str.strip()
    return long


def load_gemeente_stock() -> pd.DataFrame:
    """Load gemeente stock panel, melt to long format."""
    df = pd.read_csv(IN_STOCK)
    sector_cols = [f"sector_{s}" for s in A10_SECTORS]
    present = [c for c in sector_cols if c in df.columns]

    id_vars = ["country", "gm_code", "gm_name", "cr_code", "cr_name",
               "region_level", "year", "evidence_type", "source_table"]
    id_vars = [v for v in id_vars if v in df.columns]

    long = df.melt(id_vars=id_vars, value_vars=present,
                   var_name="sector_col", value_name="stock_observed_gemeente")
    long["sector_a10"] = long["sector_col"].str.replace("sector_", "")
    long = long.drop(columns=["sector_col"])
    long["cr_code"] = long["cr_code"].astype(str).str.strip()
    long["gm_code"] = long["gm_code"].astype(str).str.strip()
    return long


def compute_stock_shares(stock_long: pd.DataFrame) -> pd.DataFrame:
    """Compute gemeente stock share within each COROP × sector × year."""
    # Total stock per COROP × sector × year
    corop_total = (
        stock_long.groupby(["cr_code", "year", "sector_a10"], as_index=False)
        ["stock_observed_gemeente"].sum(min_count=1)
        .rename(columns={"stock_observed_gemeente": "stock_total_corop"})
    )
    merged = stock_long.merge(corop_total, on=["cr_code", "year", "sector_a10"], how="left")
    merged["stock_share_within_corop"] = (
        merged["stock_observed_gemeente"] / merged["stock_total_corop"]
    )
    # Where total is 0 or NaN, share is undefined
    mask_zero = merged["stock_total_corop"].fillna(0) == 0
    merged.loc[mask_zero, "stock_share_within_corop"] = float("nan")
    return merged


def compute_proxy(stock_shares: pd.DataFrame, corop_births: pd.DataFrame) -> pd.DataFrame:
    """Allocate COROP births to gemeenten using stock shares."""
    merged = stock_shares.merge(
        corop_births[["cr_code", "year", "sector_a10", "observed_births_corop"]],
        on=["cr_code", "year", "sector_a10"],
        how="left",
    )

    # Proxy births = COROP births × stock share
    merged["estimated_births_gemeente"] = (
        merged["observed_births_corop"] * merged["stock_share_within_corop"]
    )

    # Evidence status
    def _evidence_status(row):
        if pd.isna(row["observed_births_corop"]):
            return "no_corop_births_data"
        if pd.isna(row["stock_total_corop"]) or row["stock_total_corop"] == 0:
            return "insufficient_stock_share"
        if pd.isna(row["stock_observed_gemeente"]):
            return "missing_gemeente_stock"
        return "proxy_computed"

    merged["evidence_status"] = merged.apply(_evidence_status, axis=1)
    merged.loc[
        merged["evidence_status"] != "proxy_computed", "estimated_births_gemeente"
    ] = float("nan")

    merged["evidence_type"] = EVIDENCE_TYPE
    merged["proxy_method"] = PROXY_METHOD
    merged["source_birth_table"] = SOURCE_BIRTH_TABLE
    merged["source_stock_table"] = SOURCE_STOCK_TABLE

    cols = [
        "country", "year", "cr_code", "cr_name",
        "gm_code", "gm_name", "region_level", "sector_a10",
        "observed_births_corop", "stock_observed_gemeente",
        "stock_total_corop", "stock_share_within_corop",
        "estimated_births_gemeente", "evidence_status",
        "evidence_type", "proxy_method",
        "source_birth_table", "source_stock_table",
    ]
    return merged[[c for c in cols if c in merged.columns]]


def verify_reaggregation(proxy: pd.DataFrame) -> dict:
    """Verify that re-aggregating proxy by COROP recovers observed births."""
    ok_rows = proxy[proxy["evidence_status"] == "proxy_computed"].copy()
    if ok_rows.empty:
        return {"status": "NO_PROXY_ROWS", "max_abs_error": None, "max_rel_error": None}

    reag = (
        ok_rows.groupby(["cr_code", "year", "sector_a10"], as_index=False)
        ["estimated_births_gemeente"].sum(min_count=1)
    )
    check = reag.merge(
        proxy[["cr_code", "year", "sector_a10", "observed_births_corop"]].drop_duplicates(),
        on=["cr_code", "year", "sector_a10"], how="inner",
    )
    check = check.dropna(subset=["observed_births_corop", "estimated_births_gemeente"])
    if check.empty:
        return {"status": "NO_MATCHING_ROWS", "max_abs_error": None, "max_rel_error": None}

    check["abs_error"] = (check["estimated_births_gemeente"] - check["observed_births_corop"]).abs()
    check["rel_error"] = check["abs_error"] / check["observed_births_corop"].replace(0, float("nan"))

    max_abs = float(check["abs_error"].max())
    max_rel = float(check["rel_error"].dropna().max())
    n_checked = len(check)

    # A row fails if abs_error > ABS_TOL and rel_error > REL_TOL
    fail_mask = (check["abs_error"] > REAG_TOL_ABS) & (check["rel_error"] > REAG_TOL_REL)
    n_fail = int(fail_mask.sum())

    return {
        "status": "PASS" if n_fail == 0 else "FAIL",
        "n_checked": n_checked,
        "n_fail": n_fail,
        "max_abs_error": round(max_abs, 4),
        "max_rel_error": round(max_rel, 6),
        "tolerance_abs": REAG_TOL_ABS,
        "tolerance_rel": REAG_TOL_REL,
    }


def main() -> dict:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)

    print("\nDEC-063: NL Gemeente Birth Proxy Panel")
    print("=" * 45)

    if not IN_COROP_BIRTHS.exists():
        raise FileNotFoundError(f"COROP births not found: {IN_COROP_BIRTHS}")
    if not IN_STOCK.exists():
        raise FileNotFoundError(f"Gemeente stock not found: {IN_STOCK} — run ingest_nl_gemeente_stock_panel.py first")

    corop_births = load_corop_births()
    print(f"COROP births: {len(corop_births)} rows, {corop_births['cr_code'].nunique()} CORPs, "
          f"{corop_births['year'].nunique()} years")

    stock_long = load_gemeente_stock()
    print(f"Gemeente stock: {len(stock_long)} rows, {stock_long['gm_code'].nunique()} GMs, "
          f"{stock_long['year'].nunique()} years")

    # Year overlap
    birth_years = set(corop_births["year"].unique())
    stock_years = set(stock_long["year"].unique())
    common_years = sorted(birth_years & stock_years)
    print(f"Common years: {common_years[0]}–{common_years[-1]} ({len(common_years)} years)")

    # Filter to common years
    stock_long = stock_long[stock_long["year"].isin(common_years)].copy()
    corop_births = corop_births[corop_births["year"].isin(common_years)].copy()

    stock_shares = compute_stock_shares(stock_long)
    proxy = compute_proxy(stock_shares, corop_births)

    # Verification
    check = verify_reaggregation(proxy)
    print(f"\nRe-aggregation check: {check['status']} "
          f"(max_abs_err={check.get('max_abs_error')}, max_rel_err={check.get('max_rel_error')})")

    proxy.to_csv(OUT_PROXY, index=False)
    print(f"\nProxy panel saved: {OUT_PROXY}")

    n_proxy_computed = int((proxy["evidence_status"] == "proxy_computed").sum())
    n_total = len(proxy)
    n_gm = int(proxy["gm_code"].nunique())
    n_years = int(proxy["year"].nunique())
    evidence_counts = {k: int(v) for k, v in proxy["evidence_status"].value_counts().items()}

    manifest = {
        "experiment": "DEC-063",
        "evidence_type": EVIDENCE_TYPE,
        "proxy_method": PROXY_METHOD,
        "source_birth_table": SOURCE_BIRTH_TABLE,
        "source_stock_table": SOURCE_STOCK_TABLE,
        "n_rows": int(n_total),
        "n_gemeenten": int(n_gm),
        "n_years": int(n_years),
        "common_years": [int(y) for y in common_years],
        "n_proxy_computed": int(n_proxy_computed),
        "n_proxy_missing": int(n_total - n_proxy_computed),
        "evidence_status_counts": evidence_counts,
        "reaggregation_check": check,
        "warning": (
            "estimated_births_gemeente is a PROXY. "
            "It is NOT observed births. "
            "Claims based on this must be labelled proxy-dependent. "
            "Evaluation must report proxy-excluded sensitivity separately."
        ),
    }
    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved: {OUT_MANIFEST}")

    return manifest


if __name__ == "__main__":
    main()
