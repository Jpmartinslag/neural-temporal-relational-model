from pathlib import Path

import pandas as pd

from hpc.france_ze2020_dynamic_graph.audit_fr_ze2020_dynamic_graph_results import (
    audit_falsification,
    audit_ranker,
)


def _write_ranker_seed(seed_dir: Path) -> None:
    seed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "ze2020": ["0051", "0051"],
            "sector_code": ["GI", "MN"],
            "decision_year": [2024, 2024],
            "model": ["ridge_dynamic_graph", "mlp_dynamic_graph"],
            "score": [0.2, 0.3],
            "claim_status": ["dynamic_graph_ranker_smoke_not_recommendation"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_dynamic_graph_ranker_1y_predictions_v1.csv", index=False)
    pd.DataFrame(
        {
            "model": ["ridge_dynamic_graph", "mlp_dynamic_graph"],
            "precision_at_k": [0.5, 0.4],
            "hit_rate_at_k": [1.0, 1.0],
            "ndcg_at_k": [0.6, 0.5],
            "claim_status": ["dynamic_graph_ranker_smoke_not_recommendation"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_dynamic_graph_ranker_1y_metrics_v1.csv", index=False)


def _write_falsification_seed(seed_dir: Path) -> None:
    seed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "ze2020": ["0051", "0051"],
            "sector_code": ["GI", "MN"],
            "decision_year": [2024, 2024],
            "model": ["ridge_dynamic_graph", "mlp_dynamic_graph"],
            "score": [0.2, 0.3],
            "falsification_scenario": ["full_control", "no_edges"],
            "claim_status": ["dynamic_graph_falsification_exploratory_not_recommendation"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_dynamic_graph_falsification_1y_predictions_v1.csv", index=False)
    pd.DataFrame(
        {
            "falsification_scenario": ["full_control", "no_edges"],
            "model": ["ridge_dynamic_graph", "mlp_dynamic_graph"],
            "precision_at_k": [0.5, 0.4],
            "hit_rate_at_k": [1.0, 1.0],
            "ndcg_at_k": [0.6, 0.5],
            "claim_status": ["dynamic_graph_falsification_exploratory_not_recommendation"] * 2,
        }
    ).to_csv(seed_dir / "fr_ze2020_dynamic_graph_falsification_1y_metrics_v1.csv", index=False)
    pd.DataFrame({"falsification_scenario": ["full_control", "no_edges"]}).to_csv(
        seed_dir / "fr_ze2020_dynamic_graph_falsification_1y_summary_v1.csv", index=False
    )
    pd.DataFrame({"falsification_scenario": ["full_control", "no_edges"]}).to_csv(
        seed_dir / "fr_ze2020_dynamic_graph_falsification_1y_manifest_v1.csv", index=False
    )
    (seed_dir / "fr_ze2020_dynamic_graph_falsification_1y_run_v1.json").write_text("{}\n")


def test_dynamic_graph_ranker_audit_accepts_seed_outputs(tmp_path):
    run_dir = tmp_path / "run"
    _write_ranker_seed(run_dir / "seed_42")
    report = audit_ranker(run_dir)
    assert report["status"] == "DYNAMIC_GRAPH_RANKER_AUDIT_DESCRIPTIVE_ONLY"
    assert report["n_seed_dirs"] == 1
    assert report["top_model_by_mean_ndcg"] == "ridge_dynamic_graph"


def test_dynamic_graph_falsification_audit_accepts_seed_outputs(tmp_path):
    run_dir = tmp_path / "run"
    _write_falsification_seed(run_dir / "seed_42")
    report = audit_falsification(run_dir)
    assert report["status"] == "DYNAMIC_GRAPH_FALSIFICATION_AUDIT_DESCRIPTIVE_ONLY"
    assert report["n_seed_dirs"] == 1
    assert {r["falsification_scenario"] for r in report["top_by_scenario"]} == {
        "full_control",
        "no_edges",
    }


def test_dynamic_graph_audit_rejects_forbidden_columns(tmp_path):
    run_dir = tmp_path / "run"
    seed_dir = run_dir / "seed_42"
    _write_ranker_seed(seed_dir)
    metrics_path = seed_dir / "fr_ze2020_dynamic_graph_ranker_1y_metrics_v1.csv"
    metrics = pd.read_csv(metrics_path)
    metrics["policy_action"] = "bad"
    metrics.to_csv(metrics_path, index=False)
    try:
        audit_ranker(run_dir)
    except ValueError as exc:
        assert "Forbidden columns" in str(exc)
    else:
        raise AssertionError("audit_ranker should reject forbidden columns")
