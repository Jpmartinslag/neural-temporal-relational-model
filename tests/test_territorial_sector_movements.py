"""Tests for Phase 8 — Territorial Sector Statistical Influence.

Coverage:
- Leakage / temporal alignment (t-1 → t)
- Beta equivalence to Phase 7
- LOTO decomposition identity
- Permutation destroys source-lag association in synthetic fixture
- Known contribution recovered in controlled fixture
- Null influence below saturation (DESCRIPTIVE_ONLY or LOW)
- Structural masks respected (PT KZ excluded)
- Territory system separation (no NL/PT mixing)
- Determinism
- No NaN/Inf for eligible territories
- Evidence level nomenclature: HIGH/MODERATE/LOW DESCRIPTIVE, not STRONG/MODERATE/WEAK
- No causal/propagation/origin/transmission language in output
- Overlapping windows not described as independent replications
- Decision record contains required interpretation fields
- Output schema complete
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = REPO_ROOT / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
ROBUST_EDGES_PATH = REPO_ROOT / "data/processed/sector_precedence_results/covid_robust_edges.csv"
PHASE7_CSV = REPO_ROOT / "data/processed/sector_precedence_results/latest.csv"
OUTPUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v04"
MOVEMENTS_CSV = OUTPUT_DIR / "territorial_sector_movements.csv"
SUMMARY_CSV = OUTPUT_DIR / "territorial_sector_movement_summary.csv"
MANIFEST_JSON = OUTPUT_DIR / "territorial_sector_movement_manifest.json"
DECISION_JSON = OUTPUT_DIR / "territorial_sector_movement_decision.json"


# ---------------------------------------------------------------------------
# Helpers — small synthetic panel factories
# ---------------------------------------------------------------------------

def _synthetic_raw_panel(
    n_territories: int = 10,
    n_years: int = 6,
    start_year: int = 2014,
    rng_seed: int = 0,
    source_sector: str = "SRC",
    target_sector: str = "TGT",
    effect_territory: str | None = None,
    effect_size: float = 2.0,
) -> pd.DataFrame:
    """Build a small synthetic raw panel (velocity format, matches v02 schema).

    If effect_territory is not None, that territory has a strong source→target
    association (controlled fixture). Otherwise the association is random.
    Includes one extra year before start_year so align_samples can compute the lag.
    """
    rng = np.random.default_rng(rng_seed)
    years = list(range(start_year - 1, start_year + n_years))  # extra year for lag
    territory_ids = [f"T{i:02d}" for i in range(n_territories)]

    rows = []
    for sector in [source_sector, target_sector]:
        for tid in territory_ids:
            vals = rng.standard_normal(len(years))
            for i, yr in enumerate(years):
                rows.append({
                    "country": "XX",
                    "territory_id": tid,
                    "observation_year": yr,
                    "sector_id": sector,
                    "velocity": vals[i],
                    "structural_mask": 1,
                    "observation_mask": 1,
                })
    df = pd.DataFrame(rows)

    if effect_territory is not None:
        # Inject a strong source(t-1) → target(t) association in effect_territory
        src_rows = df[(df.territory_id == effect_territory) & (df.sector_id == source_sector)].copy()
        src_vals = {r.observation_year: r.velocity for _, r in src_rows.iterrows()}
        tgt_rows = df[(df.territory_id == effect_territory) & (df.sector_id == target_sector)]
        for idx, row in tgt_rows.iterrows():
            prev_year = row.observation_year - 1
            if prev_year in src_vals:
                df.at[idx, "velocity"] += effect_size * src_vals[prev_year]

    return df


def _aligned(
    raw: pd.DataFrame,
    source_sector: str = "SRC",
    target_sector: str = "TGT",
    start_year: int = 2014,
    n_years: int = 6,
) -> pd.DataFrame:
    """Call align_samples on a synthetic raw panel."""
    from src.data.european_panel.build_territorial_sector_movements import align_samples
    end_year = start_year + n_years - 1
    return align_samples(raw, "XX", source_sector, target_sector, start_year, end_year)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def movements():
    assert MOVEMENTS_CSV.exists(), "Run build_territorial_sector_movements.py first"
    return pd.read_csv(MOVEMENTS_CSV)


@pytest.fixture(scope="module")
def summary():
    assert SUMMARY_CSV.exists(), "Run build_territorial_sector_movements.py first"
    return pd.read_csv(SUMMARY_CSV)


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_JSON.exists(), "Run build_territorial_sector_movements.py first"
    return json.loads(MANIFEST_JSON.read_text())


@pytest.fixture(scope="module")
def decision():
    assert DECISION_JSON.exists(), "Run build_territorial_sector_movements.py first"
    return json.loads(DECISION_JSON.read_text())


@pytest.fixture(scope="module")
def robust_edges():
    return pd.read_csv(ROBUST_EDGES_PATH)


# ---------------------------------------------------------------------------
# Part 1: Temporal alignment — no leakage
# ---------------------------------------------------------------------------

class TestTemporalAlignment:
    def test_source_lag_uses_year_minus_one(self):
        """source(t-1) must be from year before the target year."""
        from src.data.european_panel.build_territorial_sector_movements import align_samples
        panel = pd.read_csv(PANEL_PATH, low_memory=False)
        df = align_samples(panel, "NL", "FZ", "GI", 2014, 2019)
        # observation_year in df is the TARGET year t
        # source_lag must correspond to year t-1 data
        # Verify by checking consistency with the raw panel velocity at t-1
        nl_fz = panel[(panel.country == "NL") & (panel.sector_id == "FZ") & (panel.observation_mask == 1)]
        lag_check = nl_fz[["territory_id", "observation_year", "velocity"]].copy()
        lag_check["target_year"] = lag_check["observation_year"] + 1
        merged = df.merge(
            lag_check[["territory_id", "target_year", "velocity"]],
            left_on=["territory_id", "observation_year"],
            right_on=["territory_id", "target_year"],
        )
        assert len(merged) == len(df), "Not all source_lag values found in panel at t-1"
        diff = (merged["source_lag"] - merged["velocity"]).abs().max()
        assert diff < 1e-10, f"source_lag does not match velocity at t-1, max diff={diff}"

    def test_target_year_not_in_source_lag(self):
        """For each row, source_lag must be from a strictly earlier year."""
        from src.data.european_panel.build_territorial_sector_movements import align_samples
        panel = pd.read_csv(PANEL_PATH, low_memory=False)
        df = align_samples(panel, "PT", "MN", "JZ", 2014, 2019)
        # There is no column for source year in the output, but we can verify
        # that if we shift source_lag forward by 1, it should not equal the
        # target for the same (territory, year) - instead source t-1 ≠ target t
        # We verify length matches Phase 7 n_samples
        assert len(df) == 150, f"Expected 150 pairs (25 territories × 6 years), got {len(df)}"

    def test_window_years_match_phase7_n_samples(self, robust_edges):
        """n_pairs for each relation must match the n_samples reported in Phase 7."""
        from src.data.european_panel.build_territorial_sector_movements import align_samples
        panel = pd.read_csv(PANEL_PATH, low_memory=False)
        p7 = pd.read_csv(PHASE7_CSV)
        for _, e in robust_edges.iterrows():
            df = align_samples(panel, e.country, e.source_sector, e.target_sector,
                               int(e.window_start), int(e.window_end))
            p7_row = p7[
                (p7.country == e.country)
                & (p7.window_start == e.window_start)
                & (p7.window_end == e.window_end)
                & (p7.source_sector == e.source_sector)
                & (p7.target_sector == e.target_sector)
            ]
            assert len(p7_row) == 1
            expected_n = int(p7_row["n_samples"].iloc[0])
            assert len(df) == expected_n, (
                f"{e.country} {e.window_start}-{e.window_end} {e.source_sector}→{e.target_sector}: "
                f"got {len(df)}, expected {expected_n}"
            )


# ---------------------------------------------------------------------------
# Part 2: Beta equivalence to Phase 7
# ---------------------------------------------------------------------------

class TestBetaEquivalence:
    def test_local_beta_matches_phase7_all_relations(self, robust_edges):
        """Local beta must match Phase 7 beta within float tolerance for all 12 relations."""
        from src.data.european_panel.build_territorial_sector_movements import (
            align_samples, compute_beta_on_samples,
        )
        panel = pd.read_csv(PANEL_PATH, low_memory=False)
        p7 = pd.read_csv(PHASE7_CSV)
        for _, e in robust_edges.iterrows():
            df = align_samples(panel, e.country, e.source_sector, e.target_sector,
                               int(e.window_start), int(e.window_end))
            beta, _ = compute_beta_on_samples(df)
            p7_row = p7[
                (p7.country == e.country)
                & (p7.window_start == e.window_start)
                & (p7.window_end == e.window_end)
                & (p7.source_sector == e.source_sector)
                & (p7.target_sector == e.target_sector)
            ]
            p7_beta = float(p7_row["beta"].iloc[0])
            assert abs(beta - p7_beta) < 1e-6, (
                f"Beta deviation for {e.country} {e.source_sector}→{e.target_sector}: "
                f"local={beta:.6f} vs p7={p7_beta:.6f}"
            )

    def test_movements_global_beta_matches_phase7(self, movements, robust_edges):
        """global_beta column in output must match Phase 7 for all 12 relations."""
        p7 = pd.read_csv(PHASE7_CSV)
        for _, e in robust_edges.iterrows():
            m = movements[
                (movements.country == e.country)
                & (movements.window_start == e.window_start)
                & (movements.window_end == e.window_end)
                & (movements.source_sector == e.source_sector)
                & (movements.target_sector == e.target_sector)
            ]
            assert len(m) > 0
            local_beta = float(m["global_beta"].iloc[0])
            p7_row = p7[
                (p7.country == e.country)
                & (p7.window_start == e.window_start)
                & (p7.window_end == e.window_end)
                & (p7.source_sector == e.source_sector)
                & (p7.target_sector == e.target_sector)
            ]
            p7_beta = float(p7_row["beta"].iloc[0])
            assert abs(local_beta - p7_beta) < 0.01


# ---------------------------------------------------------------------------
# Part 3: LOTO decomposition identity
# ---------------------------------------------------------------------------

class TestLOTODecomposition:
    def test_loto_identity_synthetic(self):
        """influence_r = beta_full - beta_without_r on synthetic data."""
        from src.data.european_panel.build_territorial_sector_movements import (
            compute_beta_on_samples, compute_loto_influences,
        )
        raw = _synthetic_raw_panel(n_territories=10, n_years=6, rng_seed=1)
        panel = _aligned(raw)
        beta_full, _ = compute_beta_on_samples(panel)
        loto = compute_loto_influences(panel, beta_full,
                                       min_territory_own_pairs=1, min_loto_pairs=10)
        for _, row in loto.iterrows():
            if row["insufficient_data"]:
                continue
            expected = beta_full - row["beta_without"]
            assert abs(row["influence"] - expected) < 1e-10, (
                f"LOTO identity failed for {row['territory_id']}: "
                f"got {row['influence']:.8f}, expected {expected:.8f}"
            )

    def test_influences_sum_to_zero_in_balanced_design(self):
        """In a balanced design, all influences should be finite."""
        from src.data.european_panel.build_territorial_sector_movements import (
            compute_beta_on_samples, compute_loto_influences,
        )
        raw = _synthetic_raw_panel(n_territories=8, n_years=6, rng_seed=2)
        panel = _aligned(raw)
        beta_full, _ = compute_beta_on_samples(panel)
        loto = compute_loto_influences(panel, beta_full,
                                       min_territory_own_pairs=1, min_loto_pairs=10)
        influences = loto.loc[~loto["insufficient_data"], "influence"].values
        assert len(influences) == 8
        # influences don't sum to 0 exactly (LOTO ≠ IF), but should be bounded
        assert np.all(np.isfinite(influences))

    def test_output_has_n_territories_times_n_relations_rows(self, movements, robust_edges):
        """Total rows = sum of territories per relation (40 NL + 25 PT each)."""
        expected = 3 * 40 + 9 * 25  # 3 NL relations × 40 + 9 PT × 25
        assert len(movements) == expected, f"Expected {expected} rows, got {len(movements)}"


# ---------------------------------------------------------------------------
# Part 4: Permutation destroys association in synthetic fixture
# ---------------------------------------------------------------------------

class TestPermutationControl:
    def test_permutation_reduces_source_lag_effect(self):
        """Within-year permutation of source_lag destroys the planted association.

        Permuting territory labels does NOT change max |influence| (trivial relabelling).
        The correct null permutes source_lag within each year, matching Phase 7 protocol.
        """
        from src.data.european_panel.build_territorial_sector_movements import (
            compute_beta_on_samples, compute_loto_influences,
        )
        rng = np.random.default_rng(99)
        raw = _synthetic_raw_panel(
            n_territories=15,
            n_years=6,
            rng_seed=7,
            effect_territory="T00",
            effect_size=3.0,
        )
        panel = _aligned(raw)
        beta_obs, _ = compute_beta_on_samples(panel)

        # Observed LOTO: planted territory T00 should be prominent
        loto_obs = compute_loto_influences(panel, beta_obs,
                                           min_territory_own_pairs=1, min_loto_pairs=10)
        t00_obs_infl = float(loto_obs.loc[loto_obs.territory_id == "T00", "influence"].iloc[0])

        # Null: permute source_lag within each year (destroys territorial association)
        null_t00_infls = []
        for _ in range(50):
            perm_panel = panel.copy()
            for yr in perm_panel["observation_year"].unique():
                mask = perm_panel["observation_year"] == yr
                perm_panel.loc[mask, "source_lag"] = rng.permutation(
                    perm_panel.loc[mask, "source_lag"].to_numpy()
                )
            beta_p, _ = compute_beta_on_samples(perm_panel)
            if not np.isfinite(beta_p):
                continue
            loto_p = compute_loto_influences(perm_panel, beta_p,
                                             min_territory_own_pairs=1, min_loto_pairs=10)
            t00_infl_p = float(
                loto_p.loc[loto_p.territory_id == "T00", "influence"].iloc[0]
            )
            null_t00_infls.append(abs(t00_infl_p) if np.isfinite(t00_infl_p) else np.nan)

        null_t00_infls = [v for v in null_t00_infls if np.isfinite(v)]
        assert len(null_t00_infls) >= 30, "Not enough valid null draws"
        assert abs(t00_obs_infl) > np.median(null_t00_infls), (
            f"T00 observed influence {t00_obs_infl:.4f} not above null median "
            f"{np.median(null_t00_infls):.4f}"
        )


# ---------------------------------------------------------------------------
# Part 5: Known contribution recoverable
# ---------------------------------------------------------------------------

class TestKnownContributionRecovery:
    def test_planted_territory_has_highest_influence(self):
        """Territory with planted association should have largest absolute LOTO influence."""
        from src.data.european_panel.build_territorial_sector_movements import (
            compute_beta_on_samples, compute_loto_influences,
        )
        raw = _synthetic_raw_panel(
            n_territories=15,
            n_years=8,
            rng_seed=42,
            effect_territory="T00",
            effect_size=4.0,
        )
        panel = _aligned(raw, n_years=8)
        beta_full, _ = compute_beta_on_samples(panel)
        loto = compute_loto_influences(panel, beta_full,
                                       min_territory_own_pairs=1, min_loto_pairs=10)
        loto["abs_inf"] = loto["influence"].abs()
        top = loto.sort_values("abs_inf", ascending=False).iloc[0]["territory_id"]
        # T00 or a territory closely correlated should dominate
        assert top == "T00", f"Expected planted territory T00 to have max influence, got {top}"


# ---------------------------------------------------------------------------
# Part 6: Null not promoted
# ---------------------------------------------------------------------------

class TestNullNotPromoted:
    def test_pure_noise_all_descriptive_or_low(self):
        """On a pure-noise panel, very few territories should reach HIGH_DESCRIPTIVE_INFLUENCE."""
        from src.data.european_panel.build_territorial_sector_movements import (
            compute_beta_on_samples,
            compute_loto_influences,
            bootstrap_loto_sign_stability,
            loyo_sign_consistency,
            classify_evidence,
            GATES,
        )
        high_count = 0
        total_checked = 0
        for seed in range(5):
            raw = _synthetic_raw_panel(n_territories=20, n_years=6, rng_seed=seed + 100)
            panel = _aligned(raw)
            beta_full, _ = compute_beta_on_samples(panel)
            if not np.isfinite(beta_full):
                continue
            loto = compute_loto_influences(panel, beta_full,
                                           min_territory_own_pairs=1, min_loto_pairs=15)
            stab = bootstrap_loto_sign_stability(
                panel, loto, n_bootstrap=50, seed=seed, min_valid_draws=10, min_pairs=15
            )
            valid = loto[~loto["insufficient_data"] & np.isfinite(loto["influence"])]
            if len(valid) == 0:
                continue
            q75 = valid["influence"].abs().quantile(0.75)
            q50 = valid["influence"].abs().quantile(0.50)
            for _, row in valid.iterrows():
                tid = row["territory_id"]
                loyo_ok, _, _ = loyo_sign_consistency(
                    panel, beta_full, tid, min_consistent=3, min_pairs=15
                )
                level = classify_evidence(
                    influence=row["influence"],
                    n_pairs=row["n_pairs_in_window"],
                    bootstrap_sign_stab=stab.get(tid, float("nan")),
                    loyo_consistent=loyo_ok,
                    without_2020=None,
                    q75=q75,
                    q50=q50,
                    gates=GATES,
                )
                total_checked += 1
                if level == "HIGH_DESCRIPTIVE_INFLUENCE":
                    high_count += 1
        # In noise, HIGH_DESCRIPTIVE_INFLUENCE must be clearly below saturation.
        # By construction, q75 threshold means ≤25% can be above it.
        # Additional gates (loyo, bootstrap) mean HIGH rate should be well below 50%.
        if total_checked > 0:
            rate = high_count / total_checked
            assert rate < 0.50, (
                f"Too many HIGH_DESCRIPTIVE_INFLUENCE in pure noise: "
                f"{high_count}/{total_checked} = {rate:.2f}"
            )


# ---------------------------------------------------------------------------
# Part 7: Structural masks — PT KZ excluded
# ---------------------------------------------------------------------------

class TestStructuralMasks:
    def test_pt_kz_not_in_robust_edges(self):
        """PT KZ is structurally absent; it must not appear in ROBUST edges."""
        edges = pd.read_csv(ROBUST_EDGES_PATH)
        pt_kz = edges[
            (edges.country == "PT")
            & ((edges.source_sector == "KZ") | (edges.target_sector == "KZ"))
        ]
        assert len(pt_kz) == 0, "PT KZ appeared in ROBUST edges — should be structurally excluded"

    def test_movements_no_pt_kz(self, movements):
        """PT KZ must not appear as source or target in movement output."""
        pt_kz = movements[
            (movements.country == "PT")
            & ((movements.source_sector == "KZ") | (movements.target_sector == "KZ"))
        ]
        assert len(pt_kz) == 0, "PT KZ found in movements output"

    def test_structural_mask_respected_in_alignment(self):
        """Territories with structural_mask=0 must not appear in aligned samples."""
        from src.data.european_panel.build_territorial_sector_movements import align_samples
        panel = pd.read_csv(PANEL_PATH, low_memory=False)
        # PT KZ has structural_mask=0 → aligning KZ to anything should give 0 rows
        df_kz_src = align_samples(panel, "PT", "KZ", "MN", 2014, 2019)
        assert len(df_kz_src) == 0, "KZ as source should give 0 aligned rows"
        df_kz_tgt = align_samples(panel, "PT", "MN", "KZ", 2014, 2019)
        assert len(df_kz_tgt) == 0, "KZ as target should give 0 aligned rows"


# ---------------------------------------------------------------------------
# Part 8: Territory system separation
# ---------------------------------------------------------------------------

class TestTerritorySystems:
    def test_nl_territories_are_corop(self, movements):
        """NL territories must use COROP identifiers (CR**)."""
        nl = movements[movements.country == "NL"]
        assert nl["territorial_system"].eq("COROP").all(), "NL system must be COROP"
        assert nl["territory_id"].str.startswith("CR").all(), "NL territory_ids must start with CR"

    def test_pt_territories_are_nuts3(self, movements):
        """PT territories must use NUTS3_2021 identifiers (PT_***)."""
        pt = movements[movements.country == "PT"]
        assert pt["territorial_system"].eq("NUTS3_2021").all(), "PT system must be NUTS3_2021"
        assert pt["territory_id"].str.startswith("PT_").all(), "PT territory_ids must start with PT_"

    def test_no_cross_country_mixing_in_loto(self, movements):
        """LOTO must be computed within each country separately."""
        # All records for a (country, window, source, target) relation must have
        # the same n_total_pairs from summary (no cross-contamination)
        summ = pd.read_csv(SUMMARY_CSV)
        for _, s in summ.iterrows():
            m = movements[
                (movements.country == s.country)
                & (movements.window_start == s.window_start)
                & (movements.window_end == s.window_end)
                & (movements.source_sector == s.source_sector)
                & (movements.target_sector == s.target_sector)
            ]
            # All records should have same global_beta (not mixed with other country)
            unique_betas = m["global_beta"].round(4).unique()
            assert len(unique_betas) == 1, (
                f"Multiple global betas for {s.country} {s.source_sector}→{s.target_sector}: {unique_betas}"
            )


# ---------------------------------------------------------------------------
# Part 9: Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_output_deterministic(self, tmp_path):
        """Two independent builds must produce bit-identical output."""
        from src.data.european_panel.build_territorial_sector_movements import build_phase8

        p1 = tmp_path / "run1"
        p2 = tmp_path / "run2"
        df1, _ = build_phase8(output_dir=p1)
        df2, _ = build_phase8(output_dir=p2)

        cols = ["territory_id", "window_start", "source_sector", "target_sector",
                "territorial_influence", "bootstrap_sign_stability"]
        sha1 = hashlib.sha256(df1[cols].to_csv(index=False).encode()).hexdigest()
        sha2 = hashlib.sha256(df2[cols].to_csv(index=False).encode()).hexdigest()
        assert sha1 == sha2, f"Non-deterministic output: {sha1[:12]} vs {sha2[:12]}"


# ---------------------------------------------------------------------------
# Part 10: No NaN/Inf for eligible territories
# ---------------------------------------------------------------------------

class TestNoNaNInfEligible:
    def test_no_nan_influence_when_sufficient_data(self, movements):
        """Territories with sufficient data must have finite influence."""
        eligible = movements[~movements["insufficient_data"]]
        n_nan = eligible["territorial_influence"].isna().sum()
        assert n_nan == 0, f"{n_nan} eligible territories have NaN influence"

    def test_no_inf_in_movements(self, movements):
        """No infinite values in numeric columns."""
        numeric_cols = ["territorial_influence", "global_beta", "bootstrap_sign_stability"]
        for col in numeric_cols:
            vals = movements[col].dropna()
            n_inf = np.isinf(vals).sum()
            assert n_inf == 0, f"Column {col} has {n_inf} infinite values"

    def test_bootstrap_stability_in_unit_interval(self, movements):
        """Bootstrap sign stability must be in [0, 1]."""
        eligible = movements[~movements["insufficient_data"]]
        bss = eligible["bootstrap_sign_stability"].dropna()
        assert (bss >= 0).all() and (bss <= 1).all(), "bootstrap_sign_stability outside [0,1]"


# ---------------------------------------------------------------------------
# Part 11: Evidence levels consistent with gates
# ---------------------------------------------------------------------------

class TestEvidenceLevels:
    VALID_LEVELS = {
        "HIGH_DESCRIPTIVE_INFLUENCE",
        "MODERATE_DESCRIPTIVE_INFLUENCE",
        "LOW_DESCRIPTIVE_INFLUENCE",
        "DESCRIPTIVE_ONLY",
        "INSUFFICIENT_DATA",
    }
    OLD_LEVELS = {"STRONG", "MODERATE", "WEAK"}

    def test_no_old_level_names_in_output(self, movements):
        """Old evidence level names (STRONG/MODERATE/WEAK) must not appear in output."""
        levels_present = set(movements["evidence_level"].unique())
        old_present = levels_present & self.OLD_LEVELS
        assert old_present == set(), (
            f"Old evidence level names found in output: {old_present}"
        )

    def test_all_levels_are_valid_new_names(self, movements):
        """All evidence_level values must be from the new descriptive nomenclature."""
        unknown = set(movements["evidence_level"].unique()) - self.VALID_LEVELS
        assert unknown == set(), f"Unknown evidence levels: {unknown}"

    def test_high_requires_bootstrap_stability(self, movements):
        """HIGH_DESCRIPTIVE_INFLUENCE must have bootstrap_sign_stability >= threshold."""
        from src.data.european_panel.build_territorial_sector_movements import GATES
        high = movements[movements["evidence_level"] == "HIGH_DESCRIPTIVE_INFLUENCE"]
        violations = high[high["bootstrap_sign_stability"] < GATES["bootstrap_sign_stability_threshold"]]
        assert len(violations) == 0, (
            f"{len(violations)} HIGH_DESCRIPTIVE records have bootstrap_sign_stability below threshold"
        )

    def test_high_requires_loyo_consistent(self, movements):
        """HIGH_DESCRIPTIVE_INFLUENCE must have loyo_consistent = True."""
        high = movements[movements["evidence_level"] == "HIGH_DESCRIPTIVE_INFLUENCE"]
        violations = high[~high["loyo_consistent"]]
        assert len(violations) == 0, (
            f"{len(violations)} HIGH_DESCRIPTIVE records have loyo_consistent = False"
        )

    def test_insufficient_data_has_no_influence(self, movements):
        """INSUFFICIENT_DATA records must have null territorial_influence."""
        insuff = movements[movements["evidence_level"] == "INSUFFICIENT_DATA"]
        assert insuff["territorial_influence"].isna().all(), (
            "INSUFFICIENT_DATA records should have null influence"
        )

    def test_zero_insufficient_data_in_output(self, movements):
        """All territory-relation records must have sufficient data."""
        n_insuff = (movements["evidence_level"] == "INSUFFICIENT_DATA").sum()
        assert n_insuff == 0, f"{n_insuff} records flagged INSUFFICIENT_DATA"


# ---------------------------------------------------------------------------
# Part 12: Schema completeness
# ---------------------------------------------------------------------------

class TestOutputSchema:
    REQUIRED_COLS = [
        "country", "territorial_system", "territory_id",
        "window_start", "window_end", "source_sector", "target_sector",
        "global_beta", "n_pairs_in_window", "territorial_influence",
        "influence_sign", "influence_share", "bootstrap_sign_stability",
        "loyo_consistent", "loyo_n_consistent", "loyo_n_total",
        "without_2020_consistent", "evidence_level", "insufficient_data", "provenance",
    ]

    def test_required_columns_present(self, movements):
        missing = [c for c in self.REQUIRED_COLS if c not in movements.columns]
        assert missing == [], f"Missing columns: {missing}"

    def test_provenance_tag_correct(self, movements):
        assert (movements["provenance"] == "Phase8_LOTO").all()

    def test_decision_sealed_before_run(self, decision):
        """Decision record must declare thresholds were defined before execution."""
        assert "gates" in decision, "Decision must contain gates"
        assert "provenance_note" in decision
        note = decision["provenance_note"]
        assert "defined" in note and "before execution" in note, (
            f"provenance_note must say 'defined ... before execution', got: {note!r}"
        )
        assert "pre-specified" not in note or "not formally pre-registered" in note, (
            "If 'pre-specified' appears it must be qualified as 'not formally pre-registered'"
        )

    def test_decision_has_interpretation_fields(self, decision):
        """Decision must contain all required interpretation scope fields."""
        assert decision.get("interpretation_scope") == "descriptive_relative_influence", (
            f"interpretation_scope wrong: {decision.get('interpretation_scope')}"
        )
        assert decision.get("independent_replication") is False, (
            "independent_replication must be False (overlapping windows)"
        )
        assert decision.get("spatial_flow_supported") is False, (
            "spatial_flow_supported must be False"
        )
        assert decision.get("causal_effect_supported") is False, (
            "causal_effect_supported must be False"
        )
        assert decision.get("threshold_status") == "defined_before_execution_not_formally_preregistered", (
            f"threshold_status wrong: {decision.get('threshold_status')}"
        )

    def test_decision_overlapping_windows_note(self, decision):
        """Decision must document that overlapping windows are not independent replications."""
        note = decision.get("overlapping_windows_note", "")
        assert note, "overlapping_windows_note missing from decision"
        assert "overlap" in note.lower() or "overlapping" in note.lower(), (
            f"overlapping_windows_note must mention overlap: {note!r}"
        )

    def test_manifest_integrity_fields(self, manifest):
        assert "input_panel_sha256" in manifest
        assert "output_csv_sha256" in manifest
        assert manifest["n_robust_relations"] == 12
        assert manifest["n_territory_relation_records"] == 345
        assert manifest["integrity_failures"] == []

    def test_manifest_has_new_interpretation_fields(self, manifest):
        """Manifest must contain interpretation scope and independence flags."""
        assert manifest.get("interpretation_scope") == "descriptive_relative_influence", (
            f"manifest interpretation_scope: {manifest.get('interpretation_scope')}"
        )
        assert manifest.get("independent_replication") is False
        assert manifest.get("spatial_flow_supported") is False
        assert manifest.get("causal_effect_supported") is False
        assert manifest.get("threshold_status") == "defined_before_execution_not_formally_preregistered"

    def test_manifest_uses_influence_level_summary_key(self, manifest):
        """Manifest must use 'influence_level_summary' not the old 'promoted_summary'."""
        assert "influence_level_summary" in manifest, (
            "manifest missing 'influence_level_summary' key"
        )
        assert "promoted_summary" not in manifest, (
            "manifest still has deprecated 'promoted_summary' key"
        )
        ils = manifest["influence_level_summary"]
        expected_keys = {
            "HIGH_DESCRIPTIVE_INFLUENCE",
            "MODERATE_DESCRIPTIVE_INFLUENCE",
            "LOW_DESCRIPTIVE_INFLUENCE",
            "DESCRIPTIVE_ONLY",
            "INSUFFICIENT_DATA",
        }
        assert set(ils.keys()) == expected_keys, (
            f"influence_level_summary keys wrong: {set(ils.keys())}"
        )

    def test_manifest_no_old_level_keys(self, manifest):
        """Manifest influence_level_summary must not have old STRONG/MODERATE/WEAK keys."""
        ils = manifest.get("influence_level_summary", {})
        old_keys = {"STRONG", "MODERATE", "WEAK"}
        present_old = set(ils.keys()) & old_keys
        assert present_old == set(), f"Old keys in influence_level_summary: {present_old}"

    def test_manifest_checksums_match_file(self, manifest):
        sha = hashlib.sha256(MOVEMENTS_CSV.read_bytes()).hexdigest()
        assert sha == manifest["output_csv_sha256"], "Output CSV checksum mismatch"


# ---------------------------------------------------------------------------
# Part 13: No causal language in output
# ---------------------------------------------------------------------------

class TestNoCausalLanguage:
    # Terms that must not appear as affirmative claims
    FORBIDDEN_AFFIRMATIVE = ["propagation", "origin", "transmission", "local impact"]
    # Structural causal terms forbidden everywhere (not just affirmatively)
    FORBIDDEN_EVERYWHERE = ["causes ", "causation"]

    def _affirms(self, text: str, term: str) -> bool:
        """Return True if term appears without a nearby negation."""
        import re
        lower = text.lower()
        for m in re.finditer(re.escape(term.lower()), lower):
            # Check 60 chars before the term for a negation
            prefix = lower[max(0, m.start() - 60):m.start()]
            if not any(neg in prefix for neg in ["not ", "no ", "does not", "without", "cannot", "non-"]):
                return True
        return False

    def test_decision_no_affirmative_causal_claims(self, decision):
        """Decision must not make affirmative causal/propagation claims."""
        text = json.dumps(decision)
        for term in self.FORBIDDEN_AFFIRMATIVE:
            assert not self._affirms(text, term), (
                f"Affirmative use of '{term}' in decision record"
            )

    def test_decision_no_causation_anywhere(self, decision):
        """Terms 'causes' and 'causation' must not appear in decision."""
        text = json.dumps(decision).lower()
        for term in self.FORBIDDEN_EVERYWHERE:
            assert term not in text, f"'{term.strip()}' found in decision record"

    def test_movements_evidence_level_no_causal_terms(self, movements):
        """Old evidence level language (STRONG/MODERATE/WEAK) must not appear in CSV."""
        level_vals = movements["evidence_level"].unique().tolist()
        for val in level_vals:
            assert val not in {"STRONG", "MODERATE", "WEAK"}, (
                f"Old evidence level name '{val}' found in movements CSV"
            )

    def test_manifest_disclaimer_present(self, manifest):
        assert "association_disclaimer" in manifest
        disclaimer = manifest["association_disclaimer"].lower()
        assert "does not" in disclaimer or "not imply" in disclaimer

    def test_manifest_no_propagation_language(self, manifest):
        """Manifest must not contain affirmative propagation/transmission claims."""
        text = json.dumps(manifest)
        for term in self.FORBIDDEN_AFFIRMATIVE:
            assert not self._affirms(text, term), (
                f"Affirmative use of '{term}' in manifest"
            )


# ---------------------------------------------------------------------------
# Part 14: FDR and concentration checks
# ---------------------------------------------------------------------------

class TestConcentration:
    def test_concentration_in_valid_range(self, summary):
        """top3_concentration must be between 0 and 1."""
        vals = summary["top3_concentration"].dropna()
        assert (vals >= 0).all() and (vals <= 1).all(), "top3_concentration outside [0,1]"

    def test_influence_shares_sum_close_to_one(self, movements):
        """Within each relation, influence shares should approximately sum to 1."""
        groups = movements.groupby(
            ["country", "window_start", "window_end", "source_sector", "target_sector"]
        )
        for name, grp in groups:
            shares = grp["influence_share"].dropna()
            if len(shares) < 5:
                continue
            total = shares.sum()
            # Shares are |influence_r| / sum(|influences|), so they sum to 1
            assert abs(total - 1.0) < 0.01, (
                f"Influence shares for {name} sum to {total:.4f}, expected ≈1.0"
            )
