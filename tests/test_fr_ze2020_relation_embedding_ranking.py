from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_relation_embedding_ranking import (
    CLAIM_STATUS,
    FORBIDDEN_EMBEDDING_COLUMNS,
    coverage_summary,
    embedding_column_groups,
    merge_panel_embeddings,
    run_relation_embedding_ranking_diagnostic,
)
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import load_ranking_panel

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "src/modeles/france_ze2020/run_fr_ze2020_relation_embedding_ranking.py"
EMBEDDINGS_PATH = (
    REPO_ROOT
    / "data/processed/france_ze2020/fr_ze2020_dynamic_relation_encoder_node_embeddings_v1.csv"
)


def test_relation_embedding_ranking_script_has_no_forbidden_claim_columns():
    source = SCRIPT_PATH.read_text()
    for term in ["recommended_action", "policy_action", "causal_effect", "causal_impact"]:
        assert term not in source


def test_encoder_embedding_table_excludes_label_like_columns_if_present():
    if not EMBEDDINGS_PATH.exists():
        return
    df = pd.read_csv(EMBEDDINGS_PATH, nrows=5)
    assert FORBIDDEN_EMBEDDING_COLUMNS.isdisjoint(df.columns)


def test_embedding_column_groups_split_sparse_and_dense_features():
    embeddings = pd.DataFrame(
        {
            "relation_in_score_mean": [0.1],
            "relation_embedding_available": [1],
            "relation_graph_in_count": [2],
            "relation_graph_embedding_available": [1],
            "claim_status": [CLAIM_STATUS],
        }
    )
    sparse, dense = embedding_column_groups(embeddings)
    assert "relation_in_score_mean" in sparse
    assert "relation_embedding_available" in sparse
    assert "relation_graph_in_count" in dense
    assert "relation_graph_embedding_available" in dense
    assert "claim_status" not in sparse


def test_merge_panel_embeddings_keeps_panel_rows_and_fills_missing():
    panel = pd.DataFrame(
        {
            "ze2020": ["0051", "0051"],
            "sector_code": ["BE", "FZ"],
            "decision_year": [2022, 2022],
            "ranking_feature_complete": [1, 1],
        }
    )
    embeddings = pd.DataFrame(
        {
            "ze2020": ["0051"],
            "sector_code": ["BE"],
            "decision_year": [2022],
            "relation_in_score_mean": [0.5],
            "relation_embedding_available": [1],
            "relation_graph_in_count": [3],
            "relation_graph_embedding_available": [1],
        }
    )
    merged, sparse, dense = merge_panel_embeddings(panel, embeddings)
    assert len(merged) == len(panel)
    assert sparse
    assert dense
    missing = merged[merged["sector_code"] == "FZ"].iloc[0]
    assert missing["relation_in_score_mean"] == 0.0
    assert missing["relation_graph_in_count"] == 0.0


def test_coverage_summary_reports_sparse_and_dense_availability():
    merged = pd.DataFrame(
        {
            "decision_year": [2022, 2022],
            "relation_embedding_available": [1, 0],
            "relation_graph_embedding_available": [1, 1],
        }
    )
    coverage = coverage_summary(merged)
    row = coverage.iloc[0]
    assert row["rows"] == 2
    assert row["learned_sparse_available"] == 1
    assert row["dense_graph_available"] == 2
    assert row["claim_status"] == CLAIM_STATUS


def test_relation_embedding_ranking_diagnostic_smoke_if_embeddings_exist():
    if not EMBEDDINGS_PATH.exists():
        return
    panel = load_ranking_panel()
    embeddings = pd.read_csv(EMBEDDINGS_PATH, dtype={"ze2020": str, "sector_code": str})
    predictions, metrics, summary, coverage = run_relation_embedding_ranking_diagnostic(
        panel=panel,
        embeddings=embeddings,
        target_horizons=[1],
        seeds=[42],
        max_epochs=20,
        feature_configs=[
            "base_formula_features",
            "dense_graph_embeddings",
            "shuffled_dense_graph_embeddings",
        ],
    )
    assert not predictions.empty
    assert not metrics.empty
    assert not summary.empty
    assert not coverage.empty
    assert "recommendation" not in {col.lower() for col in predictions.columns}
    assert set(metrics["claim_status"]) == {CLAIM_STATUS}
    assert {
        "base_formula_features",
        "dense_graph_embeddings",
        "shuffled_dense_graph_embeddings",
    }.issubset(set(summary["feature_config"]))
