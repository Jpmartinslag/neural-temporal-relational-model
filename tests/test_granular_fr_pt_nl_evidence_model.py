"""
DEC-063: Granular FR/PT/NL Evidence Model — Mandatory Tests.

Covers:
- CBS 83631NED confirmed COROP-only (no GM codes)
- CBS 81575NED confirmed gemeente stock (not births)
- CBS 71543ned explicitly rejected
- Proxy re-aggregates to COROP births exactly
- evidence_type mandatory in all panels
- observed and proxy not confused
- PT KZ structural_absent
- No NaN/Inf in critical columns
- Schema of outputs
- No causal language in manifests/reports
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.european_panel.gates_dec063_granular_evidence import (
    ALLOWED_DECISIONS,
    GATE_VERSION,
    GateResult,
    check_g1_sources_registered,
    check_g2_births_corop_only,
    check_g3_stock_not_births,
    check_g4_proxy_reaggregates,
    check_g5_fr_pt_not_proxy,
    check_g6_pt_kz_absent,
    check_g7_no_large_raw_committed,
    check_g8_tests_pass,
    check_g9_no_causal_language,
    check_g10_documentation_complete,
    derive_decision_dec063,
)
from src.data.european_panel.build_nl_gemeente_birth_proxy import (
    compute_stock_shares,
    verify_reaggregation,
    A10_SECTORS,
    EVIDENCE_TYPE,
    PROXY_METHOD,
    SOURCE_BIRTH_TABLE,
    SOURCE_STOCK_TABLE,
)

REPO_ROOT = Path(__file__).parents[1]
PANEL_DIR = REPO_ROOT / "data/processed/european_panel"
COROP_BIRTHS = REPO_ROOT / "data/external/netherlands/processed/netherlands_sector_births_cbs_83631NED_corop_a10.csv"
STOCK_PANEL = PANEL_DIR / "nl_gemeente_stock_panel.csv"
CROSSWALK = PANEL_DIR / "nl_gemeente_corop_crosswalk.csv"
PROXY_PANEL = PANEL_DIR / "nl_gemeente_birth_proxy_panel.csv"
PROXY_MANIFEST = PANEL_DIR / "nl_gemeente_birth_proxy_manifest.json"
STOCK_MANIFEST = PANEL_DIR / "nl_gemeente_stock_manifest.json"
PT_PANEL = PANEL_DIR / "pt_municipal_sector_panel.csv"
TRAINING_MATRIX = PANEL_DIR / "granular_fr_pt_nl_training_matrix.csv"

CAUSAL_TERMS = ["causes", "drives", "leads to", "induces", "results in",
                "provoca", "causa ", "conduit à", "entraîne"]


# ---------------------------------------------------------------------------
# Class 1: CBS Table Classification
# ---------------------------------------------------------------------------

class TestCBSTableClassification:
    def test_83631ned_is_corop_only_from_processed_data(self):
        """83631NED processed data should have CR codes, not GM codes."""
        if not COROP_BIRTHS.exists():
            pytest.skip("COROP births not built")
        df = pd.read_csv(COROP_BIRTHS)
        ids = df["zone_id"].astype(str).str.strip().unique()
        n_gm = sum(1 for x in ids if x.startswith("GM"))
        n_cr = sum(1 for x in ids if x.startswith("CR"))
        assert n_gm == 0, f"83631NED should have 0 GM codes, found {n_gm}"
        assert n_cr >= 40, f"83631NED should have ≥40 CR codes, found {n_cr}"

    def test_81575ned_has_gemeente_codes(self):
        """81575NED stock panel should have GM codes."""
        if not STOCK_PANEL.exists():
            pytest.skip("Stock panel not built")
        df = pd.read_csv(STOCK_PANEL)
        assert "gm_code" in df.columns
        gm_codes = df["gm_code"].astype(str).str.strip()
        n_gm = gm_codes.str.startswith("GM").sum()
        assert n_gm > 0, "Stock panel has no GM codes"
        assert n_gm >= 355, f"Expected ≥355 GM codes, found {n_gm}"

    def test_81575ned_evidence_type_is_stock(self):
        """Stock panel must be marked observed_stock, not births."""
        if not STOCK_PANEL.exists():
            pytest.skip("Stock panel not built")
        df = pd.read_csv(STOCK_PANEL)
        assert "evidence_type" in df.columns
        types = df["evidence_type"].unique()
        assert all(t == "observed_stock" for t in types), \
            f"Stock panel has wrong evidence_type: {types}"

    def test_71543ned_explicitly_rejected(self):
        """71543ned must not be used as stock source (SBI'93, 2006-2009, legacy)."""
        # Check that source_table in stock manifest is 81575NED, not 71543ned
        if not STOCK_MANIFEST.exists():
            pytest.skip("Stock manifest not built")
        with open(STOCK_MANIFEST) as f:
            m = json.load(f)
        assert m.get("source_table") != "71543ned", "71543ned must not be used as stock source"
        assert m.get("source_table") == "81575NED", f"Expected 81575NED, got {m.get('source_table')}"

    def test_81575ned_metric_is_vestigingen(self):
        """81575NED metric must be Vestigingen_1 (stock), not OprichtingenVanVestigingen_1."""
        if not STOCK_MANIFEST.exists():
            pytest.skip("Stock manifest not built")
        with open(STOCK_MANIFEST) as f:
            m = json.load(f)
        metric = m.get("metric", "")
        assert "Vestigingen" in metric, f"Wrong metric: {metric}"
        assert "Oprichtingen" not in metric, f"Stock metric should not contain Oprichtingen: {metric}"

    def test_83631ned_metric_is_oprichtingen(self):
        """83631NED source metric should be OprichtingenVanVestigingen (births/openings)."""
        if not PROXY_MANIFEST.exists():
            pytest.skip("Proxy manifest not built")
        with open(PROXY_MANIFEST) as f:
            m = json.load(f)
        birth_table = m.get("source_birth_table", "")
        assert birth_table == "83631NED"


# ---------------------------------------------------------------------------
# Class 2: CBS API DataProperties (live checks - skip if no connection)
# ---------------------------------------------------------------------------

class TestCBSDataPropertiesLive:
    @pytest.fixture
    def _skip_if_no_net(self):
        try:
            import requests
            r = requests.get("https://opendata.cbs.nl", timeout=5)
            if r.status_code >= 500:
                pytest.skip("CBS API not reachable")
        except Exception:
            pytest.skip("No network connection to CBS")

    def test_83631ned_has_no_gm_regio(self, _skip_if_no_net):
        """Verify CBS 83631NED has 0 GM codes in RegioS dimension."""
        import requests
        r = requests.get(
            "https://opendata.cbs.nl/ODataApi/OData/83631NED/RegioS",
            params={"$format": "json", "$filter": "startswith(Key,'GM')", "$top": 5},
            headers={"Accept": "application/json"}, timeout=30
        )
        assert r.status_code == 200
        vals = r.json().get("value", [])
        assert len(vals) == 0, f"83631NED should have 0 GM codes, got {len(vals)}"

    def test_81575ned_has_gm_regio(self, _skip_if_no_net):
        """Verify CBS 81575NED has GM codes in RegioS dimension."""
        import requests
        r = requests.get(
            "https://opendata.cbs.nl/ODataApi/OData/81575NED/RegioS",
            params={"$format": "json", "$filter": "startswith(Key,'GM')", "$top": 5},
            headers={"Accept": "application/json"}, timeout=30
        )
        assert r.status_code == 200
        vals = r.json().get("value", [])
        assert len(vals) > 0, "81575NED should have GM codes"

    def test_81575ned_metric_is_vestigingen_live(self, _skip_if_no_net):
        """Verify CBS 81575NED has Vestigingen_1 (stock) topic, not OprichtingenVanVestigingen."""
        import requests
        r = requests.get(
            "https://opendata.cbs.nl/ODataApi/OData/81575NED/DataProperties",
            params={"$format": "json", "$select": "Key,Title,Type"},
            headers={"Accept": "application/json"}, timeout=30
        )
        assert r.status_code == 200
        props = r.json().get("value", [])
        keys = [p["Key"] for p in props]
        assert "Vestigingen_1" in keys
        assert "OprichtingenVanVestigingen_1" not in keys


# ---------------------------------------------------------------------------
# Class 3: Proxy Construction
# ---------------------------------------------------------------------------

class TestProxyConstruction:
    @pytest.fixture
    def proxy_df(self):
        if not PROXY_PANEL.exists():
            pytest.skip("Proxy panel not built")
        return pd.read_csv(PROXY_PANEL)

    def test_proxy_has_evidence_type_column(self, proxy_df):
        assert "evidence_type" in proxy_df.columns

    def test_proxy_evidence_type_is_proxy(self, proxy_df):
        types = proxy_df["evidence_type"].unique()
        assert all("proxy" in str(t).lower() for t in types), \
            f"Proxy panel must have proxy evidence_type, got: {types}"

    def test_proxy_has_source_tables(self, proxy_df):
        assert "source_birth_table" in proxy_df.columns
        assert "source_stock_table" in proxy_df.columns
        assert (proxy_df["source_birth_table"] == "83631NED").all()
        assert (proxy_df["source_stock_table"] == "81575NED").all()

    def test_proxy_has_evidence_status(self, proxy_df):
        assert "evidence_status" in proxy_df.columns
        valid_statuses = {"proxy_computed", "no_corop_births_data",
                          "insufficient_stock_share", "missing_gemeente_stock"}
        statuses = set(proxy_df["evidence_status"].unique())
        assert statuses.issubset(valid_statuses), f"Unexpected statuses: {statuses - valid_statuses}"

    def test_proxy_estimated_births_not_called_observed(self, proxy_df):
        """Column must be named estimated_births_gemeente, not observed_births."""
        assert "estimated_births_gemeente" in proxy_df.columns
        assert "observed_births_gemeente" not in proxy_df.columns

    def test_proxy_stock_share_between_0_and_1(self, proxy_df):
        ok_rows = proxy_df[proxy_df["evidence_status"] == "proxy_computed"]
        if len(ok_rows) == 0:
            pytest.skip("No proxy_computed rows")
        shares = ok_rows["stock_share_within_corop"].dropna()
        assert (shares >= 0).all(), "Negative stock shares found"
        assert (shares <= 1.0 + 1e-9).all(), "Stock shares > 1 found"

    def test_proxy_reaggregates_to_corop(self, proxy_df):
        """Re-aggregating proxy by COROP must recover observed_births_corop."""
        ok = proxy_df[proxy_df["evidence_status"] == "proxy_computed"].copy()
        if len(ok) == 0:
            pytest.skip("No proxy_computed rows")
        reag = ok.groupby(["cr_code", "year", "sector_a10"], as_index=False)[
            "estimated_births_gemeente"].sum(min_count=1)
        check = reag.merge(
            ok[["cr_code", "year", "sector_a10", "observed_births_corop"]].drop_duplicates(),
            on=["cr_code", "year", "sector_a10"], how="inner"
        ).dropna(subset=["observed_births_corop", "estimated_births_gemeente"])
        abs_err = (check["estimated_births_gemeente"] - check["observed_births_corop"]).abs()
        assert abs_err.max() < 1.0, f"Max re-aggregation error: {abs_err.max():.4f}"

    def test_proxy_manifest_has_reaggregation_check(self):
        if not PROXY_MANIFEST.exists():
            pytest.skip("Proxy manifest not built")
        with open(PROXY_MANIFEST) as f:
            m = json.load(f)
        assert "reaggregation_check" in m
        check = m["reaggregation_check"]
        assert check.get("status") == "PASS"

    def test_no_inf_in_estimated_births(self, proxy_df):
        ok = proxy_df[proxy_df["evidence_status"] == "proxy_computed"]["estimated_births_gemeente"]
        assert not np.isinf(ok.fillna(0)).any(), "Inf values in estimated_births_gemeente"

    def test_no_negative_estimated_births(self, proxy_df):
        ok = proxy_df[proxy_df["evidence_status"] == "proxy_computed"]["estimated_births_gemeente"]
        assert (ok.dropna() >= 0).all(), "Negative estimated births found"


# ---------------------------------------------------------------------------
# Class 4: PT Panel (KZ structural_absent)
# ---------------------------------------------------------------------------

class TestPTPanelKZ:
    @pytest.fixture
    def pt_df(self):
        if not PT_PANEL.exists():
            pytest.skip("PT panel not built")
        return pd.read_csv(PT_PANEL)

    def test_pt_kz_column_exists(self, pt_df):
        assert "sector_KZ" in pt_df.columns

    def test_pt_kz_is_all_nan(self, pt_df):
        assert pt_df["sector_KZ"].isna().all(), "PT sector_KZ must be all NaN (structural_absent)"

    def test_pt_kz_has_no_zeros(self, pt_df):
        zeros = (pt_df["sector_KZ"] == 0).sum()
        assert zeros == 0, f"PT sector_KZ has {zeros} zeros — should be NaN"

    def test_pt_evidence_type_is_observed(self, pt_df):
        if "evidence_type" in pt_df.columns:
            bad = [t for t in pt_df["evidence_type"].unique() if "proxy" in str(t).lower()]
            assert len(bad) == 0, f"PT has proxy evidence_type: {bad}"

    def test_nl_kz_is_not_all_nan(self):
        """NL KZ (Finance) is present and not structural_absent unlike PT."""
        if not STOCK_PANEL.exists():
            pytest.skip("Stock panel not built")
        stock = pd.read_csv(STOCK_PANEL)
        if "sector_KZ" in stock.columns:
            # NL should have some non-NaN KZ (Finance is a major NL sector)
            n_kz = stock["sector_KZ"].notna().sum()
            assert n_kz > 0, "NL sector_KZ should not be all NaN (Finance present in NL)"


# ---------------------------------------------------------------------------
# Class 5: Evidence Separation (observed vs proxy not confused)
# ---------------------------------------------------------------------------

class TestEvidenceSeparation:
    def test_fr_panel_no_proxy_column(self):
        """FR panel must not have estimated_births or proxy columns."""
        fr = PANEL_DIR / "france_panel.csv"
        if not fr.exists():
            pytest.skip("FR panel not found")
        df = pd.read_csv(fr, nrows=5)
        assert "estimated_births_gemeente" not in df.columns
        assert "proxy_method" not in df.columns

    def test_pt_panel_no_proxy_column(self):
        """PT panel must not have estimated_births or proxy columns."""
        if not PT_PANEL.exists():
            pytest.skip("PT panel not found")
        df = pd.read_csv(PT_PANEL, nrows=5)
        assert "estimated_births_gemeente" not in df.columns
        assert "proxy_method" not in df.columns

    def test_proxy_has_proxy_method_column(self):
        """Proxy panel must have proxy_method column to distinguish from observed."""
        if not PROXY_PANEL.exists():
            pytest.skip("Proxy panel not built")
        df = pd.read_csv(PROXY_PANEL, nrows=5)
        assert "proxy_method" in df.columns

    def test_training_matrix_has_evidence_distinction(self):
        """Training matrix must distinguish observed vs proxy per country."""
        if not TRAINING_MATRIX.exists():
            pytest.skip("Training matrix not built")
        tm = pd.read_csv(TRAINING_MATRIX)
        assert "observed_births_available" in tm.columns
        assert "proxy_births_available" in tm.columns
        # FR and PT must have observed_births, NL gemeente must have proxy
        fr_pt = tm[tm["country"].isin(["FR", "PT"])]
        assert fr_pt["observed_births_available"].all()
        assert not fr_pt["proxy_births_available"].any()
        nl_proxy = tm[(tm["country"] == "NL") & (tm["region_system"] == "GEMEENTE_PROXY")]
        if len(nl_proxy) > 0:
            assert nl_proxy["proxy_births_available"].iloc[0]
            assert not nl_proxy["observed_births_available"].iloc[0]

    def test_training_matrix_has_forbidden_claims(self):
        """Each row in training matrix must document forbidden claims."""
        if not TRAINING_MATRIX.exists():
            pytest.skip("Training matrix not built")
        tm = pd.read_csv(TRAINING_MATRIX)
        assert "forbidden_claims" in tm.columns
        nl_proxy = tm[tm["region_system"] == "GEMEENTE_PROXY"]
        if len(nl_proxy) > 0:
            fc = nl_proxy["forbidden_claims"].iloc[0]
            assert "proxy" in fc.lower() or "observed" in fc.lower()


# ---------------------------------------------------------------------------
# Class 6: Output Schema
# ---------------------------------------------------------------------------

class TestOutputSchema:
    def test_stock_panel_has_required_cols(self):
        if not STOCK_PANEL.exists():
            pytest.skip("Stock panel not built")
        df = pd.read_csv(STOCK_PANEL)
        required = ["country", "gm_code", "year", "evidence_type", "source_table", "cr_code"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_proxy_panel_has_required_cols(self):
        if not PROXY_PANEL.exists():
            pytest.skip("Proxy panel not built")
        df = pd.read_csv(PROXY_PANEL)
        required = [
            "country", "year", "cr_code", "gm_code", "sector_a10",
            "observed_births_corop", "stock_observed_gemeente",
            "stock_share_within_corop", "estimated_births_gemeente",
            "evidence_status", "evidence_type", "proxy_method",
            "source_birth_table", "source_stock_table",
        ]
        for col in required:
            assert col in df.columns, f"Proxy panel missing column: {col}"

    def test_crosswalk_has_required_cols(self):
        if not CROSSWALK.exists():
            pytest.skip("Crosswalk not built")
        df = pd.read_csv(CROSSWALK)
        for col in ["gm_code", "gm_name", "cr_code", "cr_name"]:
            assert col in df.columns

    def test_crosswalk_gm_codes_start_with_gm(self):
        if not CROSSWALK.exists():
            pytest.skip("Crosswalk not built")
        df = pd.read_csv(CROSSWALK)
        assert df["gm_code"].astype(str).str.startswith("GM").all()

    def test_crosswalk_cr_codes_start_with_cr(self):
        if not CROSSWALK.exists():
            pytest.skip("Crosswalk not built")
        df = pd.read_csv(CROSSWALK)
        assert df["cr_code"].astype(str).str.startswith("CR").all()

    def test_training_matrix_has_4_entries(self):
        if not TRAINING_MATRIX.exists():
            pytest.skip("Training matrix not built")
        tm = pd.read_csv(TRAINING_MATRIX)
        assert len(tm) == 4, f"Expected 4 training matrix entries, got {len(tm)}"

    def test_stock_n_municipalities(self):
        if not STOCK_PANEL.exists():
            pytest.skip("Stock panel not built")
        df = pd.read_csv(STOCK_PANEL)
        n = df["gm_code"].nunique()
        assert n >= 400, f"Expected ≥400 GMs in stock panel, got {n}"


# ---------------------------------------------------------------------------
# Class 7: No Causal Language
# ---------------------------------------------------------------------------

class TestNoCausalLanguage:
    def _check_file(self, path: Path):
        if not path.exists():
            pytest.skip(f"File not found: {path.name}")
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in CAUSAL_TERMS:
            assert term not in text, \
                f"Causal term '{term}' found in {path.name}"

    def test_no_causal_in_proxy_manifest(self):
        self._check_file(PROXY_MANIFEST)

    def test_no_causal_in_stock_manifest(self):
        self._check_file(STOCK_MANIFEST)

    def test_evidence_type_language_in_proxy(self):
        """Proxy manifest must use 'proxy' language."""
        if not PROXY_MANIFEST.exists():
            pytest.skip("Proxy manifest not built")
        text = PROXY_MANIFEST.read_text().lower()
        assert "proxy" in text
        assert "association" in text or "evidence" in text or "share" in text


# ---------------------------------------------------------------------------
# Class 8: Gates G1-G10
# ---------------------------------------------------------------------------

class TestGatesG1G10:
    def test_g1_pass_all_sources(self):
        r = check_g1_sources_registered(True, True, True, True)
        assert r.verdict == "PASS"

    def test_g1_fail_missing_proxy(self):
        r = check_g1_sources_registered(True, True, True, False)
        assert r.verdict == "FAIL"

    def test_g2_pass_corop_only(self):
        r = check_g2_births_corop_only(0, 40)
        assert r.verdict == "PASS"

    def test_g2_fail_has_gm(self):
        r = check_g2_births_corop_only(5, 40)
        assert r.verdict == "FAIL"

    def test_g2_fail_too_few_cr(self):
        r = check_g2_births_corop_only(0, 10)
        assert r.verdict == "FAIL"

    def test_g3_pass_vestigingen_stock(self):
        r = check_g3_stock_not_births("Vestigingen_1", "observed_stock", True)
        assert r.verdict == "PASS"

    def test_g3_fail_wrong_metric(self):
        r = check_g3_stock_not_births("OprichtingenVanVestigingen_1", "observed_stock", True)
        assert r.verdict == "FAIL"

    def test_g3_fail_wrong_ev_type(self):
        r = check_g3_stock_not_births("Vestigingen_1", "observed_births", True)
        assert r.verdict == "FAIL"

    def test_g4_pass_zero_error(self):
        r = check_g4_proxy_reaggregates("PASS", 0.0, 0.0)
        assert r.verdict == "PASS"

    def test_g4_fail_too_large_error(self):
        r = check_g4_proxy_reaggregates("FAIL", 100.0, 0.5)
        assert r.verdict == "FAIL"

    def test_g5_pass_no_proxy_in_fr_pt(self):
        r = check_g5_fr_pt_not_proxy(
            ["observed_births (establishment_creation)"],
            ["observed_births (enterprise_birth)"]
        )
        assert r.verdict == "PASS"

    def test_g5_fail_proxy_in_fr(self):
        r = check_g5_fr_pt_not_proxy(
            ["proxy_disaggregated_by_stock_share"],
            ["observed_births"]
        )
        assert r.verdict == "FAIL"

    def test_g6_pass_kz_absent(self):
        r = check_g6_pt_kz_absent(True, False)
        assert r.verdict == "PASS"

    def test_g6_fail_kz_has_zeros(self):
        r = check_g6_pt_kz_absent(True, True)
        assert r.verdict == "FAIL"

    def test_g6_fail_kz_not_all_nan(self):
        r = check_g6_pt_kz_absent(False, False)
        assert r.verdict == "FAIL"

    def test_g7_pass_no_large_raw(self):
        r = check_g7_no_large_raw_committed(True, True, True)
        assert r.verdict == "PASS"

    def test_g8_pass_all_tests(self):
        r = check_g8_tests_pass(50, 0)
        assert r.verdict == "PASS"

    def test_g8_fail_some_tests(self):
        r = check_g8_tests_pass(40, 1)
        assert r.verdict == "FAIL"

    def test_g9_pass_no_causal(self):
        r = check_g9_no_causal_language(True, True)
        assert r.verdict == "PASS"

    def test_g9_fail_causal_in_manifest(self):
        r = check_g9_no_causal_language(False, True)
        assert r.verdict == "FAIL"

    def test_g10_pass_all_docs(self):
        r = check_g10_documentation_complete(True, True, True, True)
        assert r.verdict == "PASS"

    def test_g10_fail_missing_report(self):
        r = check_g10_documentation_complete(False, True, True, True)
        assert r.verdict == "FAIL"


# ---------------------------------------------------------------------------
# Class 9: Decision Derivation
# ---------------------------------------------------------------------------

class TestDecisionDerivation:
    def _all_pass(self):
        return [GateResult(f"G{i}", "PASS", {}, {}, "") for i in range(1, 11)]

    def test_all_pass_gives_ready(self):
        d = derive_decision_dec063(self._all_pass())
        assert d["decision"] == "GRANULAR_FR_PT_NL_PREFLIGHT_READY"
        assert d["n_pass"] == 10

    def test_g4_fail_blocks_proxy_invalid(self):
        gates = self._all_pass()
        gates[3] = GateResult("G4", "FAIL", {}, {}, "")  # G4 = index 3
        d = derive_decision_dec063(gates)
        assert d["decision"] == "BLOCKED_PROXY_INVALID"

    def test_g5_fail_blocks_contamination(self):
        gates = self._all_pass()
        gates[4] = GateResult("G5", "FAIL", {}, {}, "")
        d = derive_decision_dec063(gates)
        assert d["decision"] == "BLOCKED_EVIDENCE_CONTAMINATION"

    def test_decision_in_allowed_set(self):
        d = derive_decision_dec063(self._all_pass())
        assert d["decision"] in ALLOWED_DECISIONS

    def test_gate_version_set(self):
        d = derive_decision_dec063(self._all_pass())
        assert d["gate_version"] == GATE_VERSION
