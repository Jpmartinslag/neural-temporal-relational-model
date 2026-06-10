"""Build and validate the G1-L2 causal co-growth graph.

L2: same-sector cross-territory co-growth.

For each eligible country and sector, edge weight between territories (r1, r2)
at evaluation year t = Pearson correlation of their sector growth rates over
the rolling window [t-w, t-1].  Only observation_year <= t-1 data is used,
satisfying the causal temporal protocol in the G0 formal contract.

Agriculture is excluded.  PT KZ is structurally absent from INE 0009703
(section K not reported); this is a verified definitional exclusion, not a
data error (DEC-015).  PT participates with 8 sectors.

Null models (finite-sample corrected p = (1 + sum(null >= obs)) / (1 + N)):
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


def window_matrix(
    growth_years: list[int],
    matrix: np.ndarray,
    eval_year: int,
    window: int = WINDOW,
    exclude_years: frozenset[int] = frozenset(),
) -> np.ndarray:
    """Extract rows for [eval_year-window, eval_year-1], optionally excluding years."""
    target = [
        growth_years.index(y)
        for y in growth_years
        if eval_year - window <= y <= eval_year - 1 and y not in exclude_years
    ]
    return matrix[target, :] if target else np.empty((0, matrix.shape[1]))


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
    """Return years where at least one sector has a full window available."""
    all_years: set[int] = set()
    for sector in sectors:
        _, growth_years, _ = sector_data[sector]
        for y in growth_years:
            # eval_year = y+1 .. y can be used in windows ending at y
            pass
        # The latest growth year is the last element; earliest eval_year
        # needs window years starting at growth_years[0]+window
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
) -> pd.DataFrame:
    """Bootstrap by resampling eval_years; track top-k edge frequency per sector."""
    counts: dict[tuple[str, str, str], int] = {}

    for _ in range(n_bootstraps):
        sampled = rng.integers(0, len(eval_years), size=len(eval_years))
        for sector in sectors:
            region_ids, growth_years, matrix = sector_data[sector]
            # Aggregate correlation matrices over bootstrapped eval_years
            corr_sum = np.zeros(
                (len(region_ids), len(region_ids)), dtype=float
            )
            valid_count = 0
            for idx in sampled:
                t = eval_years[idx]
                w_mat = window_matrix(growth_years, matrix, t, window)
                corr = pairwise_corr(w_mat)
                if not np.all(np.isnan(corr)):
                    where = np.isfinite(corr)
                    corr_sum = np.where(where, corr_sum + corr, corr_sum)
                    valid_count += 1
            if valid_count == 0:
                continue
            mean_corr = corr_sum / valid_count
            # Top-k edges by absolute weight
            n = len(region_ids)
            pairs_idx = np.array(list(zip(*np.triu_indices(n, k=1))))
            if len(pairs_idx) == 0:
                continue
            weights = np.abs(
                [mean_corr[i, j] for i, j in pairs_idx if np.isfinite(mean_corr[i, j])]
            )
            valid_pairs = [
                (i, j) for i, j in pairs_idx if np.isfinite(mean_corr[i, j])
            ]
            if not valid_pairs:
                continue
            order = np.argsort(-weights)
            top_edges = [valid_pairs[k] for k in order[:top_k]]
            for i, j in top_edges:
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
    sectors = eligible_sectors(panel, country)
    if not sectors:
        raise ValueError(f"{country}: no eligible sectors")

    sector_data = {
        s: build_growth_matrix(panel, country, s) for s in sectors
    }

    eval_yrs = eval_years_for_country(sector_data, sectors, window)
    eval_yrs = [t for t in eval_yrs if t not in exclude_years]
    if len(eval_yrs) < 2:
        raise ValueError(f"{country}: fewer than 2 evaluation years available")

    # Observed edge vectors
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
        vecs = [l2_edge_vector(perm_data, sectors, t, window, exclude_years) for t in eval_yrs]
        s, pairs = consecutive_stability(vecs)
        temporal_stabilities.append(s)
        temporal_pairs_list.append(pairs)

    # Territory permutation nulls
    territory_stabilities = []
    territory_pairs_list = []
    for _ in range(n_perm):
        perm_data = permute_growth_territory(sector_data, rng)
        vecs = [l2_edge_vector(perm_data, sectors, t, window, exclude_years) for t in eval_yrs]
        s, pairs = consecutive_stability(vecs)
        territory_stabilities.append(s)
        territory_pairs_list.append(pairs)

    temporal_p = empirical_p(obs_stability, temporal_stabilities)
    territory_p = empirical_p(obs_stability, territory_stabilities)
    loyo = loyo_direction_pass(
        obs_pairs, temporal_pairs_list, territory_pairs_list, len(eval_yrs)
    )

    # Bootstrap
    bootstrap = bootstrap_edge_stability(sector_data, sectors, eval_yrs, rng, window)
    stable_count = int(bootstrap["promoted_stable_edge"].sum()) if not bootstrap.empty else 0

    row = {
        "country": country,
        "sectors": ",".join(sectors),
        "n_sectors": len(sectors),
        "eval_years": f"{eval_yrs[0]}-{eval_yrs[-1]}",
        "n_eval_years": len(eval_yrs),
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
# Edge output (mean correlation across eval_years, per country-sector)
# ---------------------------------------------------------------------------

def build_edge_list(
    panel: pd.DataFrame,
    country: str,
    window: int = WINDOW,
) -> pd.DataFrame:
    sectors = eligible_sectors(panel, country)
    sector_data = {s: build_growth_matrix(panel, country, s) for s in sectors}
    eval_yrs = eval_years_for_country(sector_data, sectors, window)

    records = []
    for sector in sectors:
        region_ids, growth_years, matrix = sector_data[sector]
        n = len(region_ids)
        for t in eval_yrs:
            w_mat = window_matrix(growth_years, matrix, t, window)
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
                            "window_start": t - window,
                            "window_end": t - 1,
                        }
                    )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

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

        # COVID sensitivity (separate rng draw for reproducibility)
        rng2 = np.random.default_rng(SEED + 1)
        try:
            row_nc, _ = validate_country(
                panel, country, rng2, exclude_years=exclude_covid
            )
        except ValueError:
            row_nc = {**row, "exclude_covid": True, "observed_stability": np.nan}

        validation_rows.append(row)
        validation_nocovid.append(row_nc)
        boot.insert(0, "country", country)
        bootstrap_frames.append(boot)
        edge_frames.append(build_edge_list(panel, country))

    if not validation_rows:
        raise RuntimeError("No country produced validation results")

    validation = pd.DataFrame(validation_rows)
    p_vals = validation[["temporal_p", "territory_p"]].to_numpy().ravel().tolist()
    q_vals = bh_fdr(p_vals)
    validation[["temporal_q", "territory_q"]] = np.array(q_vals).reshape(
        len(validation), 2
    )
    validation["country_pass"] = (
        validation["temporal_q"].le(0.05)
        & validation["territory_q"].le(0.05)
        & validation["leave_one_year_direction_pass"]
        & validation["stable_edge_count"].gt(0)
    )

    validation_nc = pd.DataFrame(validation_nocovid)
    p_vals_nc = validation_nc[["temporal_p", "territory_p"]].to_numpy().ravel().tolist()
    q_vals_nc = bh_fdr(p_vals_nc)
    validation_nc[["temporal_q", "territory_q"]] = np.array(q_vals_nc).reshape(
        len(validation_nc), 2
    )
    validation_nc["country_pass_nocovid"] = (
        validation_nc["temporal_q"].le(0.05)
        & validation_nc["territory_q"].le(0.05)
        & validation_nc["leave_one_year_direction_pass"]
    )

    bootstrap = pd.concat(bootstrap_frames, ignore_index=True) if bootstrap_frames else pd.DataFrame()
    edges = pd.concat(edge_frames, ignore_index=True) if edge_frames else pd.DataFrame()

    validation.to_csv(out_dir / "g1_l2_validation_by_country.csv", index=False)
    validation_nc.to_csv(out_dir / "g1_l2_validation_nocovid.csv", index=False)
    bootstrap.to_csv(out_dir / "g1_l2_bootstrap.csv", index=False)
    edges.to_csv(out_dir / "g1_l2_edges.csv", index=False)

    countries_passing = int(validation["country_pass"].sum())
    required = 2
    l2_status = "PASS" if countries_passing >= required else "FAIL"

    summary = {
        "validated_layer": "L2_same_sector_cross_territory_cogrowth",
        "window": WINDOW,
        "min_periods": MIN_PERIODS,
        "n_permutations": N_PERMUTATIONS,
        "n_bootstraps": N_BOOTSTRAPS,
        "bootstrap_threshold": BOOTSTRAP_THRESHOLD,
        "l2_status": l2_status,
        "countries_passing": countries_passing,
        "required_countries": required,
        "validation": validation.to_dict(orient="records"),
        "validation_nocovid": validation_nc.to_dict(orient="records"),
        "ineligible_countries": ineligible,
        "edge_rows": int(len(edges)),
        "pt_kz_note": (
            "PT sector KZ is structurally absent from INE indicator 0009703 "
            "(section K not published in enterprise demography statistics). "
            "This is a verified definitional exclusion per DEC-015. "
            "PT participates in L2 with 8 sectors."
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
        f"**Layer:** `{summary['validated_layer']}`",
        "",
        "L2 edges connect territory pairs within the same sector based on",
        "Pearson correlation of their past sector growth rates over a rolling",
        f"window of {summary['window']} years.  Only data from observation_year",
        "<= t-1 is used (causal temporal protocol).",
        "",
        "## PT KZ note",
        "",
        summary["pt_kz_note"],
        "",
        "## Validation (full window including 2020)",
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
        "## COVID sensitivity (2020 excluded from all windows)",
        "",
        "| Country | Eval years | Stability | Temporal q | Territory q | Pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in summary["validation_nocovid"]:
        stab = row.get("observed_stability", float("nan"))
        stab_str = f"{stab:.4f}" if isinstance(stab, float) and not pd.isna(stab) else "N/A"
        lines.append(
            f"| {row['country']} | {row.get('eval_years', 'N/A')}"
            f" | {stab_str}"
            f" | {row.get('temporal_q', float('nan')):.4f}"
            f" | {row.get('territory_q', float('nan')):.4f}"
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
