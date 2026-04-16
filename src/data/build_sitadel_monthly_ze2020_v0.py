import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "raw" / "external" / "sitadel" / "Donnees-mensuelles-communales-Locaux.2026-03.csv"
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
MONTHLY_OUTPUT_PATH = ROOT / "data" / "interim" / "tables" / "sitadel_monthly_surface_ze2020_v0.csv"
ANNUAL_FEATURE_OUTPUT_PATH = ROOT / "data" / "interim" / "tables" / "sitadel_monthly_derived_annual_ze2020_v0.csv"
QUALITY_PATH = ROOT / "reports" / "sitadel_monthly_surface_quality_v0.json"


def to_number(series):
    if series.dtype == object:
        series = series.str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def build_sitadel_monthly_ze2020(chunksize=1_000_000):
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    mapping = mapping[["CODGEO", "ZE2020"]].drop_duplicates()

    chunks = []
    rows_seen = 0
    rows_selected = 0
    usecols = ["ANNEE", "MOIS", "CODE_INSEE", "DESTINATION", "SDP_AUT", "SDP_COM"]

    for chunk in pd.read_csv(
        INPUT_PATH,
        sep=";",
        skiprows=1,
        dtype={"ANNEE": str, "MOIS": str, "CODE_INSEE": str, "DESTINATION": str},
        usecols=usecols,
        chunksize=chunksize,
    ):
        rows_seen += len(chunk)
        chunk = chunk[chunk["DESTINATION"] == "Ensemble des locaux non-residentiels"].copy()
        rows_selected += len(chunk)
        if chunk.empty:
            continue

        chunk["year"] = pd.to_numeric(chunk["ANNEE"], errors="coerce").astype("Int64")
        chunk["month"] = pd.to_numeric(chunk["MOIS"], errors="coerce").astype("Int64")
        chunk["sitadel_monthly_surface_autorisee"] = to_number(chunk["SDP_AUT"])
        chunk["sitadel_monthly_surface_commencee"] = to_number(chunk["SDP_COM"])
        chunk = chunk.rename(columns={"CODE_INSEE": "CODGEO"})

        joined = chunk.merge(mapping, on="CODGEO", how="inner")
        grouped = (
            joined.groupby(["ZE2020", "year", "month"], as_index=False)[
                ["sitadel_monthly_surface_autorisee", "sitadel_monthly_surface_commencee"]
            ]
            .sum()
        )
        chunks.append(grouped)

    if not chunks:
        raise RuntimeError("No SITADEL monthly rows were processed.")

    monthly = pd.concat(chunks, ignore_index=True)
    monthly = (
        monthly.groupby(["ZE2020", "year", "month"], as_index=False)[
            ["sitadel_monthly_surface_autorisee", "sitadel_monthly_surface_commencee"]
        ]
        .sum()
        .sort_values(["year", "month", "ZE2020"])
    )

    annual_input = monthly.copy()
    month_number = annual_input["month"].astype(int)
    for metric in ["autorisee", "commencee"]:
        source_col = f"sitadel_monthly_surface_{metric}"
        annual_input[f"sitadel_monthly_q1_{metric}"] = annual_input[source_col].where(month_number.between(1, 3), 0.0)
        annual_input[f"sitadel_monthly_h1_{metric}"] = annual_input[source_col].where(month_number.between(1, 6), 0.0)

    annual = (
        annual_input.groupby(["ZE2020", "year"], as_index=False)
        .agg(
            sitadel_monthly_total_autorisee=("sitadel_monthly_surface_autorisee", "sum"),
            sitadel_monthly_total_commencee=("sitadel_monthly_surface_commencee", "sum"),
            sitadel_monthly_q1_autorisee=("sitadel_monthly_q1_autorisee", "sum"),
            sitadel_monthly_q1_commencee=("sitadel_monthly_q1_commencee", "sum"),
            sitadel_monthly_h1_autorisee=("sitadel_monthly_h1_autorisee", "sum"),
            sitadel_monthly_h1_commencee=("sitadel_monthly_h1_commencee", "sum"),
        )
        .sort_values(["year", "ZE2020"])
    )

    os.makedirs(MONTHLY_OUTPUT_PATH.parent, exist_ok=True)
    monthly.to_csv(MONTHLY_OUTPUT_PATH, index=False)
    annual.to_csv(ANNUAL_FEATURE_OUTPUT_PATH, index=False)

    quality = {
        "source_file": str(INPUT_PATH.relative_to(ROOT)),
        "rows_seen": int(rows_seen),
        "rows_selected_nonres_total": int(rows_selected),
        "monthly_rows": int(len(monthly)),
        "annual_rows": int(len(annual)),
        "years_available": sorted(monthly["year"].dropna().astype(int).unique().tolist()),
        "months_available": sorted(monthly["month"].dropna().astype(int).unique().tolist()),
        "zones_count": int(monthly["ZE2020"].nunique()),
        "outputs": [
            str(MONTHLY_OUTPUT_PATH.relative_to(ROOT)),
            str(ANNUAL_FEATURE_OUTPUT_PATH.relative_to(ROOT)),
        ],
        "methodological_status": "candidate monthly local construction signal; evaluate lag/nowcast variants before canonical inclusion",
    }
    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    print(f"Saved monthly SITADEL surface to {MONTHLY_OUTPUT_PATH}")
    print(f"Saved derived annual SITADEL features to {ANNUAL_FEATURE_OUTPUT_PATH}")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    build_sitadel_monthly_ze2020()
