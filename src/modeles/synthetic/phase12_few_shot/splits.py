"""
splits.py — Phase 12 few-shot split definitions (DEC-047)

Key design principle:
  FEWSHOT_SEEDS control the random selection of few-shot support cells —
  NOT which synthetic dataset is generated.
  Synthetic datasets are always generated from NOVEL_TEST_SCENARIOS with seeds
  from TEST_SEEDS = [1000, 2000, 3000, 4000, 5000] (Phase 11).
  FEWSHOT_SEEDS are therefore independent from dataset seeds and do not need
  to be disjoint from them. They are disjoint from dataset generation seeds
  by construction (different role).

Temporal split protocol (frozen before execution):
  support_years : first 65% of years — labels available for adaptation
  val_years     : next 15% of years — early stopping (never used for test)
  test_years    : last 20% of years — held-out evaluation

DO NOT modify constants or split logic after first pilot execution.
"""

from __future__ import annotations

import numpy as np

# ── Few-shot support selection seeds ──────────────────────────────────────────
# These seeds control which observed cells are randomly selected as support labels.
# They are NOT dataset generation seeds (which always come from TEST_SEEDS=[1000..5000]).
# Seeds 42, 123, 456 also appear in OFAT_SEEDS and BENCHMARK_SEEDS but serve
# a different role here (support cell selection RNG), so overlap is safe.

FEWSHOT_SEEDS: list[int] = [42, 123, 456, 789, 1001]
PILOT_FEWSHOT_SEEDS: list[int] = [42, 123, 456]

# ── Few-shot fraction grid ────────────────────────────────────────────────────

K_FRACS: list[float] = [0.0, 0.01, 0.05, 0.10, 0.20]
PILOT_K_FRACS: list[float] = [0.0, 0.05, 0.10]

# ── Safety thresholds ─────────────────────────────────────────────────────────

MIN_LABELS_THRESHOLD: int = 5   # below this, flag EXTREME_LOW_SHOT

# ── Temporal split fractions (frozen) ─────────────────────────────────────────

SUPPORT_YEAR_FRAC: float = 0.65  # first 65% of years = support window
VAL_YEAR_FRAC: float = 0.15      # next 15% = val window (early stopping)
TEST_YEAR_FRAC: float = 0.20     # last 20% = test evaluation


# ── Split functions ───────────────────────────────────────────────────────────

def make_temporal_splits(n_years: int) -> tuple[range, range, range]:
    """
    Returns (support_years, val_years, test_years) as ranges.
    Temporal order strictly preserved. No overlap.

    For n_years=20 (novel_lag2 / novel_highvar):
      n_support = 13, n_val = 3, n_test = 4
    """
    n_support = max(1, int(n_years * SUPPORT_YEAR_FRAC))
    n_val = max(1, int(n_years * VAL_YEAR_FRAC))
    n_test = n_years - n_support - n_val
    if n_test < 1:
        # Edge case: squeeze val to leave at least 1 test year
        n_val = max(0, n_val - 1)
        n_test = n_years - n_support - n_val
    support_years = range(0, n_support)
    val_years = range(n_support, n_support + n_val)
    test_years = range(n_support + n_val, n_years)
    return support_years, val_years, test_years


