"""
evaluate_mobility_spatial_baseline_core_v0.py

Objetivo:
- testar se o grafo de mobilidade melhora o baseline de persistencia
- comparar diretamente: persistencia, vizinhos-geograficos, vizinhos-mobilidade
- usar o pacote tensorial com target oficial SIDE

Motivacao:
- o grafo geografico escolheu alpha = 1.0 (ignorar vizinhos) em todos os baselines anteriores
- a hipotese e que zonas ligadas por fluxos de trabalhadores tem dinamicas correlacionadas
- se o grafo de mobilidade tambem escolher alpha = 1.0, a conclusao e que nenhum grafo
  simples agrega sinal preditivo com as features e target atuais

Regra metodologica:
- alpha e selecionado apenas na validacao
- metricas sao reportadas em treino, validacao e teste
- nao ha refit apos selecao de alpha
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

TENSOR_SIDE = ROOT / "data/processed/stgnn_tensor_package_side_target_core_v0.npz"
MOBILITY_NPZ = ROOT / "data/processed/mobility_graph_core_v0.npz"
SAMPLE_INDEX = ROOT / "metadata/stgnn_tensor_sample_index_side_target_core_v0.csv"
NODES_CSV = ROOT / "data/processed/graph_nodes_ze2020_core_v0.csv"
TARGET_PANEL = ROOT / "data/processed/target_side_establishments_annual_core_v0.csv"
TARGET_COL = "side_establishment_creations_official"

OUT_PRED = ROOT / "data/processed/mobility_spatial_baseline_predictions_core_v0.csv"
OUT_JSON = ROOT / "reports/mobility_spatial_baseline_metrics_core_v0.json"
OUT_MD = ROOT / "reports/MOBILITY_SPATIAL_BASELINE_CORE_V0.md"

ALPHA_GRID = np.linspace(0.0, 1.0, 21)


def wmape(y_true, y_pred):
    d = float(np.sum(np.abs(y_true)))
    return float(np.sum(np.abs(y_true - y_pred)) / d * 100.0) if d > 0 else float("nan")

def mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))

def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mape(y_true, y_pred):
    mask = y_true != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def metric_block(df, pred_col):
    yt = df["y_true"].to_numpy(float)
    yp = df[pred_col].to_numpy(float)
    return {"mae": mae(yt, yp), "rmse": rmse(yt, yp),
            "mape": mape(yt, yp), "wmape": wmape(yt, yp)}

def best_alpha(val_df, col_a, col_b):
    scores = []
    for a in ALPHA_GRID:
        blend = a * val_df[col_a] + (1 - a) * val_df[col_b]
        scores.append((a, wmape(val_df["y_true"].values, blend.values)))
    scores.sort(key=lambda x: x[1])
    return scores[0][0], scores[0][1]


def load_target_by_year(nodes_sorted):
    """Carrega target SIDE por ano e retorna dict {year: array[N]}."""
    tpanel = pd.read_csv(TARGET_PANEL, dtype={"ze2020": str})
    ze_order = nodes_sorted["ze2020"].tolist()
    by_year = {}
    for yr, grp in tpanel.groupby("target_year"):
        grp = grp.set_index("ze2020").reindex(ze_order)
        by_year[int(yr)] = grp[TARGET_COL].to_numpy(float)
    return by_year


def main():
    tensor = np.load(TENSOR_SIDE, allow_pickle=True)
    mob = np.load(MOBILITY_NPZ, allow_pickle=True)

    y_raw = tensor["y_raw"].astype(float)           # [T, N] — target_year values
    adj_geo = tensor["adjacency_row_normalized_self_loop"].astype(float)
    adj_mob = mob["adjacency_row_normalized_self_loop"].astype(float)

    feat_years = tensor["feature_year"].astype(int)
    tgt_years = tensor["target_year"].astype(int)
    node_idx_arr = tensor["node_idx"].astype(int)

    sample_index = pd.read_csv(SAMPLE_INDEX)
    nodes = pd.read_csv(NODES_CSV, dtype=str).reset_index(drop=True)

    mob_ze_order = mob["ze2020_index"].astype(str)
    nodes_sorted = nodes.sort_values("ze2020").reset_index(drop=True)

    assert list(mob_ze_order) == list(nodes_sorted["ze2020"].tolist()), \
        "Ordem dos nos de mobilidade nao bate com tensor SIDE"

    # target por ano para persistencia (y em feature_year, nao em target_year)
    target_by_year = load_target_by_year(nodes_sorted)

    rows = []
    T = y_raw.shape[0]

    for t in range(T):
        split = sample_index.loc[t, "split"]
        fy = int(feat_years[t])
        ty = int(tgt_years[t])

        # y_true = target no target_year (o que queremos prever)
        y_true = y_raw[t]

        # persistencia e media de vizinhos usam target no feature_year (ano atual)
        if fy in target_by_year:
            y_t = target_by_year[fy]
        else:
            # fallback: usar y_raw do sample anterior se feature_year nao esta no panel
            y_t = y_raw[max(0, t - 1)]

        pred_persistence = y_t
        pred_geo = adj_geo @ y_t
        pred_mob = adj_mob @ y_t

        N = len(y_true)
        for n in range(N):
            rows.append({
                "sample_idx": t,
                "feature_year": fy,
                "target_year": ty,
                "split": split,
                "node_idx": int(node_idx_arr[n]),
                "ze2020": nodes_sorted.iloc[n]["ze2020"],
                "y_true": float(y_true[n]),
                "pred_persistence": float(pred_persistence[n]),
                "pred_geo_neighbor": float(pred_geo[n]),
                "pred_mob_neighbor": float(pred_mob[n]),
            })

    pred = pd.DataFrame(rows)

    # selecao de alpha na validacao para cada grafo
    val = pred[pred["split"] == "validation"]
    alpha_geo, wmape_geo_val = best_alpha(val, "pred_persistence", "pred_geo_neighbor")
    alpha_mob, wmape_mob_val = best_alpha(val, "pred_persistence", "pred_mob_neighbor")

    pred["pred_geo_blend"] = (
        alpha_geo * pred["pred_persistence"] + (1 - alpha_geo) * pred["pred_geo_neighbor"]
    )
    pred["pred_mob_blend"] = (
        alpha_mob * pred["pred_persistence"] + (1 - alpha_mob) * pred["pred_mob_neighbor"]
    )

    pred.to_csv(OUT_PRED, index=False)

    # metricas por split
    models = {
        "persistence": "pred_persistence",
        "geo_neighbor_average": "pred_geo_neighbor",
        "geo_blend": "pred_geo_blend",
        "mobility_neighbor_average": "pred_mob_neighbor",
        "mobility_blend": "pred_mob_blend",
    }
    metrics = {}
    for name, col in models.items():
        metrics[name] = {}
        for split in ["train", "validation", "test"]:
            sf = pred[pred["split"] == split]
            if sf.empty:
                continue
            metrics[name][split] = metric_block(sf, col)

    quality = {
        "graph_geographic_alpha": float(alpha_geo),
        "graph_geographic_val_wmape": round(wmape_geo_val, 4),
        "graph_mobility_alpha": float(alpha_mob),
        "graph_mobility_val_wmape": round(wmape_mob_val, 4),
        "metrics": metrics,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    # --- relatorio ---
    persist_val = metrics["persistence"]["validation"]["wmape"]
    geo_val = metrics["geo_blend"]["validation"]["wmape"]
    mob_val = metrics["mobility_blend"]["validation"]["wmape"]

    geo_gain = persist_val - geo_val
    mob_gain = persist_val - mob_val

    if mob_val < persist_val and mob_gain > geo_gain:
        conclusion = "grafo de mobilidade supera o geografico e ambos superam persistencia — mobilidade agrega sinal"
    elif mob_val < persist_val:
        conclusion = "grafo de mobilidade supera persistencia — sinal positivo, mas verificar magnitude"
    elif alpha_mob == 1.0:
        conclusion = "grafo de mobilidade escolheu alpha = 1.0 — ignorar vizinhos e otimo — nenhum grafo simples agrega sinal sobre persistencia"
    else:
        conclusion = "grafo de mobilidade nao supera persistencia de forma clara"

    lines = [
        "# Mobility Spatial Baseline Core v0",
        "",
        "Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- testar se o grafo de mobilidade agrega sinal preditivo sobre persistencia",
        "- comparar diretamente com o grafo geografico",
        "- usar target oficial SIDE estabelecimentos",
        "",
        "## Configuracao",
        "",
        "- pacote tensorial: `stgnn_tensor_package_side_target_core_v0.npz`",
        "- grafo geografico: adjacencia por fronteira ZE2020 (existente)",
        "- grafo de mobilidade: fluxos domicilio-trabalho RP 2021, agregados por ZE2020",
        "- alpha selecionado na validacao por minimo WMAPE",
        "",
        "## Alphas Selecionados",
        "",
        f"- grafo geografico: `alpha = {alpha_geo:.2f}` (val WMAPE = `{wmape_geo_val:.3f}`)",
        f"- grafo de mobilidade: `alpha = {alpha_mob:.2f}` (val WMAPE = `{wmape_mob_val:.3f}`)",
        "",
        "## Metricas por Modelo",
        "",
        "| modelo | split | WMAPE | MAE |",
        "|---|---|---|---|",
    ]
    for name, col in models.items():
        for split in ["train", "validation", "test"]:
            if split not in metrics.get(name, {}):
                continue
            m = metrics[name][split]
            lines.append(f"| `{name}` | {split} | `{m['wmape']:.3f}` | `{m['mae']:.1f}` |")

    lines += [
        "",
        "## Leitura",
        "",
        f"- persistencia (validacao): WMAPE = `{persist_val:.3f}`",
        f"- blend geografico (validacao): WMAPE = `{geo_val:.3f}` (alpha = `{alpha_geo:.2f}`)",
        f"- blend mobilidade (validacao): WMAPE = `{mob_val:.3f}` (alpha = `{alpha_mob:.2f}`)",
        "",
        f"**Conclusao: {conclusion}**",
        "",
        "## Decisao",
        "",
    ]

    if alpha_mob == 1.0:
        lines += [
            "- o grafo de mobilidade, como o geografico, nao agrega sinal sobre persistencia local",
            "- alpha = 1.0 significa que o otimo e ignorar os vizinhos de mobilidade",
            "- a conclusao se torna mais forte: nem vizinhanca geografica nem fluxo de trabalhadores",
            "  adiciona sinal preditivo sobre o target SIDE com as features e temporal depth atuais",
            "- isso nao invalida o uso do grafo no STGNN, mas exige que o STGNN seja avaliado",
            "  contra persistencia com rigor antes de qualquer interpretacao",
            "- proximo passo: extensao temporal das features (FLORES historico, SIDE stocks 2019-2020)",
            "  para aumentar o numero efetivo de amostras de treino",
        ]
    else:
        lines += [
            f"- o grafo de mobilidade mostrou ganho com alpha = `{alpha_mob:.2f}`",
            "- esse resultado justifica incluir o grafo de mobilidade no pacote tensorial",
            "- verificar se o ganho se mantem no teste antes de usar como evidencia definitiva",
        ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # console
    print("=" * 60)
    print("MOBILITY SPATIAL BASELINE — SIDE TARGET CORE v0")
    print("=" * 60)
    print(f"Grafo geografico : alpha={alpha_geo:.2f}  val_WMAPE={wmape_geo_val:.4f}")
    print(f"Grafo mobilidade : alpha={alpha_mob:.2f}  val_WMAPE={wmape_mob_val:.4f}")
    print()
    for name in models:
        for split in ["validation", "test"]:
            if split in metrics.get(name, {}):
                m = metrics[name][split]
                print(f"  {name:35s} [{split:10s}] WMAPE={m['wmape']:.3f}")
    print()
    print(f"Conclusao: {conclusion}")


if __name__ == "__main__":
    main()
