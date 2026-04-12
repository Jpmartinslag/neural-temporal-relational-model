from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ZONES_PATH = ROOT / "data" / "processed" / "zones_master_annual_v0.csv"
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_v0.csv"
PANEL_QUALITY_PATH = ROOT / "reports" / "panel_zones_quality_v0.json"
PANEL_FEATURE_REGISTRY_PATH = ROOT / "metadata" / "panel_feature_registry_v0.csv"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

FEATURE_SPECS = {
    2019: [
        (
            "bpe_evolution_commune_type_presence_total",
            "bpe_evolution_commune_type_presence_2019_total",
            "services_harmonized",
        ),
    ],
    2020: [
        ("filosofi_s_hh_tax_weighted_proxy", "filosofi_s_hh_tax_weighted_proxy_2020", "income"),
        ("filosofi_s_dir_tax_di_weighted_proxy", "filosofi_s_dir_tax_di_weighted_proxy_2020", "income"),
    ],
    2021: [
        ("population_total", "population_2021_total", "population"),
        ("active_lr_total", "active_15_64_2021_total", "labour"),
        ("employed_lr_total", "employed_15_64_2021_total", "labour"),
        ("unemployed_lr_total", "unemployed_15_64_2021_total", "labour"),
        ("unemployment_rate_est", "unemployment_rate_est_2021", "labour"),
        ("jobs_lt_total", "jobs_lt_2021_total", "labour"),
        ("jobs_lt_per_1000_pop", "jobs_lt_per_1000_pop_2021", "labour"),
        ("side_stocks_et_total", "side_stocks_et_2021_total", "economic_structure"),
        ("side_stocks_ul_total", "side_stocks_ul_2021_total", "economic_structure"),
        ("side_stocks_et_per_1000_pop", "side_stocks_et_per_1000_pop_2021", "economic_structure"),
        ("bpe_facilities_total", "bpe_facilities_2021_total", "services"),
        ("bpe_facilities_per_1000_pop", "bpe_facilities_per_1000_pop_2021", "services"),
        ("filosofi_s_hh_tax_weighted_proxy", "filosofi_s_hh_tax_weighted_proxy_2021", "income"),
        ("filosofi_s_dir_tax_di_weighted_proxy", "filosofi_s_dir_tax_di_weighted_proxy_2021", "income"),
    ],
    2022: [
        ("population_total", "population_2022_total", "population"),
        ("active_lr_total", "active_15_64_2022_total", "labour"),
        ("employed_lr_total", "employed_15_64_2022_total", "labour"),
        ("unemployed_lr_total", "unemployed_15_64_2022_total", "labour"),
        ("unemployment_rate_est", "unemployment_rate_est_2022", "labour"),
        ("jobs_lt_total", "jobs_lt_2022_total", "labour"),
        ("jobs_lt_per_1000_pop", "jobs_lt_per_1000_pop_2022", "labour"),
    ],
    2023: [
        ("side_stocks_et_total", "side_stocks_et_2023_total", "economic_structure"),
        ("side_stocks_ul_total", "side_stocks_ul_2023_total", "economic_structure"),
        ("side_stocks_et_per_1000_pop", "side_stocks_et_per_1000_pop_2023", "economic_structure"),
        ("bpe_facilities_total", "bpe_facilities_2023_total", "services"),
        ("bpe_facilities_per_1000_pop", "bpe_facilities_per_1000_pop_2023", "services"),
    ],
    2024: [
        (
            "bpe_evolution_commune_type_presence_total",
            "bpe_evolution_commune_type_presence_2024_total",
            "services_harmonized",
        ),
        ("bpe_facilities_total", "bpe_facilities_2024_total", "services"),
        ("bpe_facilities_per_1000_pop", "bpe_facilities_per_1000_pop_2024", "services"),
        ("flores_presential_unit_loc_total", "flores_presential_unit_loc_2024_total", "economic_structure"),
        ("flores_productive_unit_loc_total", "flores_productive_unit_loc_2024_total", "economic_structure"),
    ],
}


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
        for source_year in YEARS:
            for feature_name, source_col, domain in FEATURE_SPECS.get(source_year, []):
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
            feature_values = {feature_name: "" for spec_year in YEARS for feature_name, _source_col, _domain in FEATURE_SPECS.get(spec_year, [])}
            for panel_feature, source_col, _domain in FEATURE_SPECS.get(year, []):
                value = zone.get(source_col, "")
                feature_values[panel_feature] = value
            for panel_feature, value in feature_values.items():
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
        *list(dict.fromkeys(feature_name for spec_year in YEARS for feature_name, _source_col, _domain in FEATURE_SPECS.get(spec_year, []))),
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
