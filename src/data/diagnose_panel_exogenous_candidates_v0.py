import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = ROOT / "data" / "processed" / "panel_zones_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "panel_exogenous_candidates_diagnostic_v0.json"
REPORT_OUT = ROOT / "reports" / "PANEL_EXOGENOUS_CANDIDATES_V0.md"

TARGET_COL = "side_creations_et_total"
ID_COLS = {"ze2020", "libze2020", "reg", "year", "anomaly_reason"}
FLAG_COLS = {"is_structural_anomaly", "has_any_feature_value", "is_source_year_row", "is_training_eligible_panel_v0"}
EXCLUDE_COLS = {
    TARGET_COL,
    "side_stocks_et_total",
    "side_stocks_ul_total",
    "flores_et_total",
}


def safe_corr(x, y):
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 10:
        return np.nan
    x2 = x[mask]
    y2 = y[mask]
    if np.std(x2) == 0 or np.std(y2) == 0:
        return np.nan
    return float(np.corrcoef(x2, y2)[0, 1])


def main():
    df = pd.read_csv(PANEL_PATH)
    df = df[df["is_training_eligible_panel_v0"] == True].copy()
    df = df.sort_values(["ze2020", "year"])

    candidate_cols = [
        c for c in df.columns
        if c not in ID_COLS and c not in FLAG_COLS and c not in EXCLUDE_COLS
    ]

    rows = []
    for col in candidate_cols:
        work = df[["ze2020", "year", TARGET_COL, col]].copy()
        work[f"{col}_lag1"] = work.groupby("ze2020")[col].shift(1)
        work["target_next"] = work.groupby("ze2020")[TARGET_COL].shift(-1)
        usable = work[np.isfinite(work[f"{col}_lag1"]) & np.isfinite(work["target_next"])].copy()
        if len(usable) == 0:
            continue

        rows.append(
            {
                "feature": col,
                "usable_rows": int(len(usable)),
                "coverage_share": float(len(usable) / len(df)),
                "lag1_to_next_target_corr": safe_corr(usable[f"{col}_lag1"].to_numpy(dtype=float), usable["target_next"].to_numpy(dtype=float)),
                "lag1_mean": float(np.nanmean(usable[f"{col}_lag1"])),
                "lag1_std": float(np.nanstd(usable[f"{col}_lag1"])),
            }
        )

    out = sorted(rows, key=lambda r: (abs(r["lag1_to_next_target_corr"]) if np.isfinite(r["lag1_to_next_target_corr"]) else -1), reverse=True)
    payload = {
        "source_panel": str(PANEL_PATH.relative_to(ROOT)),
        "candidate_count": len(out),
        "top_candidates_by_abs_corr": out[:15],
    }

    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Panel Exogenous Candidates v0",
        "",
        "| feature | usable_rows | coverage_share | lag1_to_next_target_corr |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for row in payload["top_candidates_by_abs_corr"]:
        corr = row["lag1_to_next_target_corr"]
        corr_txt = "nan" if not np.isfinite(corr) else f"{corr:.3f}"
        lines.append(f"| {row['feature']} | {row['usable_rows']} | {row['coverage_share']:.3f} | {corr_txt} |")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f'Saved metrics to {METRICS_OUT}')
    print(f'Saved report to {REPORT_OUT}')


if __name__ == "__main__":
    main()
