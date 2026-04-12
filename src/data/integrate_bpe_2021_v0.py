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
BPE_2021_ZIP_PATH = ROOT / "data" / "raw" / "temporal_depth" / "bpe" / "bpe21-ensemble-csv.zip"
BPE_2021_INTERIM_PATH = ROOT / "data" / "interim" / "tables" / "bpe_commune_2021.csv"
QUALITY_PATH = ROOT / "reports" / "bpe_2021_integration_quality_v0.json"


def parse_number(value: str) -> float | None:
    if value is None:
        return None
    raw = value.strip().replace("\xa0", "")
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
    commune_map: dict[str, dict[str, str]] = {}
    with MAPPING_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codgeo = row["CODGEO"].zfill(5)
            commune_map[codgeo] = {
                "ze2020": row["ZE2020"].zfill(4),
                "libze2020": row["LIBZE2020"],
                "reg": row["REG"].zfill(2) if row["REG"] else "",
            }
    return commune_map


def aggregate_bpe_2021(commune_map: dict[str, dict[str, str]]) -> tuple[dict[str, float], dict[str, object]]:
    by_commune: dict[str, float] = defaultdict(float)
    rows_selected = 0

    with zipfile.ZipFile(BPE_2021_ZIP_PATH) as zf:
        data_name = next(name for name in zf.namelist() if name.lower().endswith("bpe21_ensemble.csv"))
        with zf.open(data_name) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                if row["AN"] != "2021":
                    continue
                codgeo = row["DEPCOM"].zfill(5)
                if codgeo not in commune_map:
                    continue
                value = parse_number(row["NB_EQUIP"])
                if value is None:
                    continue
                by_commune[codgeo] += value
                rows_selected += 1

    BPE_2021_INTERIM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BPE_2021_INTERIM_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["codgeo", "ze2020", "bpe_facilities_2021_total"])
        writer.writeheader()
        for codgeo, total in sorted(by_commune.items()):
            writer.writerow(
                {
                    "codgeo": codgeo,
                    "ze2020": commune_map[codgeo]["ze2020"],
                    "bpe_facilities_2021_total": fmt(total),
                }
            )

    by_zone: dict[str, float] = defaultdict(float)
    for codgeo, total in by_commune.items():
        by_zone[commune_map[codgeo]["ze2020"]] += total

    quality = {
        "rows_selected": rows_selected,
        "communes_with_bpe_2021": len(by_commune),
        "zones_with_bpe_2021": len(by_zone),
        "mayotte_communes_with_bpe_2021": sum(1 for c in by_commune if commune_map[c]["ze2020"] == "0601"),
    }
    return by_zone, quality


def update_zones_master(by_zone: dict[str, float]) -> dict[str, object]:
    with ZONES_MASTER_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        ze = row["ze2020"].zfill(4)
        total = by_zone.get(ze)
        pop_2021 = parse_number(row.get("population_2021_total", ""))
        per_1000 = None
        if total is not None and pop_2021 not in (None, 0):
            per_1000 = total / pop_2021 * 1000.0
        row["bpe_facilities_2021_total"] = fmt(total)
        row["bpe_facilities_per_1000_pop_2021"] = fmt(per_1000)

    fieldnames = list(rows[0].keys())
    if "bpe_facilities_2021_total" not in fieldnames:
        insert_at = fieldnames.index("bpe_facilities_2024_total")
        fieldnames = (
            fieldnames[:insert_at]
            + ["bpe_facilities_2021_total", "bpe_facilities_per_1000_pop_2021"]
            + fieldnames[insert_at:]
        )

    with ZONES_MASTER_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    zones_with_total = sum(1 for row in rows if row["bpe_facilities_2021_total"] != "")
    return {
        "zones_master_rows": len(rows),
        "zones_with_bpe_2021": zones_with_total,
    }


def main() -> None:
    commune_map = load_mapping()
    by_zone, quality = aggregate_bpe_2021(commune_map)
    quality.update(update_zones_master(by_zone))
    QUALITY_PATH.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
