from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
ZONES_MASTER_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"

SIDE_ET_ZIP_PATH = ROOT / "data" / "raw" / "temporal_depth" / "side" / "DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip"
SIDE_UL_ZIP_PATH = ROOT / "data" / "raw" / "temporal_depth" / "side" / "DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip"
BPE_2023_ZIP_PATH = ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "BPE23.zip"

SIDE_2021_INTERIM_PATH = ROOT / "data" / "interim" / "tables" / "side_stocks_commune_2021.csv"
BPE_2023_INTERIM_PATH = ROOT / "data" / "interim" / "tables" / "bpe_commune_2023.csv"
QUALITY_PATH = ROOT / "reports" / "side_2021_bpe_2023_integration_quality_v0.json"


def parse_number(value: str) -> float | None:
    raw = (value or "").strip().replace("\xa0", "")
    if raw == "":
        return None
    return float(raw.replace(",", "."))


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value - round(value)) < 1e-9:
        return f"{value:.1f}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_mapping() -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with MAPPING_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codgeo = row["CODGEO"].zfill(5)
            mapping[codgeo] = {
                "ze2020": row["ZE2020"].zfill(4),
                "libze2020": row["LIBZE2020"],
                "reg": row["REG"].zfill(2) if row["REG"] else "",
            }
    return mapping


def aggregate_side_file(path: Path, expected_measure: str) -> tuple[dict[str, float], dict[str, object]]:
    by_commune: dict[str, float] = {}
    rows_seen_2021 = 0
    rows_selected = 0
    invalid_values = 0

    with zipfile.ZipFile(path) as zf:
        data_name = next(name for name in zf.namelist() if name.endswith("_data.csv"))
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                if row["TIME_PERIOD"] != "2021":
                    continue
                rows_seen_2021 += 1
                if row["GEO_OBJECT"] != "COM":
                    continue
                if row["ACTIVITY"] != "_T":
                    continue
                if row["SIDE_MEASURE"] != expected_measure:
                    continue
                value = parse_number(row["OBS_VALUE"])
                if value is None:
                    invalid_values += 1
                    continue
                by_commune[row["GEO"].zfill(5)] = value
                rows_selected += 1

    return by_commune, {
        "source_file": path.name,
        "rows_seen_2021": rows_seen_2021,
        "rows_selected_commune_total_activity": rows_selected,
        "invalid_values": invalid_values,
        "communes_selected": len(by_commune),
    }


def aggregate_bpe_2023(commune_map: dict[str, dict[str, str]]) -> tuple[dict[str, float], dict[str, object]]:
    by_commune: dict[str, float] = defaultdict(float)
    rows_seen = 0
    rows_selected = 0
    unexpected_years: set[str] = set()

    with zipfile.ZipFile(BPE_2023_ZIP_PATH) as zf:
        data_name = next(name for name in zf.namelist() if name.lower() == "bpe23.csv")
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                rows_seen += 1
                year = row.get("AN", "")
                if year != "2023":
                    unexpected_years.add(year)
                    continue
                codgeo = row["DEPCOM"].zfill(5)
                if codgeo not in commune_map:
                    continue
                by_commune[codgeo] += 1.0
                rows_selected += 1

    by_zone: dict[str, float] = defaultdict(float)
    for codgeo, total in by_commune.items():
        by_zone[commune_map[codgeo]["ze2020"]] += total

    quality = {
        "source_file": BPE_2023_ZIP_PATH.name,
        "rows_seen": rows_seen,
        "rows_selected_mapped_communes": rows_selected,
        "unexpected_years": sorted(unexpected_years),
        "communes_with_bpe_2023": len(by_commune),
        "zones_with_bpe_2023": len(by_zone),
        "aggregation_rule": "Count one row per geolocated BPE equipment in BPE23.csv.",
    }
    return by_zone, quality


def write_side_interim(
    commune_map: dict[str, dict[str, str]],
    et_by_commune: dict[str, float],
    ul_by_commune: dict[str, float],
) -> dict[str, object]:
    codgeos = sorted(set(et_by_commune) | set(ul_by_commune))
    SIDE_2021_INTERIM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SIDE_2021_INTERIM_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "codgeo",
                "ze2020",
                "side_stocks_et_2021_total",
                "side_stocks_ul_2021_total",
            ],
        )
        writer.writeheader()
        for codgeo in codgeos:
            if codgeo not in commune_map:
                continue
            writer.writerow(
                {
                    "codgeo": codgeo,
                    "ze2020": commune_map[codgeo]["ze2020"],
                    "side_stocks_et_2021_total": fmt(et_by_commune.get(codgeo)),
                    "side_stocks_ul_2021_total": fmt(ul_by_commune.get(codgeo)),
                }
            )

    return {"side_interim_rows": len(codgeos)}


