"""
DEC-064: Tests for PT Municipal Phase 7 sector precedence.

Covers:
- PT municipal panel schema and content
- n_regions = 278, evidence_type = observed_births
- KZ structural_absent (all NaN, no zeros)
- No NL proxy mixed in
- Config points to correct directories
- Gates pre-registered before results
- Report without causal language
- Smoke output validity
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parents[1]

# Source files
PT_MUNICIPAL_PANEL = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"
PHASE7_PANEL = REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv"
PHASE7_MANIFEST = REPO_ROOT / "data/processed/phase7_pt_municipal/pt_municipal_phase7_panel_manifest.json"
CONFIG_PATH = REPO_ROOT / "hpc/phase7_sector_precedence/configs/pt_municipal_observed.json"
GATES_PATH = REPO_ROOT / "src/modeles/real_world/gates_dec064_pt_municipal_phase7.py"
REPORT_PATH = REPO_ROOT / "reports/HERALD_DEC064_PT_MUNICIPAL_PHASE7_AUDIT.md"
SMOKE_GATES = REPO_ROOT / "data/processed/phase7_pt_municipal/dec064_gates_smoke.json"
FULL_GATES = REPO_ROOT / "data/processed/phase7_pt_municipal/dec064_gates_full.json"

CAUSAL_TERMS = ["causes", "drives", "leads to", "induces", "results in", "provoca", "causa ", "conduit à"]
OBSERVABLE_SECTORS = ["BE", "FZ", "GI", "JZ", "LZ", "MN", "OQ", "RU"]


# =========================================================================
# Class 1: Source PT panel (pt_municipal_sector_panel.csv)
# =========================================================================
class TestPTMunicipalSourcePanel:

    def test_source_panel_exists(self):
        assert PT_MUNICIPAL_PANEL.exists(), "pt_municipal_sector_panel.csv not found"

    def test_n_regions_278(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert df["region_id"].nunique() == 278, f"Expected 278 municipalities, got {df['region_id'].nunique()}"

    def test_country_is_pt(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert (df["country"] == "PT").all()

    def test_region_level_is_municipality(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert (df["region_level"] == "MUNICIPALITY").all()

    def test_kz_all_nan(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert df["sector_KZ"].isna().all(), "sector_KZ should be all NaN (structural_absent)"

    def test_kz_no_zeros(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert not (df["sector_KZ"] == 0).any(), "sector_KZ must not have zeros (structural_absent, not 0)"

    def test_continental_only(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        if "is_continental" in df.columns:
            assert df["is_continental"].eq(True).all()
        if "source_geocod" in df.columns:
            assert df["source_geocod"].astype(str).str[0].eq("1").all()

    def test_observable_sectors_present(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        for s in OBSERVABLE_SECTORS:
            col = f"sector_{s}"
            assert col in df.columns, f"Missing column: {col}"

    def test_observable_sectors_nonull(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        for s in OBSERVABLE_SECTORS:
            col = f"sector_{s}"
            assert df[col].notna().any(), f"All NaN in {col}"

    def test_years_range(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        assert 2008 in df["year"].values
        assert 2023 in df["year"].values

    def test_flag_target_concept(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        if "flag_target_concept" in df.columns:
            assert (df["flag_target_concept"] == "enterprise_birth").all()

    def test_no_proxy_column(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        proxy_cols = [c for c in df.columns if "proxy" in c.lower() or "gemeente" in c.lower()]
        assert proxy_cols == [], f"Unexpected proxy columns: {proxy_cols}"


# =========================================================================
# Class 2: Phase 7 long panel (pt_municipal_phase7_panel.csv)
# =========================================================================
class TestPhase7Panel:

    @pytest.fixture
    def panel(self):
        if not PHASE7_PANEL.exists():
            pytest.skip("Phase 7 panel not built yet")
        return pd.read_csv(PHASE7_PANEL, dtype={"territory_id": str})

    def test_panel_exists(self, panel):
        assert len(panel) > 0

    def test_n_territories_278(self, panel):
        obs = panel[panel["structural_mask"] == 1]
        assert obs["territory_id"].nunique() == 278

    def test_observable_sectors_8(self, panel):
        obs = panel[panel["structural_mask"] == 1]
        assert obs["sector_id"].nunique() == 8

    def test_kz_structural_mask_zero(self, panel):
        kz = panel[panel["sector_id"] == "KZ"]
        assert kz["structural_mask"].eq(0).all()
        assert kz["observation_mask"].eq(0).all()

    def test_velocity_no_future_leakage(self, panel):
        # Verify that year 2008 (first data year) has observation_mask=0
        # because velocity requires lag1 (2007 data not available)
        min_year = int(panel[panel["structural_mask"] == 1]["observation_year"].min())
        min_year_obs = panel[
            (panel["observation_year"] == min_year) & (panel["structural_mask"] == 1)
        ]
        # All rows at min_year must have observation_mask=0 (no lag1 available)
        assert min_year_obs["observation_mask"].eq(0).all(), \
            f"Year {min_year} should have observation_mask=0 (no lag1 available)"

    def test_observation_mask_consistent(self, panel):
        obs = panel[panel["observation_mask"] == 1]
        assert obs["velocity"].notna().all(), "observation_mask=1 rows must have non-NaN velocity"

    def test_country_is_pt(self, panel):
        assert (panel["country"] == "PT").all()

    def test_no_nl_gemeente_data(self, panel):
        assert "estimated_births_gemeente" not in panel.columns
        assert "gm_code" not in panel.columns
        assert "proxy" not in str(list(panel.columns)).lower()

    def test_required_columns(self, panel):
        required = ["country", "territory_id", "observation_year", "sector_id",
                    "velocity", "structural_mask", "observation_mask"]
        for col in required:
            assert col in panel.columns, f"Missing column: {col}"


# =========================================================================
# Class 3: Config validity
# =========================================================================
class TestConfig:

    @pytest.fixture
    def cfg(self):
        assert CONFIG_PATH.exists(), "Config not found"
        return json.loads(CONFIG_PATH.read_text())

    def test_config_exists(self, cfg):
        assert cfg is not None

    def test_points_to_municipal_panel(self, cfg):
        assert "pt_municipal" in cfg["panel"]

    def test_output_dir_separate(self, cfg):
        assert "pt_municipal" in cfg["output_dir"]

    def test_gate_thresholds_pre_registered(self, cfg):
        gates = cfg["gate_thresholds"]
        assert gates["fdr_q"] == 0.05
        assert gates["min_abs_beta"] == 0.10
        assert gates["min_delta_r2"] == 0.005
        assert gates["min_sign_stability"] == 0.70
        assert gates["min_samples"] == 60

    def test_comparison_baseline_documented(self, cfg):
        assert "comparison_baseline" in cfg
        assert cfg["comparison_baseline"]["country"] == "PT"
        assert cfg["comparison_baseline"]["region_system"] == "NUTS3"

    def test_country_is_pt(self, cfg):
        assert cfg["country"] == "PT"

    def test_evidence_type(self, cfg):
        assert cfg["evidence_type"] == "observed_births"


# =========================================================================
# Class 4: Gates module pre-registration
# =========================================================================
class TestGatesPreRegistration:

    def test_gates_module_exists(self):
        assert GATES_PATH.exists()

    def test_gate_version_set(self):
        from src.modeles.real_world.gates_dec064_pt_municipal_phase7 import GATE_VERSION
        assert GATE_VERSION.startswith("DEC-064")

    def test_thresholds_match_original_phase7(self):
        from src.modeles.real_world.gates_dec064_pt_municipal_phase7 import (
            FDR_Q, MIN_ABS_BETA, MIN_DELTA_R2, MIN_SIGN_STABILITY, MIN_SAMPLES
        )
        assert FDR_Q == 0.05
        assert MIN_ABS_BETA == 0.10
        assert MIN_DELTA_R2 == 0.005
        assert MIN_SIGN_STABILITY == 0.70
        assert MIN_SAMPLES == 60

    def test_ten_gates_defined(self):
        from src.modeles.real_world import gates_dec064_pt_municipal_phase7 as gm
        gate_funcs = [name for name in dir(gm) if name.startswith("check_p")]
        assert len(gate_funcs) == 10, f"Expected 10 gate functions, found {len(gate_funcs)}: {gate_funcs}"

    def test_decision_function_exists(self):
        from src.modeles.real_world.gates_dec064_pt_municipal_phase7 import derive_decision_dec064
        assert callable(derive_decision_dec064)

    def test_allowed_decisions(self):
        from src.modeles.real_world.gates_dec064_pt_municipal_phase7 import (
            GateResult, derive_decision_dec064
        )
        # All pass → COMPLETE
        all_pass = [GateResult(f"P{i}", "PASS", None, None, "") for i in range(1, 11)]
        r = derive_decision_dec064(all_pass)
        assert r["decision"] == "PT_MUNICIPAL_PHASE7_COMPLETE"

    def test_critical_fail_blocks(self):
        from src.modeles.real_world.gates_dec064_pt_municipal_phase7 import (
            GateResult, derive_decision_dec064
        )
        gates = [GateResult(f"P{i}", "PASS", None, None, "") for i in range(1, 11)]
        gates[0] = GateResult("P1", "FAIL", None, None, "")  # P1 is critical
        r = derive_decision_dec064(gates)
        assert r["decision"] == "PT_MUNICIPAL_PHASE7_BLOCKED"


# =========================================================================
# Class 5: Evidence separation — no NL proxy mixed in
# =========================================================================
class TestEvidenceSeparation:

    def test_pt_panel_has_no_nl_gemeente_columns(self):
        df = pd.read_csv(PT_MUNICIPAL_PANEL)
        nl_cols = [c for c in df.columns if any(t in c.lower() for t in ["gm_code", "gemeente", "proxy", "corop"])]
        assert nl_cols == []

    def test_config_panel_not_nl_proxy(self):
        cfg = json.loads(CONFIG_PATH.read_text())
        assert "gemeente" not in cfg["panel"]
        assert "proxy" not in cfg["panel"]

    def test_output_dir_different_from_nl(self):
        cfg = json.loads(CONFIG_PATH.read_text())
        assert "nl_gemeente" not in cfg["output_dir"]

    @pytest.mark.skipif(not PHASE7_PANEL.exists(), reason="Phase 7 panel not built")
    def test_phase7_panel_no_nl_rows(self):
        df = pd.read_csv(PHASE7_PANEL)
        assert (df["country"] == "PT").all(), "Phase 7 panel should be PT-only"


# =========================================================================
# Class 6: No causal language
# =========================================================================
class TestNoCausalLanguage:

    def test_config_no_causal(self):
        text = CONFIG_PATH.read_text().lower()
        for term in CAUSAL_TERMS:
            assert term not in text, f"Causal term '{term}' found in config"

    @pytest.mark.skipif(not PHASE7_MANIFEST.exists(), reason="Manifest not built")
    def test_manifest_no_causal(self):
        text = PHASE7_MANIFEST.read_text().lower()
        for term in CAUSAL_TERMS:
            assert term not in text, f"Causal term '{term}' found in manifest"

    @pytest.mark.skipif(not REPORT_PATH.exists(), reason="Report not written yet")
    def test_report_no_causal(self):
        text = REPORT_PATH.read_text().lower()
        for term in CAUSAL_TERMS:
            assert term not in text, f"Causal term '{term}' found in report"


# =========================================================================
# Class 7: Smoke output validity
# =========================================================================
class TestSmokeOutputValidity:

    @pytest.fixture
    def smoke_edges(self):
        p = REPO_ROOT / "data/processed/phase7_pt_municipal/results/all_edges_smoke.csv"
        if not p.exists():
            pytest.skip("Smoke edges not yet generated")
        return pd.read_csv(p)

    @pytest.fixture
    def smoke_gates(self):
        if not SMOKE_GATES.exists():
            pytest.skip("Smoke gates not yet generated")
        return json.loads(SMOKE_GATES.read_text())

    def test_smoke_edges_nonempty(self, smoke_edges):
        assert len(smoke_edges) > 0

    def test_smoke_edges_56_pairs(self, smoke_edges):
        main = smoke_edges[smoke_edges["scenario"] == "main"]
        assert len(main) == 56, f"Expected 56 pairs (8×7), got {len(main)}"

    def test_smoke_n_samples_above_min(self, smoke_edges):
        valid = smoke_edges.dropna(subset=["n_samples"])
        assert (valid["n_samples"] >= 60).all()

    def test_smoke_n_samples_expected_scale(self, smoke_edges):
        valid = smoke_edges.dropna(subset=["n_samples"])
        # 278 muni × 6 years ≈ 1668; allow some dropout for first year NaN
        assert valid["n_samples"].min() >= 200, "Expected >> 60 samples at municipal level"

    def test_smoke_no_all_nan_beta(self, smoke_edges):
        main = smoke_edges[smoke_edges["scenario"] == "main"]
        non_null_beta = main["beta"].notna().sum()
        assert non_null_beta >= 40, f"Too many NaN betas: only {non_null_beta}/56 valid"

    def test_smoke_required_columns(self, smoke_edges):
        required = ["scenario", "country", "window_start", "window_end",
                    "source_sector", "target_sector", "n_samples",
                    "beta", "delta_r2", "p_perm", "bootstrap_sign_stability", "q_fdr",
                    "promoted_exploratory_edge"]
        for col in required:
            assert col in smoke_edges.columns, f"Missing column: {col}"

    def test_smoke_country_is_pt(self, smoke_edges):
        assert (smoke_edges["country"] == "PT").all()

    def test_smoke_gates_structure(self, smoke_gates):
        assert "decision" in smoke_gates
        assert "n_pass" in smoke_gates
        assert "gates" in smoke_gates
        assert len(smoke_gates["gates"]) == 10

    def test_smoke_gates_p2_passes(self, smoke_gates):
        gates = {g["gate_id"]: g["verdict"] for g in smoke_gates["gates"]}
        assert gates.get("P2") == "PASS", "P2 (coverage) should pass"

    def test_smoke_gates_p3_passes(self, smoke_gates):
        gates = {g["gate_id"]: g["verdict"] for g in smoke_gates["gates"]}
        assert gates.get("P3") == "PASS", "P3 (observed only) should pass"


# =========================================================================
# Class 8: Full run output validity (if available)
# =========================================================================
class TestFullRunOutput:

    @pytest.fixture
    def full_edges(self):
        p = REPO_ROOT / "data/processed/phase7_pt_municipal/results/all_edges_full.csv"
        if not p.exists():
            pytest.skip("Full run not yet completed")
        return pd.read_csv(p)

    @pytest.fixture
    def full_gates(self):
        if not FULL_GATES.exists():
            pytest.skip("Full gates not yet generated")
        return json.loads(FULL_GATES.read_text())

    def test_full_run_two_scenarios(self, full_edges):
        scenarios = set(full_edges["scenario"].unique())
        assert "main" in scenarios
        assert "without_2020" in scenarios

    def test_full_run_multiple_windows(self, full_edges):
        main_windows = full_edges[full_edges["scenario"] == "main"][["window_start", "window_end"]].drop_duplicates()
        assert len(main_windows) >= 5, f"Expected ≥5 windows for main scenario, got {len(main_windows)}"

    def test_full_run_kz_not_in_results(self, full_edges):
        assert not (full_edges["source_sector"] == "KZ").any()
        assert not (full_edges["target_sector"] == "KZ").any()

    def test_full_run_n_samples_above_min(self, full_edges):
        valid = full_edges.dropna(subset=["n_samples"])
        assert (valid["n_samples"] >= 60).all()

    def test_full_run_gates_pass(self, full_gates):
        decision = full_gates["decision"]
        assert decision in [
            "PT_MUNICIPAL_PHASE7_COMPLETE",
            "PT_MUNICIPAL_PHASE7_READY_FOR_HPC",
        ], f"Unexpected decision: {decision}"

    def test_full_run_promoted_edges_documented(self, full_edges):
        assert "promoted_exploratory_edge" in full_edges.columns

    def test_full_run_q_fdr_applied(self, full_edges):
        assert "q_fdr" in full_edges.columns
        valid = full_edges.dropna(subset=["p_perm"])
        assert valid["q_fdr"].notna().any(), "q_fdr should be applied for valid pairs"

    def test_full_run_no_causal_in_columns(self, full_edges):
        for col in full_edges.columns:
            for term in CAUSAL_TERMS:
                assert term not in col.lower(), f"Causal term '{term}' in column name '{col}'"
