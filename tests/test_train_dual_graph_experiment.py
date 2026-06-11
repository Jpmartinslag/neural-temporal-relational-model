"""HERALD — Tests for the dual-graph scientific trainer (contract §8–§9).

Mandatory coverage:
  - rolling-origin and temporal inner validation;
  - no outer target in training or model selection;
  - class weights from inner-train only;
  - C2–C5 identical parameter count;
  - determinism;
  - permutation controls C6–C10 correct and causal;
  - metrics on known cases;
  - AUCPR and precision@k with a rare class;
  - learned-graph top-k and seed Jaccard;
  - gate passes and fails on synthetic fixtures;
  - unique outputs and atomic writes;
  - NaN/Inf handled fail-closed;
  - no dependency on the old L1 / ZE2020.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import src.modeles.train_dual_graph_experiment as T  # noqa: E402
from src.modeles.train_dual_graph_experiment import (  # noqa: E402
    CONTROLS,
    apply_control,
    apply_gate,
    atomic_write_json,
    aggregate,
    binary_metrics,
    build_dual_graph_model,
    count_parameters,
    evaluate_run,
    extract_topk_edges,
    jaccard,
    mean_seed_jaccard,
    perm_seed,
    regime_metrics,
    regression_metrics,
    targets_unchanged,
    temporal_split,
    train_neural,
    _forward,
    _slice_targets,
    _to_tensor_fold,
)

RS_R, RS_S, F, TT = 6, 9, 6, 5


def _synth_fold(n_samples=4, first_year=2018, seed=0):
    rng = np.random.default_rng(seed)
    sample_years = list(range(first_year, first_year + n_samples))
    B = n_samples
    obs_years = np.array([[y - TT + i for i in range(TT)] for y in sample_years],
                         dtype=np.int64)
    feats = rng.standard_normal((B, TT, RS_R, RS_S, F)).astype(np.float32)
    fmask = (rng.random((B, TT, RS_R, RS_S, F)) > 0.05).astype(np.uint8)
    adj = np.zeros((B, TT, RS_S, RS_R, RS_R), dtype=np.float32)
    for b in range(B):
        for t in range(TT):
            for s in range(RS_S):
                m = rng.random((RS_R, RS_R)).astype(np.float32)
                m = (m + m.T) / 2
                np.fill_diagonal(m, 0.0)
                m[m < 0.6] = 0.0
                adj[b, t, s] = m
    adj_mask = (adj.sum(axis=(-1, -2)) > 0).astype(np.uint8)
    tmask = np.ones((B, RS_R, RS_S), dtype=np.uint8)
    return {
        "features_seq": feats,
        "feature_mask_seq": fmask,
        "territory_adj_seq": adj,
        "territory_adj_mask": adj_mask,
        "target_log_growth": rng.standard_normal((B, RS_R, RS_S)).astype(np.float32),
        "target_raw_growth": rng.standard_normal((B, RS_R, RS_S)).astype(np.float32),
        "target_regime": rng.integers(0, 3, (B, RS_R, RS_S)).astype(np.int64),
        "target_recovery": (rng.random((B, RS_R, RS_S)) > 0.85).astype(np.int64),
        "target_emergence": (rng.random((B, RS_R, RS_S)) > 0.9).astype(np.int64),
        "target_mask": tmask,
        "observation_years": obs_years,
        "sample_years": np.array(sample_years, dtype=np.int64),
        "region_ids": np.array([f"R{i:02d}" for i in range(RS_R)]),
        "sector_ids": np.array([f"S{i}" for i in range(RS_S)]),
        "feature_means": np.zeros(F, dtype=np.float32),
        "feature_stds": np.ones(F, dtype=np.float32),
    }


FAST_HP = dict(T.HYPERPARAMS)
FAST_HP["max_epochs"] = 4
FAST_HP["patience"] = 2


# ---------------------------------------------------------------------------
# Rolling-origin and temporal inner validation
# ---------------------------------------------------------------------------

def test_temporal_split_is_causal():
    fold = _synth_fold(n_samples=4, first_year=2018)
    split = temporal_split(fold)
    assert split["leakage_ok"] is True
    assert max(split["train_years"]) < split["val_year"] < split["outer_year"]
    assert split["max_feature_obs_year_outer"] < split["outer_year"]
    assert split["outer_idx"] == 3 and split["val_idx"] == 2
    assert split["train_idx"] == [0, 1]


def test_temporal_split_rejects_too_few_samples():
    fold = _synth_fold(n_samples=2)
    with pytest.raises(ValueError):
        temporal_split(fold)


# ---------------------------------------------------------------------------
# No outer target in training / selection
# ---------------------------------------------------------------------------

def test_training_ignores_outer_target():
    fold = _synth_fold(seed=1)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    spec = CONTROLS["C5_dual"]
    run_a = train_neural(fold_t, spec, split, seed=42, hp=FAST_HP)

    # Corrupt ONLY the outer-year targets; training must be unaffected.
    fold_t2 = {k: v.clone() for k, v in fold_t.items()}
    o = split["outer_idx"]
    fold_t2["target_log_growth"][o] += 999.0
    fold_t2["target_regime"][o] = 0
    run_b = train_neural(fold_t2, spec, split, seed=42, hp=FAST_HP)

    assert run_a["val_history"] == run_b["val_history"]
    assert np.allclose(run_a["outputs"]["pred_log_growth"],
                       run_b["outputs"]["pred_log_growth"])


def test_forward_signature_has_no_target():
    # Trainer never passes targets into the model forward.
    sig = inspect.signature(build_dual_graph_model(hidden_dim=4).forward)
    assert "target" not in " ".join(sig.parameters).lower()


# ---------------------------------------------------------------------------
# Class weights from inner-train only
# ---------------------------------------------------------------------------

def test_class_weights_from_train_slice_only():
    fold = _synth_fold(seed=2)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    tr = _slice_targets(fold_t, split["train_idx"])
    cw_train = T.compute_class_weights(tr["target_regime"], 3)

    # Changing val/outer labels must not change the train-derived weights.
    fold_t["target_regime"][split["val_idx"]] = 0
    fold_t["target_regime"][split["outer_idx"]] = 0
    tr2 = _slice_targets(fold_t, split["train_idx"])
    cw_train2 = T.compute_class_weights(tr2["target_regime"], 3)
    assert torch.allclose(cw_train, cw_train2)


# ---------------------------------------------------------------------------
# C2–C5 identical parameter count
# ---------------------------------------------------------------------------

def test_neural_controls_equal_capacity():
    counts = {}
    for c in ("C2_no_graph", "C3_territory_only", "C4_sector_only", "C5_dual",
              "C6_territory_temporal_perm", "C7_territory_graph_perm",
              "C8_sector_identity_perm", "C9_no_ardeco", "C10_ardeco_temporal_perm"):
        spec = CONTROLS[c]
        m = build_dual_graph_model(
            hidden_dim=8, use_territory_graph=spec["territory"],
            use_sector_graph=spec["sector"])
        counts[c] = count_parameters(m)
    assert len(set(counts.values())) == 1, counts


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_training_deterministic_per_seed():
    fold = _synth_fold(seed=3)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    spec = CONTROLS["C5_dual"]
    a = train_neural(fold_t, spec, split, seed=42, hp=FAST_HP)
    b = train_neural(fold_t, spec, split, seed=42, hp=FAST_HP)
    assert np.allclose(a["outputs"]["pred_log_growth"], b["outputs"]["pred_log_growth"])
    assert a["val_history"] == b["val_history"]


# ---------------------------------------------------------------------------
# Permutation controls C6–C10
# ---------------------------------------------------------------------------

def test_perm_seed_recorded_and_deterministic():
    assert perm_seed(42, 2021, "C6_territory_temporal_perm") == \
        perm_seed(42, 2021, "C6_territory_temporal_perm")
    assert perm_seed(42, 2021, "C6_territory_temporal_perm") != \
        perm_seed(43, 2021, "C6_territory_temporal_perm")


def test_c6_permutes_territory_time_only():
    fold_t = _to_tensor_fold(_synth_fold(seed=4))
    data, rec = apply_control(fold_t, "C6_territory_temporal_perm", 42, 2021)
    assert rec["perm_kind"] == "territory_temporal"
    assert len(rec["permutation"]) == TT
    # features untouched, adjacency time axis reordered
    assert torch.allclose(data["features_seq"], fold_t["features_seq"])
    tau = rec["permutation"]
    assert torch.allclose(data["territory_adj_seq"], fold_t["territory_adj_seq"][:, tau])


def test_c7_permutes_adjacency_only_targets_canonical():
    """C7 territory null: ONLY the territory adjacency is permuted (P A Pᵀ);
    features, targets and masks are bit-identical to canonical."""
    fold_t = _to_tensor_fold(_synth_fold(seed=5))
    data, rec = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    P = torch.as_tensor(rec["permutation"], dtype=torch.long)
    assert rec["mode"] == "territory_adjacency_similarity_PAPt"
    assert rec["targets_unchanged"] is True
    # features / masks / targets unchanged (bit-identical)
    assert torch.equal(data["features_seq"], fold_t["features_seq"])
    assert torch.equal(data["feature_mask_seq"], fold_t["feature_mask_seq"])
    for key in ("target_log_growth", "target_regime", "target_recovery",
                "target_emergence", "target_mask"):
        assert torch.equal(data[key], fold_t[key])
    # adjacency is the similarity transform P A Pᵀ on both region axes
    expected = fold_t["territory_adj_seq"].index_select(-2, P).index_select(-1, P)
    assert torch.equal(data["territory_adj_seq"], expected)
    assert not torch.equal(data["territory_adj_seq"], fold_t["territory_adj_seq"])


def test_c8_sector_identity_targets_canonical():
    """C8 sector null: sector axis of features + territory-graph sector axis is
    permuted by σ; targets and target_mask stay canonical (bit-identical)."""
    fold_t = _to_tensor_fold(_synth_fold(seed=6))
    data, rec = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    sig = torch.as_tensor(rec["permutation"], dtype=torch.long)
    assert rec["mode"] == "sector_feature_and_territory_sector_axis"
    assert rec["targets_unchanged"] is True
    # features + territory sector axis permuted
    assert torch.equal(data["features_seq"], fold_t["features_seq"].index_select(3, sig))
    assert torch.equal(data["territory_adj_seq"],
                       fold_t["territory_adj_seq"].index_select(2, sig))
    # targets / target_mask canonical
    for key in ("target_log_growth", "target_regime", "target_recovery",
                "target_emergence", "target_mask"):
        assert torch.equal(data[key], fold_t[key])


def test_c9_drops_ardeco_channels():
    fold_t = _to_tensor_fold(_synth_fold(seed=7))
    data, rec = apply_control(fold_t, "C9_no_ardeco", 42, 2021)
    assert rec["dropped_features"] == T.ARDECO_FEATURES
    assert torch.all(data["features_seq"][..., T.ARDECO_FEATURES] == 0)
    assert torch.all(data["feature_mask_seq"][..., T.ARDECO_FEATURES] == 0)
    # base channels untouched
    assert torch.allclose(data["features_seq"][..., T.BASE_FEATURES],
                          fold_t["features_seq"][..., T.BASE_FEATURES])


def test_c10_permutes_ardeco_time_only():
    fold_t = _to_tensor_fold(_synth_fold(seed=8))
    data, rec = apply_control(fold_t, "C10_ardeco_temporal_perm", 42, 2021)
    tau = rec["permutation"]
    # base channels untouched, ARDECO channels time-permuted
    assert torch.allclose(data["features_seq"][..., T.BASE_FEATURES],
                          fold_t["features_seq"][..., T.BASE_FEATURES])
    assert torch.allclose(data["features_seq"][..., T.ARDECO_FEATURES],
                          fold_t["features_seq"][:, tau][..., T.ARDECO_FEATURES])


def test_permutations_stay_within_causal_window():
    """Temporal permutations only reorder the 5 causal steps; no future enters."""
    fold = _synth_fold(seed=9)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    for c in ("C6_territory_temporal_perm", "C10_ardeco_temporal_perm"):
        data, _ = apply_control(fold_t, c, 42, split["outer_year"])
        # the sample axis (years) is never permuted, only the within-window T axis
        assert data["features_seq"].shape == fold_t["features_seq"].shape


# ---------------------------------------------------------------------------
# Conceptual audit of the null controls C7 / C8
# ---------------------------------------------------------------------------

def _fixed_model_predict(data, idx, seed=123):
    """Predictions of a single fixed-weight dual model on sample `idx`."""
    torch.manual_seed(seed)
    model = build_dual_graph_model(hidden_dim=8).eval()
    with torch.no_grad():
        out = _forward(model, data, [idx])
    return out["pred_log_growth"][0].numpy(), model


def _perm_index(t, dim, perm):
    return t.index_select(dim, torch.as_tensor(perm, dtype=torch.long))


# (1) full co-permutation PXPᵀ / PX / PY is a relabeling, not a null
def test_full_copermutation_is_pure_relabeling():
    """Permuting features, adjacency (P A Pᵀ) AND targets by the same region
    permutation P yields predictions equal to P·(canonical predictions): a
    similarity/relabeling that preserves the loss against the permuted targets.
    This is exactly why co-permutation is NOT a valid null control."""
    fold_t = _to_tensor_fold(_synth_fold(seed=20))
    o = 3
    rng = np.random.default_rng(0)
    P = rng.permutation(RS_R)

    canon = {k: v.clone() for k, v in fold_t.items()}
    degen = {k: v.clone() for k, v in fold_t.items()}
    degen["features_seq"] = _perm_index(degen["features_seq"], 2, P)
    degen["feature_mask_seq"] = _perm_index(degen["feature_mask_seq"], 2, P)
    degen["territory_adj_seq"] = _perm_index(
        _perm_index(degen["territory_adj_seq"], -2, P), -1, P)
    for key in ("target_log_growth", "target_mask"):
        degen[key] = _perm_index(degen[key], 1, P)

    torch.manual_seed(123)
    m = build_dual_graph_model(hidden_dim=8).eval()
    with torch.no_grad():
        pred_canon = m(canon["features_seq"][[o]], canon["feature_mask_seq"][[o]],
                       canon["territory_adj_seq"][[o]],
                       canon["territory_adj_mask"][[o]])["pred_log_growth"][0].numpy()
        pred_degen = m(degen["features_seq"][[o]], degen["feature_mask_seq"][[o]],
                       degen["territory_adj_seq"][[o]],
                       degen["territory_adj_mask"][[o]])["pred_log_growth"][0].numpy()
    # degenerate predictions are the canonical predictions permuted by P
    assert np.allclose(pred_degen, pred_canon[P], atol=1e-5)
    # and the MAE against the (also permuted) targets is identical → no null
    tgt = canon["target_log_growth"][o].numpy()
    mask = canon["target_mask"][o].numpy()
    mae_canon = regression_metrics(pred_canon, tgt, mask)["mae"]
    mae_degen = regression_metrics(pred_degen, tgt[P], mask[P])["mae"]
    assert abs(mae_canon - mae_degen) < 1e-6


# (2)/(3) C7 keeps canonical targets and breaks only territory alignment
def test_c7_changes_only_territory_alignment():
    fold_t = _to_tensor_fold(_synth_fold(seed=21))
    data, _ = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    assert targets_unchanged(fold_t, data)
    # everything except the territory adjacency is bit-identical
    for key in ("features_seq", "feature_mask_seq", "territory_adj_mask"):
        assert torch.equal(data[key], fold_t[key])
    assert not torch.equal(data["territory_adj_seq"], fold_t["territory_adj_seq"])


# (4) C8 keeps canonical targets and breaks only sector alignment
def test_c8_changes_only_sector_alignment():
    fold_t = _to_tensor_fold(_synth_fold(seed=22))
    data, rec = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    sig = rec["permutation"]
    assert targets_unchanged(fold_t, data)
    # territory region-structure preserved: same per-sector matrices, only the
    # sector slots are reindexed to follow the permuted features
    assert torch.equal(data["territory_adj_seq"],
                       _perm_index(fold_t["territory_adj_seq"], 2, sig))
    assert torch.equal(data["features_seq"], _perm_index(fold_t["features_seq"], 3, sig))


# (5) graph weight/degree/density distribution preserved
def test_c7_preserves_graph_distribution():
    fold_t = _to_tensor_fold(_synth_fold(seed=23))
    data, _ = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    a0 = fold_t["territory_adj_seq"]
    a1 = data["territory_adj_seq"]
    # total weight, density and sorted weights are invariant under P A Pᵀ
    assert torch.allclose(a0.sum(), a1.sum())
    assert torch.allclose(torch.sort(a0.flatten()).values,
                          torch.sort(a1.flatten()).values)
    # degree multiset per (sample, step, sector) preserved
    deg0 = torch.sort(a0.sum(-1).flatten()).values
    deg1 = torch.sort(a1.sum(-1).flatten()).values
    assert torch.allclose(deg0, deg1)


def test_c8_preserves_territory_graph_as_set():
    fold_t = _to_tensor_fold(_synth_fold(seed=24))
    data, _ = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    # territory adjacency total weight and sorted values unchanged (sector reorder)
    assert torch.allclose(fold_t["territory_adj_seq"].sum(),
                          data["territory_adj_seq"].sum())
    assert torch.allclose(torch.sort(fold_t["territory_adj_seq"].flatten()).values,
                          torch.sort(data["territory_adj_seq"].flatten()).values)


# (6) predictions of C5, C7, C8 differ under the SAME weights
def test_predictions_c5_c7_c8_differ_same_weights():
    fold_t = _to_tensor_fold(_synth_fold(seed=25))
    o = 3
    d5, _ = apply_control(fold_t, "C5_dual", 42, 2021)
    d7, _ = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    d8, _ = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    p5, model = _fixed_model_predict(d5, o)
    with torch.no_grad():
        p7 = _forward(model, d7, [o])["pred_log_growth"][0].numpy()
        p8 = _forward(model, d8, [o])["pred_log_growth"][0].numpy()
    assert not np.allclose(p5, p7, atol=1e-6)
    assert not np.allclose(p5, p8, atol=1e-6)
    assert not np.allclose(p7, p8, atol=1e-6)


# inverse permutation does NOT recover the canonical predictions
def test_inverse_permutation_does_not_recover_canonical():
    fold_t = _to_tensor_fold(_synth_fold(seed=26))
    o = 3
    p_canon, model = _fixed_model_predict(fold_t, o)
    d7, rec7 = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    d8, rec8 = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    with torch.no_grad():
        p7 = _forward(model, d7, [o])["pred_log_growth"][0].numpy()
        p8 = _forward(model, d8, [o])["pred_log_growth"][0].numpy()
    P = np.asarray(rec7["permutation"])
    sig = np.asarray(rec8["permutation"])
    # neither the raw nor the inverse-permuted predictions match canonical
    assert not np.allclose(p7, p_canon, atol=1e-6)
    assert not np.allclose(p7[P], p_canon, atol=1e-6)
    assert not np.allclose(p7[np.argsort(P)], p_canon, atol=1e-6)
    assert not np.allclose(p8[:, sig], p_canon, atol=1e-6)
    assert not np.allclose(p8[:, np.argsort(sig)], p_canon, atol=1e-6)


# (6) metrics are computed against canonical targets for C7/C8
def test_metrics_use_canonical_targets_for_nulls():
    fold = _synth_fold(seed=27)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    o = split["outer_idx"]
    for c in ("C7_territory_graph_perm", "C8_sector_identity_perm"):
        data, _ = apply_control(fold_t, c, 42, split["outer_year"])
        assert torch.equal(data["target_log_growth"][o],
                           fold_t["target_log_growth"][o])
        assert torch.equal(data["target_mask"][o], fold_t["target_mask"][o])


# (7) determinism of the corrected nulls
def test_c7_c8_permutation_deterministic_per_seed():
    fold_t = _to_tensor_fold(_synth_fold(seed=28))
    for c in ("C7_territory_graph_perm", "C8_sector_identity_perm"):
        _, r1 = apply_control(fold_t, c, 42, 2021)
        _, r2 = apply_control(fold_t, c, 42, 2021)
        _, r3 = apply_control(fold_t, c, 43, 2021)
        assert r1["permutation"] == r2["permutation"]
        assert r1["permutation"] != r3["permutation"]


# (8) no permutation reads the outer / future year
def test_null_permutation_independent_of_outer_data():
    fold_t = _to_tensor_fold(_synth_fold(seed=29))
    corrupted = {k: v.clone() for k, v in fold_t.items()}
    o = 3
    corrupted["features_seq"][o] += 1000.0
    corrupted["target_log_growth"][o] += 1000.0
    for c in ("C7_territory_graph_perm", "C8_sector_identity_perm"):
        _, ra = apply_control(fold_t, c, 42, 2021)
        _, rb = apply_control(corrupted, c, 42, 2021)
        # the permutation mapping depends only on (seed, year, control)
        assert ra["permutation"] == rb["permutation"]


# rejection of a degenerate co-permutation by the guard helper
def test_targets_unchanged_detects_copermutation():
    fold_t = _to_tensor_fold(_synth_fold(seed=30))
    data7, _ = apply_control(fold_t, "C7_territory_graph_perm", 42, 2021)
    data8, _ = apply_control(fold_t, "C8_sector_identity_perm", 42, 2021)
    assert targets_unchanged(fold_t, data7) is True
    assert targets_unchanged(fold_t, data8) is True
    # a hand-made degenerate co-permutation of the targets is detected
    degen = {k: v.clone() for k, v in fold_t.items()}
    P = np.random.default_rng(0).permutation(RS_R)
    degen["target_log_growth"] = _perm_index(degen["target_log_growth"], 1, P)
    assert targets_unchanged(fold_t, degen) is False


# ---------------------------------------------------------------------------
# Metrics on known cases
# ---------------------------------------------------------------------------

def test_regression_metrics_known():
    pred = np.array([[1.0, -2.0, 3.0]])
    target = np.array([[1.0, -2.0, 3.0]])
    mask = np.ones((1, 3), dtype=np.uint8)
    m = regression_metrics(pred, target, mask)
    assert m["mae"] == 0.0 and m["median_ae"] == 0.0 and m["sign_accuracy"] == 1.0


def test_regression_sign_accuracy():
    pred = np.array([1.0, -1.0, 1.0])
    target = np.array([1.0, 1.0, -1.0])  # 1/3 correct sign
    mask = np.ones(3, dtype=np.uint8)
    assert abs(regression_metrics(pred, target, mask)["sign_accuracy"] - 1 / 3) < 1e-9


def test_regime_metrics_perfect():
    logits = np.zeros((1, 3, 3))
    target = np.array([[0, 1, 2]])
    for j, c in enumerate(target[0]):
        logits[0, j, c] = 5.0
    mask = np.ones((1, 3), dtype=np.uint8)
    m = regime_metrics(logits, target, mask)
    assert m["macro_f1"] == 1.0 and m["balanced_accuracy"] == 1.0
    assert np.array(m["confusion_matrix"]).trace() == 3


# ---------------------------------------------------------------------------
# AUCPR and precision@k with a rare class
# ---------------------------------------------------------------------------

def test_binary_metrics_rare_class_ranking():
    # 20 nodes, 2 positives; scores rank the positives first → AUCPR=1.
    n = 20
    logits = np.linspace(5, -5, n)        # descending scores
    target = np.zeros(n, dtype=int)
    target[:2] = 1                         # top-2 are the positives
    mask = np.ones(n, dtype=np.uint8)
    m = binary_metrics(logits, target, mask, [5, 10])
    assert abs(m["prevalence"] - 0.1) < 1e-9
    assert m["aucpr"] == 1.0
    assert m["at_k"]["5"]["precision"] == pytest.approx(2 / 5)
    assert m["at_k"]["5"]["recall"] == 1.0
    assert m["at_k"]["5"]["ndcg"] == pytest.approx(1.0)


def test_binary_metrics_single_class_aucpr_none():
    logits = np.zeros(10)
    target = np.zeros(10, dtype=int)
    mask = np.ones(10, dtype=np.uint8)
    assert binary_metrics(logits, target, mask, [5])["aucpr"] is None


# ---------------------------------------------------------------------------
# Learned-graph top-k and Jaccard
# ---------------------------------------------------------------------------

def test_extract_topk_edges_and_jaccard():
    adj = np.zeros((4, 4), dtype=np.float32)
    adj[0, 1] = adj[1, 0] = 0.9
    adj[2, 3] = adj[3, 2] = 0.8
    edges = extract_topk_edges(adj, k=1)
    assert (0, 1) in edges["edges"] and (2, 3) in edges["edges"]
    assert edges["density"] == pytest.approx(2 / 6)
    assert jaccard(edges["edges"], edges["edges"]) == 1.0
    assert jaccard([(0, 1)], [(2, 3)]) == 0.0


def test_mean_seed_jaccard():
    a = {"edges": [(0, 1), (2, 3)]}
    b = {"edges": [(0, 1)]}
    c = {"edges": [(0, 1), (2, 3)]}
    # pairs: J(a,b)=1/2, J(a,c)=1, J(b,c)=1/2 → mean=2/3
    assert mean_seed_jaccard([a, b, c]) == pytest.approx(2 / 3)
    assert mean_seed_jaccard([a]) == 0.0  # <2 seeds → 0 (fail-closed)


# ---------------------------------------------------------------------------
# Gate passes and fails on synthetic fixtures
# ---------------------------------------------------------------------------

def _passing_agg(folds):
    """Construct an aggregated dict that satisfies every gate criterion."""
    def fold_block(mae, f1, rec, prev, jac):
        return {"mae": mae, "macro_f1": f1, "recovery_aucpr": rec,
                "recovery_prevalence": prev, "seed_jaccard": jac, "n_seeds": 5}
    agg = {}
    # dual clearly best
    agg["C5_dual"] = {
        "by_fold": {str(f): fold_block(0.50, 0.70, 0.40, 0.10, 0.60) for f in folds},
        "overall": {"mae": 0.50, "macro_f1": 0.70, "mean_seed_jaccard": 0.60}}
    agg["C1_ridge"] = {
        "by_fold": {str(f): fold_block(0.80, None, None, None, 0.0) for f in folds},
        "overall": {"mae": 0.80, "macro_f1": None, "mean_seed_jaccard": None}}
    agg["C2_no_graph"] = {
        "by_fold": {str(f): fold_block(0.70, 0.60, 0.20, 0.10, 0.0) for f in folds},
        "overall": {"mae": 0.70, "macro_f1": 0.60, "mean_seed_jaccard": None}}
    agg["C7_territory_graph_perm"] = {
        "by_fold": {str(f): fold_block(0.75, 0.55, 0.15, 0.10, 0.0) for f in folds},
        "overall": {"mae": 0.75, "macro_f1": 0.55, "mean_seed_jaccard": None}}
    agg["C8_sector_identity_perm"] = {
        "by_fold": {str(f): fold_block(0.78, 0.60, 0.15, 0.10, 0.0) for f in folds},
        "overall": {"mae": 0.78, "macro_f1": 0.60, "mean_seed_jaccard": None}}
    return agg


def test_gate_passes_on_good_fixture():
    folds = [2021, 2022, 2023, 2024, 2025]
    res = apply_gate(_passing_agg(folds), folds)
    assert res["decision"] == "DUAL_GRAPH_S1_PASS"
    assert all(res["criteria"].values())


def test_gate_fails_on_weak_jaccard():
    folds = [2021, 2022, 2023, 2024, 2025]
    agg = _passing_agg(folds)
    agg["C5_dual"]["overall"]["mean_seed_jaccard"] = 0.20  # below 0.50
    res = apply_gate(agg, folds)
    assert res["decision"] == "DUAL_GRAPH_S1_FAIL"
    assert res["criteria"]["c5_seed_jaccard"] is False


def test_gate_fails_on_no_mae_improvement():
    folds = [2021, 2022, 2023, 2024, 2025]
    agg = _passing_agg(folds)
    for f in folds:
        agg["C5_dual"]["by_fold"][str(f)]["mae"] = 0.70  # equal to no-graph
    agg["C5_dual"]["overall"]["mae"] = 0.70
    res = apply_gate(agg, folds)
    assert res["criteria"]["c1_mae_improve"] is False
    assert res["decision"] == "DUAL_GRAPH_S1_FAIL"


def test_gate_fail_closed_on_missing_data():
    folds = [2021, 2022, 2023, 2024, 2025]
    res = apply_gate({}, folds)   # nothing present
    assert res["decision"] == "DUAL_GRAPH_S1_FAIL"
    assert not any(res["criteria"].values())


def test_gate_uses_corrected_nulls_explicitly():
    """Criterion 4 must reference the corrected C7/C8 nulls and a registered
    metric/direction — nothing implicit."""
    folds = [2021, 2022, 2023, 2024, 2025]
    res = apply_gate(_passing_agg(folds), folds)
    roles = res["control_roles"]
    assert roles["territory_null"] == "C7_territory_graph_perm"
    assert roles["sector_null"] == "C8_sector_identity_perm"
    assert res["criterion4_metric"] == "primary_regression_mae"
    assert res["criterion4_direction"] == "lower_is_better"


def test_gate_fails_on_weak_null_controls():
    """Weak null: when C7/C8 are as good as the dual model, criterion 4 fails —
    the graph carries no signal beyond a destroyed-structure baseline."""
    folds = [2021, 2022, 2023, 2024, 2025]
    agg = _passing_agg(folds)
    for f in folds:
        agg["C7_territory_graph_perm"]["by_fold"][str(f)]["mae"] = 0.50
        agg["C8_sector_identity_perm"]["by_fold"][str(f)]["mae"] = 0.50
    res = apply_gate(agg, folds)
    assert res["criteria"]["c4_graph_beats_nulls_folds"] is False
    assert res["decision"] == "DUAL_GRAPH_S1_FAIL"


def test_gate_passes_with_strong_null_controls():
    """Strong null: when the dual model clearly beats C7/C8 in every fold,
    criterion 4 passes (other criteria already satisfied in the fixture)."""
    folds = [2021, 2022, 2023, 2024, 2025]
    res = apply_gate(_passing_agg(folds), folds)
    assert res["criteria"]["c4_graph_beats_nulls_folds"] is True


# ---------------------------------------------------------------------------
# Atomic writes and unique outputs
# ---------------------------------------------------------------------------

def test_atomic_write_json_roundtrip(tmp_path):
    p = tmp_path / "sub" / "out.json"
    payload = {"a": np.int64(3), "b": np.float32(1.5), "c": np.array([1, 2])}
    atomic_write_json(p, payload)
    assert p.exists()
    loaded = json.loads(p.read_text())
    assert loaded == {"a": 3, "b": 1.5, "c": [1, 2]}
    # no leftover temp files
    assert not list(p.parent.glob("*.tmp"))


def test_atomic_write_overwrites_cleanly(tmp_path):
    p = tmp_path / "out.json"
    atomic_write_json(p, {"v": 1})
    atomic_write_json(p, {"v": 2})
    assert json.loads(p.read_text()) == {"v": 2}


# ---------------------------------------------------------------------------
# NaN/Inf handled fail-closed in aggregation + a real end-to-end mini-run
# ---------------------------------------------------------------------------

def test_aggregate_skips_non_ok_runs():
    results = [
        {"control": "C5_dual", "eval_year": 2021, "status": "nonfinite_train",
         "metrics": {}},
        {"control": "C5_dual", "eval_year": 2021, "status": "ok",
         "metrics": {"regression": {"mae": 0.5}}, "learned_graph": {"edges": [(0, 1)]}},
    ]
    agg = aggregate(results, ["C5_dual"], [2021])
    # only the ok run contributes
    assert agg["C5_dual"]["by_fold"]["2021"]["mae"] == 0.5
    assert agg["C5_dual"]["by_fold"]["2021"]["n_seeds"] == 1


def test_evaluate_run_baselines_and_neural_end_to_end():
    fold = _synth_fold(seed=11)
    fold_t = _to_tensor_fold(fold)
    split = temporal_split(fold)
    for control in ("C0_persistence", "C1_ridge", "C2_no_graph", "C5_dual"):
        res = evaluate_run(fold_t, fold, control, 42, split["outer_year"],
                           split, FAST_HP)
        assert res["status"] == "ok"
        reg = res["metrics"]["regression"]
        assert reg["mae"] is not None and np.isfinite(reg["mae"])


# ---------------------------------------------------------------------------
# No dependency on old L1 / ZE2020
# ---------------------------------------------------------------------------

def test_no_legacy_graph_dependency_in_source():
    """No legacy artifact is referenced in *code* (string literals), only the
    dual_graph_tensors npz folds. Docstrings may mention them in prose."""
    import ast

    tree = ast.parse(Path(T.__file__).read_text())
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    literals = [
        n.value.lower() for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and n.value not in docstrings
    ]
    forbidden = ("g1_l1", "ze2020", "g1_l2_edges", "edges.csv", ".geojson")
    for lit in literals:
        for bad in forbidden:
            assert bad not in lit, f"trainer code references forbidden artifact: {lit}"
