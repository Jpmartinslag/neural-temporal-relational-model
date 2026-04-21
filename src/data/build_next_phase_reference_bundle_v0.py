import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PERSISTENCE_SOURCE = ROOT / "reports" / "stgnn_micro_baselines_metrics_v0.json"
REI_METRICS_SOURCE = ROOT / "reports" / "rei_created_baseline_metrics_v0.json"
REI_PRED_SOURCE = ROOT / "data" / "processed" / "rei_created_baseline_predictions_v0.csv"
OUT_JSON = ROOT / "reports" / "next_phase_reference_bundle_v0.json"
OUT_MD = ROOT / "reports" / "NEXT_PHASE_REFERENCE_BUNDLE_V0.md"


def main():
    micro = json.load(open(PERSISTENCE_SOURCE))
    rei = json.load(open(REI_METRICS_SOURCE))
    pred = pd.read_csv(REI_PRED_SOURCE)

    persistence = next(row for row in micro["summary"] if row["model"] == "persistence")
    ridge_lag_only = next(row for row in micro["summary"] if row["model"] == "ridge_lag_only")
    ridge_lag_nbcom = rei["ridge_lag_nbcom"]["summary"]
    rei_created = rei["rei_created_baseline"]["summary"]

    payload = {
        "official_next_phase_baseline": "rei_created_baseline",
        "references": {
            "persistence": persistence,
            "ridge_lag_only": ridge_lag_only,
            "ridge_lag_nbcom": ridge_lag_nbcom,
            "rei_created_baseline": rei_created,
        },
        "prediction_artifact": str(REI_PRED_SOURCE.relative_to(ROOT)),
        "prediction_rows": int(len(pred)),
        "target_years": sorted(pred["target_year"].unique().tolist()),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Next Phase Reference Bundle v0",
        "",
        f"- official baseline: `{payload['official_next_phase_baseline']}`",
        f"- prediction artifact: `{payload['prediction_artifact']}`",
        "",
        "| reference | mean_wmape |",
        "| :--- | ---: |",
        f"| persistence | {persistence['mean_wmape']:.3f} |",
        f"| ridge_lag_only | {ridge_lag_only['mean_wmape']:.3f} |",
        f"| ridge_lag_nbcom | {ridge_lag_nbcom['mean_wmape']:.3f} |",
        f"| rei_created_baseline | {rei_created['mean_wmape']:.3f} |",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {OUT_JSON}")
    print(f"Saved report to {OUT_MD}")


if __name__ == "__main__":
    main()
