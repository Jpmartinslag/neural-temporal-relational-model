from __future__ import annotations

import json
from pathlib import Path

import evaluate_feature_augmented_baseline_core_v0 as baseline


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    baseline.TENSOR_PATH = ROOT / "data" / "processed" / "stgnn_tensor_package_side_target_core_v0.npz"
    baseline.SAMPLE_INDEX_PATH = ROOT / "metadata" / "stgnn_tensor_sample_index_side_target_core_v0.csv"
    baseline.TARGET_PANEL_PATH = ROOT / "data" / "processed" / "target_side_establishments_annual_core_v0.csv"
    baseline.FEATURE_REGISTRY_PATH = ROOT / "metadata" / "stgnn_tensor_feature_registry_side_target_core_v0.csv"
    baseline.PRED_OUT = ROOT / "data" / "processed" / "feature_augmented_baseline_side_target_predictions_core_v0.csv"
    baseline.METRICS_OUT = ROOT / "reports" / "archive" / "benchmarks" / "feature_augmented_baseline_side_target_metrics_core_v0.json"
    baseline.REPORT_OUT = ROOT / "reports" / "archive" / "benchmarks" / "FEATURE_AUGMENTED_BASELINE_SIDE_TARGET_CORE_V0.md"
    baseline.TARGET_COL = "side_establishment_creations_official"

    pred, quality = baseline.evaluate()
    quality["target_column"] = baseline.TARGET_COL
    quality["target_source"] = str(baseline.TARGET_PANEL_PATH.relative_to(ROOT))
    quality["interpretation"] = (
        "This baseline tests whether the current external feature panel adds signal over local persistence "
        "after replacing the proxy with official SIDE establishment creations."
    )
    pred.to_csv(baseline.PRED_OUT, index=False)
    baseline.METRICS_OUT.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    baseline.write_report(quality)
    text = baseline.REPORT_OUT.read_text(encoding="utf-8")
    text = text.replace("# Feature-Augmented Baseline Core v0", "# Feature-Augmented Baseline SIDE Target Core v0", 1)
    text = text.replace(
        "Objetivo:\n\n- testar se features externas do painel adicionam sinal sobre a persistencia local",
        "Objetivo:\n\n- testar se features externas do painel adicionam sinal sobre a persistencia local usando target oficial `SIDE`",
        1,
    )
    text = text.replace(
        "## Modelos",
        f"Target: `{baseline.TARGET_COL}`\n\nFonte: `{baseline.TARGET_PANEL_PATH.relative_to(ROOT)}`\n\n## Modelos",
        1,
    )
    baseline.REPORT_OUT.write_text(text, encoding="utf-8")
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
