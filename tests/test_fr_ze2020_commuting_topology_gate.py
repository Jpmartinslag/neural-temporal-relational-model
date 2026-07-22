from pathlib import Path

import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_commuting_topology_gate import (
    CLAIM_STATUS,
    VIEW_NAMES,
    evaluate_topology_gate,
    uniform_variant,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "src/modeles/france_ze2020/run_fr_ze2020_commuting_topology_gate.py"
)


def _edges() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "decision_year": [2020] * 6,
            "source_ze2020": ["0001", "0001", "0002", "0002", "0003", "0003"],
            "target_ze2020": ["0002", "0003", "0001", "0003", "0001", "0002"],
            "edge_weight": [0.8, 0.2, 0.6, 0.4, 0.7, 0.3],
        }
    )


def test_uniform_variant_removes_intensity_but_keeps_normalization():
    result = uniform_variant(_edges())
    assert set(result["edge_weight"]) == {0.5}
    assert (result.groupby("source_ze2020")["edge_weight"].sum() == 1.0).all()


def test_uniform_endpoint_placebo_has_no_self_loops():
    result = uniform_variant(_edges(), endpoint_seed=7017)
    assert not (result["source_ze2020"] == result["target_ze2020"]).any()
    assert (result.groupby("source_ze2020")["edge_weight"].sum() == 1.0).all()


def test_topology_gate_counts_only_independent_deterministic_pairs():
    rows = []
    for seed in [42, 43]:
        for view in VIEW_NAMES:
            score = 0.6
            if view == "commuting_topology_real_uniform":
                score = 0.7
            elif view == "commuting_topology_endpoint_randomized_uniform":
                score = 0.5 + 0.01 * (seed - 42)
            elif view == "commuting_topology_target_shuffled":
                score = 0.4 + 0.01 * (seed - 42)
            rows.append(
                {
                    "view": view,
                    "seed": seed,
                    "eval_year": 2022,
                    "ze_fold": 0,
                    "ndcg_at_3": score,
                }
            )
    gate = evaluate_topology_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True
    assert gate["comparisons"]["commuting_topology_degree_only"]["n_pairs"] == 1
    assert (
        gate["comparisons"]["commuting_topology_endpoint_randomized_uniform"][
            "n_pairs"
        ]
        == 2
    )


def test_script_is_linear_and_has_conservative_claim_status():
    source = SCRIPT_PATH.read_text().lower()
    for forbidden in [
        "mlpregressor",
        "gconvgru",
        "evolvegcn",
        "recommendation_score",
        "causal_effect",
    ]:
        assert forbidden not in source
    assert CLAIM_STATUS in SCRIPT_PATH.read_text()
