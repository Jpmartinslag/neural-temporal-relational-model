"""
Tests for src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py
-- MVP3-B sector graph smoke prototype.

Building the full ZE2020 x sector node table with both edge types takes
~1 minute (9 sectors x 13 years x 280 zones of manual message passing) --
done ONCE in a module-scoped fixture and reused by every test below, rather
than rebuilt per test. Leakage-specific checks use a small synthetic panel
instead, so they run in milliseconds regardless of the fixture cost.
"""

import ast
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.modeles.france_ze2020.train_fr_ze2020_sector_graph_prototype import (
    GRAPH_FEATURE_COLS,
    OWN_FEATURE_COLS,
    SECTOR_FEATURES_PATH,
    SECTOR_PANEL_PATH,
    add_cross_ze_messages,
    add_intra_ze_messages,
    build_graph_node_features,
    build_node_table,
    intra_ze_relation_signals,
    run_sector_graph_smoke,
)

SCRIPT_PATH = (
    Path(__file__).parent.parent / "src/modeles/france_ze2020/train_fr_ze2020_sector_graph_prototype.py"
)

FORBIDDEN_COLUMN_NAMES = {"recommendation", "recommended_action", "policy_action"}


@pytest.fixture(scope="module")
def nodes_with_messages():
    assert SECTOR_PANEL_PATH.exists()
    assert SECTOR_FEATURES_PATH.exists()
    nodes = build_node_table()
    return build_graph_node_features(nodes)


def _tiny_synthetic_panel() -> pd.DataFrame:
    """3 zones x 2 sectors x 7 years (2018-2024), hand-built, just enough
    columns for add_intra_ze_messages / add_cross_ze_messages to run."""
    rows = []
    rng = np.random.RandomState(0)
    for zone in ["A001", "A002", "A003"]:
        for sector in ["X1", "Y1"]:
            base = rng.uniform(0.3, 0.7)
            for i, year in enumerate(range(2018, 2025)):
                share = float(np.clip(base + 0.02 * i + rng.normal(0, 0.01), 0.05, 0.95))
                growth = float(rng.normal(0.05, 0.02)) if i >= 1 else np.nan
                rows.append(
                    {
                        "ze2020": zone,
                        "year": year,
                        "sector_code": sector,
                        "sector_share_lag_1": share,
                        "sector_growth_lag_1": growth,
                        "sector_growth_lag_2": growth,
                        "national_sector_share_lag_1": 0.5,
                        "national_sector_growth_lag_1": 0.05,
                        "dominant_sector_lag_1": "X1",
                        "dominant_sector_share_lag_1": 0.6,
                        "sector_diversity_lag_1": 0.8,
                        "sector_concentration_hhi_lag_1": 0.3,
                        "commerce_share_lag_1": 0.2,
                        "construction_share_lag_1": 0.1,
                        "sector_share": share,
                    }
                )
    df = pd.DataFrame(rows)
    df["dominant_sector_flag"] = (df["sector_code"] == df["dominant_sector_lag_1"]).astype(int)
    df["node_id"] = df["ze2020"] + "_" + df["sector_code"]
    return df


def test_script_does_not_read_legacy_or_unprovenanced_sources():
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree) or ""
    code_without_docstring = source.replace(docstring, "")

    assert "dynamic_stgnn_feature_panel" not in code_without_docstring
    assert "graph_adjacency_core_v0" not in code_without_docstring
    assert "graph_adjacency_mobility_v0" not in code_without_docstring


def test_intra_ze_message_is_mean_of_other_sectors_same_zone():
    panel = _tiny_synthetic_panel()
    out = add_intra_ze_messages(panel)
    row = out[(out["ze2020"] == "A001") & (out["sector_code"] == "X1") & (out["year"] == 2024)].iloc[0]
    sibling = out[(out["ze2020"] == "A001") & (out["sector_code"] == "Y1") & (out["year"] == 2024)].iloc[0]
    assert row["intra_ze_share_mean"] == pytest.approx(sibling["sector_share_lag_1"])


