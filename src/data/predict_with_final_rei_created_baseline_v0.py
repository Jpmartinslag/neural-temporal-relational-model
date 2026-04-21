import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = ROOT / "data" / "processed" / "final_rei_created_baseline_artifact_v0.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with required feature columns.")
    parser.add_argument("--output", required=True, help="CSV path for predictions.")
    args = parser.parse_args()

    artifact = json.loads(ARTIFACT_PATH.read_text())
    features = artifact["feature_set"]
    means = artifact["feature_means"]
    stds = artifact["feature_stds"]
    coefs = artifact["coefficients"]
    intercept = float(artifact["intercept"])

    df = pd.read_csv(args.input)
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    score = np.full(len(df), intercept, dtype=float)
    for feat in features:
        raw = df[feat].to_numpy(dtype=float)
        mean = float(means[feat])
        std = float(stds[feat])
        scaled = np.where(np.isfinite(raw), (raw - mean) / std, 0.0)
        score += scaled * float(coefs[feat])

    out = df.copy()
    out["prediction"] = np.clip(score, a_min=0, a_max=None)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(json.dumps({"rows": int(len(out)), "output": args.output}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
