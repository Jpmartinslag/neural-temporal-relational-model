"""Tests for the France ZE2020 sectoral persistence audit (HERALD_58 A, DEC-083).

Written before the audit was executed, so they fix the specification's rules
rather than the numbers that came out of it. No test asserts an error metric
value; the gate logic is exercised on synthetic tables where the intended
verdict is known by construction.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.run_fr_ze2020_sectoral_persistence_audit import (  # noqa: E402
    ELIGIBLE_FOR_ENGINE,
    FEATURES,
    MIN_YEARLY_WINS,
    MODELS,
    NAIVE_CONTROLS,
    NATIONAL_SCALED,
    OFFICIAL_CELL_COUNT,
    OFFICIAL_FIRST_EVAL_YEAR,
    OFFICIAL_LAST_EVAL_YEAR,
    PERSISTENCE,
    RIDGE_AR,
    SECTOR_MEAN,
    SECTOR_REGRESSION_VETO,
    TARGET,
    ZE_SECTOR_MEAN,
    N_FOLDS,
    assign_folds,
    build_features,
    completeness_mask,
    evaluate_gate,
    load_panel,
    national_ratio,
    national_totals,
    predict_year,
    sector_veto,
    wmape,
)

SUPPLEMENT_FIRST_YEAR = 2013


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return load_panel()


@pytest.fixture(scope="module")
def featured(panel: pd.DataFrame) -> pd.DataFrame:
    return build_features(panel)


@pytest.fixture(scope="module")
def totals(panel: pd.DataFrame) -> pd.DataFrame:
    return national_totals(panel)


@pytest.fixture(scope="module")
def folds(panel: pd.DataFrame) -> dict[str, int]:
    return assign_folds(sorted(panel["ze2020"].unique()))


# --- window derived from the rules, not chosen ----------------------------


def test_feature_completeness_starts_2015(featured: pd.DataFrame) -> None:
    complete = completeness_mask(featured)
    assert int(featured.loc[complete, "year"].min()) == 2015


def test_official_window_is_the_registered_one() -> None:
    assert (OFFICIAL_FIRST_EVAL_YEAR, OFFICIAL_LAST_EVAL_YEAR) == (2019, 2025)
    assert OFFICIAL_CELL_COUNT == 7 * 2520 - 1


def test_completeness_uses_isfinite_not_notna(featured: pd.DataFrame) -> None:
    """The single observed zero makes a growth denominator infinite, not missing;
    notna() alone would let two corrupted rows through."""
    values = featured[FEATURES]
    infinite = np.isinf(values.to_numpy(dtype=float)).any(axis=1)
    assert infinite.sum() > 0, "fixture no longer exercises the infinite case"
    complete = completeness_mask(featured)
    assert not complete[infinite].any()


def test_excluded_cell_inside_the_official_window(featured: pd.DataFrame) -> None:
    """Only 5218/JZ/2019 falls inside 2019-2025; the 2018 cell is earlier."""
    complete = completeness_mask(featured)
    window = featured["year"].between(OFFICIAL_FIRST_EVAL_YEAR, OFFICIAL_LAST_EVAL_YEAR)
    excluded = featured[window & ~complete][["ze2020", "sector_code", "year"]]
    assert set(map(tuple, excluded.to_numpy())) == {("5218", "JZ", 2019)}


def test_incomplete_cells_from_2015_are_both_dropped_from_training(
    featured: pd.DataFrame,
) -> None:
    """2018 is never evaluated but must still leave the Ridge training rows."""
    complete = completeness_mask(featured)
    from_2015 = featured["year"] >= 2015
    incomplete = featured[from_2015 & ~complete][["ze2020", "sector_code", "year"]]
    assert set(map(tuple, incomplete.to_numpy())) == {
        ("5218", "JZ", 2018),
        ("5218", "JZ", 2019),
    }


# --- causality ------------------------------------------------------------


def test_features_use_only_prior_years(panel: pd.DataFrame, featured: pd.DataFrame) -> None:
    """lag_1 at year t must equal the observed value at t-1, per series."""
    merged = featured.merge(
        panel[["ze2020", "sector_code", "year", TARGET]].rename(
            columns={"year": "prior_year", TARGET: "prior_value"}
        ),
        left_on=["ze2020", "sector_code"],
        right_on=["ze2020", "sector_code"],
    )
    merged = merged[merged["prior_year"] == merged["year"] - 1]
    have_lag = merged["lag_1"].notna()
    assert (merged.loc[have_lag, "lag_1"] == merged.loc[have_lag, "prior_value"]).all()


def test_prediction_year_is_absent_from_every_input(
    featured: pd.DataFrame, totals: pd.DataFrame, folds: dict[str, int]
) -> None:
    """Truncating the panel after t must not change the predictions for t."""
    year = 2021
    full = predict_year(featured, totals, year, folds)
    truncated_panel = featured[featured["year"] <= year]
    truncated_totals = national_totals(truncated_panel)
    again = predict_year(truncated_panel, truncated_totals, year, folds)
    pd.testing.assert_frame_equal(
        full.sort_values(["ze2020", "sector_code"]).reset_index(drop=True),
        again.sort_values(["ze2020", "sector_code"]).reset_index(drop=True),
        check_dtype=False,
    )


# --- fold discipline ------------------------------------------------------


def test_folds_are_deterministic_and_seedless(panel: pd.DataFrame) -> None:
    zones = sorted(panel["ze2020"].unique())
    assert assign_folds(zones) == assign_folds(list(reversed(zones)))
    assert len(set(assign_folds(zones).values())) == N_FOLDS


def test_each_cell_predicted_exactly_once(
    featured: pd.DataFrame, totals: pd.DataFrame, folds: dict[str, int]
) -> None:
    out = predict_year(featured, totals, 2022, folds)
    assert not out.duplicated(["ze2020", "sector_code"]).any()
    assert len(out) == 2520


def test_all_models_share_one_population(
    featured: pd.DataFrame, totals: pd.DataFrame, folds: dict[str, int]
) -> None:
    out = predict_year(featured, totals, 2022, folds)
    for model in MODELS:
        assert out[model].notna().all()
        assert np.isfinite(out[model].to_numpy(dtype=float)).all()


def _contiguous_folds(zones: list[str]) -> dict[str, int]:
    """A genuinely different partition, not a relabelling.

    `(index + 1) % N_FOLDS` looks different but produces the same collection of
    groups with permuted labels, so every training set is unchanged and it
    cannot detect fold dependence. Contiguous blocks regroup the zones.
    """
    size = len(zones) // N_FOLDS
    return {zone: min(index // size, N_FOLDS - 1) for index, zone in enumerate(zones)}


def test_fold_independent_models_ignore_fold_membership(
    featured: pd.DataFrame, totals: pd.DataFrame, panel: pd.DataFrame
) -> None:
    """persistence, ze_sector_mean and national_scaled_persistence read the test
    cell's own causal history, so a different fold split must not move them."""
    zones = sorted(panel["ze2020"].unique())
    folds_a = assign_folds(zones)
    folds_b = _contiguous_folds(zones)
    year = 2023
    a = predict_year(featured, totals, year, folds_a).sort_values(["ze2020", "sector_code"])
    b = predict_year(featured, totals, year, folds_b).sort_values(["ze2020", "sector_code"])
    for model in (PERSISTENCE, ZE_SECTOR_MEAN, NATIONAL_SCALED):
        np.testing.assert_allclose(
            a[model].to_numpy(dtype=float), b[model].to_numpy(dtype=float)
        )


