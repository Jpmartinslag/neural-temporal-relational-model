"""
HERALD -- France ZE2020 top-3 entry target preflight.

Audits whether the ZE2020 x sector ranking panel supports a stricter target:
sectors that were not already top-3 in a ZE-year but enter the future top-3
growth set. This is a target diagnostic only, not a model and not a
recommendation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeles.france_ze2020.train_fr_ze2020_sector_ranking import (  # noqa: E402
    RANKING_PANEL_PATH,
    load_ranking_panel,
)

CLAIM_STATUS = "top3_entry_target_preflight_not_recommendation"
DEFAULT_HORIZONS = [1, 3]
FORBIDDEN_OUTPUT_COLUMNS = {
    "recommendation",
    "recommended" + "_action",
    "policy" + "_action",
    "causal" + "_effect",
    "causal" + "_impact",
}


def _future_top3_label(panel: pd.DataFrame, horizon: int) -> pd.Series:
    target_col = f"future_growth_{horizon}y"
    mask_col = f"mask_future_growth_{horizon}y_available"
    label_col = f"future_top3_growth_{horizon}y_label"
    if label_col in panel.columns:
        return panel[label_col].astype(int)
    if target_col not in panel.columns or mask_col not in panel.columns:
        raise ValueError(f"Missing target/mask columns for horizon={horizon}")
    rank = panel.groupby(["ze2020", "decision_year"])[target_col].rank(
        ascending=False,
        method="min",
    )
    return ((rank <= 3) & (panel[mask_col] == 1)).astype(int)


def add_top3_entry_labels(panel: pd.DataFrame, horizons: list[int] | None = None) -> pd.DataFrame:
    """Add future top-3 and future top-3 entry labels without mutating input."""
    horizons = horizons or DEFAULT_HORIZONS
    out = panel.copy()
    out["ze2020"] = out["ze2020"].astype(str).str.zfill(4)
    out["decision_year"] = out["decision_year"].astype(int)
    out["current_top3_sector_share_label"] = (out["sector_rank_in_ze_year_t"] <= 3).astype(int)

    for horizon in horizons:
        mask_col = f"mask_future_growth_{horizon}y_available"
        if mask_col not in out.columns:
            raise ValueError(f"Missing mask column: {mask_col}")
        top3_col = f"future_top3_growth_{horizon}y_label"
        entry_col = f"future_top3_entry_{horizon}y_label"
        out[top3_col] = _future_top3_label(out, horizon)
        out[entry_col] = (
            (out[top3_col] == 1)
            & (out["current_top3_sector_share_label"] == 0)
            & (out[mask_col] == 1)
        ).astype(int)
    return out


def summarize_top3_entry_target(
    panel: pd.DataFrame,
    horizons: list[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return overall and by-year preflight summaries for the entry target."""
    horizons = horizons or DEFAULT_HORIZONS
    labelled = add_top3_entry_labels(panel, horizons=horizons)
    summary_rows = []
    year_rows = []

    for horizon in horizons:
        target_col = f"future_growth_{horizon}y"
        mask_col = f"mask_future_growth_{horizon}y_available"
        top3_col = f"future_top3_growth_{horizon}y_label"
        entry_col = f"future_top3_entry_{horizon}y_label"
        eligible = (
            (labelled["ranking_feature_complete"] == 1)
            & (labelled[mask_col] == 1)
            & np.isfinite(labelled[target_col].to_numpy(dtype=float))
        )
        frame = labelled[eligible].copy()
        years = sorted(int(y) for y in frame["decision_year"].unique())

        summary_rows.append(
            {
                "target_horizon_years": int(horizon),
                "eligible_rows": int(len(frame)),
                "eligible_ze_sector_years": int(
                    frame[["ze2020", "sector_code", "decision_year"]].drop_duplicates().shape[0]
                ),
                "eligible_decision_year_start": int(min(years)) if years else None,
                "eligible_decision_year_end": int(max(years)) if years else None,
                "eligible_decision_years": " ".join(str(y) for y in years),
                "future_top3_positive_rows": int(frame[top3_col].sum()),
                "future_top3_positive_rate": float(frame[top3_col].mean()) if len(frame) else float("nan"),
                "future_top3_entry_positive_rows": int(frame[entry_col].sum()),
                "future_top3_entry_positive_rate": float(frame[entry_col].mean()) if len(frame) else float("nan"),
                "claim_status": CLAIM_STATUS,
            }
        )

        by_year = (
            frame.groupby("decision_year", as_index=False)
            .agg(
                eligible_rows=("ze2020", "size"),
                future_top3_positive_rows=(top3_col, "sum"),
                future_top3_entry_positive_rows=(entry_col, "sum"),
            )
            .sort_values("decision_year")
        )
        by_year["target_horizon_years"] = int(horizon)
        by_year["future_top3_entry_positive_rate"] = (
            by_year["future_top3_entry_positive_rows"] / by_year["eligible_rows"]
        )
        by_year["claim_status"] = CLAIM_STATUS
        year_rows.append(by_year)

    summary = pd.DataFrame(summary_rows)
    by_year = pd.concat(year_rows, ignore_index=True) if year_rows else pd.DataFrame()
    forbidden = FORBIDDEN_OUTPUT_COLUMNS.intersection(summary.columns).union(
        FORBIDDEN_OUTPUT_COLUMNS.intersection(by_year.columns)
    )
    if forbidden:
        raise ValueError(f"Forbidden output columns present: {sorted(forbidden)}")
    return summary, by_year


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit the France ZE2020 x sector future top-3 entry target."
    )
    parser.add_argument("--panel", type=Path, default=RANKING_PANEL_PATH)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--horizons", nargs="+", type=int, choices=DEFAULT_HORIZONS, default=DEFAULT_HORIZONS)
    args = parser.parse_args()

    panel = load_ranking_panel(args.panel)
    summary, by_year = summarize_top3_entry_target(panel, horizons=args.horizons)

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        summary.to_csv(args.output_dir / "fr_ze2020_top3_entry_target_preflight_summary_v1.csv", index=False)
        by_year.to_csv(args.output_dir / "fr_ze2020_top3_entry_target_preflight_by_year_v1.csv", index=False)
        (args.output_dir / "fr_ze2020_top3_entry_target_preflight_run_v1.json").write_text(
            json.dumps(
                {
                    "status": "TOP3_ENTRY_TARGET_PREFLIGHT_COMPLETE",
                    "panel": str(args.panel),
                    "horizons": args.horizons,
                    "claim_status": CLAIM_STATUS,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    print("TOP-3 ENTRY TARGET PREFLIGHT -- not causal, not recommendation.")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
