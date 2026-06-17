"""
Tests for DEC-066: Phase 7 fine-grain threshold calibration.

Gates C1-C10 are checked here plus structural invariants.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

# ── Paths
CANDIDATES = Path("data/processed/phase7_threshold_calibration/phase7_threshold_candidates.csv")
SENSITIVITY = Path("data/processed/phase7_threshold_calibration/threshold_sensitivity_summary.json")
POLICY = Path("data/processed/phase7_threshold_calibration/fine_grain_label_policy.json")
FR_EDGES = Path("data/processed/sector_precedence_results/all_edges.csv")
PT_MUNI_EDGES = Path("data/processed/phase7_pt_municipal/results/all_edges.csv")

ORIGINAL_THRESHOLD = 0.10
FINE_GRAIN_THRESHOLD = 0.09
FDR_Q = 0.05

ALL_LABELS = {"ROBUST_ORIGINAL", "FINE_GRAIN_SUPPORTED", "EXPLORATORY_FINE_GRAIN", "REJECTED_OR_WEAK"}
VALID_COUNTRIES = {"FR", "NL", "PT_NUTS3", "PT_MUNI"}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def candidates() -> pd.DataFrame:
    return pd.read_csv(CANDIDATES)


@pytest.fixture(scope="module")
def sensitivity() -> dict:
    return json.loads(SENSITIVITY.read_text())


@pytest.fixture(scope="module")
def policy() -> dict:
    return json.loads(POLICY.read_text())


@pytest.fixture(scope="module")
def fr_edges() -> pd.DataFrame:
    df = pd.read_csv(FR_EDGES)
    return df[df["country"] == "FR"].copy()


@pytest.fixture(scope="module")
def pt_muni_edges() -> pd.DataFrame:
    return pd.read_csv(PT_MUNI_EDGES)


# ─────────────────────────────────────────────────────────────────────────────
# C1: DATA_AVAILABLE
# ─────────────────────────────────────────────────────────────────────────────

class TestC1DataAvailable:
    def test_candidates_file_exists(self):
        assert CANDIDATES.exists(), "phase7_threshold_candidates.csv missing"

    def test_sensitivity_file_exists(self):
        assert SENSITIVITY.exists(), "threshold_sensitivity_summary.json missing"

    def test_policy_file_exists(self):
        assert POLICY.exists(), "fine_grain_label_policy.json missing"

    def test_fr_edges_present(self, candidates):
        assert "FR" in candidates["country"].unique()

    def test_pt_muni_edges_present(self, candidates):
        assert "PT_MUNI" in candidates["country"].unique()

    def test_candidates_not_empty(self, candidates):
        assert len(candidates) > 0

    def test_source_edges_exist(self):
        assert FR_EDGES.exists()
        assert PT_MUNI_EDGES.exists()


# ─────────────────────────────────────────────────────────────────────────────
# C2: SCALE_EFFECT_CONFIRMED
# ─────────────────────────────────────────────────────────────────────────────

class TestC2ScaleEffect:
    def test_scale_evidence_in_sensitivity(self, sensitivity):
        assert "ecological_scale_evidence" in sensitivity

    def test_pt_nuts3_larger_beta_than_pt_muni(self, sensitivity):
        eco = sensitivity["ecological_scale_evidence"]
        assert eco["PT_NUTS3_max_abs_beta"] > eco["PT_MUNI_max_abs_beta"]

    def test_coarser_scale_larger_effects(self, sensitivity):
        eco = sensitivity["ecological_scale_evidence"]
        # PT NUTS3 (25 territories) > NL COROP (40) > FR ZE2020 / PT municipal (280)
        assert eco["PT_NUTS3_max_abs_beta"] > eco["NL_COROP_max_abs_beta"]
        assert eco["NL_COROP_max_abs_beta"] > eco["FR_ZE2020_max_abs_beta"]


# ─────────────────────────────────────────────────────────────────────────────
# C3: FDR_NOT_BINDING
# ─────────────────────────────────────────────────────────────────────────────

class TestC3FDRNotBinding:
    def test_fr_near_misses_blocked_by_beta_not_q(self, fr_edges):
        """FR edges with |β|∈[0.07,0.10) and q_fdr<0.05 should have β as the binding gate."""
        main = fr_edges[fr_edges["scenario"] == "main"].copy()
        near_misses = main[
            (main["q_fdr"] < FDR_Q)
            & (main["beta"].abs() >= 0.07)
            & (main["beta"].abs() < ORIGINAL_THRESHOLD)
            & (main["delta_r2"] >= 0.005)
            & (main["bootstrap_sign_stability"] >= 0.70)
            & (main["n_samples"] >= 60)
        ]
        # There must be at least one near-miss (FR MN→BE etc.)
        assert len(near_misses) > 0, "Expected FR near-misses blocked only by |β|<0.10"
        # All should have q_fdr<0.05 (q_fdr is not the blocker)
        assert (near_misses["q_fdr"] < FDR_Q).all()


# ─────────────────────────────────────────────────────────────────────────────
# C4: THRESHOLD_009_STABILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestC4ThresholdStability:
    def test_fine_grain_edges_have_high_bss(self, candidates):
        fg = candidates[candidates["label"] == "FINE_GRAIN_SUPPORTED"]
        if len(fg) > 0:
            assert (fg["bootstrap_sign_stability"] >= 0.80).all(), \
                "FINE_GRAIN_SUPPORTED edges must have bss>=0.80"

    def test_fine_grain_edges_have_q_fdr(self, candidates):
        fg = candidates[candidates["label"] == "FINE_GRAIN_SUPPORTED"]
        if len(fg) > 0:
            assert (fg["q_fdr"] < FDR_Q).all()

    def test_fine_grain_edges_have_min_beta(self, candidates):
        fg = candidates[candidates["label"] == "FINE_GRAIN_SUPPORTED"]
        if len(fg) > 0:
            assert (fg["abs_beta"] >= FINE_GRAIN_THRESHOLD).all()

    def test_robust_original_unchanged_at_010(self, candidates):
        """All ROBUST_ORIGINAL must have |β|≥0.10."""
        ro = candidates[candidates["label"] == "ROBUST_ORIGINAL"]
        assert (ro["abs_beta"] >= ORIGINAL_THRESHOLD).all()


# ─────────────────────────────────────────────────────────────────────────────
# C5: NO_THRESHOLD_OVERFITTING
# ─────────────────────────────────────────────────────────────────────────────

class TestC5NoThresholdOverfitting:
    def test_policy_prohibitions_present(self, policy):
        prohibitions = policy.get("prohibitions", [])
        # Must explicitly forbid NL proxy
        proxy_forbidden = any("proxy" in p.lower() or "gemeente" in p.lower() for p in prohibitions)
        assert proxy_forbidden, "Policy must explicitly forbid NL proxy data in threshold selection"

    def test_no_nl_proxy_in_candidates(self, candidates):
        assert "NL_GEMEENTE" not in candidates["country"].unique(), \
            "NL gemeente proxy must not appear in calibration candidates"

    def test_policy_forbids_future_labels(self, policy):
        prohibitions = policy.get("prohibitions", [])
        future_forbidden = any("future" in p.lower() or "post-training" in p.lower() for p in prohibitions)
        assert future_forbidden, "Policy must forbid using future/post-training labels as condition"

    def test_calibration_uses_only_fr_pt_observed(self, candidates):
        allowed = {"FR", "NL", "PT_NUTS3", "PT_MUNI"}
        actual = set(candidates["country"].unique())
        disallowed = actual - allowed
        assert not disallowed, f"Calibration uses disallowed data sources: {disallowed}"


# ─────────────────────────────────────────────────────────────────────────────
# C6: CROSS_COUNTRY_REASONABLE
# ─────────────────────────────────────────────────────────────────────────────

class TestC6CrossCountryReasonable:
    def test_no_single_country_dominates_fine_grain(self, candidates):
        """No single country should represent >80% of FINE_GRAIN_SUPPORTED edges."""
        fg = candidates[candidates["label"] == "FINE_GRAIN_SUPPORTED"]
        if len(fg) >= 4:
            for country in fg["country"].unique():
                share = (fg["country"] == country).mean()
                assert share <= 0.80, \
                    f"{country} has {share:.0%} of FINE_GRAIN_SUPPORTED edges (>80%)"

    def test_nl_and_pt_nuts3_unaffected(self, candidates):
        """NL and PT_NUTS3 have no edges below 0.10 — threshold change doesn't touch them."""
        nl = candidates[candidates["country"] == "NL"]
        pt_n3 = candidates[candidates["country"] == "PT_NUTS3"]
        assert (nl["abs_beta"] >= ORIGINAL_THRESHOLD).all(), "NL has edges below 0.10"
        assert (pt_n3["abs_beta"] >= ORIGINAL_THRESHOLD).all(), "PT_NUTS3 has edges below 0.10"


