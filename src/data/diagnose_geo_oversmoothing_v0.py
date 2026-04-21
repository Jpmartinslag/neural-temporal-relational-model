import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_PATH = ROOT / "reports" / "region84_graph_predictions_v0.csv"
EDGES_PATH = ROOT / "data" / "processed" / "graph_edges_ze2020_core_v0.csv"
METRICS_OUT = ROOT / "reports" / "geo_oversmoothing_diagnostic_v0.json"
REPORT_OUT = ROOT / "reports" / "GEO_OVERSMOOTHING_DIAGNOSTIC_V0.md"


def load_region_frame():
    df = pd.read_csv(PREDICTIONS_PATH)
    edges = pd.read_csv(EDGES_PATH)
    node_ids = set(df["ze2020"].tolist())
    sub_edges = edges[
        edges["source_ze2020"].isin(node_ids) & edges["target_ze2020"].isin(node_ids)
    ].copy()
    degree = pd.concat([sub_edges["source_ze2020"], sub_edges["target_ze2020"]]).value_counts()
    df["regional_degree"] = df["ze2020"].map(degree).fillna(0).astype(int)
    df["improved"] = df["geo_minus_ridge_error"] < 0
    df["worsened"] = df["geo_minus_ridge_error"] > 0
    return df


def add_bins(df):
    degree_bins = [-0.1, 2, 5, 8, np.inf]
    degree_labels = ["0-2", "3-5", "6-8", "9+"]
    df["degree_band"] = pd.cut(df["regional_degree"], bins=degree_bins, labels=degree_labels)

    size_quantiles = df["y_true"].quantile([0.0, 0.33, 0.66, 1.0]).to_numpy()
    size_quantiles[0] -= 1e-9
    size_quantiles[-1] += 1e-9
    size_labels = ["small", "medium", "large"]
    df["size_band"] = pd.cut(df["y_true"], bins=size_quantiles, labels=size_labels, duplicates="drop")
    return df


def summarize_group(df, group_col):
    out = (
        df.groupby(group_col, dropna=False)
        .agg(
            zones=("ze2020", "count"),
            avg_delta=("geo_minus_ridge_error", "mean"),
            median_delta=("geo_minus_ridge_error", "median"),
            worsened_zones=("worsened", "sum"),
            improved_zones=("improved", "sum"),
            avg_target=("y_true", "mean"),
            avg_degree=("regional_degree", "mean"),
            ridge_mean_error=("ridge_abs_error", "mean"),
            geo_mean_error=("geo_abs_error", "mean"),
        )
        .reset_index()
    )
    return out


def summarize_cross(df):
    out = (
        df.groupby(["degree_band", "size_band"], dropna=False)
        .agg(
            zones=("ze2020", "count"),
            avg_delta=("geo_minus_ridge_error", "mean"),
            worsened_zones=("worsened", "sum"),
            improved_zones=("improved", "sum"),
            ridge_mean_error=("ridge_abs_error", "mean"),
            geo_mean_error=("geo_abs_error", "mean"),
        )
        .reset_index()
    )
    return out


def build_payload(df):
    degree_summary = summarize_group(df, "degree_band")
    size_summary = summarize_group(df, "size_band")
    cross_summary = summarize_cross(df)

    payload = {
        "source_predictions": str(PREDICTIONS_PATH.relative_to(ROOT)),
        "zones": int(len(df)),
        "improved_zones": int(df["improved"].sum()),
        "worsened_zones": int(df["worsened"].sum()),
        "mean_delta": float(df["geo_minus_ridge_error"].mean()),
        "median_delta": float(df["geo_minus_ridge_error"].median()),
        "degree_delta_correlation": float(df["regional_degree"].corr(df["geo_minus_ridge_error"])),
        "target_delta_correlation": float(df["y_true"].corr(df["geo_minus_ridge_error"])),
        "top_improvements": df.sort_values("geo_minus_ridge_error")
        .head(10)[["ze2020", "libze2020", "regional_degree", "y_true", "geo_minus_ridge_error"]]
        .to_dict(orient="records"),
        "top_degradations": df.sort_values("geo_minus_ridge_error", ascending=False)
        .head(10)[["ze2020", "libze2020", "regional_degree", "y_true", "geo_minus_ridge_error"]]
        .to_dict(orient="records"),
        "degree_summary": degree_summary.to_dict(orient="records"),
        "size_summary": size_summary.to_dict(orient="records"),
        "degree_size_summary": cross_summary.to_dict(orient="records"),
    }
    return payload


