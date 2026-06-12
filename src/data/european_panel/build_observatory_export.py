"""Build the causal-safe HERALD Economic Observatory exports.

Two products are generated:

* v0.1.1: aggregate enterprise-birth panel for PT/IT/AT.
* v0.2: sector-level panel for FR/NL/PT.

Economic states are descriptive labels derived from observed history. Forecasts
are causal rolling-origin baselines. No sector-to-sector graph is implemented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
AGGREGATE_PANEL_PATH = (
    REPO_ROOT
    / "data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv"
)
SECTOR_PANEL_PATH = (
    REPO_ROOT / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
)
OUTPUT_DIR_V01 = REPO_ROOT / "data/processed/herald_observatory_v01"
OUTPUT_DIR_V02 = REPO_ROOT / "data/processed/herald_observatory_v02"

SECTOR_LABELS = {
    "BE": "Industry",
    "FZ": "Construction",
    "GI": "Trade, transport and hospitality",
    "JZ": "Information and communication",
    "KZ": "Financial and insurance activities",
    "LZ": "Real estate activities",
    "MN": "Professional and administrative services",
    "OQ": "Public administration, education and health",
    "RU": "Arts and other services",
}

VALID_ECONOMIC_STATES = {
    "growth",
    "acceleration",
    "deceleration",
    "stagnation",
    "decline",
    "recovery",
    "insufficient_history",
}
VALID_DATA_EVIDENCE_TIERS = {
    "harmonized_enterprise_birth",
    "observed_national_sector_panel",
    "structural_absence",
    "missing_observation",
}
VALID_FORECAST_EVIDENCE_TIERS = {
    "exploratory_rolling_origin",
    "causal_persistence_only",
    "unavailable",
}
VALID_GRAPH_EVIDENCE_TIERS = {
    "supported_association_field",
    "structural_absence",
    "not_available",
}

G1_L2_COUNTRIES = {"PT", "FR", "NL"}
STAGNATION_THRESHOLD = 0.03
RIDGE_MIN_TRAIN = 4
RIDGE_ALPHA = 1.0


def _finite(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _economic_state(
    y_tm2: Optional[float],
    y_tm1: Optional[float],
    y_t: Optional[float],
) -> str:
    """Classify an observed series using only t, t-1 and t-2 values.

    ``deceleration`` means activity is still growing, but the positive growth
    rate is lower than in the previous period. A transition into negative
    growth is classified as ``decline``.
    """
    if not (_finite(y_t) and _finite(y_tm1)):
        return "insufficient_history"
    y_t_f = float(y_t)
    y_tm1_f = float(y_tm1)
    if y_t_f < 0 or y_tm1_f <= 0:
        return "insufficient_history"

    delta_t = (y_t_f - y_tm1_f) / y_tm1_f
    if abs(delta_t) <= STAGNATION_THRESHOLD:
        return "stagnation"

    if not _finite(y_tm2) or float(y_tm2) <= 0:
        return "growth" if delta_t > 0 else "decline"

    delta_tm1 = (y_tm1_f - float(y_tm2)) / float(y_tm2)
    if delta_t > STAGNATION_THRESHOLD:
        if delta_tm1 < -STAGNATION_THRESHOLD:
            return "recovery"
        if delta_tm1 > STAGNATION_THRESHOLD:
            return "acceleration" if delta_t > delta_tm1 else "deceleration"
        return "growth"
    return "decline"


def _rolling_ridge_forecasts(
    series: pd.Series,
    min_train: int = RIDGE_MIN_TRAIN,
    alpha: float = RIDGE_ALPHA,
) -> pd.Series:
    """Return causal rolling-origin AR(1) Ridge forecasts."""
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
        predictions[index] = max(
            0.0, float(model.predict([[values[index - 1]]])[0])
        )
    return pd.Series(predictions, index=series.index)


def _series_rows(
    group: pd.DataFrame,
    *,
    value_col: str,
    observed_mask_col: str,
    structural_mask_col: str,
    base_metadata: dict[str, object],
) -> list[dict[str, object]]:
    group = group.sort_values("observation_year").reset_index(drop=True).copy()
    structural = group[structural_mask_col].fillna(0).astype(int).eq(1)
    observed = group[observed_mask_col].fillna(0).astype(int).eq(1) & structural
    values = pd.to_numeric(group[value_col], errors="coerce").where(observed)
    ridge = _rolling_ridge_forecasts(values)
    rows: list[dict[str, object]] = []

    for index, source in group.iterrows():
        is_structural = bool(structural.iloc[index])
        is_observed = bool(observed.iloc[index] and _finite(values.iloc[index]))
        current = float(values.iloc[index]) if is_observed else np.nan
        previous = values.iloc[index - 1] if index >= 1 else np.nan
        previous2 = values.iloc[index - 2] if index >= 2 else np.nan

        velocity = np.nan
        acceleration = np.nan
        if is_observed and _finite(previous) and float(previous) > 0:
            velocity = (current - float(previous)) / float(previous)
        if (
            _finite(velocity)
            and _finite(previous)
            and _finite(previous2)
            and float(previous2) > 0
        ):
            prior_velocity = (float(previous) - float(previous2)) / float(previous2)
            acceleration = float(velocity) - prior_velocity

        persistence = (
            float(previous)
            if is_structural and _finite(previous)
            else np.nan
        )
        ridge_value = (
            float(ridge.iloc[index])
            if is_structural and _finite(ridge.iloc[index])
            else np.nan
        )

        if not is_structural:
            data_tier = "structural_absence"
            forecast_tier = "unavailable"
            graph_tier = "structural_absence"
            quality_flags = "STRUCTURAL_ABSENCE"
        elif not is_observed:
            data_tier = "missing_observation"
            forecast_tier = "unavailable"
            graph_tier = "not_available"
            quality_flags = "MISSING_OBSERVATION"
        else:
            data_tier = str(base_metadata["observed_data_tier"])
            if _finite(ridge_value):
                forecast_tier = "exploratory_rolling_origin"
            elif _finite(persistence):
                forecast_tier = "causal_persistence_only"
            else:
                forecast_tier = "unavailable"
            graph_tier = (
                "supported_association_field"
                if bool(base_metadata["graph_eligible"])
                else "not_available"
            )
            quality_flags = "OK"

        rows.append(
            {
                **base_metadata,
                "observation_year": int(source["observation_year"]),
                "observed_value": current,
                "lag1_value": persistence,
                "persistence_forecast": persistence,
                "ridge_forecast": ridge_value,
                "forecast_lower": np.nan,
                "forecast_upper": np.nan,
                "forecast_method": (
                    "ridge_ar1"
                    if _finite(ridge_value)
                    else "persistence"
                    if _finite(persistence)
                    else "unavailable"
                ),
                "forecast_status": (
                    "POINT_ONLY"
                    if _finite(ridge_value) or _finite(persistence)
                    else "UNAVAILABLE"
                ),
                "economic_state": _economic_state(previous2, previous, current),
                "velocity": round(float(velocity), 6) if _finite(velocity) else np.nan,
                "acceleration": (
                    round(float(acceleration), 6)
                    if _finite(acceleration)
                    else np.nan
                ),
                "data_evidence_tier": data_tier,
                "forecast_evidence_tier": forecast_tier,
                "graph_evidence_tier": graph_tier,
                "territorial_graph_available": int(
                    graph_tier == "supported_association_field"
                ),
                "sector_graph_available": 0,
                "structural_mask": int(is_structural),
                "observation_mask": int(is_observed),
                "data_quality_flags": quality_flags,
            }
        )
    return rows


def _validate_export(export: pd.DataFrame, key: list[str]) -> None:
    if export.duplicated(key).any():
        raise ValueError(f"Duplicate Observatory keys: {key}")
    if not set(export["economic_state"]).issubset(VALID_ECONOMIC_STATES):
        raise ValueError("Invalid economic state")
    if not set(export["data_evidence_tier"]).issubset(VALID_DATA_EVIDENCE_TIERS):
        raise ValueError("Invalid data evidence tier")
    if not set(export["forecast_evidence_tier"]).issubset(
        VALID_FORECAST_EVIDENCE_TIERS
    ):
        raise ValueError("Invalid forecast evidence tier")
    if not set(export["graph_evidence_tier"]).issubset(
        VALID_GRAPH_EVIDENCE_TIERS
    ):
        raise ValueError("Invalid graph evidence tier")
    if export.loc[export["structural_mask"].eq(0), "observed_value"].notna().any():
        raise ValueError("Structural absence encoded as an observed value")
    if not export["sector_graph_available"].eq(0).all():
        raise ValueError("Sector graph is not implemented")
    if export[["forecast_lower", "forecast_upper"]].notna().any().any():
        raise ValueError("Forecast intervals are not implemented")


def _write_outputs(
    export: pd.DataFrame,
    output_dir: Path,
    *,
    stem: str,
    version: str,
    source_panel: Path,
    decision: str,
    limitations: list[str],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    export = export.sort_values(
        ["country", "territory_id", "sector_id", "observation_year"]
    ).reset_index(drop=True)
    csv_path = output_dir / f"{stem}_panel.csv"
    export.to_csv(csv_path, index=False)
    checksum = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    manifest = {
        "version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "source_panel": str(source_panel.relative_to(REPO_ROOT)),
        "rows": int(len(export)),
        "countries": sorted(export["country"].unique().tolist()),
        "territories": int(
            export[["country", "territory_id"]].drop_duplicates().shape[0]
        ),
        "years_by_country": {
            country: [
                int(group["observation_year"].min()),
                int(group["observation_year"].max()),
            ]
            for country, group in export.groupby("country")
        },
        "sector_ids": sorted(export["sector_id"].unique().tolist()),
        "economic_states_distribution": export["economic_state"].value_counts().to_dict(),
        "data_evidence_distribution": export["data_evidence_tier"].value_counts().to_dict(),
        "forecast_evidence_distribution": (
            export["forecast_evidence_tier"].value_counts().to_dict()
        ),
        "graph_evidence_distribution": (
            export["graph_evidence_tier"].value_counts().to_dict()
        ),
        "forecast_coverage": {
            "persistence": int(export["persistence_forecast"].notna().sum()),
            "ridge": int(export["ridge_forecast"].notna().sum()),
            "intervals": 0,
        },
        "sha256": checksum,
        "causal_safety": {
            "same_year_feature_used": False,
            "ridge_features": ["lag1_value"],
            "rolling_origin": True,
            "state_uses_at_most_t_tminus1_tminus2": True,
            "leakage_free": True,
        },
        "limitations": limitations,
    }
    (output_dir / f"{stem}_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )

    summary = {
        "version": version,
        "total_rows": int(len(export)),
        "countries": {
            country: {
                "rows": int(len(group)),
                "territories": int(group["territory_id"].nunique()),
                "sectors": int(group["sector_id"].nunique()),
                "year_min": int(group["observation_year"].min()),
                "year_max": int(group["observation_year"].max()),
                "observed_rows": int(group["observation_mask"].sum()),
                "structural_absence_rows": int(group["structural_mask"].eq(0).sum()),
                "economic_state_dist": group["economic_state"].value_counts().to_dict(),
            }
            for country, group in export.groupby("country")
        },
    }
    (output_dir / f"{stem}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    logger.info("Wrote %s (%d rows)", csv_path, len(export))
    return csv_path


def build_aggregate_export(
    panel_path: Path = AGGREGATE_PANEL_PATH,
    output_dir: Path = OUTPUT_DIR_V01,
) -> Path:
    """Build corrected aggregate Observatory v0.1.1."""
    panel = pd.read_csv(panel_path, dtype={"region_id": str})
    required = {
        "country",
        "region_id",
        "region_name",
        "meta_nuts3_code",
        "year",
        "target_births",
        "mask_target",
    }
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Aggregate panel missing columns: {sorted(missing)}")
    panel = panel.rename(columns={"year": "observation_year"})

    rows: list[dict[str, object]] = []
    for (country, region_id), group in panel.groupby(["country", "region_id"]):
        first = group.iloc[0]
        rows.extend(
            _series_rows(
                group,
                value_col="target_births",
                observed_mask_col="mask_target",
                structural_mask_col="mask_target",
                base_metadata={
                    "country": country,
                    "territory_id": str(region_id),
                    "meta_nuts3_code": str(first["meta_nuts3_code"]),
                    "territory_name": str(first["region_name"]),
                    "region_system": str(first.get("meta_region_system", "NUTS3")),
                    "sector_id": "AGGREGATE",
                    "sector_label": "All business sectors",
                    "target_concept": str(
                        first.get("flag_target_concept", "enterprise_birth")
                    ),
                    "source_label": str(first.get("meta_source_label", "")),
                    "observed_data_tier": "harmonized_enterprise_birth",
                    "graph_eligible": False,
                },
            )
        )
    export = pd.DataFrame(rows).drop(columns=["observed_data_tier", "graph_eligible"])
    key = ["country", "territory_id", "observation_year", "sector_id"]
    _validate_export(export, key)
    return _write_outputs(
        export,
        Path(output_dir),
        stem="herald_observatory_v011",
        version="0.1.1",
        source_panel=Path(panel_path),
        decision="DEC-030/DEC-031",
        limitations=[
            "Aggregate enterprise_birth only; no sector-level interpretation.",
            "Intervals are unavailable.",
            "Ridge AR(1) is exploratory and not equivalent to Phase 4N.",
            "Territorial graph is not attached to aggregate rows.",
            "France is excluded while its historical headline remains PENDING_REAUDIT.",
        ],
    )


def build_sector_export(
    panel_path: Path = SECTOR_PANEL_PATH,
    output_dir: Path = OUTPUT_DIR_V02,
) -> Path:
    """Build sector-level Observatory v0.2 for FR/NL/PT."""
    panel = pd.read_csv(panel_path, dtype={"region_id": str})
    required = {
        "country",
        "region_id",
        "region_name",
        "observation_year",
        "sector_a10",
        "sector_births",
        "mask_sector_births",
        "mask_sector_supported",
    }
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Sector panel missing columns: {sorted(missing)}")
    panel["_structural_mask"] = (
        ~(panel["country"].eq("PT") & panel["sector_a10"].eq("KZ"))
    ).astype(int)
    panel["_observation_mask"] = (
        panel["mask_sector_births"].fillna(0).astype(int).eq(1)
        & panel["mask_sector_supported"].fillna(0).astype(int).eq(1)
        & panel["_structural_mask"].eq(1)
    ).astype(int)

    rows: list[dict[str, object]] = []
    for (country, region_id, sector), group in panel.groupby(
        ["country", "region_id", "sector_a10"]
    ):
        first = group.iloc[0]
        graph_eligible = country in G1_L2_COUNTRIES
        rows.extend(
            _series_rows(
                group,
                value_col="sector_births",
                observed_mask_col="_observation_mask",
                structural_mask_col="_structural_mask",
                base_metadata={
                    "country": country,
                    "territory_id": str(region_id),
                    "meta_nuts3_code": str(
                        first.get("meta_nuts3_code", first["region_id"])
                    ),
                    "territory_name": str(first["region_name"]),
                    "region_system": str(
                        first.get("meta_region_system", first.get("region_level", ""))
                    ),
                    "sector_id": str(sector),
                    "sector_label": SECTOR_LABELS.get(str(sector), str(sector)),
                    "target_concept": str(first.get("flag_target_concept", "")),
                    "source_label": str(
                        first.get("meta_source_label", first.get("source_label", ""))
                    ),
                    "observed_data_tier": "observed_national_sector_panel",
                    "graph_eligible": graph_eligible,
                },
            )
        )
    export = pd.DataFrame(rows).drop(columns=["observed_data_tier", "graph_eligible"])
    key = ["country", "territory_id", "observation_year", "sector_id"]
    _validate_export(export, key)
    return _write_outputs(
        export,
        Path(output_dir),
        stem="herald_observatory_v02",
        version="0.2",
        source_panel=Path(panel_path),
        decision="DEC-030/DEC-031",
        limitations=[
            "Targets are heterogeneous national sector concepts; no country pooling.",
            "Ridge AR(1) forecasts are exploratory point baselines.",
            "Intervals are unavailable.",
            "G1-L2 availability means supported association field, not prediction or causality.",
            "Sector-to-sector graph is not implemented.",
            "PT KZ remains structural absence; unsupported NL OQ years remain missing observations, never economic zeros.",
        ],
    )


def build_export(
    panel_path: Path = AGGREGATE_PANEL_PATH,
    output_dir: Path = OUTPUT_DIR_V01,
) -> Path:
    """Backward-compatible alias for the corrected aggregate export."""
    return build_aggregate_export(panel_path=panel_path, output_dir=output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["all", "aggregate", "sector"], default="all"
    )
    args = parser.parse_args()
    if args.mode in {"all", "aggregate"}:
        build_aggregate_export()
    if args.mode in {"all", "sector"}:
        build_sector_export()


if __name__ == "__main__":
    main()
