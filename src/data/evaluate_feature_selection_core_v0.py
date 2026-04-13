"""
evaluate_feature_selection_core_v0.py

Objetivo:
- Auditar as 23 features do pacote tensorial SIDE target
- Calcular taxa de observacao por feature e por ano de treino
- Calcular correlacao com o target nas amostras observadas
- Identificar features inuteis, esparsas e bem cobertas
- Produzir recomendacao auditavel para o subconjunto Phase 1

Regra metodologica:
- Todas as metricas de selecao sao calculadas APENAS no split de treino
- Validacao e teste nao influenciam a selecao
- A mascara x_mask e usada para separar observacao real de imputacao
"""

import json
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
TENSOR_PATH = ROOT / "data/processed/stgnn_tensor_package_side_target_core_v0.npz"
SAMPLE_INDEX_PATH = ROOT / "metadata/stgnn_tensor_sample_index_side_target_core_v0.csv"
FEATURE_REGISTRY_PATH = ROOT / "metadata/stgnn_tensor_feature_registry_side_target_core_v0.csv"
OUT_CSV = ROOT / "metadata/feature_selection_audit_core_v0.csv"
OUT_JSON = ROOT / "reports/feature_selection_audit_core_quality_v0.json"
OUT_MD = ROOT / "reports/FEATURE_SELECTION_AUDIT_CORE_V0.md"


def load_tensor():
    data = np.load(TENSOR_PATH)
    return {k: data[k] for k in data.files}


def get_train_mask(sample_index):
    is_train = sample_index["split"] == "train"
    return is_train.values


def correlate_with_target(x_raw, x_mask, y_raw, train_idx):
    """
    Por feature: correlacao de Pearson entre x e y usando apenas celulas
    que sao (a) no split de treino e (b) observadas (mask=1).
    Retorna vetor [n_features] de correlacoes. NaN se < 10 pares validos.
    """
    T, N, F = x_raw.shape
    corr = np.full(F, np.nan)
    n_valid = np.zeros(F, dtype=int)

    for f in range(F):
        pairs_x, pairs_y = [], []
        for t in train_idx:
            obs = x_mask[t, :, f].astype(bool)
            if obs.sum() == 0:
                continue
            pairs_x.append(x_raw[t, obs, f])
            pairs_y.append(y_raw[t, obs])
        if not pairs_x:
            continue
        px = np.concatenate(pairs_x)
        py = np.concatenate(pairs_y)
        n_valid[f] = len(px)
        if len(px) >= 10 and px.std() > 0 and py.std() > 0:
            corr[f] = float(np.corrcoef(px, py)[0, 1])

    return corr, n_valid


def obs_rate_by_year(x_mask, sample_index, feature_names):
    """
    Taxa de observacao por feature e por ano de feature.
    """
    rows = []
    for i, row in sample_index.iterrows():
        t = int(row["sample_idx"])
        year = int(row["feature_year"])
        split = row["split"]
        for f, fname in enumerate(feature_names):
            obs = float(x_mask[t, :, f].mean())
            rows.append({"feature_name": fname, "feature_year": year,
                         "split": split, "obs_rate": obs})
    return pd.DataFrame(rows)


def classify_feature(row):
    tr = row["train_obs_rate"]
    if tr == 0.0:
        return "useless_no_train_obs"
    if tr < 0.34:
        return "sparse_low_train_coverage"
    if tr < 0.67:
        return "moderate_train_coverage"
    return "well_covered"


