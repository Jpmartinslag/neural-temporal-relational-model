from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SEGMENTED_METRICS_PATH = ROOT / "reports" / "segmented_side_target_metrics_core_v0.json"
CONTROLLED_METRICS_PATH = ROOT / "reports" / "controlled_hybrid_side_target_metrics_core_v0.json"

MATRIX_OUT = ROOT / "metadata" / "side_model_decision_matrix_core_v0.csv"
QUALITY_OUT = ROOT / "reports" / "side_model_decision_matrix_quality_v0.json"
REPORT_OUT = ROOT / "reports" / "SIDE_MODEL_DECISION_MATRIX_CORE_V0.md"

BASELINE_MODEL = "persistence"
VALIDATION_TOLERANCE_WMAPE = 0.25
MIN_VALIDATION_IMPROVEMENT_WMAPE = 0.05


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_metrics(metrics: dict, source_package: str) -> pd.DataFrame:
    rows = []
    for model_name, split_metrics in metrics.items():
        row = {"source_package": source_package, "model": model_name}
        for split in ["train", "validation", "test"]:
            values = split_metrics.get(split, {})
            for metric_name in ["wmape", "mae", "rmse", "mape"]:
                row[f"{split}_{metric_name}"] = values.get(metric_name)
        rows.append(row)
    return pd.DataFrame(rows)


def add_decision_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    baseline = out[out["model"] == BASELINE_MODEL].iloc[0]
    baseline_validation = float(baseline["validation_wmape"])
    baseline_test = float(baseline["test_wmape"])

    out["validation_delta_vs_persistence_wmape"] = out["validation_wmape"] - baseline_validation
    out["test_delta_vs_persistence_wmape"] = out["test_wmape"] - baseline_test
    out["beats_persistence_validation"] = out["validation_delta_vs_persistence_wmape"] < 0
    out["beats_persistence_test"] = out["test_delta_vs_persistence_wmape"] < 0
    out["passes_validation_gate"] = out["validation_delta_vs_persistence_wmape"] <= VALIDATION_TOLERANCE_WMAPE

    decisions = []
    for row in out.itertuples(index=False):
        meaningful_validation_gain = row.validation_delta_vs_persistence_wmape <= -MIN_VALIDATION_IMPROVEMENT_WMAPE
        if row.model == BASELINE_MODEL:
            decision = "conservative_default"
            reason = "strong simple baseline and reference for all comparisons"
        elif meaningful_validation_gain and row.beats_persistence_test:
            decision = "candidate_for_next_stage"
            reason = "beats persistence in validation with meaningful margin and also beats test"
        elif row.beats_persistence_validation and row.beats_persistence_test:
            decision = "marginal_candidate"
            reason = "beats persistence in validation and test, but validation gain is too small"
        elif row.beats_persistence_validation and not row.beats_persistence_test:
            decision = "validation_candidate_needs_more_tests"
            reason = "beats persistence in validation but not test"
        elif row.passes_validation_gate and row.beats_persistence_test:
            decision = "test_challenger_not_primary"
            reason = "beats test but does not beat validation; keep as challenger"
        else:
            decision = "diagnostic_only"
            reason = "does not pass validation gate against persistence"
        decisions.append((decision, reason))
    out["decision_status"] = [item[0] for item in decisions]
    out["decision_reason"] = [item[1] for item in decisions]
    return out.sort_values(["validation_wmape", "test_wmape", "model"]).reset_index(drop=True)


