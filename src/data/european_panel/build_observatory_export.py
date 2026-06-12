"""
HERALD Economic Observatory v0.1 — Unified causal-safe data export.

Produces per-territory × per-year rows with observed enterprise births,
persistence and Ridge point forecasts (rolling-origin), economic state labels,
velocity/acceleration signals, and evidence tier metadata.

Output directory: data/processed/herald_observatory_v01/
  - herald_observatory_v01_panel.csv
  - herald_observatory_v01_manifest.json
  - herald_observatory_v01_summary.json

Causal-safety guarantee:
  Forecast for year t uses ONLY data available through t-1 (lagged features,
  no growth_1y leakage). Rolling-origin Ridge is trained on all t' < t.
  Uncertainty intervals are NOT yet implemented (forecast_lower/upper = NaN).
  Sector-level data is NOT included in v0.1 (sector_id = "AGGREGATE").
  Sector graph is NOT implemented (sector_graph_available = 0 always).

Data contract: reports/HERALD_OBSERVATORY_V01_DATA_CONTRACT.md
Decision: DEC-030 (Observatory v0.1 authorized)
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PANEL_PATH = (
    REPO_ROOT
    / "data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv"
)
OUTPUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v01"

VALID_ECONOMIC_STATES = {
    "growth",
    "acceleration",
    "deceleration",
    "stagnation",
    "decline",
    "recovery",
    "insufficient_history",
}

# Countries where G1-L2 co-growth field has been validated (DEC-019/020)
G1_L2_COUNTRIES = {"PT", "FR", "NL"}

# Minimum absolute fractional change to declare non-stagnation
STAGNATION_THRESHOLD = 0.03


def _economic_state(y_tm2: Optional[float], y_tm1: Optional[float], y_t: float) -> str:
    """Classify the economic state for territory-year based on last 3 observed values."""
    if y_tm1 is None or np.isnan(y_tm1):
        return "insufficient_history"
    if y_t <= 0 or y_tm1 <= 0:
        return "insufficient_history"

    delta_t = (y_t - y_tm1) / y_tm1

    if y_tm2 is None or np.isnan(y_tm2) or y_tm2 <= 0:
        if abs(delta_t) <= STAGNATION_THRESHOLD:
            return "stagnation"
        return "growth" if delta_t > 0 else "decline"

    delta_tm1 = (y_tm1 - y_tm2) / y_tm2

    if abs(delta_t) <= STAGNATION_THRESHOLD:
        return "stagnation"

    if delta_t > 0:
        if delta_tm1 < -STAGNATION_THRESHOLD:
            return "recovery"
        if delta_t > delta_tm1:
            return "acceleration"
        return "growth"
    else:
        if delta_tm1 > STAGNATION_THRESHOLD:
            return "deceleration"
        return "decline"


def _rolling_ridge_forecasts(
    series: pd.Series, min_train: int = 4, alpha: float = 1.0
) -> pd.Series:
    """
    Rolling-origin Ridge forecast for a single territory.
    Feature: lag1 of the observed value.
    Returns a Series aligned with the input index with NaN where unavailable.
    Causal-safe: forecast at index i uses only values at indices < i.
    """
    from sklearn.linear_model import Ridge

    values = series.values.astype(float)
    n = len(values)
    preds = np.full(n, np.nan)

    for i in range(min_train, n):
        X = values[: i - 1].reshape(-1, 1)
        y = values[1:i]
        if np.any(np.isnan(X)) or np.any(np.isnan(y)):
            continue
        model = Ridge(alpha=alpha)
        model.fit(X, y)
        feat = np.array([[values[i - 1]]])
        if not np.isnan(feat).any():
            preds[i] = model.predict(feat)[0]

    return pd.Series(preds, index=series.index)


def _evidence_tier(row: pd.Series) -> str:
    """Assign evidence tier based on panel metadata."""
    if row.get("mask_target", 0) != 1.0:
        return "not_available"
    if row.get("flag_forecast_safe", 0) != 1:
        return "not_available"
    country = row.get("country", "")
    if country in {"PT", "IT", "AT"}:
        return "validated_loco"
    return "not_available"


def build_export(panel_path: Path = PANEL_PATH, output_dir: Path = OUTPUT_DIR) -> Path:
    """
    Build Observatory v0.1 export from the harmonized PT/IT/AT panel.

    Returns path to the output CSV.
    """
    panel_path = Path(panel_path)
    output_dir = Path(output_dir)

    logger.info("Loading panel: %s", panel_path)
    df = pd.read_csv(panel_path)

    required_cols = {
        "country", "region_id", "region_name", "meta_nuts3_code",
        "year", "target_births", "lag1_births", "lag2_births",
        "mask_target", "flag_forecast_safe",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Panel missing required columns: {missing}")

    df = df.sort_values(["region_id", "year"]).reset_index(drop=True)

    rows = []
    for region_id, grp in df.groupby("region_id"):
        grp = grp.sort_values("year").reset_index(drop=True)
        country = grp["country"].iloc[0]
        region_name = grp["region_name"].iloc[0]
        nuts3 = grp["meta_nuts3_code"].iloc[0]

        observed = grp.set_index("year")["target_births"]
        lag1 = grp.set_index("year")["lag1_births"]

        ridge_raw = _rolling_ridge_forecasts(observed, min_train=4)
        ridge_by_year = dict(zip(grp["year"], ridge_raw.values))

        for _, row in grp.iterrows():
            yr = row["year"]
            obs = row["target_births"]
            y_tm1 = row.get("lag1_births")
            y_tm2 = row.get("lag2_births")

            y_tm1_val = float(y_tm1) if pd.notna(y_tm1) else None
            y_tm2_val = float(y_tm2) if pd.notna(y_tm2) else None

            persistence = float(y_tm1) if pd.notna(y_tm1) else np.nan
            ridge = float(ridge_by_year.get(yr, np.nan))

            velocity = (
                (obs - y_tm1_val) / y_tm1_val
                if (y_tm1_val is not None and y_tm1_val > 0)
                else np.nan
            )
            if y_tm1_val is not None and y_tm2_val is not None and y_tm2_val > 0:
                vel_prev = (y_tm1_val - y_tm2_val) / y_tm2_val
                acceleration = velocity - vel_prev if pd.notna(velocity) else np.nan
            else:
                acceleration = np.nan

            state = _economic_state(y_tm2_val, y_tm1_val, obs)

            rows.append(
                {
                    "country": country,
                    "territory_id": region_id,
                    "meta_nuts3_code": nuts3,
                    "territory_name": region_name,
                    "observation_year": yr,
                    "sector_id": "AGGREGATE",
                    "observed_value": obs,
                    "persistence_forecast": persistence,
                    "ridge_forecast": ridge,
                    "forecast_lower": np.nan,
                    "forecast_upper": np.nan,
                    "economic_state": state,
                    "velocity": round(velocity, 6) if pd.notna(velocity) else np.nan,
                    "acceleration": (
                        round(acceleration, 6) if pd.notna(acceleration) else np.nan
                    ),
                    "g1_l2_available": int(country in G1_L2_COUNTRIES),
                    "sector_graph_available": 0,
                    "evidence_tier": _evidence_tier(row),
                    "data_source": row.get("meta_source_label", ""),
                }
            )

    export = pd.DataFrame(rows)

    assert set(export["economic_state"]).issubset(
        VALID_ECONOMIC_STATES
    ), "Invalid economic states produced"
    assert (export["sector_graph_available"] == 0).all(), "sector_graph_available must be 0"
    assert (export["forecast_lower"].isna() & export["forecast_upper"].isna()).all(), (
        "Uncertainty intervals must be NaN in v0.1"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "herald_observatory_v01_panel.csv"
    export.to_csv(csv_path, index=False)
    logger.info("Wrote %d rows to %s", len(export), csv_path)

    sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()[:20]
    manifest = {
        "version": "0.1",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "decision": "DEC-030",
        "source_panel": str(PANEL_PATH.relative_to(REPO_ROOT)),
        "rows": len(export),
        "countries": sorted(export["country"].unique().tolist()),
        "territories": int(export["territory_id"].nunique()),
        "years": sorted(export["observation_year"].unique().tolist()),
        "sector_ids": sorted(export["sector_id"].unique().tolist()),
        "economic_states_distribution": (
            export["economic_state"].value_counts().to_dict()
        ),
        "evidence_tier_distribution": (
            export["evidence_tier"].value_counts().to_dict()
        ),
        "forecast_coverage": {
            "persistence": int(export["persistence_forecast"].notna().sum()),
            "ridge": int(export["ridge_forecast"].notna().sum()),
            "intervals": 0,
        },
        "sha256_prefix": sha256,
        "causal_safety": {
            "growth_1y_used": False,
            "features": ["lag1_births"],
            "rolling_origin": True,
            "leakage_free": True,
        },
        "limitations": [
            "Sector-level data not included (v0.1 aggregate only, sector_id='AGGREGATE').",
            "Uncertainty intervals not yet implemented (forecast_lower/upper = NaN).",
            "France not included (WMAPE 0.0204 PENDING_REAUDIT; separate data source).",
            "Ridge trained on lag1 feature only; not equivalent to Phase 4N causal config.",
            "sector_graph_available=0: sector->sector graph not yet implemented.",
            "G1-L2 flag marks countries with validated co-growth field (PT=1, IT/AT=0).",
        ],
    }
    manifest_path = output_dir / "herald_observatory_v01_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Wrote manifest to %s", manifest_path)

    validated = export[export["evidence_tier"] == "validated_loco"]
    summary = {
        "version": "0.1",
        "total_rows": len(export),
        "validated_rows": len(validated),
        "countries": {
            c: {
                "territories": int(
                    export[export["country"] == c]["territory_id"].nunique()
                ),
                "years": sorted(
                    export[export["country"] == c]["observation_year"]
                    .unique()
                    .tolist()
                ),
                "economic_state_dist": (
                    export[export["country"] == c]["economic_state"]
                    .value_counts()
                    .to_dict()
                ),
            }
            for c in sorted(export["country"].unique())
        },
        "persistence_wmape_by_country": {},
    }
    for c, grp_c in export[export["persistence_forecast"].notna()].groupby("country"):
        wmape = float(
            (
                (grp_c["observed_value"] - grp_c["persistence_forecast"]).abs()
                / grp_c["observed_value"].clip(lower=1)
            ).mean()
        )
        summary["persistence_wmape_by_country"][c] = round(wmape, 6)

    summary_path = output_dir / "herald_observatory_v01_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    logger.info("Wrote summary to %s", summary_path)

    return csv_path


if __name__ == "__main__":
    out = build_export()
    print(f"Observatory v0.1 export complete: {out}")