def write_bpe_interim(commune_map: dict[str, dict[str, str]], by_commune: dict[str, float]) -> dict[str, object]:
    BPE_2023_INTERIM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BPE_2023_INTERIM_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["codgeo", "ze2020", "bpe_facilities_2023_total"])
        writer.writeheader()
        for codgeo, total in sorted(by_commune.items()):
            writer.writerow(
                {
                    "codgeo": codgeo,
                    "ze2020": commune_map[codgeo]["ze2020"],
                    "bpe_facilities_2023_total": fmt(total),
                }
            )

    return {"bpe_interim_rows": len(by_commune)}


def add_columns(fieldnames: list[str], new_columns: list[str], before_column: str | None = None) -> list[str]:
    missing = [col for col in new_columns if col not in fieldnames]
    if not missing:
        return fieldnames
    if before_column and before_column in fieldnames:
        idx = fieldnames.index(before_column)
        return fieldnames[:idx] + missing + fieldnames[idx:]
    return fieldnames + missing


def update_zones_master(
    commune_map: dict[str, dict[str, str]],
    et_by_commune: dict[str, float],
    ul_by_commune: dict[str, float],
    bpe_2023_by_zone: dict[str, float],
) -> dict[str, object]:
    with ZONES_MASTER_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    side_et_by_zone: dict[str, float] = defaultdict(float)
    side_ul_by_zone: dict[str, float] = defaultdict(float)
    for codgeo, value in et_by_commune.items():
        if codgeo in commune_map:
            side_et_by_zone[commune_map[codgeo]["ze2020"]] += value
    for codgeo, value in ul_by_commune.items():
        if codgeo in commune_map:
            side_ul_by_zone[commune_map[codgeo]["ze2020"]] += value

    for row in rows:
        ze = row["ze2020"].zfill(4)
        pop_2021 = parse_number(row.get("population_2021_total", ""))
        pop_2022 = parse_number(row.get("population_2022_total", ""))

        side_et = side_et_by_zone.get(ze)
        side_ul = side_ul_by_zone.get(ze)
        bpe_2023 = bpe_2023_by_zone.get(ze)

        row["side_stocks_et_2021_total"] = fmt(side_et)
        row["side_stocks_ul_2021_total"] = fmt(side_ul)
        row["side_stocks_et_per_1000_pop_2021"] = fmt(side_et / pop_2021 * 1000.0 if side_et is not None and pop_2021 not in (None, 0) else None)
        row["bpe_facilities_2023_total"] = fmt(bpe_2023)
        row["bpe_facilities_per_1000_pop_2023"] = fmt(bpe_2023 / pop_2022 * 1000.0 if bpe_2023 is not None and pop_2022 not in (None, 0) else None)

    fieldnames = list(rows[0].keys())
    fieldnames = add_columns(
        fieldnames,
        ["side_stocks_et_2021_total", "side_stocks_ul_2021_total", "side_stocks_et_per_1000_pop_2021"],
        before_column="side_stocks_et_2023_total",
    )
    fieldnames = add_columns(
        fieldnames,
        ["bpe_facilities_2023_total", "bpe_facilities_per_1000_pop_2023"],
        before_column="bpe_facilities_2024_total",
    )

    with ZONES_MASTER_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "zones_with_side_et_2021": sum(1 for row in rows if row["side_stocks_et_2021_total"] != ""),
        "zones_with_side_ul_2021": sum(1 for row in rows if row["side_stocks_ul_2021_total"] != ""),
        "zones_with_bpe_2023": sum(1 for row in rows if row["bpe_facilities_2023_total"] != ""),
    }


def main() -> None:
    commune_map = load_mapping()

    side_et_by_commune, side_et_quality = aggregate_side_file(SIDE_ET_ZIP_PATH, "UNIT_LOC")
    side_ul_by_commune, side_ul_quality = aggregate_side_file(SIDE_UL_ZIP_PATH, "LEGAL_UNIT")
    bpe_2023_by_zone, bpe_quality = aggregate_bpe_2023(commune_map)

    bpe_by_commune: dict[str, float] = defaultdict(float)
    with zipfile.ZipFile(BPE_2023_ZIP_PATH) as zf:
        data_name = next(name for name in zf.namelist() if name.lower() == "bpe23.csv")
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                if row.get("AN") != "2023":
                    continue
                codgeo = row["DEPCOM"].zfill(5)
                if codgeo in commune_map:
                    bpe_by_commune[codgeo] += 1.0

    quality = {
        "side_et": side_et_quality,
        "side_ul": side_ul_quality,
        "bpe_2023": bpe_quality,
    }
    quality.update(write_side_interim(commune_map, side_et_by_commune, side_ul_by_commune))
    quality.update(write_bpe_interim(commune_map, bpe_by_commune))
    quality.update(update_zones_master(commune_map, side_et_by_commune, side_ul_by_commune, bpe_2023_by_zone))

    QUALITY_PATH.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
