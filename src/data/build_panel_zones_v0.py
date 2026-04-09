from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZONES_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_v0.csv"
PANEL_QUALITY_PATH = ROOT / "reports" / "panel_zones_quality_v0.json"
PANEL_FEATURE_REGISTRY_PATH = ROOT / "metadata" / "panel_feature_registry_v0.csv"

YEARS = [2021, 2022, 2023, 2024]

FEATURE_SPECS = [
    ("filosofi_s_hh_tax_weighted_proxy", "filosofi_s_hh_tax_weighted_proxy_2021", 2021, "income"),
    ("filosofi_s_dir_tax_di_weighted_proxy", "filosofi_s_dir_tax_di_weighted_proxy_2021", 2021, "income"),
    ("population_total", "population_2022_total", 2022, "population"),
    ("active_lr_total", "active_15_64_2022_total", 2022, "labour"),
    ("employed_lr_total", "employed_15_64_2022_total", 2022, "labour"),
    ("unemployed_lr_total", "unemployed_15_64_2022_total", 2022, "labour"),
    ("unemployment_rate_est", "unemployment_rate_est_2022", 2022, "labour"),
    ("jobs_lt_total", "jobs_lt_2022_total", 2022, "labour"),
    ("jobs_lt_per_1000_pop", "jobs_lt_per_1000_pop_2022", 2022, "labour"),
    ("side_stocks_et_total", "side_stocks_et_2023_total", 2023, "economic_structure"),
    ("side_stocks_ul_total", "side_stocks_ul_2023_total", 2023, "economic_structure"),
    ("side_stocks_et_per_1000_pop", "side_stocks_et_per_1000_pop_2023", 2023, "economic_structure"),
    ("bpe_facilities_total", "bpe_facilities_2024_total", 2024, "services"),
    ("bpe_facilities_per_1000_pop", "bpe_facilities_per_1000_pop_2024", 2024, "services"),
    ("flores_presential_unit_loc_total", "flores_presential_unit_loc_2024_total", 2024, "economic_structure"),
    ("flores_productive_unit_loc_total", "flores_productive_unit_loc_2024_total", 2024, "economic_structure"),
]


def has_value(value: str) -> bool:
    return value.strip() != ""


def write_feature_registry() -> None:
    PANEL_FEATURE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PANEL_FEATURE_REGISTRY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["panel_feature", "zones_master_column", "source_year", "domain", "panel_rule"],
        )
        writer.writeheader()
        for feature_name, source_col, source_year, domain in FEATURE_SPECS:
            writer.writerow(
                {
                    "panel_feature": feature_name,
                    "zones_master_column": source_col,
                    "source_year": source_year,
                    "domain": domain,
                    "panel_rule": "populate only on matching source year; keep blank otherwise",
                }
            )


def main() -> None:
    with ZONES_PATH.open(encoding="utf-8", newline="") as f:
        zones = list(csv.DictReader(f))

    rows = []
    years_with_any_feature = {str(year): 0 for year in YEARS}
    training_eligible_panel_rows = 0

    for zone in zones:
        for year in YEARS:
            row = {
                "ze2020": zone["ze2020"],
                "libze2020": zone["libze2020"],
                "reg": zone["reg"],
                "year": str(year),
                "is_structural_anomaly": zone["is_structural_anomaly"],
                "anomaly_reason": zone["anomaly_reason"],
            }
            observed_count = 0
            for panel_feature, source_col, source_year, _domain in FEATURE_SPECS:
                value = zone[source_col] if year == source_year else ""
                row[panel_feature] = value
                if has_value(value):
                    observed_count += 1

            row["observed_feature_count"] = str(observed_count)
            row["has_any_feature_value"] = str(int(observed_count > 0))
            row["is_source_year_row"] = str(int(observed_count > 0))
            row["is_training_eligible_panel_v0"] = str(
                int(zone["is_training_eligible_v0"] == "1" and zone["is_structural_anomaly"] == "0")
            )

            if observed_count > 0:
                years_with_any_feature[str(year)] += 1
            if row["is_training_eligible_panel_v0"] == "1":
                training_eligible_panel_rows += 1
            rows.append(row)

    fieldnames = [
        "ze2020",
        "libze2020",
        "reg",
        "year",
        "is_structural_anomaly",
        "anomaly_reason",
        *[feature_name for feature_name, *_ in FEATURE_SPECS],
        "observed_feature_count",
        "has_any_feature_value",
        "is_source_year_row",
        "is_training_eligible_panel_v0",
    ]

    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PANEL_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_feature_registry()

    quality = {
        "panel_rows": len(rows),
        "panel_years": YEARS,
        "zones_count": len(zones),
        "years_with_any_feature_rows": years_with_any_feature,
        "training_eligible_panel_rows_v0": training_eligible_panel_rows,
        "structural_anomaly_zones_v0": sum(1 for zone in zones if zone["is_structural_anomaly"] == "1"),
        "panel_rule": "No temporal imputation. Each feature is populated only on its observed source year.",
    }

    with PANEL_QUALITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "panel_path": str(PANEL_PATH),
                "panel_quality_path": str(PANEL_QUALITY_PATH),
                "panel_feature_registry_path": str(PANEL_FEATURE_REGISTRY_PATH),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
