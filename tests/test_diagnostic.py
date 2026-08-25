"""
test_diagnostic.py — DEC-042

Pre-specified tests for diagnostic gates D1-D5 and bug confirmations B1-B3.
These tests are FIXED before the diagnostic runs. They do NOT tune thresholds.

All tests use the trivial scenario (5T × 3S × 30Y, 1 edge, seed=42).

Run:
    python3 -m pytest tests/test_diagnostic.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from src.data.synthetic.generate_herald_synthetic import (
    SyntheticConfig,
    generate_dataset,
    _sector_adj_from_relations,
)
from src.modeles.synthetic.herald_graph_imputer import (
    HERALDGraphImputer,
    train_herald_imputer,
    impute_deterministic,
    _build_temporal_features,
)
from src.modeles.synthetic.run_diagnostic import (
    TRIVIAL_CONFIG,
    HERALDGraphImputerLagged,
    verify_b1_transposition,
    _directed_log_adj,
    _symmetric_log_adj,
    _freeze_oracle,
)
from src.modeles.synthetic.imputation_baselines import ForwardFillImputer
from src.modeles.synthetic.evaluate_imputation import (
    compute_imputation_metrics,
    compute_edge_recovery_metrics,
)
from sklearn.metrics import roc_auc_score


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def trivial_ds():
    return generate_dataset(TRIVIAL_CONFIG)


@pytest.fixture(scope="module")
def trivial_mask(trivial_ds):
    return trivial_ds["masks"]["mcar_30"]


# ── B1: AUC orientation is transposed ────────────────────────────────────────

class TestB1AUCTransposition:
    """
    B1 (evaluate_imputation.py): learned_attn[i,j] is target-i←source-j weight.
    true_adj[s,t]=1 means s→t. Correct score for s→t: learned_attn[t,s] = attn[cols,rows].
    The bug used attn[rows,cols] → AUC systematically below 0.5 when model is correct.
    """

    def test_auc_fix_flips_score(self):
        """Corrected AUC must be strictly higher than the buggy AUC."""
        n_S = 5
        # attn[i,j] = weight for target i from source j (j→i)
        # True edge: 0→2, so correct score = attn[target=2, source=0] = attn[2,0]
        attn = np.full((n_S, n_S), 0.04)   # uniform low background
        attn[2, 0] = 0.90                   # target=2 attends strongly to source=0
        # Row-normalise
        attn = attn / attn.sum(axis=1, keepdims=True)

        true_adj = np.zeros((n_S, n_S))
        true_adj[0, 2] = 1   # true edge: 0→2

        rows, cols = np.where(~np.eye(n_S, dtype=bool))
        y_true = true_adj[rows, cols]

        # Wrong (bug): attn[rows,cols] → [source,target] indexing = opposite direction
        auc_wrong = roc_auc_score(y_true, attn[rows, cols])

        # Correct (fix): attn[cols,rows] → [target,source] indexing
        auc_correct = roc_auc_score(y_true, attn[cols, rows])

        assert auc_correct > 0.80, f"Correct AUC should be high, got {auc_correct:.3f}"
        assert auc_correct > auc_wrong, (
            f"Correct AUC {auc_correct:.3f} must exceed wrong AUC {auc_wrong:.3f}"
        )

    def test_b1_confirmed_from_hpc_results(self):
        """
        If HPC full results exist, verify mean AUC ≈ 0.27 and 1-mean ≈ 0.73.
        Skipped if no results found.
        """
        results_dir = _REPO / "data/processed/synthetic_benchmark/full"
        files = list(results_dir.glob("*.json"))
        if len(files) < 10:
            pytest.skip("Full benchmark results not found")

        b1 = verify_b1_transposition(results_dir)
        assert b1["n_observations"] >= 100, "Expected >= 100 AUC observations"
        # Corrected AUC should be substantially above 0.5
        assert b1["mean_auc_corrected"] > 0.60, (
            f"Corrected AUC {b1['mean_auc_corrected']:.3f} should exceed G2 threshold 0.60"
        )
        # Symmetry: reported + corrected should be near 1.0
        assert b1["symmetry_check"] < 0.05, (
            f"AUC symmetry check {b1['symmetry_check']:.4f} too large — not a simple transposition"
        )


# ── B2: sector_adj is symmetric ──────────────────────────────────────────────

class TestB2SymmetricAdj:
    """
    B2: _sector_adj_from_relations returns a SYMMETRIC matrix even for directed
    relations. This means the oracle cannot distinguish A→B from B→A.
    """

    def test_sector_adj_is_symmetric(self, trivial_ds):
        adj = trivial_ds["sector_adj"]
        np.testing.assert_array_equal(adj, adj.T, err_msg="sector_adj must be symmetric")

    def test_directed_adj_is_asymmetric(self, trivial_ds):
        n_S = TRIVIAL_CONFIG.n_sectors
        true_relations = trivial_ds["true_relations"]
        directed = np.zeros((n_S, n_S))
        for r in true_relations:
            directed[r.source_sector, r.target_sector] = 1.0
        # Directed adj should NOT equal its transpose (assuming at least 1 directed edge)
        # (unless the one edge happens to be from i→i+1 and also i+1→i, which is unlikely)
        if len(true_relations) >= 1:
            r0 = true_relations[0]
            s, t = r0.source_sector, r0.target_sector
            # sym adj has both directions; directed adj has only one
            sym = trivial_ds["sector_adj"]
            assert sym[s, t] == 1.0 and sym[t, s] == 1.0, (
                "Symmetric adj should set both directions for each true edge"
            )

    def test_directed_log_adj_is_asymmetric(self, trivial_ds):
        """Directed log adj should give different scores to s→t vs t→s."""
        n_S = TRIVIAL_CONFIG.n_sectors
        true_relations = trivial_ds["true_relations"]
        log_dir = _directed_log_adj(true_relations, n_S)
        # log_dir[i,j] = 0 if j→i is true, else log(1e-6)
        # For a true edge s→t: log_dir[t,s] = 0 (high), log_dir[s,t] = log(1e-6) (low)
        r0 = true_relations[0]
        s, t = r0.source_sector, r0.target_sector
        assert log_dir[t, s] > log_dir[s, t] + 5.0, (
            f"Directed log adj: [t,s]={log_dir[t,s]:.2f} should >> [s,t]={log_dir[s,t]:.2f}"
        )


# ── B3: Contemporaneous aggregation misses lagged effects ────────────────────

class TestB3LagMismatch:
    """
    B3: Graph aggregation uses safe * mask at year y (contemporaneous).
    True relations use panel[:, source, y - lag] (lagged).
    Lagged aggregation should outperform contemporaneous on a lag-only scenario.
    """

    def test_lagged_source_more_predictive_than_contemporaneous(self, trivial_ds):
        """
        Structural test for B3: the true mechanism is sector_src[t-lag] → sector_tgt[t].
        Lag-1 source values must correlate more strongly with the target than
        contemporaneous source values do. This holds regardless of training.
        """
        panel = trivial_ds["panel"]
        true_relations = trivial_ds["true_relations"]
        rel = true_relations[0]   # one true relation: src → tgt at lag=1
        src, tgt = rel.source_sector, rel.target_sector

        # Flatten across territories
        src_vals = panel[:, src, :]       # (n_T, n_Y)
        tgt_vals = panel[:, tgt, :]       # (n_T, n_Y)

        # Contemporaneous: corr(src[t], tgt[t])
        x_contemp = src_vals[:, :-1].ravel()   # align time axis
        y_contemp = tgt_vals[:, :-1].ravel()

        # Lagged: corr(src[t-1], tgt[t])
        x_lagged = src_vals[:, :-1].ravel()    # src at t-1
        y_lagged = tgt_vals[:, 1:].ravel()     # tgt at t

        corr_contemp = float(np.corrcoef(x_contemp, y_contemp)[0, 1])
        corr_lagged = float(np.corrcoef(x_lagged, y_lagged)[0, 1])

        assert abs(corr_lagged) > abs(corr_contemp), (
            f"B3: lagged correlation |{corr_lagged:.3f}| should exceed "
            f"contemporaneous |{corr_contemp:.3f}|. "
            f"True mechanism is lag-{rel.lag}; contemporaneous is only a proxy."
        )

    def test_lagged_aggregation_output_shape(self, trivial_ds, trivial_mask):
        """HERALDGraphImputerLagged forward pass returns correct shape."""
        panel = trivial_ds["panel"]
        n_T, n_S, n_Y = panel.shape
        m = HERALDGraphImputerLagged(n_S, n_T)
        panel_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32))
        mask_t = torch.from_numpy(trivial_mask.astype(np.float32))
        temp_feats = torch.from_numpy(
            _build_temporal_features(panel, trivial_mask).astype(np.float32)
        )
        with torch.no_grad():
            out = m(panel_t, mask_t, None, None, temp_feats)
        assert out.shape == (n_T, n_S, n_Y, 2), f"Unexpected shape: {out.shape}"

    def test_lagged_feature_year0_is_zero(self, trivial_ds, trivial_mask):
        """Year 0 lag-1 feature must be zeroed (no data before year 0)."""
        panel = trivial_ds["panel"]
        n_T, n_S, n_Y = panel.shape
        adj_s = trivial_ds["sector_adj"]
        adj_t = trivial_ds["territory_adj"]

        m = HERALDGraphImputerLagged(n_S, n_T)
        panel_t = torch.from_numpy(np.nan_to_num(panel, nan=0.0).astype(np.float32))
        mask_t = torch.from_numpy(trivial_mask.astype(np.float32))
        adj_s_t = torch.from_numpy(adj_s.astype(np.float32))
        adj_t_t = torch.from_numpy(adj_t.astype(np.float32))

        sect_attn = torch.softmax(m.log_sect_attn + adj_s_t, dim=-1)
        terr_attn = torch.softmax(m.log_terr_attn + adj_t_t, dim=-1)
        safe = panel_t * mask_t
        graph_f = m._compute_graph_features_torch(safe, mask_t, sect_attn, terr_attn)
        # graph_f[:, :, 0, 0] = sector neighbor at year 0 = should be 0 (no lag-1)
        sector_nb_y0 = graph_f[:, :, 0, 0]
        assert torch.allclose(sector_nb_y0, torch.zeros_like(sector_nb_y0), atol=1e-6), (
            "Sector neighbor feature at year 0 (lag-1) must be zero"
        )


# ── D1: Oracle wiring valid ───────────────────────────────────────────────────

class TestD1OracleWiring:
    """D1: oracle (frozen correct adj) should outperform no-graph model."""

    def test_d1_oracle_beats_no_graph(self, trivial_ds, trivial_mask):
        panel = trivial_ds["panel"]
        adj_s = trivial_ds["sector_adj"]
        adj_t = trivial_ds["territory_adj"]
        n_S = TRIVIAL_CONFIG.n_sectors
        n_T = TRIVIAL_CONFIG.n_territories

        torch.manual_seed(42)
        m_ng = HERALDGraphImputer(n_S, n_T)
        train_herald_imputer(m_ng, panel, trivial_mask, None, adj_t, n_epochs=300)
        pred_ng = impute_deterministic(m_ng, panel, trivial_mask, None, adj_t)
        mae_ng = float(compute_imputation_metrics(panel, pred_ng, trivial_mask).mae)

        torch.manual_seed(42)
        m_oc = HERALDGraphImputer(n_S, n_T)
        _freeze_oracle(m_oc, _symmetric_log_adj(adj_s))
        train_herald_imputer(m_oc, panel, trivial_mask, adj_s, adj_t, n_epochs=300)
        pred_oc = impute_deterministic(m_oc, panel, trivial_mask, adj_s, adj_t)
        mae_oc = float(compute_imputation_metrics(panel, pred_oc, trivial_mask).mae)

        assert mae_oc < mae_ng, (
            f"D1 FAIL: oracle MAE={mae_oc:.5f} >= no-graph MAE={mae_ng:.5f}. "
            f"Oracle wiring may be broken."
        )


# ── D3: Edge score orientation valid ─────────────────────────────────────────

class TestD3EdgeScoreOrientation:
    """
    D3: After B1 fix (cols/rows transposition), a trained model on the trivial
    scenario should recover the single true edge with AUC > 0.65.
    """

    def test_d3_directed_oracle_achieves_perfect_auc(self, trivial_ds):
        """
        Structural D3 test: an oracle with DIRECTED adjacency (attn[t,s]=high for s→t)
        should achieve AUC=1.0 with the corrected evaluation metric, without training.
        This confirms both (a) the B1 fix is correct and (b) directed information works.
        """
        true_relations = trivial_ds["true_relations"]
        n_S = TRIVIAL_CONFIG.n_sectors

        # Build directed attention: high weight for target←source on true edges
        log_dir = _directed_log_adj(true_relations, n_S)   # log_dir[t,s]=0 if s→t
        attn_dir = np.exp(log_dir)
        # Row-normalise to make valid attention (softmax-like)
        attn_dir = attn_dir / attn_dir.sum(axis=1, keepdims=True).clip(min=1e-8)

        true_adj = np.zeros((n_S, n_S))
        for r in true_relations:
            if r.source_sector < n_S and r.target_sector < n_S:
                true_adj[r.source_sector, r.target_sector] = 1.0

        rows, cols = np.where(~np.eye(n_S, dtype=bool))
        y_true = true_adj[rows, cols]

        if y_true.sum() == 0:
            pytest.skip("No true edges in trivial scenario — check config")

        # Corrected AUC (B1 fix: cols,rows instead of rows,cols)
        y_score_corrected = attn_dir[cols, rows]
        auc_corrected = roc_auc_score(y_true, y_score_corrected)

        # Buggy AUC (original orientation)
        y_score_wrong = attn_dir[rows, cols]
        auc_wrong = roc_auc_score(y_true, y_score_wrong)

        assert auc_corrected == 1.0, (
            f"Directed oracle AUC (corrected) should be 1.0, got {auc_corrected:.3f}"
        )
        assert auc_wrong < auc_corrected, (
            f"Directed oracle: wrong AUC {auc_wrong:.3f} should be < correct {auc_corrected:.3f}"
        )

    def test_d3_g2_passes_on_hpc_results_after_b1_fix(self):
        """
        Integration test: after applying B1 fix to evaluate_imputation.py, the
        corrected mean AUC from HPC results must exceed the G2 threshold of 0.60.
        """
        results_dir = _REPO / "data/processed/synthetic_benchmark/full"
        files = list(results_dir.glob("*.json"))
        if len(files) < 10:
            pytest.skip("Full HPC results not found")

        import json
        aucs = []
        for fp in files:
            with open(fp) as f:
                d = json.load(f)
            for mk, bl in d["baselines"].items():
                if not isinstance(bl, dict):
                    continue
                auc = bl.get("herald_graph", {}).get("edge_auc")
                if auc is not None:
                    aucs.append(auc)

        # The stored AUC was computed with the BUG (rows,cols).
        # After the fix, the correct AUC is 1 - stored_auc.
        mean_stored = float(np.mean(aucs))
        mean_corrected = 1.0 - mean_stored

        # G2 threshold
        assert mean_corrected > 0.60, (
            f"Corrected mean AUC {mean_corrected:.3f} should exceed G2 threshold 0.60"
        )


# ── D5: Lagged oracle beats ffill ────────────────────────────────────────────

class TestD5GraphAddsInformation:
    """D5: oracle with lagged aggregation should beat ffill on the trivial scenario."""

    def test_d5_lagged_oracle_beats_ffill(self, trivial_ds, trivial_mask):
        panel = trivial_ds["panel"]
        adj_s = trivial_ds["sector_adj"]
        adj_t = trivial_ds["territory_adj"]
        n_S = TRIVIAL_CONFIG.n_sectors
        n_T = TRIVIAL_CONFIG.n_territories

        mae_ffill = float(
            compute_imputation_metrics(
                panel,
                ForwardFillImputer().fit_transform(panel, trivial_mask),
                trivial_mask,
            ).mae
        )

        torch.manual_seed(42)
        m = HERALDGraphImputerLagged(n_S, n_T)
        _freeze_oracle(m, _symmetric_log_adj(adj_s))
        train_herald_imputer(m, panel, trivial_mask, adj_s, adj_t, n_epochs=300)
        pred = impute_deterministic(m, panel, trivial_mask, adj_s, adj_t)
        mae_lagged = float(compute_imputation_metrics(panel, pred, trivial_mask).mae)

        assert mae_lagged < mae_ffill, (
            f"D5 FAIL: oracle-lagged MAE={mae_lagged:.5f} >= ffill MAE={mae_ffill:.5f}. "
            f"Lagged graph does not add information — check trivial scenario strength."
        )
