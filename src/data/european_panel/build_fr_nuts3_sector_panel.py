"""Build a France NUTS3 target and A10 sector panel from commune-level SIDE.

The source archive is large, so the SIDE table is streamed in chunks.  This
builder performs upward aggregation only:

    commune -> department -> Eurostat NUTS3 2021

No ARDECO values are read here.  The resulting panel is the territorial basis
required for a later direct NUTS3 join with historical ARDECO SNETZ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[3]
DEFAULT_SIDE_ZIP = (
    BASE
    / "data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2025_CSV.zip"
)
DEFAULT_COMMUNE_MAP = BASE / "data/interim/mappings/commune_to_ze2020_2026.csv"
DEFAULT_COG_ZIP = BASE / "data/raw/territorial/cog_ensemble_2026_csv.zip"
DEFAULT_NUTS_GEOJSON = BASE / "data/external/nuts3_2021_eurostat.geojson"
DEFAULT_PANEL_OUT = BASE / "data/processed/european_panel/fr_nuts3_panel.csv"
DEFAULT_SECTOR_OUT = (
    BASE / "data/processed/economic_graph/sector_panel_fr_nuts3.csv"
)
DEFAULT_AUDIT_OUT = (
    BASE / "data/processed/ardeco_extension/fr_nuts3_build_audit.json"
)

SIDE_DATA_MEMBER = "DS_SIDE_CREA_ETAB_COM_2025_data.csv"
COG_DEPARTMENT_MEMBER = "v_departement_2026.csv"
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", text)


def build_department_to_nuts3(
    cog_departments: pd.DataFrame,
    nuts_properties: pd.DataFrame,
) -> pd.DataFrame:
    """Match all French departments to NUTS3 by normalized official names."""
    dep = cog_departments[["DEP", "LIBELLE"]].copy()
    dep["DEP"] = dep["DEP"].astype(str).str.zfill(2)
    dep["name_key"] = dep["LIBELLE"].map(normalize_name)

    nuts = nuts_properties[
        nuts_properties["CNTR_CODE"].eq("FR")
        & nuts_properties["LEVL_CODE"].eq(3)
    ][["NUTS_ID", "NUTS_NAME"]].copy()
    nuts["name_key"] = nuts["NUTS_NAME"].map(normalize_name)

    if dep["name_key"].duplicated().any() or nuts["name_key"].duplicated().any():
        raise ValueError("Department/NUTS normalized names are not unique")

    mapping = dep.merge(nuts, on="name_key", how="outer", indicator=True)
    unmatched = mapping[mapping["_merge"].ne("both")]
    if not unmatched.empty:
        raise ValueError(
            "Department-to-NUTS3 mapping incomplete: "
            + unmatched[["DEP", "LIBELLE", "NUTS_ID", "NUTS_NAME"]]
            .to_dict("records")
            .__repr__()
        )
    return mapping[["DEP", "LIBELLE", "NUTS_ID", "NUTS_NAME"]].sort_values("DEP")


def aggregate_side_chunk(
    chunk: pd.DataFrame,
    commune_to_nuts: pd.DataFrame,
) -> pd.DataFrame:
    """Filter one SIDE chunk and aggregate it to NUTS3."""
    required = {
        "ACTIVITY",
        "GEO",
        "GEO_OBJECT",
        "LEGAL_FORM",
        "SIDE_MEASURE",
        "TIME_PERIOD",
        "OBS_VALUE",
    }
    missing = required.difference(chunk.columns)
    if missing:
        raise ValueError(f"SIDE chunk missing columns: {sorted(missing)}")

    valid_activities = set(SECTORS + ["_T"])
    selected = chunk[
        chunk["GEO_OBJECT"].eq("COM")
        & chunk["LEGAL_FORM"].eq("_T")
        & chunk["SIDE_MEASURE"].eq("UNIT_LOC_BURE")
        & chunk["ACTIVITY"].isin(valid_activities)
    ].copy()
    if selected.empty:
        return pd.DataFrame(
            columns=["NUTS_ID", "NUTS_NAME", "year", "activity", "value"]
        )

    selected["CODGEO"] = selected["GEO"].astype(str).str.zfill(5)
    selected["year"] = pd.to_numeric(
        selected["TIME_PERIOD"], errors="coerce"
    ).astype("Int64")
    selected["value"] = pd.to_numeric(selected["OBS_VALUE"], errors="coerce")
    selected = selected.merge(
        commune_to_nuts,
        on="CODGEO",
        how="left",
        validate="many_to_one",
    )
    if selected["NUTS_ID"].isna().any():
        sample = selected.loc[selected["NUTS_ID"].isna(), "CODGEO"].head().tolist()
        raise ValueError(f"SIDE communes without NUTS3 mapping: {sample}")

    return (
        selected.groupby(
            ["NUTS_ID", "NUTS_NAME", "year", "ACTIVITY"],
            as_index=False,
            dropna=False,
        )["value"]
        .sum(min_count=1)
        .rename(columns={"ACTIVITY": "activity"})
    )


def finalize_aggregates(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        raise ValueError("No eligible SIDE observations found")
    combined = pd.concat(parts, ignore_index=True)
    return (
        combined.groupby(
            ["NUTS_ID", "NUTS_NAME", "year", "activity"],
            as_index=False,
        )["value"]
        .sum(min_count=1)
        .sort_values(["NUTS_ID", "year", "activity"])
        .reset_index(drop=True)
    )


def build_outputs(aggregated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target = aggregated[aggregated["activity"].eq("_T")].copy()
    target = target.rename(
        columns={
            "NUTS_ID": "region_id",
            "NUTS_NAME": "region_name",
            "value": "target_births",
        }
    )[["region_id", "region_name", "year", "target_births"]]
    target["country"] = "FR"
    target["region_level"] = "NUTS3"
    region_order = {
        region: idx for idx, region in enumerate(sorted(target["region_id"].unique()))
    }
    target["node_idx"] = target["region_id"].map(region_order)
    target = target.sort_values(["region_id", "year"]).reset_index(drop=True)
    grouped = target.groupby("region_id")["target_births"]
    target["lag1_births"] = grouped.shift(1)
    target["lag2_births"] = grouped.shift(2)
    target["lag3_births"] = grouped.shift(3)
    target["growth_1y"] = (
        target["lag1_births"] / target["lag2_births"].replace(0, np.nan) - 1.0
    )
    target["growth_2y"] = (
        target["lag1_births"] / target["lag3_births"].replace(0, np.nan) - 1.0
    )
    target["mask_target"] = target["target_births"].notna().astype(int)
    target["flag_target_concept"] = "establishment_creation"
    target["meta_nuts3_code"] = target["region_id"]
    target["meta_region_system"] = "NUTS3-2021"
    target["meta_source_label"] = "SIDE commune aggregation"

    sectors = aggregated[aggregated["activity"].isin(SECTORS)].copy()
    sectors = sectors.rename(
        columns={
            "NUTS_ID": "region_id",
            "NUTS_NAME": "region_name",
            "activity": "sector_a10",
            "value": "sector_births",
            "year": "observation_year",
        }
    )
    sectors["country"] = "FR"
    sectors["source_label"] = "SIDE commune aggregation"
    sectors["region_level"] = "NUTS3"
    sectors["flag_target_concept"] = "establishment_creation"
    sectors["meta_region_system"] = "NUTS3-2021"
    sectors["meta_source_label"] = "SIDE"
    sectors["mask_sector_births"] = sectors["sector_births"].notna().astype(int)
    sectors["mask_sector_supported"] = 1
    keys = ["country", "region_id", "observation_year"]
    observed_count = sectors.groupby(keys)["mask_sector_births"].transform("sum")
    sectors["mask_complete_sector_vector"] = observed_count.eq(len(SECTORS)).astype(int)
    total_lookup = target.rename(
        columns={"year": "observation_year", "target_births": "business_sector_total"}
    )[["region_id", "observation_year", "business_sector_total"]]
    sectors = sectors.merge(
        total_lookup,
        on=["region_id", "observation_year"],
        how="left",
        validate="many_to_one",
    )
    sectors["sector_share"] = (
        sectors["sector_births"]
        / sectors["business_sector_total"].replace(0, np.nan)
    )
    sectors = sectors.sort_values(
        ["country", "region_id", "sector_a10", "observation_year"]
    ).reset_index(drop=True)
    sectors["sector_growth_1y"] = sectors.groupby(
        ["country", "region_id", "sector_a10"]
    )["sector_births"].pct_change(fill_method=None)
    sectors["available_for_forecast_year"] = sectors["observation_year"] + 1

    panel_columns = [
        "country",
        "region_id",
        "region_name",
        "region_level",
        "year",
        "node_idx",
        "target_births",
        "lag1_births",
        "lag2_births",
        "lag3_births",
        "growth_1y",
        "growth_2y",
        "mask_target",
        "flag_target_concept",
        "meta_nuts3_code",
        "meta_region_system",
        "meta_source_label",
    ]
    sector_columns = [
        "region_id",
        "observation_year",
        "sector_a10",
        "sector_births",
        "country",
        "source_label",
        "region_name",
        "region_level",
        "flag_target_concept",
        "meta_region_system",
        "meta_source_label",
        "mask_sector_births",
        "mask_sector_supported",
        "mask_complete_sector_vector",
        "business_sector_total",
        "sector_share",
        "sector_growth_1y",
        "available_for_forecast_year",
    ]
    return target[panel_columns], sectors[sector_columns]


def run_builder(
    side_zip: Path = DEFAULT_SIDE_ZIP,
    commune_map_path: Path = DEFAULT_COMMUNE_MAP,
    cog_zip: Path = DEFAULT_COG_ZIP,
    nuts_geojson: Path = DEFAULT_NUTS_GEOJSON,
    panel_out: Path = DEFAULT_PANEL_OUT,
    sector_out: Path = DEFAULT_SECTOR_OUT,
    audit_out: Path = DEFAULT_AUDIT_OUT,
    chunksize: int = 500_000,
) -> dict:
    for path in (side_zip, commune_map_path, cog_zip, nuts_geojson):
        if not path.exists():
            raise FileNotFoundError(path)

    commune = pd.read_csv(commune_map_path, dtype=str)[["CODGEO", "DEP"]]
    commune["CODGEO"] = commune["CODGEO"].astype(str).str.zfill(5)
    commune["DEP"] = commune["DEP"].astype(str).str.zfill(2)

    with zipfile.ZipFile(cog_zip) as archive:
        departments = pd.read_csv(
            archive.open(COG_DEPARTMENT_MEMBER), dtype=str
        )
    geojson = json.loads(nuts_geojson.read_text(encoding="utf-8"))
    nuts_properties = pd.DataFrame(
        [feature["properties"] for feature in geojson["features"]]
    )
    dep_to_nuts = build_department_to_nuts3(departments, nuts_properties)
    commune_to_nuts = commune.merge(
        dep_to_nuts[["DEP", "NUTS_ID", "NUTS_NAME"]],
        on="DEP",
        how="left",
        validate="many_to_one",
    )
    if commune_to_nuts["NUTS_ID"].isna().any():
        raise ValueError("Some communes do not map to a French NUTS3 region")

    parts: list[pd.DataFrame] = []
    with zipfile.ZipFile(side_zip) as archive:
        with archive.open(SIDE_DATA_MEMBER) as source:
            for chunk in pd.read_csv(
                source,
                sep=";",
                dtype=str,
                chunksize=chunksize,
                low_memory=False,
            ):
                part = aggregate_side_chunk(chunk, commune_to_nuts)
                if not part.empty:
                    parts.append(part)

    aggregated = finalize_aggregates(parts)
    panel, sectors = build_outputs(aggregated)

    panel_out.parent.mkdir(parents=True, exist_ok=True)
    sector_out.parent.mkdir(parents=True, exist_ok=True)
    audit_out.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(panel_out, index=False)
    sectors.to_csv(sector_out, index=False)

    sector_sum = (
        sectors.groupby(["region_id", "observation_year"], as_index=False)
        ["sector_births"]
        .sum(min_count=1)
        .rename(columns={"sector_births": "sector_sum"})
    )
    target_sum = panel[["region_id", "year", "target_births"]].rename(
        columns={"year": "observation_year", "target_births": "target"}
    )
    aligned = sector_sum.merge(
        target_sum,
        on=["region_id", "observation_year"],
        how="inner",
        validate="one_to_one",
    )
    relative_gap = (
        (aligned["sector_sum"] - aligned["target"]).abs()
        / aligned["target"].replace(0, np.nan)
    )

    audit = {
        "decision": "FR_NUTS3_PANEL_READY",
        "rows": int(len(panel)),
        "sector_rows": int(len(sectors)),
        "regions": int(panel["region_id"].nunique()),
        "years": sorted(int(year) for year in panel["year"].unique()),
        "sectors": sorted(sectors["sector_a10"].unique()),
        "complete_sector_vectors_rate": float(
            sectors["mask_complete_sector_vector"].mean()
        ),
        "median_sector_total_relative_gap": float(relative_gap.median()),
        "max_sector_total_relative_gap": float(relative_gap.max()),
        "sources": {
            "side_zip": str(side_zip),
            "side_zip_sha256": file_sha256(side_zip),
            "commune_map": str(commune_map_path),
            "commune_map_sha256": file_sha256(commune_map_path),
            "cog_zip": str(cog_zip),
            "cog_zip_sha256": file_sha256(cog_zip),
            "nuts_geojson": str(nuts_geojson),
            "nuts_geojson_sha256": file_sha256(nuts_geojson),
        },
        "outputs": {
            "panel": str(panel_out),
            "sector_panel": str(sector_out),
        },
    }
    audit_out.write_text(
        json.dumps(audit, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--side-zip", type=Path, default=DEFAULT_SIDE_ZIP)
    parser.add_argument("--commune-map", type=Path, default=DEFAULT_COMMUNE_MAP)
    parser.add_argument("--cog-zip", type=Path, default=DEFAULT_COG_ZIP)
    parser.add_argument("--nuts-geojson", type=Path, default=DEFAULT_NUTS_GEOJSON)
    parser.add_argument("--panel-out", type=Path, default=DEFAULT_PANEL_OUT)
    parser.add_argument("--sector-out", type=Path, default=DEFAULT_SECTOR_OUT)
    parser.add_argument("--audit-out", type=Path, default=DEFAULT_AUDIT_OUT)
    parser.add_argument("--chunksize", type=int, default=500_000)
    args = parser.parse_args()
    result = run_builder(
        side_zip=args.side_zip,
        commune_map_path=args.commune_map,
        cog_zip=args.cog_zip,
        nuts_geojson=args.nuts_geojson,
        panel_out=args.panel_out,
        sector_out=args.sector_out,
        audit_out=args.audit_out,
        chunksize=args.chunksize,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
