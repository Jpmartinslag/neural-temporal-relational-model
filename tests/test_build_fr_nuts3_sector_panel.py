from __future__ import annotations

import pandas as pd

from src.data.european_panel.build_fr_nuts3_sector_panel import (
    SECTORS,
    aggregate_side_chunk,
    build_department_to_nuts3,
    build_outputs,
    finalize_aggregates,
    normalize_name,
)


def test_normalize_name_handles_accents_and_punctuation() -> None:
    assert normalize_name("Côte-d’Or") == "cotedor"
    assert normalize_name("Cote d'Or") == "cotedor"


def test_department_to_nuts3_is_complete() -> None:
    departments = pd.DataFrame(
        {"DEP": ["01", "2A"], "LIBELLE": ["Ain", "Corse-du-Sud"]}
    )
    nuts = pd.DataFrame(
        {
            "CNTR_CODE": ["FR", "FR"],
            "LEVL_CODE": [3, 3],
            "NUTS_ID": ["FRK21", "FRM01"],
            "NUTS_NAME": ["Ain", "Corse-du-Sud"],
        }
    )
    result = build_department_to_nuts3(departments, nuts)
    assert result.set_index("DEP")["NUTS_ID"].to_dict() == {
        "01": "FRK21",
        "2A": "FRM01",
    }


def test_side_chunk_filters_and_aggregates() -> None:
    mapping = pd.DataFrame(
        {
            "CODGEO": ["01001", "01002"],
            "DEP": ["01", "01"],
            "NUTS_ID": ["FRK21", "FRK21"],
            "NUTS_NAME": ["Ain", "Ain"],
        }
    )
    rows = []
    for commune, value in (("01001", 2), ("01002", 3)):
        rows.extend(
            [
                {
                    "ACTIVITY": "BE",
                    "GEO": commune,
                    "GEO_OBJECT": "COM",
                    "LEGAL_FORM": "_T",
                    "SIDE_MEASURE": "UNIT_LOC_BURE",
                    "TIME_PERIOD": "2020",
                    "OBS_VALUE": str(value),
                },
                {
                    "ACTIVITY": "_T",
                    "GEO": commune,
                    "GEO_OBJECT": "COM",
                    "LEGAL_FORM": "_T",
                    "SIDE_MEASURE": "UNIT_LOC_BURE",
                    "TIME_PERIOD": "2020",
                    "OBS_VALUE": str(value + 10),
                },
            ]
        )
    rows.append(
        {
            "ACTIVITY": "BE",
            "GEO": "01001",
            "GEO_OBJECT": "COM",
            "LEGAL_FORM": "54",
            "SIDE_MEASURE": "UNIT_LOC_BURE",
            "TIME_PERIOD": "2020",
            "OBS_VALUE": "999",
        }
    )
    result = aggregate_side_chunk(pd.DataFrame(rows), mapping)
    values = result.set_index("activity")["value"].to_dict()
    assert values == {"BE": 5, "_T": 25}


def test_build_outputs_has_causal_lags_and_sector_schema() -> None:
    rows = []
    for year, total in ((2019, 90.0), (2020, 99.0), (2021, 108.0)):
        rows.append(
            {
                "NUTS_ID": "FRK21",
                "NUTS_NAME": "Ain",
                "year": year,
                "activity": "_T",
                "value": total,
            }
        )
        for sector in SECTORS:
            rows.append(
                {
                    "NUTS_ID": "FRK21",
                    "NUTS_NAME": "Ain",
                    "year": year,
                    "activity": sector,
                    "value": total / len(SECTORS),
                }
            )
    panel, sectors = build_outputs(finalize_aggregates([pd.DataFrame(rows)]))
    row_2021 = panel[panel["year"].eq(2021)].iloc[0]
    assert row_2021["lag1_births"] == 99.0
    assert row_2021["lag2_births"] == 90.0
    assert abs(row_2021["growth_1y"] - 0.1) < 1e-12
    assert sectors["mask_complete_sector_vector"].eq(1).all()
    assert sectors["available_for_forecast_year"].eq(
        sectors["observation_year"] + 1
    ).all()
    sector_sum = sectors.groupby(
        ["region_id", "observation_year"]
    )["sector_births"].sum()
    target = panel.set_index(["region_id", "year"])["target_births"]
    target.index = target.index.set_names(["region_id", "observation_year"])
    assert sector_sum.equals(target)
