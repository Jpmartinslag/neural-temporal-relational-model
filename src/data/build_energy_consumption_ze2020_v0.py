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


def build_energy_consumption():
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    chunks = []
    processed_files = []
    skipped_files = []

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

    long = pd.concat(chunks, ignore_index=True)
    long = long.groupby(["ZE2020", "ANNEE", "fuel"], as_index=False)[["CONSO", "PDL"]].sum()

    wide = long.pivot_table(index=["ZE2020", "ANNEE"], columns="fuel", values=["CONSO", "PDL"], aggfunc="sum")
    wide.columns = [f"energy_{fuel}_{metric.lower()}_nonres" for metric, fuel in wide.columns]
    wide = wide.reset_index().rename(columns={"ANNEE": "year"}).sort_values(["year", "ZE2020"])

    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    wide.to_csv(OUTPUT_PATH, index=False)

    quality = {
        "years_available": sorted(wide["year"].dropna().astype(int).unique().tolist()),
        "zones_count": int(wide["ZE2020"].nunique()),
        "total_rows": int(len(wide)),
        "features": [col for col in wide.columns if col not in ["ZE2020", "year"]],
        "processed_files": processed_files,
        "skipped_files_count": len(skipped_files),
        "methodological_status": "candidate_lagged_feature_source; non-residential electricity/gas only",
    }
    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    print(f"Saved energy features to {OUTPUT_PATH}")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    build_energy_consumption()
