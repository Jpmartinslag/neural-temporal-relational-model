import csv
import json
import os
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_ZIP = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "energy"
    / "Données locales de consommation d'électricité, de gaz naturel et de chaleur et de froid - IRIS (à partir de 2018).zip"
)
HISTORICAL_ELECTRICITY_PATH = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "energy"
    / "Donnees-locales-de-consommation-denergie-periode-2008-2017-electricite.2017-12.csv"
)
HISTORICAL_GAS_PATH = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "energy"
    / "Donnees-locales-de-consommation-denergie-periode-2008-2017-gaz.2017-12.csv"
)
HISTORICAL_HEAT_COLD_PATH = (
    ROOT
    / "data"
    / "raw"
    / "external"
    / "energy"
    / "Donnees-locales-de-consommation-denergie-periode-2008-2017-chaleur-et-froid.2017-12.csv"
)
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
OUTPUT_PATH = ROOT / "data" / "interim" / "tables" / "energy_consumption_ze2020_v0.csv"
QUALITY_PATH = ROOT / "reports" / "energy_consumption_quality_v0.json"


def fuel_from_name(name):
    lower = name.lower()
    if "electricite" in lower:
        return "electricity"
    if "gaz-naturel" in lower:
        return "gas"
    if "chaleur" in lower:
        return "heat_cold"
    return None


def to_number(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)


def aggregate_energy_chunks(chunks, mapping):
    long = pd.concat(chunks, ignore_index=True)
    long = long.groupby(["ZE2020", "ANNEE", "fuel"], as_index=False)[["CONSO", "PDL"]].sum()

    wide = long.pivot_table(index=["ZE2020", "ANNEE"], columns="fuel", values=["CONSO", "PDL"], aggfunc="sum")
    wide.columns = [f"energy_{fuel}_{metric.lower()}_nonres" for metric, fuel in wide.columns]
    return wide.reset_index().rename(columns={"ANNEE": "year"}).sort_values(["year", "ZE2020"])


def select_best_historical_level(frame):
    # SDES historical files can contain the same year at multiple geographic levels.
    # Prefer IRIS when present to avoid double counting aggregate Commune/Region rows.
    selected = []
    for (_, year), group in frame.groupby(["fuel", "ANNEE"]):
        if (group["TYPE"] == "IRIS").any():
            selected.append(group[group["TYPE"] == "IRIS"])
        elif (group["TYPE"] == "Commune").any():
            selected.append(group[group["TYPE"] == "Commune"])
    if not selected:
        return frame.iloc[0:0].copy()
    return pd.concat(selected, ignore_index=True)


def process_historical_electricity_gas(mapping):
    chunks = []
    processed_files = []
    selected_levels = []
    specs = [
        (HISTORICAL_ELECTRICITY_PATH, "electricity"),
        (HISTORICAL_GAS_PATH, "gas"),
    ]

    for path, fuel in specs:
        if not path.exists():
            continue
        local_chunks = []
        usecols = ["ANNEE", "TYPE", "CODE", "CONSOA", "CONSOI", "CONSOT", "PDLA", "PDLI", "PDLT"]
        for chunk in pd.read_csv(path, sep=";", skiprows=1, dtype=str, usecols=usecols, chunksize=500_000):
            chunk = chunk[chunk["TYPE"].isin(["IRIS", "Commune"])].copy()
            if chunk.empty:
                continue
            chunk["fuel"] = fuel
            local_chunks.append(chunk)

        if not local_chunks:
            continue

        frame = pd.concat(local_chunks, ignore_index=True)
        selected = select_best_historical_level(frame)
        for year, group in selected.groupby("ANNEE"):
            selected_levels.append(
                {
                    "fuel": fuel,
                    "year": int(year),
                    "type": sorted(group["TYPE"].unique().tolist()),
                    "rows": int(len(group)),
                }
            )

        selected["CODGEO"] = selected["CODE"].astype(str).str[:5]
        selected["ANNEE"] = pd.to_numeric(selected["ANNEE"], errors="coerce").astype("Int64")
        selected["CONSO"] = to_number(selected["CONSOA"]) + to_number(selected["CONSOI"]) + to_number(selected["CONSOT"])
        selected["PDL"] = to_number(selected["PDLA"]) + to_number(selected["PDLI"]) + to_number(selected["PDLT"])
        joined = selected.merge(mapping[["CODGEO", "ZE2020"]], on="CODGEO", how="inner")
        grouped = joined.groupby(["ZE2020", "ANNEE"], as_index=False)[["CONSO", "PDL"]].sum()
        grouped["fuel"] = fuel
        chunks.append(grouped)
        processed_files.append(str(path.relative_to(ROOT)))

    return chunks, processed_files, selected_levels


