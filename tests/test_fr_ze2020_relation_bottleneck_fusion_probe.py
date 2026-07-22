from src.modeles.france_ze2020.run_fr_ze2020_relation_bottleneck_fusion_probe import (
    build_bottleneck_model,
)


def test_bottleneck_is_fitted_before_mlp_with_fixed_pca_threshold() -> None:
    model = build_bottleneck_model(
        ["node_a", "node_b"],
        ["relation_a", "relation_b"],
        seed=42,
        max_epochs=200,
    )
    preprocess = model.named_steps["preprocess"]
    relation = dict((name, transformer) for name, transformer, _ in preprocess.transformers)[
        "relation"
    ]
    assert relation.named_steps["pca"].n_components == 0.90
    assert model.named_steps["mlp"].hidden_layer_sizes == (32, 16)
    assert list(model.named_steps) == ["preprocess", "mlp"]
