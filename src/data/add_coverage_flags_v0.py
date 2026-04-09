from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZONES_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"
QUALITY_PATH = ROOT / "reports" / "data_quality_report_v0.json"


def has_value(row: dict[str, str], key: str) -> bool:
    return row.get(key, "").strip() != ""


def main() -> None:
    with ZONES_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    output_rows = []
    eligible_count = 0
    anomaly_count = 0

    for row in rows:
        has_population = has_value(row, "population_2022_total")
        has_active = has_value(row, "active_15_64_2022_total")
        has_jobs_lt = has_value(row, "jobs_lt_2022_total")
        has_side_et = has_value(row, "side_stocks_et_2023_total")
        has_side_ul = has_value(row, "side_stocks_ul_2023_total")
        has_bpe = has_value(row, "bpe_facilities_2024_total")
        has_flores = has_value(row, "flores_presential_unit_loc_2024_total") and has_value(
            row, "flores_productive_unit_loc_2024_total"
        )
        has_filosofi = has_value(row, "filosofi_s_hh_tax_weighted_proxy_2021") and has_value(
            row, "filosofi_s_dir_tax_di_weighted_proxy_2021"
        )

        source_flags = [
            has_population,
            has_active,
            has_jobs_lt,
            has_side_et,
            has_side_ul,
            has_bpe,
            has_flores,
            has_filosofi,
        ]
        coverage_count = sum(source_flags)

        anomaly_reason = ""
        is_structural_anomaly = 0
        if row["ze2020"] == "0601":
            is_structural_anomaly = 1
            anomaly_reason = "structural_missing_rp_filosofi_mayotte"
            anomaly_count += 1

        # Core coverage excludes Filosofi because it is not available for every zone in the current scope.
        is_training_eligible = int(
            has_population
            and has_active
            and has_jobs_lt
            and has_side_et
            and has_side_ul
            and has_bpe
            and has_flores
            and not is_structural_anomaly
        )
        if is_training_eligible:
            eligible_count += 1

        row["has_population_2022"] = str(int(has_population))
        row["has_active_lr_2022"] = str(int(has_active))
        row["has_jobs_lt_2022"] = str(int(has_jobs_lt))
        row["has_side_stocks_et_2023"] = str(int(has_side_et))
        row["has_side_stocks_ul_2023"] = str(int(has_side_ul))
        row["has_bpe_2024"] = str(int(has_bpe))
        row["has_flores_2024"] = str(int(has_flores))
        row["has_filosofi_2021"] = str(int(has_filosofi))
        row["source_coverage_count"] = str(coverage_count)
        row["source_coverage_ratio"] = f"{coverage_count / 8:.6f}"
        row["is_structural_anomaly"] = str(is_structural_anomaly)
        row["anomaly_reason"] = anomaly_reason
        row["is_training_eligible_v0"] = str(is_training_eligible)
        output_rows.append(row)

    fieldnames = list(output_rows[0].keys())
    with ZONES_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    with QUALITY_PATH.open(encoding="utf-8") as f:
        quality = json.load(f)

    quality["zones_with_filosofi"] = sum(1 for row in output_rows if row["has_filosofi_2021"] == "1")
    quality["zones_with_flores"] = sum(1 for row in output_rows if row["has_flores_2024"] == "1")
    quality["training_eligible_zones_v0"] = eligible_count
    quality["structural_anomaly_zones_v0"] = anomaly_count
    quality["anomaly_zone_ids_v0"] = [row["ze2020"] for row in output_rows if row["is_structural_anomaly"] == "1"]

    with QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "zones_master_path": str(ZONES_PATH),
                "quality_report_path": str(QUALITY_PATH),
                "training_eligible_zones_v0": eligible_count,
                "structural_anomaly_zones_v0": anomaly_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
