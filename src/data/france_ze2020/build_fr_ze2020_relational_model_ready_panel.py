"""
HERALD -- France ZE2020 relational model-ready panel (MVP2, Category A only).

See reports/canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md section
"MVP2 implementation" for the full rationale. This is a planning/smoke
artifact: it adds a small set of ZE-to-ZE relational features on top of the
existing causal model-ready panel, to test whether simple relational
aggregates carry any predictive signal BEFORE any graph neural network is
considered (Charter-aligned staged approach, not a final model).

Input (read-only):
  data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv
  -- the ONLY input. Never dynamic_stgnn_feature_panel_v1.csv (or siblings),
  never graph_adjacency_core_v0.csv / graph_adjacency_mobility_v0.csv (their
  generator is missing from the current tree -- HERALD_16 section 4.1 --
  so they are not used here as a trusted source of ZE-to-ZE relations).

Output:
  data/processed/france_ze2020/fr_ze2020_relational_model_ready_panel.csv

Method (Category A -- trajectory similarity, no legacy matrix):
  For each evaluation year t, compute a ZE-to-ZE Pearson correlation matrix
  over each zone's growth_1y_safe history restricted to years < t only (an
  expanding window -- never years >= t). For each zone, the top-K
  positively-correlated zones (excluding itself) become its "similar ZEs".
  The relational features then read those neighbors' OWN lag_1/
  growth_1y_safe values at row year=t -- both of which are themselves
  already shifted to t-1 by the model-ready panel, so no neighbor's
  current-year (t) observed_value is ever read, directly or indirectly.

  Sector composition features (Category C) and a from-scratch geographic
  adjacency (Category A via geometry, Category C otherwise) are explicitly
  NOT implemented in this pass -- see the plan document's "features
  recusadas" section for why.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MODEL_READY_PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_model_ready_panel.csv"
OUT_DIR = ROOT / "data/processed/france_ze2020"
OUT_PATH = OUT_DIR / "fr_ze2020_relational_model_ready_panel.csv"

SIMILARITY_FEATURE = "growth_1y_safe"
TOP_K = 5
MIN_HISTORY_YEARS = 3

BASE_COLUMNS = [
    "ze2020",
    "ze2020_label",
    "year",
    "observed_value",
    "target_variable",
    "lag_1",
    "lag_2",
    "lag_3",
    "growth_1y_safe",
    "growth_2y_safe",
    "mask_observed_available",
    "mask_lag_1_available",
    "mask_lag_2_available",
    "mask_lag_3_available",
    "node_id",
]

RELATIONAL_COLUMNS = [
    "similar_ze_lag_1_mean",
    "similar_ze_lag_1_weighted_mean",
    "similar_ze_growth_1y_safe_mean",
    "similar_ze_count",
    "relational_feature_available",
]


def load_model_ready_panel(path: Path = MODEL_READY_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df


def similarity_matrix_for_year(
    panel: pd.DataFrame, eval_year: int, min_history_years: int = MIN_HISTORY_YEARS
) -> pd.DataFrame | None:
    """Pairwise Pearson correlation between zones' SIMILARITY_FEATURE
    histories, using strictly years < eval_year. Returns None if eval_year
    is the panel's first year (no history exists yet)."""
    history = panel[panel["year"] < eval_year]
    if history.empty:
        return None
    pivot = history.pivot(index="ze2020", columns="year", values=SIMILARITY_FEATURE)
    return pivot.T.corr(min_periods=min_history_years)


def neighbor_features_for_year(panel: pd.DataFrame, eval_year: int, top_k: int = TOP_K) -> pd.DataFrame:
    """Builds the relational columns for every ze2020 at eval_year. Reads
    only neighbors' lag_1/growth_1y_safe at row year=eval_year (already
    shifted to t-1 by the model-ready panel) -- never any zone's
    observed_value for eval_year itself."""
    current = panel[panel["year"] == eval_year].set_index("ze2020")
    corr = similarity_matrix_for_year(panel, eval_year)

    rows = []
    for zone in current.index:
        neighbors: list[str] = []
        weights: list[float] = []
        candidates = pd.Series(dtype=float)
        if corr is not None and zone in corr.index:
            candidates = corr.loc[zone].drop(labels=[zone], errors="ignore").dropna()
            candidates = candidates[candidates > 0].sort_values(ascending=False).head(top_k)
            neighbors = candidates.index.tolist()
            weights = candidates.to_numpy(dtype=float).tolist()

        neighbor_rows = current.reindex(neighbors)
        valid = neighbor_rows.dropna(subset=["lag_1", "growth_1y_safe"])
        valid_weights = candidates.reindex(valid.index).to_numpy(dtype=float)
        count = len(valid)

        if count == 0:
            rows.append(
                {
                    "ze2020": zone,
                    "year": eval_year,
                    "similar_ze_lag_1_mean": np.nan,
                    "similar_ze_lag_1_weighted_mean": np.nan,
                    "similar_ze_growth_1y_safe_mean": np.nan,
                    "similar_ze_count": 0,
                    "relational_feature_available": 0,
                }
            )
            continue

        lag1_vals = valid["lag_1"].to_numpy(dtype=float)
        growth_vals = valid["growth_1y_safe"].to_numpy(dtype=float)
        w_norm = (
            valid_weights / valid_weights.sum()
            if valid_weights.sum() > 0
            else np.full(count, 1.0 / count)
        )

        rows.append(
            {
                "ze2020": zone,
                "year": eval_year,
                "similar_ze_lag_1_mean": float(lag1_vals.mean()),
                "similar_ze_lag_1_weighted_mean": float((lag1_vals * w_norm).sum()),
                "similar_ze_growth_1y_safe_mean": float(growth_vals.mean()),
                "similar_ze_count": count,
                "relational_feature_available": 1,
            }
        )
    return pd.DataFrame(rows)


def build_relational_model_ready_panel(panel: pd.DataFrame | None = None) -> pd.DataFrame:
    if panel is None:
        panel = load_model_ready_panel()

    years = sorted(panel["year"].unique())
    relational = pd.concat(
        [neighbor_features_for_year(panel, year) for year in years], ignore_index=True
    )

    merged = panel.merge(relational, on=["ze2020", "year"], how="left")
    merged["similar_ze_count"] = merged["similar_ze_count"].fillna(0).astype(int)
    merged["relational_feature_available"] = (
        merged["relational_feature_available"].fillna(0).astype(int)
    )

    col_order = BASE_COLUMNS + RELATIONAL_COLUMNS
    merged = merged[col_order].sort_values(["ze2020", "year"]).reset_index(drop=True)
    return merged


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_relational_model_ready_panel()
    panel.to_csv(OUT_PATH, index=False)

    n_available = int(panel["relational_feature_available"].sum())
    print(f"Zones: {panel['ze2020'].nunique()}")
    print(f"Relational feature available: {n_available}/{len(panel)} rows")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
