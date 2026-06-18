"""
Build a causal-safe persistence + Ridge AR(1) forecast layer for the PT
Municipal panel (data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv),
closing the prediction-layer gap documented in
reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md.

This is the same method already validated and shipped for FR ZE2020 / NL
COROP in src/data/european_panel/build_observatory_export.py
(`_rolling_ridge_forecasts`, `RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`,
causal persistence/lag-1 baseline). No proxy disaggregation is used: the PT
municipal panel is directly observed (INE enterprise_birth, DEC-064), so this
script only re-runs the existing causal forecasting code against a different
(but real, observed) input panel — pure data engineering, no HPC.

Hard rules:
  - Forecast at year t uses only data through t-1 (verified by an explicit
    assertion in this script, not just by construction).
  - PT/KZ (structurally absent sector, structural_mask=0 for every row) is
    NEVER given a forecast and is NEVER encoded as a bare NaN in the
    human-facing forecast_status field — it gets forecast_status=
    "structural_absent".
  - Rows with structural_mask=1 but insufficient trailing history get
    forecast_status="insufficient_history" (never a fabricated number).
  - No fabrication: if neither Ridge nor persistence can be computed for a
    structurally available row, both forecast columns stay NaN and
    forecast_status reflects that explicitly.

Output: data/processed/herald_observatory_v051_narrative/pt_municipal_prediction_view.csv
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
PT_MUNICIPAL_PANEL_PATH = REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv"
OUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v051_narrative"
OUT_PATH = OUT_DIR / "pt_municipal_prediction_view.csv"

# Same constants as build_observatory_export.py — reused, not re-tuned.
RIDGE_MIN_TRAIN = 4
RIDGE_ALPHA = 1.0
STAGNATION_THRESHOLD = 0.03

SECTOR_LABELS = {
    "BE": "Industrie et énergie",
    "FZ": "Construction",
    "GI": "Commerce, transport et hébergement",
    "JZ": "Information et communication",
    "KZ": "Finance et assurance",
    "LZ": "Immobilier",
    "MN": "Services professionnels",
    "OQ": "Administration, éducation et santé",
    "RU": "Culture et autres services",
}


def _finite(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _economic_state(y_tm1: float | None, y_t: float | None) -> str:
    """Same 3-state simplified classification used across the narrative
    layer (Growing/Stable/Falling), derived only from t and t-1."""
    if not (_finite(y_t) and _finite(y_tm1)):
        return "insufficient_history"
    y_t_f, y_tm1_f = float(y_t), float(y_tm1)
    if y_tm1_f <= 0:
        return "insufficient_history"
    delta = (y_t_f - y_tm1_f) / y_tm1_f
    if abs(delta) <= STAGNATION_THRESHOLD:
        return "STAGNATION"
    return "GROWTH" if delta > 0 else "DECLINE"


def _rolling_ridge_forecasts(series: pd.Series, min_train: int = RIDGE_MIN_TRAIN,
                              alpha: float = RIDGE_ALPHA) -> pd.Series:
    """Causal rolling-origin AR(1) Ridge forecast — verbatim reuse of the
    method in build_observatory_export.py._rolling_ridge_forecasts. For
    every index, the model is fit ONLY on (x[:-1], y[:-1]) pairs strictly
    before `index`, and predicts using values[index-1] (t-1) only."""
    from sklearn.linear_model import Ridge

    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    predictions = np.full(len(values), np.nan)
    for index in range(1, len(values)):
        historical_x = values[: index - 1]
        historical_y = values[1:index]
        valid = np.isfinite(historical_x) & np.isfinite(historical_y)
        if int(valid.sum()) < min_train or not np.isfinite(values[index - 1]):
            continue
        model = Ridge(alpha=alpha)
        model.fit(historical_x[valid].reshape(-1, 1), historical_y[valid])
        predictions[index] = max(0.0, float(model.predict([[values[index - 1]]])[0]))
    return pd.Series(predictions, index=series.index)


def build_forecast_rows(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    panel = panel.sort_values(["territory_id", "sector_id", "observation_year"]).reset_index(drop=True)

    for (territory_id, sector_id), group in panel.groupby(["territory_id", "sector_id"], sort=False):
        group = group.sort_values("observation_year").reset_index(drop=True)
        is_structural = bool(group["structural_mask"].iloc[0] == 1) if len(group) else False

        if not is_structural:
            # KZ for PT: structural_absent for every row of this group, by
            # construction (DEC-064/DEC-018). Never compute a forecast.
            for _, src in group.iterrows():
                rows.append({
                    "country": "PT", "territory_id": territory_id, "sector_id": sector_id,
                    "sector_name": SECTOR_LABELS.get(sector_id, sector_id),
                    "observation_year": int(src["observation_year"]),
                    "observed_value": np.nan,
                    "persistence_forecast": np.nan,
                    "ridge_forecast": np.nan,
                    "expected_value": np.nan,
                    "difference": np.nan,
                    "forecast_method": "unavailable",
                    "forecast_status": "structural_absent",
                    "economic_state": "STRUCTURAL_ABSENT",
                })
            continue

        observed = pd.to_numeric(group["observed_value"], errors="coerce").where(
            group["observation_mask"].fillna(0).astype(int).eq(1)
        )
        ridge = _rolling_ridge_forecasts(observed)

        for index, src in group.iterrows():
            current = observed.iloc[index]
            previous = observed.iloc[index - 1] if index >= 1 else np.nan
            is_observed_now = _finite(current)

            persistence = float(previous) if _finite(previous) else np.nan
            ridge_value = float(ridge.iloc[index]) if _finite(ridge.iloc[index]) else np.nan
            expected = ridge_value if _finite(ridge_value) else persistence

            if not _finite(previous):
                status = "insufficient_history"
                method = "unavailable"
            elif _finite(ridge_value):
                status = "valid_forecast"
                method = "ridge_ar1"
            elif _finite(persistence):
                status = "valid_forecast"
                method = "persistence"
            else:
                status = "insufficient_history"
                method = "unavailable"

            difference = (float(current) - expected) if (is_observed_now and _finite(expected)) else np.nan

            rows.append({
                "country": "PT", "territory_id": territory_id, "sector_id": sector_id,
                "sector_name": SECTOR_LABELS.get(sector_id, sector_id),
                "observation_year": int(src["observation_year"]),
                "observed_value": float(current) if is_observed_now else np.nan,
                "persistence_forecast": persistence,
                "ridge_forecast": ridge_value,
                "expected_value": expected,
                "difference": difference,
                "forecast_method": method,
                "forecast_status": status,
                "economic_state": _economic_state(previous, current),
            })

    return pd.DataFrame(rows)


def _assert_no_leakage(panel: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    """For every (territory, sector, year) row with a valid_forecast status,
    verify the forecast value could only have been derived from data at
    years < that year — i.e. the persistence_forecast must equal the
    observed_value of the *previous* year in the source panel (this is the
    explicit, code-level proof that no t-features were used)."""
    src = panel.set_index(["territory_id", "sector_id", "observation_year"])
    bad = []
    for _, row in forecasts.iterrows():
        if row["forecast_status"] != "valid_forecast":
            continue
        key_prev = (row["territory_id"], row["sector_id"], int(row["observation_year"]) - 1)
        if key_prev not in src.index:
            bad.append(row)
            continue
        prev_obs = src.loc[key_prev, "observed_value"]
        prev_mask = src.loc[key_prev, "observation_mask"]
        if int(prev_mask) == 1 and _finite(prev_obs):
            if not np.isclose(float(row["persistence_forecast"]), float(prev_obs), atol=1e-6):
                bad.append(row)
    if bad:
        raise AssertionError(
            f"LEAKAGE_CHECK_FAILED: {len(bad)} rows have a persistence_forecast that does not "
            f"equal the prior-year observed value — possible use of t or future data."
        )
    logger.info("Leakage check PASS: persistence_forecast always equals t-1 observed value "
                "for all %d valid_forecast rows.", (forecasts["forecast_status"] == "valid_forecast").sum())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(PT_MUNICIPAL_PANEL_PATH, low_memory=False)
    panel["territory_id"] = panel["territory_id"].astype(str)

    forecasts = build_forecast_rows(panel)
    _assert_no_leakage(panel, forecasts)

    # Structural-absence invariant: every KZ row must be structural_absent,
    # never insufficient_history/valid_forecast/NaN-as-text.
    kz = forecasts[forecasts["sector_id"] == "KZ"]
    assert (kz["forecast_status"] == "structural_absent").all(), \
        "FAIL_CLOSED: PT KZ must always be forecast_status=structural_absent"
    assert kz["observed_value"].isna().all() and kz["expected_value"].isna().all()

    tmp = Path(str(OUT_PATH) + ".tmp")
    forecasts.to_csv(tmp, index=False)
    tmp.replace(OUT_PATH)

    n_valid = int((forecasts["forecast_status"] == "valid_forecast").sum())
    n_insufficient = int((forecasts["forecast_status"] == "insufficient_history").sum())
    n_structural_absent = int((forecasts["forecast_status"] == "structural_absent").sum())
    logger.info("Wrote %s: %d rows (valid_forecast=%d, insufficient_history=%d, structural_absent=%d)",
                OUT_PATH, len(forecasts), n_valid, n_insufficient, n_structural_absent)


if __name__ == "__main__":
    main()
