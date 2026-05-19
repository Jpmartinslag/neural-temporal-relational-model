#!/usr/bin/env python3
"""Phase 2F: cheap forecast-combination/switching audit for HERALD.

This script does not train models.  It reuses Phase 2E prediction CSVs and
evaluates whether forecast combination can handle the 2021 regime ambiguity.

Admissible combinations use only no-manual HERALD variants and Ridge.  Manual
control combinations are reported as upper bounds only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


LABELS = [
    "ctrl_manual",
    "cand_2c",
    "E1_resid_pelt_real",
    "E2_velocity_causal",
    "E2_velocity_perm",
    "E4_step_thr05",
    "E4_step_thr06",
    "E4_step_thr07",
    "E1_E4_resid_pelt_thr06",
    "E2_E4_velocity_thr06",
    "E1_E2_E4_combo_light",
]

CORE_NONMANUAL = ["cand_2c", "E4_step_thr05", "E4_step_thr06", "E4_step_thr07"]
EXTENDED_NONMANUAL = [
    "cand_2c",
    "E1_resid_pelt_real",
    "E2_velocity_causal",
    "E4_step_thr05",
    "E4_step_thr06",
    "E4_step_thr07",
    "E1_E4_resid_pelt_thr06",
    "E2_E4_velocity_thr06",
    "E1_E2_E4_combo_light",
]


def wmape(y_true, y_pred) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    denom = np.abs(y).sum()
    return float(np.abs(y - p).sum() / denom) if denom > 0 else float("nan")


def parse_label_seed(path: Path) -> tuple[str, int]:
    name = path.name
    seed_m = re.search(r"_seed_(\d+)_v1\.csv$", name)
    if not seed_m:
        raise ValueError(f"Cannot parse seed from {name}")
    seed = int(seed_m.group(1))
    matches = [lab for lab in LABELS if lab in name]
    if not matches:
        raise ValueError(f"Cannot parse label from {name}")
    # Prefer the longest label so E1_E4... is not parsed as E4...
    label = sorted(matches, key=len, reverse=True)[0]
    return label, seed


def load_predictions(root: Path) -> Dict[tuple[str, int], pd.DataFrame]:
    out = {}
    for path in (root / "data_processed").glob("*predictions_total*_v1.csv"):
        label, seed = parse_label_seed(path)
        df = pd.read_csv(path)
        df = df.sort_values(["target_year", "ZE2020"]).reset_index(drop=True)
        out[(label, seed)] = df
    return out


def assert_aligned(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frames = list(frames)
    base = frames[0][["target_year", "ZE2020", "y_true", "ridge_pred"]].reset_index(drop=True)
    for df in frames[1:]:
        cur = df[["target_year", "ZE2020", "y_true", "ridge_pred"]].reset_index(drop=True)
        if not base.equals(cur):
            raise ValueError("Prediction frames are not aligned")
    return base.copy()


def softmax_weights(losses: np.ndarray, tau: float = 0.01) -> np.ndarray:
    losses = np.asarray(losses, dtype=float)
    if not np.isfinite(losses).all():
        return np.ones_like(losses) / len(losses)
    z = -losses / tau
    z -= z.max()
    w = np.exp(z)
    return w / w.sum()


def combine_recent_error(frames: Dict[str, pd.DataFrame], labels: List[str], seed: int) -> pd.DataFrame:
    base = assert_aligned(frames[l] for l in labels)
    pred = np.zeros(len(base), dtype=float)
    weights_by_year = {}
    for year in sorted(base.target_year.unique()):
        idx = base.target_year == year
        past = base.target_year < year
        if not past.any():
            weights = np.ones(len(labels)) / len(labels)
        else:
            losses = []
            for lab in labels:
                df = frames[lab]
                losses.append(wmape(df.loc[past, "y_true"], df.loc[past, "y_pred"]))
            weights = softmax_weights(np.array(losses), tau=0.01)
        weights_by_year[int(year)] = {lab: float(w) for lab, w in zip(labels, weights)}
        mat = np.vstack([frames[lab].loc[idx, "y_pred"].to_numpy(float) for lab in labels])
        pred[idx] = weights @ mat
    out = base.copy()
    out["y_pred"] = np.maximum(pred, 0.0)
    out["method"] = "recent_error_weighted_core"
    out["seed"] = seed
    out.attrs["weights_by_year"] = weights_by_year
    return out


def make_combo(preds: Dict[tuple[str, int], pd.DataFrame], seed: int, method: str) -> pd.DataFrame:
    frames = {lab: preds[(lab, seed)] for lab in LABELS if (lab, seed) in preds}

    if method == "ridge_only":
        base = assert_aligned([frames["cand_2c"]])
        out = base.copy()
        out["y_pred"] = out["ridge_pred"].clip(lower=0)
    elif method == "avg_clean_e4_06":
        labs = ["cand_2c", "E4_step_thr06"]
        base = assert_aligned(frames[l] for l in labs)
        out = base.copy()
        out["y_pred"] = np.mean([frames[l]["y_pred"].to_numpy(float) for l in labs], axis=0)
    elif method == "median_core_nonmanual":
        base = assert_aligned(frames[l] for l in CORE_NONMANUAL)
        out = base.copy()
        out["y_pred"] = np.median([frames[l]["y_pred"].to_numpy(float) for l in CORE_NONMANUAL], axis=0)
    elif method == "median_extended_nonmanual":
        labs = [l for l in EXTENDED_NONMANUAL if l in frames]
        base = assert_aligned(frames[l] for l in labs)
        out = base.copy()
        out["y_pred"] = np.median([frames[l]["y_pred"].to_numpy(float) for l in labs], axis=0)
    elif method == "recent_error_weighted_core":
        return combine_recent_error(frames, CORE_NONMANUAL, seed)
    elif method == "avg_clean_ridge":
        base = assert_aligned([frames["cand_2c"]])
        out = base.copy()
        out["y_pred"] = 0.5 * frames["cand_2c"]["y_pred"].to_numpy(float) + 0.5 * base["ridge_pred"].to_numpy(float)
    elif method == "avg_clean_manual_upper":
        labs = ["cand_2c", "ctrl_manual"]
        base = assert_aligned(frames[l] for l in labs)
        out = base.copy()
        out["y_pred"] = 0.5 * frames["cand_2c"]["y_pred"].to_numpy(float) + 0.5 * frames["ctrl_manual"]["y_pred"].to_numpy(float)
    elif method == "manual_2021_then_clean_upper":
        base = assert_aligned([frames["cand_2c"], frames["ctrl_manual"]])
        out = base.copy()
        out["y_pred"] = frames["cand_2c"]["y_pred"].to_numpy(float)
        mask_2021 = out["target_year"].to_numpy() == 2021
        out.loc[mask_2021, "y_pred"] = frames["ctrl_manual"].loc[mask_2021, "y_pred"].to_numpy(float)
    else:
        raise ValueError(f"Unknown method={method}")

    out["method"] = method
    out["seed"] = seed
    return out


def summarize(rows: List[pd.DataFrame]) -> pd.DataFrame:
    all_df = pd.concat(rows, ignore_index=True)
    per_run = []
    for (method, seed), g in all_df.groupby(["method", "seed"]):
        rec = {"method": method, "seed": int(seed)}
        per_year = {}
        for year, gy in g.groupby("target_year"):
            per_year[int(year)] = wmape(gy["y_true"], gy["y_pred"])
            rec[f"y{int(year)}"] = per_year[int(year)]
        rec["mean"] = float(np.mean(list(per_year.values())))
        per_run.append(rec)
    run_df = pd.DataFrame(per_run)
    summary = (
        run_df.groupby("method", as_index=False)
        .agg(
            n=("seed", "count"),
            mean=("mean", "mean"),
            std=("mean", "std"),
            y2021=("y2021", "mean"),
            y2021_std=("y2021", "std"),
            y2024=("y2024", "mean"),
            y2025=("y2025", "mean"),
        )
        .sort_values("mean")
    )
    summary["seeds_y2021_lt_0040"] = run_df.groupby("method")["y2021"].apply(lambda s: int((s < 0.040).sum())).reindex(summary["method"]).to_numpy()
    return run_df, summary


def markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for col in cols:
            val = row[col]
            if isinstance(val, float):
                vals.append(f"{val:.6f}")
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    args = ap.parse_args()

    preds = load_predictions(args.root)
    seeds = sorted({seed for _, seed in preds})
    expected = {(lab, seed) for lab in LABELS for seed in seeds}
    missing = sorted(expected - set(preds))
    if missing:
        raise SystemExit(f"Missing predictions: {missing[:10]} ... total={len(missing)}")

    methods = [
        "ridge_only",
        "avg_clean_ridge",
        "avg_clean_e4_06",
        "median_core_nonmanual",
        "median_extended_nonmanual",
        "recent_error_weighted_core",
        "avg_clean_manual_upper",
        "manual_2021_then_clean_upper",
    ]
    rows = []
    weights = {}
    for seed in seeds:
        for method in methods:
            df = make_combo(preds, seed, method)
            rows.append(df)
            if method == "recent_error_weighted_core":
                weights[str(seed)] = df.attrs.get("weights_by_year", {})

    out_dir = args.root / "reports" / "phase2f_switch"
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_df = pd.concat(rows, ignore_index=True)
    pred_df.to_csv(out_dir / "phase2f_switch_predictions.csv", index=False)
    run_df, summary = summarize(rows)
    run_df.to_csv(out_dir / "phase2f_switch_runs.csv", index=False)
    summary.to_csv(out_dir / "phase2f_switch_summary.csv", index=False)
    (out_dir / "phase2f_recent_error_weights.json").write_text(json.dumps(weights, indent=2), encoding="utf-8")

    lines = [
        "# HERALD Phase 2F Switch Audit",
        "",
        "No model was retrained. This audit combines Phase 2E predictions.",
        "",
        "## Summary",
        "",
        markdown_table(summary),
        "",
        "Admissible methods exclude `ctrl_manual`. Methods with `_upper` are diagnostic upper bounds only.",
        "",
    ]
    (out_dir / "HERALD_PHASE2F_SWITCH_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"Saved: {out_dir}")


if __name__ == "__main__":
    main()
