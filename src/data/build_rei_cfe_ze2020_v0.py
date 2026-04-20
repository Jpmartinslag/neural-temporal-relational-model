import json
import os
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "external" / "rei"
CONVERTED_DIR = ROOT / "data" / "interim" / "tables" / "rei_converted_csv_v0"
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

AGGREGATE_TO_COMPONENT_PREFIXES = {
    "P31": "P31_",
    "P33": "P33_",
    "P34": "P34_",
}


OUTPUT_FEATURES = [
    "rei_cfe_commune_base",
    "rei_cfe_commune_product",
    "rei_cfe_commune_articles",
    "rei_cfe_epci_base",
    "rei_cfe_epci_product",
    "rei_cfe_epci_articles",
    "rei_cfe_microentrepreneurs",
    "rei_cfe_microentrepreneurs_created_n_1",
]


def normalize_column_name(name):
    return " ".join(str(name).upper().replace("\u00a0", " ").split())


def source_columns_for_output(columns):
    normalized = {col: normalize_column_name(col) for col in columns}
    sources = {feature: [] for feature in OUTPUT_FEATURES}

    for col, norm in normalized.items():
        if col in CFE_COLUMNS:
            sources[CFE_COLUMNS[col]].append(col)
        elif col.startswith("P31_"):
            sources["rei_cfe_epci_base"].append(col)
        elif col.startswith("P33_"):
            sources["rei_cfe_epci_product"].append(col)
        elif col.startswith("P34_"):
            sources["rei_cfe_epci_articles"].append(col)
        elif col == "NBCFEMICRO":
            sources["rei_cfe_microentrepreneurs"].append(col)

        if norm == "CFE - COMMUNE / BASE":
            sources["rei_cfe_commune_base"].append(col)
        elif norm == "CFE - COMMUNE / PRODUIT REEL NET":
            sources["rei_cfe_commune_product"].append(col)
        elif norm == "CFE - COMMUNE / NOMBRE ARTICLES COMPORTANT UNE BASE TAXABLE DE CFE":
            sources["rei_cfe_commune_articles"].append(col)
        elif norm.startswith("CFE - INTERCOMMUNALITE / BASE /"):
            sources["rei_cfe_epci_base"].append(col)
        elif norm.startswith("CFE - INTERCOMMUNALITE / PRODUIT REEL NET /"):
            sources["rei_cfe_epci_product"].append(col)
        elif norm.startswith("CFE - INTERCOMMUNALITE /NB ARTICLES /"):
            sources["rei_cfe_epci_articles"].append(col)
        elif norm in {
            "CFE - NOMBRE TOTAL MICRO-ENTREPRENEURS",
            "CFE - NOMBRE DE MICRO-ENTREPRISES OU SPECIAL BNC",
            "CFE - NOMBRE DE MICRO-ENTREPRISES OU SPÉCIAL BNC",
        }:
            sources["rei_cfe_microentrepreneurs"].append(col)
        elif "MICRO" in norm and "CREE" in norm and "N-1" in norm:
            sources["rei_cfe_microentrepreneurs_created_n_1"].append(col)

    deduped_sources = {feature: sorted(set(cols)) for feature, cols in sources.items()}

    # Recent REI files may include both aggregate EPCI columns (P31/P33/P34)
    # and their fiscal-regime components (P31_*/P33_*/P34_*). Use the aggregate
    # when present; summing both double-counts the same fiscal base/product.
    for feature, aggregate_col in [
        ("rei_cfe_epci_base", "P31"),
        ("rei_cfe_epci_product", "P33"),
        ("rei_cfe_epci_articles", "P34"),
    ]:
        cols = deduped_sources[feature]
        if aggregate_col in cols:
            deduped_sources[feature] = [aggregate_col]

    return deduped_sources


def identifier_columns(columns):
    columns = list(columns)
    if "code INSEE" in columns:
        return ["code INSEE"]
    if "IDCOM" in columns:
        return ["IDCOM"]
    if {"DEP", "COM"}.issubset(columns):
        return ["DEP", "COM"]
    if {"DEPARTEMENT", "COMMUNE"}.issubset(columns):
        return ["DEPARTEMENT", "COMMUNE"]
    return []


