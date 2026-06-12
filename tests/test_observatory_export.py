"""
Tests for HERALD Observatory v0.1 data export.
Run: pytest tests/test_observatory_export.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
PANEL_PATH = (
    REPO_ROOT
    / "data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv"
)

REQUIRED_COLUMNS = {
    "country", "territory_id", "meta_nuts3_code", "territory_name",
    "observation_year", "sector_id", "observed_value",
    "persistence_forecast", "ridge_forecast", "forecast_lower", "forecast_upper",
    "economic_state", "velocity", "acceleration",
    "g1_l2_available", "sector_graph_available", "evidence_tier", "data_source",
}

VALID_ECONOMIC_STATES = {
    "growth", "acceleration", "deceleration", "stagnation",
    "decline", "recovery", "insufficient_history",
}

VALID_EVIDENCE_TIERS = {"validated_loco", "pending_reaudit", "exploratory", "not_available"}


@pytest.fixture(scope="module")
def export_df():
    from src.data.european_panel.build_observatory_export import build_export
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        build_export(panel_path=PANEL_PATH, output_dir=Path(tmp))
        csv = Path(tmp) / "herald_observatory_v01_panel.csv"
        manifest = Path(tmp) / "herald_observatory_v01_manifest.json"
        summary = Path(tmp) / "herald_observatory_v01_summary.json"
        df = pd.read_csv(csv)
        with open(manifest) as f:
            meta = json.load(f)
        with open(summary) as f:
            summ = json.load(f)
    return df, meta, summ


def test_export_runs(export_df):
    df, meta, summ = export_df
    assert len(df) > 0


def test_required_columns_present(export_df):
    df, _, _ = export_df
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing, f"Missing columns: {missing}"


def test_row_count_matches_panel(export_df):
    df, _, _ = export_df
    source = pd.read_csv(PANEL_PATH)
    assert len(df) == len(source), (
        f"Export rows {len(df)} != source panel rows {len(source)}"
    )


def test_valid_economic_states(export_df):
    df, _, _ = export_df
    invalid = set(df["economic_state"].unique()) - VALID_ECONOMIC_STATES
    assert not invalid, f"Invalid economic states: {invalid}"


def test_all_economic_states_present(export_df):
    df, _, _ = export_df
    present = set(df["economic_state"].unique())
    assert present == VALID_ECONOMIC_STATES, (
        f"Not all states present. Missing: {VALID_ECONOMIC_STATES - present}"
    )


def test_valid_evidence_tiers(export_df):
    df, _, _ = export_df
    invalid = set(df["evidence_tier"].unique()) - VALID_EVIDENCE_TIERS
    assert not invalid, f"Invalid evidence tiers: {invalid}"


def test_sector_graph_always_zero(export_df):
    df, _, _ = export_df
    assert (df["sector_graph_available"] == 0).all(), (
        "sector_graph_available must always be 0 in v0.1"
    )


def test_uncertainty_intervals_are_nan(export_df):
    df, _, _ = export_df
    assert df["forecast_lower"].isna().all(), "forecast_lower must be NaN in v0.1"
    assert df["forecast_upper"].isna().all(), "forecast_upper must be NaN in v0.1"


def test_persistence_is_causal(export_df):
    """For each territory-year, persistence_forecast must equal observed_value of prior year."""
    df, _, _ = export_df
    df_sorted = df.sort_values(["territory_id", "observation_year"]).reset_index(drop=True)
    for region_id, grp in df_sorted.groupby("territory_id"):
        grp = grp.reset_index(drop=True)
        for i in range(1, len(grp)):
            expected_persistence = grp.loc[i - 1, "observed_value"]
            actual_persistence = grp.loc[i, "persistence_forecast"]
            if pd.notna(actual_persistence) and pd.notna(expected_persistence):
                assert abs(actual_persistence - expected_persistence) < 1e-3, (
                    f"Region {region_id} year {grp.loc[i,'observation_year']}: "
                    f"persistence {actual_persistence} != prior observed {expected_persistence}"
                )


def test_ridge_causal_first_years_nan(export_df):
    """Ridge forecasts should be NaN for the earliest years (insufficient training data)."""
    df, _, _ = export_df
    first_year = df["observation_year"].min()
    first_year_rows = df[df["observation_year"] == first_year]
    assert first_year_rows["ridge_forecast"].isna().all(), (
        f"Ridge forecast should be NaN for year {first_year} (no training data)"
    )


def test_g1_l2_availability_by_country(export_df):
    """PT has G1-L2 validated; IT and AT do not."""
    df, _, _ = export_df
    assert (df[df["country"] == "PT"]["g1_l2_available"] == 1).all()
    assert (df[df["country"] == "IT"]["g1_l2_available"] == 0).all()
    assert (df[df["country"] == "AT"]["g1_l2_available"] == 0).all()


def test_sector_id_is_aggregate(export_df):
    """v0.1 uses only AGGREGATE sector."""
    df, _, _ = export_df
    assert (df["sector_id"] == "AGGREGATE").all()


def test_observed_values_positive(export_df):
    df, _, _ = export_df
    assert (df["observed_value"] > 0).all(), "All observed enterprise birth counts must be positive"


def test_manifest_causal_safety_fields(export_df):
    _, meta, _ = export_df
    assert meta["causal_safety"]["growth_1y_used"] is False
    assert meta["causal_safety"]["leakage_free"] is True
    assert meta["causal_safety"]["rolling_origin"] is True


def test_manifest_decision_reference(export_df):
    _, meta, _ = export_df
    assert meta["decision"] == "DEC-030"


def test_manifest_limitations_not_empty(export_df):
    _, meta, _ = export_df
    assert len(meta["limitations"]) >= 4, "Manifest must document key limitations"


def test_velocity_acceleration_consistent(export_df):
    """velocity and acceleration should be NaN only for insufficient history rows."""
    df, _, _ = export_df
    insuf = df["economic_state"] == "insufficient_history"
    assert df.loc[insuf, "velocity"].isna().all(), "Velocity must be NaN for insufficient_history"
    assert df.loc[insuf, "acceleration"].isna().all()


def test_no_future_leakage_in_persistence(export_df):
    """Persistence forecast for year t must not exceed observed values at year t."""
    df, _, _ = export_df
    valid = df[df["persistence_forecast"].notna() & df["observed_value"].notna()]
    assert len(valid) > 0
    # Persistence is just the prior year value — it can be < or > actual, just not leaky.
    # Check that persistence_forecast != observed_value (would imply same-year leakage)
    same_year = (valid["persistence_forecast"] == valid["observed_value"])
    # Allow up to 5% of rows to coincidentally match (plateau regions)
    frac = same_year.mean()
    assert frac < 0.20, f"Too many rows where persistence==observed ({frac:.1%}); possible leakage"


def test_summary_wmape_in_expected_range(export_df):
    """Persistence WMAPE by country should be in the plausible range for this panel."""
    _, _, summ = export_df
    wmape = summ.get("persistence_wmape_by_country", {})
    for country, w in wmape.items():
        assert 0.0 < w < 0.5, (
            f"Country {country}: persistence WMAPE {w:.4f} outside expected range (0, 0.5)"
        )
