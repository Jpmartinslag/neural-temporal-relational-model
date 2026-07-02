"""
HERALD -- France ZE2020 dynamic edge variant builder.

Builds the first HERALD_26 edge-learning variant without overwriting HERALD_25
inputs. This is edge construction only: no model training, no causal claim, and
no automatic recommendation.

Input:
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz

Output:
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful.csv.gz
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.france_ze2020.build_fr_ze2020_dynamic_graph_inputs import (
    EXPANDING_EDGES_OUT_PATH,
    OUT_DIR,
)

PRUNED_STABLE_EDGES_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz"
STATEFUL_EDGES_OUT_PATH = OUT_DIR / "fr_ze2020_dynamic_graph_edges_stateful.csv.gz"

DEFAULT_TOP_K_PER_NODE = 5
DEFAULT_MIN_STABILITY = 0.25
DEFAULT_MIN_ABS_SIGNAL = 0.30
DEFAULT_MAX_EDGE_AGE = 5
CLAIM_STATUS = "dynamic_graph_edge_variant_exploratory_not_causal"
EDGE_VARIANT = "pruned_stable"
STATEFUL_EDGE_VARIANT = "stateful"
STATEFUL_EDGE_MEMORY_MODE = "stateful_decay"
STATE_MULTIPLIERS = {
    "persistent_relation": 1.00,
    "reappearing_relation": 0.75,
    "new_relation": 0.50,
    "decaying_relation": 0.35,
    "volatile_relation": 0.15,
}
STATEFUL_RECENT_WINDOW = 3


def load_expanding_edges(path: Path = EXPANDING_EDGES_OUT_PATH) -> pd.DataFrame:
    edges = pd.read_csv(path)
    edges["decision_year"] = edges["decision_year"].astype(int)
    edges["source_relation_year_end"] = edges["source_relation_year_end"].astype(int)
    edges["edge_age"] = edges["edge_age"].astype(int)
    return edges


def build_pruned_stable_edges(
    edges: pd.DataFrame | None = None,
    *,
    top_k_per_node: int = DEFAULT_TOP_K_PER_NODE,
    min_stability: float = DEFAULT_MIN_STABILITY,
    min_abs_signal: float = DEFAULT_MIN_ABS_SIGNAL,
    max_edge_age: int = DEFAULT_MAX_EDGE_AGE,
) -> pd.DataFrame:
    """Keep stable, finite, high-priority incoming edges per target node-year."""
    if top_k_per_node < 1:
        raise ValueError("top_k_per_node must be >= 1")
    if not 0 <= min_stability <= 1:
        raise ValueError("min_stability must be between 0 and 1")
    if min_abs_signal < 0:
        raise ValueError("min_abs_signal must be non-negative")
    if max_edge_age < 0:
        raise ValueError("max_edge_age must be non-negative")

    if edges is None:
        edges = load_expanding_edges()

    required = {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "claim_status",
    }
    missing = required.difference(edges.columns)
    if missing:
        raise ValueError(f"Expanding edge table missing required columns: {sorted(missing)}")

    out = edges.copy()
    numeric_cols = ["edge_weight", "signal_strength", "stability_score", "edge_age"]
    finite = np.isfinite(out[numeric_cols].to_numpy(dtype=float)).all(axis=1)
    out = out[finite].copy()
    out = out[out["stability_score"].astype(float) >= min_stability]
    out = out[out["signal_strength"].astype(float).abs() >= min_abs_signal]
    out = out[out["edge_age"].astype(int) <= max_edge_age]
    out = out[out["source_node_id"] != out["target_node_id"]].copy()

    if out.empty:
        return _empty_pruned_schema(edges)

    out["edge_priority"] = (
        out["edge_weight"].astype(float).abs()
        * out["stability_score"].astype(float)
        / (1.0 + out["edge_age"].astype(float))
    )
    out = out.sort_values(
        [
            "decision_year",
            "target_node_id",
            "edge_priority",
            "stability_score",
            "source_node_id",
        ],
        ascending=[True, True, False, False, True],
    )
    out["rank_within_target_year"] = (
        out.groupby(["decision_year", "target_node_id"]).cumcount() + 1
    )
    out = out[out["rank_within_target_year"] <= top_k_per_node].copy()

    out["edge_variant"] = EDGE_VARIANT
    out["edge_id"] = "pruned_stable__" + out["edge_id"].astype(str)
    out["claim_status"] = CLAIM_STATUS
    out["prune_top_k_per_node"] = int(top_k_per_node)
    out["prune_min_stability"] = float(min_stability)
    out["prune_min_abs_signal"] = float(min_abs_signal)
    out["prune_max_edge_age"] = int(max_edge_age)

    columns = [
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "edge_variant",
        "edge_priority",
        "rank_within_target_year",
        "prune_top_k_per_node",
        "prune_min_stability",
        "prune_min_abs_signal",
        "prune_max_edge_age",
        "claim_status",
    ]
    return out[columns].sort_values(
        ["decision_year", "target_node_id", "rank_within_target_year", "edge_type", "source_node_id"]
    ).reset_index(drop=True)


def build_stateful_edges(edges: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate edge memory into one stateful relation per node pair, type and year."""
    if edges is None:
        edges = load_expanding_edges()

    required = {
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
    }
    missing = required.difference(edges.columns)
    if missing:
        raise ValueError(f"Expanding edge table missing required columns: {sorted(missing)}")

    out = edges.copy()
    numeric_cols = ["edge_weight", "signal_strength", "stability_score", "edge_age"]
    finite = np.isfinite(out[numeric_cols].to_numpy(dtype=float)).all(axis=1)
    out = out[finite].copy()
    out = out[out["source_node_id"] != out["target_node_id"]].copy()
    if out.empty:
        return _empty_stateful_schema()

    key_cols = ["source_node_id", "target_node_id", "edge_type"]
    out = out.sort_values(
        [*key_cols, "decision_year", "source_relation_year_end", "edge_id"]
    ).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for (*key, decision_year), group in out.groupby([*key_cols, "decision_year"], sort=True):
        latest_idx = group["source_relation_year_end"].astype(int).idxmax()
        latest = group.loc[latest_idx]
        observed_years = sorted(set(int(y) for y in group["source_relation_year_end"]))
        latest_year = int(observed_years[-1])
        previous_year = int(observed_years[-2]) if len(observed_years) >= 2 else None
        edge_age = int(decision_year) - latest_year
        recent_start = int(decision_year) - STATEFUL_RECENT_WINDOW + 1
        recent_observation_count = sum(y >= recent_start for y in observed_years)
        state = _classify_edge_state(
            decision_year=int(decision_year),
            latest_year=latest_year,
            previous_year=previous_year,
            recent_observation_count=recent_observation_count,
            signal_strength=float(latest["signal_strength"]),
            stability_score=float(latest["stability_score"]),
        )
        multiplier = STATE_MULTIPLIERS[state]
        signal_strength = float(latest["signal_strength"])
        stability_score = float(latest["stability_score"])
        stateful_weight = signal_strength * stability_score * multiplier / (1.0 + edge_age)
        source_node_id, target_node_id, edge_type = key
        rows.append(
            {
                "edge_id": (
                    f"stateful__{int(decision_year)}__{source_node_id}__"
                    f"{target_node_id}__{edge_type}"
                ),
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "decision_year": int(decision_year),
                "edge_type": edge_type,
                "edge_weight": stateful_weight,
                "signal_strength": signal_strength,
                "stability_score": stability_score,
                "source_basis": latest["source_basis"],
                "source_relation_id": latest["source_relation_id"],
                "source_relation_year_end": latest_year,
                "edge_age": edge_age,
                "edge_memory_mode": STATEFUL_EDGE_MEMORY_MODE,
                "edge_variant": STATEFUL_EDGE_VARIANT,
                "edge_state": state,
                "state_multiplier": multiplier,
                "recent_observation_count": int(recent_observation_count),
                "total_observation_count": int(len(observed_years)),
                "first_observed_year": int(observed_years[0]),
                "latest_observed_year": latest_year,
                "claim_status": CLAIM_STATUS,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["decision_year", "target_node_id", "edge_type", "source_node_id"]
    ).reset_index(drop=True)


def _classify_edge_state(
    *,
    decision_year: int,
    latest_year: int,
    previous_year: int | None,
    recent_observation_count: int,
    signal_strength: float,
    stability_score: float,
) -> str:
    if abs(signal_strength) >= 0.70 and stability_score < 0.25:
        return "volatile_relation"
    if latest_year == decision_year:
        if previous_year is None:
            return "new_relation"
        if previous_year < decision_year - 1:
            return "reappearing_relation"
        return "persistent_relation"
    if recent_observation_count >= 2:
        return "persistent_relation"
    return "decaying_relation"


def _empty_pruned_schema(reference_edges: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "edge_variant",
        "edge_priority",
        "rank_within_target_year",
        "prune_top_k_per_node",
        "prune_min_stability",
        "prune_min_abs_signal",
        "prune_max_edge_age",
        "claim_status",
    ]
    return pd.DataFrame(columns=columns)


def _empty_stateful_schema() -> pd.DataFrame:
    columns = [
        "edge_id",
        "source_node_id",
        "target_node_id",
        "decision_year",
        "edge_type",
        "edge_weight",
        "signal_strength",
        "stability_score",
        "source_basis",
        "source_relation_id",
        "source_relation_year_end",
        "edge_age",
        "edge_memory_mode",
        "edge_variant",
        "edge_state",
        "state_multiplier",
        "recent_observation_count",
        "total_observation_count",
        "first_observed_year",
        "latest_observed_year",
        "claim_status",
    ]
    return pd.DataFrame(columns=columns)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expanding_edges = load_expanding_edges()
    pruned_edges = build_pruned_stable_edges(expanding_edges)
    pruned_edges.to_csv(PRUNED_STABLE_EDGES_OUT_PATH, index=False)
    stateful_edges = build_stateful_edges(expanding_edges)
    stateful_edges.to_csv(STATEFUL_EDGES_OUT_PATH, index=False)
    print(f"Pruned stable edges: {len(pruned_edges)} -> {PRUNED_STABLE_EDGES_OUT_PATH}")
    print(f"Stateful edges: {len(stateful_edges)} -> {STATEFUL_EDGES_OUT_PATH}")
    if not pruned_edges.empty:
        print(f"Pruned years: {pruned_edges['decision_year'].min()}-{pruned_edges['decision_year'].max()}")
        print(f"Pruned edge types: {', '.join(sorted(pruned_edges['edge_type'].unique()))}")
        print(
            "Pruning: "
            f"top_k={DEFAULT_TOP_K_PER_NODE}, "
            f"min_stability={DEFAULT_MIN_STABILITY}, "
            f"min_abs_signal={DEFAULT_MIN_ABS_SIGNAL}, "
            f"max_edge_age={DEFAULT_MAX_EDGE_AGE}"
        )
    if not stateful_edges.empty:
        print(f"Stateful years: {stateful_edges['decision_year'].min()}-{stateful_edges['decision_year'].max()}")
        print(f"Stateful edge states: {', '.join(sorted(stateful_edges['edge_state'].unique()))}")


if __name__ == "__main__":
    main()
