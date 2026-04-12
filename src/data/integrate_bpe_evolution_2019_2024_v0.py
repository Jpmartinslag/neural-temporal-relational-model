from __future__ import annotations

import csv
import json
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RAW_CANDIDATES = [
    ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "ds_bpe_evolution_com_2019_2024_geo_2025.zip",
    ROOT / "ds_bpe_evolution_com_2019_2024_geo_2025.zip",
]
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
CORE_NODES_PATH = ROOT / "data" / "processed" / "graph_nodes_ze2020_core_v0.csv"
ZONES_MASTER_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"
COMMUNE_OUT = ROOT / "data" / "interim" / "tables" / "bpe_evolution_commune_2019_2024_geo2025.csv"
ZE_CORE_OUT = ROOT / "data" / "processed" / "bpe_evolution_ze2020_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "bpe_evolution_2019_2024_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "BPE_EVOLUTION_2019_2024_INTEGRATION_V0.md"

YEARS = {"2019", "2024"}
PLM_PARENT_COMMUNES = {
    **{f"751{i:02d}": "75056" for i in range(1, 21)},
    **{f"6938{i}": "69123" for i in range(1, 10)},
    **{f"132{i:02d}": "13055" for i in range(1, 17)},
}


def fmt(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def find_raw_zip() -> Path:
    for path in RAW_CANDIDATES:
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in RAW_CANDIDATES)
    raise FileNotFoundError(f"BPE evolution zip not found. Searched: {searched}")


def load_commune_map() -> dict[str, dict[str, str]]:
    with MAPPING_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {
            row["CODGEO"].zfill(5): {
                "ze2020": row["ZE2020"].zfill(4),
                "libze2020": row["LIBZE2020"],
                "reg": row["REG"],
            }
            for row in reader
        }


def load_core_zones() -> set[str]:
    with CORE_NODES_PATH.open(encoding="utf-8", newline="") as f:
        return {row["ze2020"].zfill(4) for row in csv.DictReader(f)}