def make_fewshot_support_mask(
    obs_mask: np.ndarray,      # (n_T, n_S, n_Y) observed=1 mask from dataset
    support_years: range,
    k_frac: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict]:
    """
    Returns (support_mask, info_dict).

    support_mask: (n_T, n_S, n_Y) binary; 1 = available for adaptation.
    Selects K% of observed cells in support_years window only.
    If k_frac=0.0, returns all-zeros mask (zero-shot).

    info: {n_observed_support, n_selected, k_frac_actual, is_extreme_low_shot}

    Important: support cells are drawn from obs_mask=1 (observed, non-missing panel
    cells) in the support window — not from imputation hidden cells.
    """
    n_T, n_S, n_Y = obs_mask.shape
    support_mask = np.zeros((n_T, n_S, n_Y), dtype=np.int8)

    # Build support window mask
    support_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in support_years:
        support_window[:, :, y] = True

    # Candidate cells: observed AND in support window
    candidate = (obs_mask == 1) & support_window
    n_observed_support = int(candidate.sum())

    if k_frac <= 0.0 or n_observed_support == 0:
        info = {
            "n_observed_support": n_observed_support,
            "n_selected": 0,
            "k_frac_actual": 0.0,
            "is_extreme_low_shot": False,
            "zero_shot": True,
        }
        return support_mask, info

    n_selected = max(0, round(n_observed_support * k_frac))
    n_selected = min(n_selected, n_observed_support)

    if n_selected > 0:
        candidate_indices = np.argwhere(candidate)  # (N, 3)
        chosen = rng.choice(len(candidate_indices), size=n_selected, replace=False)
        for idx in chosen:
            t, s, y = candidate_indices[idx]
            support_mask[t, s, y] = 1

    k_frac_actual = n_selected / n_observed_support if n_observed_support > 0 else 0.0
    is_extreme_low_shot = 0 < n_selected < MIN_LABELS_THRESHOLD

    info = {
        "n_observed_support": n_observed_support,
        "n_selected": n_selected,
        "k_frac_actual": float(k_frac_actual),
        "is_extreme_low_shot": bool(is_extreme_low_shot),
        "zero_shot": n_selected == 0,
    }
    return support_mask, info


def make_eval_masks(
    obs_mask: np.ndarray,
    val_years: range,
    test_years: range,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (val_mask, test_mask).
    val_mask: cells in val_years window that are OBSERVED (obs_mask=1).
    test_mask: cells in test_years window that are OBSERVED (obs_mask=1).

    Note: "test cells" for imputation evaluation are the HIDDEN cells (obs_mask=0)
    in test_years. This function returns observed cells used for early stopping.
    Use ~obs_mask & test_window to find imputation evaluation targets.
    """
    n_T, n_S, n_Y = obs_mask.shape

    val_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in val_years:
        val_window[:, :, y] = True

    test_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in test_years:
        test_window[:, :, y] = True

    val_mask = ((obs_mask == 1) & val_window).astype(np.int8)
    test_mask = ((obs_mask == 1) & test_window).astype(np.int8)
    return val_mask, test_mask


def make_imputation_test_mask(
    obs_mask: np.ndarray,
    test_years: range,
) -> np.ndarray:
    """
    Returns the imputation evaluation mask: cells HIDDEN (obs_mask=0) in test_years.
    These are the cells we want to impute and measure MAE on.
    """
    n_T, n_S, n_Y = obs_mask.shape
    test_window = np.zeros((n_T, n_S, n_Y), dtype=bool)
    for y in test_years:
        test_window[:, :, y] = True
    return ((obs_mask == 0) & test_window).astype(np.int8)


def verify_disjoint_splits(
    support_mask: np.ndarray,
    val_mask: np.ndarray,
    test_mask: np.ndarray,
    hidden_mask: np.ndarray,
) -> None:
    """
    Assert no cell is in more than one mask.
    hidden_mask = ~obs_mask (cells we want to impute).

    Invariants checked:
    - support ∩ val = 0
    - support ∩ test = 0
    - val ∩ test = 0
    - support ∩ hidden = 0  (support must come from observed cells)
    """
    sm = support_mask.astype(bool)
    vm = val_mask.astype(bool)
    tm = test_mask.astype(bool)
    hm = hidden_mask.astype(bool)

    sv = int((sm & vm).sum())
    st = int((sm & tm).sum())
    vt = int((vm & tm).sum())
    sh = int((sm & hm).sum())

    assert sv == 0, f"Support ∩ Val overlap: {sv} cells"
    assert st == 0, f"Support ∩ Test overlap: {st} cells"
    assert vt == 0, f"Val ∩ Test overlap: {vt} cells"
    assert sh == 0, f"Support ∩ Hidden overlap: {sh} cells (support must be from observed)"
