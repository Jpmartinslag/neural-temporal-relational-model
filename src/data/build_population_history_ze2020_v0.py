from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
POP_HISTORY_PATH = ROOT / "data" / "interim" / "population_history" / "population_history_communes_v0.csv"
OUT_PATH = ROOT / "data" / "processed" / "population_history_ze2020_v0.csv"
QUALITY_PATH = ROOT / "reports" / "population_history_ze2020_quality_v0.json"


def parse_number(value: str) -> float | None:
    raw = (value or "").strip()
    if raw == "":
        return None
    return float(raw.replace(",", "."))


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value - round(value)) < 1e-9:
        return f"{value:.1f}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def main() -> None:
    commune_to_zone: dict[str, dict[str, str]] = {}
    zones: dict[str, dict[str, str]] = {}
    with MAPPING_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            codgeo = row["CODGEO"].zfill(5)
            ze = row["ZE2020"].zfill(4)
            commune_to_zone[codgeo] = {
                "ze2020": ze,
                "libze2020": row["LIBZE2020"],
                "reg": row["REG"].zfill(2) if row["REG"] else "",
            }
            zones.setdefault(
                ze,
                {
                    "ze2020": ze,
                    "libze2020": row["LIBZE2020"],
                    "reg": row["REG"].zfill(2) if row["REG"] else "",
                },
            )

    with POP_HISTORY_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        time_columns = [c for c in reader.fieldnames if c not in {"codgeo", "reg", "dep", "libgeo"}]
        totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        covered_communes = 0
        missing_mapped_communes = 0
        for row in reader:
            codgeo = row["codgeo"].zfill(5)
            info = commune_to_zone.get(codgeo)
            if info is None:
                missing_mapped_communes += 1
                continue
            covered_communes += 1
            ze = info["ze2020"]
            for col in time_columns:
                value = parse_number(row[col])
                if value is not None:
                    totals[ze][col] += value

    output_rows = []
    missing_recent_2023 = []
    for ze, meta in sorted(zones.items()):
        row = dict(meta)
        for col in time_columns:
            row[col] = fmt(totals.get(ze, {}).get(col))
        if row.get("PMUN2023", "") == "":
            missing_recent_2023.append(ze)
        output_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["ze2020", "libze2020", "reg", *time_columns]
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    quality = {
        "zones_count": len(output_rows),
        "time_columns_count": len(time_columns),
        "covered_communes": covered_communes,
        "unmapped_communes_in_population_history": missing_mapped_communes,
        "zones_missing_pmun2023": missing_recent_2023,
        "notes": [
            "Aggregation uses commune_to_ze2020_2026 bridge.",
            "Population history source is France hors Mayotte, so ZE 0601 remains structurally uncovered.",
        ],
    }
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "out_path": str(OUT_PATH),
                "quality_path": str(QUALITY_PATH),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