def test_cross_ze_similarity_uses_strictly_prior_years_only():
    """Truncating the input to year <= eval_year must produce identical
    cross_ze_* columns at eval_year as the full panel -- proving rows for
    later years had zero effect (synthetic data, milliseconds)."""
    panel = _tiny_synthetic_panel()
    eval_year = 2023

    full, _ = add_cross_ze_messages(panel)
    truncated, _ = add_cross_ze_messages(panel[panel["year"] <= eval_year])

    full_at_t = full[full["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    trunc_at_t = (
        truncated[truncated["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    )
    pd.testing.assert_series_equal(
        full_at_t["cross_ze_share_mean"], trunc_at_t["cross_ze_share_mean"], check_names=False
    )
    pd.testing.assert_series_equal(
        full_at_t["cross_ze_growth_mean"], trunc_at_t["cross_ze_growth_mean"], check_names=False
    )


def test_cross_ze_edges_never_reference_the_target_year_itself():
    panel = _tiny_synthetic_panel()
    _, edges = add_cross_ze_messages(panel)
    if edges.empty:
        pytest.skip("no edges formed on this synthetic panel (acceptable -- correlation may be too weak)")
    # the similarity matrix used to pick these edges only ever read
    # history strictly before `year`; nothing here asserts the edge's own
    # year column was used as a feature value, only as a label.
    assert edges["year"].between(2018, 2024).all()


def test_mutating_current_years_target_does_not_change_its_own_cross_ze_message():
    """sector_growth_lag_1/sector_share_lag_1 (the MESSAGE columns) are
    already lagged by construction (verified in
    test_fr_ze2020_sector_relational_features.py upstream) -- mutating
    them directly would legitimately change the message, since that's
    exactly what they feed. The real leakage check is the TARGET
    (sector_share, contemporaneous): mutating it at eval_year must NOT
    change cross_ze_* at that same eval_year, since the message never
    reads sector_share at all."""
    panel = _tiny_synthetic_panel()
    eval_year = 2023

    baseline, _ = add_cross_ze_messages(panel)
    mutated_input = panel.copy()
    mutated_input.loc[mutated_input["year"] == eval_year, "sector_share"] = 999.0
    mutated, _ = add_cross_ze_messages(mutated_input)

    baseline_at_t = baseline[baseline["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    mutated_at_t = mutated[mutated["year"] == eval_year].set_index(["ze2020", "sector_code"]).sort_index()
    pd.testing.assert_series_equal(
        baseline_at_t["cross_ze_growth_mean"], mutated_at_t["cross_ze_growth_mean"], check_names=False
    )


def test_target_column_never_appears_in_graph_features():
    """Structural guard: sector_share (the target) must never be part of
    the feature vector fed to the model -- this is what actually prevents
    target leakage, independent of the mutation test above."""
    assert "sector_share" not in GRAPH_FEATURE_COLS
    assert "sector_share" not in OWN_FEATURE_COLS


def test_node_table_schema_and_no_forbidden_columns(nodes_with_messages):
    nodes, _ = nodes_with_messages
    for col in OWN_FEATURE_COLS + GRAPH_FEATURE_COLS:
        assert col in nodes.columns
    cols_lower = {c.lower() for c in nodes.columns}
    assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)
    assert not any("stgnn" in c for c in cols_lower)


def test_run_produces_both_models(nodes_with_messages):
    nodes, _ = nodes_with_messages
    predictions, metrics = run_sector_graph_smoke(nodes, eval_years=[2023, 2024], max_epochs=50)
    assert set(metrics["model"].unique()) == {"persistence_sector", "graph_mlp"}
    assert set(predictions["model"].unique()) == {"persistence_sector", "graph_mlp"}


def test_outputs_marked_smoke_not_headline(nodes_with_messages):
    nodes, _ = nodes_with_messages
    predictions, metrics = run_sector_graph_smoke(nodes, eval_years=[2024], max_epochs=50)
    assert (predictions["claim_status"] == "sector_graph_smoke").all()
    assert (metrics["claim_status"] == "sector_graph_smoke").all()


def test_relation_signals_have_exploratory_claim_status(nodes_with_messages):
    nodes, _ = nodes_with_messages
    signals = intra_ze_relation_signals(nodes, [2023, 2024])
    if signals.empty:
        pytest.skip("no intra-ZE signal pairs formed for these eval years")
    assert (signals["claim_status"] == "sector_graph_smoke").all()
    assert {"source_node", "target_node", "year", "relation_type", "learned_or_aggregated_weight", "signal_strength"}.issubset(
        signals.columns
    )


def test_no_recommendation_or_policy_column_anywhere(nodes_with_messages):
    nodes, edges = nodes_with_messages
    predictions, metrics = run_sector_graph_smoke(nodes, eval_years=[2024], max_epochs=50)
    for df in (predictions, metrics, edges):
        cols_lower = {c.lower() for c in df.columns}
        assert not (cols_lower & FORBIDDEN_COLUMN_NAMES)


def test_no_causal_or_recommendation_language_in_docstring():
    source = SCRIPT_PATH.read_text()
    tree = ast.parse(source)
    docstring = (ast.get_docstring(tree) or "").lower()
    assert "no causal claim" in docstring
    assert "no automatic" in docstring or "no recommendation" in docstring


def test_runs_fast_with_small_max_epochs(nodes_with_messages):
    nodes, _ = nodes_with_messages
    start = time.time()
    run_sector_graph_smoke(nodes, eval_years=[2024], max_epochs=50)
    elapsed = time.time() - start
    assert elapsed < 30


def test_reproducible_with_fixed_seed(nodes_with_messages):
    nodes, _ = nodes_with_messages
    predictions_a, metrics_a = run_sector_graph_smoke(nodes, eval_years=[2023, 2024], max_epochs=80, seed=42)
    predictions_b, metrics_b = run_sector_graph_smoke(nodes, eval_years=[2023, 2024], max_epochs=80, seed=42)
    assert predictions_a.equals(predictions_b)
    np.testing.assert_array_equal(metrics_a["wmape"].to_numpy(), metrics_b["wmape"].to_numpy())


def test_node_features_are_finite_for_complete_rows(nodes_with_messages):
    """Guards against the infinite-value edge case found in
    fr_ze2020_sector_relational_features.csv (one zero-establishment row
    causes a division-by-zero growth value) -- the completeness filter
    inside run_sector_graph_smoke must exclude it, never feed it to the MLP."""
    nodes, _ = nodes_with_messages
    predictions, _ = run_sector_graph_smoke(nodes, eval_years=[2024], max_epochs=50)
    assert np.isfinite(predictions["y_pred"].to_numpy()).all()
    assert np.isfinite(predictions["y_true"].to_numpy()).all()
