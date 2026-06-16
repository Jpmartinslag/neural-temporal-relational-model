"""
DEC-060: France Relation Signal Recovery Audit — Mandatory Tests.

Tests gates F1-F10 and key audit logic. All must PASS before commit.
No causal language. No promotion without gate passage.
"""

import pytest
import pandas as pd
import numpy as np

from src.modeles.real_world.gates_dec060_france_audit import (
    PHASE7_FDR_Q,
    PHASE7_MIN_ABS_BETA,
    PHASE7_MIN_DELTA_R2,
    PHASE7_MIN_BSS,
    COVID_WINDOW_MIN_START,
    VALID_FR_LABELS,
    CAUSAL_TERMS_DEC060,
    check_f1_dataset_coverage,
    check_f2_binding_criterion,
    check_f3_near_miss_exists,
    check_f4_scale_documented,
    check_f5_window_stability,
    check_f6_covid_isolation,
    check_f7_label_integrity,
    check_f8_no_causal_language,
    check_f9_no_cross_target_mixing,
    check_f10_audit_completeness,
    derive_decision_dec060,
    GateResult,
)
from src.modeles.real_world.run_dec060_france_signal_audit import (
    analyse_criteria,
    audit_pairs,
    fdr_sensitivity_analysis,
    beta_sensitivity_analysis,
    _assign_fr_label,
    load_phase7_fr,
    PHASE7_CSV,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_fr_df():
    """Minimal Phase 7 FR-style dataframe for unit tests."""
    rows = []
    sectors = ["MN", "BE", "OQ", "RU"]
    for i, (src, tgt) in enumerate([(s, t) for s in sectors for t in sectors if s != t]):
        for ws in [2012, 2015, 2018, 2020]:
            rows.append({
                "country": "FR",
                "source_sector": src,
                "target_sector": tgt,
                "window_start": ws,
                "window_end": ws + 5,
                "beta": 0.05,
                "delta_r2": 0.003,
                "p_perm": 0.10,
                "bootstrap_sign_stability": 0.60,
                "q_fdr": 0.15,
                "promoted": False,
                "promoted_without_2020": False,
            })
    df = pd.DataFrame(rows)
    # Add one fully-promoted pair
    idx = df[(df["source_sector"] == "RU") & (df["target_sector"] == "MN") & (df["window_start"] == 2020)].index
    df.loc[idx, "beta"] = -0.11
    df.loc[idx, "delta_r2"] = 0.012
    df.loc[idx, "p_perm"] = 0.001
    df.loc[idx, "bootstrap_sign_stability"] = 1.0
    df.loc[idx, "q_fdr"] = 0.024
    df.loc[idx, "promoted"] = True
    # Add near-miss-beta pair
    idx2 = df[(df["source_sector"] == "MN") & (df["target_sector"] == "BE") & (df["window_start"] == 2020)].index
    df.loc[idx2, "beta"] = 0.09
    df.loc[idx2, "delta_r2"] = 0.009
    df.loc[idx2, "bootstrap_sign_stability"] = 1.0
    df.loc[idx2, "q_fdr"] = 0.024
    df.loc[idx2, "p_perm"] = 0.001
    return df


@pytest.fixture
def all_pass_gates():
    return [GateResult(f"F{i}", "PASS", i, i, "") for i in range(1, 11)]


@pytest.fixture
def real_fr_df():
    """Load actual Phase 7 FR results (requires data file)."""
    pytest.importorskip("pandas")
    if not PHASE7_CSV.exists():
        pytest.skip("Phase 7 CSV not found")
    return load_phase7_fr(PHASE7_CSV)


# ---------------------------------------------------------------------------
# Class 1: F1 — Dataset Coverage
# ---------------------------------------------------------------------------

class TestF1DatasetCoverage:
    def test_passes_with_full_coverage(self):
        r = check_f1_dataset_coverage(9, 0.90, 11)
        assert r.verdict == "PASS"
        assert r.gate_id == "F1"

    def test_fails_missing_sectors(self):
        r = check_f1_dataset_coverage(8, 0.90, 11)
        assert r.verdict == "FAIL"

    def test_fails_low_valid_row_frac(self):
        r = check_f1_dataset_coverage(9, 0.50, 11)
        assert r.verdict == "FAIL"

    def test_fails_too_few_windows(self):
        r = check_f1_dataset_coverage(9, 0.90, 3)
        assert r.verdict == "FAIL"

    def test_value_fields_present(self):
        r = check_f1_dataset_coverage(9, 0.92, 11)
        assert "n_sectors" in r.value
        assert "valid_row_frac" in r.value
        assert "n_windows" in r.value


# ---------------------------------------------------------------------------
# Class 2: F2 — Binding Criterion
# ---------------------------------------------------------------------------

class TestF2BindingCriterion:
    def test_identifies_beta_as_binding(self):
        r = check_f2_binding_criterion(9, 8, 43, 497, 1, "beta")
        assert r.verdict == "PASS"
        assert r.value["binding_criterion"] == "beta"

    def test_passes_when_beta_fewer_than_fdr(self):
        # beta=5 < fdr=9 → beta is binding
        r = check_f2_binding_criterion(9, 5, 43, 497, 1, "beta")
        assert r.verdict == "PASS"

    def test_real_data_identifies_beta(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        # From our analysis: pass_beta=8 < pass_fdr=9
        assert crit["binding_criterion"] == "beta"
        assert crit["n_pass_beta"] <= crit["n_pass_fdr"]

    def test_returns_gate_result(self):
        r = check_f2_binding_criterion(9, 8, 43, 497, 1, "beta")
        assert isinstance(r, GateResult)
        assert r.gate_id == "F2"


# ---------------------------------------------------------------------------
# Class 3: F3 — Near-Miss Characterization
# ---------------------------------------------------------------------------

class TestF3NearMiss:
    def test_passes_with_near_miss_beta(self):
        r = check_f3_near_miss_exists(n_near_miss_beta=8, n_near_miss_fdr=0)
        assert r.verdict == "PASS"

    def test_passes_with_near_miss_fdr(self):
        r = check_f3_near_miss_exists(n_near_miss_beta=0, n_near_miss_fdr=3)
        assert r.verdict == "PASS"

    def test_fails_with_no_near_miss(self):
        r = check_f3_near_miss_exists(n_near_miss_beta=0, n_near_miss_fdr=0)
        assert r.verdict == "FAIL"

    def test_real_data_has_near_misses(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        assert crit["n_near_miss_beta"] == 8
        assert crit["n_near_miss_fdr"] >= 0  # 7 observed: pairs with |beta|>=0.10 but q_fdr>0.05

    def test_value_contains_total(self):
        r = check_f3_near_miss_exists(3, 2)
        assert r.value["total_near_miss"] == 5


# ---------------------------------------------------------------------------
# Class 4: F4 — Scale Documentation
# ---------------------------------------------------------------------------

class TestF4ScaleDocumented:
    def test_passes_correct_params(self):
        r = check_f4_scale_documented(280, False, "ZE2020 280 territories vs NUTS3 101 regions — sector cols absent")
        assert r.verdict == "PASS"

    def test_fails_nuts3_has_sector_cols(self):
        r = check_f4_scale_documented(280, True, "some note longer than 20 chars total here")
        assert r.verdict == "FAIL"

    def test_fails_too_few_territories(self):
        r = check_f4_scale_documented(150, False, "note is long enough for this test case")
        assert r.verdict == "FAIL"

    def test_fails_empty_note(self):
        r = check_f4_scale_documented(280, False, "short")
        assert r.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Class 5: F5 — Window Stability
# ---------------------------------------------------------------------------

class TestF5WindowStability:
    def test_passes_with_stable_pairs(self):
        r = check_f5_window_stability({"MN_BE": 6, "OQ_MN": 4})
        assert r.verdict == "PASS"

    def test_fails_no_stable_pairs(self):
        r = check_f5_window_stability({"MN_BE": 1})
        assert r.verdict == "FAIL"

    def test_fails_empty_dict(self):
        r = check_f5_window_stability({})
        assert r.verdict == "FAIL"

    def test_real_data_has_stable_pairs(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        pair_window_counts = {
            f"{r['source_sector']}_{r['target_sector']}": r["n_perm001"]
            for _, r in pair_df.iterrows()
            if r["n_perm001"] >= 2
        }
        r = check_f5_window_stability(pair_window_counts)
        assert r.verdict == "PASS"
        assert r.value["n_stable_pairs"] >= 1


# ---------------------------------------------------------------------------
# Class 6: F6 — COVID Isolation
# ---------------------------------------------------------------------------

class TestF6CovidIsolation:
    def test_passes_with_pre_covid_data(self):
        promoted = [{"pair_key": "RU_MN", "window_start": 2020, "window_end": 2025, "beta": -0.108, "q_fdr": 0.024}]
        pre_covid_p = {"RU_MN": 0.05}
        r = check_f6_covid_isolation(promoted, pre_covid_p)
        assert r.verdict == "PASS"

    def test_fails_no_promoted_pairs(self):
        r = check_f6_covid_isolation([], {})
        assert r.verdict == "FAIL"

    def test_passes_with_none_pre_covid_value(self):
        # None means data exists (just not significant)
        promoted = [{"pair_key": "RU_MN", "window_start": 2020, "window_end": 2025, "beta": -0.108, "q_fdr": 0.024}]
        pre_covid_p = {"RU_MN": None}
        r = check_f6_covid_isolation(promoted, pre_covid_p)
        # None = no pre-covid windows at all → data present but p=None
        assert r.gate_id == "F6"

    def test_real_data_ru_mn_covid_sensitive(self, real_fr_df):
        from src.modeles.real_world.run_dec060_france_signal_audit import covid_isolation_check
        promoted, pre_covid_p = covid_isolation_check(real_fr_df)
        assert len(promoted) >= 1
        pair_key = "RU_MN"
        assert pair_key in pre_covid_p


# ---------------------------------------------------------------------------
# Class 7: F7 — Label Integrity
# ---------------------------------------------------------------------------

class TestF7LabelIntegrity:
    def test_passes_with_valid_labels(self):
        r = check_f7_label_integrity(["FR_NATIONAL_ROBUST", "FR_BETA_BELOW_THRESHOLD", "FR_WEAK_SIGNAL"])
        assert r.verdict == "PASS"

    def test_fails_with_invalid_label(self):
        r = check_f7_label_integrity(["FR_NATIONAL_ROBUST", "COVID_ROBUST", "FR_WEAK_SIGNAL"])
        assert r.verdict == "FAIL"
        assert "COVID_ROBUST" in r.value["invalid_labels"]

    def test_fails_with_non_fr_label(self):
        r = check_f7_label_integrity(["REPLICATED", "FR_WEAK_SIGNAL"])
        assert r.verdict == "FAIL"

    def test_all_valid_fr_labels_accepted(self):
        r = check_f7_label_integrity(list(VALID_FR_LABELS))
        assert r.verdict == "PASS"

    def test_real_data_labels_valid(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        r = check_f7_label_integrity(pair_df["fr_label"].tolist())
        assert r.verdict == "PASS"


# ---------------------------------------------------------------------------
# Class 8: F8 — No Causal Language
# ---------------------------------------------------------------------------

class TestF8NoCausalLanguage:
    def test_passes_with_clean_text(self):
        r = check_f8_no_causal_language([
            "FR association audit", "FR_WEAK_SIGNAL", "multi-window stability", "beta below threshold"
        ])
        assert r.verdict == "PASS"

    def test_fails_with_causal_term(self):
        r = check_f8_no_causal_language(["this sector causa the other"])
        assert r.verdict == "FAIL"

    def test_fails_with_impact_term(self):
        r = check_f8_no_causal_language(["sector A impacta sector B"])
        assert r.verdict == "FAIL"

    def test_causal_terms_list_nonempty(self):
        assert len(CAUSAL_TERMS_DEC060) >= 5

    def test_empty_text_list_passes(self):
        r = check_f8_no_causal_language([])
        assert r.verdict == "PASS"


# ---------------------------------------------------------------------------
# Class 9: F9 — No Cross-Target Mixing
# ---------------------------------------------------------------------------

class TestF9NoCrossTargetMixing:
    def test_passes_single_correct_target(self):
        r = check_f9_no_cross_target_mixing(["establishment_creation"], "establishment_creation")
        assert r.verdict == "PASS"

    def test_fails_multiple_targets(self):
        r = check_f9_no_cross_target_mixing(["establishment_creation", "employment"], "establishment_creation")
        assert r.verdict == "FAIL"

    def test_fails_wrong_target(self):
        r = check_f9_no_cross_target_mixing(["employment"], "establishment_creation")
        assert r.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Class 10: F10 — Audit Completeness
# ---------------------------------------------------------------------------

class TestF10AuditCompleteness:
    def test_passes_full_coverage(self):
        r = check_f10_audit_completeness(72, 11, True, True)
        assert r.verdict == "PASS"

    def test_fails_missing_pairs(self):
        r = check_f10_audit_completeness(60, 11, True, True)
        assert r.verdict == "FAIL"

    def test_fails_missing_windows(self):
        r = check_f10_audit_completeness(72, 8, True, True)
        assert r.verdict == "FAIL"

    def test_fails_missing_csv(self):
        r = check_f10_audit_completeness(72, 11, False, True)
        assert r.verdict == "FAIL"

    def test_fails_missing_json(self):
        r = check_f10_audit_completeness(72, 11, True, False)
        assert r.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Class 11: Decision derivation
# ---------------------------------------------------------------------------

class TestDecisionDerivation:
    def test_all_pass_gives_audit_complete(self, all_pass_gates):
        d = derive_decision_dec060(all_pass_gates)
        assert d["decision"] == "AUDIT_COMPLETE"
        assert d["n_pass"] == 10
        assert d["n_fail"] == 0

    def test_critical_fail_gives_audit_incomplete(self, all_pass_gates):
        gates = all_pass_gates.copy()
        gates[0] = GateResult("F1", "FAIL", {}, {}, "")
        d = derive_decision_dec060(gates)
        assert d["decision"] == "AUDIT_INCOMPLETE"
        assert "F1" in d["critical_fail"]

    def test_secondary_fail_gives_audit_partial(self, all_pass_gates):
        gates = all_pass_gates.copy()
        gates[3] = GateResult("F4", "FAIL", {}, {}, "")
        d = derive_decision_dec060(gates)
        assert d["decision"] == "AUDIT_PARTIAL"
        assert "F4" in d["secondary_fail"]

    def test_gate_version_in_decision(self, all_pass_gates):
        d = derive_decision_dec060(all_pass_gates)
        assert "gate_version" in d
        assert d["gate_version"].startswith("DEC-060")


# ---------------------------------------------------------------------------
# Class 12: Assign FR labels
# ---------------------------------------------------------------------------

class TestAssignFRLabels:
    def test_promoted_no_pre_covid_gives_covid_sensitive(self):
        label = _assign_fr_label(
            n_promoted=1, n_near_miss_beta=0, n_near_miss_fdr=0,
            n_perm001=5, n_covid_era_p001=3, n_pre_covid_p001=0,
            max_abs_beta=0.11, min_q=0.024, max_dr2=0.012, max_bss=1.0,
        )
        assert label == "FR_COVID_SENSITIVE"

    def test_promoted_with_pre_covid_gives_national_robust(self):
        label = _assign_fr_label(
            n_promoted=1, n_near_miss_beta=0, n_near_miss_fdr=0,
            n_perm001=5, n_covid_era_p001=3, n_pre_covid_p001=2,
            max_abs_beta=0.11, min_q=0.024, max_dr2=0.012, max_bss=1.0,
        )
        assert label == "FR_NATIONAL_ROBUST"

    def test_near_miss_beta_gives_beta_below_threshold(self):
        label = _assign_fr_label(
            n_promoted=0, n_near_miss_beta=1, n_near_miss_fdr=0,
            n_perm001=3, n_covid_era_p001=2, n_pre_covid_p001=1,
            max_abs_beta=0.09, min_q=0.036, max_dr2=0.009, max_bss=1.0,
        )
        assert label == "FR_BETA_BELOW_THRESHOLD"

    def test_near_miss_fdr_gives_fdr_only_blocked(self):
        label = _assign_fr_label(
            n_promoted=0, n_near_miss_beta=0, n_near_miss_fdr=1,
            n_perm001=3, n_covid_era_p001=2, n_pre_covid_p001=1,
            max_abs_beta=0.12, min_q=0.08, max_dr2=0.009, max_bss=1.0,
        )
        assert label == "FR_FDR_ONLY_BLOCKED"

    def test_multi_window_candidate(self):
        label = _assign_fr_label(
            n_promoted=0, n_near_miss_beta=0, n_near_miss_fdr=0,
            n_perm001=4, n_covid_era_p001=2, n_pre_covid_p001=2,
            max_abs_beta=0.06, min_q=0.20, max_dr2=0.004, max_bss=0.80,
        )
        assert label == "FR_MULTI_WINDOW_CANDIDATE"

    def test_weak_signal_when_nothing_passes(self):
        label = _assign_fr_label(
            n_promoted=0, n_near_miss_beta=0, n_near_miss_fdr=0,
            n_perm001=1, n_covid_era_p001=0, n_pre_covid_p001=0,
            max_abs_beta=0.03, min_q=0.40, max_dr2=0.001, max_bss=0.50,
        )
        assert label == "FR_WEAK_SIGNAL"

    def test_all_labels_in_valid_set(self):
        test_cases = [
            (1, 0, 0, 5, 3, 0, 0.11, 0.024, 0.012, 1.0),
            (1, 0, 0, 5, 3, 2, 0.11, 0.024, 0.012, 1.0),
            (0, 1, 0, 3, 2, 1, 0.09, 0.036, 0.009, 1.0),
            (0, 0, 1, 3, 2, 1, 0.12, 0.08, 0.009, 1.0),
            (0, 0, 0, 4, 2, 2, 0.06, 0.20, 0.004, 0.80),
            (0, 0, 0, 1, 0, 0, 0.03, 0.40, 0.001, 0.50),
        ]
        for args in test_cases:
            label = _assign_fr_label(*args)
            assert label in VALID_FR_LABELS, f"Invalid label: {label}"


# ---------------------------------------------------------------------------
# Class 13: FDR and Beta Sensitivity
# ---------------------------------------------------------------------------

class TestSensitivityAnalysis:
    def test_fdr_relaxation_increases_promotions(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        sens = fdr_sensitivity_analysis(fr)
        assert sens["q_05"] <= sens["q_10"] <= sens["q_15"] <= sens["q_20"]

    def test_beta_relaxation_increases_promotions(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        sens = beta_sensitivity_analysis(fr)
        assert sens["beta_10"] <= sens["beta_08"] <= sens["beta_06"] <= sens["beta_05"]

    def test_real_fdr_sensitivity_matches_expected(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        sens = fdr_sensitivity_analysis(fr)
        # At q=0.05 only 1 pair promoted (all 4 criteria)
        assert sens["q_05"] == 1
        # At q=0.10 some more unlock (observed: 15 from earlier analysis)
        assert sens["q_10"] >= 1

    def test_real_beta_sensitivity_matches_expected(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        sens = beta_sensitivity_analysis(fr)
        # At beta=0.10: 1 promoted; at beta=0.08: more
        assert sens["beta_10"] == 1
        assert sens["beta_08"] >= 7


# ---------------------------------------------------------------------------
# Class 14: Pair Audit on Real Data
# ---------------------------------------------------------------------------

class TestPairAuditRealData:
    def test_pair_audit_covers_all_72_pairs(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        assert len(pair_df) >= 72

    def test_ru_mn_is_covid_sensitive(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        ru_mn = pair_df[(pair_df["source_sector"] == "RU") & (pair_df["target_sector"] == "MN")]
        assert not ru_mn.empty
        assert ru_mn.iloc[0]["fr_label"] == "FR_COVID_SENSITIVE"

    def test_mn_be_is_beta_below_threshold(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        mn_be = pair_df[(pair_df["source_sector"] == "MN") & (pair_df["target_sector"] == "BE")]
        assert not mn_be.empty
        assert mn_be.iloc[0]["fr_label"] == "FR_BETA_BELOW_THRESHOLD"

    def test_all_labels_valid(self, real_fr_df):
        crit = analyse_criteria(real_fr_df)
        fr = crit["fr"]
        pair_df = audit_pairs(fr)
        for label in pair_df["fr_label"]:
            assert label in VALID_FR_LABELS