def test_sector_mean_is_cross_sectional_and_fold_dependent(
    featured: pd.DataFrame, totals: pd.DataFrame, panel: pd.DataFrame
) -> None:
    """sector_mean borrows from other zones, so it must change with the split."""
    zones = sorted(panel["ze2020"].unique())
    folds_a = assign_folds(zones)
    folds_b = _contiguous_folds(zones)
    year = 2023
    a = predict_year(featured, totals, year, folds_a).sort_values(["ze2020", "sector_code"])
    b = predict_year(featured, totals, year, folds_b).sort_values(["ze2020", "sector_code"])
    assert not np.allclose(
        a[SECTOR_MEAN].to_numpy(dtype=float), b[SECTOR_MEAN].to_numpy(dtype=float)
    )


def test_rotating_fold_labels_is_not_a_different_partition(panel: pd.DataFrame) -> None:
    """Guards the two tests above: shifting every label by one leaves the
    grouping identical, so it would silently weaken them into no-ops."""
    zones = sorted(panel["ze2020"].unique())
    base = assign_folds(zones)
    rotated = {zone: (index + 1) % N_FOLDS for index, zone in enumerate(zones)}
    groups = lambda mapping: {
        frozenset(z for z, f in mapping.items() if f == fold) for fold in range(N_FOLDS)
    }
    assert groups(base) == groups(rotated)
    assert groups(base) != groups(_contiguous_folds(zones))


