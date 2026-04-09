from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZAN_PATH = ROOT / "data" / "interim" / "policy" / "zan_consumption_communes_v0.csv"
MAP_PATH = ROOT / "data" / "interim" / "mappings" / "commune_to_ze2020_2026.csv"
OUT_PATH = ROOT / "data" / "processed" / "zan_consumption_ze2020_v0.csv"
QUALITY_PATH = ROOT / "reports" / "zan_consumption_ze2020_quality_v0.json"

SUM_COLUMNS = [
    "naf09art24",
    "art09act24",
    "art09hab24",
    "art09mix24",
    "art09inc24",
    "art09rou24",
    "art09fer24",
    "artcom0924",
    "pop15",
    "pop21",
    "men15",
    "men21",
    "emp15",
    "emp21",
    "surfcom2024",
]


def to_float(value: str) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    return float(text.replace(",", "."))


def main() -> None:
    commune_to_zone = {}
    zone_labels = {}
    with MAP_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            codgeo = row["CODGEO"].zfill(5)
            zone = row["ZE2020"].zfill(4)
            commune_to_zone[codgeo] = zone
            zone_labels[zone] = row["LIBZE2020"]

    aggregates = {}
    mapped_rows = 0
    unmapped_rows = 0

    with ZAN_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            codgeo = row["idcom"].zfill(5)
            zone = commune_to_zone.get(codgeo)
            if not zone:
                unmapped_rows += 1
                continue
            mapped_rows += 1
            bucket = aggregates.setdefault(
                zone,
                {
                    "ze2020": zone,
                    "libze2020": zone_labels.get(zone, ""),
                    "communes_count": 0,
                    **{f"zan_{col}_total": 0.0 for col in SUM_COLUMNS},
                },
            )
            bucket["communes_count"] += 1
            for col in SUM_COLUMNS:
                bucket[f"zan_{col}_total"] += to_float(row[col])

    rows = []
    for zone in sorted(aggregates):
        row = aggregates[zone]
        total_artif = row["zan_naf09art24_total"]
        pop21 = row["zan_pop21_total"]
        surface = row["zan_surfcom2024_total"]
        row["zan_artif_per_pop21"] = round(total_artif / pop21, 6) if pop21 else ""
        row["zan_artif_per_surface"] = round(total_artif / surface, 9) if surface else ""
        normalized = {}
        for key, value in row.items():
            if isinstance(value, float):
                normalized[key] = round(value, 6)
            else:
                normalized[key] = value
        rows.append(normalized)

    fieldnames = list(rows[0].keys()) if rows else [
        "ze2020",
        "libze2020",
        "communes_count",
    ]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    quality = {
        "rows": len(rows),
        "mapped_rows": mapped_rows,
        "unmapped_rows": unmapped_rows,
        "sum_columns": SUM_COLUMNS,
        "notes": [
            "ZAN commune quantitative layer aggregated to ZE2020 using additive columns only.",
            "Derived rates are limited to artif per population 2021 and artif per municipal surface 2024.",
        ],
    }
    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "out_path": str(OUT_PATH),
                "quality_path": str(QUALITY_PATH),
                "rows": len(rows),
                "mapped_rows": mapped_rows,
                "unmapped_rows": unmapped_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
