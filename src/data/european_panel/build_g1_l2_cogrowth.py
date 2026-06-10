"""Build and validate the G1-L2 causal co-growth graph.

L2: same-sector cross-territory co-growth.

For each eligible country and sector, edge weight between territories (r1, r2)
at evaluation year t = Pearson correlation of their sector growth rates over
the rolling window [t-w, t-1].  Only observation_year <= t-1 data is used,
satisfying the causal temporal protocol in the G0 formal contract.

Agriculture is excluded.  PT KZ is structurally absent from INE 0009703
(section K not reported); this is a verified definitional exclusion, not a
data error (DEC-018).  PT participates with 8 sectors.

COVID sensitivity: 2020 is excluded from window observation years (not from
eval_year selection).  eval_year=2020's window covers [2015..2019] which
contains no COVID data; excluding 2020 from observation years leaves it
unaffected.  eval_year=2021 uses [2016..2019] (4 years, ≥ MIN_PERIODS).
Gaps in windows are tracked explicitly in validation output.

Null models (finite-sample corrected p = (1 + count(null >= obs)) / (1 + N)):
  1. Temporal permutation: shuffle years within territory-sector.
  2. Territory permutation: shuffle territories within year-sector.

Both preserve the rolling-window structure used for the observed graph.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
DEFAULT_OUT = BASE / "data/processed/economic_graph/g1_l2_cogrowth"
DEFAULT_REPORT = BASE / "reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md"

SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
WINDOW = 5
MIN_PERIODS = 4
TOP_K = 5
N_PERMUTATIONS = 199
N_BOOTSTRAPS = 199
BOOTSTRAP_THRESHOLD = 0.70
SEED = 42
COVID_YEAR = 2020


# ---------------------------------------------------------------------------
# Growth matrix helpers
# ---------------------------------------------------------------------------

def eligible_sectors(panel: pd.DataFrame, country: str) -> list[str]:
    sub = panel[
        panel["country"].eq(country)
        & panel["mask_sector_supported"].eq(1)
        & panel["sector_growth_1y"].notna()
    ]
    return sorted(sub["sector_a10"].unique())


def build_growth_matrix(
    panel: pd.DataFrame, country: str, sector: str
) -> tuple[list[str], list[int], np.ndarray]:
    """Return (region_ids, growth_years, matrix[years, regions])."""
    sub = panel[
        panel["country"].eq(country)
        & panel["sector_a10"].eq(sector)
        & panel["mask_sector_supported"].eq(1)
    ].copy()
    region_ids = sorted(sub["region_id"].astype(str).unique())
    growth_years = sorted(sub["observation_year"].unique().tolist())
    wide = sub.pivot_table(
        index="observation_year",
        columns="region_id",
        values="sector_growth_1y",
        aggfunc="first",
    ).reindex(index=growth_years, columns=region_ids)
    return region_ids, growth_years, wide.to_numpy(dtype=float)


def window_years_used(
    growth_years: list[int],
    eval_year: int,
    window: int = WINDOW,
    exclude_years: frozenset[int] = frozenset(),
) -> list[int]:
    """Return the actual observation years that enter the window for eval_year t.

    Window is [t-window, t-1] minus explicitly excluded years.
    Years with no observation in growth_years are also absent.
    """
    return [
        y for y in growth_years
        if eval_year - window <= y <= eval_year - 1 and y not in exclude_years
    ]


def window_matrix(
    growth_years: list[int],
    matrix: np.ndarray,
    eval_year: int,
    window: int = WINDOW,
    exclude_years: frozenset[int] = frozenset(),
) -> np.ndarray:
    """Extract rows for the causal window [t-window, t-1] minus excluded years.

    Returns an empty 2-D array (shape 0×n_regions) if no rows qualify,
    which downstream pairwise_corr interprets as all-NaN.
    """
    indices = [
        growth_years.index(y)
        for y in window_years_used(growth_years, eval_year, window, exclude_years)
    ]
    return matrix[indices, :] if indices else np.empty((0, matrix.shape[1]))


def pairwise_corr(mat: np.ndarray, min_periods: int = MIN_PERIODS) -> np.ndarray:
    """Pairwise Pearson correlation via pandas (handles NaN, min_periods)."""
    if mat.shape[0] < min_periods:
        n = mat.shape[1]
        return np.full((n, n), np.nan)
    return pd.DataFrame(mat).corr(min_periods=min_periods).to_numpy(dtype=float)


def upper_triangle(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    return matrix[np.triu_indices(n, k=1)]


# ---------------------------------------------------------------------------
# Aggregate edge vector across all sectors for a given eval_year
# ---------------------------------------------------------------------------

def l2_edge_vector(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sectors: list[str],
    eval_year: int,
    window: int = WINDOW,
    exclude_years: frozenset[int] = frozenset(),
) -> np.ndarray:
    """Full L2 edge vector concatenating upper triangles across sectors."""
    parts = []
    for sector in sectors:
        region_ids, growth_years, matrix = sector_data[sector]
        w_mat = window_matrix(growth_years, matrix, eval_year, window, exclude_years)
        corr = upper_triangle(pairwise_corr(w_mat))
        parts.append(corr)
    return np.concatenate(parts) if parts else np.array([])


def eval_years_for_country(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sectors: list[str],
    window: int = WINDOW,
) -> list[int]:
    """Return evaluation years where at least one sector can produce a window.

    Evaluation years are NOT filtered by exclude_years — only the window data
    for each eval_year is filtered.  This preserves eval_year=2020, whose
    window covers [t-window, t-1] = pre-COVID years.
    """
    all_years: set[int] = set()
    for sector in sectors:
        _, growth_years, _ = sector_data[sector]
        first = growth_years[0] + window
        last = growth_years[-1] + 1
        all_years.update(range(first, last + 1))
    return sorted(all_years)


# ---------------------------------------------------------------------------
# Stability
# ---------------------------------------------------------------------------

def finite_corr(a: np.ndarray, b: np.ndarray) -> float:
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 2:
        return np.nan
    a2, b2 = a[mask], b[mask]
    if np.std(a2) < 1e-12 or np.std(b2) < 1e-12:
        return np.nan
    return float(np.corrcoef(a2, b2)[0, 1])


def consecutive_stability(
    vectors: list[np.ndarray],
) -> tuple[float, list[float]]:
    pairs = [finite_corr(vectors[i - 1], vectors[i]) for i in range(1, len(vectors))]
    finite = [v for v in pairs if np.isfinite(v)]
    return (float(np.mean(finite)) if finite else np.nan), pairs


def empirical_p(observed: float, null_values: list[float]) -> float:
    vals = np.array([v for v in null_values if np.isfinite(v)])
    return float((1 + np.sum(vals >= observed)) / (1 + len(vals)))


def bh_fdr(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 1.0
    for rev in range(len(p) - 1, -1, -1):
        idx = order[rev]
        running = min(running, p[idx] * len(p) / (rev + 1))
        adj[idx] = running
    return adj.tolist()


# ---------------------------------------------------------------------------
# Null permutations
# ---------------------------------------------------------------------------

def permute_growth_temporal(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    rng: np.random.Generator,
) -> dict[str, tuple[list[str], list[int], np.ndarray]]:
    """Shuffle years within each territory-sector."""
    result = {}
    for sector, (region_ids, growth_years, matrix) in sector_data.items():
        perm = matrix.copy()
        for col in range(perm.shape[1]):
            valid = np.where(np.isfinite(perm[:, col]))[0]
            if len(valid) > 1:
                perm[valid, col] = rng.permutation(perm[valid, col])
        result[sector] = (region_ids, growth_years, perm)
    return result


def permute_growth_territory(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    rng: np.random.Generator,
) -> dict[str, tuple[list[str], list[int], np.ndarray]]:
    """Shuffle territories within each year-sector."""
    result = {}
    for sector, (region_ids, growth_years, matrix) in sector_data.items():
        perm = matrix.copy()
        for row in range(perm.shape[0]):
            perm[row] = rng.permutation(perm[row])
        result[sector] = (region_ids, growth_years, perm)
    return result


# ---------------------------------------------------------------------------
# LOYO direction test
# ---------------------------------------------------------------------------

def leave_one_year_mean(pairs: list[float], omitted: int) -> float:
    kept = [
        v for i, v in enumerate(pairs)
        if i not in {omitted - 1, omitted} and np.isfinite(v)
    ]
    return float(np.mean(kept)) if kept else np.nan


def loyo_direction_pass(
    observed_pairs: list[float],
    temporal_pairs_list: list[list[float]],
    territory_pairs_list: list[list[float]],
    n_years: int,
) -> bool:
    for omit in range(n_years):
        obs = leave_one_year_mean(observed_pairs, omit)
        if not np.isfinite(obs):
            continue
        t_vals = [leave_one_year_mean(p, omit) for p in temporal_pairs_list]
        r_vals = [leave_one_year_mean(p, omit) for p in territory_pairs_list]
        if obs <= np.nanmedian(t_vals) or obs <= np.nanmedian(r_vals):
            return False
    return True


# ---------------------------------------------------------------------------
# Bootstrap edge frequency
# ---------------------------------------------------------------------------

def bootstrap_edge_stability(
    sector_data: dict[str, tuple[list[str], list[int], np.ndarray]],
    sectors: list[str],
    eval_years: list[int],
    rng: np.random.Generator,
    window: int = WINDOW,
    top_k: int = TOP_K,
    n_bootstraps: int = N_BOOTSTRAPS,
    exclude_years: frozenset[int] = frozenset(),
) -> pd.DataFrame:
    """Bootstrap by resampling eval_years; track top-k edge frequency per sector.

    exclude_years is propagated to window_matrix so that COVID-excluded years
    do not enter any bootstrap window.
    """
    counts: dict[tuple[str, str, str], int] = {}

    for _ in range(n_bootstraps):
        sampled = rng.integers(0, len(eval_years), size=len(eval_years))
        for sector in sectors:
            region_ids, growth_years, matrix = sector_data[sector]
            corr_sum = np.zeros((len(region_ids), len(region_ids)), dtype=float)
            valid_count = 0
            for idx in sampled:
                t = eval_years[idx]
                w_mat = window_matrix(
                    growth_years, matrix, t, window, exclude_years
                )
                corr = pairwise_corr(w_mat)
                if not np.all(np.isnan(corr)):
                    where = np.isfinite(corr)
                    corr_sum = np.where(where, corr_sum + corr, corr_sum)
                    valid_count += 1
            if valid_count == 0:
                continue
            mean_corr = corr_sum / valid_count
            n = len(region_ids)
            all_pairs = list(zip(*np.triu_indices(n, k=1)))
            valid_pairs = [(i, j) for i, j in all_pairs if np.isfinite(mean_corr[i, j])]
            if not valid_pairs:
                continue
            weights = np.abs([mean_corr[i, j] for i, j in valid_pairs])
            order = np.argsort(-weights)
            for k in order[:top_k]:
                i, j = valid_pairs[k]
                key = (sector, region_ids[i], region_ids[j])
                counts[key] = counts.get(key, 0) + 1

    records = [
        {
            "sector": k[0],
            "source_region": k[1],
            "target_region": k[2],
            "bootstrap_frequency": v / n_bootstraps,
            "promoted_stable_edge": int(v / n_bootstraps >= BOOTSTRAP_THRESHOLD),
        }
        for k, v in counts.items()
    ]
    return pd.DataFrame(records).sort_values(
        ["promoted_stable_edge", "bootstrap_frequency"],
        ascending=[False, False],
    ).reset_index(drop=True) if records else pd.DataFrame(
        columns=["sector", "source_region", "target_region",
                 "bootstrap_frequency", "promoted_stable_edge"]
    )


# ---------------------------------------------------------------------------
# Per-country validation
# ---------------------------------------------------------------------------

def validate_country(
    panel: pd.DataFrame,
    country: str,
    rng: np.random.Generator,
    window: int = WINDOW,
    n_perm: int = N_PERMUTATIONS,
    exclude_years: frozenset[int] = frozenset(),
) -> tuple[dict, pd.DataFrame]:
    """Validate L2 co-growth for one country.

    exclude_years controls which observation years are removed from windows.
    It does NOT filter eval_years: eval_year=2020's window is [2015..2019]
    which never contains 2020, so that eval_year is unaffected by exclusion.
    """
    sectors = eligible_sectors(panel, country)
    if not sectors:
        raise ValueError(f"{country}: no eligible sectors")

    sector_data = {
        s: build_growth_matrix(panel, country, s) for s in sectors
    }

    # eval_years are NOT filtered by exclude_years
    eval_yrs = eval_years_for_country(sector_data, sectors, window)
    if len(eval_yrs) < 2:
        raise ValueError(f"{country}: fewer than 2 evaluation years available")

    # Observed edge vectors (exclude_years propagated to window_matrix)
    obs_vectors = [
        l2_edge_vector(sector_data, sectors, t, window, exclude_years)
        for t in eval_yrs
    ]
    obs_stability, obs_pairs = consecutive_stability(obs_vectors)

    # Temporal permutation nulls
    temporal_stabilities = []
    temporal_pairs_list = []
    for _ in range(n_perm):
        perm_data = permute_growth_temporal(sector_data, rng)
        vecs = [
            l2_edge_vector(perm_data, sectors, t, window, exclude_years)
            for t in eval_yrs
        ]
        s, pairs = consecutive_stability(vecs)
        temporal_stabilities.append(s)
        temporal_pairs_list.append(pairs)

    # Territory permutation nulls
    territory_stabilities = []
    territory_pairs_list = []
    for _ in range(n_perm):
        perm_data = permute_growth_territory(sector_data, rng)
        vecs = [
            l2_edge_vector(perm_data, sectors, t, window, exclude_years)
            for t in eval_yrs
        ]
        s, pairs = consecutive_stability(vecs)
        territory_stabilities.append(s)
        territory_pairs_list.append(pairs)

    temporal_p = empirical_p(obs_stability, temporal_stabilities)
    territory_p = empirical_p(obs_stability, territory_stabilities)
    loyo = loyo_direction_pass(
        obs_pairs, temporal_pairs_list, territory_pairs_list, len(eval_yrs)
    )

    # Bootstrap — exclude_years propagated so bootstrap windows honour exclusion
    bootstrap = bootstrap_edge_stability(
        sector_data, sectors, eval_yrs, rng, window,
        exclude_years=exclude_years,
    )
    stable_count = int(bootstrap["promoted_stable_edge"].sum()) if not bootstrap.empty else 0

    # Record explicit gap information so the output is never misleading
    window_gaps: list[int] = []
    for t in eval_yrs:
        for sector in sectors:
            _, gy, _ = sector_data[sector]
            used = window_years_used(gy, t, window, exclude_years)
            expected = set(range(t - window, t)) & set(gy)
            window_gaps.extend(sorted(expected - set(used)))
    window_gaps_unique = sorted(set(window_gaps))

    row = {
        "country": country,
        "sectors": ",".join(sectors),
        "n_sectors": len(sectors),
        "eval_years_list": eval_yrs,
        "eval_years": f"{eval_yrs[0]}-{eval_yrs[-1]}",
        "n_eval_years": len(eval_yrs),
        "window_years_excluded": sorted(exclude_years),
        "window_gaps_detected": window_gaps_unique,
        "observed_stability": obs_stability,
        "temporal_null_median": float(np.nanmedian(temporal_stabilities)),
        "temporal_p": temporal_p,
        "territory_null_median": float(np.nanmedian(territory_stabilities)),
        "territory_p": territory_p,
        "leave_one_year_direction_pass": loyo,
        "stable_edge_count": stable_count,
        "exclude_covid": len(exclude_years) > 0,
    }
    return row, bootstrap


# ---------------------------------------------------------------------------
# Edge output
# ---------------------------------------------------------------------------

def build_edge_list(
    panel: pd.DataFrame,
    country: str,
    window: int = WINDOW,
    exclude_years: frozenset[int] = frozenset(),
) -> pd.DataFrame:
    """Build per-(sector, eval_year) edge list with explicit window year lists."""
    sectors = eligible_sectors(panel, country)
    sector_data = {s: build_growth_matrix(panel, country, s) for s in sectors}
    eval_yrs = eval_years_for_country(sector_data, sectors, window)

    records = []
    for sector in sectors:
        region_ids, growth_years, matrix = sector_data[sector]
        n = len(region_ids)
        for t in eval_yrs:
            used = window_years_used(growth_years, t, window, exclude_years)
            w_mat = window_matrix(growth_years, matrix, t, window, exclude_years)
            corr = pairwise_corr(w_mat)
            for i, j in zip(*np.triu_indices(n, k=1)):
                w = corr[i, j]
                if np.isfinite(w):
                    records.append(
                        {
                            "country": country,
                            "sector": sector,
                            "available_for_forecast_year": t,
                            "source_region": region_ids[i],
                            "target_region": region_ids[j],
                            "weight_cogrowth": float(w),
                            "window_years_used": ",".join(map(str, used)),
                            "n_window_years": len(used),
                        }
                    )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def _country_pass_gate(row: dict) -> bool:
    """Full gate: temporal q, territory q, LOYO, bootstrap stable edge > 0."""
    return bool(
        row.get("temporal_q", 1.0) <= 0.05
        and row.get("territory_q", 1.0) <= 0.05
        and row.get("leave_one_year_direction_pass", False)
        and row.get("stable_edge_count", 0) > 0
    )


def build(panel: pd.DataFrame, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    validation_rows: list[dict] = []
    validation_nocovid: list[dict] = []
    bootstrap_frames: list[pd.DataFrame] = []
    edge_frames: list[pd.DataFrame] = []
    ineligible: list[dict] = []

    exclude_covid = frozenset({COVID_YEAR})

    for country in sorted(panel["country"].unique()):
        try:
            row, boot = validate_country(panel, country, rng)
        except ValueError as exc:
            ineligible.append({"country": country, "reason": str(exc)})
            continue

        # COVID sensitivity — separate deterministic rng; exclude_years propagated
        rng2 = np.random.default_rng(SEED + 1)
        try:
            row_nc, _ = validate_country(
                panel, country, rng2, exclude_years=exclude_covid
            )
        except ValueError:
            row_nc = {
                **row,
                "exclude_covid": True,
                "observed_stability": float("nan"),
                "stable_edge_count": 0,
                "leave_one_year_direction_pass": False,
            }

        validation_rows.append(row)
        validation_nocovid.append(row_nc)
        boot.insert(0, "country", country)
        bootstrap_frames.append(boot)
        edge_frames.append(build_edge_list(panel, country))

    if not validation_rows:
        raise RuntimeError("No country produced validation results")

    # --- Main validation ---
    validation = pd.DataFrame(validation_rows)
    p_vals = validation[["temporal_p", "territory_p"]].to_numpy().ravel().tolist()
    q_vals = bh_fdr(p_vals)
    validation[["temporal_q", "territory_q"]] = np.array(q_vals).reshape(
        len(validation), 2
    )
    validation["country_pass"] = validation.apply(
        lambda r: _country_pass_gate(r.to_dict()), axis=1
    )

    # --- COVID sensitivity — identical gate ---
    validation_nc = pd.DataFrame(validation_nocovid)
    p_vals_nc = validation_nc[["temporal_p", "territory_p"]].to_numpy().ravel().tolist()
    q_vals_nc = bh_fdr(p_vals_nc)
    validation_nc[["temporal_q", "territory_q"]] = np.array(q_vals_nc).reshape(
        len(validation_nc), 2
    )
    validation_nc["country_pass_nocovid"] = validation_nc.apply(
        lambda r: _country_pass_gate(r.to_dict()), axis=1
    )

    # Classify overall COVID sensitivity
    main_pass = set(
        validation.loc[validation["country_pass"], "country"].tolist()
    )
    nocovid_pass = set(
        validation_nc.loc[validation_nc["country_pass_nocovid"], "country"].tolist()
    )
    countries_passing = len(main_pass)
    required = 2
    l2_status = "PASS" if countries_passing >= required else "FAIL"

    if l2_status == "PASS" and nocovid_pass >= main_pass:
        covid_classification = "COVID_ROBUST"
    elif l2_status == "PASS":
        covid_classification = "COVID_SENSITIVE"
    else:
        covid_classification = "FAIL"

    bootstrap = pd.concat(bootstrap_frames, ignore_index=True) if bootstrap_frames else pd.DataFrame()
    edges = pd.concat(edge_frames, ignore_index=True) if edge_frames else pd.DataFrame()

    # Drop eval_years_list from CSV (it's a Python list, not CSV-friendly)
    validation_csv = validation.drop(
        columns=["eval_years_list", "window_gaps_detected", "window_years_excluded"],
        errors="ignore",
    )
    validation_nc_csv = validation_nc.drop(
        columns=["eval_years_list", "window_gaps_detected", "window_years_excluded"],
        errors="ignore",
    )
    validation_csv.to_csv(out_dir / "g1_l2_validation_by_country.csv", index=False)
    validation_nc_csv.to_csv(out_dir / "g1_l2_validation_nocovid.csv", index=False)
    bootstrap.to_csv(out_dir / "g1_l2_bootstrap.csv", index=False)
    edges.to_csv(out_dir / "g1_l2_edges.csv", index=False)

    summary = {
        "validated_layer": "L2_same_sector_cross_territory_cogrowth",
        "window": WINDOW,
        "min_periods": MIN_PERIODS,
        "n_permutations": N_PERMUTATIONS,
        "n_bootstraps": N_BOOTSTRAPS,
        "bootstrap_threshold": BOOTSTRAP_THRESHOLD,
        "l2_status": l2_status,
        "covid_classification": covid_classification,
        "countries_passing": countries_passing,
        "required_countries": required,
        "validation": validation.to_dict(orient="records"),
        "validation_nocovid": validation_nc.to_dict(orient="records"),
        "ineligible_countries": ineligible,
        "edge_rows": int(len(edges)),
        "pt_kz_note": (
            "PT sector KZ is structurally absent from INE indicator 0009703 "
            "(section K not published in enterprise demography statistics). "
            "Verified definitional exclusion per DEC-018. "
            "PT participates in L2 with 8 sectors."
        ),
        "covid_note": (
            f"COVID sensitivity excludes observation year {COVID_YEAR} from all windows. "
            f"eval_year={COVID_YEAR} is retained: its window covers "
            f"[{COVID_YEAR - WINDOW}..{COVID_YEAR - 1}] which predates the shock. "
            f"Windows spanning {COVID_YEAR} lose one year but remain >= {MIN_PERIODS} periods. "
            f"Classification: {covid_classification}."
        ),
    }
    (out_dir / "g1_l2_decision.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    return summary


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def render_report(summary: dict) -> str:
    lines = [
        "# HERALD G1-L2 Causal Co-Growth Graph Audit",
        "",
        f"**Decision:** `{summary['l2_status']}`",
        f"**COVID classification:** `{summary['covid_classification']}`",
        f"**Layer:** `{summary['validated_layer']}`",
        "",
        "L2 edges connect territory pairs within the same sector based on",
        "Pearson correlation of their past sector growth rates over a rolling",
        f"window of {summary['window']} years (min {summary['min_periods']} periods).",
        "Only observation_year <= t-1 is used (causal temporal protocol).",
        "",
        "## PT KZ note",
        "",
        summary["pt_kz_note"],
        "",
        "## COVID sensitivity note",
        "",
        summary["covid_note"],
        "",
        "## Validation (full window, 2020 included as observation year)",
        "",
        "Gate: temporal q ≤ 0.05, territory q ≤ 0.05, LOYO direction pass, ≥ 1 stable bootstrap edge.",
        "",
        "| Country | Sectors | Eval years | Stability | Temporal q | Territory q | LOYO | Stable edges | Pass |",
        "|---|---|---|---:|---:|---:|---|---:|---|",
    ]
    for row in summary["validation"]:
        lines.append(
            f"| {row['country']} | {row['n_sectors']} | {row['eval_years']}"
            f" | {row['observed_stability']:.4f}"
            f" | {row['temporal_q']:.4f}"
            f" | {row['territory_q']:.4f}"
            f" | {row['leave_one_year_direction_pass']}"
            f" | {row['stable_edge_count']}"
            f" | {row['country_pass']} |"
        )

    lines += [
        "",
        f"Countries passing: {summary['countries_passing']}/{summary['required_countries']} required.",
        "",
        "## COVID sensitivity (2020 excluded from observation windows)",
        "",
        (
            "eval_year=2020 is retained (window covers pre-COVID years). "
            "Windows containing 2020 lose that year but remain ≥ min_periods. "
            "Same full gate applied."
        ),
        "",
        "| Country | Eval years | Gaps | Stability | Temporal q | Territory q | LOYO | Stable edges | Pass |",
        "|---|---|---|---:|---:|---:|---|---:|---|",
    ]
    for row in summary["validation_nocovid"]:
        stab = row.get("observed_stability", float("nan"))
        stab_str = f"{stab:.4f}" if isinstance(stab, float) and stab == stab else "N/A"
        gaps = row.get("window_gaps_detected", [])
        gaps_str = ",".join(map(str, gaps)) if gaps else "none"
        lines.append(
            f"| {row['country']} | {row.get('eval_years', 'N/A')}"
            f" | {gaps_str}"
            f" | {stab_str}"
            f" | {row.get('temporal_q', float('nan')):.4f}"
            f" | {row.get('territory_q', float('nan')):.4f}"
            f" | {row.get('leave_one_year_direction_pass', False)}"
            f" | {row.get('stable_edge_count', 0)}"
            f" | {row.get('country_pass_nocovid', False)} |"
        )

    if summary["ineligible_countries"]:
        lines += ["", "## Ineligible countries", ""]
        for row in summary["ineligible_countries"]:
            lines.append(f"- {row['country']}: {row['reason']}")

    lines += [
        "",
        "## Scope",
        "",
        "- PASS validates L2 co-growth as an analytically stable layer.",
        "- Correlation edges are statistical associations, not economic causality.",
        "- Granger predictability must not be inferred from Pearson co-growth.",
        "- L4 mobility and L5 geography remain unvalidated.",
        "- This result does not authorize GNN training, forecast integration",
        "  or economic recommendation.",
        "- Dashboard work remains deferred per DEC-014.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    panel = pd.read_csv(args.panel, dtype={"region_id": str}, low_memory=False)
    summary = build(panel, args.out_dir)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    raise SystemExit(0 if summary["l2_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
