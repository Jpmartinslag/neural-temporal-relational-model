import json
import os
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "external" / "rei"
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
OUTPUT_PATH = ROOT / "data" / "interim" / "tables" / "rei_cfe_ze2020_v0.csv"
QUALITY_PATH = ROOT / "reports" / "rei_cfe_quality_v0.json"


CFE_COLUMNS = {
    "P11": "rei_cfe_commune_base",
    "P13": "rei_cfe_commune_product",
    "P14": "rei_cfe_commune_articles",
    "P31": "rei_cfe_epci_base",
    "P33": "rei_cfe_epci_product",
    "P34": "rei_cfe_epci_articles",
    "NBCFEAE": "rei_cfe_microentrepreneurs",
    "NBCFEAECREE": "rei_cfe_microentrepreneurs_created_n_1",
}


def commune_code(frame):
    return frame["DEP"].astype(str).str.zfill(2) + frame["COM"].astype(str).str.zfill(3)


def read_rei_csv_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        csv_names = [name for name in z.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            return None
        usecols = ["DEP", "COM"] + [col for col in CFE_COLUMNS if col]
        for encoding in ["utf-8", "cp1252", "latin1"]:
            try:
                with z.open(csv_names[0]) as f:
                    return pd.read_csv(
                        f,
                        sep=";",
                        dtype=str,
                        encoding=encoding,
                        usecols=lambda c: c in usecols,
                    )
            except UnicodeDecodeError:
                continue
        with z.open(csv_names[0]) as f:
            return pd.read_csv(
                f,
                sep=";",
                dtype=str,
                encoding="latin1",
                encoding_errors="replace",
                usecols=lambda c: c in usecols,
            )


def build_rei_cfe():
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    rows = []
    skipped = []

    for zip_path in sorted(RAW_DIR.glob("REI-*-fichier-*.zip")):
        year = int(zip_path.name.split("-")[1])
        frame = read_rei_csv_from_zip(zip_path)
        if frame is None:
            skipped.append({"year": year, "reason": "xlsx_only_or_no_csv", "file": zip_path.name})
            continue

        frame["CODGEO"] = commune_code(frame)
        keep = ["CODGEO"] + [col for col in CFE_COLUMNS if col in frame.columns]
        frame = frame[keep].copy()

        for col in CFE_COLUMNS:
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col].str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)

        joined = frame.merge(mapping[["CODGEO", "ZE2020"]], on="CODGEO", how="inner")
        numeric_cols = [col for col in CFE_COLUMNS if col in joined.columns]
        aggregated = joined.groupby("ZE2020", as_index=False)[numeric_cols].sum()
        aggregated["year"] = year
        aggregated = aggregated.rename(columns=CFE_COLUMNS)
        rows.append(aggregated)

    if not rows:
        raise RuntimeError("No REI CSV files could be processed. Convert XLSX years to CSV or install openpyxl.")

    output = pd.concat(rows, ignore_index=True).sort_values(["year", "ZE2020"])
    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)

    quality = {
        "years_available": sorted(output["year"].unique().astype(int).tolist()),
        "zones_count": int(output["ZE2020"].nunique()),
        "total_rows": int(len(output)),
        "features": [col for col in output.columns if col not in ["ZE2020", "year"]],
        "skipped_files": skipped,
        "methodological_status": "candidate_lagged_feature_source; not included in canonical tensor before incremental validation",
    }
    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    print(f"Saved REI CFE features to {OUTPUT_PATH}")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    build_rei_cfe()