def main():
    tensor = load_tensor()
    x_raw = tensor["x_raw"]              # [T, N, F]
    x_mask = tensor["x_mask"]            # [T, N, F]
    y_raw = tensor["y_raw"]              # [T, N]
    sample_index = pd.read_csv(SAMPLE_INDEX_PATH)
    feature_registry = pd.read_csv(FEATURE_REGISTRY_PATH)
    feature_names = feature_registry["feature_name"].tolist()

    # indices de treino
    train_rows = sample_index[sample_index["split"] == "train"]
    train_idx = train_rows["sample_idx"].astype(int).tolist()
    val_rows = sample_index[sample_index["split"] == "validation"]
    test_rows = sample_index[sample_index["split"] == "test"]

    T, N, F = x_raw.shape
    assert len(feature_names) == F

    # --- taxa de observacao por feature e por ano ---
    obs_by_year = obs_rate_by_year(x_mask, sample_index, feature_names)

    # taxa de observacao media no treino por feature
    train_obs = obs_by_year[obs_by_year["split"] == "train"].groupby("feature_name")["obs_rate"].mean()

    # taxa de observacao global por feature
    global_obs = obs_by_year.groupby("feature_name")["obs_rate"].mean()

    # --- correlacao com target (apenas treino, apenas observado) ---
    corr_with_target, n_valid_pairs = correlate_with_target(x_raw, x_mask, y_raw, train_idx)

    # --- dataframe de auditoria ---
    audit = pd.DataFrame({
        "feature_name": feature_names,
        "train_obs_rate": [float(train_obs.get(n, 0.0)) for n in feature_names],
        "global_obs_rate": [float(global_obs.get(n, 0.0)) for n in feature_names],
        "corr_with_target_train": corr_with_target,
        "n_valid_pairs_train": n_valid_pairs,
    })

    audit["feature_type"] = audit["feature_name"].apply(
        lambda x: "static" if x.startswith("static_") else "dynamic"
    )
    audit["coverage_class"] = audit.apply(classify_feature, axis=1)
    audit["abs_corr"] = audit["corr_with_target_train"].abs()

    # --- recomendacao Phase 1 ---
    # Incluir: bem cobertas + moderadas com correlacao minima
    # Excluir: sem observacao no treino
    # Revisar: esparsas (incluir mas sinalizar)
    def recommend(row):
        if row["coverage_class"] == "useless_no_train_obs":
            return "exclude"
        if row["coverage_class"] == "sparse_low_train_coverage":
            return "include_flagged"
        return "include"

    audit["recommendation"] = audit.apply(recommend, axis=1)

    audit = audit.sort_values(["recommendation", "abs_corr"], ascending=[True, False])
    audit.to_csv(OUT_CSV, index=False)

    # --- sumario ---
    include = audit[audit["recommendation"] == "include"]
    flagged = audit[audit["recommendation"] == "include_flagged"]
    exclude = audit[audit["recommendation"] == "exclude"]

    top_corr = (
        audit[audit["recommendation"].isin(["include", "include_flagged"])]
        .dropna(subset=["corr_with_target_train"])
        .nlargest(5, "abs_corr")[["feature_name", "corr_with_target_train", "train_obs_rate"]]
        .to_dict(orient="records")
    )

    quality = {
        "total_features": int(F),
        "include_count": int(len(include)),
        "include_flagged_count": int(len(flagged)),
        "exclude_count": int(len(exclude)),
        "excluded_features": exclude["feature_name"].tolist(),
        "flagged_features": flagged["feature_name"].tolist(),
        "top5_by_abs_corr_with_target_train": top_corr,
        "mean_train_obs_rate_included": round(float(include["train_obs_rate"].mean()), 3),
        "mean_abs_corr_included": round(float(include["abs_corr"].dropna().mean()), 3),
        "static_features_count": int((audit["feature_type"] == "static").sum()),
        "dynamic_features_count": int((audit["feature_type"] == "dynamic").sum()),
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(quality, f, indent=2, ensure_ascii=False)

    # --- relatorio markdown ---
    lines = []
    lines += [
        "# Feature Selection Audit Core v0",
        "",
        f"Data: 2026-04-13",
        "",
        "Objetivo:",
        "",
        "- auditar as 23 features do pacote tensorial com target oficial SIDE",
        "- identificar features sem sinal no treino",
        "- calcular correlacao com o target usando apenas valores observados",
        "- produzir recomendacao de subconjunto para os primeiros experimentos",
        "",
        "## Regra Metodologica",
        "",
        "- todas as metricas foram calculadas exclusivamente no split de treino",
        "- a correlacao usa apenas celulas com `x_mask = 1` (observadas realmente)",
        "- features com `train_obs_rate = 0` nao tem nenhuma observacao real no treino",
        "",
        "## Sumario",
        "",
        f"- total de features: `{quality['total_features']}`",
        f"- incluidas diretamente: `{quality['include_count']}`",
        f"- incluidas com sinalizacao: `{quality['include_flagged_count']}`",
        f"- excluidas (sem observacao no treino): `{quality['exclude_count']}`",
        f"- features estaticas: `{quality['static_features_count']}`",
        f"- features dinamicas: `{quality['dynamic_features_count']}`",
        "",
        "## Features Excluidas",
        "",
    ]
    for fn in quality["excluded_features"]:
        r = audit[audit["feature_name"] == fn].iloc[0]
        lines.append(f"- `{fn}`: train_obs_rate=`{r['train_obs_rate']:.3f}` — sem observacao real no treino, apenas imputacao")
    lines += [
        "",
        "Leitura: estas features nao devem ser interpretadas em modelos Phase 1.",
        "Qualquer peso aprendido sobre elas reflete imputacao, nao sinal economico.",
        "",
        "## Features Sinalizadas (esparsas, mas com alguma observacao)",
        "",
    ]
    for fn in quality["flagged_features"]:
        r = audit[audit["feature_name"] == fn].iloc[0]
        corr_str = f"{r['corr_with_target_train']:.3f}" if not np.isnan(r["corr_with_target_train"]) else "n/a"
        lines.append(
            f"- `{fn}`: train_obs_rate=`{r['train_obs_rate']:.3f}`, "
            f"corr_target=`{corr_str}`, n_pares=`{int(r['n_valid_pairs_train'])}`"
        )
    lines += [
        "",
        "## Top 5 por Correlacao Absoluta com Target (treino, observado)",
        "",
    ]
    for rec in quality["top5_by_abs_corr_with_target_train"]:
        lines.append(
            f"- `{rec['feature_name']}`: corr=`{rec['corr_with_target_train']:.3f}`, "
            f"train_obs_rate=`{rec['train_obs_rate']:.3f}`"
        )
    lines += [
        "",
        "## Tabela Completa",
        "",
        "| feature_name | type | train_obs | global_obs | corr_target | class | rec |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, row in audit.iterrows():
        corr_str = f"{row['corr_with_target_train']:.3f}" if not np.isnan(row["corr_with_target_train"]) else "n/a"
        lines.append(
            f"| `{row['feature_name']}` | {row['feature_type']} "
            f"| {row['train_obs_rate']:.2f} | {row['global_obs_rate']:.2f} "
            f"| {corr_str} | {row['coverage_class']} | **{row['recommendation']}** |"
        )
    lines += [
        "",
        "## Decisao",
        "",
        "- `flores_presential_unit_loc_total` e `flores_productive_unit_loc_total` sao excluidas dos experimentos Phase 1",
        "- a exclusao e justificada por ausencia total de observacao no treino, nao por baixa importancia tematica",
        "- essas features podem voltar em versoes futuras com extensao temporal do FLORES historico",
        "- features esparsas (train_obs_rate < 0.34) sao incluidas com sinalizacao explícita",
        "- o subconjunto recomendado para Phase 1 fica com `21` features efetivas",
        "",
        "## Proxima Etapa",
        "",
        "- construir grafo de mobilidade a partir de `DS_RP_NAVETTES_PRINC_2022`",
        "- substituir adjacencia geografica estatica por adjacencia de fluxo economico",
        "- repetir baseline espacial com o novo grafo antes de qualquer STGNN",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # console
    print("=" * 60)
    print("FEATURE SELECTION AUDIT — SIDE TARGET CORE v0")
    print("=" * 60)
    print(f"Total features  : {F}")
    print(f"Include         : {len(include)}")
    print(f"Include flagged : {len(flagged)}")
    print(f"Exclude         : {len(exclude)}")
    print()
    print("EXCLUDED (no train observations):")
    for fn in quality["excluded_features"]:
        print(f"  - {fn}")
    print()
    print("FLAGGED (sparse, but has some train obs):")
    for fn in quality["flagged_features"]:
        r = audit[audit["feature_name"] == fn].iloc[0]
        corr_str = f"{r['corr_with_target_train']:.3f}" if not np.isnan(r["corr_with_target_train"]) else "n/a"
        print(f"  - {fn}: train_obs={r['train_obs_rate']:.2f}, corr={corr_str}")
    print()
    print("TOP 5 by |corr| with target (train, observed only):")
    for rec in quality["top5_by_abs_corr_with_target_train"]:
        print(f"  {rec['feature_name']}: {rec['corr_with_target_train']:.3f} (obs={rec['train_obs_rate']:.2f})")
    print()
    print(f"Artefatos: {OUT_CSV.name}, {OUT_JSON.name}, {OUT_MD.name}")


if __name__ == "__main__":
    main()
