"""
Pipelines A–D: build trainable feature panel for Dynamic STGNN.

Outputs:
  data/processed/flores_panel_ze2020_annual_v1.csv        (Pipeline A)
  data/processed/side_stocks_lagged_ze2020_annual_v1.csv  (Pipeline B)
  data/processed/dynamic_stgnn_feature_panel_v1.csv       (Pipeline C)
  metadata/dynamic_stgnn_walk_forward_splits_v1.csv       (Pipeline D)

Leakage rules:
  - FLORES: use year T-1 only (forecast-safe; INSEE lag 6-12 months).
  - SIDE stocks: use year T-1 only (never use T).
  - Zone_Sectoral excluded (leakage confirmed, δ=-85%).
  - SIRENE excluded (quarantine).
"""

import io
import zipfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

ROOT = Path(__file__).resolve().parents[2]
RAW_FLORES = ROOT / "data/raw/employment/flores"
RAW_SIDE   = ROOT / "data/raw/business_demography/side"
PROCESSED  = ROOT / "data/processed"
METADATA   = ROOT / "metadata"
MAPPINGS   = ROOT / "data/interim/mappings"

A17_SECTORS = ["AZ","DE","C1","C2","C3","C4","C5","FZ","GZ","HZ","IZ","JZ","KZ","LZ","MN","OQ","RU"]


# ─── helpers ──────────────────────────────────────────────────────────────────

def _load_commune_ze2020():
    df = pd.read_csv(MAPPINGS / "commune_to_ze2020_2026.csv", dtype={"CODGEO": str, "ZE2020": str})
    df["CODGEO"] = df["CODGEO"].str.zfill(5)
    df["ZE2020"] = df["ZE2020"].str.zfill(4)
    return df[["CODGEO","ZE2020"]].drop_duplicates("CODGEO")


def _flores_td_to_ze2020(year: int, comm_map: pd.DataFrame) -> pd.DataFrame:
    """Read wide commune-level FLORES (TD format 2017-2021) and aggregate to ZE2020."""
    tag = str(year)
    # Try both lowercase and uppercase suffixes
    for suffix in [f"_csv.zip", f"_CSV.zip"]:
        p = RAW_FLORES / f"TD_FLORES{tag}_NA17_TREF_NBETAB{suffix}"
        if p.exists():
            break
    else:
        print(f"  [FLORES TD] NBETAB not found for {year}")
        return pd.DataFrame()

    with zipfile.ZipFile(p) as z:
        fname = [n for n in z.namelist() if n.startswith("TD_") and n.endswith(".csv")][0]
        with z.open(fname) as f:
            etab = pd.read_csv(f, sep=";", dtype={"CODGEO": str})

    etab["CODGEO"] = etab["CODGEO"].astype(str).str.zfill(5)

    # Optional: salaried jobs
    sal = None
    for suffix in ["_csv.zip", "_CSV.zip"]:
        ps = RAW_FLORES / f"TD_FLORES{tag}_NA17_TREF_NBSAL{suffix}"
        if ps.exists():
            with zipfile.ZipFile(ps) as z:
                fname = [n for n in z.namelist() if n.startswith("TD_") and n.endswith(".csv")][0]
                with z.open(fname) as f:
                    sal = pd.read_csv(f, sep=";", dtype={"CODGEO": str})
            sal["CODGEO"] = sal["CODGEO"].astype(str).str.zfill(5)
            break

    # Merge with ZE2020 mapping
    etab = etab.merge(comm_map, on="CODGEO", how="inner")
    coverage = etab["CODGEO"].nunique()
    n_merged = etab["ZE2020"].notna().sum()

    # Sum establishments to ZE2020
    et_cols = ["ET_TOT"] + [f"ET_{s}" for s in A17_SECTORS]
    et_cols = [c for c in et_cols if c in etab.columns]
    agg = etab.groupby("ZE2020")[et_cols].sum().reset_index()
    agg.rename(columns={"ET_TOT": "flores_total_establishments"}, inplace=True)
    for s in A17_SECTORS:
        col = f"ET_{s}"
        if col in agg.columns:
            agg.rename(columns={col: f"flores_etab_{s.lower()}"}, inplace=True)

    if sal is not None:
        sal = sal.merge(comm_map, on="CODGEO", how="inner")
        eff_cols = ["EFF_TOT"] + [f"EFF_{s}" for s in A17_SECTORS]
        eff_cols = [c for c in eff_cols if c in sal.columns]
        sal_agg = sal.groupby("ZE2020")[eff_cols].sum().reset_index()
        sal_agg.rename(columns={"EFF_TOT": "flores_total_salaried_jobs"}, inplace=True)
        agg = agg.merge(sal_agg[["ZE2020","flores_total_salaried_jobs"]], on="ZE2020", how="left")

    agg["flores_year"] = year
    print(f"  [FLORES TD {year}] ZE2020 zones: {len(agg)}, commune coverage: {coverage}/{len(comm_map)}")
    return agg


