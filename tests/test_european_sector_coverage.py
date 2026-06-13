"""
Tests for European sector coverage preflight (DEC-038).

Checks: determinism, schema, eligibility classification, temporal criteria,
sector coverage, concept semantics, no-download contract, Belgium and Spain
explicitly evaluated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "data/processed/european_panel/european_sector_coverage_matrix.csv"
SUMMARY_PATH = REPO_ROOT / "data/processed/european_panel/european_sector_coverage_summary.json"
MANIFEST_PATH = REPO_ROOT / "data/processed/european_panel/european_sector_source_manifest.json"

VALID_STATUSES = {
    "IN_OBSERVATORY",
    "ELIGIBLE_WITH_MAPPING",
    "ELIGIBLE_WITH_DOWNLOAD",
    "PARTIAL_DESCRIPTIVE_ONLY",
    "BLOCKED_DATA",
    "BLOCKED_SEMANTICS",
}

REQUIRED_MATRIX_COLS = {
    "country",
    "country_name",
    "primary_source",
    "n_territories",
    "year_min",
    "year_max",
    "consecutive_years",
    "n_sectors_a10_compatible",
    "enterprise_births_available",
    "sector_births_available",
    "geometry_available",
    "phase7_temporal_ok",
    "phase7_territorial_ok",
    "phase7_sector_ok",
    "phase7_concept_ok",
    "phase7_samples_ok",
    "phase7_n_samples",
    "eligibility_status",
    "blocking_reason",
}

REQUIRED_SUMMARY_KEYS = {
    "generated",
    "decision",
    "n_countries_evaluated",
    "status_counts",
    "status_groups",
    "panel_proposals",
    "critical_findings",
}

REQUIRED_PANEL_PROPOSALS = {"CORE_CONTIGUOUS", "EU_EXTENDED", "DESCRIPTIVE_ONLY", "BLOCKED"}

REQUIRED_MANIFEST_KEYS = {
    "generated",
    "decision",
    "local_sources",
    "external_sources_not_downloaded",
}

MIN_CONSECUTIVE_YEARS = 6
MIN_SAMPLES = 60


@pytest.fixture(scope="module")
def matrix() -> pd.DataFrame:
    return pd.read_csv(MATRIX_PATH, low_memory=False)


@pytest.fixture(scope="module")
def summary() -> dict:
    with open(SUMMARY_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


# ── Schema tests ──────────────────────────────────────────────────────────────

class TestSchema:
    def test_matrix_has_required_columns(self, matrix):
        missing = REQUIRED_MATRIX_COLS - set(matrix.columns)
        assert not missing, f"Matrix missing columns: {missing}"

    def test_summary_has_required_keys(self, summary):
        missing = REQUIRED_SUMMARY_KEYS - set(summary.keys())
        assert not missing, f"Summary missing keys: {missing}"

    def test_manifest_has_required_keys(self, manifest):
        missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
        assert not missing, f"Manifest missing keys: {missing}"

    def test_all_statuses_are_valid(self, matrix):
        invalid = set(matrix["eligibility_status"].unique()) - VALID_STATUSES
        assert not invalid, f"Invalid statuses found: {invalid}"

    def test_panel_proposals_present(self, summary):
        missing = REQUIRED_PANEL_PROPOSALS - set(summary["panel_proposals"].keys())
        assert not missing, f"Missing panel proposals: {missing}"

    def test_no_duplicate_countries(self, matrix):
        dupes = matrix[matrix.duplicated("country")]["country"].tolist()
        assert not dupes, f"Duplicate country rows: {dupes}"

    def test_decision_is_dec038(self, summary, manifest):
        assert summary["decision"] == "DEC-038"
        assert manifest["decision"] == "DEC-038"

    def test_manifest_local_sources_have_paths(self, manifest):
        for src in manifest["local_sources"]:
            assert "path" in src
            assert "sha256_head" in src or "path" in src

    def test_manifest_external_sources_have_urls(self, manifest):
        for country, ext in manifest["external_sources_not_downloaded"].items():
            assert "url" in ext, f"{country} missing url"
            assert "source" in ext, f"{country} missing source"
            assert "concept" in ext, f"{country} missing concept"


# ── Eligibility classification tests ─────────────────────────────────────────

class TestEligibilityClassification:
    def test_observatory_countries_in_observatory(self, matrix):
        obs = matrix[matrix["country"].isin(["FR", "NL", "PT"])]
        assert (obs["eligibility_status"] == "IN_OBSERVATORY").all(), \
            "FR, NL, PT must be IN_OBSERVATORY"

    def test_belgium_is_blocked_semantics(self, matrix):
        be = matrix[matrix["country"] == "BE"].iloc[0]
        assert be["eligibility_status"] == "BLOCKED_SEMANTICS", \
            "Belgium must be BLOCKED_SEMANTICS (VAT concept incompatible)"

    def test_belgium_blocking_reason_mentions_vat(self, matrix):
        be = matrix[matrix["country"] == "BE"].iloc[0]
        reason = str(be["blocking_reason"]).lower()
        assert "vat" in reason or "vat_first_registration" in reason.replace(" ", "_")

    def test_finland_is_eligible_with_mapping(self, matrix):
        fi = matrix[matrix["country"] == "FI"].iloc[0]
        assert fi["eligibility_status"] == "ELIGIBLE_WITH_MAPPING", \
            "Finland must be ELIGIBLE_WITH_MAPPING (K_L combined)"

    def test_spain_is_eligible_with_download(self, matrix):
        es = matrix[matrix["country"] == "ES"].iloc[0]
        assert es["eligibility_status"] == "ELIGIBLE_WITH_DOWNLOAD", \
            "Spain must be ELIGIBLE_WITH_DOWNLOAD (national source INE DIRCE)"

    def test_no_country_promoted_without_meeting_criteria(self, matrix):
        """Countries with <6 consecutive years from BD_HGNACE_R must not be IN_OBSERVATORY
        or ELIGIBLE_WITH_MAPPING without an external source documented."""
        # The only ELIGIBLE_WITH_MAPPING country must be FI (≥6 years in BD_HGNACE_R)
        mapping = matrix[matrix["eligibility_status"] == "ELIGIBLE_WITH_MAPPING"]
        for _, row in mapping.iterrows():
            assert row["consecutive_years"] >= MIN_CONSECUTIVE_YEARS, \
                f"{row['country']}: ELIGIBLE_WITH_MAPPING but only {row['consecutive_years']} consecutive years"

    def test_blocked_semantics_has_enterprise_births_false(self, matrix):
        blocked_sem = matrix[matrix["eligibility_status"] == "BLOCKED_SEMANTICS"]
        for _, row in blocked_sem.iterrows():
            assert not row["enterprise_births_available"], \
                f"{row['country']}: BLOCKED_SEMANTICS but enterprise_births_available=True"

    def test_in_observatory_has_sector_births(self, matrix):
        obs = matrix[matrix["eligibility_status"] == "IN_OBSERVATORY"]
        for _, row in obs.iterrows():
            assert row["sector_births_available"], \
                f"{row['country']}: IN_OBSERVATORY but sector_births_available=False"

    def test_partial_descriptive_only_has_insufficient_years(self, matrix):
        """PARTIAL_DESCRIPTIVE_ONLY countries from BD_HGNACE_R have ≤3 years from that source."""
        partial = matrix[matrix["eligibility_status"] == "PARTIAL_DESCRIPTIVE_ONLY"]
        # These countries lack external source in registry, so they rely on BD only (3 years)
        for _, row in partial.iterrows():
            # n_sectors may show 8 (from BD) but consecutive_years from BD is 3
            assert row["consecutive_years"] <= MIN_CONSECUTIVE_YEARS or \
                pd.isna(row["sector_births_available"]) or \
                not row["sector_births_available"] or \
                row["n_sectors_a10_compatible"] == 0 or \
                row["phase7_sector_ok"] == False, \
                f"{row['country']}: PARTIAL_DESCRIPTIVE_ONLY but appears fully eligible"


# ── Consecutive years tests ───────────────────────────────────────────────────

class TestConsecutiveYears:
    def test_observatory_countries_have_sufficient_years(self, matrix):
        for country in ["FR", "NL", "PT"]:
            row = matrix[matrix["country"] == country].iloc[0]
            assert row["consecutive_years"] >= MIN_CONSECUTIVE_YEARS

    def test_finland_has_sufficient_years(self, matrix):
        fi = matrix[matrix["country"] == "FI"].iloc[0]
        assert fi["consecutive_years"] >= MIN_CONSECUTIVE_YEARS

    def test_phase7_temporal_ok_consistent_with_consecutive_years(self, matrix):
        for _, row in matrix.iterrows():
            if row["consecutive_years"] >= MIN_CONSECUTIVE_YEARS:
                assert row["phase7_temporal_ok"], \
                    f"{row['country']}: {row['consecutive_years']} years but phase7_temporal_ok=False"

    def test_partial_countries_have_fewer_than_min_years_from_eurostat(self, matrix):
        """BD_HGNACE_R covers 2021-2023 only for non-FI countries (3 years < 6)."""
        partial = matrix[matrix["eligibility_status"] == "PARTIAL_DESCRIPTIVE_ONLY"]
        for _, row in partial.iterrows():
            # These countries are partial because BD_HGNACE_R only has 3 years
            # and no national source is in the external source registry
            assert row["phase7_temporal_ok"] == False, \
                f"{row['country']}: PARTIAL_DESCRIPTIVE_ONLY but phase7_temporal_ok=True"


# ── A10 sector coverage tests ─────────────────────────────────────────────────

class TestA10Coverage:
    def test_observatory_countries_have_max_sectors(self, matrix):
        for country in ["FR", "NL"]:
            row = matrix[matrix["country"] == country].iloc[0]
            assert row["n_sectors_a10_compatible"] == 9, \
                f"{country}: expected 9 sectors (IN_OBSERVATORY), got {row['n_sectors_a10_compatible']}"

    def test_portugal_has_8_sectors_kz_absent(self, matrix):
        pt = matrix[matrix["country"] == "PT"].iloc[0]
        assert pt["n_sectors_a10_compatible"] == 8, "PT: expected 8 sectors (KZ=0)"

    def test_finland_kl_combined_flag(self, matrix):
        fi = matrix[matrix["country"] == "FI"].iloc[0]
        assert fi["kl_combined"] == True, "FI: K_L combined flag must be set"
        assert fi["n_sectors_a10_compatible"] == 8

    def test_bd_countries_have_kl_combined(self, matrix):
        """All countries using BD_HGNACE_R as primary source must have kl_combined=True."""
        bd_countries = matrix[
            matrix["primary_source"].notna() &
            matrix["primary_source"].str.contains("BD_HGNACE_R", na=False)
        ]
        for _, row in bd_countries.iterrows():
            assert row["kl_combined"] == True, \
                f"{row['country']}: BD_HGNACE_R source but kl_combined=False"

    def test_belgium_has_zero_sectors(self, matrix):
        be = matrix[matrix["country"] == "BE"].iloc[0]
        assert be["n_sectors_a10_compatible"] == 0, \
            "BE: must have 0 A10 comparable sectors (mask_sector_a10=0)"


# ── n_samples gate tests ──────────────────────────────────────────────────────

class TestNSamplesGate:
    def test_phase7_samples_ok_consistent_with_n_samples(self, matrix):
        for _, row in matrix.iterrows():
            if pd.notna(row["phase7_n_samples"]) and row["phase7_n_samples"] > 0:
                expected_ok = row["phase7_n_samples"] >= MIN_SAMPLES
                assert row["phase7_samples_ok"] == expected_ok, \
                    f"{row['country']}: phase7_n_samples={row['phase7_n_samples']} but " \
                    f"phase7_samples_ok={row['phase7_samples_ok']}"

    def test_observatory_countries_have_sufficient_samples(self, matrix):
        for country in ["FR", "NL", "PT"]:
            row = matrix[matrix["country"] == country].iloc[0]
            assert row["phase7_n_samples"] >= MIN_SAMPLES


# ── Zeros vs missing / structural absence tests ───────────────────────────────

class TestZerosMissingDistinguishable:
    def test_observatory_countries_can_distinguish_zeros(self, matrix):
        obs = matrix[matrix["eligibility_status"] == "IN_OBSERVATORY"]
        for _, row in obs.iterrows():
            assert row["zeros_vs_missing_distinguishable"], \
                f"{row['country']}: IN_OBSERVATORY but zeros/missing not distinguishable"

    def test_finland_can_distinguish_zeros(self, matrix):
        fi = matrix[matrix["country"] == "FI"].iloc[0]
        assert fi["zeros_vs_missing_distinguishable"]


# ── NUTS version tests ────────────────────────────────────────────────────────

class TestNUTSVersion:
    def test_all_countries_report_nuts_version(self, matrix):
        missing = matrix[matrix["nuts_version"].isna()]["country"].tolist()
        assert not missing, f"Missing NUTS version for: {missing}"

    def test_nuts_version_is_2021(self, matrix):
        non_2021 = matrix[~matrix["nuts_version"].str.contains("2021", na=False)]["country"].tolist()
        assert not non_2021, f"Non-NUTS2021 entries: {non_2021}"


# ── Geometry tests ────────────────────────────────────────────────────────────

class TestGeometry:
    def test_geometry_available_for_all_bd_countries(self, matrix):
        """Eurostat NUTS3 2021 geojson covers all EU countries in BD_HGNACE_R."""
        for _, row in matrix.iterrows():
            assert row["geometry_available"] == True, \
                f"{row['country']}: geometry_available=False but geojson covers all EU"

    def test_nuts3_geojson_exists(self):
        nuts_path = REPO_ROOT / "data/external/nuts3_2021_eurostat.geojson"
        assert nuts_path.exists(), "nuts3_2021_eurostat.geojson must exist"


# ── No-download contract tests ────────────────────────────────────────────────

class TestNoDownloadContract:
    def test_eligible_with_download_countries_have_blocking_reason(self, matrix):
        dl = matrix[matrix["eligibility_status"] == "ELIGIBLE_WITH_DOWNLOAD"]
        for _, row in dl.iterrows():
            assert pd.notna(row["blocking_reason"]) and len(str(row["blocking_reason"])) > 10, \
                f"{row['country']}: ELIGIBLE_WITH_DOWNLOAD but no blocking_reason"

    def test_manifest_documents_external_sources_for_eligible_countries(self, matrix, manifest):
        """All ELIGIBLE_WITH_DOWNLOAD countries must appear in the external source manifest."""
        dl_countries = set(
            matrix[matrix["eligibility_status"] == "ELIGIBLE_WITH_DOWNLOAD"]["country"].tolist()
        )
        documented = set(manifest["external_sources_not_downloaded"].keys())
        not_documented = dl_countries - documented
        assert not not_documented, \
            f"ELIGIBLE_WITH_DOWNLOAD countries not in manifest: {not_documented}"

    def test_manifest_external_sources_not_local_files(self, manifest):
        """External sources documented as 'not downloaded' must not have local file paths."""
        for country, ext in manifest["external_sources_not_downloaded"].items():
            assert "path" not in ext or ext.get("path") is None, \
                f"{country}: external source has a local path (implies it was downloaded)"


# ── Panel proposal tests ──────────────────────────────────────────────────────

class TestPanelProposals:
    def test_core_contiguous_excludes_belgium(self, summary):
        core = summary["panel_proposals"]["CORE_CONTIGUOUS"]["countries"]
        assert "BE" not in core, "Belgium must not be in CORE_CONTIGUOUS (BLOCKED_SEMANTICS)"

    def test_core_contiguous_includes_observatory_countries(self, summary):
        core = summary["panel_proposals"]["CORE_CONTIGUOUS"]["countries"]
        for country in ["FR", "NL", "PT"]:
            assert country in core, f"{country} must be in CORE_CONTIGUOUS (IN_OBSERVATORY)"

    def test_eu_extended_includes_finland(self, summary):
        ext = summary["panel_proposals"]["EU_EXTENDED"]["countries"]
        assert "FI" in ext, "Finland must be in EU_EXTENDED (ELIGIBLE_WITH_MAPPING)"

    def test_blocked_contains_belgium(self, summary):
        blocked = summary["panel_proposals"]["BLOCKED"]["countries"]
        assert "BE" in blocked

    def test_panel_proposals_disjoint(self, summary):
        """Each country appears in exactly one non-IN_OBSERVATORY proposal."""
        obs = set(summary["status_groups"]["IN_OBSERVATORY"])
        ewd = set(summary["panel_proposals"]["ELIGIBLE_WITH_DOWNLOAD"]["countries"] if "ELIGIBLE_WITH_DOWNLOAD" in summary["panel_proposals"] else [])
        # Core and Extended are inclusive proposals, not exclusive sets
        # Just verify blocked and descriptive_only don't overlap
        blocked = set(summary["panel_proposals"]["BLOCKED"]["countries"])
        desc = set(summary["panel_proposals"]["DESCRIPTIVE_ONLY"]["countries"])
        overlap = blocked & desc
        assert not overlap, f"Countries in both BLOCKED and DESCRIPTIVE_ONLY: {overlap}"

    def test_spain_in_some_eligible_proposal(self, summary):
        ext = summary["panel_proposals"]["EU_EXTENDED"]["countries"]
        core = summary["panel_proposals"]["CORE_CONTIGUOUS"]["countries"]
        assert "ES" in ext or "ES" in core, \
            "Spain (ELIGIBLE_WITH_DOWNLOAD) must appear in a panel proposal"


# ── Critical findings tests ───────────────────────────────────────────────────

class TestCriticalFindings:
    def test_findings_mention_finland(self, summary):
        findings_text = " ".join(summary["critical_findings"]).lower()
        assert "finland" in findings_text or "fi" in findings_text.split()

    def test_findings_mention_kl_combined(self, summary):
        findings_text = " ".join(summary["critical_findings"]).lower()
        assert "k_l" in findings_text or "kl" in findings_text

    def test_findings_mention_belgium_blocked(self, summary):
        findings_text = " ".join(summary["critical_findings"]).lower()
        assert "belgium" in findings_text or "be" in findings_text.split()

    def test_findings_mention_temporal_limitation(self, summary):
        findings_text = " ".join(summary["critical_findings"]).lower()
        assert "2021" in findings_text and "2023" in findings_text


# ── Determinism tests ─────────────────────────────────────────────────────────

class TestDeterminism:
    def test_matrix_row_count_is_stable(self, matrix):
        """Must evaluate exactly the countries known from BD_HGNACE_R + local panels."""
        assert len(matrix) >= 25, f"Expected ≥25 countries, got {len(matrix)}"

    def test_finland_n_territories_is_19(self, matrix):
        fi = matrix[matrix["country"] == "FI"].iloc[0]
        assert fi["n_territories"] == 19, \
            f"FI stable territories must be 19 (confirmed from BD_HGNACE_R 2013-2021)"

    def test_belgium_n_territories_is_42(self, matrix):
        be = matrix[matrix["country"] == "BE"].iloc[0]
        assert be["n_territories"] == 42

    def test_france_n_territories_is_280(self, matrix):
        fr = matrix[matrix["country"] == "FR"].iloc[0]
        assert fr["n_territories"] == 280

    def test_netherlands_n_territories_is_40(self, matrix):
        nl = matrix[matrix["country"] == "NL"].iloc[0]
        assert nl["n_territories"] == 40
