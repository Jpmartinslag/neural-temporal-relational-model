"""
DEC-062: PT Municipal Sector Panel Builder.

Downloads INE enterprise birth data at municipality × CAE × year and builds
a panel compatible with the HERALD Phase 7 sector-precedence analysis.

Sources:
  INE indicator 0009703: enterprise births × CAE × município (NUTS2013, 2008-2022)
  INE indicator 0014099: enterprise births × CAE × município (NUTS2024, 2023+)

Continental filter: geocod[0] == '1' → 278 continental municipalities
  geocod[0] == '2' → Açores (19 municipalities, excluded in CONTINENT mode)
  geocod[0] == '3' → Madeira (11 municipalities, excluded in CONTINENT mode)

CAE → HERALD A10 mapping:
  BE = B, C, D, E (Industry)
  FZ = F (Construction)
  GI = G, H, I (Trade/Transport/Hospitality)
  JZ = J (ICT)
  KZ = K (Finance) — structural_absent in INE (definitional exclusion)
  LZ = L (Real Estate)
  MN = M, N (Professional/Business Services)
  OQ = O, P, Q, A (Public/Education/Health + Agriculture per existing PT convention)
  RU = R, S (Arts/Other Services)

Agriculture (A) is merged into OQ following the existing HERALD PT convention.
KZ recorded as structural_absent (not as zero or missing).

No HPC. No model training. No causal language. No raw large files committed.
"""

from __future__ import annotations
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[3]
OUT_DIR = REPO_ROOT / "data/processed/european_panel"
OUT_CSV = OUT_DIR / "pt_municipal_sector_panel.csv"
OUT_MANIFEST = OUT_DIR / "pt_municipal_sector_panel_manifest.json"

INE_BASE = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
IND_CAE_OLD = "0009703"   # NUTS2013, 2008-2022
IND_CAE_NEW = "0014099"   # NUTS2024, 2023+

YEARS_OLD = list(range(2008, 2023))  # 2008-2022 inclusive
YEARS_NEW = [2023]

CONTINENTAL_PREFIX = "1"    # geocod[0] == '1' → continental Portugal
ACORES_PREFIX = "2"
MADEIRA_PREFIX = "3"

# CAE section → HERALD A10
CAE_TO_A10 = {
    "A": "OQ",   # Agriculture → merged into OQ per HERALD PT convention
    "B": "BE", "C": "BE", "D": "BE", "E": "BE",
    "F": "FZ",
    "G": "GI", "H": "GI", "I": "GI",
    "J": "JZ",
    "K": None,   # structural_absent (not emitted to sector columns)
    "L": "LZ",
    "M": "MN", "N": "MN",
    "O": "OQ", "P": "OQ", "Q": "OQ",
    "R": "RU", "S": "RU",
}

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "LZ", "MN", "OQ", "RU"]  # 8 observable sectors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "application/json",
}

COVID_YEARS = {2020, 2021}
REBOUND_YEARS = {2022, 2023}

# ---------------------------------------------------------------------------
# 1. INE fetch
# ---------------------------------------------------------------------------

def fetch_ine(indicator: str, year: int, retries: int = 3) -> list:
    params = {"op": "2", "varcd": indicator, "Dim1": f"S7A{year}", "lang": "PT"}
    for attempt in range(retries):
        try:
            r = requests.get(INE_BASE, params=params, headers=HEADERS, timeout=40)
            r.raise_for_status()
            d = r.json()
            return d[0]["Dados"].get(str(year), [])
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"    retry {attempt+1}: {e}")
            time.sleep(3)


def indicator_for_year(year: int) -> str:
    return IND_CAE_NEW if year >= 2023 else IND_CAE_OLD


# ---------------------------------------------------------------------------
# 2. Parse one year → long DataFrame
# ---------------------------------------------------------------------------