# ─────────────────────────────────────────────────────────────────────────────
# C7: ROBUST_LABEL_POLICY
# ─────────────────────────────────────────────────────────────────────────────

class TestC7RobustLabelPolicy:
    def test_policy_has_all_four_labels(self, policy):
        labels = set(policy["labels"].keys())
        assert labels == ALL_LABELS

    def test_policy_specifies_use_in_training(self, policy):
        for label, spec in policy["labels"].items():
            assert "use_in_training" in spec, f"{label} missing use_in_training"

    def test_robust_original_use_in_training_true(self, policy):
        assert policy["labels"]["ROBUST_ORIGINAL"]["use_in_training"] is True

    def test_exploratory_not_used_in_training(self, policy):
        assert policy["labels"]["EXPLORATORY_FINE_GRAIN"]["use_in_training"] is False

    def test_rejected_not_used_in_training(self, policy):
        assert policy["labels"]["REJECTED_OR_WEAK"]["use_in_training"] is False


# ─────────────────────────────────────────────────────────────────────────────
# C8: COVID_POLICY
# ─────────────────────────────────────────────────────────────────────────────

class TestC8CovidPolicy:
    def test_pt_muni_promoted_are_covid_robust(self, candidates):
        """PT Municipal ROBUST_ORIGINAL edges must be COVID-robust."""
        pt_ro = candidates[
            (candidates["country"] == "PT_MUNI")
            & (candidates["label"] == "ROBUST_ORIGINAL")
        ]
        assert len(pt_ro) > 0
        assert pt_ro["covid_robust"].all(), \
            "PT Municipal ROBUST_ORIGINAL edges must be COVID-robust"

    def test_fr_fine_grain_supported_not_required_covid_robust(self, candidates):
        """FINE_GRAIN_SUPPORTED is allowed to be non-covid-robust if cross-window."""
        fr_fg = candidates[
            (candidates["country"] == "FR")
            & (candidates["label"] == "FINE_GRAIN_SUPPORTED")
        ]
        # Some FR FINE_GRAIN_SUPPORTED may lack covid_robust (cross-window condition used instead)
        # This is allowed — just verify they have n_windows>=2
        if not fr_fg["covid_robust"].all():
            non_robust = fr_fg[~fr_fg["covid_robust"]]
            assert (non_robust["n_windows_at_009"] >= 2).all(), \
                "FR FINE_GRAIN_SUPPORTED without covid_robust must have n_windows_at_009>=2"