def build_report(matrix: pd.DataFrame, quality: dict) -> str:
    lines = [
        "# SIDE Model Decision Matrix Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "## Objetivo",
        "",
        "- transformar os baselines atuais em decisao auditavel",
        "- impedir salto prematuro para STGNN",
        "- separar modelo conservador, candidato e desafiante",
        "",
        "## Regra Atual",
        "",
        f"- baseline de referencia: `{BASELINE_MODEL}`",
        f"- tolerancia de validacao contra persistencia: `{VALIDATION_TOLERANCE_WMAPE:.3f}` ponto de WMAPE",
        f"- ganho minimo para candidato forte: `{MIN_VALIDATION_IMPROVEMENT_WMAPE:.3f}` ponto de WMAPE na validacao",
        "- modelo que vence apenas no teste nao substitui o baseline principal",
        "- modelo que vence validacao e teste vira candidato para proxima etapa",
        "- metricas de pacotes diferentes nao sao equivalentes; o pacote longo e a referencia principal",
        "",
        "## Matriz",
        "",
        "| modelo | validation WMAPE | test WMAPE | delta val vs pers. | delta test vs pers. | status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in matrix.itertuples(index=False):
        lines.append(
            "| `{}` | `{:.3f}` | `{:.3f}` | `{:+.3f}` | `{:+.3f}` | `{}` |".format(
                row.model,
                row.validation_wmape,
                row.test_wmape,
                row.validation_delta_vs_persistence_wmape,
                row.test_delta_vs_persistence_wmape,
                row.decision_status,
            )
        )

    lines += [
        "",
        "## Decisao",
        "",
        f"- modelo conservador: `{quality['conservative_default']}`",
        f"- melhor validacao: `{quality['best_validation_model']}` com WMAPE `{quality['best_validation_wmape']:.3f}`",
        f"- melhor teste: `{quality['best_test_model']}` com WMAPE `{quality['best_test_wmape']:.3f}`",
        f"- candidato recomendado agora: `{quality['recommended_next_candidate']}`",
        "",
        "## Leitura",
        "",
        "- a segmentacao por tamanho+volatilidade e o primeiro ganho limpo sobre persistencia na validacao",
        "- o ridge autoregressivo e desafiante forte no teste, mas perde demais na validacao",
        "- `rich_lags_only` aparece forte no teste, mas vem de uma janela curta diferente e nao e comparacao decisiva",
        "- a decisao correta agora e manter os tres caminhos no radar, com persistencia como referencia obrigatoria",
        "- antes de STGNN, falta testar se a regra segmentada se mantem em outra janela ou validacao temporal adicional",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    segmented = load_json(SEGMENTED_METRICS_PATH)
    controlled = load_json(CONTROLLED_METRICS_PATH)

    segmented_frame = flatten_metrics(segmented, "long_history_segmented")
    controlled_frame = flatten_metrics(controlled["metrics"], "rich_controlled_hybrid")
    controlled_frame = controlled_frame[controlled_frame["model"].isin(["persistence", "lags_only"])]
    controlled_frame["model"] = controlled_frame["model"].replace({"lags_only": "rich_lags_only"})

    matrix = pd.concat([segmented_frame, controlled_frame], ignore_index=True)
    matrix = matrix.drop_duplicates(subset=["model"], keep="first")
    matrix = add_decision_columns(matrix)

    best_validation = matrix.sort_values(["validation_wmape", "test_wmape", "model"]).iloc[0]
    best_test = matrix.sort_values(["test_wmape", "validation_wmape", "model"]).iloc[0]
    candidate_rows = matrix[matrix["decision_status"] == "candidate_for_next_stage"]
    if candidate_rows.empty:
        recommended = BASELINE_MODEL
        recommendation_reason = "no challenger beats persistence in both validation and test"
    else:
        recommended = str(candidate_rows.sort_values(["validation_wmape", "test_wmape"]).iloc[0]["model"])
        recommendation_reason = "candidate beats persistence in both validation and test"

    quality = {
        "baseline_model": BASELINE_MODEL,
        "validation_tolerance_wmape": VALIDATION_TOLERANCE_WMAPE,
        "min_validation_improvement_wmape": MIN_VALIDATION_IMPROVEMENT_WMAPE,
        "rows": int(len(matrix)),
        "conservative_default": BASELINE_MODEL,
        "best_validation_model": str(best_validation["model"]),
        "best_validation_wmape": float(best_validation["validation_wmape"]),
        "best_test_model": str(best_test["model"]),
        "best_test_wmape": float(best_test["test_wmape"]),
        "recommended_next_candidate": recommended,
        "recommendation_reason": recommendation_reason,
        "decision_counts": matrix["decision_status"].value_counts().sort_index().to_dict(),
        "main_conclusion": "Do not advance to STGNN until the segmented/ridge/persistence decision rule is stable under an additional temporal validation.",
    }

    MATRIX_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(MATRIX_OUT, index=False)
    QUALITY_OUT.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_OUT.write_text(build_report(matrix, quality), encoding="utf-8")
    print(
        json.dumps(
            {
                "matrix": str(MATRIX_OUT.relative_to(ROOT)),
                "quality": str(QUALITY_OUT.relative_to(ROOT)),
                "report": str(REPORT_OUT.relative_to(ROOT)),
                **quality,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