def parse_year(entries: list, year: int) -> pd.DataFrame:
    """
    Parse INE response entries for one year → long rows:
    (geocod, geodsg, cae_section, year, births)

    Filter:
    - geocod length == 7 (municipality level)
    - dim_3 not 'TOT' (individual sector; TOT used for business_sector_total)
    - valor parseable as int
    """
    rows = []
    total_rows = []

    for e in entries:
        gc = e.get("geocod", "")
        if len(gc) != 7:
            continue

        section = e.get("dim_3", "")
        val_str = e.get("valor", "")

        # Parse value
        try:
            val = int(val_str.replace(" ", "").replace(" ", ""))
        except (ValueError, AttributeError):
            val = None  # genuine missing

        if section == "TOT":
            total_rows.append({"geocod": gc, "geodsg": e.get("geodsg", ""), "year": year, "births_total": val})
        elif section in CAE_TO_A10:
            a10 = CAE_TO_A10[section]
            rows.append({
                "geocod": gc,
                "geodsg": e.get("geodsg", ""),
                "year": year,
                "cae_section": section,
                "a10": a10,
                "births": val,
            })

    df_long = pd.DataFrame(rows)
    df_tot = pd.DataFrame(total_rows).drop_duplicates("geocod") if total_rows else pd.DataFrame()
    return df_long, df_tot


# ---------------------------------------------------------------------------
# 3. Aggregate to A10 × municipality
# ---------------------------------------------------------------------------

