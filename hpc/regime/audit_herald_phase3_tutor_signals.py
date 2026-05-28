#!/usr/bin/env python3
"""Audit candidate macro tutor signals before more HERALD training.

This script does not train a model.  It checks whether available causal macro
signals have a plausible temporal shape for the 2021 problem.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_MACRO = Path("data/processed/phase2h_macro_annual_features_v1.csv")
DEFAULT_PANEL = Path("data/processed/dynamic_stgnn_feature_panel_phase2h_macro_v1.csv")
DEFAULT_OUT = Path("reports/phase3_tutor_signal_audit")


def zscore_by_train(values: pd.Series, years: pd.Series, train_max: int = 2020) -> pd.Series:
    mask = years <= train_max
    mu = float(values[mask].mean())
    sd = float(values[mask].std(ddof=0))
    if not np.isfinite(sd) or sd < 1e-8:
        sd = 1.0
    return (values - mu) / sd


def markdown_table(df: pd.DataFrame, floatfmt: str = ".4f") -> str:
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, np.floating)):
                vals.append(format(float(v), floatfmt) if np.isfinite(v) else "")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def load_target(panel_path: Path) -> pd.DataFrame:
    panel = pd.read_csv(panel_path)
    annual = (
        panel[["target_year", "side_establishment_creations_official"]]
        .groupby("target_year", as_index=False)["side_establishment_creations_official"]
        .sum()
        .rename(columns={"side_establishment_creations_official": "side_total"})
    )
    annual["side_growth"] = annual["side_total"].pct_change()
    annual["side_growth_change"] = annual["side_growth"].diff()
    return annual


def audit_signals(macro_path: Path, panel_path: Path, out_dir: Path) -> None:
    macro = pd.read_csv(macro_path).sort_values("target_year")
    target = load_target(panel_path)
    df = macro.merge(target, on="target_year", how="inner")
    df = df[(df["target_year"] >= 2012) & (df["target_year"] <= 2025)].copy()

    signal_cols = [c for c in macro.columns if c != "target_year"]
    for col in signal_cols:
        df[f"{col}_z_train2020"] = zscore_by_train(df[col], df["target_year"], 2020)
        df[f"{col}_delta"] = df[col].diff()

    rows = []
    for col in signal_cols:
        valid = df.dropna(subset=[col, "side_growth"]).copy()
        z_col = f"{col}_z_train2020"
        d_col = f"{col}_delta"
        corr_growth = valid[col].corr(valid["side_growth"]) if len(valid) >= 3 else np.nan
        corr_growth_change = valid[col].corr(valid["side_growth_change"]) if len(valid) >= 3 else np.nan
        v2021 = df.loc[df["target_year"] == 2021, col]
        z2021 = df.loc[df["target_year"] == 2021, z_col]
        v2022 = df.loc[df["target_year"] == 2022, col]
        z2022 = df.loc[df["target_year"] == 2022, z_col]
        rows.append({
            "signal": col,
            "n_years": int(valid[col].notna().sum()),
            "value_2021_uses_2020": float(v2021.iloc[0]) if len(v2021) and pd.notna(v2021.iloc[0]) else np.nan,
            "z_2021_vs_train_to_2020": float(z2021.iloc[0]) if len(z2021) and pd.notna(z2021.iloc[0]) else np.nan,
            "value_2022_uses_2021": float(v2022.iloc[0]) if len(v2022) and pd.notna(v2022.iloc[0]) else np.nan,
            "z_2022_vs_train_to_2020": float(z2022.iloc[0]) if len(z2022) and pd.notna(z2022.iloc[0]) else np.nan,
            "delta_2021": float(df.loc[df["target_year"] == 2021, d_col].iloc[0])
            if (df["target_year"] == 2021).any() else np.nan,
            "corr_with_side_growth": float(corr_growth) if np.isfinite(corr_growth) else np.nan,
            "corr_with_side_growth_change": float(corr_growth_change) if np.isfinite(corr_growth_change) else np.nan,
        })
    summary = pd.DataFrame(rows)
    summary["shock_signal_strength"] = summary["z_2021_vs_train_to_2020"].abs()
    summary["rebound_separation"] = (
        summary["z_2022_vs_train_to_2020"] - summary["z_2021_vs_train_to_2020"]
    ).abs()
    summary["screening_verdict"] = np.where(
        (summary["shock_signal_strength"] >= 1.5) & (summary["rebound_separation"] >= 1.0),
        "candidate",
        "weak_for_2021",
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "phase3_tutor_signal_timeseries.csv", index=False)
    summary.to_csv(out_dir / "phase3_tutor_signal_summary.csv", index=False)

    md = []
    md.append("# HERALD Phase 3B — Tutor Signal Audit")
    md.append("")
    md.append("No model training here. This screens whether available macro signals have enough temporal shape to justify more GPU runs.")
    md.append("")
    md.append("## Inputs")
    md.append("")
    md.append(f"- Macro file: `{macro_path}`")
    md.append(f"- Panel file: `{panel_path}`")
    md.append("- Rule inherited from Phase 2H: `target_year=t` receives annual monthly mean observed in `t-1`.")
    md.append("")
    md.append("## Target Shape")
    md.append("")
    cols = ["target_year", "side_total", "side_growth", "side_growth_change"]
    md.append(markdown_table(target[target["target_year"].between(2018, 2025)][cols]))
    md.append("")
    md.append("## Signal Screen")
    md.append("")
    show = summary[[
        "signal",
        "n_years",
        "z_2021_vs_train_to_2020",
        "z_2022_vs_train_to_2020",
        "shock_signal_strength",
        "rebound_separation",
        "corr_with_side_growth",
        "screening_verdict",
    ]]
    md.append(markdown_table(show))
    md.append("")
    md.append("## Reading")
    md.append("")
    bad = summary[summary["screening_verdict"].eq("weak_for_2021")]
    if len(bad) == len(summary):
        md.append("- Available Phase 2H macro signals look weak for the 2021 tutor role.")
        md.append("- More architecture is not the next clean move; better tutor signal construction is.")
    else:
        good = ", ".join(summary.loc[summary["screening_verdict"].eq("candidate"), "signal"].tolist())
        md.append(f"- Candidate signals worth training: {good}.")
    md.append("- Keep permutation falsification mandatory for any next battery.")
    md.append("- Do not advance to cross-attention until a tutor signal beats its permuted control.")
    md.append("")
    (out_dir / "HERALD_PHASE3B_TUTOR_SIGNAL_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--macro", type=Path, default=DEFAULT_MACRO)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    audit_signals(args.macro, args.panel, args.out_dir)


if __name__ == "__main__":
    main()