# ─────────────────────────────────────────────────────────────────────────────
# C9: NO_CAUSAL_LANGUAGE
# ─────────────────────────────────────────────────────────────────────────────

class TestC9NoCausalLanguage:
    CAUSAL_TERMS = ["causes", "drives", "leads to", "induces", "results in",
                    "provoca", "causa ", "determines", "causal"]

    def test_policy_no_causal_language(self, policy):
        text = json.dumps(policy).lower()
        for term in self.CAUSAL_TERMS:
            assert term not in text, f"Causal term '{term}' found in policy JSON"

    def test_sensitivity_no_causal_language(self, sensitivity):
        text = json.dumps(sensitivity).lower()
        for term in self.CAUSAL_TERMS:
            assert term not in text, f"Causal term '{term}' found in sensitivity JSON"


# ─────────────────────────────────────────────────────────────────────────────
# C10: REPRODUCIBILITY
# ─────────────────────────────────────────────────────────────────────────────

class TestC10Reproducibility:
    def test_policy_has_dec_field(self, policy):
        assert policy.get("dec") == "DEC-066"

    def test_policy_has_schema_version(self, policy):
        assert "schema_version" in policy

    def test_sensitivity_has_recommended_threshold(self, sensitivity):
        assert "recommended_threshold" in sensitivity

    def test_valid_json_files(self):
        for path in [SENSITIVITY, POLICY]:
            data = json.loads(path.read_text())
            assert isinstance(data, dict)

    def test_candidates_no_nan_in_key_columns(self, candidates):
        key_cols = ["abs_beta", "q_fdr", "bootstrap_sign_stability", "n_samples", "label"]
        for col in key_cols:
            assert not candidates[col].isnull().any(), f"NaN in {col}"

    def test_candidates_no_inf(self, candidates):
        num_cols = ["abs_beta", "q_fdr", "delta_r2", "bootstrap_sign_stability"]
        for col in num_cols:
            assert not (candidates[col] == float("inf")).any()
            assert not (candidates[col] == float("-inf")).any()


