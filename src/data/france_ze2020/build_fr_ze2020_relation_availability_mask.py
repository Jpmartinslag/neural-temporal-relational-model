"""Build the France ZE2020 relational availability mask.

This artifact answers one question per relation family and decision year:

    is a relation available for this family at this decision year, and if not,
    why not?

It exists because relational unavailability in this project is expressed as an
*absent row*, not as a flag.  ``fr_ze2020_temporal_relation_signals.csv.gz``
simply has no rows before 2017, and
``fr_ze2020_commuting_strict_ex_ante_edges.csv.gz`` has none before 2016.  A
consumer that joins on ``decision_year`` without counting rows cannot see the
gap, and a year with zero edges is indistinguishable from a year whose
relations are merely weak.  DEC-065 is the precedent for how expensive that
confusion is.

The mask is a standalone table.  It never modifies a canonical artifact: every
input is opened read-only and its SHA-256 is recorded before and after the run.

Status vocabulary
-----------------
``observed``
    The relation is observed at its own decision year.  No current family
    satisfies this; the value is retained because a future directly observed
    relation source would need it.
``carried_forward_from_snapshot``
    A real observation exists, but from an earlier year, carried forward under
    a release-aware rule.  Commuting.
``derived_available``
    The relation is computed from causal lag features rather than observed.
    The three temporal signal families.
``unavailable``
    No relation exists for this family and decision year.

Unavailable reasons
-------------------
``source_not_released``
    The upstream source had not been published by the decision year.
``insufficient_history``
    The causal feature the relation is derived from does not yet have enough
    non-null years at the decision year.
``not_constructed``
    The family is documented as planned but was never built.

This builder produces no model input, no metric, and no claim.  It is a
provenance and availability artifact only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROCESSED_DIR = ROOT / "data/processed/france_ze2020"
SIGNALS_PATH = PROCESSED_DIR / "fr_ze2020_temporal_relation_signals.csv.gz"
COMMUTING_PATH = PROCESSED_DIR / "fr_ze2020_commuting_strict_ex_ante_edges.csv.gz"
SECTOR_PANEL_PATH = PROCESSED_DIR / "fr_ze2020_sector_panel.csv"

DEFAULT_OUT_DIR = PROCESSED_DIR
OUT_NAME = "fr_ze2020_relation_availability_mask.csv"
SUMMARY_NAME = "fr_ze2020_relation_availability_mask_summary.json"

PANEL_YEARS = tuple(range(2012, 2026))

STATUS_OBSERVED = "observed"
STATUS_CARRIED_FORWARD = "carried_forward_from_snapshot"
STATUS_DERIVED = "derived_available"
STATUS_UNAVAILABLE = "unavailable"
VALID_STATUSES = frozenset(
    {STATUS_OBSERVED, STATUS_CARRIED_FORWARD, STATUS_DERIVED, STATUS_UNAVAILABLE}
)

REASON_NOT_RELEASED = "source_not_released"
REASON_INSUFFICIENT_HISTORY = "insufficient_history"
REASON_NOT_CONSTRUCTED = "not_constructed"
VALID_REASONS = frozenset(
    {REASON_NOT_RELEASED, REASON_INSUFFICIENT_HISTORY, REASON_NOT_CONSTRUCTED}
)

# Families derived from causal lag features by
# build_fr_ze2020_temporal_relation_signals.py.  Each correlates a growth
# history with pandas `corr(min_periods=3)` over years strictly < t.  The
# underlying growth features (growth_1y_safe, sector_growth_lag_1) have their
# first non-null year at 2014, so the first decision year with three non-null
# prior years is 2017.  This is the documented mechanism behind the 2012-2016
# gap; it is not an inference from the output.
DERIVED_FAMILIES = ("ze_similarity", "cross_ze_same_sector", "intra_ze_sector")
DERIVED_FIRST_YEAR = 2017
DERIVED_GROWTH_FEATURE_FIRST_YEAR = 2014
DERIVED_MIN_HISTORY_YEARS = 3

COMMUTING_FAMILY = "commuting_strict_ex_ante"

# Families specified in HERALD_20 section 2 as deliberately not populated.
# Recording them keeps the mask honest about planned-but-absent structure
# instead of omitting them silently.
NOT_CONSTRUCTED_FAMILIES = ("sector_to_sector_comovement", "temporal_precedence_signal")

ZE_TOP_K = 5

OUTPUT_COLUMNS = [
    "relation_family",
    "decision_year",
    "availability_status",
    "unavailable_reason",
    "source_snapshot_year",
    "source_release_date",
    "snapshot_age_years",
    "expected_edge_count",
    "actual_edge_count",
    "provenance",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _derived_expected_count(family: str, n_zones: int, n_sectors: int) -> int | None:
    """Structural expectation, only where a documented formula exists.

    `ze_similarity` keeps the top-k positive correlations per zone and repeats
    the pair for every sector, giving zones x k x sectors.  The two sector
    families select over available pairs with no documented closed form, so
    their expectation is left unknown rather than back-filled from the output.
    """
    if family == "ze_similarity":
        return n_zones * ZE_TOP_K * n_sectors
    return None


def build_mask(
    signals_path: Path = SIGNALS_PATH,
    commuting_path: Path = COMMUTING_PATH,
    sector_panel_path: Path = SECTOR_PANEL_PATH,
) -> pd.DataFrame:
    signals = pd.read_csv(signals_path)
    commuting = pd.read_csv(commuting_path, dtype={"source_release_date": str})
    sector_panel = pd.read_csv(sector_panel_path, dtype={"ze2020": str})

    n_zones = sector_panel["ze2020"].nunique()
    n_sectors = sector_panel["sector_code"].nunique()

    signal_counts = (
        signals.groupby(["relation_family", "decision_year"]).size().to_dict()
    )
    commuting_counts = commuting.groupby("decision_year").size().to_dict()
    commuting_meta = (
        commuting.groupby("decision_year")
        .agg(
            observation_year=("observation_year", "first"),
            source_release_date=("source_release_date", "first"),
            snapshot_age_years=("snapshot_age_years", "first"),
        )
        .to_dict("index")
    )

    rows: list[dict[str, object]] = []

    for family in DERIVED_FAMILIES:
        for year in PANEL_YEARS:
            actual = int(signal_counts.get((family, year), 0))
            if year >= DERIVED_FIRST_YEAR:
                rows.append(
                    {
                        "relation_family": family,
                        "decision_year": year,
                        "availability_status": STATUS_DERIVED,
                        "unavailable_reason": "",
                        "source_snapshot_year": "",
                        "source_release_date": "",
                        "snapshot_age_years": "",
                        "expected_edge_count": _derived_expected_count(
                            family, n_zones, n_sectors
                        ),
                        "actual_edge_count": actual,
                        "provenance": (
                            "fr_ze2020_temporal_relation_signals.csv.gz via "
                            "build_fr_ze2020_temporal_relation_signals.py; "
                            "derived from causal lag features, not observed"
                        ),
                    }
                )
            else:
                rows.append(
                    {
                        "relation_family": family,
                        "decision_year": year,
                        "availability_status": STATUS_UNAVAILABLE,
                        "unavailable_reason": REASON_INSUFFICIENT_HISTORY,
                        "source_snapshot_year": "",
                        "source_release_date": "",
                        "snapshot_age_years": "",
                        "expected_edge_count": None,
                        "actual_edge_count": actual,
                        "provenance": (
                            "growth feature first non-null year "
                            f"{DERIVED_GROWTH_FEATURE_FIRST_YEAR} and "
                            f"corr(min_periods={DERIVED_MIN_HISTORY_YEARS}) over years "
                            f"strictly < t require t >= {DERIVED_FIRST_YEAR}"
                        ),
                    }
                )

    for year in PANEL_YEARS:
        actual = int(commuting_counts.get(year, 0))
        meta = commuting_meta.get(year)
        if meta is not None:
            rows.append(
                {
                    "relation_family": COMMUTING_FAMILY,
                    "decision_year": year,
                    "availability_status": STATUS_CARRIED_FORWARD,
                    "unavailable_reason": "",
                    "source_snapshot_year": int(meta["observation_year"]),
                    "source_release_date": str(meta["source_release_date"]),
                    "snapshot_age_years": int(meta["snapshot_age_years"]),
                    "expected_edge_count": None,
                    "actual_edge_count": actual,
                    "provenance": (
                        "fr_ze2020_commuting_strict_ex_ante_edges.csv.gz via "
                        "build_fr_ze2020_commuting_strict_ex_ante_edges.py; "
                        "official INSEE flow snapshot carried forward under a "
                        "release-aware rule (DEC-073)"
                    ),
                }
            )
        else:
            rows.append(
                {
                    "relation_family": COMMUTING_FAMILY,
                    "decision_year": year,
                    "availability_status": STATUS_UNAVAILABLE,
                    "unavailable_reason": REASON_NOT_RELEASED,
                    "source_snapshot_year": "",
                    "source_release_date": "",
                    "snapshot_age_years": "",
                    "expected_edge_count": None,
                    "actual_edge_count": actual,
                    "provenance": (
                        "no official commuting snapshot had been released by this "
                        "decision year; the earliest snapshot (observation 2012) was "
                        "released 2015-06-25 (DEC-073)"
                    ),
                }
            )

    for family in NOT_CONSTRUCTED_FAMILIES:
        for year in PANEL_YEARS:
            rows.append(
                {
                    "relation_family": family,
                    "decision_year": year,
                    "availability_status": STATUS_UNAVAILABLE,
                    "unavailable_reason": REASON_NOT_CONSTRUCTED,
                    "source_snapshot_year": "",
                    "source_release_date": "",
                    "snapshot_age_years": "",
                    "expected_edge_count": None,
                    "actual_edge_count": 0,
                    "provenance": (
                        "documented as planned but never built; see HERALD_20 section 2 "
                        "(no grain reconciliation with Phase 7, no signed-precedence "
                        "test at ZE2020 grain)"
                    ),
                }
            )

    mask = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    # Nullable integer, so an unknown expectation stays blank in the CSV instead
    # of becoming a float ("12600.0") through NaN promotion.
    mask["expected_edge_count"] = mask["expected_edge_count"].astype("Int64")
    mask["actual_edge_count"] = mask["actual_edge_count"].astype("Int64")
    return mask.sort_values(["relation_family", "decision_year"]).reset_index(drop=True)


def validate_mask(mask: pd.DataFrame) -> None:
    """Fail closed.  Every check here encodes a defect this artifact exists to
    prevent, so a violation must stop the build rather than be reported."""
    families = sorted(mask["relation_family"].unique())
    expected_families = sorted(
        set(DERIVED_FAMILIES) | {COMMUTING_FAMILY} | set(NOT_CONSTRUCTED_FAMILIES)
    )
    assert families == expected_families, f"family set drift: {families}"

    # Every family x year cell must exist and be classified exactly once.
    expected_cells = len(expected_families) * len(PANEL_YEARS)
    assert len(mask) == expected_cells, f"expected {expected_cells} rows, got {len(mask)}"
    assert not mask.duplicated(["relation_family", "decision_year"]).any(), "duplicate cell"
    for family in expected_families:
        years = sorted(mask.loc[mask["relation_family"] == family, "decision_year"])
        assert years == list(PANEL_YEARS), f"{family} does not cover {PANEL_YEARS}"

    assert mask["availability_status"].isin(VALID_STATUSES).all(), "unknown status"
    assert mask["availability_status"].notna().all(), "unclassified cell"
    assert (mask["availability_status"].astype(str).str.len() > 0).all(), "empty status"

    unavailable = mask["availability_status"] == STATUS_UNAVAILABLE
    assert mask.loc[unavailable, "unavailable_reason"].isin(VALID_REASONS).all(), (
        "unavailable row without a valid reason"
    )
    assert (mask.loc[~unavailable, "unavailable_reason"].astype(str) == "").all(), (
        "available row carries an unavailable_reason"
    )

    # An available family-year must actually contain edges.  Zero edges under an
    # available status would be silent emptiness, which is precisely the
    # confusion this mask exists to remove.
    available = ~unavailable
    assert (mask.loc[available, "actual_edge_count"] > 0).all(), (
        "available family-year with zero edges: availability and emptiness must not "
        "be conflated"
    )

    # Structural expectation, where a documented formula exists, must hold.
    has_expected = mask["expected_edge_count"].notna()
    checked = mask.loc[has_expected & available]
    assert (
        checked["expected_edge_count"].astype(int) == checked["actual_edge_count"].astype(int)
    ).all(), "expected vs actual edge-count mismatch"

    # The two gaps this artifact was created to make explicit.
    commuting = mask[mask["relation_family"] == COMMUTING_FAMILY]
    gap = commuting[commuting["decision_year"] <= 2015]
    assert (gap["availability_status"] == STATUS_UNAVAILABLE).all(), (
        "commuting 2012-2015 must be explicitly unavailable"
    )
    assert (gap["unavailable_reason"] == REASON_NOT_RELEASED).all(), (
        "commuting 2012-2015 reason must be source_not_released"
    )

    for family in DERIVED_FAMILIES:
        rows = mask[mask["relation_family"] == family]
        early = rows[rows["decision_year"] < DERIVED_FIRST_YEAR]
        assert (early["availability_status"] == STATUS_UNAVAILABLE).all(), (
            f"{family} 2012-2016 must be explicitly unavailable"
        )
        assert (early["unavailable_reason"] == REASON_INSUFFICIENT_HISTORY).all(), (
            f"{family} 2012-2016 reason must be insufficient_history"
        )
        late = rows[rows["decision_year"] >= DERIVED_FIRST_YEAR]
        assert (late["availability_status"] == STATUS_DERIVED).all(), (
            f"{family} from {DERIVED_FIRST_YEAR} must be derived_available, never observed"
        )

    # Derived relations are computed, not observed.  Guard the vocabulary.
    derived_rows = mask["relation_family"].isin(DERIVED_FAMILIES)
    assert (mask.loc[derived_rows, "availability_status"] != STATUS_OBSERVED).all(), (
        "a computed relation must never be labelled observed"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals-path", type=Path, default=SIGNALS_PATH)
    parser.add_argument("--commuting-path", type=Path, default=COMMUTING_PATH)
    parser.add_argument("--sector-panel-path", type=Path, default=SECTOR_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    inputs = {
        "signals": args.signals_path,
        "commuting": args.commuting_path,
        "sector_panel": args.sector_panel_path,
    }
    before = {name: sha256(path) for name, path in inputs.items()}

    mask = build_mask(args.signals_path, args.commuting_path, args.sector_panel_path)
    validate_mask(mask)

    after = {name: sha256(path) for name, path in inputs.items()}
    unchanged = before == after
    assert unchanged, "an input artifact changed during the run; inputs are read-only"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / OUT_NAME
    mask.to_csv(out_path, index=False)

    status_counts = mask["availability_status"].value_counts().to_dict()
    reason_counts = (
        mask.loc[mask["unavailable_reason"] != "", "unavailable_reason"]
        .value_counts()
        .to_dict()
    )
    summary = {
        "artifact": "fr_ze2020_relation_availability_mask",
        "status": "REGENERABLE_PROVENANCE_ARTIFACT",
        "claim_status": "availability_provenance_only_not_model_input",
        "decision_year_min": min(PANEL_YEARS),
        "decision_year_max": max(PANEL_YEARS),
        "family_count": int(mask["relation_family"].nunique()),
        "row_count": int(len(mask)),
        "status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "unavailable_reason_counts": {str(k): int(v) for k, v in reason_counts.items()},
        "observed_status_used": bool((mask["availability_status"] == STATUS_OBSERVED).any()),
        "input_sha256": before,
        "inputs_unchanged": unchanged,
        "output_sha256": sha256(out_path),
        "notes": (
            "Standalone availability mask. Canonical artifacts are read-only inputs and "
            "were verified unchanged by SHA-256 before and after the run. The 'observed' "
            "status is unused because no current relation family observes at its own "
            "decision year. See HERALD_57 and DEC-082."
        ),
    }
    summary_path = args.output_dir / SUMMARY_NAME
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {out_path} ({len(mask)} rows)")
    print(f"Wrote {summary_path}")
    print(f"Statuses: {status_counts}")
    print(f"Unavailable reasons: {reason_counts}")
    print(f"Inputs unchanged: {unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