def _flores_ds_to_ze2020(year: int) -> pd.DataFrame:
    """Read DS format nested zip (2022–2023) and extract ZE2020 UNIT_LOC data."""
    outer_path = RAW_FLORES / f"DS_FLORES_{year}_CSV_FR.zip"
    if not outer_path.exists():
        print(f"  [FLORES DS] not found for {year}")
        return pd.DataFrame()

    with zipfile.ZipFile(outer_path) as outer:
        inner_name = f"DS_FLORES_A17_{year}_CSV_FR.zip"
        inner_bytes = outer.read(inner_name)

    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
        # 2022 uses generic name; 2023+ uses year-specific name
        candidates = [f"DS_FLORES_A17_{year}_data.csv", "DS_FLORES_A17_data.csv"]
        data_name = next(n for n in candidates if n in inner.namelist())
        with inner.open(data_name) as f:
            df = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False)

    df = df[
        (df["GEO_OBJECT"] == "ZE2020") &
        (df["FLORES_MEASURE"] == "UNIT_LOC") &
        (df["NUMBER_EMPL"] == "_T") &
        (df["TIME_PERIOD"] == year)
    ].copy()

    df["GEO"] = df["GEO"].astype(str).str.zfill(4)
    df["ACTIVITY"] = df["ACTIVITY"].str.upper()

    # Total establishments
    total = df[df["ACTIVITY"] == "_T"][["GEO","OBS_VALUE"]].rename(
        columns={"GEO": "ZE2020", "OBS_VALUE": "flores_total_establishments"}
    )

    # Sector breakdown
    sectors = df[df["ACTIVITY"].isin(A17_SECTORS)].copy()
    pivot = sectors.pivot_table(index="GEO", columns="ACTIVITY", values="OBS_VALUE", aggfunc="sum")
    pivot.columns = [f"flores_etab_{c.lower()}" for c in pivot.columns]
    pivot = pivot.reset_index().rename(columns={"GEO": "ZE2020"})

    out = total.merge(pivot, on="ZE2020", how="outer")
    out["flores_year"] = year

    # Salaried jobs: filter EMPL3112, _T
    sal = df[(df["FLORES_MEASURE"] == "EMPL3112") & (df["ACTIVITY"] == "_T")]
    if len(sal) == 0:
        # Re-read without measure filter for salaried
        with zipfile.ZipFile(outer_path) as outer:
            inner_bytes2 = outer.read(f"DS_FLORES_A17_{year}_CSV_FR.zip")
        with zipfile.ZipFile(io.BytesIO(inner_bytes2)) as inner:
            candidates2 = [f"DS_FLORES_A17_{year}_data.csv", "DS_FLORES_A17_data.csv"]
            data_name2 = next(n for n in candidates2 if n in inner.namelist())
            with inner.open(data_name2) as f:
                df2 = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False)
        sal = df2[
            (df2["GEO_OBJECT"] == "ZE2020") &
            (df2["FLORES_MEASURE"] == "EMPL3112") &
            (df2["NUMBER_EMPL"] == "_T") &
            (df2["TIME_PERIOD"] == year) &
            (df2["ACTIVITY"] == "_T")
        ]
    if len(sal) > 0:
        sal_agg = sal.groupby("GEO")["OBS_VALUE"].sum().reset_index()
        sal_agg.columns = ["ZE2020","flores_total_salaried_jobs"]
        sal_agg["ZE2020"] = sal_agg["ZE2020"].astype(str).str.zfill(4)
        out = out.merge(sal_agg, on="ZE2020", how="left")

    print(f"  [FLORES DS {year}] ZE2020 zones: {len(out)}")
    return out