def test_ze_sector_mean_is_own_history_not_training_zones(
    featured: pd.DataFrame, totals: pd.DataFrame, folds: dict[str, int]
) -> None:
    """The corrected rule: the own-history control reads the test cell's past.

    Restricting it to training zones would leave it undefined for the cells it
    scores, which is the contradiction the DEC-083 addendum removed.
    """
    year = 2020
    out = predict_year(featured, totals, year, folds)
    history = featured[featured["year"] < year]
    expected = history.groupby(["ze2020", "sector_code"])[TARGET].mean()
    merged = out.merge(
        expected.rename("expected"), on=["ze2020", "sector_code"], how="left"
    )
    np.testing.assert_allclose(
        merged[ZE_SECTOR_MEAN].to_numpy(dtype=float),
        merged["expected"].to_numpy(dtype=float),
    )


def test_persistence_equals_previous_observation(
    featured: pd.DataFrame, totals: pd.DataFrame, folds: dict[str, int]
) -> None:
    year = 2024
    out = predict_year(featured, totals, year, folds)
    prior = featured[featured["year"] == year - 1][["ze2020", "sector_code", TARGET]]
    merged = out.merge(prior, on=["ze2020", "sector_code"], how="left")
    np.testing.assert_allclose(
        merged[PERSISTENCE].to_numpy(dtype=float), merged[TARGET].to_numpy(dtype=float)
    )


# --- national ratio fails closed -----------------------------------------


def test_national_ratio_reads_nothing_after_t_minus_one(totals: pd.DataFrame) -> None:
    year = 2022
    expected = (
        totals[(totals.sector_code == "GI") & (totals.year == year - 1)]["national_total"].iloc[0]
        / totals[(totals.sector_code == "GI") & (totals.year == year - 2)]["national_total"].iloc[0]
    )
    assert national_ratio(totals, "GI", year) == pytest.approx(expected)


def test_zero_national_denominator_aborts(totals: pd.DataFrame) -> None:
    broken = totals.copy()
    target = broken.index[(broken.sector_code == "GI") & (broken.year == 2020)][0]
    broken.loc[target, "national_total"] = 0
    with pytest.raises(AssertionError, match="strictly positive"):
        national_ratio(broken, "GI", 2022)


def test_negative_national_denominator_aborts(totals: pd.DataFrame) -> None:
    broken = totals.copy()
    target = broken.index[(broken.sector_code == "GI") & (broken.year == 2020)][0]
    broken.loc[target, "national_total"] = -5
    with pytest.raises(AssertionError, match="strictly positive"):
        national_ratio(broken, "GI", 2022)


def test_missing_national_total_aborts(totals: pd.DataFrame) -> None:
    broken = totals[~((totals.sector_code == "GI") & (totals.year == 2020))]
    with pytest.raises(AssertionError, match="not uniquely defined"):
        national_ratio(broken, "GI", 2022)


# --- gate logic, on synthetic tables where the verdict is known -----------


def _metrics(
    overall: dict[str, float],
    yearly: dict[str, list[float]],
    sectoral: dict[str, dict[str, float]] | None = None,
) -> dict[str, object]:
    years = {
        str(2019 + i): {model: values[i] for model, values in yearly.items()}
        for i in range(len(next(iter(yearly.values()))))
    }
    sectors = sectoral or {"GI": {model: value for model, value in overall.items()}}
    return {
        "overall": {model: {"wmape": value, "mae": value} for model, value in overall.items()},
        "wmape_by_year": years,
        "wmape_by_sector": sectors,
    }


def _flat(values: dict[str, float], n: int = 7) -> dict[str, list[float]]:
    return {model: [value] * n for model, value in values.items()}


