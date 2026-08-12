"""Guards for HERALD 90 stage 1: the real-signal audit and the cheap tournament.

NumPy and stdlib only. ``python3 tests/test_herald90_guards.py`` runs every guard.

The guards cover the mechanisms stage 1 actually uses. Guards for the synthetic generator,
the multisignal oracle and the neural arms are not written here, because those stages are
not authorised: writing their guards would imply an authorisation the tournament has not
granted.
"""
from __future__ import annotations

import csv
import inspect
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.modeles.france_ze2020 import herald90_signal_audit as h90  # noqa: E402

_cache: dict = {}


def zones() -> list[str]:
    if "zones" not in _cache:
        _cache["zones"] = h90.canonical_zones()
    return _cache["zones"]


def signal(measure: str = "urssaf_employer_establishments") -> dict:
    key = f"signal::{measure}"
    if key not in _cache:
        _cache[key] = h90.load_signal(measure, zones())
    return _cache[key]


def commuting() -> np.ndarray:
    if "commuting" not in _cache:
        _cache["commuting"] = h90.commuting_matrix(zones(), 2019)
    return _cache["commuting"]


# 1 ── release dates are respected ───────────────────────────────────────────

def test_g1_only_released_rows_are_loaded():
    """A panel row marked unavailable must never become a value."""
    observed = 0
    with h90.PANEL.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if (row["measure"] == "urssaf_employer_establishments"
                    and row["sector"] == "TOTAL" and row["availability_mask"] == "0"):
                observed += 1
    loaded = signal()
    assert np.isfinite(loaded["values"][loaded["mask"]]).all()
    assert not np.isfinite(loaded["values"][~loaded["mask"]]).any(), (
        "a masked cell arrived as a number")
    source = inspect.getsource(h90.load_signal)
    assert 'availability_mask' in source and 'release_date' in source


# 2 ── the future target never enters the features ──────────────────────────

def test_g2_features_are_strictly_lagged():
    design = h90._design(signal(), None)
    values = signal()["values"]
    with np.errstate(divide="ignore", invalid="ignore"):
        level = np.log(np.maximum(values, 1e-6))
    assert np.allclose(np.nan_to_num(design["y"]), np.nan_to_num(level[1:]), equal_nan=False)
    # Column 1 is the lagged level: it must equal level[:-1], never level[1:].
    assert np.allclose(np.nan_to_num(design["x"][..., 1]),
                       np.nan_to_num(level[:-1]))
    assert not np.allclose(np.nan_to_num(design["x"][..., 1]),
                           np.nan_to_num(level[1:]))


# 3 ── absence is never turned into zero ────────────────────────────────────

def test_g3_absence_stays_absent():
    loaded = signal("establishment_creations")
    assert np.isnan(loaded["values"][~loaded["mask"]]).all()
    # The French panel happens to be complete for these measures, so a guard that only
    # counted its gaps would be vacuous. A hole is punched here on purpose, and the design
    # must propagate it as an exclusion rather than as a zero level.
    holed = {key: (value.copy() if isinstance(value, np.ndarray) else value)
             for key, value in loaded.items()}
    holed["values"][2, :10] = np.nan
    holed["mask"][2, :10] = False
    design = h90._design(holed, None)
    expected = int((~(holed["mask"][:-1] & holed["mask"][1:])).sum())
    assert expected >= 20, "the injected hole did not reach the design"
    assert (~design["usable"]).sum() == expected, (
        "a missing cell was carried into the fit instead of being excluded")


# 4 ── methodological breaks are nuisance regressors ────────────────────────

def test_g4_breaks_are_modelled_not_read_as_dynamics():
    with_breaks = h90._design(signal(), None, breaks=True)
    without = h90._design(signal(), None, breaks=False)
    expected = len(h90.URSSAF_BREAK_YEARS) + len(h90.COVID_YEARS)
    assert with_breaks["x"].shape[-1] - without["x"].shape[-1] == expected, (
        "break indicators are missing from the baseline")
    assert h90.URSSAF_BREAK_YEARS == (2021, 2023)


# 5 ── the placebo cannot smuggle in the national mean ──────────────────────

def test_g5_national_mean_lives_in_the_baseline():
    base = h90._design(signal(), None)
    withgraph = h90._design(signal(), commuting())
    # The national column is present in both, so a placebo cannot win by adding it.
    assert base["x"].shape[-1] + 1 == withgraph["x"].shape[-1]
    national_base = base["x"][..., 3]
    national_graph = withgraph["x"][..., 3]
    assert np.allclose(np.nan_to_num(national_base), np.nan_to_num(national_graph))
    assert np.nanstd(national_base) > 0, "the national column is constant"


# 6 ── the permutation is a derangement ─────────────────────────────────────