# ─────────────────────────────────────────────────────────────────────────────
# Structural invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestStructuralInvariants:
    def test_labels_mutually_exclusive(self, candidates):
        """Each row has exactly one label."""
        assert candidates["label"].isin(ALL_LABELS).all()

    def test_original_threshold_preserves_dec064_promotions(self, candidates):
        """GI→OQ and MN→JZ (PT Municipal) must be ROBUST_ORIGINAL."""
        pt = candidates[candidates["country"] == "PT_MUNI"]
        for src, tgt in [("GI", "OQ"), ("MN", "JZ")]:
            row = pt[(pt["source_sector"] == src) & (pt["target_sector"] == tgt)]
            assert len(row) > 0, f"{src}→{tgt} not in PT_MUNI candidates"
            assert (row["label"] == "ROBUST_ORIGINAL").all(), \
                f"{src}→{tgt} must be ROBUST_ORIGINAL"

    def test_exploratory_not_treated_as_robust(self, candidates):
        """EXPLORATORY_FINE_GRAIN edges must NOT have |β|≥0.10."""
        exp = candidates[candidates["label"] == "EXPLORATORY_FINE_GRAIN"]
        assert (exp["abs_beta"] < ORIGINAL_THRESHOLD).all(), \
            "EXPLORATORY_FINE_GRAIN edge has |β|>=0.10 — should be ROBUST_ORIGINAL"

    def test_fine_grain_does_not_use_nl_proxy(self, candidates):
        """NL gemeente proxy is not a source for any label."""
        assert "NL_GEMEENTE" not in candidates["country"].values

    def test_threshold_sensitivity_has_all_countries(self, sensitivity):
        for t_key in ["0.1", "0.09", "0.08", "0.07"]:
            assert t_key in sensitivity["thresholds"], f"Threshold {t_key} missing"
            for country in ["FR", "NL", "PT_NUTS3", "PT_MUNI"]:
                assert country in sensitivity["thresholds"][t_key]

    def test_fr_mn_be_cross_window_documented(self, sensitivity):
        assert "fr_mn_be_cross_window" in sensitivity
        info = sensitivity["fr_mn_be_cross_window"]
        assert info["pair"] == "MN→BE"
        assert len(info["windows_at_009"]) >= 2

    def test_kz_fz_caution_documented(self, sensitivity):
        assert "caution_kz_fz" in sensitivity