def aggregate_to_a10(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate CAE section births to A10 buckets per (geocod, geodsg, year).
    Sum all non-K sections; K is structural_absent (no column).
    """
    df = df_long[df_long["a10"].notna()].copy()  # drop K rows (a10=None)
    agg = (
        df.groupby(["geocod", "geodsg", "year", "a10"])["births"]
        .sum()
        .reset_index()
    )
    # Pivot to wide
    wide = agg.pivot_table(
        index=["geocod", "geodsg", "year"],
        columns="a10",
        values="births",
        aggfunc="sum",
    ).reset_index()
    wide.columns.name = None

    # Ensure all A10 columns present
    for s in A10_SECTORS:
        if s not in wide.columns:
            wide[s] = np.nan

    return wide


# ---------------------------------------------------------------------------
# 4. Download all years
# ---------------------------------------------------------------------------

def download_all_years(years_old: list, years_new: list, verbose: bool = True) -> pd.DataFrame:
    frames_long = []
    frames_tot = []

    for year in sorted(set(years_old + years_new)):
        ind = indicator_for_year(year)
        if verbose:
            print(f"  Fetching year {year} ({ind})...", end=" ")
        try:
            entries = fetch_ine(ind, year)
            df_long, df_tot = parse_year(entries, year)
            frames_long.append(df_long)
            frames_tot.append(df_tot)
            n_gc = df_long["geocod"].nunique() if not df_long.empty else 0
            if verbose:
                print(f"OK ({n_gc} geocods, {len(df_long)} rows)")
        except Exception as e:
            if verbose:
                print(f"ERROR: {e}")

        time.sleep(0.5)  # rate limit

    all_long = pd.concat(frames_long, ignore_index=True) if frames_long else pd.DataFrame()
    all_tot = pd.concat(frames_tot, ignore_index=True) if frames_tot else pd.DataFrame()
    return all_long, all_tot


# ---------------------------------------------------------------------------
# 5. Build final panel
# ---------------------------------------------------------------------------

def _harmonise_geocods(df: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonise geocod across NUTS2013/NUTS2024 transition.

    INE switched indicator numbering at 2023 (NUTS2013→NUTS2024) causing
    176/278 municipalities to get new 7-char geocods. Use municipality name
    (geodsg) as the join key and adopt the NUTS2024 geocod as canonical.

    Approach:
    1. Build name→canonical_geocod mapping from NUTS2024 data (year 2023).
    2. For older years, replace geocod with canonical if name matches.
    3. Flag NUTS version used.
    """
    nuts2024 = df[df["year"] >= 2023][["geocod", "geodsg"]].drop_duplicates("geodsg")
    name_to_canon = dict(zip(nuts2024["geodsg"], nuts2024["geocod"]))

    def resolve(row):
        canon = name_to_canon.get(row["geodsg"])
        if canon is not None:
            return canon
        return row["geocod"]  # no 2024 match → keep original

    df = df.copy()
    df["geocod"] = df.apply(resolve, axis=1)
    return df


def build_panel(
    all_long: pd.DataFrame,
    all_tot: pd.DataFrame,
    mode: str = "CONTINENT",
) -> pd.DataFrame:
    """
    Build the final wide panel in HERALD schema.
    mode: 'CONTINENT' (only geocod[0]=='1') or 'ALL'
    """
    # Harmonise geocods across NUTS2013/NUTS2024 transition
    all_long = _harmonise_geocods(all_long)
    if not all_tot.empty:
        all_tot = _harmonise_geocods(all_tot)

    # Aggregate to A10 wide
    wide = aggregate_to_a10(all_long)

    # Merge totals
    if not all_tot.empty:
        tot = all_tot.drop_duplicates(["geocod", "year"]).rename(columns={"births_total": "business_sector_total"})
        wide = wide.merge(tot[["geocod", "year", "business_sector_total"]], on=["geocod", "year"], how="left")
    else:
        wide["business_sector_total"] = np.nan

    # Continental filter: after harmonisation all geocods should use NUTS2024 format
    # NUTS2024 continental prefix is '1' (same as NUTS2013 for most, now canonical)
    if mode == "CONTINENT":
        wide = wide[wide["geocod"].str[0] == CONTINENTAL_PREFIX].copy()

    # is_continental flag
    wide["is_continental"] = wide["geocod"].str[0] == CONTINENTAL_PREFIX

    # Rename columns to sector_* style
    for s in A10_SECTORS:
        if s in wide.columns:
            wide.rename(columns={s: f"sector_{s}"}, inplace=True)

    # Sort by geocod, year
    wide = wide.sort_values(["geocod", "year"]).reset_index(drop=True)

    # Lags and growth per municipality
    wide["sector_KZ"] = np.nan  # structural_absent
    wide = _add_lags_and_growth(wide)

    # node_idx
    geocod_to_idx = {gc: i for i, gc in enumerate(sorted(wide["geocod"].unique()))}
    wide["node_idx"] = wide["geocod"].map(geocod_to_idx)

    # Flags
    wide["flag_target_concept"] = "enterprise_birth"
    wide["flag_is_covid_year"] = wide["year"].isin(COVID_YEARS).astype(int)
    wide["flag_is_rebound_year"] = wide["year"].isin(REBOUND_YEARS).astype(int)
    wide["flag_has_national_employment"] = 0
    wide["flag_has_eurostat_bd"] = 0
    wide["flag_forecast_safe"] = (
        (~wide["year"].isin(COVID_YEARS | REBOUND_YEARS)) & wide["year"] >= 2010
    ).astype(int)

    # Masks
    sector_cols = [f"sector_{s}" for s in A10_SECTORS]
    wide["mask_sector_a10"] = (wide[sector_cols].notna().all(axis=1)).astype(float)
    wide["mask_target"] = wide["target_births"].notna().astype(float)
    wide["mask_employment"] = 0.0
    wide["mask_tensor"] = 0.0

    # Meta
    wide["country"] = "PT"
    wide["region_id"] = wide["geocod"]
    wide["region_name"] = wide["geodsg"]
    wide["region_level"] = "MUNICIPALITY"
    wide["meta_region_system"] = "MUNICIPALITY_CONTINENTE" if mode == "CONTINENT" else "MUNICIPALITY_ALL"
    wide["meta_nuts3_code"] = ""
    wide["meta_source_label"] = "INE_0009703_0014099"
    wide["source_indicator"] = wide["year"].apply(
        lambda y: IND_CAE_NEW if y >= 2023 else IND_CAE_OLD
    )
    wide["source_geocod"] = wide["geocod"]
    wide["nuts_version"] = wide["year"].apply(lambda y: "NUTS2024" if y >= 2023 else "NUTS2013")
    wide["available_for_forecast_year"] = 1

    # EU signal placeholders (not available at municipality level)
    for sig in ["eu_employment_rate_lag1", "eu_unemployment_rate_lag1", "eu_sts_turnover_lag1",
                "eu_esi_lag1", "eu_eei_lag1", "eu_credit_standards_lag1", "eu_gdp_growth_lag1"]:
        wide[sig] = np.nan
    wide["mask_eu_signals"] = 0.0

    # Column order
    base_cols = [
        "country", "region_id", "region_name", "region_level", "year", "node_idx",
        "target_births", "lag1_births", "lag2_births", "lag3_births",
        "growth_1y", "growth_2y", "business_sector_total",
    ]
    sector_out = [f"sector_{s}" for s in A10_SECTORS] + ["sector_KZ"]
    mask_cols = ["mask_sector_a10", "mask_target", "mask_employment", "mask_tensor"]
    flag_cols = [
        "flag_target_concept", "flag_has_national_employment", "flag_has_eurostat_bd",
        "flag_is_covid_year", "flag_is_rebound_year", "flag_forecast_safe",
    ]
    meta_cols = [
        "meta_nuts3_code", "meta_region_system", "meta_source_label",
        "source_indicator", "source_geocod", "nuts_version",
        "is_continental", "available_for_forecast_year",
    ]

    all_cols = base_cols + sector_out + mask_cols + flag_cols + meta_cols
    # Keep only columns that exist
    all_cols = [c for c in all_cols if c in wide.columns]
    return wide[all_cols]


def _add_lags_and_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Add target_births, lag1_births, lag2_births, lag3_births, growth_1y, growth_2y per municipality."""
    # target_births = business_sector_total (from INE TOT section)
    df = df.sort_values(["geocod", "year"])
    df["target_births"] = df["business_sector_total"]

    df["lag1_births"] = df.groupby("geocod")["target_births"].shift(1)
    df["lag2_births"] = df.groupby("geocod")["target_births"].shift(2)
    df["lag3_births"] = df.groupby("geocod")["target_births"].shift(3)

    # Causal growth: growth at t uses t-1 as base (no future leakage)
    df["growth_1y"] = (df["target_births"] - df["lag1_births"]) / df["lag1_births"].replace(0, np.nan)
    df["growth_2y"] = (df["target_births"] - df["lag2_births"]) / df["lag2_births"].replace(0, np.nan)

    return df


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def main(mode: str = "CONTINENT", verbose: bool = True) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"\nDEC-062: Building PT Municipal Sector Panel (mode={mode})")
        print(f"Years: {YEARS_OLD[0]}-{YEARS_NEW[-1]}")
        print(f"Continental filter: geocod[0] == '{CONTINENTAL_PREFIX}'")
        print()

    print("Downloading INE data...")
    all_long, all_tot = download_all_years(YEARS_OLD, YEARS_NEW, verbose=verbose)

    print(f"\nBuilding panel...")
    panel = build_panel(all_long, all_tot, mode=mode)

    n_muni = panel["region_id"].nunique()
    n_years = panel["year"].nunique()
    year_range = f"{panel['year'].min()}-{panel['year'].max()}"
    n_rows = len(panel)

    print(f"  N municipalities ({mode}): {n_muni}")
    print(f"  N years: {n_years} ({year_range})")
    print(f"  N rows: {n_rows}")

    # Check sector coverage
    sector_cols = [f"sector_{s}" for s in A10_SECTORS]
    coverage = {s: panel[s].notna().mean() for s in sector_cols}
    print(f"  Sector coverage: {coverage}")
    print(f"  mask_sector_a10 mean: {panel['mask_sector_a10'].mean():.3f}")

    # Save
    panel.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")

    # Manifest
    manifest = {
        "experiment": "DEC-062",
        "build_mode": mode,
        "sources": [
            {"indicator": IND_CAE_OLD, "years": f"{YEARS_OLD[0]}-{YEARS_OLD[-1]}", "url": INE_BASE},
            {"indicator": IND_CAE_NEW, "years": f"{YEARS_NEW[0]}+", "url": INE_BASE},
        ],
        "continental_filter": f"geocod[0] == '{CONTINENTAL_PREFIX}'",
        "n_municipalities": int(n_muni),
        "n_years": int(n_years),
        "year_range": year_range,
        "n_rows": int(n_rows),
        "sectors_observable": A10_SECTORS,
        "sector_KZ_status": "structural_absent_definitional_exclusion",
        "cae_to_a10": {k: v for k, v in CAE_TO_A10.items() if v is not None},
        "cae_k_status": "K_structural_absent",
        "target_concept": "enterprise_birth",
        "flag_target_concept": "enterprise_birth",
        "source_label": "INE_0009703_0014099",
        "sector_coverage": coverage,
        "mask_sector_a10_mean": float(panel["mask_sector_a10"].mean()),
    }

    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved: {OUT_MANIFEST}")


if __name__ == "__main__":
    main()