def data_member_name(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    data_names = [name for name in names if name.lower().endswith(".csv") and "metadata" not in name.lower()]
    if len(data_names) != 1:
        raise ValueError(f"Expected exactly one data CSV in {zip_path}, found: {data_names}")
    return data_names[0]


def integrate() -> dict[str, object]:
    raw_zip = find_raw_zip()
    member = data_member_name(raw_zip)
    commune_map = load_commune_map()
    core_zones = load_core_zones()

    commune_presence: dict[tuple[str, str], set[str]] = defaultdict(set)
    ze_presence_total: dict[tuple[str, str], int] = defaultdict(int)
    ze_communes: dict[tuple[str, str], set[str]] = defaultdict(set)
    ze_types: dict[tuple[str, str], set[str]] = defaultdict(set)
    unmatched_geo: set[str] = set()
    geo_object_counts: dict[str, int] = defaultdict(int)
    year_counts: dict[str, int] = defaultdict(int)
    obs_value_counts: dict[str, int] = defaultdict(int)
    total_rows = 0
    retained_rows = 0
    retained_core_rows = 0

    with zipfile.ZipFile(raw_zip) as zf:
        with zf.open(member) as raw:
            text = (line.decode("utf-8-sig").replace("\r\n", "\n") for line in raw)
            reader = csv.DictReader(text, delimiter=";")
            expected = {"TIME_PERIOD", "GEO", "FACILITY_TYPE", "OBS_VALUE", "BPE_MEASURE", "GEO_OBJECT"}
            missing = expected - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing expected columns in {member}: {sorted(missing)}")

            for row in reader:
                total_rows += 1
                year = row["TIME_PERIOD"].strip()
                geo = row["GEO"].strip().zfill(5)
                facility_type = row["FACILITY_TYPE"].strip()
                obs_value = row["OBS_VALUE"].strip()
                geo_object = row["GEO_OBJECT"].strip()
                year_counts[year] += 1
                obs_value_counts[obs_value] += 1
                geo_object_counts[geo_object] += 1

                if year not in YEARS or obs_value != "1" or geo_object not in {"COM", "ARM"}:
                    continue
                mapped_geo = PLM_PARENT_COMMUNES.get(geo, geo)
                info = commune_map.get(mapped_geo)
                if info is None:
                    unmatched_geo.add(geo)
                    continue
                ze = info["ze2020"]

                retained_rows += 1
                if ze in core_zones:
                    retained_core_rows += 1
                commune_presence[(mapped_geo, year)].add(facility_type)
                ze_presence_total[(ze, year)] += 1
                ze_communes[(ze, year)].add(mapped_geo)
                ze_types[(ze, year)].add(facility_type)

    COMMUNE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with COMMUNE_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "codgeo",
                "ze2020",
                "year",
                "bpe_evolution_presence_type_count",
                "source_geography_year",
                "measure_definition",
            ],
        )
        writer.writeheader()
        for (codgeo, year), facility_types in sorted(commune_presence.items()):
            writer.writerow(
                {
                    "codgeo": codgeo,
                    "ze2020": commune_map[codgeo]["ze2020"],
                    "year": year,
                    "bpe_evolution_presence_type_count": len(facility_types),
                    "source_geography_year": "2025",
                    "measure_definition": "count of facility types present in commune; OBS_VALUE=1 rows only",
                }
            )

    zone_labels = {
        info["ze2020"]: {"libze2020": info["libze2020"], "reg": info["reg"]}
        for info in commune_map.values()
        if info["ze2020"] in core_zones
    }
    ZE_CORE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with ZE_CORE_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ze2020",
                "libze2020",
                "reg",
                "year",
                "bpe_evolution_commune_type_presence_total",
                "bpe_evolution_communes_observed",
                "bpe_evolution_facility_types_observed",
                "source_geography_year",
                "comparability_status",
            ],
        )
        writer.writeheader()
        for ze in sorted(core_zones):
            for year in sorted(YEARS):
                labels = zone_labels.get(ze, {"libze2020": "", "reg": ""})
                key = (ze, year)
                writer.writerow(
                    {
                        "ze2020": ze,
                        "libze2020": labels["libze2020"],
                        "reg": labels["reg"],
                        "year": year,
                        "bpe_evolution_commune_type_presence_total": fmt(ze_presence_total.get(key, 0)),
                        "bpe_evolution_communes_observed": fmt(len(ze_communes.get(key, set()))),
                        "bpe_evolution_facility_types_observed": fmt(len(ze_types.get(key, set()))),
                        "source_geography_year": "2025",
                        "comparability_status": "official_harmonized_2019_2024_presence_absence",
                    }
                )

    update_zones_master(ze_presence_total)

    quality = {
        "source_zip": str(raw_zip),
        "source_member": member,
        "total_rows": total_rows,
        "retained_mapped_rows_obs_value_1": retained_rows,
        "retained_core_rows_obs_value_1": retained_core_rows,
        "source_year_counts": dict(sorted(year_counts.items())),
        "obs_value_counts": dict(sorted(obs_value_counts.items())),
        "geo_object_counts": dict(sorted(geo_object_counts.items())),
        "unmatched_geo_count": len(unmatched_geo),
        "unmatched_geo_sample": sorted(unmatched_geo)[:20],
        "commune_year_rows_out": len(commune_presence),
        "ze_year_rows_out": len(core_zones) * len(YEARS),
        "core_zone_count": len(core_zones),
        "method_note": "Official BPE evolution source is harmonized for 2019 and 2024 in geography 2025. The metric is presence of facility types, not physical facility counts.",
        "future_update_note": "When INSEE publishes the planned 2015-2025 count/presence table, this integration can be extended by changing YEARS and raw file location without changing downstream semantics.",
    }
    QUALITY_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    REPORT_OUT.write_text(
        "\n".join(
            [
                "# BPE Evolution 2019-2024 Integration v0",
                "",
                "## Decision",
                "",
                "Use the official INSEE BPE evolution file as the comparable temporal BPE layer for now.",
                "Do not treat it as a raw BPE 2020 replacement.",
                "",
                "## Source",
                "",
                f"- Source ZIP: `{raw_zip.relative_to(ROOT)}`",
                f"- Data member: `{member}`",
                "- Official semantics: commune/arrondissement presence of equipment types, `OBS_VALUE=1`.",
                "- Geography: 1 January 2025.",
                "- Years currently present locally: `2019`, `2024`.",
                "",
                "## Outputs",
                "",
                f"- Commune interim: `{COMMUNE_OUT.relative_to(ROOT)}`",
                f"- ZE2020 core panel: `{ZE_CORE_OUT.relative_to(ROOT)}`",
                f"- Quality JSON: `{QUALITY_OUT.relative_to(ROOT)}`",
                "",
                "## Method",
                "",
                "- `bpe_evolution_presence_type_count`: number of distinct equipment types present in a commune-year.",
                "- `bpe_evolution_commune_type_presence_total`: sum of commune-type presences inside a ZE2020-year.",
                "- This is not a physical equipment count and should not be compared directly with raw BPE facility counts.",
                "",
                "## Forward Compatibility",
                "",
                "INSEE indicated a planned July 2026 release with count and presence tables for 2015-2025.",
                "This pipeline keeps the BPE evolution layer separate so the future 2015-2025 table can replace or extend the current 2019/2024 layer without changing the model interface.",
                "",
                "## Quality Snapshot",
                "",
                f"- Total source rows: `{quality['total_rows']}`",
                f"- Retained core rows: `{quality['retained_core_rows_obs_value_1']}`",
                f"- Unmatched GEO count: `{quality['unmatched_geo_count']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return quality


def update_zones_master(ze_presence_total: dict[tuple[str, str], int]) -> None:
    rows: list[dict[str, str]] = []
    with ZONES_MASTER_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            ze = row["ze2020"].zfill(4)
            value_2019 = ze_presence_total.get((ze, "2019"))
            value_2024 = ze_presence_total.get((ze, "2024"))
            row["bpe_evolution_commune_type_presence_2019_total"] = fmt(value_2019)
            row["bpe_evolution_commune_type_presence_2024_total"] = fmt(value_2024)
            if value_2019 is not None and value_2024 is not None:
                delta = value_2024 - value_2019
                row["bpe_evolution_commune_type_presence_delta_2019_2024"] = fmt(delta)
                row["bpe_evolution_commune_type_presence_pct_change_2019_2024"] = fmt(
                    delta / value_2019 if value_2019 else None
                )
            else:
                row["bpe_evolution_commune_type_presence_delta_2019_2024"] = ""
                row["bpe_evolution_commune_type_presence_pct_change_2019_2024"] = ""
            rows.append(row)

    new_columns = [
        "bpe_evolution_commune_type_presence_2019_total",
        "bpe_evolution_commune_type_presence_2024_total",
        "bpe_evolution_commune_type_presence_delta_2019_2024",
        "bpe_evolution_commune_type_presence_pct_change_2019_2024",
    ]
    for column in new_columns:
        if column not in fieldnames:
            fieldnames.append(column)

    with ZONES_MASTER_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    quality = integrate()
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
