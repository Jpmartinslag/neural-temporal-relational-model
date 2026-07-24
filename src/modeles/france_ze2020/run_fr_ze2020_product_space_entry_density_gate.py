"""Evaluate leakage-safe product-space density for next-year RCA entry."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.european_panel.build_g1_l1_sector_graph import proximity_matrix
from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import ranking_metrics

PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
SECTORS = ["BE", "FZ", "GI", "JZ", "KZ", "LZ", "MN", "OQ", "RU"]
SEEDS = [42, 43, 44, 45, 46]
FOLDS = list(range(5))
DECISION_YEARS = list(range(2012, 2025))
SPLIT_SEED = 20260723
CLAIM_STATUS = "product_space_entry_density_association_not_causal"
VIEWS = [
    "product_space_density",
    "target_prevalence",
    "target_rca",
    "randomized_product_space",
    "sector_shuffled_density",
    "target_shuffled_density",
    "random_score",
]


def assign_ze_folds(zones: list[str]) -> dict[str, int]:
    ordered = np.array(sorted({str(zone).zfill(4) for zone in zones}))
    shuffled = np.random.default_rng(SPLIT_SEED).permutation(ordered)
    return {zone: int(index % len(FOLDS)) for index, zone in enumerate(shuffled)}


def build_rca_states(panel: pd.DataFrame) -> dict[int, dict[str, object]]:
    frame = panel.copy()
    frame["ze2020"] = frame["ze2020"].astype(str).str.zfill(4)
    key = ["ze2020", "year", "sector_code"]
    if frame.duplicated(key).any():
        raise ValueError("Duplicate ZE-year-sector observations")
    states: dict[int, dict[str, object]] = {}
    for year, snapshot in frame.groupby("year", sort=True):
        births = snapshot.pivot(
            index="ze2020",
            columns="sector_code",
            values="sector_establishment_creations",
        ).reindex(columns=SECTORS)
        if births.isna().any().any():
            raise ValueError(f"Incomplete sector vector in {year}")
        territory_total = births.sum(axis=1).replace(0, np.nan)
        sector_total = births.sum(axis=0)
        grand_total = float(sector_total.sum())
        if grand_total <= 0:
            raise ValueError(f"Zero national sector mass in {year}")
        rca = births.div(territory_total, axis=0).div(
            (sector_total / grand_total).replace(0, np.nan), axis=1
        )
        if not np.isfinite(rca.to_numpy(dtype=float)).all():
            raise ValueError(f"Non-finite RCA in {year}")
        states[int(year)] = {"rca": rca, "specialized": rca.ge(1.0)}
    return states


def _density(specialized: np.ndarray, proximity: np.ndarray) -> np.ndarray:
    weights = proximity.copy().astype(float)
    np.fill_diagonal(weights, 0.0)
    denominator = weights.sum(axis=0)
    return np.divide(
        specialized.astype(float) @ weights,
        denominator,
        out=np.zeros((len(specialized), len(SECTORS)), dtype=float),
        where=denominator > 0,
    )


def build_fold_candidates(
    states: dict[int, dict[str, object]],
    fold_map: dict[str, int],
    *,
    decision_year: int,
    fold: int,
    seed: int,
) -> pd.DataFrame:
    current = states[decision_year]
    following = states[decision_year + 1]
    current_rca = current["rca"]
    current_specialized = current["specialized"]
    next_specialized = following["specialized"].reindex(current_rca.index)
    train_zones = [zone for zone in current_rca.index if fold_map[zone] != fold]
    test_zones = [zone for zone in current_rca.index if fold_map[zone] == fold]
    overlap = set(train_zones) & set(test_zones)
    if overlap:
        raise AssertionError(f"ZE overlap in fold {fold}")

    train_binary = current_specialized.loc[train_zones, SECTORS].to_numpy(dtype=bool)
    test_binary = current_specialized.loc[test_zones, SECTORS].to_numpy(dtype=bool)
    proximity = proximity_matrix(train_binary)
    real_density = _density(test_binary, proximity)
    prevalence = train_binary.mean(axis=0)

    rng = np.random.default_rng(seed + decision_year * 100 + fold)
    permutation = rng.permutation(len(SECTORS))
    randomized_density = _density(test_binary, proximity[permutation][:, permutation])
    shuffled_binary = np.vstack([rng.permutation(row) for row in test_binary])
    sector_shuffled_density = _density(shuffled_binary, proximity)

    rows = []
    for zone_index, zone in enumerate(test_zones):
        for sector_index, sector in enumerate(SECTORS):
            if test_binary[zone_index, sector_index]:
                continue
            rows.append(
                {
                    "ze2020": zone,
                    "decision_year": decision_year,
                    "sector_code": sector,
                    "entry_label": int(
                        next_specialized.loc[zone, sector]
                    ),
                    "product_space_density": real_density[zone_index, sector_index],
                    "target_prevalence": prevalence[sector_index],
                    "target_rca": current_rca.loc[zone, sector],
                    "randomized_product_space": randomized_density[
                        zone_index, sector_index
                    ],
                    "sector_shuffled_density": sector_shuffled_density[
                        zone_index, sector_index
                    ],
                    "random_score": rng.random(),
                }
            )
    candidates = pd.DataFrame(rows)
    candidates["target_shuffled_label"] = candidates.groupby(
        "sector_code", sort=True
    )["entry_label"].transform(lambda values: rng.permutation(values.to_numpy()))
    keys = candidates[["ze2020", "decision_year", "sector_code"]].astype(str)
    checksum = hashlib.sha256(
        "\n".join(keys.agg("|".join, axis=1).sort_values()).encode()
    ).hexdigest()
    candidates["candidate_key_sha256"] = checksum
    candidates["train_test_ze_overlap"] = len(overlap)
    return candidates


def evaluate(states: dict[int, dict[str, object]]) -> pd.DataFrame:
    zones = list(states[min(states)]["rca"].index)
    fold_map = assign_ze_folds(zones)
    rows: list[dict[str, object]] = []
    for seed in SEEDS:
        for decision_year in DECISION_YEARS:
            for fold in FOLDS:
                candidates = build_fold_candidates(
                    states,
                    fold_map,
                    decision_year=decision_year,
                    fold=fold,
                    seed=seed,
                )
                for view in VIEWS:
                    label = (
                        "target_shuffled_label"
                        if view == "target_shuffled_density"
                        else "entry_label"
                    )
                    score_column = (
                        "product_space_density"
                        if view == "target_shuffled_density"
                        else view
                    )
                    scored = candidates.assign(score=candidates[score_column])
                    metrics = ranking_metrics(
                        scored,
                        model_name=view,
                        k=3,
                        target_col=label,
                        label_col=label,
                    )
                    rows.append(
                        {
                            "view": view,
                            "seed": seed,
                            "eval_year": decision_year,
                            "ze_fold": fold,
                            "ndcg_at_3": metrics["ndcg_at_k"],
                            "precision_at_3": metrics["precision_at_k"],
                            "hit_rate_at_3": metrics["hit_rate_at_k"],
                            "average_precision": average_precision_score(
                                candidates[label], candidates[score_column]
                            ),
                            "n_test": len(candidates),
                            "n_test_positive": int(candidates[label].sum()),
                            "candidate_key_sha256": candidates[
                                "candidate_key_sha256"
                            ].iloc[0],
                            "train_test_ze_overlap": candidates[
                                "train_test_ze_overlap"
                            ].iloc[0],
                            "claim_status": CLAIM_STATUS,
                        }
                    )
    metrics = pd.DataFrame(rows)
    numeric = [
        "ndcg_at_3",
        "precision_at_3",
        "hit_rate_at_3",
        "average_precision",
        "n_test",
        "n_test_positive",
    ]
    if not np.isfinite(metrics[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite product-space gate metrics")
    key = ["view", "seed", "eval_year", "ze_fold"]
    if metrics.duplicated(key).any():
        raise ValueError("Duplicate product-space metric keys")
    return metrics.sort_values(key).reset_index(drop=True)


def audit_gate(metrics: pd.DataFrame) -> dict[str, object]:
    keys = ["seed", "eval_year", "ze_fold"]
    real = metrics[metrics["view"] == "product_space_density"][
        keys + ["ndcg_at_3"]
    ].rename(columns={"ndcg_at_3": "real"})
    comparisons = {}
    for control in [
        "target_prevalence",
        "target_rca",
        "randomized_product_space",
        "sector_shuffled_density",
        "target_shuffled_density",
        "random_score",
    ]:
        other = metrics[metrics["view"] == control][keys + ["ndcg_at_3"]].rename(
            columns={"ndcg_at_3": "control"}
        )
        paired = real.merge(other, on=keys, validate="one_to_one")
        lift = paired["real"] - paired["control"]
        comparisons[control] = {
            "mean_ndcg_lift": float(lift.mean()),
            "paired_win_rate": float((lift > 0).mean()),
            "n_pairs": int(len(paired)),
        }

    yearly = metrics[metrics["view"].isin(
        ["product_space_density", "target_prevalence", "target_rca"]
    )].groupby(["eval_year", "view"])["ndcg_at_3"].mean().unstack()
    years_beating_marginals = int(
        (
            (yearly["product_space_density"] > yearly["target_prevalence"])
            & (yearly["product_space_density"] > yearly["target_rca"])
        ).sum()
    )
    integrity = {
        "all_metrics_finite": bool(
            np.isfinite(
                metrics[
                    ["ndcg_at_3", "precision_at_3", "hit_rate_at_3", "average_precision"]
                ].to_numpy(dtype=float)
            ).all()
        ),
        "all_views_present": set(metrics["view"]) == set(VIEWS),
        "identical_populations": bool(
            metrics.groupby(keys)["candidate_key_sha256"].nunique().eq(1).all()
        ),
        "zero_ze_overlap": bool(metrics["train_test_ze_overlap"].eq(0).all()),
        "expected_rows": len(metrics)
        == len(VIEWS) * len(SEEDS) * len(DECISION_YEARS) * len(FOLDS),
    }
    gate_pass = (
        all(integrity.values())
        and comparisons["target_prevalence"]["mean_ndcg_lift"] > 0
        and comparisons["target_rca"]["mean_ndcg_lift"] > 0
        and comparisons["randomized_product_space"]["mean_ndcg_lift"] > 0
        and comparisons["randomized_product_space"]["paired_win_rate"] >= 0.60
        and comparisons["sector_shuffled_density"]["mean_ndcg_lift"] > 0
        and comparisons["sector_shuffled_density"]["paired_win_rate"] >= 0.60
        and comparisons["target_shuffled_density"]["paired_win_rate"] >= 0.80
        and years_beating_marginals >= 9
    )
    return {
        "gate_pass": bool(gate_pass),
        "integrity": integrity,
        "comparisons": comparisons,
        "years_beating_both_marginals": years_beating_marginals,
        "claim_status": CLAIM_STATUS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    panel = pd.read_csv(args.panel, dtype={"ze2020": str})
    metrics = evaluate(build_rca_states(panel))
    summary = (
        metrics.groupby("view", as_index=False)
        .agg(
            mean_ndcg_at_3=("ndcg_at_3", "mean"),
            mean_precision_at_3=("precision_at_3", "mean"),
            mean_hit_rate_at_3=("hit_rate_at_3", "mean"),
            mean_average_precision=("average_precision", "mean"),
            rows=("ndcg_at_3", "size"),
        )
        .sort_values("view")
    )
    summary["claim_status"] = CLAIM_STATUS
    gate = audit_gate(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "fr_ze2020_product_space_entry_density"
    metrics.to_csv(args.output_dir / f"{stem}_metrics_v1.csv", index=False)
    summary.to_csv(args.output_dir / f"{stem}_summary_v1.csv", index=False)
    (args.output_dir / f"{stem}_gate_v1.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    )
    print(summary.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
