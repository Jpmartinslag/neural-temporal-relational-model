import pandas as pd

from src.modeles.france_ze2020.run_fr_ze2020_similarity_nonlinear_transfer_probe import (
    evaluate_nonlinear_gate,
)


def test_nonlinear_gate_requires_all_registered_comparisons() -> None:
    rows = []
    values = {
        "mlp_ze_similarity": 0.70,
        "mlp_node_only": 0.65,
        "logit_ze_similarity": 0.66,
        "mlp_ze_similarity_endpoint_randomized": 0.60,
        "mlp_ze_similarity_target_shuffled": 0.50,
    }
    for fold in range(5):
        for view, ndcg in values.items():
            rows.append(
                {
                    "view": view,
                    "seed": 42,
                    "eval_year": 2022,
                    "ze_fold": fold,
                    "ndcg_at_3": ndcg,
                }
            )
    gate = evaluate_nonlinear_gate(pd.DataFrame(rows))
    assert gate["gate_pass"] is True
    assert gate["comparisons"]["mlp_ze_similarity_endpoint_randomized"][
        "paired_win_rate"
    ] == 1.0