def process_historical_heat_cold(mapping):
    if not HISTORICAL_HEAT_COLD_PATH.exists():
        return [], [], []

    usecols = ["ANNEE", "CODE", "CONSOT", "CONSOI", "CONSOA", "PDL"]
    frame = pd.read_csv(HISTORICAL_HEAT_COLD_PATH, sep=";", skiprows=1, dtype=str, usecols=usecols)
    frame["CODGEO"] = frame["CODE"].astype(str).str[:5]
    frame["ANNEE"] = pd.to_numeric(frame["ANNEE"], errors="coerce").astype("Int64")
    frame["CONSO"] = to_number(frame["CONSOA"]) + to_number(frame["CONSOI"]) + to_number(frame["CONSOT"])
    frame["PDL"] = to_number(frame["PDL"])
    joined = frame.merge(mapping[["CODGEO", "ZE2020"]], on="CODGEO", how="inner")
    grouped = joined.groupby(["ZE2020", "ANNEE"], as_index=False)[["CONSO", "PDL"]].sum()
    grouped["fuel"] = "heat_cold"
    selected_levels = [
        {"fuel": "heat_cold", "year": int(year), "type": ["Commune"], "rows": int(len(group))}
        for year, group in frame.groupby("ANNEE")
    ]
    return [grouped], [str(HISTORICAL_HEAT_COLD_PATH.relative_to(ROOT))], selected_levels


def build_energy_consumption():
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    chunks = []
    processed_files = []
    skipped_files = []
    historical_selected_levels = []

    historical_chunks, historical_files, selected_levels = process_historical_electricity_gas(mapping)
    chunks.extend(historical_chunks)
    processed_files.extend(historical_files)
    historical_selected_levels.extend(selected_levels)

    heat_chunks, heat_files, heat_selected_levels = process_historical_heat_cold(mapping)
    chunks.extend(heat_chunks)
    processed_files.extend(heat_files)
    historical_selected_levels.extend(heat_selected_levels)

    with zipfile.ZipFile(RAW_ZIP) as z:
        csv_names = [name for name in z.namelist() if name.lower().endswith(".csv")]
        for name in csv_names:
            fuel = fuel_from_name(name)
            if fuel not in {"electricity", "gas"}:
                skipped_files.append({"file": name, "reason": "fuel_not_used"})
                continue

            with z.open(name) as f:
                header = next(csv.reader((line.decode("utf-8", errors="replace") for line in f), delimiter=";"))

            skiprows = 1 if header and header[0] != "OPERATEUR" else 0
            usecols = [
                "ANNEE",
                "CODE_IRIS_CODE",
                "CODE_CATEGORIE_CONSOMMATION",
                "CONSO",
                "PDL",
            ]

            with z.open(name) as f:
                for chunk in pd.read_csv(
                    f,
                    sep=";",
                    skiprows=skiprows,
                    dtype=str,
                    usecols=lambda c: c in usecols,
                    chunksize=500_000,
                ):
                    if chunk.empty:
                        continue
                    chunk["CODGEO"] = chunk["CODE_IRIS_CODE"].astype(str).str[:5]
                    chunk["ANNEE"] = pd.to_numeric(chunk["ANNEE"], errors="coerce").astype("Int64")
                    chunk["CONSO"] = pd.to_numeric(chunk["CONSO"].str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)
                    chunk["PDL"] = pd.to_numeric(chunk["PDL"].str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)
                    chunk = chunk[chunk["CODE_CATEGORIE_CONSOMMATION"].fillna("") != "RES"]
                    joined = chunk.merge(mapping[["CODGEO", "ZE2020"]], on="CODGEO", how="inner")
                    grouped = joined.groupby(["ZE2020", "ANNEE"], as_index=False)[["CONSO", "PDL"]].sum()
                    grouped["fuel"] = fuel
                    chunks.append(grouped)

            processed_files.append(name)

    if not chunks:
        raise RuntimeError("No energy rows were processed.")

    wide = aggregate_energy_chunks(chunks, mapping)

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    wide.to_csv(OUTPUT_PATH, index=False)

    quality = {
        "years_available": sorted(wide["year"].dropna().astype(int).unique().tolist()),
        "zones_count": int(wide["ZE2020"].nunique()),
        "total_rows": int(len(wide)),
        "features": [col for col in wide.columns if col not in ["ZE2020", "year"]],
        "processed_files": processed_files,
        "skipped_files_count": len(skipped_files),
        "historical_selected_levels": historical_selected_levels,
        "methodological_status": (
            "candidate_lagged_feature_source; non-residential electricity/gas 2008-2024 plus heat/cold 2008-2017; "
            "historical files use best available IRIS-or-Commune level per fuel/year to avoid double counting"
        ),
    }
    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    print(f"Saved energy features to {OUTPUT_PATH}")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    build_energy_consumption()
