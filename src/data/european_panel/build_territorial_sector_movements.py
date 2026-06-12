"""Phase 8 — Territorial Sector Movement Attribution.

For each of the 12 COVID-robust Phase 7 edges, decomposes the global beta
into per-territory contributions using leave-one-territory-out (LOTO):

    influence_r = beta_full - beta_without_territory_r

This is a descriptive attribution layer. It shows WHERE within the country the
sector-precedence association concentrates. It does NOT claim:
- causal transmission between territories
- propagation of enterprise-birth shocks
- that removing a territory would change the economy

Gates are pre-specified in decision.json and sealed before results are observed.
Association language only: "predictive precedence" not "causation" or "transmission".
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
V02_PANEL = (
    REPO_ROOT
    / "data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv"
)
ROBUST_EDGES = (
    REPO_ROOT
    / "data/processed/sector_precedence_results/covid_robust_edges.csv"
)
PHASE7_DECISION = (
    REPO_ROOT / "data/processed/sector_precedence_results/decision.json"
)
OUTPUT_DIR = REPO_ROOT / "data/processed/herald_observatory_v04"

# Pre-specified gates — sealed before observing any result
GATES = {
    "beta_integrity_tol": 0.01,
    "min_territory_own_pairs": 3,   # territory must have ≥ 3 complete pairs in window
    "min_loto_pairs": 30,           # LOTO dataset (all other territories) must have ≥ 30 pairs
    # keep for backward compatibility in classify_evidence call sites
    "min_territory_pairs": 3,
    "bootstrap_sign_stability_threshold": 0.60,
    "loyo_min_consistent_splits": 4,
    "evidence_strong_percentile": 75,
    "evidence_moderate_percentile": 50,
    "n_bootstrap": 500,
    "bootstrap_seed": 42,
    "provenance": "pre-specified before Phase 8 execution; not revised after observing results",
}

TERRITORY_SYSTEMS = {"NL": "COROP", "PT": "NUTS3_2021", "FR": "ZE2020"}


# ---------------------------------------------------------------------------
# Core regression helpers (replicate Phase 7 exactly)
# ---------------------------------------------------------------------------

def two_way_demean(
    values: np.ndarray,
    territories: np.ndarray,
    years: np.ndarray,
    max_iter: int = 8,
    tol: float = 1e-10,
) -> np.ndarray:
    """Alternating projection FE removal (replicates Phase 7)."""
    v = values.astype(float) - values.mean()
    for _ in range(max_iter):
        prev = v.copy()
        for labels in (territories, years):
            for lbl in np.unique(labels):
                mask = labels == lbl
                v[mask] -= v[mask].mean()
        if np.max(np.abs(v - prev)) < tol:
            break
    return v


def ols_beta_and_r2(
    y: np.ndarray,
    x1: np.ndarray,
    x2: np.ndarray,
) -> tuple[float, float, float]:
    """OLS of y ~ x1 + x2; returns (beta_x2, beta_x1, r2_full).

    x2 is the source_lag (variable of interest), x1 is target_lag (control).
    """
    X = np.column_stack([np.ones(len(y)), x1, x2])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return float("nan"), float("nan"), float("nan")
    beta_x2 = float(coeffs[2])
    y_hat = X @ coeffs
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return beta_x2, float(coeffs[1]), r2


def standardize(arr: np.ndarray) -> np.ndarray:
    """Z-score standardisation; returns array of NaNs if std=0."""
    std = arr.std()
    if std == 0 or not np.isfinite(std):
        return np.full_like(arr, np.nan)
    return (arr - arr.mean()) / std


def align_samples(
    panel: pd.DataFrame,
    country: str,
    source_sector: str,
    target_sector: str,
    window_start: int,
    window_end: int,
    exclude_years: frozenset[int] = frozenset(),
) -> pd.DataFrame:
    """Replicate Phase 7 alignment exactly.

    Returns DataFrame with columns:
        territory_id, observation_year, target_growth, target_lag, source_lag
    """
    keys = ["territory_id", "observation_year"]
    usable = panel[
        panel["country"].eq(country)
        & panel["observation_mask"].eq(1)
        & panel["structural_mask"].eq(1)
        & panel["observation_year"].between(window_start - 1, window_end)
        & ~panel["observation_year"].isin(exclude_years)
    ].copy()

    source = (
        usable[usable["sector_id"].eq(source_sector)][keys + ["velocity"]]
        .copy()
        .rename(columns={"velocity": "source_lag"})
    )
    source["observation_year"] += 1

    target_lag = (
        usable[usable["sector_id"].eq(target_sector)][keys + ["velocity"]]
        .copy()
        .rename(columns={"velocity": "target_lag"})
    )
    target_lag["observation_year"] += 1

    target = (
        usable[
            usable["sector_id"].eq(target_sector)
            & usable["observation_year"].between(window_start, window_end)
        ][keys + ["velocity"]]
        .rename(columns={"velocity": "target_growth"})
    )

    merged = (
        target.merge(target_lag, on=keys, how="inner")
        .merge(source, on=keys, how="inner")
        .dropna(subset=["target_growth", "target_lag", "source_lag"])
        .sort_values(keys)
        .reset_index(drop=True)
    )
    return merged


def compute_beta_on_samples(df: pd.DataFrame) -> tuple[float, float]:
    """Apply two-way demean + standardize + OLS; return (beta_source, r2)."""
    if len(df) < 10:
        return float("nan"), float("nan")
    terr = df["territory_id"].to_numpy()
    yrs = df["observation_year"].to_numpy()
    tg = two_way_demean(df["target_growth"].to_numpy(), terr, yrs)
    tl = two_way_demean(df["target_lag"].to_numpy(), terr, yrs)
    sl = two_way_demean(df["source_lag"].to_numpy(), terr, yrs)
    tg_s = standardize(tg)
    tl_s = standardize(tl)
    sl_s = standardize(sl)
    if not all(np.isfinite(v).any() for v in [tg_s, tl_s, sl_s]):
        return float("nan"), float("nan")
    valid = np.isfinite(tg_s) & np.isfinite(tl_s) & np.isfinite(sl_s)
    if valid.sum() < 10:
        return float("nan"), float("nan")
    return ols_beta_and_r2(tg_s[valid], tl_s[valid], sl_s[valid])[:2]


# ---------------------------------------------------------------------------
# LOTO influence computation
# ---------------------------------------------------------------------------

def compute_loto_influences(
    df: pd.DataFrame,
    beta_full: float,
    min_territory_own_pairs: int = 3,
    min_loto_pairs: int = 30,
) -> pd.DataFrame:
    """Compute LOTO influence for each territory.

    influence_r = beta_full - beta_without_r

    Eligibility:
    - Territory's own pair count must be >= min_territory_own_pairs
    - LOTO dataset (all other territories) must have >= min_loto_pairs

    Returns DataFrame with columns: territory_id, n_pairs_in_window, n_pairs_loto,
        beta_without, influence, insufficient_data.
    """
    territories = df["territory_id"].unique()
    records = []
    for tid in territories:
        n_own = int((df["territory_id"] == tid).sum())
        mask = df["territory_id"] != tid
        sub = df[mask]
        n_loto = len(sub)

        insufficient = n_own < min_territory_own_pairs or n_loto < min_loto_pairs
        if insufficient:
            records.append({
                "territory_id": tid,
                "n_pairs_in_window": n_own,
                "n_pairs_loto": n_loto,
                "beta_without": float("nan"),
                "influence": float("nan"),
                "insufficient_data": True,
            })
            continue
        beta_wo, _ = compute_beta_on_samples(sub)
        influence = beta_full - beta_wo if np.isfinite(beta_wo) else float("nan")
        records.append({
            "territory_id": tid,
            "n_pairs_in_window": n_own,
            "n_pairs_loto": n_loto,
            "beta_without": beta_wo,
            "influence": influence,
            "insufficient_data": False,
        })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Bootstrap sign stability
# ---------------------------------------------------------------------------

def bootstrap_loto_sign_stability(
    df: pd.DataFrame,
    loto_results: pd.DataFrame,
    n_bootstrap: int = 500,
    seed: int = 42,
    min_valid_draws: int = 50,
    min_pairs: int = 30,
) -> dict[str, float]:
    """Bootstrap sign stability of LOTO influence per territory.

    Resamples territories with replacement; for each draw computes
    influence_r only if territory r appears in the sample.
    Returns {territory_id: sign_stability}.
    """
    rng = np.random.default_rng(seed)
    territories = loto_results["territory_id"].tolist()

    # Map territory -> observed influence sign
    obs_signs = {
        row["territory_id"]: np.sign(row["influence"])
        for _, row in loto_results.iterrows()
        if np.isfinite(row["influence"]) and row["influence"] != 0
    }

    sign_counts: dict[str, int] = {t: 0 for t in territories}
    draw_counts: dict[str, int] = {t: 0 for t in territories}

    all_territories = df["territory_id"].unique()

    for _ in range(n_bootstrap):
        # Resample territories
        sampled = rng.choice(all_territories, size=len(all_territories), replace=True)
        sampled_set = set(sampled)

        # Build resampled dataframe
        frames = [df[df["territory_id"] == t] for t in sampled]
        if not frames:
            continue
        boot_df = pd.concat(frames, ignore_index=True)
        if len(boot_df) < min_pairs * 2:
            continue

        beta_boot, _ = compute_beta_on_samples(boot_df)
        if not np.isfinite(beta_boot):
            continue

        for tid in territories:
            if tid not in sampled_set or tid not in obs_signs:
                continue
            # LOTO on bootstrap sample
            sub = boot_df[boot_df["territory_id"] != tid]
            if len(sub) < min_pairs:
                continue
            beta_wo, _ = compute_beta_on_samples(sub)
            if not np.isfinite(beta_wo):
                continue
            boot_influence = beta_boot - beta_wo
            if boot_influence == 0:
                continue
            draw_counts[tid] += 1
            if np.sign(boot_influence) == obs_signs[tid]:
                sign_counts[tid] += 1

    result = {}
    for tid in territories:
        if draw_counts[tid] >= min_valid_draws:
            result[tid] = sign_counts[tid] / draw_counts[tid]
        else:
            result[tid] = float("nan")
    return result


# ---------------------------------------------------------------------------
# LOYO (leave-one-year-out) consistency
# ---------------------------------------------------------------------------

def loyo_sign_consistency(
    df: pd.DataFrame,
    beta_full: float,
    territory_id: str,
    min_consistent: int = 4,
    min_pairs: int = 10,
) -> tuple[bool, int, int]:
    """Check if LOTO influence sign is consistent across LOYO splits.

    Returns (is_consistent, n_consistent, n_total_splits)
    """
    if not np.isfinite(beta_full):
        return False, 0, 0

    mask_r = df["territory_id"] != territory_id
    years = sorted(df["observation_year"].unique())
    consistent = 0
    total = 0

    # Full LOTO influence sign (reference)
    sub_full = df[mask_r]
    if len(sub_full) < min_pairs:
        return False, 0, 0
    beta_wo_full, _ = compute_beta_on_samples(sub_full)
    if not np.isfinite(beta_wo_full):
        return False, 0, 0
    ref_sign = np.sign(beta_full - beta_wo_full)
    if ref_sign == 0:
        return False, 0, 0

    for y in years:
        sub_loyo = df[df["observation_year"] != y]
        sub_loyo_r = sub_loyo[sub_loyo["territory_id"] != territory_id]
        if len(sub_loyo) < min_pairs or len(sub_loyo_r) < min_pairs:
            continue
        beta_full_y, _ = compute_beta_on_samples(sub_loyo)
        beta_wo_y, _ = compute_beta_on_samples(sub_loyo_r)
        if not (np.isfinite(beta_full_y) and np.isfinite(beta_wo_y)):
            continue
        infl_y = beta_full_y - beta_wo_y
        if infl_y == 0:
            continue
        total += 1
        if np.sign(infl_y) == ref_sign:
            consistent += 1

    return consistent >= min_consistent, consistent, total


# ---------------------------------------------------------------------------
# without_2020 sign consistency
# ---------------------------------------------------------------------------

def without_2020_sign_consistency(
    df: pd.DataFrame,
    beta_full: float,
    territory_id: str,
    min_pairs: int = 10,
) -> bool | None:
    """Check if LOTO influence sign is consistent when 2020 is excluded.

    Returns None if 2020 is not in the window (not applicable).
    Returns True/False if 2020 is in the window.
    """
    has_2020 = 2020 in df["observation_year"].values
    if not has_2020:
        return None
    if not np.isfinite(beta_full):
        return False

    df_wo20 = df[df["observation_year"] != 2020]
    sub_wo20 = df_wo20[df_wo20["territory_id"] != territory_id]
    if len(df_wo20) < min_pairs or len(sub_wo20) < min_pairs:
        return None

    beta_full_wo, _ = compute_beta_on_samples(df_wo20)
    beta_wo_wo, _ = compute_beta_on_samples(sub_wo20)
    if not (np.isfinite(beta_full_wo) and np.isfinite(beta_wo_wo)):
        return None

    infl_wo20 = beta_full_wo - beta_wo_wo
    obs_mask_r = df["territory_id"] != territory_id
    beta_wo_full, _ = compute_beta_on_samples(df[obs_mask_r])
    if not np.isfinite(beta_wo_full):
        return None

    obs_infl = beta_full - beta_wo_full
    if obs_infl == 0 or infl_wo20 == 0:
        return None

    return bool(np.sign(infl_wo20) == np.sign(obs_infl))


# ---------------------------------------------------------------------------
# Evidence level classification (pre-specified gates)
# ---------------------------------------------------------------------------

def classify_evidence(
    influence: float,
    n_pairs: int,
    bootstrap_sign_stab: float,
    loyo_consistent: bool,
    without_2020: bool | None,
    q75: float,
    q50: float,
    gates: dict,
) -> str:
    """Apply pre-specified gates to assign evidence level.

    Returns: STRONG | MODERATE | WEAK | DESCRIPTIVE_ONLY | INSUFFICIENT_DATA
    """
    if n_pairs < gates["min_territory_pairs"]:
        return "INSUFFICIENT_DATA"

    if not np.isfinite(influence):
        return "INSUFFICIENT_DATA"

    abs_infl = abs(influence)
    has_stab = np.isfinite(bootstrap_sign_stab) and bootstrap_sign_stab >= gates["bootstrap_sign_stability_threshold"]
    # without_2020=None means not applicable → treat as satisfied
    wo20_ok = without_2020 is None or without_2020

    if (
        has_stab
        and loyo_consistent
        and wo20_ok
        and abs_infl >= q75
    ):
        return "STRONG"
    if (
        has_stab
        and loyo_consistent
        and wo20_ok
        and abs_infl >= q50
    ):
        return "MODERATE"
    if has_stab and abs_infl >= q50:
        return "WEAK"
    return "DESCRIPTIVE_ONLY"


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------

def build_phase8(
    output_dir: Path | None = None,
    n_bootstrap: int = GATES["n_bootstrap"],
    bootstrap_seed: int = GATES["bootstrap_seed"],
) -> tuple[pd.DataFrame, dict]:
    """Run Phase 8 territorial movement attribution.

    Returns (movements_df, manifest).
    """
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Seal decision record
    decision_path = output_dir / "territorial_sector_movement_decision.json"
    decision = {
        "phase": "Phase8_TerritorialSectorMovementAttribution",
        "method": "LOTO (leave-one-territory-out) regression influence decomposition",
        "equation": "influence_r = beta_full - beta_without_territory_r",
        "interpretation": (
            "Descriptive attribution only. Indicates where the sector-precedence "
            "association concentrates territorially. Does NOT imply causal transmission, "
            "geographic propagation, or enterprise-birth flow between territories."
        ),
        "input_edges": "covid_robust_edges.csv — Phase 7 ROBUST associations only",
        "gates": GATES,
        "provenance_note": (
            "Gates are pre-specified before execution (sealed in decision.json). "
            "Phase 7 global betas are IMMUTABLE; this layer only localises them."
        ),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
    }
    decision_path.write_text(json.dumps(decision, indent=2))
    logger.info("Decision sealed: %s", decision_path)

    # Load data
    logger.info("Loading panel …")
    panel = pd.read_csv(V02_PANEL, low_memory=False)
    edges = pd.read_csv(ROBUST_EDGES)
    phase7_dec = json.loads(PHASE7_DECISION.read_text())

    # Build Phase 7 beta lookup for integrity check
    phase7_results_path = (
        REPO_ROOT / "data/processed/sector_precedence_results/latest.csv"
    )
    p7 = pd.read_csv(phase7_results_path)
    p7_lookup: dict[tuple, float] = {}
    for _, row in p7.iterrows():
        key = (
            str(row["country"]),
            int(row["window_start"]),
            int(row["window_end"]),
            str(row["source_sector"]),
            str(row["target_sector"]),
        )
        p7_lookup[key] = float(row["beta"])

    all_records: list[dict] = []
    relation_summaries: list[dict] = []
    integrity_failures: list[str] = []

    for _, edge in edges.iterrows():
        country = str(edge["country"])
        ws, we = int(edge["window_start"]), int(edge["window_end"])
        src, tgt = str(edge["source_sector"]), str(edge["target_sector"])
        label = f"{country} {ws}-{we} {src}→{tgt}"
        logger.info("Processing %s …", label)

        # Align samples (full, with and without 2020)
        df_full = align_samples(panel, country, src, tgt, ws, we)
        has_2020 = 2020 in df_full["observation_year"].values

        if len(df_full) < 30:
            logger.warning("  SKIP: insufficient samples n=%d", len(df_full))
            continue

        # Compute global beta (must match Phase 7)
        beta_full, _ = compute_beta_on_samples(df_full)
        p7_key = (country, ws, we, src, tgt)
        p7_beta = p7_lookup.get(p7_key, float("nan"))

        if np.isfinite(p7_beta):
            deviation = abs(beta_full - p7_beta)
            if deviation > GATES["beta_integrity_tol"]:
                msg = (
                    f"{label}: beta deviation {deviation:.6f} > "
                    f"{GATES['beta_integrity_tol']} — INTEGRITY FAIL"
                )
                logger.error(msg)
                integrity_failures.append(msg)
                continue
            logger.info("  beta=%.4f (p7=%.4f, dev=%.2e) ✓", beta_full, p7_beta, deviation)
        else:
            logger.warning("  Phase 7 beta not found in lookup for %s", label)

        # LOTO influences
        loto = compute_loto_influences(
            df_full, beta_full,
            min_territory_own_pairs=GATES["min_territory_own_pairs"],
            min_loto_pairs=GATES["min_loto_pairs"],
        )

        # Bootstrap sign stability
        logger.info("  Bootstrap (n=%d) …", n_bootstrap)
        stab = bootstrap_loto_sign_stability(
            df_full, loto,
            n_bootstrap=n_bootstrap,
            seed=bootstrap_seed,
            min_valid_draws=50,
            min_pairs=GATES["min_loto_pairs"],
        )

        # Compute percentile thresholds for this relation
        valid_influences = loto.loc[
            np.isfinite(loto["influence"]) & ~loto["insufficient_data"],
            "influence"
        ].abs().values
        q75 = float(np.percentile(valid_influences, GATES["evidence_strong_percentile"])) if len(valid_influences) else 0.0
        q50 = float(np.percentile(valid_influences, GATES["evidence_moderate_percentile"])) if len(valid_influences) else 0.0
        total_abs_influence = float(valid_influences.sum())

        # Assemble per-territory records
        for _, row in loto.iterrows():
            tid = row["territory_id"]
            influence = float(row["influence"])
            n_pairs_tid = int(row["n_pairs_in_window"])
            insufficient = bool(row["insufficient_data"])

            bss = stab.get(tid, float("nan"))

            # LOYO consistency
            if not insufficient and np.isfinite(influence):
                loyo_ok, loyo_n_consistent, loyo_n_total = loyo_sign_consistency(
                    df_full, beta_full, tid,
                    min_consistent=GATES["loyo_min_consistent_splits"],
                    min_pairs=GATES["min_loto_pairs"],
                )
            else:
                loyo_ok, loyo_n_consistent, loyo_n_total = False, 0, 0

            # Without-2020 consistency
            wo20 = None
            if not insufficient and np.isfinite(influence) and has_2020:
                wo20 = without_2020_sign_consistency(
                    df_full, beta_full, tid,
                    min_pairs=GATES["min_loto_pairs"],
                )

            # Evidence level
            evidence = classify_evidence(
                influence=influence,
                n_pairs=n_pairs_tid,
                bootstrap_sign_stab=bss,
                loyo_consistent=loyo_ok,
                without_2020=wo20,
                q75=q75,
                q50=q50,
                gates=GATES,
            )

            # Influence share
            infl_share = (
                abs(influence) / total_abs_influence
                if total_abs_influence > 0 and np.isfinite(influence)
                else float("nan")
            )
            # Influence sign
            if np.isfinite(influence) and influence > 1e-10:
                infl_sign = "positive"
            elif np.isfinite(influence) and influence < -1e-10:
                infl_sign = "negative"
            elif np.isfinite(influence):
                infl_sign = "neutral"
            else:
                infl_sign = "unknown"

            all_records.append({
                "country": country,
                "territorial_system": TERRITORY_SYSTEMS[country],
                "territory_id": tid,
                "window_start": ws,
                "window_end": we,
                "source_sector": src,
                "target_sector": tgt,
                "global_beta": round(beta_full, 6),
                "global_beta_phase7": round(p7_beta, 6) if np.isfinite(p7_beta) else None,
                "n_pairs_in_window": n_pairs_tid,
                "beta_without": round(float(row["beta_without"]), 6) if np.isfinite(row["beta_without"]) else None,
                "territorial_influence": round(influence, 6) if np.isfinite(influence) else None,
                "influence_sign": infl_sign,
                "influence_share": round(infl_share, 6) if np.isfinite(infl_share) else None,
                "q50_abs_influence": round(q50, 6),
                "q75_abs_influence": round(q75, 6),
                "bootstrap_sign_stability": round(bss, 4) if np.isfinite(bss) else None,
                "loyo_consistent": bool(loyo_ok),
                "loyo_n_consistent": loyo_n_consistent,
                "loyo_n_total": loyo_n_total,
                "without_2020_consistent": wo20,
                "evidence_level": evidence,
                "insufficient_data": insufficient,
                "provenance": "Phase8_LOTO",
            })

        # Relation summary
        n_strong = sum(1 for r in all_records[-len(loto):] if r["evidence_level"] == "STRONG")
        n_moderate = sum(1 for r in all_records[-len(loto):] if r["evidence_level"] == "MODERATE")
        n_weak = sum(1 for r in all_records[-len(loto):] if r["evidence_level"] == "WEAK")
        top3_conc = float(
            np.sort(valid_influences)[::-1][:3].sum() / total_abs_influence
        ) if total_abs_influence > 0 and len(valid_influences) >= 3 else float("nan")

        relation_summaries.append({
            "country": country,
            "window": f"{ws}-{we}",
            "window_start": ws,
            "window_end": we,
            "source_sector": src,
            "target_sector": tgt,
            "global_beta": round(beta_full, 6),
            "n_territories": int(loto["territory_id"].nunique()),
            "n_total_pairs": len(df_full),
            "n_strong": n_strong,
            "n_moderate": n_moderate,
            "n_weak": n_weak,
            "n_insufficient": int(loto["insufficient_data"].sum()),
            "total_abs_influence": round(total_abs_influence, 6),
            "top3_concentration": round(top3_conc, 4) if np.isfinite(top3_conc) else None,
            "q50_abs_influence": round(q50, 6),
            "q75_abs_influence": round(q75, 6),
        })

    if integrity_failures:
        raise SystemExit(
            "FAIL_CLOSED: beta integrity check failed for %d relations:\n%s"
            % (len(integrity_failures), "\n".join(integrity_failures))
        )

    movements_df = pd.DataFrame(all_records)

    # Write outputs
    csv_path = output_dir / "territorial_sector_movements.csv"
    movements_df.to_csv(csv_path, index=False)
    logger.info("Movements: %d rows → %s", len(movements_df), csv_path)

    summary_df = pd.DataFrame(relation_summaries)
    summary_path = output_dir / "territorial_sector_movement_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    logger.info("Summary: %d relations → %s", len(summary_df), summary_path)

    # Manifest
    csv_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    v02_sha256 = hashlib.sha256(V02_PANEL.read_bytes()).hexdigest()

    promoted_summary = {
        level: int((movements_df["evidence_level"] == level).sum())
        for level in ["STRONG", "MODERATE", "WEAK", "DESCRIPTIVE_ONLY", "INSUFFICIENT_DATA"]
    }

    manifest = {
        "phase": "Phase8_TerritorialSectorMovementAttribution",
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_panel_sha256": v02_sha256,
        "n_robust_relations": len(edges),
        "n_territory_relation_records": len(movements_df),
        "promoted_summary": promoted_summary,
        "output_csv_sha256": csv_sha256,
        "n_bootstrap": n_bootstrap,
        "bootstrap_seed": bootstrap_seed,
        "gates": GATES,
        "integrity_failures": integrity_failures,
        "association_disclaimer": (
            "This layer decomposes validated Phase 7 sector-precedence associations "
            "into per-territory contributions. It does NOT imply causal transmission, "
            "real business-creation flows, or policy recommendations."
        ),
    }
    manifest_path = output_dir / "territorial_sector_movement_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Manifest → %s", manifest_path)

    return movements_df, manifest


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df, mf = build_phase8()
    print("\n=== Phase 8 Summary ===")
    print(f"Total territory-relation records: {len(df)}")
    print(f"Evidence breakdown: {mf['promoted_summary']}")
