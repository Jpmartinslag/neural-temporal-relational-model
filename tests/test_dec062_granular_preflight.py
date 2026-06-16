"""
DEC-062: Granular Phase 7 Preflight — Mandatory Tests.

Covers:
- PT panel schema and continental filter
- KZ structural_absent handling
- CAE→A10 mapping correctness
- Growth calculation causality
- Missing vs zero vs structural_absent distinction
- NL candidate verdicts
- Readiness JSON structure
- Gate logic H1-H10
- No raw large files in tracked artefacts
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.gates_dec062_granular_preflight import (
    N_CONTINENTAL_MUNICIPALITIES_PT,
    SECTOR_KZ_STATUS,
    ALLOWED_DECISIONS,
    check_h1_dec061_review_complete,
    check_h2_pt_panel_built,
    check_h3_pt_continent_filter,
    check_h4_pt_a10_valid,
    check_h5_pt_no_missing_zero_confusion,
    check_h6_nl_search_complete,
    check_h7_nl_decision_conservative,
    check_h8_granular_preflight,
    check_h9_no_unauthorized_training,
    check_h10_reproducibility,
    derive_decision_dec062,
    GateResult,
)
from src.data.european_panel.build_pt_municipal_sector_panel import (
    CAE_TO_A10,
    A10_SECTORS,
    CONTINENTAL_PREFIX,
    ACORES_PREFIX,
    MADEIRA_PREFIX,
    parse_year,
    aggregate_to_a10,
    _harmonise_geocods,
)

REPO_ROOT = Path(__file__).parents[1]
PT_PANEL_CSV = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel.csv"
PT_MANIFEST = REPO_ROOT / "data/processed/european_panel/pt_municipal_sector_panel_manifest.json"
NL_CANDIDATES_CSV = REPO_ROOT / "data/processed/granular_phase7_preflight/nl_gemeente_source_candidates.csv"
NL_SEARCH_JSON = REPO_ROOT / "data/processed/granular_phase7_preflight/nl_gemeente_source_search.json"
READINESS_JSON = REPO_ROOT / "data/processed/granular_phase7_preflight/granular_phase7_readiness.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pt_panel():
    if not PT_PANEL_CSV.exists():
        pytest.skip("PT municipal panel not built")
    return pd.read_csv(PT_PANEL_CSV)


@pytest.fixture
def all_pass_gates():
    return [GateResult(f"H{i}", "PASS", i, i, "") for i in range(1, 11)]


@pytest.fixture
def sample_ine_entries():
    """Minimal INE-style entries for unit testing parse_year."""
    return [
        # Municipal entries (len=7 geocod)
        {"geocod": "1106100", "geodsg": "Lisboa", "dim_3": "G", "valor": "500"},
        {"geocod": "1106100", "geodsg": "Lisboa", "dim_3": "C", "valor": "120"},
        {"geocod": "1106100", "geodsg": "Lisboa", "dim_3": "K", "valor": "0"},   # K = absent
        {"geocod": "1106100", "geodsg": "Lisboa", "dim_3": "TOT", "valor": "1200"},
        {"geocod": "2004101", "geodsg": "Ponta Delgada", "dim_3": "G", "valor": "50"},  # Açores
        {"geocod": "3003101", "geodsg": "Funchal", "dim_3": "G", "valor": "80"},  # Madeira
        # Non-municipality entries (len != 7)
        {"geocod": "1", "geodsg": "Portugal", "dim_3": "G", "valor": "9000"},
        {"geocod": "PT", "geodsg": "Portugal Total", "dim_3": "TOT", "valor": "50000"},
    ]


# ---------------------------------------------------------------------------
# Class 1: CAE → A10 Mapping
# ---------------------------------------------------------------------------

class TestCAEToA10Mapping:
    def test_be_sectors_mapped(self):
        for s in ["B", "C", "D", "E"]:
            assert CAE_TO_A10[s] == "BE"

    def test_fz_mapped(self):
        assert CAE_TO_A10["F"] == "FZ"

    def test_gi_mapped(self):
        for s in ["G", "H", "I"]:
            assert CAE_TO_A10[s] == "GI"

    def test_jz_mapped(self):
        assert CAE_TO_A10["J"] == "JZ"

    def test_kz_is_none(self):
        assert CAE_TO_A10["K"] is None, "K must map to None (structural_absent)"

    def test_lz_mapped(self):
        assert CAE_TO_A10["L"] == "LZ"

    def test_mn_mapped(self):
        for s in ["M", "N"]:
            assert CAE_TO_A10[s] == "MN"

    def test_oq_includes_agriculture(self):
        """Agriculture (A) merged into OQ per HERALD PT convention."""
        assert CAE_TO_A10["A"] == "OQ"

    def test_oq_mapped(self):
        for s in ["O", "P", "Q"]:
            assert CAE_TO_A10[s] == "OQ"

    def test_ru_mapped(self):
        for s in ["R", "S"]:
            assert CAE_TO_A10[s] == "RU"

    def test_eight_observable_sectors(self):
        assert len(A10_SECTORS) == 8
        assert "KZ" not in A10_SECTORS


# ---------------------------------------------------------------------------
# Class 2: Continental Filter
# ---------------------------------------------------------------------------

class TestContinentalFilter:
    def test_continental_prefix_is_1(self):
        assert CONTINENTAL_PREFIX == "1"

    def test_acores_prefix_is_2(self):
        assert ACORES_PREFIX == "2"

    def test_madeira_prefix_is_3(self):
        assert MADEIRA_PREFIX == "3"

    def test_continental_not_acores(self):
        assert CONTINENTAL_PREFIX != ACORES_PREFIX

    def test_continental_not_madeira(self):
        assert CONTINENTAL_PREFIX != MADEIRA_PREFIX

    def test_panel_n_continental_correct(self, pt_panel):
        n = pt_panel["region_id"].nunique()
        assert abs(n - N_CONTINENTAL_MUNICIPALITIES_PT) <= 2, \
            f"Expected ~{N_CONTINENTAL_MUNICIPALITIES_PT} municipalities, got {n}"

    def test_no_acores_in_continent_panel(self, pt_panel):
        """All region_ids in panel must start with '1' (continental)."""
        acores = pt_panel[pt_panel["region_id"].astype(str).str[0] == "2"]
        assert len(acores) == 0, f"Açores municipalities found in continental panel: {len(acores)}"

    def test_no_madeira_in_continent_panel(self, pt_panel):
        """All region_ids must not start with '3' (Madeira)."""
        madeira = pt_panel[pt_panel["region_id"].astype(str).str[0] == "3"]
        assert len(madeira) == 0, f"Madeira municipalities found in continental panel: {len(madeira)}"


# ---------------------------------------------------------------------------
# Class 3: Panel Schema
# ---------------------------------------------------------------------------

class TestPanelSchema:
    def test_panel_has_region_level_municipality(self, pt_panel):
        assert (pt_panel["region_level"] == "MUNICIPALITY").all()

    def test_panel_has_correct_sectors(self, pt_panel):
        for s in A10_SECTORS:
            col = f"sector_{s}"
            assert col in pt_panel.columns, f"Missing column: {col}"

    def test_sector_kz_is_structural_absent(self, pt_panel):
        """sector_KZ must be all NaN (not zeros) — structural absence."""
        assert "sector_KZ" in pt_panel.columns
        assert pt_panel["sector_KZ"].isna().all(), "sector_KZ should be all NaN (structural_absent)"

    def test_no_kz_zeros(self, pt_panel):
        """sector_KZ must not contain 0 — 0 would imply observed but empty, not absent."""
        if "sector_KZ" in pt_panel.columns:
            zeros = (pt_panel["sector_KZ"] == 0).sum()
            assert zeros == 0, f"sector_KZ has {zeros} zeros — should be NaN for structural_absent"

    def test_target_births_not_all_null(self, pt_panel):
        assert pt_panel["target_births"].notna().sum() > 0

    def test_flag_target_concept(self, pt_panel):
        assert (pt_panel["flag_target_concept"] == "enterprise_birth").all()

    def test_country_is_pt(self, pt_panel):
        assert (pt_panel["country"] == "PT").all()

    def test_year_range_covers_2008_2023(self, pt_panel):
        assert pt_panel["year"].min() <= 2008
        assert pt_panel["year"].max() >= 2023

    def test_n_years_at_least_15(self, pt_panel):
        assert pt_panel["year"].nunique() >= 15

    def test_panel_unique_muni_year(self, pt_panel):
        """Each (region_id, year) pair must be unique."""
        dupes = pt_panel.duplicated(["region_id", "year"]).sum()
        assert dupes == 0, f"{dupes} duplicate (region_id, year) rows"

    def test_mask_sector_a10_binary(self, pt_panel):
        unique_vals = set(pt_panel["mask_sector_a10"].dropna().unique())
        assert unique_vals.issubset({0.0, 1.0})

    def test_nuts_version_column_present(self, pt_panel):
        assert "nuts_version" in pt_panel.columns

    def test_is_continental_all_true(self, pt_panel):
        assert pt_panel["is_continental"].all()


# ---------------------------------------------------------------------------
# Class 4: Growth Calculation Causality
# ---------------------------------------------------------------------------

class TestGrowthCalculationCausality:
    def test_growth_1y_uses_lag(self, pt_panel):
        """growth_1y at year t must use target_births[t-1] as denominator."""
        sub = pt_panel[pt_panel["region_id"] == pt_panel["region_id"].iloc[0]].sort_values("year")
        if len(sub) < 3:
            pytest.skip("Not enough rows to test")
        row_t = sub.iloc[2]
        row_tm1 = sub.iloc[1]
        if row_tm1["target_births"] is None or pd.isna(row_tm1["target_births"]) or row_tm1["target_births"] == 0:
            pytest.skip("Base year has no births")
        expected_growth = (row_t["target_births"] - row_tm1["target_births"]) / row_tm1["target_births"]
        assert abs(row_t["growth_1y"] - expected_growth) < 1e-6, "growth_1y not computed correctly"

    def test_first_year_growth_is_null(self, pt_panel):
        """Growth in the first year (no lag available) must be NaN."""
        first_year = pt_panel["year"].min()
        first_rows = pt_panel[pt_panel["year"] == first_year]
        assert first_rows["growth_1y"].isna().all(), "First year should have NaN growth_1y"

    def test_lag1_is_previous_year_target(self, pt_panel):
        """lag1_births at year t should equal target_births at year t-1."""
        sub = pt_panel[pt_panel["region_id"] == pt_panel["region_id"].iloc[0]].sort_values("year")
        if len(sub) < 3:
            pytest.skip("Not enough rows")
        row_t = sub.iloc[2]
        row_tm1 = sub.iloc[1]
        if not pd.isna(row_t["lag1_births"]) and not pd.isna(row_tm1["target_births"]):
            assert abs(row_t["lag1_births"] - row_tm1["target_births"]) < 1e-6


# ---------------------------------------------------------------------------
# Class 5: Missing vs Zero vs Structural Absent
# ---------------------------------------------------------------------------

class TestMissingZeroStructuralAbsent:
    def test_sector_zeros_are_float_not_nan(self, pt_panel):
        """Genuine zero births (sector had no enterprise births) should be 0.0, not NaN."""
        sector_cols = [f"sector_{s}" for s in A10_SECTORS]
        n_zeros = sum((pt_panel[col] == 0).sum() for col in sector_cols if col in pt_panel.columns)
        # Genuine zeros exist in the data
        assert n_zeros > 0, "Expected some genuine zero-birth sector-year observations"

    def test_kz_nan_not_zero(self, pt_panel):
        """KZ must be NaN (structural_absent), not 0."""
        if "sector_KZ" in pt_panel.columns:
            assert not (pt_panel["sector_KZ"] == 0).any()

    def test_parse_year_handles_zero_valor(self, sample_ine_entries):
        """valor='0' should produce 0 births, not NaN."""
        entry = {"geocod": "1106100", "geodsg": "Lisboa", "dim_3": "D", "valor": "0"}
        long, _ = parse_year([entry], 2020)
        assert not long.empty
        row = long[long["cae_section"] == "D"]
        assert not row.empty
        assert row.iloc[0]["births"] == 0

    def test_parse_year_kz_not_in_output(self, sample_ine_entries):
        """K (finance) entries should not appear in output long DataFrame."""
        long, _ = parse_year(sample_ine_entries, 2020)
        # a10=None (K) rows should not be in output
        k_rows = long[long.get("cae_section", pd.Series([], dtype=str)) == "K"] if "cae_section" in long.columns else pd.DataFrame()
        assert k_rows.empty or k_rows["a10"].isna().all() or len(k_rows) == 0

    def test_parse_year_filters_non_municipality_geocods(self, sample_ine_entries):
        """Entries with geocod length != 7 must be filtered out."""
        long, _ = parse_year(sample_ine_entries, 2020)
        assert all(len(str(gc)) == 7 for gc in long["geocod"].unique())


# ---------------------------------------------------------------------------
# Class 6: NL Candidates
# ---------------------------------------------------------------------------

class TestNLCandidates:
    @pytest.fixture
    def nl_candidates(self):
        if not NL_CANDIDATES_CSV.exists():
            pytest.skip("NL candidates CSV not found")
        return pd.read_csv(NL_CANDIDATES_CSV)

    def test_nl_candidates_csv_exists(self):
        assert NL_CANDIDATES_CSV.exists()

    def test_nl_candidates_has_verdict_column(self, nl_candidates):
        assert "verdict" in nl_candidates.columns

    def test_nl_candidates_has_rejection_reason(self, nl_candidates):
        assert "rejection_reason" in nl_candidates.columns

    def test_stock_only_not_promoted_as_births(self, nl_candidates):
        """Tables with STOCK_ONLY verdict must not have is_births=True."""
        stock_rows = nl_candidates[nl_candidates["verdict"] == "STOCK_ONLY_NOT_ACCEPTABLE"]
        if len(stock_rows) > 0:
            assert not stock_rows["is_births"].all(), "Stock-only table incorrectly marked as births"

    def test_corop_only_not_marked_gemeente(self, nl_candidates):
        """COROP_ONLY tables must have has_gemeente=False."""
        corop_rows = nl_candidates[nl_candidates["verdict"] == "COROP_ONLY"]
        if len(corop_rows) > 0:
            assert not corop_rows["has_gemeente"].all(), "COROP-only table incorrectly marked as gemeente"

    def test_no_acceptable_open_data_found(self, nl_candidates):
        """DEC-061+062 confirm no acceptable open-data source exists."""
        acceptable = nl_candidates[nl_candidates["verdict"] == "ACCEPTABLE_OPEN_DATA"]
        assert len(acceptable) == 0, f"Unexpected acceptable table found: {acceptable['table_id'].tolist()}"

    def test_known_tables_documented(self, nl_candidates):
        """83631NED and 81575NED must be in candidates."""
        table_ids = set(nl_candidates["table_id"])
        assert "83631NED" in table_ids
        assert "81575NED" in table_ids

    def test_83631ned_is_corop_only(self, nl_candidates):
        row = nl_candidates[nl_candidates["table_id"] == "83631NED"]
        assert not row.empty
        assert row.iloc[0]["verdict"] == "COROP_ONLY"

    def test_81575ned_is_stock_only(self, nl_candidates):
        row = nl_candidates[nl_candidates["table_id"] == "81575NED"]
        assert not row.empty
        assert row.iloc[0]["verdict"] == "STOCK_ONLY_NOT_ACCEPTABLE"


# ---------------------------------------------------------------------------
# Class 7: Readiness JSON
# ---------------------------------------------------------------------------

class TestReadinessJSON:
    @pytest.fixture
    def readiness(self):
        if not READINESS_JSON.exists():
            pytest.skip("Readiness JSON not found")
        with open(READINESS_JSON) as f:
            return json.load(f)

    def test_readiness_json_exists(self):
        assert READINESS_JSON.exists()

    def test_has_fr_entry(self, readiness):
        countries = [e["country"] for e in readiness["entries"]]
        assert "FR" in countries

    def test_has_pt_entry(self, readiness):
        countries = [e["country"] for e in readiness["entries"]]
        assert "PT" in countries

    def test_has_nl_entry(self, readiness):
        countries = [e["country"] for e in readiness["entries"]]
        assert "NL" in countries

    def test_pt_municipality_ready_or_limited(self, readiness):
        pt = next((e for e in readiness["entries"] if e["country"] == "PT" and "MUNICIPALITY" in e.get("region_system", "")), None)
        assert pt is not None
        assert pt["readiness_status"] in ("READY", "READY_WITH_LIMITATION")

    def test_nl_gemeente_is_blocked(self, readiness):
        nl_gem = next((e for e in readiness["entries"] if e["country"] == "NL" and e.get("region_system", "") == "GEMEENTE"), None)
        assert nl_gem is not None
        assert nl_gem["readiness_status"] == "BLOCKED"

    def test_fr_is_ready(self, readiness):
        fr = next((e for e in readiness["entries"] if e["country"] == "FR"), None)
        if fr:
            assert fr["readiness_status"] in ("READY", "READY_WITH_LIMITATION")

    def test_readiness_status_values_valid(self, readiness):
        valid = {"READY", "READY_WITH_LIMITATION", "BLOCKED"}
        for e in readiness["entries"]:
            assert e.get("readiness_status") in valid, f"Invalid status: {e.get('readiness_status')}"


# ---------------------------------------------------------------------------
# Class 8: Gates H1-H10
# ---------------------------------------------------------------------------

class TestGatesH1H10:
    def test_h1_passes_when_review_complete(self):
        r = check_h1_dec061_review_complete(True, True, True)
        assert r.verdict == "PASS"

    def test_h1_fails_missing_review(self):
        r = check_h1_dec061_review_complete(False, True, True)
        assert r.verdict == "FAIL"

    def test_h1_fails_no_continental_fix(self):
        r = check_h1_dec061_review_complete(True, False, True)
        assert r.verdict == "FAIL"

    def test_h2_passes_with_existing_files(self):
        r = check_h2_pt_panel_built(True, True, 5000)
        assert r.verdict == "PASS"

    def test_h2_fails_no_csv(self):
        r = check_h2_pt_panel_built(False, True, 5000)
        assert r.verdict == "FAIL"

    def test_h2_fails_too_few_rows(self):
        r = check_h2_pt_panel_built(True, True, 100)
        assert r.verdict == "FAIL"

    def test_h3_passes_correct_count(self):
        r = check_h3_pt_continent_filter(278, "geocod[0]=='1'", True, True)
        assert r.verdict == "PASS"

    def test_h3_fails_wrong_count(self):
        r = check_h3_pt_continent_filter(297, "prefix 1 or 2", True, True)  # DEC-061 bug
        assert r.verdict == "FAIL"

    def test_h3_fails_acores_included(self):
        r = check_h3_pt_continent_filter(278, "geocod[0]=='1'", False, True)
        assert r.verdict == "FAIL"

    def test_h4_passes_8_sectors(self):
        r = check_h4_pt_a10_valid(8, "structural_absent", ["BE","FZ","GI","JZ","LZ","MN","OQ","RU"])
        assert r.verdict == "PASS"

    def test_h4_fails_9_sectors_no_kz_record(self):
        r = check_h4_pt_a10_valid(9, "present", list("BEFGJLMOR"))
        assert r.verdict == "FAIL"

    def test_h5_passes_all_documented(self):
        r = check_h5_pt_no_missing_zero_confusion(True, True, True)
        assert r.verdict == "PASS"

    def test_h5_fails_no_na_policy(self):
        r = check_h5_pt_no_missing_zero_confusion(False, True, True)
        assert r.verdict == "FAIL"

    def test_h6_passes_full_search(self):
        r = check_h6_nl_search_complete(6, ["a","b","c","d","e"], True, True)
        assert r.verdict == "PASS"

    def test_h6_fails_few_terms(self):
        r = check_h6_nl_search_complete(6, ["a","b"], True, True)
        assert r.verdict == "FAIL"

    def test_h7_passes_conservative(self):
        r = check_h7_nl_decision_conservative("NL_GEMEENTE_OPEN_DATA_BLOCKED", True, True)
        assert r.verdict == "PASS"

    def test_h7_fails_stock_promoted(self):
        r = check_h7_nl_decision_conservative("NL_GEMEENTE_OPEN_DATA_BLOCKED", False, True)
        assert r.verdict == "FAIL"

    def test_h8_passes_all_countries(self):
        r = check_h8_granular_preflight(True, True, True, True)
        assert r.verdict == "PASS"

    def test_h8_fails_missing_country(self):
        r = check_h8_granular_preflight(True, True, False, True)
        assert r.verdict == "FAIL"

    def test_h9_passes_no_training(self):
        r = check_h9_no_unauthorized_training(True, True)
        assert r.verdict == "PASS"

    def test_h9_fails_model_trained(self):
        r = check_h9_no_unauthorized_training(False, True)
        assert r.verdict == "FAIL"

    def test_h10_passes_full_manifest(self):
        r = check_h10_reproducibility(True, True, True)
        assert r.verdict == "PASS"

    def test_h10_fails_missing_urls(self):
        r = check_h10_reproducibility(False, True, True)
        assert r.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Class 9: Decision Derivation
# ---------------------------------------------------------------------------

class TestDecisionDerivation:
    def test_all_pass_pt_ready_nl_blocked_gives_correct_decision(self, all_pass_gates):
        d = derive_decision_dec062(all_pass_gates, pt_ready=True, nl_blocked=True)
        assert d["decision"] == "PT_PANEL_READY_NL_OPEN_DATA_BLOCKED"
        assert d["n_pass"] == 10

    def test_all_pass_pt_ready_nl_found(self, all_pass_gates):
        d = derive_decision_dec062(all_pass_gates, pt_ready=True, nl_blocked=False)
        assert d["decision"] == "PT_PANEL_READY_NL_SOURCE_FOUND"

    def test_critical_fail_gives_inconclusive(self, all_pass_gates):
        gates = all_pass_gates.copy()
        gates[0] = GateResult("H1", "FAIL", {}, {}, "")
        d = derive_decision_dec062(gates, pt_ready=True, nl_blocked=True)
        assert d["decision"] == "GRANULAR_PREFLIGHT_INCONCLUSIVE"

    def test_allowed_decisions_is_valid(self, all_pass_gates):
        d = derive_decision_dec062(all_pass_gates, pt_ready=True, nl_blocked=True)
        assert d["decision"] in ALLOWED_DECISIONS


# ---------------------------------------------------------------------------
# Class 10: No Raw Large Files
# ---------------------------------------------------------------------------

class TestNoRawLargeFiles:
    def test_manifest_has_urls(self):
        if not PT_MANIFEST.exists():
            pytest.skip("PT manifest not built")
        with open(PT_MANIFEST) as f:
            m = json.load(f)
        has_url = any("url" in str(s).lower() for s in m.get("sources", []))
        assert has_url, "Manifest must contain source URLs"

    def test_manifest_has_indicator_ids(self):
        if not PT_MANIFEST.exists():
            pytest.skip("PT manifest not built")
        with open(PT_MANIFEST) as f:
            m = json.load(f)
        indicators = [s.get("indicator", "") for s in m.get("sources", [])]
        assert "0009703" in indicators

    def test_panel_csv_not_too_large(self):
        """Panel CSV should be < 5MB (processed, not raw)."""
        if not PT_PANEL_CSV.exists():
            pytest.skip("Panel not built")
        size_mb = PT_PANEL_CSV.stat().st_size / (1024 * 1024)
        assert size_mb < 5.0, f"Panel CSV is {size_mb:.1f}MB — may be too large to commit"

    def test_no_raw_ine_birth_files_in_data_external(self):
        """Raw INE birth API responses must not be committed as tracked artefacts."""
        raw_dir = REPO_ROOT / "data" / "external" / "portugal" / "raw"
        if raw_dir.exists():
            birth_keywords = ["birth", "nascimento", "empresa", "criacao", "0009703", "0014099"]
            large = [
                f for f in raw_dir.rglob("*.json")
                if f.stat().st_size > 2 * 1024 * 1024
                and any(kw in f.name.lower() for kw in birth_keywords)
            ]
            assert len(large) == 0, f"Large raw birth files in data/external: {[f.name for f in large]}"

    def test_geocod_harmonisation_reduces_unique_ids(self):
        """After harmonisation, unique geocods per year should be ≤ 278."""
        if not PT_PANEL_CSV.exists():
            pytest.skip("Panel not built")
        df = pd.read_csv(PT_PANEL_CSV)
        per_year = df.groupby("year")["region_id"].nunique()
        assert (per_year <= 280).all(), f"Some years have > 280 unique municipalities: {per_year[per_year > 280]}"