def columns_to_read(columns):
    sources = source_columns_for_output(columns)
    feature_cols = sorted({col for cols in sources.values() for col in cols})
    return identifier_columns(columns) + feature_cols


def commune_code(frame):
    if "code INSEE" in frame.columns:
        return frame["code INSEE"].astype(str).str.zfill(5)
    if "IDCOM" in frame.columns:
        return frame["IDCOM"].astype(str).str.zfill(5)
    if {"DEP", "COM"}.issubset(frame.columns):
        return frame["DEP"].astype(str).str.zfill(2) + frame["COM"].astype(str).str.zfill(3)
    if {"DEPARTEMENT", "COMMUNE"}.issubset(frame.columns):
        return frame["DEPARTEMENT"].astype(str).str.zfill(2) + frame["COMMUNE"].astype(str).str.zfill(3)
    raise KeyError(f"No commune identifier columns found. Columns include: {frame.columns[:20].tolist()}")


def normalize_rei_frame(frame):
    frame = frame.copy()
    frame["CODGEO"] = commune_code(frame)
    sources = source_columns_for_output(frame.columns)
    output = frame[["CODGEO"]].copy()

    for feature, cols in sources.items():
        if not cols:
            output[feature] = 0.0
            continue
        values = pd.DataFrame(
            {
                col: pd.to_numeric(frame[col].astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)
                for col in cols
            }
        )
        output[feature] = values.sum(axis=1)

    return output, sources


def read_rei_csv_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        csv_names = [name for name in z.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            return None
        with z.open(csv_names[0]) as f:
            header = pd.read_csv(f, sep=";", dtype=str, nrows=0, encoding="latin1").columns
        usecols = columns_to_read(header)
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


def read_converted_rei_csv(year):
    path = CONVERTED_DIR / f"rei_{year}.csv"
    if not path.exists():
        return None
    header = pd.read_csv(path, sep=";", dtype=str, nrows=0).columns
    usecols = columns_to_read(header)
    return pd.read_csv(path, sep=";", dtype=str, usecols=lambda c: c in usecols)


def build_rei_cfe():
    mapping = pd.read_csv(MAPPING_PATH, dtype={"CODGEO": str, "ZE2020": str})
    rows = []
    skipped = []
    processed_sources = []

    for zip_path in sorted(RAW_DIR.glob("REI-*-fichier-*.zip")):
        year = int(zip_path.name.split("-")[1])
        frame = read_converted_rei_csv(year)
        source_kind = "converted_csv"
        if frame is None:
            frame = read_rei_csv_from_zip(zip_path)
            source_kind = "raw_zip_csv"
        if frame is None:
            skipped.append({"year": year, "reason": "xlsx_only_or_no_csv", "file": zip_path.name})
            continue
        processed_sources.append({"year": year, "source_kind": source_kind, "file": zip_path.name})

        frame, source_columns = normalize_rei_frame(frame)

        joined = frame.merge(mapping[["CODGEO", "ZE2020"]], on="CODGEO", how="inner")
        numeric_cols = [col for col in OUTPUT_FEATURES if col in joined.columns]
        aggregated = joined.groupby("ZE2020", as_index=False)[numeric_cols].sum()
        aggregated["year"] = year
        rows.append(aggregated)
        processed_sources[-1]["source_columns"] = source_columns

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
        "processed_sources": processed_sources,
        "skipped_files": skipped,
        "methodological_status": (
            "diagnostic_lagged_feature_source_under_quarantine; aggregate/component "
            "double-counting fixed, but publication-lag and vintage safety remain unresolved"
        ),
    }
    os.makedirs(QUALITY_PATH.parent, exist_ok=True)
    with open(QUALITY_PATH, "w") as f:
        json.dump(quality, f, indent=2)

    print(f"Saved REI CFE features to {OUTPUT_PATH}")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    build_rei_cfe()