def write_report(payload):
    lines = [
        "# Geo Oversmoothing Diagnostic v0",
        "",
        "Date : 2026-04-21",
        "",
        "## Objectif",
        "",
        "Transformer l'intuition d'oversmoothing en diagnostic tabulaire reproductible sur la région 84 pour l'année cible 2023.",
        "",
        "## Résumé global",
        "",
        f"- Zones : `{payload['zones']}`",
        f"- Improved zones : `{payload['improved_zones']}`",
        f"- Worsened zones : `{payload['worsened_zones']}`",
        f"- Mean delta (`geo_abs_error - ridge_abs_error`) : `{payload['mean_delta']:.3f}`",
        f"- Median delta : `{payload['median_delta']:.3f}`",
        f"- Corr(degree, delta) : `{payload['degree_delta_correlation']:.3f}`",
        f"- Corr(target, delta) : `{payload['target_delta_correlation']:.3f}`",
        "",
        "## Par bande de degré",
        "",
        "| degree_band | zones | avg_delta | median_delta | worsened | improved | avg_target | avg_degree |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["degree_summary"]:
        lines.append(
            f"| {row['degree_band']} | {int(row['zones'])} | {row['avg_delta']:.3f} | {row['median_delta']:.3f} | {int(row['worsened_zones'])} | {int(row['improved_zones'])} | {row['avg_target']:.1f} | {row['avg_degree']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Par bande de taille",
            "",
            "| size_band | zones | avg_delta | median_delta | worsened | improved | avg_target | avg_degree |",
            "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["size_summary"]:
        lines.append(
            f"| {row['size_band']} | {int(row['zones'])} | {row['avg_delta']:.3f} | {row['median_delta']:.3f} | {int(row['worsened_zones'])} | {int(row['improved_zones'])} | {row['avg_target']:.1f} | {row['avg_degree']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Croisement degré × taille",
            "",
            "| degree_band | size_band | zones | avg_delta | worsened | improved |",
            "| :--- | :--- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["degree_size_summary"]:
        lines.append(
            f"| {row['degree_band']} | {row['size_band']} | {int(row['zones'])} | {row['avg_delta']:.3f} | {int(row['worsened_zones'])} | {int(row['improved_zones'])} |"
        )

    lines.extend(
        [
            "",
            "## Plus fortes améliorations",
            "",
            "| ze2020 | libze2020 | degree | y_true | delta |",
            "| ---: | :--- | ---: | ---: | ---: |",
        ]
    )
    for row in payload["top_improvements"]:
        lines.append(
            f"| {row['ze2020']} | {row['libze2020']} | {row['regional_degree']} | {row['y_true']:.1f} | {row['geo_minus_ridge_error']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Plus fortes dégradations",
            "",
            "| ze2020 | libze2020 | degree | y_true | delta |",
            "| ---: | :--- | ---: | ---: | ---: |",
        ]
    )
    for row in payload["top_degradations"]:
        lines.append(
            f"| {row['ze2020']} | {row['libze2020']} | {row['regional_degree']} | {row['y_true']:.1f} | {row['geo_minus_ridge_error']:.3f} |"
        )

    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    df = load_region_frame()
    df = add_bins(df)
    payload = build_payload(df)
    METRICS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Saved metrics to {METRICS_OUT}")
    print(f"Saved report to {REPORT_OUT}")


if __name__ == "__main__":
    main()
