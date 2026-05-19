"""Build HERALD Phase 2H panels with official INSEE macro indicators.

Inputs are INSEE BDM ZIP exports downloaded manually from the INSEE site.
The generated columns are lagged by one target year:

    target_year=t receives the annual mean of monthly indicators in t-1.

That keeps the panel ex-ante for an annual forecast made after the previous
year's monthly releases are available.
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


CLIMAT_AFFAIRES_ID = "001565530"
CLIMAT_EMPLOI_ID = "001796629"
BDF_CONJ_SERVICES_CLIMATE_KEY = "CONJ.M.N01.S.SM.00NAT.ICASM182.1A"
BDF_GSTIX_COMP_KEY = "GSTIX.M.A1._Z.GSC._Z.GSTIX_COMP.BVAR"


def read_bdm_monthly_zip(path: Path, expected_id: str) -> tuple[pd.DataFrame, dict]:
    with zipfile.ZipFile(path) as zf:
        meta = zf.read("caractéristiques.csv").decode("utf-8-sig")
        values = zf.read("valeurs_mensuelles.csv").decode("utf-8-sig").splitlines()

    meta_rows = list(csv.DictReader(meta.splitlines(), delimiter=";"))
    meta_row = meta_rows[0] if meta_rows else {}
    idbank = str(meta_row.get("idBank", "")).strip()
    if idbank != expected_id:
        raise ValueError(f"{path} has idBank={idbank!r}, expected {expected_id!r}")

    rows = []
    for row in csv.reader(values, delimiter=";"):
        if not row or len(row) < 2:
            continue
        period = row[0].strip().strip('"')
        if len(period) != 7 or period[4] != "-":
            continue
        try:
            value = float(str(row[1]).replace(",", "."))
        except ValueError:
            continue
        rows.append((period, value, row[2].strip() if len(row) > 2 else ""))

    df = pd.DataFrame(rows, columns=["period", "value", "code"])
    if df.empty:
        raise ValueError(f"No monthly observations parsed from {path}")
    df["date"] = pd.to_datetime(df["period"] + "-01")
    df["year"] = df["date"].dt.year.astype(int)
    return df, meta_row


def annual_mean_lag(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    annual = (
        df.groupby("year", as_index=False)["value"]
        .mean()
        .rename(columns={"value": col_name, "year": "macro_year"})
    )
    annual["target_year"] = annual["macro_year"] + 1
    return annual[["target_year", col_name, "macro_year"]]


def read_webstat_long_csv(path: Path, series_key: str, value_col: str) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    if "series_key" not in df.columns:
        raise ValueError(f"{path} is not a Webstat long CSV: missing series_key")
    sub = df[df["series_key"].eq(series_key)].copy()
    if sub.empty:
        raise ValueError(f"Series {series_key!r} not found in {path}")
    sub = sub[sub["time_period"].astype(str).str.match(r"^\d{4}-\d{2}$", na=False)]
    sub[value_col] = (
        sub["obs_value"].astype(str).str.replace(",", ".", regex=False).astype(float)
    )
    sub["date"] = pd.to_datetime(sub["time_period"] + "-01")
    sub["year"] = sub["date"].dt.year.astype(int)
    meta_cols = [
        "series_key",
        "dataset_id",
        "title_fr",
        "title_long_fr",
        "updated_at",
        "FREQ",
        "SOURCE_AGENCY",
    ]
    meta = {
        c: str(sub[c].dropna().iloc[0])
        for c in meta_cols
        if c in sub.columns and not sub[c].dropna().empty
    }
    return sub[["time_period", "date", "year", value_col]].rename(
        columns={"time_period": "period", value_col: "value"}
    ), meta


def build_panel(args: argparse.Namespace) -> None:
    panel = pd.read_csv(args.base_panel)
    required_base = {"target_year", "ZE2020"}
    missing_base = sorted(required_base - set(panel.columns))
    if missing_base:
        raise ValueError(f"Base panel missing columns: {missing_base}")

    affaires, affaires_meta = read_bdm_monthly_zip(args.climat_affaires_zip, CLIMAT_AFFAIRES_ID)
    emploi, emploi_meta = read_bdm_monthly_zip(args.climat_emploi_zip, CLIMAT_EMPLOI_ID)
    bdf_conj, bdf_conj_meta = read_webstat_long_csv(
        args.bdf_conj_csv,
        BDF_CONJ_SERVICES_CLIMATE_KEY,
        "fr_bdf_conj_services_climate_t_minus_1",
    )
    gstix, gstix_meta = read_webstat_long_csv(
        args.gstix_csv,
        BDF_GSTIX_COMP_KEY,
        "fr_bdf_gstix_comp_t_minus_1",
    )

    aff_y = annual_mean_lag(affaires, "fr_climat_affaires_t_minus_1")
    emp_y = annual_mean_lag(emploi, "fr_climat_emploi_t_minus_1")
    bdf_conj_y = annual_mean_lag(bdf_conj, "fr_bdf_conj_services_climate_t_minus_1")
    gstix_y = annual_mean_lag(gstix, "fr_bdf_gstix_comp_t_minus_1")
    macro = aff_y.drop(columns=["macro_year"]).merge(
        emp_y.drop(columns=["macro_year"]), on="target_year", how="outer"
    )
    macro = macro.merge(
        bdf_conj_y.drop(columns=["macro_year"]), on="target_year", how="outer"
    ).merge(gstix_y.drop(columns=["macro_year"]), on="target_year", how="outer")
    macro = macro.sort_values("target_year")

    out = panel.merge(macro, on="target_year", how="left", validate="many_to_one")
    macro_cols = [
        "fr_climat_affaires_t_minus_1",
        "fr_climat_emploi_t_minus_1",
        "fr_bdf_conj_services_climate_t_minus_1",
        "fr_bdf_gstix_comp_t_minus_1",
    ]
    na_share = out[macro_cols].isna().mean().to_dict()
    if any(v > 0 for v in na_share.values()):
        raise ValueError(f"Macro columns contain missing values after merge: {na_share}")

    args.output_panel.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_panel, index=False)

    perm = out.copy()
    rng = np.random.default_rng(args.permutation_seed)
    years = np.array(sorted(perm["target_year"].unique()))
    shuffled = years.copy()
    rng.shuffle(shuffled)
    year_map = dict(zip(years, shuffled))
    annual_values = (
        out[["target_year", *macro_cols]]
        .drop_duplicates("target_year")
        .set_index("target_year")
    )
    for col in macro_cols:
        perm[col] = perm["target_year"].map(
            {int(y): float(annual_values.loc[year_map[int(y)], col]) for y in years}
        )
    args.output_permuted_panel.parent.mkdir(parents=True, exist_ok=True)
    perm.to_csv(args.output_permuted_panel, index=False)

    args.output_macro_csv.parent.mkdir(parents=True, exist_ok=True)
    macro.to_csv(args.output_macro_csv, index=False)

    audit = {
        "base_panel": str(args.base_panel),
        "output_panel": str(args.output_panel),
        "output_permuted_panel": str(args.output_permuted_panel),
        "n_rows": int(len(out)),
        "target_year_min": int(out["target_year"].min()),
        "target_year_max": int(out["target_year"].max()),
        "n_zones": int(out["ZE2020"].nunique()),
        "macro_columns": macro_cols,
        "macro_na_share": {k: float(v) for k, v in na_share.items()},
        "permutation_seed": int(args.permutation_seed),
        "source_series": {
            "fr_climat_affaires_t_minus_1": {
                "idbank": CLIMAT_AFFAIRES_ID,
                "file": str(args.climat_affaires_zip),
                "metadata": affaires_meta,
                "monthly_min": str(affaires["period"].min()),
                "monthly_max": str(affaires["period"].max()),
            },
            "fr_climat_emploi_t_minus_1": {
                "idbank": CLIMAT_EMPLOI_ID,
                "file": str(args.climat_emploi_zip),
                "metadata": emploi_meta,
                "monthly_min": str(emploi["period"].min()),
                "monthly_max": str(emploi["period"].max()),
            },
            "fr_bdf_conj_services_climate_t_minus_1": {
                "series_key": BDF_CONJ_SERVICES_CLIMATE_KEY,
                "file": str(args.bdf_conj_csv),
                "metadata": bdf_conj_meta,
                "monthly_min": str(bdf_conj["period"].min()),
                "monthly_max": str(bdf_conj["period"].max()),
            },
            "fr_bdf_gstix_comp_t_minus_1": {
                "series_key": BDF_GSTIX_COMP_KEY,
                "file": str(args.gstix_csv),
                "metadata": gstix_meta,
                "monthly_min": str(gstix["period"].min()),
                "monthly_max": str(gstix["period"].max()),
            },
        },
        "lag_rule": "target_year=t uses annual monthly mean observed in t-1",
        "manual_flags_added": False,
        "bdf_nowcast_added": False,
        "bdf_webstat_features_added": True,
    }
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(audit, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--base-panel",
        type=Path,
        default=Path("data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"),
    )
    p.add_argument(
        "--climat-affaires-zip",
        type=Path,
        default=Path("serie_001565530_15052026.zip"),
    )
    p.add_argument(
        "--climat-emploi-zip",
        type=Path,
        default=Path("serie_001796629_15052026.zip"),
    )
    p.add_argument(
        "--bdf-conj-csv",
        type=Path,
        default=Path("Webstat_Export_fr_CONJ (1).csv"),
    )
    p.add_argument(
        "--gstix-csv",
        type=Path,
        default=Path("Webstat_Export_fr_GSTIX (1).csv"),
    )
    p.add_argument(
        "--output-panel",
        type=Path,
        default=Path("data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv"),
    )
    p.add_argument(
        "--output-permuted-panel",
        type=Path,
        default=Path("data/processed/dynamic_stgnn_feature_panel_phase2h_macro_permuted_v1.csv"),
    )
    p.add_argument(
        "--output-macro-csv",
        type=Path,
        default=Path("data/processed/phase2h_macro_annual_features_v1.csv"),
    )
    p.add_argument(
        "--audit-json",
        type=Path,
        default=Path("reports/phase2h_macro_panel_audit.json"),
    )
    p.add_argument("--permutation-seed", type=int, default=20260515)
    return p.parse_args()


if __name__ == "__main__":
    build_panel(parse_args())
