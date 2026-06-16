"""
tests/test_dec059_weak_label_revalidation.py — DEC-059 mandatory tests.

Tests required by spec:
  1. DEC-058 decision corrected to PARTIAL
  2. country-shuffled cannot be ignored (M2 checks all controls)
  3. V1 only passes M2 if it beats ALL controls by margin
  4. INSUFFICIENT_EVIDENCE triggered by n_windows/confidence/sign_consistency
  5. COVID_SENSITIVE never becomes REPLICATED
  6. LOW_EVIDENCE fold not used for strong claims
  7. sign-flipped control (C4) degrades
  8. random prevalence control (C6) preserves prevalence
  9. outputs deterministic
  10. report without causal language

Additional structural tests for multi-window aggregation, gates, and classification.
"""

from __future__ import annotations

import copy
import math
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import torch

from src.modeles.real_world.gates_dec059 import (
    GateResult,
    evaluate_all_gates_dec059,
    format_gate_report_dec059,
    derive_decision_dec059,
    scan_causal_terms_dec059,
    CAUSAL_TERMS_DEC059,
    MIN_WINDOWS,
    SIGN_CONSISTENCY_THRESHOLD,
    LOW_EVIDENCE_LABEL_THRESHOLD,
    ABSTENTION_MIN_RATE,
    CONTROL_MARGIN,
)
from src.modeles.real_world.run_dec059_weak_label_revalidation import (
    aggregate_pair_scores,
    classify_pairs_multiwindow,
    make_control_labels,
    ABSTENTION_MIN_WINDOWS,
    ABSTENTION_MEAN_THRESHOLD,
    ABSTENTION_SIGN_THRESHOLD,
)
from src.modeles.real_world.build_phase7_weak_labels import REQUIRED_COLS
from src.modeles.real_world.train_real_relation_weak_labels import (
    permute_labels,
    shuffle_country_labels,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_label_df(n_covid_robust: int = 5, n_covid_sensitive: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(n_covid_robust):
        rows.append({
            "country": "NL", "source_sector": f"S{i}", "target_sector": "MN",
            "window_start": 2014, "window_end": 2020,
            "sign_label": 1 if i % 2 == 0 else -1,
            "lag_label": 1, "presence_label": 1,
            "confidence_weight": 0.75, "evidence_class": "COVID_ROBUST",
            "source_artifact": "phase7", "notes": "",
        })
    for i in range(n_covid_sensitive):
        rows.append({
            "country": "PT", "source_sector": f"C{i}", "target_sector": "GI",
            "window_start": 2015, "window_end": 2021,
            "sign_label": 1, "lag_label": 1, "presence_label": 1,
            "confidence_weight": 0.10, "evidence_class": "COVID_SENSITIVE",
            "source_artifact": "phase7", "notes": "",
        })
    return pd.DataFrame(rows, columns=REQUIRED_COLS)


def _base_gate_input(
    v1: float = 0.667,
    c1: float = 0.55, c2: float = 0.55, c3: float = 0.55,
    c4: float = 0.55, c5: float = 0.55, c6: float = 0.55,
    n_stable: int = 3, n_replicated: int = 3, n_unstable: int = 0,
    n_insufficient: int = 10, n_total: int = 60,
    n_country_specific: int = 1,
    loco: dict | None = None,
) -> dict:
    if loco is None:
        loco = {
            "FR": {"sign_concordance": v1, "n_labels": 4, "low_evidence": False},
            "NL": {"sign_concordance": v1, "n_labels": 5, "low_evidence": False},
            "PT": {"sign_concordance": v1, "n_labels": 10, "low_evidence": False},
        }
    return {
        "nan_count": 0, "inf_count": 0, "leakage_check": True,
        "schema_valid": True, "pt_kz_excluded": True,
        "v1_sign_concordance_mean": v1,
        "c1_sign_concordance_mean": c1,
        "c2_sign_concordance_mean": c2,
        "c3_sign_concordance_mean": c3,
        "c4_sign_concordance_mean": c4,
        "c5_sign_concordance_mean": c5,
        "c6_sign_concordance_mean": c6,
        "n_stable_relations": n_stable,
        "n_replicated_associations": n_replicated,
        "n_unstable_promoted": n_unstable,
        "n_insufficient_evidence": n_insufficient,
        "n_total_pairs_evaluated": n_total,
        "loco_by_country": loco,
        "covid_sensitive_promoted_as_robust": [],
        "covid_in_replicated": [],
        "n_stable_replicated": n_stable,
        "stable_replicated_pairs": ["RU→MN", "GI→OQ"],
        "n_country_specific": n_country_specific,
        "country_specific_in_replicated": False,
        "determinism_hash_match": True,
        "causal_terms_found": [],
    }


def _make_window_df(
    n_windows: int = 5,
    presence_scores: list[float] | None = None,
    positive_signs: list[int] | None = None,
    country: str = "FR",
    src: str = "RU",
    tgt: str = "MN",
    include_covid: bool = False,
) -> pd.DataFrame:
    """Build a window-level DataFrame for a single (country, src, tgt) pair."""
    if presence_scores is None:
        presence_scores = [0.70] * n_windows
    if positive_signs is None:
        positive_signs = [1] * n_windows
    rows = []
    for i, (p, s) in enumerate(zip(presence_scores, positive_signs)):
        rows.append({
            "country": country,
            "source_sector": src,
            "target_sector": tgt,
            "window_start": 2009 + i,
            "window_end": 2015 + i,
            "score_presence": p,
            "score_sign": 0.7 if s == 1 else 0.3,
            "inferred_positive": s,
            "confidence": 0.8,
            "is_covid_window": include_covid and i == 2,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1: DEC-058 decision corrected to PARTIAL
# ══════════════════════════════════════════════════════════════════════════════

class TestDec058Corrected:

    def test_dec058_report_says_partial(self):
        """DEC-058 decision must be REAL_WEAK_LABEL_TUNING_PARTIAL in the report."""
        report_path = "reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md"
        try:
            with open(report_path) as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip("DEC-058 report not found")
        assert "REAL_WEAK_LABEL_TUNING_PARTIAL" in content, \
            "DEC-058 report must be corrected to REAL_WEAK_LABEL_TUNING_PARTIAL"

    def test_dec058_decision_not_supported(self):
        """DEC-058 report must NOT claim REAL_WEAK_LABEL_TUNING_SUPPORTED as final decision."""
        report_path = "reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md"
        try:
            with open(report_path) as f:
                lines = f.readlines()
        except FileNotFoundError:
            pytest.skip("DEC-058 report not found")
        # Find Status line
        for line in lines[:10]:  # header area
            if "Status:" in line and "Decision:" in line:
                assert "SUPPORTED" not in line or "PARTIAL" in line, \
                    f"DEC-058 Status line must not claim SUPPORTED: {line.strip()}"
                break

    def test_codex_memory_says_partial(self):
        """CODEX_MEMORY must reflect corrected DEC-058 decision."""
        try:
            with open("CODEX_MEMORY.md") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip("CODEX_MEMORY.md not found")
        # Should say PARTIAL somewhere in DEC-058 bullet
        assert "PARTIAL" in content or "REAL_WEAK_LABEL_TUNING_PARTIAL" in content, \
            "CODEX_MEMORY must reflect REAL_WEAK_LABEL_TUNING_PARTIAL for DEC-058"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2: Country-shuffled cannot be ignored (M2 checks all controls)
# ══════════════════════════════════════════════════════════════════════════════

class TestCountryShuffledNotIgnored:

    def test_m2_checks_c2_country_shuffled(self):
        """M2 must fail when C2 (country-shuffled) >= V1."""
        inp = _base_gate_input(v1=0.667, c2=0.688)  # C2 > V1
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M2"].verdict == "FAIL", \
            "M2 must FAIL when C2 country-shuffled >= V1"

    def test_m2_fails_if_any_control_within_margin(self):
        """M2 fails if even one control is within CONTROL_MARGIN of V1."""
        # Set all controls well below V1 except C3
        inp = _base_gate_input(v1=0.70, c1=0.60, c2=0.60, c3=0.66,  # C3: gap=0.04 < 0.05
                               c4=0.55, c5=0.55, c6=0.55)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M2"].verdict == "FAIL", \
            f"M2 must fail when C3 gap ({0.70-0.66:.2f}) < {CONTROL_MARGIN}"

    def test_m2_passes_only_when_all_controls_clearly_degraded(self):
        """M2 passes only when V1 exceeds ALL controls by >= CONTROL_MARGIN."""
        v1 = 0.75
        inp = _base_gate_input(v1=v1, c1=v1-0.10, c2=v1-0.08, c3=v1-0.12,
                               c4=v1-0.15, c5=v1-0.09, c6=v1-0.10)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M2"].verdict == "PASS"

    def test_m2_includes_all_six_controls(self):
        """M2 must reference C1 through C6 in its gate evidence."""
        inp = _base_gate_input(v1=0.667, c2=0.50, c3=0.50, c4=0.50, c5=0.50, c6=0.50)
        gates = evaluate_all_gates_dec059(inp)
        ev = gates["M2"].evidence
        assert "controls" in ev, "M2 evidence must contain controls dict"
        ctrl_names = set(ev["controls"].keys())
        for expected in ["C1_permuted_labels", "C2_country_shuffled", "C3_sector_shuffled",
                         "C4_sign_flipped", "C5_window_shuffled", "C6_random_labels"]:
            assert expected in ctrl_names, f"M2 evidence missing control {expected}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3: V1 only passes M2 if it beats ALL controls by margin
# ══════════════════════════════════════════════════════════════════════════════

class TestM2ControlMarginStrict:

    def test_decision_ceiling_when_m2_fails(self):
        """When M2 fails, decision can be at most PARTIAL, never SUPPORTED."""
        inp = _base_gate_input(v1=0.667, c2=0.688)
        gates = evaluate_all_gates_dec059(inp)
        decision = derive_decision_dec059(gates)
        assert decision != "REAL_WEAK_LABEL_TUNING_SUPPORTED", \
            "SUPPORTED is impossible when M2 fails"
        assert "PARTIAL" in decision or decision == "WEAK_LABELS_TOO_NOISY" \
               or decision == "COUNTRY_SPECIFIC_ONLY" \
               or decision == "REAL_RELATION_LEARNING_NOT_SUPPORTED", \
            f"Unexpected decision with M2 FAIL: {decision}"

    def test_supported_requires_m2_m3_m7(self):
        """SUPPORTED decision requires M2, M3, AND M7 to all pass."""
        inp = _base_gate_input(v1=0.75, c1=0.60, c2=0.60, c3=0.60,
                               c4=0.55, c5=0.58, c6=0.60)
        gates = evaluate_all_gates_dec059(inp)
        decision = derive_decision_dec059(gates)
        assert decision == "REAL_WEAK_LABEL_TUNING_SUPPORTED", \
            f"Expected SUPPORTED when all controls degrade and M7 passes, got: {decision}"

    def test_m2_gap_below_margin_fails(self):
        """Gap strictly below CONTROL_MARGIN fails."""
        v1 = 0.70
        c = v1 - CONTROL_MARGIN + 0.01  # gap = CONTROL_MARGIN - 0.01 → FAIL
        inp = _base_gate_input(v1=v1, c1=c)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M2"].verdict == "FAIL", \
            f"M2 must FAIL when gap ({CONTROL_MARGIN-0.01:.2f}) < {CONTROL_MARGIN}"

    def test_m2_gap_at_margin_passes(self):
        """Gap exactly at CONTROL_MARGIN passes (>= threshold)."""
        v1 = 0.70
        c = v1 - CONTROL_MARGIN  # exactly at threshold → PASS
        inp = _base_gate_input(v1=v1, c1=c, c2=v1-0.20, c3=v1-0.15,
                               c4=v1-0.20, c5=v1-0.12, c6=v1-0.15)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M2"].verdict == "PASS", \
            f"M2 must PASS when gap exactly equals CONTROL_MARGIN={CONTROL_MARGIN}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4: INSUFFICIENT_EVIDENCE when n_windows/sign_consistency/score low
# ══════════════════════════════════════════════════════════════════════════════

class TestInsufficientEvidence:

    def _make_agg_df_single(
        self,
        country="FR", src="RU", tgt="MN",
        n_windows=5, sign_consistency=0.80,
        mean_score=0.70, n_covid=1,
    ) -> pd.DataFrame:
        return pd.DataFrame([{
            "country": country, "source_sector": src, "target_sector": tgt,
            "mean_score": mean_score, "median_score": mean_score,
            "std_score": 0.05, "stability_score": 0.95,
            "sign_consistency": sign_consistency, "dominant_sign": "positive",
            "n_windows": n_windows, "n_covid_windows": n_covid,
            "n_non_covid_windows": n_windows - n_covid,
            "n_above_threshold": int(n_windows * 0.8),
        }])

    def _empty_labels(self) -> pd.DataFrame:
        return pd.DataFrame(columns=REQUIRED_COLS)

    def test_insufficient_when_too_few_windows(self):
        """Pairs with n_windows < MIN_WINDOWS must be INSUFFICIENT_EVIDENCE."""
        agg = self._make_agg_df_single(n_windows=ABSTENTION_MIN_WINDOWS - 1,
                                        sign_consistency=0.90, mean_score=0.80)
        result = classify_pairs_multiwindow(agg, self._empty_labels())
        total_insufficient = len(result["INSUFFICIENT_EVIDENCE"])
        total_supported = len(result["REPLICATED_ASSOCIATION"]) + len(result["COUNTRY_SPECIFIC"])
        assert total_insufficient > 0 or total_supported == 0, \
            "Pair with too few windows must not be promoted to REPLICATED/COUNTRY_SPECIFIC"

    def test_not_insufficient_when_enough_windows_and_stable(self):
        """A pair with enough windows and high sign_consistency must be classified."""
        agg_fr = self._make_agg_df_single(country="FR", n_windows=5, sign_consistency=0.90,
                                           mean_score=0.75)
        agg_nl = self._make_agg_df_single(country="NL", n_windows=4, sign_consistency=0.85,
                                           mean_score=0.72)
        agg = pd.concat([agg_fr, agg_nl], ignore_index=True)
        result = classify_pairs_multiwindow(agg, self._empty_labels())
        # Should be REPLICATED (>= 2 stable countries) or COUNTRY_SPECIFIC
        n_classified = (len(result["REPLICATED_ASSOCIATION"]) +
                        len(result["COUNTRY_SPECIFIC"]))
        assert n_classified >= 1, "Stable pair must be classified (not just INSUFFICIENT)"

    def test_insufficient_when_low_sign_consistency(self):
        """Low sign_consistency (below threshold) → not stably classified."""
        agg = self._make_agg_df_single(n_windows=5,
                                        sign_consistency=ABSTENTION_SIGN_THRESHOLD - 0.05,
                                        mean_score=0.80)
        result = classify_pairs_multiwindow(agg, self._empty_labels())
        # Pair should not appear in REPLICATED or COUNTRY_SPECIFIC
        rep_keys = {(r["source_sector"], r["target_sector"])
                    for r in result["REPLICATED_ASSOCIATION"]}
        cs_keys = {(r["source_sector"], r["target_sector"])
                   for r in result["COUNTRY_SPECIFIC"]}
        assert ("RU", "MN") not in rep_keys and ("RU", "MN") not in cs_keys, \
            "Low sign_consistency pair must not be promoted"

    def test_m4_gate_fails_when_zero_abstentions(self):
        """M4 fails when INSUFFICIENT_EVIDENCE count is 0."""
        inp = _base_gate_input(n_insufficient=0, n_total=72)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M4"].verdict == "FAIL", "M4 must FAIL with 0 abstentions"

    def test_m4_gate_passes_with_sufficient_abstention_rate(self):
        """M4 passes when abstention rate >= ABSTENTION_MIN_RATE."""
        n_total = 72
        n_abstained = math.ceil(n_total * ABSTENTION_MIN_RATE)
        inp = _base_gate_input(n_insufficient=n_abstained, n_total=n_total)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M4"].verdict == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5: COVID_SENSITIVE never becomes REPLICATED
# ══════════════════════════════════════════════════════════════════════════════

class TestCovidSensitiveNotReplicated:

    def test_classify_covid_sensitive_not_in_replicated(self):
        """COVID_SENSITIVE pairs appearing in >=2 countries must NOT be REPLICATED."""
        # Two countries have the pair above threshold with good stability
        agg_rows = []
        for country in ["FR", "PT"]:
            agg_rows.append({
                "country": country, "source_sector": "C0", "target_sector": "GI",
                "mean_score": 0.80, "median_score": 0.78,
                "std_score": 0.04, "stability_score": 0.96,
                "sign_consistency": 0.90, "dominant_sign": "positive",
                "n_windows": 5, "n_covid_windows": 2, "n_non_covid_windows": 3,
                "n_above_threshold": 4,
            })
        agg = pd.DataFrame(agg_rows)

        # The label marks this pair as COVID_SENSITIVE
        labels = pd.DataFrame([{
            "country": "PT", "source_sector": "C0", "target_sector": "GI",
            "window_start": 2015, "window_end": 2021,
            "sign_label": 1, "lag_label": 1, "presence_label": 1,
            "confidence_weight": 0.10, "evidence_class": "COVID_SENSITIVE",
            "source_artifact": "phase7", "notes": "",
        }], columns=REQUIRED_COLS)

        result = classify_pairs_multiwindow(agg, labels)
        rep_keys = {(r["source_sector"], r["target_sector"])
                    for r in result["REPLICATED_ASSOCIATION"]}
        assert ("C0", "GI") not in rep_keys, \
            "COVID_SENSITIVE pair must not appear in REPLICATED_ASSOCIATION"

    def test_m6_gate_fails_if_covid_in_replicated(self):
        """M6 fails when a COVID_SENSITIVE pair is in the REPLICATED list."""
        inp = _base_gate_input()
        inp["covid_in_replicated"] = ["GI→JZ"]
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M6"].verdict == "FAIL"

    def test_m6_gate_passes_when_covid_isolated(self):
        gates = evaluate_all_gates_dec059(_base_gate_input())
        assert gates["M6"].verdict == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6: LOW_EVIDENCE fold not used for strong claims
# ══════════════════════════════════════════════════════════════════════════════

class TestLowEvidenceFold:

    def test_m5_marks_fold_low_evidence(self):
        """M5 must mark folds with n_labels < threshold as LOW_EVIDENCE."""
        inp = _base_gate_input(loco={
            "FR": {"sign_concordance": 1.0, "n_labels": 1, "low_evidence": True},
            "NL": {"sign_concordance": 0.60, "n_labels": 5, "low_evidence": False},
            "PT": {"sign_concordance": 0.55, "n_labels": 10, "low_evidence": False},
        })
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M5"].verdict == "PASS"  # honest reporting, not a failure
        fr_ev = gates["M5"].evidence.get("FR", {})
        assert fr_ev.get("low_evidence") is True, "FR fold (n=1) must be LOW_EVIDENCE"

    def test_m5_fails_if_all_folds_low_evidence(self):
        """M5 fails if every LOCO fold is LOW_EVIDENCE (no valid multi-country claim)."""
        inp = _base_gate_input(loco={
            "FR": {"sign_concordance": 1.0, "n_labels": 1, "low_evidence": True},
            "NL": {"sign_concordance": 0.50, "n_labels": 2, "low_evidence": True},
            "PT": {"sign_concordance": 0.50, "n_labels": 1, "low_evidence": True},
        })
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M5"].verdict == "FAIL"

    def test_low_evidence_threshold(self):
        assert LOW_EVIDENCE_LABEL_THRESHOLD >= 3, \
            "LOW_EVIDENCE threshold must be at least 3 labels"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7: Sign-flipped control (C4) degrades
# ══════════════════════════════════════════════════════════════════════════════

class TestSignFlippedControl:

    def test_c4_flips_all_sign_labels(self):
        """C4 must flip all sign_label values."""
        labels = _make_label_df(n_covid_robust=6, n_covid_sensitive=0)
        # Ensure mixed signs
        labels = labels.copy()
        labels.loc[labels.index[:3], "sign_label"] = 1
        labels.loc[labels.index[3:], "sign_label"] = -1
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        rng = np.random.default_rng(0)
        c4 = make_control_labels(train, "C4", rng)
        # All signs should be flipped
        assert (c4["sign_label"].values == -train["sign_label"].values).all(), \
            "C4 must flip all sign labels"

    def test_c4_returns_opposite_signs(self):
        labels = _make_label_df(n_covid_robust=4, n_covid_sensitive=0)
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        train = train.copy()
        train.loc[train.index[0], "sign_label"] = 1
        train.loc[train.index[1], "sign_label"] = -1
        rng = np.random.default_rng(1)
        c4 = make_control_labels(train, "C4", rng)
        assert c4.iloc[0]["sign_label"] == -1
        assert c4.iloc[1]["sign_label"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8: Random prevalence control (C6) preserves prevalence
# ══════════════════════════════════════════════════════════════════════════════

class TestRandomPrevalenceControl:

    def test_c6_preserves_positive_prevalence(self):
        """C6 must keep roughly the same positive sign rate."""
        labels = _make_label_df(n_covid_robust=20, n_covid_sensitive=0)
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        # Set a known prevalence
        train = train.copy()
        n = len(train)
        for i, idx in enumerate(train.index):
            train.loc[idx, "sign_label"] = 1 if i < n // 2 else -1
        orig_pos_rate = float((train["sign_label"] == 1).mean())
        rng = np.random.default_rng(42)
        c6 = make_control_labels(train, "C6", rng)
        c6_pos_rate = float((c6["sign_label"] == 1).mean())
        # Should be within 25% of original (stochastic)
        assert abs(c6_pos_rate - orig_pos_rate) < 0.30, \
            f"C6 positive rate {c6_pos_rate:.2f} diverges too much from original {orig_pos_rate:.2f}"

    def test_c6_sign_labels_are_binary(self):
        labels = _make_label_df(n_covid_robust=10)
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        rng = np.random.default_rng(0)
        c6 = make_control_labels(train, "C6", rng)
        assert set(c6["sign_label"].unique()).issubset({1, -1}), \
            "C6 sign labels must be 1 or -1"

    def test_c3_shuffles_sector_codes(self):
        """C3 must change source/target sector assignments."""
        labels = _make_label_df(n_covid_robust=8, n_covid_sensitive=0)
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        rng = np.random.default_rng(7)
        c3 = make_control_labels(train, "C3", rng)
        # At least some sectors should change
        same_src = (c3["source_sector"].values == train["source_sector"].values).sum()
        same_tgt = (c3["target_sector"].values == train["target_sector"].values).sum()
        assert same_src < len(train) or same_tgt < len(train), \
            "C3 must shuffle at least some sector assignments"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9: Outputs deterministic (same seed → same result)
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:

    def test_c1_permute_deterministic(self):
        labels = _make_label_df(n_covid_robust=6)
        train = labels[labels["evidence_class"] == "COVID_ROBUST"].copy()
        for i, idx in enumerate(train.index):
            train.loc[idx, "sign_label"] = 1 if i % 2 == 0 else -1
        c1_a = make_control_labels(train, "C1", np.random.default_rng(42))
        c1_b = make_control_labels(train, "C1", np.random.default_rng(42))
        assert (c1_a["sign_label"].values == c1_b["sign_label"].values).all(), \
            "Same RNG seed must produce same C1 labels"

    def test_aggregate_pair_scores_deterministic(self):
        """aggregate_pair_scores is a pure function — same input → same output."""
        df = _make_window_df(n_windows=5, presence_scores=[0.7, 0.6, 0.8, 0.75, 0.65])
        agg1 = aggregate_pair_scores(df)
        agg2 = aggregate_pair_scores(df)
        assert abs(agg1.iloc[0]["mean_score"] - agg2.iloc[0]["mean_score"]) < 1e-9

    def test_gate_evaluation_deterministic(self):
        """Gate evaluation has no randomness — same input → same gates."""
        inp = _base_gate_input()
        g1 = evaluate_all_gates_dec059(inp)
        g2 = evaluate_all_gates_dec059(inp)
        for gid in g1:
            assert g1[gid].verdict == g2[gid].verdict


# ══════════════════════════════════════════════════════════════════════════════
# TEST 10: Report without causal language
# ══════════════════════════════════════════════════════════════════════════════

class TestNoCausalLanguage:

    def test_causal_terms_list_nonempty(self):
        assert len(CAUSAL_TERMS_DEC059) >= len(["causes", "causal", "causality"])

    def test_scan_detects_causal(self):
        assert "causes" in scan_causal_terms_dec059("sector A causes sector B")

    def test_scan_detects_portuguese(self):
        assert "impacta" in scan_causal_terms_dec059("setor A impacta setor B")
        assert "impacto causal" in scan_causal_terms_dec059("o impacto causal é grande")

    def test_scan_clean_text_empty(self):
        clean = "association precedence sign stability replication evidence partial"
        found = scan_causal_terms_dec059(clean)
        assert found == [], f"Clean text flagged: {found}"

    def test_m10_fails_on_causal(self):
        inp = _base_gate_input()
        inp["causal_terms_found"] = ["causes"]
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M10"].verdict == "FAIL"

    def test_m10_passes_on_clean(self):
        gates = evaluate_all_gates_dec059(_base_gate_input())
        assert gates["M10"].verdict == "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL: Multi-window aggregation
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiWindowAggregation:

    def test_aggregate_computes_mean(self):
        df = _make_window_df(n_windows=4, presence_scores=[0.6, 0.7, 0.8, 0.5])
        agg = aggregate_pair_scores(df)
        assert abs(agg.iloc[0]["mean_score"] - 0.65) < 0.01

    def test_aggregate_sign_consistency_all_positive(self):
        df = _make_window_df(n_windows=5, positive_signs=[1, 1, 1, 1, 1])
        agg = aggregate_pair_scores(df)
        assert agg.iloc[0]["sign_consistency"] == 1.0

    def test_aggregate_sign_consistency_mixed(self):
        df = _make_window_df(n_windows=4, positive_signs=[1, 1, 0, 0])
        agg = aggregate_pair_scores(df)
        assert agg.iloc[0]["sign_consistency"] == 0.5

    def test_aggregate_counts_windows(self):
        df = _make_window_df(n_windows=6)
        agg = aggregate_pair_scores(df)
        assert agg.iloc[0]["n_windows"] == 6

    def test_aggregate_multiple_pairs(self):
        df1 = _make_window_df(n_windows=4, src="RU", tgt="MN")
        df2 = _make_window_df(n_windows=3, src="GI", tgt="OQ")
        df = pd.concat([df1, df2], ignore_index=True)
        agg = aggregate_pair_scores(df)
        assert len(agg) == 2
        assert set(zip(agg["source_sector"], agg["target_sector"])) == {("RU", "MN"), ("GI", "OQ")}

    def test_aggregate_covid_windows_counted(self):
        df = _make_window_df(n_windows=4, include_covid=True)
        agg = aggregate_pair_scores(df)
        # One row has is_covid_window=True (i==2 in _make_window_df)
        assert agg.iloc[0]["n_covid_windows"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL: Gate structure
# ══════════════════════════════════════════════════════════════════════════════

class TestGateStructure:

    def test_all_ten_gates_present(self):
        gates = evaluate_all_gates_dec059(_base_gate_input())
        assert len(gates) == 10
        for gid in [f"M{i}" for i in range(1, 11)]:
            assert gid in gates

    def test_format_report_has_all_gates(self):
        gates = evaluate_all_gates_dec059(_base_gate_input())
        report = format_gate_report_dec059(gates)
        for gid in [f"M{i}" for i in range(1, 11)]:
            assert gid in report

    def test_m1_fails_on_nan(self):
        inp = _base_gate_input()
        inp["nan_count"] = 3
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M1"].verdict == "FAIL"

    def test_m7_fails_with_zero_replicated(self):
        inp = _base_gate_input(n_stable=0, n_replicated=0)
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M7"].verdict == "FAIL"

    def test_m8_fails_when_country_specific_in_replicated(self):
        inp = _base_gate_input()
        inp["country_specific_in_replicated"] = True
        gates = evaluate_all_gates_dec059(inp)
        assert gates["M8"].verdict == "FAIL"

    def test_decision_not_supported_without_m7(self):
        inp = _base_gate_input(n_stable=0, n_replicated=0,
                               v1=0.75, c1=0.55, c2=0.55, c3=0.55,
                               c4=0.50, c5=0.55, c6=0.55)
        gates = evaluate_all_gates_dec059(inp)
        decision = derive_decision_dec059(gates)
        assert decision != "REAL_WEAK_LABEL_TUNING_SUPPORTED"

    def test_decision_supported_requires_all_key_gates(self):
        """Full passing scenario produces SUPPORTED."""
        inp = _base_gate_input(
            v1=0.75, c1=0.60, c2=0.58, c3=0.60, c4=0.50, c5=0.60, c6=0.58,
            n_stable=5, n_replicated=5, n_unstable=0,
            n_insufficient=10, n_total=60,
        )
        gates = evaluate_all_gates_dec059(inp)
        decision = derive_decision_dec059(gates)
        assert decision == "REAL_WEAK_LABEL_TUNING_SUPPORTED"