def test_persistence_designated_when_it_beats_controls() -> None:
    overall = {PERSISTENCE: 0.10, RIDGE_AR: 0.30, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["verdict"] == "ENGINE_DESIGNATED"
    assert gate["engine"] == PERSISTENCE


def test_ridge_designated_when_it_beats_persistence_and_controls() -> None:
    overall = {PERSISTENCE: 0.20, RIDGE_AR: 0.10, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["engine"] == RIDGE_AR


def test_no_engine_when_nothing_beats_controls() -> None:
    overall = {PERSISTENCE: 0.60, RIDGE_AR: 0.70, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["verdict"] == "NO_ENGINE_DESIGNATED"
    assert gate["engine"] is None


def test_exhaustive_clause_ridge_beats_controls_but_not_persistence() -> None:
    """A state the earlier non-exhaustive clause left without a verdict."""
    overall = {PERSISTENCE: 0.10, RIDGE_AR: 0.20, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["verdict"] == "ENGINE_DESIGNATED"
    assert gate["engine"] == PERSISTENCE


def test_exhaustive_clause_ridge_vetoed_and_persistence_fails_controls() -> None:
    """The state the earlier non-exhaustive clause left with no verdict at all.

    Ridge beats both controls and beats persistence, so "neither candidate beats
    both controls" is false; but the sector veto blocks it, and persistence
    itself fails the controls. No engine can be designated, yet the old clause 3
    would not have fired.
    """
    overall = {PERSISTENCE: 0.55, RIDGE_AR: 0.45, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.52}
    sectoral = {
        "GI": {PERSISTENCE: 0.55, RIDGE_AR: 0.45, SECTOR_MEAN: 0.5, ZE_SECTOR_MEAN: 0.52},
        "KZ": {PERSISTENCE: 0.20, RIDGE_AR: 0.40, SECTOR_MEAN: 0.5, ZE_SECTOR_MEAN: 0.52},
    }
    gate = evaluate_gate(_metrics(overall, _flat(overall), sectoral), 7)
    assert gate["naive_control_gate"][RIDGE_AR]["qualifies"] is True
    assert gate["ridge_vs_persistence"]["beats_aggregate"] is True
    assert gate["ridge_sector_safety_veto"]["vetoed"] is True
    assert gate["naive_control_gate"][PERSISTENCE]["qualifies"] is False
    assert gate["verdict"] == "NO_ENGINE_DESIGNATED"
    assert gate["engine"] is None


def test_ridge_not_beating_persistence_implies_persistence_beats_controls() -> None:
    """A coherence property of the gate, worth pinning.

    If Ridge qualifies against both controls but does not beat persistence, then
    persistence is at least as good as Ridge and therefore also beats both
    controls. The state "persistence fails the controls while Ridge passes them
    without beating it" is unreachable, so no verdict can be missing there.
    """
    overall = {PERSISTENCE: 0.45, RIDGE_AR: 0.46, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.47}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["naive_control_gate"][RIDGE_AR]["qualifies"] is True
    assert gate["ridge_vs_persistence"]["beats_aggregate"] is False
    assert gate["naive_control_gate"][PERSISTENCE]["qualifies"] is True
    assert gate["engine"] == PERSISTENCE


def test_tie_is_not_a_win() -> None:
    overall = {PERSISTENCE: 0.40, RIDGE_AR: 0.40, SECTOR_MEAN: 0.40, ZE_SECTOR_MEAN: 0.40}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["verdict"] == "NO_ENGINE_DESIGNATED"


def test_yearly_win_threshold_is_enforced() -> None:
    overall = {PERSISTENCE: 0.10, RIDGE_AR: 0.30, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    yearly = _flat(overall)
    # persistence loses to ze_sector_mean in two years -> 5 wins, below 6
    yearly[PERSISTENCE] = [0.10, 0.10, 0.10, 0.10, 0.10, 0.90, 0.90]
    gate = evaluate_gate(_metrics(overall, yearly), 7)
    assert gate["naive_control_gate"][PERSISTENCE][ZE_SECTOR_MEAN]["yearly_wins"] < MIN_YEARLY_WINS
    assert gate["verdict"] == "NO_ENGINE_DESIGNATED"


def test_sector_veto_blocks_ridge_but_cannot_promote() -> None:
    overall = {PERSISTENCE: 0.20, RIDGE_AR: 0.10, SECTOR_MEAN: 0.50, ZE_SECTOR_MEAN: 0.40}
    sectoral = {
        "GI": {PERSISTENCE: 0.20, RIDGE_AR: 0.10, SECTOR_MEAN: 0.5, ZE_SECTOR_MEAN: 0.4},
        "KZ": {PERSISTENCE: 0.20, RIDGE_AR: 0.30, SECTOR_MEAN: 0.5, ZE_SECTOR_MEAN: 0.4},
    }
    gate = evaluate_gate(_metrics(overall, _flat(overall), sectoral), 7)
    assert gate["ridge_sector_safety_veto"]["vetoed"] is True
    assert gate["clause_1_ridge_designated"] is False
    # Blocking Ridge must fall through to persistence, never to a control.
    assert gate["engine"] == PERSISTENCE


def test_sector_veto_threshold_is_ten_percent() -> None:
    by_sector = {
        "A": {PERSISTENCE: 0.20, RIDGE_AR: 0.22},  # exactly +10%, not a veto
        "B": {PERSISTENCE: 0.20, RIDGE_AR: 0.2201},  # just above, veto
    }
    assert SECTOR_REGRESSION_VETO == 0.10
    assert sector_veto({"A": by_sector["A"]}, RIDGE_AR)["vetoed"] is False
    assert sector_veto({"B": by_sector["B"]}, RIDGE_AR)["vetoed"] is True


def test_zero_reference_sector_vetoes_only_when_candidate_is_worse() -> None:
    assert sector_veto({"A": {PERSISTENCE: 0.0, RIDGE_AR: 0.0}}, RIDGE_AR)["vetoed"] is False
    assert sector_veto({"A": {PERSISTENCE: 0.0, RIDGE_AR: 0.1}}, RIDGE_AR)["vetoed"] is True


def test_nan_sector_reference_aborts() -> None:
    with pytest.raises(AssertionError, match="NaN WMAPE"):
        sector_veto({"A": {PERSISTENCE: float("nan"), RIDGE_AR: 0.1}}, RIDGE_AR)


def test_controls_and_baseline_are_never_eligible() -> None:
    """Even dominating every candidate, a control or the national baseline
    cannot be designated: eligibility is registered, not earned."""
    overall = {PERSISTENCE: 0.30, RIDGE_AR: 0.30, SECTOR_MEAN: 0.01, ZE_SECTOR_MEAN: 0.01}
    gate = evaluate_gate(_metrics(overall, _flat(overall)), 7)
    assert gate["engine"] is None
    assert set(gate["eligible_for_engine"]) == set(ELIGIBLE_FOR_ENGINE)
    for name in (SECTOR_MEAN, ZE_SECTOR_MEAN, NATIONAL_SCALED):
        assert name in gate["never_eligible"]


# --- metric definition ----------------------------------------------------


def test_wmape_definition() -> None:
    y = np.array([10.0, 20.0])
    yhat = np.array([12.0, 18.0])
    assert wmape(y, yhat) == pytest.approx(4.0 / 30.0)


def test_wmape_zero_denominator_is_nan_not_zero() -> None:
    assert np.isnan(wmape(np.array([0.0]), np.array([1.0])))


# --- end-to-end artifacts -------------------------------------------------


@pytest.fixture(scope="module")
def manifest_path() -> Path:
    return ROOT / "data/processed/france_ze2020/fr_ze2020_sectoral_persistence_audit_v1.json"


def test_manifest_records_environment_and_disclosures(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("audit not executed yet")
    import json

    manifest = json.loads(manifest_path.read_text())
    assert manifest["claim_status"].startswith("sectoral_persistence_audit")
    assert manifest["integrity"]["rows"] == OFFICIAL_CELL_COUNT
    assert manifest["integrity"]["duplicated_cells"] == 0
    assert manifest["integrity"]["seeds_used"] == 0
    assert manifest["integrity"]["truncation_invariance"] == "PASS"
    assert manifest["integrity"]["excluded_cell_count"] == 1
    assert "negative_predictions" in manifest["integrity"]
    for key in ("python", "pandas", "numpy", "scikit_learn"):
        assert manifest["environment"][key]
    assert manifest["persistence_only_supplement"]["comparability"] == "NOT_COMPARABLE"
    assert manifest["gate"]["verdict"] in {"ENGINE_DESIGNATED", "NO_ENGINE_DESIGNATED"}


def test_supplement_is_persistence_only_and_labelled(manifest_path: Path) -> None:
    supplement = ROOT / "data/processed/france_ze2020/fr_ze2020_sectoral_persistence_supplement_v1.csv"
    if not supplement.exists():
        pytest.skip("audit not executed yet")
    frame = pd.read_csv(supplement, dtype={"ze2020": str})
    assert PERSISTENCE in frame.columns
    for fitted in (RIDGE_AR, SECTOR_MEAN, ZE_SECTOR_MEAN, NATIONAL_SCALED):
        assert fitted not in frame.columns
    assert int(frame["year"].min()) == SUPPLEMENT_FIRST_YEAR


def test_runner_is_deterministic(tmp_path: Path) -> None:
    script = ROOT / "src/modeles/france_ze2020/run_fr_ze2020_sectoral_persistence_audit.py"
    hashes = []
    for name in ("run1", "run2"):
        out = tmp_path / name
        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", str(out), "--skip-truncation-check"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        import hashlib

        hashes.append(
            hashlib.sha256(
                (out / "fr_ze2020_sectoral_persistence_predictions_v1.csv").read_bytes()
            ).hexdigest()
        )
    assert hashes[0] == hashes[1]
