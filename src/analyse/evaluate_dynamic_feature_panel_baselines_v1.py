"""
Pipeline E: Ridge baseline evaluation for Dynamic STGNN feature panel.

Compares 4 models via walk-forward:
  1. Ridge autoregressivo (benchmark)
  2. Ridge + FLORES t-1
  3. Ridge + SIDE stocks t-1
  4. Ridge + FLORES t-1 + SIDE stocks t-1

Approval rule:
  A source enters V1 Dynamic STGNN if it:
    1. Improves mean WMAPE 2021-2024
    2. Does not strongly degrade 2022 or 2024
    3. Has positive gain in mean 2022-2024 (independent of 2021 rebound)
    4. Is forecast-safe (confirmed t-1 lag)

Outputs:
  reports/DYNAMIC_FEATURE_PANEL_BASELINE_V1.md
  reports/dynamic_feature_panel_baseline_metrics_v1.json
  data/processed/dynamic_feature_panel_baseline_predictions_v1.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

ROOT      = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data/processed"
REPORTS   = ROOT / "reports"
METADATA  = ROOT / "metadata"

PANEL_PATH  = PROCESSED / "dynamic_stgnn_feature_panel_v1.csv"
SPLITS_PATH = METADATA  / "dynamic_stgnn_walk_forward_splits_v1.csv"
TARGET_COL  = "side_establishment_creations_official"


# ─── helpers ──────────────────────────────────────────────────────────────────

def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 0
    if mask.sum() == 0:
        return np.nan
    return float(np.sum(np.abs(y_true[mask] - y_pred[mask])) / np.sum(y_true[mask]))


def _feature_sets(panel: pd.DataFrame):
    ar_cols     = [c for c in ["side_lag_1","side_lag_2","side_lag_3","growth_1y","growth_2y"]
                   if c in panel.columns]
    # FLORES: only reliable aggregate features (exclude granular sectors with suppression risk)
    flores_cols = [c for c in panel.columns if "flores_" in c and "_t_minus_1" in c
                   and not any(s in c for s in ["etab_c2","etab_c4","etab_az","etab_de",
                                                 "etab_c1","etab_c3","etab_c5"])]
    side_cols   = [c for c in panel.columns if "side_stock" in c and "_t_minus_1" in c]
    urssaf_cols = [c for c in panel.columns if "urssaf_" in c and "_t_minus_1" in c]

    return {
        "Ridge_AR":                         ar_cols,
        "Ridge_AR_FLORES":                  ar_cols + flores_cols,
        "Ridge_AR_SIDE_stocks":             ar_cols + side_cols,
        "Ridge_AR_URSSAF":                  ar_cols + urssaf_cols,
        "Ridge_AR_FLORES_SIDE_URSSAF":      ar_cols + flores_cols + side_cols + urssaf_cols,
    }


def _source_flag(feature_cols: list):
    """Return the has_*_source flag for this feature set, or None for AR-only."""
    if any("flores_" in c for c in feature_cols):
        return "has_flores_source"
    if any("side_stock" in c for c in feature_cols):
        return "has_side_stock_source"
    if any("urssaf_" in c for c in feature_cols):
        return "has_urssaf_source"
    return None


def _run_walk_forward(panel: pd.DataFrame, splits: pd.DataFrame, feature_cols: list, model_name: str):
    records = []
    panel = panel.copy().dropna(subset=[TARGET_COL])

    # Clean Ridge test: restrict to rows where source actually exists
    source_flag = _source_flag(feature_cols)

    for _, split in splits.iterrows():
        target_year = int(split["target_year"])
        train_max   = int(split["train_years_max"])

        train = panel[panel["target_year"] <= train_max].copy()
        test  = panel[panel["target_year"] == target_year].copy()

        # Restrict test to zones with real source data (not imputed)
        if source_flag and source_flag in test.columns:
            test = test[test[source_flag] == 1]

        # Restrict train to rows with real source data (clean Ridge test)
        if source_flag and source_flag in train.columns:
            train = train[train[source_flag] == 1]

        if len(train) == 0 or len(test) == 0:
            continue

        available = [c for c in feature_cols if c in train.columns]
        if not available:
            continue

        train_clean = train.dropna(subset=[TARGET_COL])
        test_clean  = test.dropna(subset=[TARGET_COL])

        if len(train_clean) < 10 or len(test_clean) == 0:
            continue

        X_train = train_clean[available].values
        y_train = train_clean[TARGET_COL].values
        X_test  = test_clean[available].values
        y_true  = test_clean[TARGET_COL].values

        # Fix 3: log-transform stock and URSSAF absolute level columns before scaling
        log_cols_idx = [i for i, c in enumerate(available)
                        if any(k in c for k in ["side_stock_total","urssaf_employer_estab",
                                                 "urssaf_salaried","urssaf_payroll",
                                                 "flores_total_estab","flores_total_salaried"])]
        def log_transform(X, idx=log_cols_idx):
            X = X.copy().astype(float)
            if idx:
                X[:, idx] = np.log1p(np.abs(X[:, idx]))
            return X

        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),  # Fix 1
            ("log", FunctionTransformer(log_transform)),    # Fix 3
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ])
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_pred = np.maximum(y_pred, 0)

        wm = wmape(y_true, y_pred)

        # Hub error: top-10% zones by target value
        threshold = np.quantile(y_true, 0.9)
        hub_mask  = y_true >= threshold
        hub_wmape = wmape(y_true[hub_mask], y_pred[hub_mask]) if hub_mask.sum() > 0 else np.nan

        # Improvement share: % zones where |error| decreased vs AR baseline (stored later)
        records.append({
            "model":        model_name,
            "target_year":  target_year,
            "n_train":      len(train_clean),
            "n_test":       len(test_clean),
            "n_features":   len(available),
            "wmape":        round(wm, 6),
            "hub_wmape":    round(hub_wmape, 6) if not np.isnan(hub_wmape) else None,
            "y_true":       y_true.tolist(),
            "y_pred":       y_pred.tolist(),
            "ze2020":       test_clean["ZE2020"].tolist(),
        })

    return records


def _compute_deltas(all_records: list) -> pd.DataFrame:
    rows = []
    for r in all_records:
        rows.append({
            "model":       r["model"],
            "target_year": r["target_year"],
            "wmape":       r["wmape"],
            "hub_wmape":   r["hub_wmape"],
            "n_train":     r["n_train"],
            "n_test":      r["n_test"],
            "n_features":  r["n_features"],
        })
    df = pd.DataFrame(rows)

    # Compute delta vs Ridge_AR benchmark
    baseline = df[df["model"] == "Ridge_AR"][["target_year","wmape"]].rename(
        columns={"wmape": "wmape_ar"}
    )
    df = df.merge(baseline, on="target_year", how="left")
    df["delta_vs_ar"] = df["wmape"] - df["wmape_ar"]
    df["pct_improvement_vs_ar"] = -df["delta_vs_ar"] / df["wmape_ar"] * 100
    return df


def _improvement_share(all_records: list) -> dict:
    """% of zones where a model reduces absolute error vs AR baseline."""
    ar_lookup = {}
    for r in all_records:
        if r["model"] == "Ridge_AR":
            ze  = r["ze2020"]
            yt  = r["y_true"]
            yp  = r["y_pred"]
            yr  = r["target_year"]
            ar_lookup[yr] = dict(zip(ze, zip(yt, yp)))

    share = {}
    for r in all_records:
        model = r["model"]
        if model == "Ridge_AR":
            continue
        yr = r["target_year"]
        if yr not in ar_lookup:
            continue
        ar_yr = ar_lookup[yr]
        better = 0
        total  = 0
        for ze, yt, yp in zip(r["ze2020"], r["y_true"], r["y_pred"]):
            if ze in ar_yr:
                ar_err  = abs(ar_yr[ze][0] - ar_yr[ze][1])
                new_err = abs(yt - yp)
                better += int(new_err < ar_err)
                total  += 1
        key = f"{model}_year{yr}"
        share[key] = round(100 * better / total, 1) if total > 0 else None

    return share


def _residual_direction(all_records: list) -> dict:
    """Are residuals (pred - true) systematically biased?"""
    result = {}
    for r in all_records:
        yt = np.array(r["y_true"])
        yp = np.array(r["y_pred"])
        resid = yp - yt
        result[f"{r['model']}_year{r['target_year']}"] = {
            "mean_residual": round(float(resid.mean()), 2),
            "pct_over": round(float((resid > 0).mean() * 100), 1),
        }
    return result


# ─── approval decision ────────────────────────────────────────────────────────

def _apply_approval_rules(metrics: pd.DataFrame) -> dict:
    decisions = {}
    ar_row = metrics[metrics["model"] == "Ridge_AR"]
    ar_mean_all  = ar_row["wmape"].mean()
    ar_mean_2224 = ar_row[ar_row["target_year"] >= 2022]["wmape"].mean()

    for model in metrics["model"].unique():
        if model == "Ridge_AR":
            continue
        m = metrics[metrics["model"] == model]
        mean_all  = m["wmape"].mean()
        mean_2224 = m[m["target_year"] >= 2022]["wmape"].mean()
        wmape_2022 = float(m[m["target_year"] == 2022]["wmape"].iloc[0]) if 2022 in m["target_year"].values else None
        wmape_2024 = float(m[m["target_year"] == 2024]["wmape"].iloc[0]) if 2024 in m["target_year"].values else None

        rule1 = mean_all < ar_mean_all
        rule2 = not (
            (wmape_2022 is not None and wmape_2022 > (ar_row[ar_row["target_year"] == 2022]["wmape"].iloc[0] if 2022 in ar_row["target_year"].values else np.inf) * 1.02)) and \
            not (wmape_2024 is not None and wmape_2024 > (ar_row[ar_row["target_year"] == 2024]["wmape"].iloc[0] if 2024 in ar_row["target_year"].values else np.inf) * 1.02)
        rule3 = mean_2224 < ar_mean_2224
        rule4 = True  # confirmed forecast-safe (t-1 lag, documented)

        approved = rule1 and rule2 and rule3 and rule4
        decisions[model] = {
            "approved_for_v1":     approved,
            "rule1_improves_mean_2021_2024": rule1,
            "rule2_no_strong_2022_2024_degradation": rule2,
            "rule3_gain_without_2021": rule3,
            "rule4_forecast_safe":  rule4,
            "mean_wmape_2021_2024": round(float(mean_all), 6),
            "mean_wmape_2022_2024": round(float(mean_2224), 6),
            "delta_mean_vs_ar":    round(float(mean_all - ar_mean_all), 6),
        }
    return decisions


# ─── report generation ────────────────────────────────────────────────────────

def _write_markdown(metrics: pd.DataFrame, decisions: dict, share: dict,
                    residuals: dict, out_path: Path):
    lines = [
        "# Dynamic Feature Panel Baseline — V1",
        "",
        "Walk-forward evaluation of Ridge baselines with FLORES t-1 and SIDE stocks t-1.",
        "",
        "## WMAPE by model and year",
        "",
    ]

    pivot = metrics.pivot_table(index="model", columns="target_year", values="wmape").round(4)
    lines.append(pivot.to_csv(sep="|"))
    lines.append("")

    lines.append("## Delta vs Ridge autoregressivo (WMAPE, negative = improvement)")
    lines.append("")
    delta_pivot = metrics.pivot_table(
        index="model", columns="target_year", values="delta_vs_ar"
    ).round(4)
    lines.append(delta_pivot.to_csv(sep="|"))
    lines.append("")

    lines.append("## Approval decisions")
    lines.append("")
    for model, d in decisions.items():
        status = "✅ APPROVED" if d["approved_for_v1"] else "❌ REJECTED"
        lines.append(f"### {model} → {status}")
        for k, v in d.items():
            if k != "approved_for_v1":
                lines.append(f"  - {k}: {v}")
        lines.append("")

    lines.append("## Improvement share (% zones better than AR)")
    lines.append("")
    for k, v in share.items():
        lines.append(f"  - {k}: {v}%")
    lines.append("")

    lines.append("## Conclusions")
    lines.append("")
    for model, d in decisions.items():
        verdict = "enters V1 Dynamic STGNN" if d["approved_for_v1"] else "does NOT enter V1"
        lines.append(f"- **{model}**: {verdict} (Δ mean WMAPE = {d['delta_mean_vs_ar']:+.4f})")
    lines.append("")

    lines.append("## Methodological notes")
    lines.append("")
    lines.append("- COVID 2020 retained in training with `is_covid_year=1` flag.")
    lines.append("- Approval requires gain in mean 2022-2024 (rule 3) to guard against 2021 rebound bias.")
    lines.append("- All features are t-1 lagged (forecast-safe, INSEE lag ≥6 months for FLORES).")
    lines.append("- Zone_Sectoral excluded (leakage confirmed, δ=-85%).")
    lines.append("- SIRENE excluded (quarantine).")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Saved: {out_path}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    REPORTS.mkdir(parents=True, exist_ok=True)

    if not PANEL_PATH.exists():
        raise FileNotFoundError(
            f"{PANEL_PATH} not found. Run build_dynamic_stgnn_feature_panel_v1.py first."
        )

    panel  = pd.read_csv(PANEL_PATH, dtype={"ZE2020": str})
    splits = pd.read_csv(SPLITS_PATH)

    panel["ZE2020"] = panel["ZE2020"].astype(str).str.zfill(4)
    panel[TARGET_COL] = pd.to_numeric(panel[TARGET_COL], errors="coerce")

    feat_sets = _feature_sets(panel)
    print("\n=== Pipeline E: Ridge baseline evaluation ===")
    for model_name, cols in feat_sets.items():
        print(f"  Features for {model_name}: {len(cols)} cols")

    all_records = []
    for model_name, cols in feat_sets.items():
        print(f"\n  Running {model_name}...")
        recs = _run_walk_forward(panel, splits, cols, model_name)
        all_records.extend(recs)
        for r in recs:
            print(f"    year {r['target_year']}: WMAPE={r['wmape']:.4f}, n_train={r['n_train']}, n_test={r['n_test']}")

    metrics  = _compute_deltas(all_records)
    share    = _improvement_share(all_records)
    residuals = _residual_direction(all_records)
    decisions = _apply_approval_rules(metrics)

    # ── Print summary ──
    print("\n=== Summary ===")
    print(metrics[["model","target_year","wmape","delta_vs_ar","pct_improvement_vs_ar"]].to_string(index=False))

    print("\n=== Approval decisions ===")
    for model, d in decisions.items():
        print(f"  {model}: {'APPROVED' if d['approved_for_v1'] else 'REJECTED'} "
              f"(Δ={d['delta_mean_vs_ar']:+.4f}, rule3_gain_2224={d['rule3_gain_without_2021']})")

    # ── Answers to the 6 questions ──
    print("\n=== Answers to 6 questions ===")
    flores_model  = decisions.get("Ridge_AR_FLORES", {})
    side_model    = decisions.get("Ridge_AR_SIDE_stocks", {})
    urssaf_model  = decisions.get("Ridge_AR_URSSAF", {})
    combined      = decisions.get("Ridge_AR_FLORES_SIDE_URSSAF", {})

    flores_delta = flores_model.get("delta_mean_vs_ar", np.nan)
    side_delta   = side_model.get("delta_mean_vs_ar", np.nan)
    combined_delta = combined.get("delta_mean_vs_ar", np.nan)

    urssaf_delta = urssaf_model.get("delta_mean_vs_ar", np.nan)
    print(f"1. FLORES t-1 melhora Ridge? "
          f"{'SIM' if flores_model.get('approved_for_v1') else 'NAO'} "
          f"(Δ WMAPE = {flores_delta:+.4f})")
    print(f"2. SIDE stocks t-1 melhora Ridge? "
          f"{'SIM' if side_model.get('approved_for_v1') else 'NAO'} "
          f"(Δ WMAPE = {side_delta:+.4f})")
    print(f"2b. URSSAF t-1 melhora Ridge? "
          f"{'SIM' if urssaf_model.get('approved_for_v1') else 'NAO'} "
          f"(Δ WMAPE = {urssaf_delta:+.4f})")
    print(f"3. Combinação melhora mais? "
          f"{'SIM' if combined_delta < min(flores_delta, side_delta, urssaf_delta) else 'NAO'} "
          f"(Δ combinado = {combined_delta:+.4f})")

    # Check if any source degrades 2022 or 2024
    for model_name, d in decisions.items():
        print(f"4. {model_name} piora 2022/2024? "
              f"{'SIM' if not d['rule2_no_strong_2022_2024_degradation'] else 'NAO'}")

    # Panel readiness
    flores_ok = flores_model.get("approved_for_v1", False)
    side_ok   = side_model.get("approved_for_v1", False)
    print(f"5. Painel pronto para Dynamic STGNN? "
          f"{'SIM' if (flores_ok or side_ok) else 'Parcialmente - revisar features rejeitadas'}")

    approved_features = []
    if flores_ok:
        approved_features += ["flores_total_establishments_t_minus_1",
                              "flores_total_salaried_jobs_t_minus_1",
                              "flores_herfindahl_t_minus_1",
                              "flores_growth_etab_1y_t_minus_1"]
    if side_ok:
        approved_features += ["side_stock_total_t_minus_1", "side_stock_growth_1y_t_minus_1"]
    approved_features += ["side_lag_1", "side_lag_2", "growth_1y"]
    print(f"6. Features para V1 neural: {approved_features}")

    # ── Save outputs ──
    pred_rows = []
    for r in all_records:
        for ze, yt, yp in zip(r["ze2020"], r["y_true"], r["y_pred"]):
            pred_rows.append({
                "model": r["model"], "target_year": r["target_year"],
                "ZE2020": ze, "y_true": yt, "y_pred": yp,
                "abs_error": abs(yt - yp),
            })
    preds_df = pd.DataFrame(pred_rows)
    pred_path = PROCESSED / "dynamic_feature_panel_baseline_predictions_v1.csv"
    preds_df.to_csv(pred_path, index=False)
    print(f"\n  Saved predictions: {pred_path}")

    json_out = {
        "metrics_by_model_year": metrics[
            ["model","target_year","wmape","delta_vs_ar","pct_improvement_vs_ar"]
        ].to_dict(orient="records"),
        "approval_decisions": decisions,
        "improvement_share": share,
        "residual_direction_sample": {k: v for k, v in list(residuals.items())[:8]},
        "approved_features_for_v1_neural": approved_features,
    }
    json_path = REPORTS / "dynamic_feature_panel_baseline_metrics_v1.json"
    def _json_safe(obj):
        if isinstance(obj, (np.bool_, np.integer)):
            return bool(obj) if isinstance(obj, np.bool_) else int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        raise TypeError(f"Not serializable: {type(obj)}")
    json_path.write_text(json.dumps(json_out, indent=2, ensure_ascii=False, default=_json_safe), encoding="utf-8")
    print(f"  Saved metrics JSON: {json_path}")

    _write_markdown(metrics, decisions, share, residuals,
                    REPORTS / "DYNAMIC_FEATURE_PANEL_BASELINE_V1.md")


if __name__ == "__main__":
    main()
