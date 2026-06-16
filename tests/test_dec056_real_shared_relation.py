"""
tests/test_dec056_real_shared_relation.py — DEC-056 validation tests.

Verifies correctness of the real-data pipeline before execution.
No HPC. No pseudo-labels. No causal claims.
"""

from __future__ import annotations

import math
import numpy as np
import pytest
import torch

from src.modeles.synthetic.phase16_decoupled.shared_relation_encoder import (
    SharedRelationEncoder,
    extract_pair_features,
    INPUT_DIM,
)
from src.modeles.synthetic.phase16_decoupled.gates_dec056 import (
    CAUSAL_TERMS,
    scan_for_causal_terms,
    evaluate_all_gates_dec056,
    check_r1_safety,
    check_r2_negative_controls,
    check_r3_temporal_stability,
    check_r4_phase7_concordance,
    check_r5_cross_country_replication,
    check_r6_country_specificity,
    check_r7_covid_sensitivity,
    check_r8_interpretability,
    check_r9_no_causal_overclaim,
    check_r10_dashboard_readiness,
)
from src.modeles.real_world.run_shared_relation_real import (
    SECTOR_CODES,
    SECTOR_COLS,
    PT_ABSENT_SECTORS,
    PRESENCE_THRESHOLD,
    REQUIRED_CSV_COLS,
    build_panel_array,
    normalize_panel,
    compute_stability,
    classify_relations,
    _region_system,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_synthetic_panel(
    n_regions: int = 5,
    n_sectors: int = 9,
    n_years: int = 8,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    panel = rng.random((n_regions, n_sectors, n_years)).astype(np.float32) * 1000
    obs_mask = (rng.random((n_regions, n_sectors, n_years)) > 0.1).astype(np.float32)
    return panel, obs_mask


def _make_mock_panel_df(country: str = "PT"):
    """Create a minimal mock DataFrame matching the panel schema."""
    import pandas as pd
    n_regions = 3
    n_years = 6
    rows = []
    for r in range(n_regions):
        for y, year in enumerate(range(2014, 2014 + n_years)):
            row = {
                "country": country,
                "region_id": f"REG{r:02d}",
                "year": year,
                "mask_sector_a10": 1.0,
                "flag_is_covid_year": int(year == 2020),
            }
            for sc in SECTOR_CODES:
                if country == "PT" and sc == "KZ":
                    row[f"sector_{sc}"] = 0.0
                else:
                    row[f"sector_{sc}"] = float(r * 100 + y * 10 + SECTOR_CODES.index(sc))
            rows.append(row)
    return pd.DataFrame(rows)


# ── Test: No leakage in feature extraction ────────────────────────────────────

class TestNoLeakage:
    def test_window_end_is_exclusive(self):
        """Features at window_end=5 must not use data at index 5."""
        panel, obs_mask = _make_synthetic_panel(n_years=10)
        feat_before = extract_pair_features(panel, obs_mask, 0, 1, window_end=5)
        # Corrupt data at index 5+
        panel_corrupted = panel.copy()
        panel_corrupted[:, :, 5:] = 1e9
        feat_after = extract_pair_features(panel_corrupted, obs_mask, 0, 1, window_end=5)
        assert torch.allclose(feat_before, feat_after, atol=1e-5), \
            "Features depend on post-window data — leakage detected"

    def test_window_size_causal(self):
        """Features must only use data in [window_end - window_size, window_end)."""
        panel, obs_mask = _make_synthetic_panel(n_years=12)
        # Corrupt early history (should not affect features with window_size=4, window_end=12)
        panel_c = panel.copy()
        panel_c[:, :, :6] = -999.0
        feat_normal = extract_pair_features(panel, obs_mask, 0, 2, window_end=12, window_size=4)
        feat_corrupted = extract_pair_features(panel_c, obs_mask, 0, 2, window_end=12, window_size=4)
        assert torch.allclose(feat_normal, feat_corrupted, atol=1e-5), \
            "Features include data outside causal window"


# ── Test: PT KZ structural mask ───────────────────────────────────────────────

class TestPTKZMask:
    def test_pt_kz_excluded_from_pairs(self):
        """PT KZ should be excluded in eval_window."""
        df = _make_mock_panel_df("PT")
        panel, obs_mask, regions, years = build_panel_array(df, "PT")
        kz_idx = SECTOR_CODES.index("KZ")
        # PT KZ should have obs_mask = 0 everywhere
        assert obs_mask[:, kz_idx, :].sum() == 0.0, "PT KZ obs_mask not zeroed"

    def test_pt_kz_panel_zero(self):
        """PT KZ panel values should be 0."""
        df = _make_mock_panel_df("PT")
        panel, obs_mask, regions, years = build_panel_array(df, "PT")
        kz_idx = SECTOR_CODES.index("KZ")
        assert panel[:, kz_idx, :].sum() == 0.0, "PT KZ panel not zeroed"

    def test_fr_kz_not_excluded(self):
        """FR KZ should NOT be zeroed."""
        df = _make_mock_panel_df("FR")
        panel, obs_mask, regions, years = build_panel_array(df, "FR")
        kz_idx = SECTOR_CODES.index("KZ")
        assert obs_mask[:, kz_idx, :].sum() > 0.0, "FR KZ incorrectly excluded"


# ── Test: No cross-country pooling ────────────────────────────────────────────

class TestTerritorySeparation:
    def test_panel_build_per_country(self):
        """Each country builds its own panel independently."""
        df_fr = _make_mock_panel_df("FR")
        df_pt = _make_mock_panel_df("PT")
        panel_fr, _, _, _ = build_panel_array(df_fr, "FR")
        panel_pt, _, _, _ = build_panel_array(df_pt, "PT")
        # Different shapes → independent
        assert panel_fr.shape[0] == 3  # n_regions from mock
        assert panel_pt.shape[0] == 3
        # Ensure they are not the same object
        assert panel_fr is not panel_pt


# ── Test: No NaN/Inf in encoder outputs ───────────────────────────────────────

class TestNoNaNInf:
    def test_encoder_output_finite(self):
        """SharedRelationEncoder should produce finite outputs on valid input."""
        encoder = SharedRelationEncoder()
        encoder.eval()
        with torch.no_grad():
            panel, obs_mask = _make_synthetic_panel()
            feat = extract_pair_features(panel, obs_mask, 0, 1, window_end=6)
            out = encoder(feat)
            for k, v in out.items():
                assert torch.isfinite(v).all(), f"Non-finite value in {k}"

    def test_encoder_output_finite_zero_data(self):
        """Zero panel (all sectors absent) should not produce NaN."""
        encoder = SharedRelationEncoder()
        encoder.eval()
        with torch.no_grad():
            panel = np.zeros((5, 9, 8), dtype=np.float32)
            obs_mask = np.zeros((5, 9, 8), dtype=np.float32)
            feat = extract_pair_features(panel, obs_mask, 0, 1, window_end=6)
            out = encoder(feat)
            for k, v in out.items():
                assert torch.isfinite(v).all(), f"NaN/Inf for zero panel in {k}"

    def test_encoder_output_finite_large_values(self):
        """Large but finite input should not cause overflow."""
        encoder = SharedRelationEncoder()
        encoder.eval()
        with torch.no_grad():
            panel = np.ones((5, 9, 8), dtype=np.float32) * 1e6
            obs_mask = np.ones((5, 9, 8), dtype=np.float32)
            feat = extract_pair_features(panel, obs_mask, 0, 1, window_end=6)
            out = encoder(feat)
            for k, v in out.items():
                assert torch.isfinite(v).all(), f"Overflow for large input in {k}"


# ── Test: Permutation controls degrade ────────────────────────────────────────

class TestControlDegradation:
    def test_year_permutation_changes_features(self):
        """Permuting years should change the extracted features."""
        rng = np.random.default_rng(0)
        panel, obs_mask = _make_synthetic_panel(seed=0)
        feat_real = extract_pair_features(panel, obs_mask, 0, 2, window_end=6)

        perm = rng.permutation(panel.shape[2])
        panel_p = panel[:, :, perm]
        obs_mask_p = obs_mask[:, :, perm]
        feat_perm = extract_pair_features(panel_p, obs_mask_p, 0, 2, window_end=6)

        assert not torch.allclose(feat_real, feat_perm, atol=1e-4), \
            "Year permutation did not change features — control not working"


# ── Test: Stability computation ───────────────────────────────────────────────

class TestStabilityComputation:
    def _make_window_records(self) -> dict:
        """Create mock window records with stable scores (>= 5 pairs required by Spearman)."""
        windows = {}
        pairs = [(s, t) for s in SECTOR_CODES[:4] for t in SECTOR_CODES[:4] if s != t]
        for ws in range(2014, 2018):
            recs = []
            for i, (src, tgt) in enumerate(pairs):
                # Score is stable across windows (monotone, no shuffling)
                recs.append({
                    "source_sector": src,
                    "target_sector": tgt,
                    "score_presence": 0.50 + i * 0.02,
                })
            windows[(ws, ws + 6)] = recs
        return windows

    def test_stable_scores_high_spearman(self):
        """Perfectly stable ranking should give Spearman near 1.0."""
        windows = self._make_window_records()
        result = compute_stability(windows)
        mean_stab = result.get("mean", float("nan"))
        assert not math.isnan(mean_stab), "Stability is NaN"
        assert mean_stab > 0.90, f"Expected high stability for stable ranking, got {mean_stab}"

    def test_random_scores_low_spearman(self):
        """Random scores should give low Spearman stability."""
        rng = np.random.default_rng(42)
        pairs = [(s, t) for s in SECTOR_CODES[:4] for t in SECTOR_CODES[:4] if s != t]
        windows = {}
        for ws in range(2014, 2018):
            windows[(ws, ws + 6)] = [
                {"source_sector": src, "target_sector": tgt,
                 "score_presence": float(rng.random())}
                for src, tgt in pairs
            ]
        result = compute_stability(windows)
        mean_stab = result.get("mean", 1.0)
        # Random should be near 0; not asserting below 0 to avoid flakiness
        assert abs(mean_stab) < 0.60, f"Random stability too high: {mean_stab}"


# ── Test: Phase 7 comparison ──────────────────────────────────────────────────

class TestPhase7Comparison:
    def test_concordance_range(self):
        """Gate R4 concordance must be in [0, 1] if computed."""
        from src.modeles.real_world.run_shared_relation_real import compare_phase7
        # compare_phase7 gracefully handles missing file
        result = compare_phase7([], phase7_path="/nonexistent/path.csv")
        # Either NaN (file missing) or a valid concordance
        concordance = result.get("phase7_sign_concordance", float("nan"))
        if not math.isnan(concordance):
            assert 0.0 <= concordance <= 1.0


# ── Test: Classification ──────────────────────────────────────────────────────

class TestClassification:
    def test_replicated_if_two_countries(self):
        """A pair found in 2+ countries → REPLICATED_ASSOCIATION."""
        records = [
            {"country": "FR", "source_sector": "BE", "target_sector": "FZ",
             "score_presence": 0.8, "covid_period": "pre_covid",
             "inferred_sign": "positive", "inferred_lag": 1, "confidence": 0.7,
             "window_start": 2014, "window_end": 2020},
            {"country": "NL", "source_sector": "BE", "target_sector": "FZ",
             "score_presence": 0.75, "covid_period": "pre_covid",
             "inferred_sign": "positive", "inferred_lag": 1, "confidence": 0.6,
             "window_start": 2014, "window_end": 2020},
        ]
        classified = classify_relations(records, presence_threshold=0.55)
        statuses = {(c["country"], c["source_sector"], c["target_sector"]): c["validation_status"]
                    for c in classified}
        assert statuses[("FR", "BE", "FZ")] == "REPLICATED_ASSOCIATION"
        assert statuses[("NL", "BE", "FZ")] == "REPLICATED_ASSOCIATION"

    def test_not_supported_if_below_threshold(self):
        """A pair always below threshold → NOT_SUPPORTED."""
        records = [
            {"country": "PT", "source_sector": "GI", "target_sector": "JZ",
             "score_presence": 0.30, "covid_period": "pre_covid",
             "inferred_sign": "negative", "inferred_lag": 2, "confidence": 0.4,
             "window_start": 2014, "window_end": 2020},
        ]
        classified = classify_relations(records, presence_threshold=0.55)
        assert classified[0]["validation_status"] == "NOT_SUPPORTED"

    def test_covid_sensitive(self):
        """Pair only above threshold in COVID windows → COVID_SENSITIVE."""
        records = [
            {"country": "FR", "source_sector": "LZ", "target_sector": "MN",
             "score_presence": 0.70, "covid_period": "covid",
             "inferred_sign": "negative", "inferred_lag": 1, "confidence": 0.5,
             "window_start": 2015, "window_end": 2021},
            {"country": "FR", "source_sector": "LZ", "target_sector": "MN",
             "score_presence": 0.30, "covid_period": "pre_covid",
             "inferred_sign": "negative", "inferred_lag": 1, "confidence": 0.5,
             "window_start": 2012, "window_end": 2018},
        ]
        classified = classify_relations(records, presence_threshold=0.55)
        lz_mn = [c for c in classified if c["source_sector"] == "LZ" and c["country"] == "FR"]
        assert len(lz_mn) == 1
        assert lz_mn[0]["validation_status"] == "COVID_SENSITIVE"


# ── Test: CSV schema ──────────────────────────────────────────────────────────

class TestCSVSchema:
    def test_required_columns_defined(self):
        """REQUIRED_CSV_COLS must include all mandatory fields."""
        required_fields = [
            "country", "region_system", "window_start", "window_end",
            "source_sector", "target_sector", "score_presence", "score_sign",
            "score_lag1", "score_lag2", "inferred_lag", "inferred_sign",
            "confidence", "stability", "covid_period", "validation_status",
            "provenance", "claim_scope",
        ]
        for f in required_fields:
            assert f in REQUIRED_CSV_COLS, f"Missing required column: {f}"


# ── Test: No causal terms ─────────────────────────────────────────────────────

class TestNoCausalTerms:
    def test_clean_text_passes(self):
        """Text with no causal terms → empty list."""
        text = "Association score between sector A and sector B was found to be 0.7."
        found = scan_for_causal_terms(text)
        assert found == [], f"False positive causal terms: {found}"

    def test_causal_text_fails(self):
        """Text with 'causes' → detected."""
        text = "Sector A causes sector B growth."
        found = scan_for_causal_terms(text)
        assert "causes" in found

    def test_analytic_claim_scope_clean(self):
        """claim_scope field values must not contain causal terms."""
        claim = "analytic_association_only"
        found = scan_for_causal_terms(claim)
        assert found == [], f"claim_scope contains causal term: {found}"

    @pytest.mark.parametrize("term", CAUSAL_TERMS)
    def test_all_causal_terms_detected(self, term: str):
        """Every term in CAUSAL_TERMS should be detected."""
        found = scan_for_causal_terms(f"This {term} something")
        assert term in found or term.lower() in [f.lower() for f in found]


# ── Test: Determinism ─────────────────────────────────────────────────────────

class TestDeterminism:
    def test_encoder_deterministic(self):
        """Encoder eval mode is deterministic (no dropout)."""
        encoder = SharedRelationEncoder()
        encoder.eval()
        panel, obs_mask = _make_synthetic_panel(seed=99)
        with torch.no_grad():
            feat = extract_pair_features(panel, obs_mask, 1, 3, window_end=7)
            out1 = encoder(feat)
            out2 = encoder(feat)
        assert torch.allclose(out1["presence_logit"], out2["presence_logit"])

    def test_feature_extraction_deterministic(self):
        """Feature extraction is purely deterministic."""
        panel, obs_mask = _make_synthetic_panel(seed=1)
        f1 = extract_pair_features(panel, obs_mask, 0, 4, window_end=6)
        f2 = extract_pair_features(panel, obs_mask, 0, 4, window_end=6)
        assert torch.allclose(f1, f2)


# ── Test: DEC-056 gates on mock data ─────────────────────────────────────────

class TestGatesDEC056:
    def _base_gate_input(self) -> dict:
        return {
            "leakage_check": True,
            "nan_count": 0,
            "inf_count": 0,
            "cross_country_pooling": False,
            "pt_kz_excluded": True,
            "real_presence_logit_mean": 0.60,
            "control_presence_logit_means": {
                "permuted_years": 0.40,
                "permuted_sectors": 0.45,
                "permuted_regions": 0.52,
            },
            "stability_by_country": {"FR": 0.55, "NL": 0.40, "PT": 0.25},
            "phase7_sign_concordance": 0.65,
            "phase7_n_compared": 10,
            "phase7_pairs_compared": [
                {"country": "FR", "pair": "BE→FZ", "agree": True,
                 "p7_sign": "positive", "enc_sign": "positive"}
            ],
            "replicated_pairs": ["BE→FZ", "GI→JZ"],
            "presence_threshold": 0.55,
            "replication_note": "test",
            "country_specific_pairs": {
                "FR": ["LZ→MN"],
                "NL": [],
                "PT": [],
            },
            "covid_windows_reported_separately": True,
            "pre_covid_stability_mean": 0.45,
            "covid_stability_mean": 0.30,
            "post_covid_stability_mean": float("nan"),
            "top_pairs_documented": [
                {
                    "country": "FR",
                    "source_sector": "BE",
                    "target_sector": "FZ",
                    "score_presence": 0.80,
                    "score_sign": 0.70,
                    "inferred_lag": 1,
                    "inferred_sign": "positive",
                    "confidence": 0.75,
                    "window_start": 2014,
                    "window_end": 2020,
                    "validation_status": "REPLICATED_ASSOCIATION",
                }
            ],
            "causal_terms_found": [],
            "csv_schema_valid": True,
            "json_schema_valid": True,
            "required_csv_cols_present": True,
        }

    def test_r1_passes_clean_input(self):
        gates = evaluate_all_gates_dec056(self._base_gate_input())
        assert gates["R1"].verdict == "PASS"

    def test_r1_fails_on_nan(self):
        inp = {**self._base_gate_input(), "nan_count": 5}
        gate = check_r1_safety(inp)
        assert gate.verdict == "FAIL"

    def test_r1_fails_on_pt_kz_not_excluded(self):
        inp = {**self._base_gate_input(), "pt_kz_excluded": False}
        gate = check_r1_safety(inp)
        assert gate.verdict == "FAIL"

    def test_r2_passes_when_controls_degrade(self):
        gate = check_r2_negative_controls(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r2_not_evaluated_when_no_controls(self):
        inp = {**self._base_gate_input(), "control_presence_logit_means": {}}
        gate = check_r2_negative_controls(inp)
        assert gate.verdict == "NOT_EVALUATED"

    def test_r3_passes_two_countries_stable(self):
        gate = check_r3_temporal_stability(self._base_gate_input())
        assert gate.verdict == "PASS"  # FR=0.55, NL=0.40 > 0.30

    def test_r3_fails_zero_stable_countries(self):
        inp = {**self._base_gate_input(), "stability_by_country": {"FR": 0.10, "NL": 0.20, "PT": 0.15}}
        gate = check_r3_temporal_stability(inp)
        assert gate.verdict == "FAIL"

    def test_r4_passes_concordance_above_half(self):
        gate = check_r4_phase7_concordance(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r4_not_evaluated_no_comparison(self):
        inp = {**self._base_gate_input(), "phase7_n_compared": 0}
        gate = check_r4_phase7_concordance(inp)
        assert gate.verdict == "NOT_EVALUATED"

    def test_r5_passes_with_replicated_pairs(self):
        gate = check_r5_cross_country_replication(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r5_fails_no_replicated_pairs(self):
        inp = {**self._base_gate_input(), "replicated_pairs": []}
        gate = check_r5_cross_country_replication(inp)
        assert gate.verdict == "FAIL"

    def test_r6_passes_country_specific_found(self):
        gate = check_r6_country_specificity(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r7_passes_when_reported_separately(self):
        gate = check_r7_covid_sensitivity(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r8_passes_all_fields_present(self):
        gate = check_r8_interpretability(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r9_passes_no_causal_terms(self):
        gate = check_r9_no_causal_overclaim(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r9_fails_with_causal_term(self):
        inp = {**self._base_gate_input(), "causal_terms_found": ["causes"]}
        gate = check_r9_no_causal_overclaim(inp)
        assert gate.verdict == "FAIL"

    def test_r10_passes_valid_schema(self):
        gate = check_r10_dashboard_readiness(self._base_gate_input())
        assert gate.verdict == "PASS"

    def test_r10_fails_invalid_csv(self):
        inp = {**self._base_gate_input(), "csv_schema_valid": False, "required_csv_cols_present": False}
        gate = check_r10_dashboard_readiness(inp)
        assert gate.verdict == "FAIL"

    def test_all_gates_evaluated(self):
        """All 10 gates R1-R10 must be evaluated."""
        gates = evaluate_all_gates_dec056(self._base_gate_input())
        assert set(gates.keys()) == {f"R{i}" for i in range(1, 11)}


# ── Test: Normalization ───────────────────────────────────────────────────────

class TestNormalization:
    def test_normalized_no_nan(self):
        """Normalization should not produce NaN."""
        panel, obs_mask = _make_synthetic_panel()
        norm = normalize_panel(panel, obs_mask, 0, 6)
        assert not np.any(np.isnan(norm))

    def test_normalized_clipped(self):
        """Normalized values should be in [-5, 5]."""
        panel, obs_mask = _make_synthetic_panel()
        norm = normalize_panel(panel, obs_mask, 0, 6)
        assert norm.max() <= 5.0 + 1e-6
        assert norm.min() >= -5.0 - 1e-6

    def test_normalized_zeros_where_missing(self):
        """Missing observations should be zeroed after normalization."""
        panel, obs_mask = _make_synthetic_panel()
        obs_mask[0, 0, :] = 0.0   # region 0, sector 0 always missing
        norm = normalize_panel(panel, obs_mask, 0, 6)
        assert (norm[0, 0, :] == 0.0).all(), "Missing region-sector not zeroed after normalization"


# ── Test: Region system labels ────────────────────────────────────────────────

class TestRegionSystem:
    def test_region_system_known_countries(self):
        assert _region_system("FR") == "ZE2020"
        assert _region_system("NL") == "COROP"
        assert _region_system("PT") == "NUTS3"

    def test_region_system_unknown(self):
        assert _region_system("XX") == "UNKNOWN"


# ── Tests: Checkpoint requirement (DEC-056 correction) ───────────────────────

import hashlib
import json
import tempfile
from pathlib import Path

from src.modeles.real_world.run_p0_checkpointed import (
    load_trained_encoder,
    is_encoder_trained,
    _state_dict_hash,
)


class TestCheckpointRequired:
    def test_load_trained_encoder_missing_file(self):
        """load_trained_encoder raises FileNotFoundError for missing checkpoint."""
        with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
            load_trained_encoder("/nonexistent/path/encoder.pt")

    def test_load_trained_encoder_exists(self, tmp_path):
        """load_trained_encoder loads a valid checkpoint and returns encoder + hash."""
        encoder = SharedRelationEncoder()
        # Simulate trained weights (shift bias)
        with torch.no_grad():
            encoder.head_presence.bias.data.fill_(-1.0)
        ckpt_path = tmp_path / "test_encoder.pt"
        torch.save({
            "model_state_dict": encoder.state_dict(),
            "architecture": {"class": "SharedRelationEncoder"},
            "training": {"best_seed": 1, "best_unseen_pair_auc": 0.70},
            "experiment": "DEC-055",
        }, ckpt_path)
        loaded_enc, h = load_trained_encoder(str(ckpt_path))
        assert h is not None and len(h) == 16
        assert loaded_enc.n_parameters() == encoder.n_parameters()

    def test_hash_mismatch_raises(self, tmp_path):
        """load_trained_encoder raises RuntimeError on hash mismatch."""
        encoder = SharedRelationEncoder()
        with torch.no_grad():
            encoder.head_presence.bias.data.fill_(-0.5)
        ckpt_path = tmp_path / "encoder.pt"
        torch.save({
            "model_state_dict": encoder.state_dict(),
            "architecture": {},
            "training": {},
            "experiment": "DEC-055",
        }, ckpt_path)

        manifest_path = tmp_path / "manifest.json"
        manifest = {"sha256_prefix": "wrong_hash_12345"}
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        with pytest.raises(RuntimeError, match="hash mismatch"):
            load_trained_encoder(str(ckpt_path), str(manifest_path))

    def test_hash_match_succeeds(self, tmp_path):
        """load_trained_encoder succeeds when manifest hash matches checkpoint."""
        encoder = SharedRelationEncoder()
        with torch.no_grad():
            encoder.head_presence.bias.data.fill_(-0.8)
        state = encoder.state_dict()
        expected_hash = _state_dict_hash(state)

        ckpt_path = tmp_path / "encoder.pt"
        torch.save({
            "model_state_dict": state,
            "architecture": {},
            "training": {"best_seed": 2, "best_unseen_pair_auc": 0.72},
            "experiment": "DEC-055",
        }, ckpt_path)

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump({"sha256_prefix": expected_hash}, f)

        loaded, h = load_trained_encoder(str(ckpt_path), str(manifest_path))
        assert h == expected_hash


class TestManifestHasHash:
    def test_manifest_schema(self):
        """Checkpoint manifest must contain sha256_prefix."""
        manifest_path = Path("data/processed/phase16_dec055/checkpoint_manifest.json")
        if not manifest_path.exists():
            pytest.skip("DEC-055 not yet run")
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "sha256_prefix" in manifest, "Manifest missing sha256_prefix"
        h = manifest["sha256_prefix"]
        assert len(h) == 16, f"Hash should be 16 chars, got {len(h)}"

    def test_manifest_has_required_fields(self):
        """Manifest must have training config and gate summary."""
        manifest_path = Path("data/processed/phase16_dec055/checkpoint_manifest.json")
        if not manifest_path.exists():
            pytest.skip("DEC-055 not yet run")
        with open(manifest_path) as f:
            manifest = json.load(f)
        required = ["sha256_prefix", "best_seed", "best_unseen_pair_auc",
                    "n_encoder_params", "architecture", "training", "gate_summary"]
        for field in required:
            assert field in manifest, f"Manifest missing field: {field}"

    def test_manifest_hash_matches_checkpoint(self):
        """Manifest sha256_prefix must match actual checkpoint hash."""
        ckpt_path = Path("data/processed/phase16_dec055/shared_relation_encoder_best.pt")
        manifest_path = Path("data/processed/phase16_dec055/checkpoint_manifest.json")
        if not ckpt_path.exists() or not manifest_path.exists():
            pytest.skip("DEC-055 not yet run")
        ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
        actual_hash = _state_dict_hash(ckpt["model_state_dict"])
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["sha256_prefix"] == actual_hash, \
            f"Hash mismatch: manifest={manifest['sha256_prefix']}, actual={actual_hash}"


class TestCheckpointChangesScoreDistribution:
    """Trained encoder must produce different score distribution than untrained."""

    def test_trained_vs_untrained_mean_presence(self):
        """Trained encoder must shift mean presence away from initialization prior."""
        ckpt_path = Path("data/processed/phase16_dec055/shared_relation_encoder_best.pt")
        if not ckpt_path.exists():
            pytest.skip("DEC-055 not yet run")

        trained_enc, _ = load_trained_encoder(str(ckpt_path))
        untrained_enc = SharedRelationEncoder()  # fresh init, bias=-2.0

        panel, obs_mask = _make_synthetic_panel(seed=42)
        trained_scores = []
        untrained_scores = []
        trained_enc.eval()
        untrained_enc.eval()
        with torch.no_grad():
            for si in range(4):
                for ti in range(4):
                    if si == ti:
                        continue
                    feat = extract_pair_features(panel, obs_mask, si, ti, window_end=6)
                    trained_scores.append(float(torch.sigmoid(trained_enc(feat)["presence_logit"])))
                    untrained_scores.append(float(torch.sigmoid(untrained_enc(feat)["presence_logit"])))

        trained_mean = float(np.mean(trained_scores))
        untrained_mean = float(np.mean(untrained_scores))
        # Trained encoder should differ significantly from untrained prior (~0.067-0.119)
        assert abs(trained_mean - untrained_mean) > 0.05, (
            f"Trained ({trained_mean:.3f}) vs untrained ({untrained_mean:.3f}) "
            "means too similar — checkpoint may not be properly trained"
        )

    def test_trained_encoder_not_at_initialization_prior(self):
        """Trained encoder presence bias should NOT be -2.0 (initialization value)."""
        ckpt_path = Path("data/processed/phase16_dec055/shared_relation_encoder_best.pt")
        if not ckpt_path.exists():
            pytest.skip("DEC-055 not yet run")
        trained_enc, _ = load_trained_encoder(str(ckpt_path))
        bias = trained_enc.head_presence.bias.data.item()
        assert abs(bias - (-2.0)) > 1e-4, \
            f"Presence bias still at initialization (-2.0), encoder was not trained"

    def test_is_encoder_trained_rejects_fresh_init(self):
        """is_encoder_trained should return False for a fresh encoder."""
        fresh = SharedRelationEncoder()
        assert not is_encoder_trained(fresh), "Fresh encoder incorrectly flagged as trained"

    def test_is_encoder_trained_accepts_modified(self):
        """is_encoder_trained should return True after bias modification (simulating training)."""
        enc = SharedRelationEncoder()
        with torch.no_grad():
            enc.head_presence.bias.data.fill_(-0.5)
        assert is_encoder_trained(enc), "Modified encoder not recognized as trained"


class TestP0UsesCorrectCheckpoint:
    """Verify that P0 records contain the correct checkpoint hash."""

    def test_output_records_have_checkpoint_hash(self):
        """P0 output records must include checkpoint_hash field."""
        out_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_scores_checkpointed.csv")
        if not out_path.exists():
            pytest.skip("P0 checkpointed run not yet executed")
        import pandas as pd
        df = pd.read_csv(out_path)
        assert "checkpoint_hash" in df.columns, "Output CSV missing checkpoint_hash column"
        assert df["checkpoint_hash"].notna().all(), "Some records have missing checkpoint_hash"

    def test_output_hash_matches_manifest(self):
        """checkpoint_hash in outputs must match manifest sha256_prefix."""
        out_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_scores_checkpointed.csv")
        manifest_path = Path("data/processed/phase16_dec055/checkpoint_manifest.json")
        if not out_path.exists() or not manifest_path.exists():
            pytest.skip("Files not yet produced")
        import pandas as pd
        df = pd.read_csv(out_path)
        with open(manifest_path) as f:
            manifest = json.load(f)
        expected = manifest["sha256_prefix"]
        hashes = df["checkpoint_hash"].unique().tolist()
        assert len(hashes) == 1, f"Multiple checkpoint hashes in output: {hashes}"
        assert hashes[0] == expected, f"Hash mismatch: output={hashes[0]}, manifest={expected}"

    def test_output_provenance_is_trained(self):
        """Provenance field must say 'trained_shared_encoder_p0', not random init."""
        out_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_scores_checkpointed.csv")
        if not out_path.exists():
            pytest.skip("P0 checkpointed run not yet executed")
        import pandas as pd
        df = pd.read_csv(out_path)
        unique_provenance = df["provenance"].unique().tolist()
        assert "trained_shared_encoder_p0" in unique_provenance, \
            f"Expected trained provenance, got: {unique_provenance}"
        assert "real_observed_association_score" not in unique_provenance, \
            "Old (untrained) provenance found in corrected output"


class TestSeedDeterminism:
    """DEC-055 checkpoint and DEC-056 P0 must be deterministic."""

    def test_state_dict_hash_deterministic(self):
        """Same state dict → same hash."""
        enc = SharedRelationEncoder()
        torch.manual_seed(1)
        with torch.no_grad():
            enc.head_presence.bias.data.fill_(-0.9)
        h1 = _state_dict_hash(enc.state_dict())
        h2 = _state_dict_hash(enc.state_dict())
        assert h1 == h2

    def test_encoder_eval_deterministic_features(self):
        """Same features → same presence logit (no stochastic ops in eval)."""
        ckpt_path = Path("data/processed/phase16_dec055/shared_relation_encoder_best.pt")
        if not ckpt_path.exists():
            pytest.skip("DEC-055 not yet run")
        enc, _ = load_trained_encoder(str(ckpt_path))
        panel, obs_mask = _make_synthetic_panel(seed=7)
        feat = extract_pair_features(panel, obs_mask, 0, 1, window_end=6)
        enc.eval()
        with torch.no_grad():
            o1 = enc(feat)["presence_logit"]
            o2 = enc(feat)["presence_logit"]
        assert torch.allclose(o1, o2)


class TestSchemaNoNaNInf:
    """Validated output files must not contain NaN/Inf in numeric columns."""

    def test_checkpointed_csv_no_nan_presence(self):
        """Presence scores in checkpointed CSV must be finite."""
        out_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_scores_checkpointed.csv")
        if not out_path.exists():
            pytest.skip("P0 checkpointed run not yet executed")
        import pandas as pd
        df = pd.read_csv(out_path)
        assert df["score_presence"].notna().all(), "NaN presence scores in output"
        assert df["score_presence"].apply(lambda x: not math.isinf(x)).all(), \
            "Inf presence scores in output"
        assert (df["score_presence"] >= 0).all() and (df["score_presence"] <= 1).all(), \
            "Presence scores outside [0,1]"

    def test_checkpointed_csv_required_cols(self):
        """Checkpointed output must have all REQUIRED_CSV_COLS."""
        from src.modeles.real_world.run_shared_relation_real import REQUIRED_CSV_COLS
        out_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_scores_checkpointed.csv")
        if not out_path.exists():
            pytest.skip("P0 checkpointed run not yet executed")
        import pandas as pd
        df = pd.read_csv(out_path)
        for col in REQUIRED_CSV_COLS:
            assert col in df.columns, f"Missing required column: {col}"


class TestNoCausalLanguageCheckpointed:
    """Corrected P0 outputs must not contain causal language."""

    def test_trained_provenance_no_causal_terms(self):
        """Provenance values must not contain causal language."""
        causal_terms_in_provenance = scan_for_causal_terms("trained_shared_encoder_p0")
        assert causal_terms_in_provenance == []

    def test_claim_scope_no_causal_terms(self):
        """claim_scope must not contain causal language."""
        assert scan_for_causal_terms("analytic_association_only") == []

    def test_output_validation_json_no_causal(self):
        """Validation JSON decision field must not contain causal terms."""
        val_path = Path("data/processed/real_shared_relations_checkpointed/"
                        "shared_relation_validation_checkpointed.json")
        if not val_path.exists():
            pytest.skip("P0 checkpointed run not yet executed")
        with open(val_path) as f:
            val = json.load(f)
        decision = val.get("decision", "")
        found = scan_for_causal_terms(decision)
        assert found == [], f"Causal terms in decision: {found}"
