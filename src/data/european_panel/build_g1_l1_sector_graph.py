"""Build the observable L1 sector-relatedness graph.

The graph follows the product-space proximity definition. A territory is
specialized in a sector when its revealed comparative advantage (RCA) is at
least one. The weight between two sectors is the minimum of the two
conditional co-specialization probabilities.

All snapshots use an observation year and are available only for forecasting
the following year. Edges are associations, not input-output or causal links.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[3]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.data.european_panel.build_g1_observable_graph import (
    N_BOOTSTRAPS,
    N_PERMUTATIONS,
    SECTORS,
    SEED,
    bh_fdr,
    correlation,
    empirical_p,
    leave_one_year_mean,
)


DEFAULT_PANEL = BASE / "data/processed/economic_graph/sector_panel_fr_nl_pt.csv"
DEFAULT_OUT = BASE / "data/processed/economic_graph/g1_l1_sector"
DEFAULT_REPORT = BASE / "reports/HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md"
RCA_THRESHOLD = 1.0
EDGE_THRESHOLD = 0.5
BOOTSTRAP_THRESHOLD = 0.70


def rca_matrix(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Return territory x sector RCA using only one country-year snapshot."""
    births = (
        snapshot.pivot(index="region_id", columns="sector_a10", values="sector_births")
        .reindex(columns=SECTORS)
        .astype(float)
    )
    territory_total = births.sum(axis=1)
    sector_total = births.sum(axis=0)
    grand_total = float(sector_total.sum())
    expected_share = sector_total / grand_total if grand_total > 0 else sector_total * np.nan
    territory_share = births.div(territory_total.replace(0, np.nan), axis=0)
    return territory_share.div(expected_share.replace(0, np.nan), axis=1)


def proximity_matrix(specialized: np.ndarray) -> np.ndarray:
    """Hidalgo-Hausmann sector proximity from binary specialization."""
    binary = specialized.astype(float)
    cooccurrence = binary.T @ binary
    prevalence = binary.sum(axis=0)
    conditional = np.divide(
        cooccurrence,
        prevalence[:, None],
        out=np.zeros_like(cooccurrence, dtype=float),
        where=prevalence[:, None] > 0,
    )
    proximity = np.minimum(conditional, conditional.T)
    np.fill_diagonal(proximity, 1.0)
    return proximity


def edge_vector(matrix: np.ndarray) -> np.ndarray:
    return matrix[np.triu_indices(len(SECTORS), k=1)]


def country_specialization_tensor(
    panel: pd.DataFrame, country: str
) -> tuple[list[int], list[str], np.ndarray]:
    sub = panel[
        panel["country"].eq(country) & panel["mask_complete_sector_vector"].eq(1)
    ].copy()
    if sub.empty:
        unsupported_mask = (
            panel["mask_sector_supported"].eq(0)
            if "mask_sector_supported" in panel
            else pd.Series(False, index=panel.index)
        )
        unsupported = sorted(
            panel.loc[
                panel["country"].eq(country) & unsupported_mask,
                "sector_a10",
            ].unique()
        )
        raise ValueError(
            f"{country}: no complete sector years"
            + (f"; unsupported sectors={unsupported}" if unsupported else "")
        )
    region_count = sub["region_id"].nunique()
    years = [
        int(year)
        for year, frame in sub.groupby("observation_year")
        if frame["region_id"].nunique() == region_count
    ]
    regions = sorted(sub["region_id"].astype(str).unique())
    tensor = np.empty((len(years), len(regions), len(SECTORS)), dtype=bool)
    for index, year in enumerate(years):
        frame = sub[sub["observation_year"].eq(year)].copy()
        rca = rca_matrix(frame).reindex(index=regions, columns=SECTORS)
        if rca.isna().all(axis=0).any():
            missing = rca.columns[rca.isna().all(axis=0)].tolist()
            raise ValueError(f"{country} {year}: sectors without observable mass: {missing}")
        tensor[index] = rca.fillna(0).to_numpy() >= RCA_THRESHOLD
    return years, regions, tensor


def stability(tensor: np.ndarray) -> tuple[float, list[float]]:
    vectors = [edge_vector(proximity_matrix(snapshot)) for snapshot in tensor]
    yearly = [correlation(vectors[i - 1], vectors[i]) for i in range(1, len(vectors))]
    finite = [value for value in yearly if np.isfinite(value)]
    return (float(np.mean(finite)) if finite else np.nan), yearly


