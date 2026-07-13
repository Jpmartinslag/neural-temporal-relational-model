"""
HERALD -- France ZE2020 sector ranking panel.

Builds the first retrospective ZE x sector ranking dataset for the reframed
HERALD objective (HERALD_23/HERALD_24). This is not an operational
recommendation file. It is a model input/evaluation panel for exploratory
ranking: using information available through decision_year T, rank A10 sectors
for each ZE2020, then evaluate realized future sector growth.

Reads only audited France ZE2020 inputs:
  data/processed/france_ze2020/fr_ze2020_sector_panel.csv
  data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
  data/processed/france_ze2020/fr_ze2020_temporal_relation_signals.csv.gz

Output:
  data/processed/france_ze2020/fr_ze2020_sector_ranking_panel.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "data/processed/france_ze2020"
SECTOR_PANEL_PATH = OUT_DIR / "fr_ze2020_sector_panel.csv"
SECTOR_FEATURES_PATH = OUT_DIR / "fr_ze2020_sector_relational_features.csv"
RELATION_SIGNALS_PATH = OUT_DIR / "fr_ze2020_temporal_relation_signals.csv.gz"
OUT_PATH = OUT_DIR / "fr_ze2020_sector_ranking_panel.csv"

FORBIDDEN_INPUT_STEMS = (
    "dynamic_stgnn_feature_panel",
    "graph_adjacency_core_v0",
    "graph_adjacency_mobility_v0",
)

FEATURE_COLUMNS = [
    "sector_share_t",
    "sector_rank_in_ze_year_t",
    "sector_share_lag_1",
    "sector_growth_lag_1",
    "sector_growth_lag_2",
    "dominant_sector_flag_t",
    "dominant_sector_share_lag_1",
    "sector_diversity_lag_1",
    "sector_concentration_hhi_lag_1",
    "commerce_share_lag_1",
    "construction_share_lag_1",
    "national_sector_share_lag_1",
    "national_sector_growth_lag_1",
    "relation_signal_strength_mean_to_t",
    "relation_signal_strength_max_to_t",
    "relation_stability_mean_to_t",
    "relation_count_to_t",
]

MASK_COLUMNS = [
    "mask_sector_share_lag_1_available",
    "mask_sector_growth_lag_1_available",
    "mask_sector_growth_lag_2_available",
    "mask_ze_sector_distribution_lag_1_available",
    "mask_national_sector_share_lag_1_available",
    "mask_national_sector_growth_lag_1_available",
    "mask_future_growth_1y_available",
    "mask_future_growth_3y_available",
]


def _assert_no_forbidden_paths() -> None:
    paths = [SECTOR_PANEL_PATH, SECTOR_FEATURES_PATH, RELATION_SIGNALS_PATH]
    joined = "\n".join(str(p) for p in paths)
    for stem in FORBIDDEN_INPUT_STEMS:
        if stem in joined:
            raise ValueError(f"Forbidden legacy input referenced: {stem}")


def load_sector_panel(path: Path = SECTOR_PANEL_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df


def load_sector_features(path: Path = SECTOR_FEATURES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"ze2020": str})
    df["ze2020"] = df["ze2020"].str.zfill(4)
    df["year"] = df["year"].astype(int)
    return df


def load_relation_signals(path: Path = RELATION_SIGNALS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"source_node_id": str, "target_node_id": str})
    df["decision_year"] = df["decision_year"].astype(int)
    return df


def _safe_growth(future: pd.Series, current: pd.Series) -> pd.Series:
    current = current.astype(float)
    future = future.astype(float)
    return (future - current) / current.replace(0, np.nan)


def _relation_node_rows(signals: pd.DataFrame) -> pd.DataFrame:
    """Convert annual relation snapshots into incident node-year rows."""
    rows = []
    for _, row in signals.iterrows():
        for side in ("source", "target"):
            node_id = row.get(f"{side}_node_id")
            if not isinstance(node_id, str) or "_" not in node_id:
                continue
            ze2020, sector_code = node_id.split("_", 1)
            rows.append(
                {
                    "ze2020": ze2020.zfill(4),
                    "sector_code": sector_code,
                    "decision_year": int(row["decision_year"]),
                    "relation_id": str(row["relation_id"]),
                    "signal_strength": float(row["signal_strength"]),
                    "stability_score": float(row["stability_score"]),
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=[
                "ze2020",
                "sector_code",
                "decision_year",
                "relation_id",
                "signal_strength",
                "stability_score",
            ]
        )
    return pd.DataFrame(rows)


def _build_relation_features(
    base_keys: pd.DataFrame, relation_signals: pd.DataFrame
) -> pd.DataFrame:
    node_rows = _relation_node_rows(relation_signals)
    out_rows = []
    keys = base_keys[["ze2020", "sector_code", "decision_year"]].drop_duplicates()
    node_groups = {
        key: frame.sort_values("decision_year")
        for key, frame in node_rows.groupby(["ze2020", "sector_code"], sort=False)
    }
    for (ze2020, sector_code), node_keys in keys.groupby(["ze2020", "sector_code"], sort=False):
        history = node_groups.get((ze2020, sector_code))
        for decision_year in sorted(int(year) for year in node_keys["decision_year"].unique()):
            if history is None:
                latest = pd.DataFrame(columns=["signal_strength", "stability_score"])
            else:
                latest = (
                    history[history["decision_year"] <= decision_year]
                    .drop_duplicates("relation_id", keep="last")
                )
            magnitudes = latest["signal_strength"].abs()
            out_rows.append(
                {
                    "ze2020": ze2020,
                    "sector_code": sector_code,
                    "decision_year": decision_year,
                    "relation_signal_strength_mean_to_t": latest["signal_strength"].mean() if len(latest) else 0.0,
                    "relation_signal_strength_max_to_t": magnitudes.max() if len(latest) else 0.0,
                    "relation_stability_mean_to_t": latest["stability_score"].mean() if len(latest) else 0.0,
                    "relation_count_to_t": int(len(latest)),
                }
            )
    return pd.DataFrame(out_rows)


def build_sector_ranking_panel(
    sector_panel: pd.DataFrame | None = None,
    sector_features: pd.DataFrame | None = None,
    relation_signals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    _assert_no_forbidden_paths()
    if sector_panel is None:
        sector_panel = load_sector_panel()
    if sector_features is None:
        sector_features = load_sector_features()
    if relation_signals is None:
        relation_signals = load_relation_signals()

    current = sector_panel.rename(
        columns={
            "year": "decision_year",
            "sector_establishment_creations": "sector_count_t",
            "sector_share": "sector_share_t",
            "sector_rank_in_ze_year": "sector_rank_in_ze_year_t",
        }
    )[
        [
            "ze2020",
            "ze2020_label",
            "decision_year",
            "sector_code",
            "sector_label",
            "sector_count_t",
            "total_establishment_creations",
            "sector_share_t",
            "sector_rank_in_ze_year_t",
            "mask_sector_available",
        ]
    ].copy()

    future = sector_panel[
        ["ze2020", "year", "sector_code", "sector_establishment_creations", "sector_share"]
    ].copy()
    future_1y = future.rename(
        columns={
            "year": "future_1y_year",
            "sector_establishment_creations": "sector_count_t_plus_1",
            "sector_share": "sector_share_t_plus_1",
        }
    )
    future_1y["decision_year"] = future_1y["future_1y_year"] - 1

    future_3y = future.rename(
        columns={
            "year": "future_3y_year",
            "sector_establishment_creations": "sector_count_t_plus_3",
            "sector_share": "sector_share_t_plus_3",
        }
    )
    future_3y["decision_year"] = future_3y["future_3y_year"] - 3

    panel = current.merge(
        future_1y[
            [
                "ze2020",
                "sector_code",
                "decision_year",
                "sector_count_t_plus_1",
                "sector_share_t_plus_1",
            ]
        ],
        on=["ze2020", "sector_code", "decision_year"],
        how="left",
    ).merge(
        future_3y[
            [
                "ze2020",
                "sector_code",
                "decision_year",
                "sector_count_t_plus_3",
                "sector_share_t_plus_3",
            ]
        ],
        on=["ze2020", "sector_code", "decision_year"],
        how="left",
    )

    panel["future_growth_1y"] = _safe_growth(panel["sector_count_t_plus_1"], panel["sector_count_t"])
    panel["future_growth_3y"] = _safe_growth(panel["sector_count_t_plus_3"], panel["sector_count_t"])
    panel["mask_future_growth_1y_available"] = np.isfinite(panel["future_growth_1y"]).astype(int)
    panel["mask_future_growth_3y_available"] = np.isfinite(panel["future_growth_3y"]).astype(int)

    feature_rows = sector_features.copy()
    feature_rows["decision_year"] = feature_rows["year"] - 1
    panel = panel.merge(
        feature_rows.drop(columns=["year"]),
        on=["ze2020", "sector_code", "decision_year"],
        how="left",
    )
    panel["dominant_sector_flag_t"] = (panel["sector_code"] == panel["dominant_sector_lag_1"]).astype(int)

    relation_features = _build_relation_features(panel, relation_signals)
    panel = panel.merge(relation_features, on=["ze2020", "sector_code", "decision_year"], how="left")

    panel["future_rank_growth_3y_in_ze_year"] = (
        panel.groupby(["ze2020", "decision_year"])["future_growth_3y"]
        .rank(ascending=False, method="min")
    )
    panel["future_top3_growth_3y_label"] = (
        (panel["future_rank_growth_3y_in_ze_year"] <= 3)
        & (panel["mask_future_growth_3y_available"] == 1)
    ).astype(int)
    panel["ranking_feature_complete"] = (
        np.isfinite(panel[FEATURE_COLUMNS].to_numpy(dtype=float)).all(axis=1)
        & (panel[MASK_COLUMNS[:6]] == 1).all(axis=1).to_numpy()
    ).astype(int)
    panel["claim_status"] = "ranking_panel_exploratory_not_recommendation"

    col_order_raw = [
        "ze2020",
        "ze2020_label",
        "sector_code",
        "sector_label",
        "decision_year",
        "sector_count_t",
        "sector_count_t_plus_1",
        "sector_count_t_plus_3",
        "sector_share_t",
        "sector_share_t_plus_1",
        "sector_share_t_plus_3",
        "future_growth_1y",
        "future_growth_3y",
        "future_rank_growth_3y_in_ze_year",
        "future_top3_growth_3y_label",
        *FEATURE_COLUMNS,
        *MASK_COLUMNS,
        "ranking_feature_complete",
        "claim_status",
    ]
    col_order = list(dict.fromkeys(col_order_raw))
    return panel[col_order].sort_values(["ze2020", "decision_year", "sector_code"]).reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_sector_ranking_panel()
    panel.to_csv(OUT_PATH, index=False)
    print(f"Rows: {len(panel)}")
    print(f"Zones: {panel['ze2020'].nunique()}")
    print(f"Sectors: {panel['sector_code'].nunique()}")
    print(f"Decision years: {panel['decision_year'].min()}-{panel['decision_year'].max()}")
    print(f"Feature-complete rows: {int(panel['ranking_feature_complete'].sum())}")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
