from __future__ import annotations

import pandas as pd

from src.data.european_panel.build_dynamic_sector_preflight import (
    SECTORS,
    enrich_birth_panel,
    validate_birth_panel,
)


def _sample() -> pd.DataFrame:
    rows = []
    for year in (2020, 2021):
        for sector_index, sector in enumerate(SECTORS, start=1):
            rows.append(
                {
                    "country": "XX",
                    "region_id": "XX001",
                    "region_name": "Test",
                    "region_level": "NUTS3",
                    "observation_year": year,
                    "sector_a10": sector,
                    "sector_births": float(sector_index + year - 2020),
                    "source_label": "test",
                    "flag_target_concept": "test_birth",
                    "meta_region_system": "NUTS3",
                    "meta_source_label": "test",
                }
            )
    return pd.DataFrame(rows)


def test_enrichment_is_causal_and_shares_sum_to_one() -> None:
    panel = enrich_birth_panel(_sample())
    sums = panel.groupby(["country", "region_id", "observation_year"])["sector_share"].sum()
    assert (sums.round(12) == 1.0).all()
    assert (panel["available_for_forecast_year"] == panel["observation_year"] + 1).all()
    first_year = panel["observation_year"].min()
    assert panel.loc[panel["observation_year"].eq(first_year), "sector_growth_1y"].isna().all()


def test_validator_rejects_duplicate_keys() -> None:
    panel = enrich_birth_panel(_sample())
    broken = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
    errors, _ = validate_birth_panel(broken)
    assert any("duplicate" in error for error in errors)


def test_vocabulary_excludes_agriculture() -> None:
    assert "A" not in SECTORS
    assert SECTORS == ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]


def test_country_year_sector_with_zero_mass_is_not_complete() -> None:
    sample = _sample()
    sample.loc[sample["sector_a10"].eq("KZ"), "sector_births"] = 0.0
    panel = enrich_birth_panel(sample)
    assert panel.loc[panel["sector_a10"].eq("KZ"), "mask_sector_supported"].eq(0).all()
    assert panel["mask_complete_sector_vector"].eq(0).all()