def temporal_null(tensor: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    result = np.empty_like(tensor)
    for region in range(tensor.shape[1]):
        for sector in range(tensor.shape[2]):
            result[:, region, sector] = rng.permutation(tensor[:, region, sector])
    return result


def configuration_null(tensor: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Preserve country-year sector prevalence while breaking co-specialization."""
    result = np.empty_like(tensor)
    for year in range(tensor.shape[0]):
        for sector in range(tensor.shape[2]):
            result[year, :, sector] = rng.permutation(tensor[year, :, sector])
    return result


def leave_one_year_direction(
    tensor: np.ndarray,
    temporal_nulls: list[np.ndarray],
    configuration_nulls: list[np.ndarray],
) -> bool:
    _, observed_pairs = stability(tensor)
    temporal_pairs = [stability(null)[1] for null in temporal_nulls]
    configuration_pairs = [stability(null)[1] for null in configuration_nulls]
    for omitted in range(tensor.shape[0]):
        observed = leave_one_year_mean(observed_pairs, omitted)
        if not np.isfinite(observed):
            continue
        temporal = [leave_one_year_mean(values, omitted) for values in temporal_pairs]
        configuration = [
            leave_one_year_mean(values, omitted) for values in configuration_pairs
        ]
        if observed <= np.nanmedian(temporal) or observed <= np.nanmedian(configuration):
            return False
    return True


def bootstrap_edges(
    tensor: np.ndarray, country: str, rng: np.random.Generator
) -> pd.DataFrame:
    counts = {pair: 0 for pair in combinations(range(len(SECTORS)), 2)}
    weights = {pair: [] for pair in counts}
    for _ in range(N_BOOTSTRAPS):
        sampled = rng.integers(0, tensor.shape[0], size=tensor.shape[0])
        matrix = proximity_matrix(tensor[sampled].reshape(-1, len(SECTORS)))
        for pair in counts:
            weight = float(matrix[pair])
            weights[pair].append(weight)
            counts[pair] += int(weight >= EDGE_THRESHOLD)
    return pd.DataFrame(
        [
            {
                "country": country,
                "source_sector": SECTORS[source],
                "target_sector": SECTORS[target],
                "mean_proximity": float(np.mean(weights[(source, target)])),
                "bootstrap_frequency": counts[(source, target)] / N_BOOTSTRAPS,
                "promoted_stable_edge": int(
                    counts[(source, target)] / N_BOOTSTRAPS >= BOOTSTRAP_THRESHOLD
                ),
            }
            for source, target in counts
        ]
    )


def build(panel: pd.DataFrame, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    edge_rows: list[dict] = []
    validation_rows: list[dict] = []
    bootstrap_frames: list[pd.DataFrame] = []
    ineligible_countries: list[dict] = []
    rng = np.random.default_rng(SEED)

    for country in sorted(panel["country"].unique()):
        try:
            years, regions, tensor = country_specialization_tensor(panel, country)
        except ValueError as error:
            ineligible_countries.append(
                {
                    "country": country,
                    "reason": str(error),
                    "country_pass": False,
                }
            )
            continue
        for year_index, year in enumerate(years):
            matrix = proximity_matrix(tensor[year_index])
            for source, target in combinations(range(len(SECTORS)), 2):
                edge_rows.append(
                    {
                        "country": country,
                        "observation_year": year,
                        "available_for_forecast_year": year + 1,
                        "source_sector": SECTORS[source],
                        "target_sector": SECTORS[target],
                        "weight_proximity": float(matrix[source, target]),
                        "source_specialized_territories": int(tensor[year_index, :, source].sum()),
                        "target_specialized_territories": int(tensor[year_index, :, target].sum()),
                        "promoted_edge": int(matrix[source, target] >= EDGE_THRESHOLD),
                    }
                )

        observed, yearly = stability(tensor)
        temporal = [temporal_null(tensor, rng) for _ in range(N_PERMUTATIONS)]
        configuration = [
            configuration_null(tensor, rng) for _ in range(N_PERMUTATIONS)
        ]
        temporal_values = [stability(null)[0] for null in temporal]
        configuration_values = [stability(null)[0] for null in configuration]
        bootstrap = bootstrap_edges(tensor, country, rng)
        bootstrap_frames.append(bootstrap)
        validation_rows.append(
            {
                "country": country,
                "years": f"{years[0]}-{years[-1]}",
                "year_count": len(years),
                "regions": len(regions),
                "observed_stability": observed,
                "temporal_null_median": float(np.nanmedian(temporal_values)),
                "temporal_p": empirical_p(observed, temporal_values),
                "configuration_null_median": float(np.nanmedian(configuration_values)),
                "configuration_p": empirical_p(observed, configuration_values),
                "leave_one_year_direction_pass": leave_one_year_direction(
                    tensor, temporal, configuration
                ),
                "min_yearly_stability": float(np.nanmin(yearly)),
                "stable_edge_count": int(bootstrap["promoted_stable_edge"].sum()),
            }
        )

    edges = pd.DataFrame(edge_rows)
    bootstrap = pd.concat(bootstrap_frames, ignore_index=True)
    validation = pd.DataFrame(validation_rows)
    q_values = bh_fdr(
        validation[["temporal_p", "configuration_p"]].to_numpy().ravel().tolist()
    )
    validation[["temporal_q", "configuration_q"]] = np.asarray(q_values).reshape(
        len(validation), 2
    )
    validation["country_pass"] = (
        validation["temporal_q"].le(0.05)
        & validation["configuration_q"].le(0.05)
        & validation["leave_one_year_direction_pass"]
        & validation["stable_edge_count"].gt(0)
    )

    edges.to_csv(out_dir / "g1_l1_sector_edges.csv", index=False)
    bootstrap.to_csv(out_dir / "g1_l1_bootstrap_stability.csv", index=False)
    validation.to_csv(out_dir / "g1_l1_validation_by_country.csv", index=False)
    pd.DataFrame(ineligible_countries).to_csv(
        out_dir / "g1_l1_ineligible_countries.csv", index=False
    )
    return {
        "validated_layer": "L1_within_territory_sector_cospecialization",
        "method": "RCA>=1 and Hidalgo-Hausmann minimum conditional probability",
        "edge_threshold": EDGE_THRESHOLD,
        "bootstrap_threshold": BOOTSTRAP_THRESHOLD,
        "edge_rows": int(len(edges)),
        "validation": validation.to_dict(orient="records"),
        "ineligible_countries": ineligible_countries,
        "countries_passing": int(validation["country_pass"].sum()),
        "required_countries": 2,
        "l1_status": "PASS" if validation["country_pass"].sum() >= 2 else "FAIL",
    }


def render_report(summary: dict) -> str:
    lines = [
        "# HERALD G1-L1 Sector Relatedness Audit",
        "",
        f"**Decision:** `{summary['l1_status']}`",
        f"**Layer:** `{summary['validated_layer']}`",
        "",
        "L1 uses RCA-based co-specialization and product-space proximity. It is",
        "an observable association between sectors, not an input-output flow,",
        "causal influence or recommendation.",
        "",
        "| Country | Years | Regions | Stability | Temporal q | Configuration q | LOYO | Stable edges | Pass |",
        "|---|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in summary["validation"]:
        lines.append(
            f"| {row['country']} | {row['years']} | {row['regions']} "
            f"| {row['observed_stability']:.4f} | {row['temporal_q']:.4f} "
            f"| {row['configuration_q']:.4f} "
            f"| {row['leave_one_year_direction_pass']} "
            f"| {row['stable_edge_count']} | {row['country_pass']} |"
        )
    if summary["ineligible_countries"]:
        lines += ["", "## Ineligible countries", ""]
        for row in summary["ineligible_countries"]:
            lines.append(f"- {row['country']}: {row['reason']}")
    lines += [
        "",
        f"Countries passing: {summary['countries_passing']}/{summary['required_countries']} required.",
        "",
        "## Scope",
        "",
        "- A PASS validates only L1 sector co-specialization under this definition.",
        "- L2 co-growth, L4 mobility and L5 geography remain separate layers.",
        "- Economic interpretation of the strongest edges must be reviewed before visualization.",
        "- This result does not authorize a GNN, forecast integration or recommendation.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    panel = pd.read_csv(args.panel, dtype={"region_id": str})
    summary = build(panel, args.out_dir)
    args.report.write_text(render_report(summary), encoding="utf-8")
    (args.out_dir / "g1_l1_decision.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["l1_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