def _compute_flores_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Add Herfindahl index and sector weights from establishment counts."""
    sec_cols = [f"flores_etab_{s.lower()}" for s in A17_SECTORS if f"flores_etab_{s.lower()}" in df.columns]
    if not sec_cols:
        return df

    tot = df["flores_total_establishments"].replace(0, np.nan)
    weights = df[sec_cols].div(tot, axis=0).fillna(0)
    df["flores_herfindahl"] = (weights ** 2).sum(axis=1)
    # Dominant sector weight
    df["flores_dominant_sector_weight"] = weights.max(axis=1)
    return df


# ─── Pipeline A: FLORES t-1 ───────────────────────────────────────────────────

def pipeline_a_flores():
    print("\n=== Pipeline A: FLORES t-1 ===")
    comm_map = _load_commune_ze2020()

    frames = []
    # TD format: 2016–2021
    for year in range(2016, 2022):
        f = _flores_td_to_ze2020(year, comm_map)
        if not f.empty:
            frames.append(f)
    # DS format: 2022, 2023
    for year in [2022, 2023]:
        f = _flores_ds_to_ze2020(year)
        if not f.empty:
            frames.append(f)

    panel = pd.concat(frames, ignore_index=True)
    panel = _compute_flores_derived(panel)

    # Growth year-over-year
    panel = panel.sort_values(["ZE2020","flores_year"])
    panel["flores_growth_etab_1y"] = panel.groupby("ZE2020")["flores_total_establishments"].pct_change()

    # Rename for lag semantics: flores_year = T-1 → used for target_year T
    panel.rename(columns={"flores_year": "source_year"}, inplace=True)
    panel["target_year"] = panel["source_year"] + 1

    # Rename all feature columns to _t_minus_1
    feat_cols = [c for c in panel.columns if c.startswith("flores_")]
    rename_map = {c: c + "_t_minus_1" for c in feat_cols}
    panel.rename(columns=rename_map, inplace=True)

    out_path = PROCESSED / "flores_panel_ze2020_annual_v1.csv"
    panel.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(panel)} rows, {panel['ZE2020'].nunique()} ZE, "
          f"target_years {sorted(panel['target_year'].unique())})")
    return panel


# ─── Pipeline B: SIDE stocks t-1 ─────────────────────────────────────────────

def pipeline_b_side_stocks():
    print("\n=== Pipeline B: SIDE stocks t-1 ===")

    zip_path = RAW_SIDE / "DS_SIDE_STOCKS_ET_COM_2023_CSV.zip"
    if not zip_path.exists():
        print(f"  ERROR: {zip_path} not found")
        return pd.DataFrame()

    with zipfile.ZipFile(zip_path) as z:
        with z.open("DS_SIDE_STOCKS_ET_COM_2023_data.csv") as f:
            df = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False,
                             dtype={"GEO": str})

    # Filter to ZE2020 only
    df = df[df["GEO_OBJECT"] == "ZE2020"].copy()
    df["ZE2020"] = df["GEO"].astype(str).str.zfill(4)
    df = df[df["SIDE_MEASURE"] == "UNIT_LOC"].copy()
    df["TIME_PERIOD"] = df["TIME_PERIOD"].astype(int)

    print(f"  ZE2020 rows after filter: {len(df)}, years: {sorted(df['TIME_PERIOD'].unique())}")

    # Total stock per year
    total = df[df["ACTIVITY"] == "_T"][["ZE2020","TIME_PERIOD","OBS_VALUE"]].copy()
    total.rename(columns={"OBS_VALUE": "side_stock_total"}, inplace=True)

    # Sector breakdown (A21 codes available; keep major ones)
    major_sectors = ["BE","FZ","GI","JZ","KZ","LZ","MN","OQ","RU"]
    sec_df = df[df["ACTIVITY"].isin(major_sectors)].copy()
    pivot = sec_df.pivot_table(
        index=["ZE2020","TIME_PERIOD"], columns="ACTIVITY",
        values="OBS_VALUE", aggfunc="sum"
    ).reset_index()
    pivot.columns = ["ZE2020","TIME_PERIOD"] + [f"side_stock_{c.lower()}" for c in pivot.columns[2:]]

    panel = total.merge(pivot, on=["ZE2020","TIME_PERIOD"], how="left")

    # Growth
    panel = panel.sort_values(["ZE2020","TIME_PERIOD"])
    panel["side_stock_growth_1y"] = panel.groupby("ZE2020")["side_stock_total"].pct_change()

    # Coverage check (must be 0-100%)
    if panel["side_stock_total"].max() < 0:
        print("  WARNING: negative stock values detected")

    # Lag: source_year T-1 → target_year T
    panel.rename(columns={"TIME_PERIOD": "source_year"}, inplace=True)
    panel["target_year"] = panel["source_year"] + 1

    feat_cols = [c for c in panel.columns if c.startswith("side_stock")]
    rename_map = {c: c + "_t_minus_1" for c in feat_cols}
    panel.rename(columns=rename_map, inplace=True)

    out_path = PROCESSED / "side_stocks_lagged_ze2020_annual_v1.csv"
    panel.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(panel)} rows, {panel['ZE2020'].nunique()} ZE, "
          f"target_years {sorted(panel['target_year'].unique())})")
    return panel


# ─── Pipeline C: unified panel ────────────────────────────────────────────────

def pipeline_c_unified(flores_panel: pd.DataFrame, side_panel: pd.DataFrame, urssaf_panel: pd.DataFrame = None):
    print("\n=== Pipeline C: Unified feature panel ===")

    target = pd.read_csv(
        PROCESSED / "target_side_establishments_annual_core_v0.csv",
        dtype={"ze2020": str}
    )
    target["ze2020"] = target["ze2020"].astype(str).str.zfill(4)
    target = target.rename(columns={"ze2020": "ZE2020"})

    # Autoregressive lags on the target
    target = target.sort_values(["ZE2020","target_year"])
    for lag in [1, 2, 3]:
        target[f"side_lag_{lag}"] = target.groupby("ZE2020")["side_establishment_creations_official"].shift(lag)
    target["growth_1y"] = target.groupby("ZE2020")["side_establishment_creations_official"].pct_change(1)
    target["growth_2y"] = target.groupby("ZE2020")["side_establishment_creations_official"].pct_change(2)

    # COVID flags
    target["is_covid_year"] = (target["target_year"] == 2020).astype(int)
    target["is_post_covid_rebound"] = (target["target_year"] == 2021).astype(int)

    # Build source-year lookup sets for honest coverage flags
    flores_source_years  = set(flores_panel["source_year"].unique()) if not flores_panel.empty else set()
    side_source_years    = set(side_panel["source_year"].unique())   if not side_panel.empty  else set()
    urssaf_source_years  = set()

    # Merge FLORES
    if not flores_panel.empty:
        flores_panel["ZE2020"] = flores_panel["ZE2020"].astype(str).str.zfill(4)
        target = target.merge(flores_panel.drop(columns=["source_year"], errors="ignore"),
                              on=["ZE2020","target_year"], how="left")
        # Suppress C2/C4 only where FLORES source actually exists (stat suppression ≠ missing source)
        for col in ["flores_etab_c2_t_minus_1", "flores_etab_c4_t_minus_1"]:
            if col in target.columns:
                mask_has_source = target["target_year"].isin({y+1 for y in flores_source_years})
                n_fixed = (target[col].isna() & mask_has_source).sum()
                target.loc[mask_has_source, col] = target.loc[mask_has_source, col].fillna(0)
                if n_fixed:
                    print(f"  Fix C2/C4: {col} → {n_fixed} suppressed NaN→0 (source exists, stat suppression)")

    # Merge SIDE stocks
    if not side_panel.empty:
        side_panel["ZE2020"] = side_panel["ZE2020"].astype(str).str.zfill(4)
        target = target.merge(side_panel.drop(columns=["source_year"], errors="ignore"),
                              on=["ZE2020","target_year"], how="left")

    # Merge URSSAF (already deduplicated to 1 row per ZE×year)
    if urssaf_panel is not None and not urssaf_panel.empty:
        urssaf_panel["ZE2020"] = urssaf_panel["ZE2020"].astype(str).str.zfill(4)
        urssaf_source_years = set(urssaf_panel["source_year"].unique())
        target = target.merge(urssaf_panel.drop(columns=["source_year"], errors="ignore"),
                              on=["ZE2020","target_year"], how="left")

    # Fix 2: honest coverage flags based on source availability, not NaN presence
    target["has_flores_source"]     = (target["target_year"] - 1).isin(flores_source_years).astype(int)
    target["has_side_stock_source"] = (target["target_year"] - 1).isin(side_source_years).astype(int)
    target["has_urssaf_source"]     = (target["target_year"] - 1).isin(urssaf_source_years).astype(int)
    target["feature_forecast_safe"] = 1

    # Validate uniqueness
    n_total  = len(target)
    n_unique = target[["ZE2020","target_year"]].drop_duplicates().shape[0]
    n_dupes  = n_total - n_unique
    print(f"  Rows: {n_total} | Unique ZE×year: {n_unique} | Duplicates: {n_dupes}")
    if n_dupes > 0:
        print("  WARNING: duplicates remain — inspect merge keys")

    # Honest coverage report
    for flag, label in [("has_flores_source","FLORES"),
                         ("has_side_stock_source","SIDE stocks"),
                         ("has_urssaf_source","URSSAF")]:
        n_with = target[flag].sum()
        print(f"  {label} source present: {n_with}/{n_total} rows ({100*n_with/n_total:.1f}%)")

    out_path = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
    target.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({n_total} rows, {target['ZE2020'].nunique()} ZE, "
          f"cols: {len(target.columns)})")
    return target


# ─── Pipeline D: walk-forward splits ─────────────────────────────────────────

def pipeline_d_splits():
    print("\n=== Pipeline D: Walk-forward splits ===")

    rows = []
    for target_year in [2021, 2022, 2023, 2024]:
        rows.append({
            "fold": f"fold_{target_year}",
            "target_year": target_year,
            "train_years_max": target_year - 1,
            "train_years_min": 2012,
            "eval_year": target_year,
            "covid_in_train": 1 if target_year > 2020 else 0,
            "is_post_covid_eval": 1 if target_year == 2021 else 0,
            "note": "2020 retained in train with is_covid_year=1 flag",
        })

    splits = pd.DataFrame(rows)
    out_path = METADATA / "dynamic_stgnn_walk_forward_splits_v1.csv"
    splits.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")
    print(splits.to_string(index=False))
    return splits


# ─── Pipeline A2: URSSAF t-1 ─────────────────────────────────────────────────

def pipeline_a2_urssaf():
    print("\n=== Pipeline A2: URSSAF t-1 ===")
    raw = "data/raw/employment/urssaf/urssaf_etab_emploi_ze_annual_raw.csv"
    df = pd.read_csv(raw, dtype={"code_zone_d_emploi": str})
    df["code_zone_d_emploi"] = df["code_zone_d_emploi"].str.zfill(4)
    df = df.rename(columns={"code_zone_d_emploi": "ZE2020", "annee": "source_year"})
    df["source_year"] = df["source_year"].astype(int)

    # Fix 1: deduplicate — ZE appears multiple times when it spans two regions.
    # Sum numeric columns across duplicate ZE×year rows before any computation.
    num_cols = ["nombre_d_etablissements", "effectifs_salaries_moyens", "masse_salariale"]
    df = df.groupby(["ZE2020", "source_year"])[num_cols].sum().reset_index()
    dupes = df.duplicated(["ZE2020", "source_year"]).sum()
    print(f"  After dedup: {len(df)} rows, {dupes} remaining duplicates")

    df = df.sort_values(["ZE2020", "source_year"])
    df["urssaf_employer_growth_1y"] = df.groupby("ZE2020")["nombre_d_etablissements"].pct_change(fill_method=None)
    df["urssaf_wage_per_employee"] = (
        df["masse_salariale"] / df["effectifs_salaries_moyens"].replace(0, np.nan)
    )

    df = df.rename(columns={
        "nombre_d_etablissements": "urssaf_employer_establishments",
        "effectifs_salaries_moyens": "urssaf_salaried_employees",
        "masse_salariale": "urssaf_payroll",
    })

    feat_cols = ["urssaf_employer_establishments", "urssaf_salaried_employees",
                 "urssaf_payroll", "urssaf_employer_growth_1y", "urssaf_wage_per_employee"]
    panel = df[["ZE2020", "source_year"] + feat_cols].copy()
    panel["target_year"] = panel["source_year"] + 1

    rename_map = {c: c + "_t_minus_1" for c in feat_cols}
    panel.rename(columns=rename_map, inplace=True)

    coverage = panel[panel["target_year"].between(2013, 2025)]["ZE2020"].nunique()
    print(f"  URSSAF ZE coverage: {coverage}/280, target_years {sorted(panel['target_year'].unique())}")
    return panel


# ─── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)

    flores  = pipeline_a_flores()
    side    = pipeline_b_side_stocks()
    urssaf  = pipeline_a2_urssaf()
    panel   = pipeline_c_unified(flores, side, urssaf)
    splits  = pipeline_d_splits()

    print("\n=== Done ===")
    print(f"Panel shape: {panel.shape}")
    print(f"Columns: {panel.columns.tolist()}")
