"""
Integrate INSEE SIDE 2012-2025 creation files for HERALD V6 validation.

Inputs expected in ~/Downloads:
  - DS_SIDE_CREA_ETAB_COM_2025_CSV.zip  (creations d'etablissements, 2012-2025, geo 2025)
  - DS_SIDE_CREA_ENT_COM_2025_CSV.zip   (creations d'entreprises, 2012-2025, geo 2025)

The older sidemo2025_* detail files are accepted as a fallback for the 2025
target only, but the preferred source is the complete 2012-2025 SIDE release.

Outputs are additive, preserving the 2012-2024 training artifacts:
  - data/processed/target_side_establishments_annual_core_through_2025_v1.csv
  - data/processed/side_creations_a10_ze2020_through_2025_v1.csv
  - data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv
  - metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = Path.home() / "Downloads"
RAW_SIDE = ROOT / "data/raw/business_demography/side"
RAW_FLORES = ROOT / "data/raw/employment/flores"
RAW_URSSAF = ROOT / "data/raw/employment/urssaf"
PROCESSED = ROOT / "data/processed"
METADATA = ROOT / "metadata"

CREA_ETAB_FULL_ZIP = RAW_SIDE / "DS_SIDE_CREA_ETAB_COM_2025_CSV.zip"
CREA_ENT_FULL_ZIP = RAW_SIDE / "DS_SIDE_CREA_ENT_COM_2025_CSV.zip"
CRETS_DETAIL_ZIP = RAW_SIDE / "sidemo2025_crets_2025_csv.zip"
CRENT_DETAIL_ZIP = RAW_SIDE / "sidemo2025_crent_2025_csv.zip"

CORE_PATH = PROCESSED / "graph_node_index_core_v0.csv"
TARGET_OLD = PROCESSED / "target_side_establishments_annual_core_v0.csv"
A10_OLD = PROCESSED / "side_creations_a10_ze2020_v1.csv"
PANEL_OLD = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"

A10_SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
A17_SECTORS = ["AZ", "DE", "C1", "C2", "C3", "C4", "C5", "FZ", "GZ", "HZ", "IZ", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def _require_inputs() -> None:
    missing = [str(p) for p in [TARGET_OLD, A10_OLD, PANEL_OLD, CORE_PATH] if not p.exists()]
    has_full = CREA_ETAB_FULL_ZIP.exists() and CREA_ENT_FULL_ZIP.exists()
    has_detail = CRETS_DETAIL_ZIP.exists() and CRENT_DETAIL_ZIP.exists()
    if not has_full and not has_detail:
        missing.extend([str(CREA_ETAB_FULL_ZIP), str(CREA_ENT_FULL_ZIP)])
    if missing:
        raise SystemExit("Missing required files:\n" + "\n".join(missing))


def _copy_raw_files() -> None:
    RAW_SIDE.mkdir(parents=True, exist_ok=True)
    for name in [
        "DS_SIDE_CREA_ETAB_COM_2025_CSV.zip",
        "DS_SIDE_CREA_ENT_COM_2025_CSV.zip",
        "sidemo2025_crets_2025_csv.zip",
        "sidemo2025_crent_2025_csv.zip",
    ]:
        src = DOWNLOADS / name
        dst = RAW_SIDE / name
        if src.exists() and (not dst.exists() or dst.stat().st_size != src.stat().st_size):
            shutil.copy2(src, dst)
            print(f"Copied: {dst}")


def _read_side_2025(zip_path: Path, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as f:
            df = pd.read_csv(
                f,
                sep=";",
                dtype={"ZE": str, "A10": str, "FREQ": str},
                usecols=["ZE", "A10", "FREQ"],
            )
    df["ZE2020"] = pd.to_numeric(df["ZE"].str.zfill(4), errors="coerce").astype("Int64")
    df["FREQ"] = pd.to_numeric(df["FREQ"], errors="coerce").fillna(0.0)
    df = df[df["ZE2020"].notna()].copy()
    df["ZE2020"] = df["ZE2020"].astype(int)
    return df


def _read_side_complete(zip_path: Path, member: str, activities: list[str]) -> pd.DataFrame:
    """Read the official SIDE 2012-2025 release at ZE2020 level in geo 2025."""
    keep = []
    usecols = ["GEO", "GEO_OBJECT", "ACTIVITY", "LEGAL_FORM", "FREQ", "TIME_PERIOD", "OBS_VALUE"]
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as raw:
            for chunk in pd.read_csv(
                raw,
                sep=";",
                usecols=usecols,
                dtype={"GEO": str, "ACTIVITY": str, "LEGAL_FORM": str, "FREQ": str},
                chunksize=500_000,
                low_memory=False,
            ):
                sub = chunk[
                    (chunk["GEO_OBJECT"] == "ZE2020")
                    & (chunk["LEGAL_FORM"] == "_T")
                    & (chunk["FREQ"] == "A")
                    & (chunk["ACTIVITY"].isin(activities))
                ].copy()
                if not sub.empty:
                    keep.append(sub[["GEO", "ACTIVITY", "TIME_PERIOD", "OBS_VALUE"]])
    if not keep:
        raise RuntimeError(f"No ZE2020 SIDE rows found in {zip_path.name}:{member}")
    df = pd.concat(keep, ignore_index=True)
    df["ZE2020"] = pd.to_numeric(df["GEO"].astype(str).str.zfill(4), errors="coerce").astype("Int64")
    df["target_year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce").fillna(0.0)
    df = df[df["ZE2020"].notna() & df["target_year"].notna()].copy()
    df["ZE2020"] = df["ZE2020"].astype(int)
    df["target_year"] = df["target_year"].astype(int)
    return df[["target_year", "ZE2020", "ACTIVITY", "OBS_VALUE"]]


def _has_complete_side_release() -> bool:
    return CREA_ETAB_FULL_ZIP.exists() and CREA_ENT_FULL_ZIP.exists()


def _build_2025_targets(core: pd.DataFrame) -> pd.DataFrame:
    crets = _read_side_2025(CRETS_DETAIL_ZIP, "FD_CRETS_2025.csv")
    crent = _read_side_2025(CRENT_DETAIL_ZIP, "FD_CRENT_2025.csv")

    etab = crets.groupby("ZE2020", as_index=False)["FREQ"].sum().rename(
        columns={"FREQ": "side_establishment_creations_official"}
    )
    ent = crent.groupby("ZE2020", as_index=False)["FREQ"].sum().rename(
        columns={"FREQ": "side_enterprise_creations_official"}
    )

    target_2025 = (
        core[["node_idx", "ze2020", "libze2020", "nb_com"]]
        .rename(columns={"ze2020": "ZE2020", "nb_com": "communes_count"})
        .merge(ent, on="ZE2020", how="left")
        .merge(etab, on="ZE2020", how="left")
    )
    target_2025["target_year"] = 2025
    for col in ["side_enterprise_creations_official", "side_establishment_creations_official"]:
        target_2025[col] = target_2025[col].fillna(0.0)
    target_2025 = target_2025[
        [
            "target_year",
            "ZE2020",
            "node_idx",
            "libze2020",
            "side_enterprise_creations_official",
            "side_establishment_creations_official",
            "communes_count",
        ]
    ].rename(columns={"ZE2020": "ze2020"})
    return target_2025


def _build_targets_from_complete_release(core: pd.DataFrame) -> pd.DataFrame:
    etab_raw = _read_side_complete(CREA_ETAB_FULL_ZIP, "DS_SIDE_CREA_ETAB_COM_2025_data.csv", ["_T"])
    ent_raw = _read_side_complete(CREA_ENT_FULL_ZIP, "DS_SIDE_CREA_ENT_COM_2025_data.csv", ["_T"])
    etab = etab_raw.rename(columns={"OBS_VALUE": "side_establishment_creations_official"})
    ent = ent_raw.rename(columns={"OBS_VALUE": "side_enterprise_creations_official"})

    years = sorted(set(etab["target_year"]).intersection(set(ent["target_year"])))
    grid = core[["node_idx", "ze2020", "libze2020", "nb_com"]].rename(columns={"nb_com": "communes_count"})
    grid = grid.assign(_key=1).merge(pd.DataFrame({"target_year": years, "_key": 1}), on="_key").drop(columns="_key")
    out = (
        grid.rename(columns={"ze2020": "ZE2020"})
        .merge(ent[["target_year", "ZE2020", "side_enterprise_creations_official"]], on=["target_year", "ZE2020"], how="left")
        .merge(etab[["target_year", "ZE2020", "side_establishment_creations_official"]], on=["target_year", "ZE2020"], how="left")
    )
    for col in ["side_enterprise_creations_official", "side_establishment_creations_official"]:
        out[col] = out[col].fillna(0.0)
    out = out.rename(columns={"ZE2020": "ze2020"})
    out = out[
        [
            "target_year",
            "ze2020",
            "node_idx",
            "libze2020",
            "side_enterprise_creations_official",
            "side_establishment_creations_official",
            "communes_count",
        ]
    ]
    return out.sort_values(["ze2020", "target_year"]).reset_index(drop=True)


def build_target_through_2025(core: pd.DataFrame) -> pd.DataFrame:
    if _has_complete_side_release():
        print("Using complete SIDE creations release 2012-2025 for targets.")
        out = _build_targets_from_complete_release(core)
    else:
        print("Complete SIDE release not found; falling back to old 2012-2024 + sidemo2025 detail files.")
        old = pd.read_csv(TARGET_OLD)
        old = old[old["target_year"] <= 2024].copy()
        target_2025 = _build_2025_targets(core)
        out = pd.concat([old, target_2025], ignore_index=True).sort_values(["ze2020", "target_year"])
    path = PROCESSED / "target_side_establishments_annual_core_through_2025_v1.csv"
    out.to_csv(path, index=False)
    print(f"Saved: {path} rows={len(out)} years={out['target_year'].min()}-{out['target_year'].max()}")
    return out


def build_a10_through_2025(core: pd.DataFrame) -> pd.DataFrame:
    if _has_complete_side_release():
        print("Using complete SIDE creations release 2012-2025 for A10 sector targets.")
        crets = _read_side_complete(CREA_ETAB_FULL_ZIP, "DS_SIDE_CREA_ETAB_COM_2025_data.csv", A10_SECTORS)
        pivot = crets.pivot_table(
            index=["target_year", "ZE2020"], columns="ACTIVITY", values="OBS_VALUE", aggfunc="sum", fill_value=0.0
        ).reset_index()
        years = sorted(pivot["target_year"].unique())
        grid = core[["ze2020"]].rename(columns={"ze2020": "ZE2020"}).assign(_key=1).merge(
            pd.DataFrame({"target_year": years, "_key": 1}), on="_key"
        ).drop(columns="_key")
        pivot = grid.merge(pivot, on=["target_year", "ZE2020"], how="left")
        for sector in A10_SECTORS:
            if sector not in pivot.columns:
                pivot[sector] = 0.0
            pivot[sector] = pivot[sector].fillna(0.0)
        pivot["total"] = pivot[A10_SECTORS].sum(axis=1)
        out = pivot[["target_year", "ZE2020"] + A10_SECTORS + ["total"]].sort_values(["ZE2020", "target_year"])
    else:
        old = pd.read_csv(A10_OLD)
        old = old[old["target_year"] <= 2024].copy()
        crets = _read_side_2025(CRETS_DETAIL_ZIP, "FD_CRETS_2025.csv")
        crets = crets[crets["A10"].isin(A10_SECTORS)].copy()
        pivot = crets.pivot_table(index="ZE2020", columns="A10", values="FREQ", aggfunc="sum", fill_value=0.0)
        for sector in A10_SECTORS:
            if sector not in pivot.columns:
                pivot[sector] = 0.0
        pivot = pivot[A10_SECTORS].reset_index()
        pivot = core[["ze2020"]].rename(columns={"ze2020": "ZE2020"}).merge(pivot, on="ZE2020", how="left")
        for sector in A10_SECTORS:
            pivot[sector] = pivot[sector].fillna(0.0)
        pivot["total"] = pivot[A10_SECTORS].sum(axis=1)
        pivot["target_year"] = 2025
        pivot = pivot[["target_year", "ZE2020"] + A10_SECTORS + ["total"]]
        out = pd.concat([old, pivot], ignore_index=True).sort_values(["ZE2020", "target_year"])
    path = PROCESSED / "side_creations_a10_ze2020_through_2025_v1.csv"
    out.to_csv(path, index=False)
    print(f"Saved: {path} rows={len(out)} years={out['target_year'].min()}-{out['target_year'].max()}")
    return out


def _load_flores_2024() -> pd.DataFrame:
    path = RAW_FLORES / "DS_FLORES_A17_2024_CSV_FR.zip"
    if not path.exists():
        print("FLORES 2024 not found; 2025 panel will mark has_flores_source=0")
        return pd.DataFrame()

    keep = []
    with zipfile.ZipFile(path) as zf:
        with zf.open("DS_FLORES_A17_2024_data.csv") as raw:
            text = io.TextIOWrapper(raw, encoding="latin1")
            for chunk in pd.read_csv(text, sep=";", chunksize=500_000, dtype={"GEO": str}, low_memory=False):
                sub = chunk[
                    (chunk["GEO_OBJECT"] == "ZE2020")
                    & (chunk["TIME_PERIOD"] == 2024)
                    & (chunk["NUMBER_EMPL"] == "_T")
                    & (chunk["ACTIVITY"].isin(A17_SECTORS + ["_T"]))
                    & (chunk["FLORES_MEASURE"].isin(["UNIT_LOC", "EMPL3112"]))
                ].copy()
                if not sub.empty:
                    keep.append(sub[["GEO", "ACTIVITY", "FLORES_MEASURE", "OBS_VALUE"]])
    if not keep:
        return pd.DataFrame()
    df = pd.concat(keep, ignore_index=True)
    df["ZE2020"] = pd.to_numeric(df["GEO"].astype(str).str.zfill(4), errors="coerce").astype("Int64")
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce").fillna(0.0)
    df = df[df["ZE2020"].notna()].copy()
    df["ZE2020"] = df["ZE2020"].astype(int)

    unit = df[df["FLORES_MEASURE"] == "UNIT_LOC"]
    total = unit[unit["ACTIVITY"] == "_T"].groupby("ZE2020", as_index=False)["OBS_VALUE"].sum().rename(
        columns={"OBS_VALUE": "flores_total_establishments_t_minus_1"}
    )
    sectors = unit[unit["ACTIVITY"].isin(A17_SECTORS)].pivot_table(
        index="ZE2020", columns="ACTIVITY", values="OBS_VALUE", aggfunc="sum", fill_value=0.0
    )
    sectors.columns = [f"flores_etab_{c.lower()}_t_minus_1" for c in sectors.columns]
    sectors = sectors.reset_index()
    out = total.merge(sectors, on="ZE2020", how="outer")
    sal = df[(df["FLORES_MEASURE"] == "EMPL3112") & (df["ACTIVITY"] == "_T")]
    if not sal.empty:
        sal = sal.groupby("ZE2020", as_index=False)["OBS_VALUE"].sum().rename(
            columns={"OBS_VALUE": "flores_total_salaried_jobs_t_minus_1"}
        )
        out = out.merge(sal, on="ZE2020", how="left")

    sec_cols = [c for c in out.columns if c.startswith("flores_etab_") and c.endswith("_t_minus_1")]
    denom = out["flores_total_establishments_t_minus_1"].replace(0, np.nan)
    weights = out[sec_cols].div(denom, axis=0).fillna(0.0)
    out["flores_herfindahl_t_minus_1"] = (weights**2).sum(axis=1)
    out["flores_dominant_sector_weight_t_minus_1"] = weights.max(axis=1)

    old_flores = pd.read_csv(PROCESSED / "flores_panel_ze2020_annual_v1.csv")
    prev = old_flores[old_flores["target_year"] == 2024][["ZE2020", "flores_total_establishments_t_minus_1"]].rename(
        columns={"flores_total_establishments_t_minus_1": "prev_flores_total"}
    )
    out = out.merge(prev, on="ZE2020", how="left")
    out["flores_growth_etab_1y_t_minus_1"] = (
        out["flores_total_establishments_t_minus_1"] - out["prev_flores_total"]
    ) / out["prev_flores_total"].replace(0, np.nan)
    out = out.drop(columns=["prev_flores_total"])
    out["target_year"] = 2025
    out["source_year"] = 2024
    return out


def _load_urssaf_2024() -> pd.DataFrame:
    path = RAW_URSSAF / "urssaf_etab_emploi_ze_annual_raw.csv"
    df = pd.read_csv(path, dtype={"code_zone_d_emploi": str})
    df["ZE2020"] = pd.to_numeric(df["code_zone_d_emploi"].str.zfill(4), errors="coerce").astype("Int64")
    df = df[(df["annee"] == 2024) & df["ZE2020"].notna()].copy()
    df["ZE2020"] = df["ZE2020"].astype(int)
    num_cols = ["nombre_d_etablissements", "effectifs_salaries_moyens", "masse_salariale"]
    out = df.groupby("ZE2020", as_index=False)[num_cols].sum()
    hist = pd.read_csv(path, dtype={"code_zone_d_emploi": str})
    hist["ZE2020"] = pd.to_numeric(hist["code_zone_d_emploi"].str.zfill(4), errors="coerce").astype("Int64")
    hist = hist[hist["ZE2020"].notna()].copy()
    hist["ZE2020"] = hist["ZE2020"].astype(int)
    hist = hist.groupby(["ZE2020", "annee"], as_index=False)[num_cols].sum().sort_values(["ZE2020", "annee"])
    hist["growth"] = hist.groupby("ZE2020")["nombre_d_etablissements"].pct_change(fill_method=None)
    growth = hist[hist["annee"] == 2024][["ZE2020", "growth"]]
    out = out.merge(growth, on="ZE2020", how="left")
    out["urssaf_wage_per_employee_t_minus_1"] = out["masse_salariale"] / out["effectifs_salaries_moyens"].replace(0, np.nan)
    out = out.rename(
        columns={
            "nombre_d_etablissements": "urssaf_employer_establishments_t_minus_1",
            "effectifs_salaries_moyens": "urssaf_salaried_employees_t_minus_1",
            "masse_salariale": "urssaf_payroll_t_minus_1",
            "growth": "urssaf_employer_growth_1y_t_minus_1",
        }
    )
    out["target_year"] = 2025
    return out


def build_feature_panel_through_2025(target: pd.DataFrame, core: pd.DataFrame) -> pd.DataFrame:
    old_panel = pd.read_csv(PANEL_OLD)
    old_panel = old_panel[old_panel["target_year"] <= 2024].copy()
    work = target.rename(columns={"ze2020": "ZE2020"}).copy().sort_values(["ZE2020", "target_year"])
    for lag in [1, 2, 3]:
        work[f"side_lag_{lag}"] = work.groupby("ZE2020")["side_establishment_creations_official"].shift(lag)
    work["growth_1y"] = work.groupby("ZE2020")["side_establishment_creations_official"].pct_change(1)
    work["growth_2y"] = work.groupby("ZE2020")["side_establishment_creations_official"].pct_change(2)
    work["is_covid_year"] = (work["target_year"] == 2020).astype(int)
    work["is_post_covid_rebound"] = (work["target_year"] == 2021).astype(int)

    replacement_cols = [
        "side_enterprise_creations_official",
        "side_establishment_creations_official",
        "communes_count",
        "side_lag_1",
        "side_lag_2",
        "side_lag_3",
        "growth_1y",
        "growth_2y",
        "is_covid_year",
        "is_post_covid_rebound",
    ]
    old_panel = old_panel.drop(columns=[c for c in replacement_cols if c in old_panel.columns])
    old_panel = old_panel.merge(
        work[["target_year", "ZE2020"] + replacement_cols],
        on=["target_year", "ZE2020"],
        how="left",
    )

    row_2025 = work[work["target_year"] == 2025].copy()

    flores = _load_flores_2024()
    if not flores.empty:
        row_2025 = row_2025.merge(flores.drop(columns=["source_year"], errors="ignore"), on=["ZE2020", "target_year"], how="left")
        for col in ["flores_etab_c2_t_minus_1", "flores_etab_c4_t_minus_1"]:
            if col in row_2025.columns:
                row_2025[col] = row_2025[col].fillna(0.0)

    urssaf = _load_urssaf_2024()
    row_2025 = row_2025.merge(urssaf, on=["ZE2020", "target_year"], how="left")

    row_2025["has_flores_source"] = 0 if flores.empty else 1
    row_2025["has_side_stock_source"] = 0
    row_2025["has_urssaf_source"] = 1
    row_2025["feature_forecast_safe"] = 1

    for col in old_panel.columns:
        if col not in row_2025.columns:
            row_2025[col] = np.nan
    row_2025 = row_2025[old_panel.columns]
    out = pd.concat([old_panel, row_2025], ignore_index=True).sort_values(["ZE2020", "target_year"])
    path = PROCESSED / "dynamic_stgnn_feature_panel_through_2025_v1.csv"
    out.to_csv(path, index=False)
    print(f"Saved: {path} rows={len(out)} years={out['target_year'].min()}-{out['target_year'].max()} cols={len(out.columns)}")
    print("2025 coverage flags:", out[out["target_year"] == 2025][["has_flores_source", "has_side_stock_source", "has_urssaf_source"]].mean().to_dict())
    return out


def build_splits_through_2025() -> pd.DataFrame:
    rows = []
    for year in [2021, 2022, 2023, 2024, 2025]:
        rows.append(
            {
                "fold": f"fold_{year}",
                "target_year": year,
                "train_years_max": year - 1,
                "train_years_min": 2012,
                "eval_year": year,
                "covid_in_train": 1 if year > 2020 else 0,
                "is_post_covid_eval": 1 if year == 2021 else 0,
                "note": "2025 observed SIDE validation fold from complete INSEE SIDE 2012-2025 release in geo 2025" if year == 2025 else "2020 retained in train with is_covid_year=1 flag",
            }
        )
    out = pd.DataFrame(rows)
    path = METADATA / "dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"
    out.to_csv(path, index=False)
    print(f"Saved: {path}")
    print(out.to_string(index=False))
    return out


def main() -> None:
    _require_inputs()
    _copy_raw_files()
    core = pd.read_csv(CORE_PATH)
    core["ze2020"] = pd.to_numeric(core["ze2020"], errors="coerce").astype(int)
    target = build_target_through_2025(core)
    build_a10_through_2025(core)
    build_feature_panel_through_2025(target, core)
    build_splits_through_2025()


if __name__ == "__main__":
    main()
