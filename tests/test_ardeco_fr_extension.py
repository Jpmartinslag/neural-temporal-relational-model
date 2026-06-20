from __future__ import annotations

import pandas as pd

from src.data.european_panel.audit_ardeco_fr_extension import audit_frames


def _france(level: str = "ZE2020", with_nuts: bool = False) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region_id": ["1101", "1102"],
            "region_level": [level, level],
            "year": [2024, 2024],
            "meta_nuts3_code": ["FR101", "FR102"] if with_nuts else ["", ""],
        }
    )


def _ardeco(years: range = range(2016, 2024)) -> pd.DataFrame:
    rows = []
    for year in years:
        for region in ("FR101", "FR102"):
            for sector in ("A", "B-E", "F", "G-I", "J", "K", "L", "M_N", "O-Q"):
                rows.append(
                    {
                        "TERRITORY_ID": region,
                        "YEAR": year,
                        "SECTOR": sector,
                        "VALUE": 1.0,
                        "COUNTRY_REQUEST": "FR",
                    }
                )
    return pd.DataFrame(rows)


def _commune_ze() -> pd.DataFrame:
    return pd.DataFrame({"CODGEO": ["01001", "01002"], "ZE2020": ["1101", "1102"]})


def test_current_ze_panel_is_blocked() -> None:
    result = audit_frames(_france(), _ardeco(), _commune_ze())
    assert result["decision"] == "ARDECO_FR_EXTENSION_BLOCKED_PRETRAIN"
    assert not result["checks"]["c4_france_panel_is_nuts3"]
    assert result["inventory"]["direct_region_overlap"] == 0


def test_single_ardeco_year_is_blocked() -> None:
    result = audit_frames(
        _france(level="NUTS3", with_nuts=True),
        _ardeco(range(2024, 2025)).assign(
            TERRITORY_ID=lambda frame: frame["TERRITORY_ID"]
        ),
        _commune_ze(),
    )
    assert not result["checks"]["c2_ardeco_history_at_least_8_years"]
    assert result["decision"] == "ARDECO_FR_EXTENSION_BLOCKED_PRETRAIN"


def test_nuts3_panel_with_history_can_pass() -> None:
    france = _france(level="NUTS3", with_nuts=True)
    france["region_id"] = france["meta_nuts3_code"]
    result = audit_frames(france, _ardeco(), _commune_ze())
    assert all(
        result["checks"][key]
        for key in (
            "c1_local_ardeco_fr_present",
            "c2_ardeco_history_at_least_8_years",
            "c3_ardeco_has_at_least_9_sectors",
            "c4_france_panel_is_nuts3",
            "c5_france_panel_has_nuts3_codes",
            "c6_direct_region_overlap_at_least_95pct",
        )
    )
    assert result["decision"] == "ARDECO_FR_EXTENSION_READY"


def test_commune_ze_is_not_treated_as_nuts_crosswalk() -> None:
    result = audit_frames(_france(), _ardeco(), _commune_ze())
    assert result["checks"]["c7_commune_to_ze_mapping_present"]
    assert not result["checks"]["c5_france_panel_has_nuts3_codes"]
    assert result["decision"] == "ARDECO_FR_EXTENSION_BLOCKED_PRETRAIN"