def test_g6_permutation_moves_every_zone():
    matrix = commuting()
    permuted = h90.derangement(matrix, 9001)
    assert not np.array_equal(matrix, permuted)
    assert np.allclose(np.sort(matrix, axis=None), np.sort(permuted, axis=None))
    assert np.array_equal(np.sort((matrix > 0).sum(1)), np.sort((permuted > 0).sum(1)))


# 7 ── the random control matches the degree ────────────────────────────────

def test_g7_random_control_matches_degree_and_weights():
    matrix = commuting()
    random_graph = h90.degree_matched_random(matrix, 9001)
    assert np.array_equal((matrix > 0).sum(1), (random_graph > 0).sum(1)), (
        "the random control does not preserve out-degree")
    assert not np.array_equal(matrix > 0, random_graph > 0)
    rows = random_graph.sum(1)
    assert np.allclose(rows[rows > 0], 1.0), "rows are not renormalised"


# 8 ── no self-loop can carry the signal ────────────────────────────────────

def test_g8_no_self_loop():
    for matrix in (commuting(), h90.derangement(commuting(), 9001),
                   h90.degree_matched_random(commuting(), 9001)):
        assert np.allclose(np.diag(matrix), 0.0), "a zone is its own neighbour"


# 9 ── coefficients are never fitted on the scored period ───────────────────

def test_g9_no_coefficient_is_fitted_on_the_scored_period():
    design = h90._design(signal(), commuting())
    train, score = list(range(10)), 12
    base = h90._fit_score(design, train, score)
    perturbed = {key: (value.copy() if isinstance(value, np.ndarray) else value)
                 for key, value in design.items()}
    perturbed["y"][score] *= 5.0
    moved = h90._fit_score(perturbed, train, score)
    assert base["neighbour_beta"] == moved["neighbour_beta"], (
        "changing the scored period moved a fitted coefficient")


# 10 ── the direction gate is applied, not asserted ─────────────────────────

def test_g10_direction_gate_actually_decides():
    good = {"status": "scored", "commuting_vs_permuted": 0.05,
            "commuting_vs_random": 0.04, "gain_vs_local": {"B1_commuting": 0.03},
            "fold_share_favouring_commuting": 0.9,
            "by_target_year": {2020: 0.8, 2021: 0.9, 2022: 0.7}}
    assert h90.relation_informative(good)["passes"] is True
    for key, value in (("commuting_vs_permuted", -0.01),
                       ("commuting_vs_random", -0.01),
                       ("fold_share_favouring_commuting", 0.4)):
        bad = dict(good); bad[key] = value
        assert h90.relation_informative(bad)["passes"] is False, (
            f"the gate ignored {key}")
    assert h90.relation_informative({"status": "too_short"})["passes"] is False


# 11 ── zone codes stay four-character strings ──────────────────────────────

def test_g11_zone_codes_are_four_character_strings():
    codes = zones()
    assert len(codes) == 280
    assert all(isinstance(code, str) and len(code) == 4 and code.isdigit()
               for code in codes)
    assert commuting().shape == (280, 280)


# 12 ── a duplicated signal is not new evidence ─────────────────────────────

def test_g12_duplicating_a_signal_adds_no_independent_information():
    """Stacking the same regressor twice must not improve the fit.

    The stage-5 arm A6 rests on this arithmetic: a collinear copy carries no extra
    information, so any gain it appears to produce would be an artefact.
    """
    design = h90._design(signal(), commuting())
    doubled = {key: (value.copy() if isinstance(value, np.ndarray) else value)
               for key, value in design.items()}
    doubled["x"] = np.concatenate([design["x"], design["x"][..., -1:]], axis=-1)
    train, score = list(range(10)), 12
    assert abs(h90._fit_score(design, train, score)["sse"]
               - h90._fit_score(doubled, train, score)["sse"]) < 1e-6, (
        "a duplicated regressor changed the fit")


# 13 ── stage authorisation follows the tournament ──────────────────────────

def test_g13_multisignal_stage_needs_two_informative_signals():
    two = {"a": {"passes": True}, "b": {"passes": True}, "c": {"passes": False}}
    one = {"a": {"passes": True}, "b": {"passes": False}}
    none = {"a": {"passes": False}}
    assert h90.authorise_multisignal_oracle(two)["authorises_multisignal_oracle"] is True
    decided = h90.authorise_multisignal_oracle(one)
    assert decided["authorises_multisignal_oracle"] is False, (
        "one informative signal authorised a multisignal stage")
    assert decided["authorises_single_signal_followup"] is True
    assert h90.authorise_multisignal_oracle(none)["authorises_single_signal_followup"] is False


def _main() -> int:
    names = sorted((name for name in globals() if name.startswith("test_")),
                   key=lambda n: int(n.split("_")[1][1:]))
    failures = 0
    for name in names:
        try:
            globals()[name]()
            print(f"PASS  {name}")
        except Exception as error:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name}\n      {type(error).__name__}: {str(error)[:240]}")
    print(f"\n{len(names) - failures}/{len(names)} guards passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
