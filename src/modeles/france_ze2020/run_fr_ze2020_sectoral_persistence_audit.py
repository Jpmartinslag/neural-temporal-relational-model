"""France ZE2020 sectoral persistence audit (HERALD_58 part A, DEC-083).

Implements the pre-registered specification exactly.  Every constant, rule and
threshold here is frozen in
``reports/canonical/HERALD_58_FR_ZE2020_SECTORAL_PERSISTENCE_AUDIT_SPEC.md``;
this module makes no methodological choice of its own.

The audit decides one thing: whether sectoral persistence at ZE x sector can be
promoted from CANDIDATE to the product's forecasting engine (DEC-081 Q1).  It
produces no model artifact, no relational input and no recommendation.

Run with ``python3.10`` -- the default ``python3`` on the reference machine has
no pandas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PANEL_PATH = ROOT / "data/processed/france_ze2020/fr_ze2020_sector_panel.csv"
DEFAULT_OUT_DIR = ROOT / "data/processed/france_ze2020"

TARGET = "sector_establishment_creations"
FEATURES = ["lag_1", "lag_2", "lag_3", "growth_1y_safe", "growth_2y_safe"]

# Frozen in HERALD_58 sections 3-6.  Reused from the ZE-total baseline
# convention in train_fr_ze2020_baselines.py rather than reinvented.
RIDGE_ALPHA = 1.0
RIDGE_MIN_TRAIN_YEARS = 4
N_FOLDS = 5
PANEL_FIRST_YEAR = 2012
PANEL_LAST_YEAR = 2025

# Official comparison window.  Derived from the training rules in section 4, not
# chosen: feature completeness starts at 2015, and four complete prior training
# years first hold at 2019.  Asserted against the data at run time.
OFFICIAL_FIRST_EVAL_YEAR = 2019
OFFICIAL_LAST_EVAL_YEAR = 2025
OFFICIAL_CELL_COUNT = 17_639

# Persistence-only supplement.  NEVER ranked against the models above.
SUPPLEMENT_FIRST_EVAL_YEAR = 2013
SUPPLEMENT_LAST_EVAL_YEAR = 2025

PERSISTENCE = "persistence"
RIDGE_AR = "ridge_ar"
SECTOR_MEAN = "sector_mean"
ZE_SECTOR_MEAN = "ze_sector_mean"
NATIONAL_SCALED = "national_scaled_persistence"

MODELS = [PERSISTENCE, RIDGE_AR, SECTOR_MEAN, ZE_SECTOR_MEAN, NATIONAL_SCALED]
# Section 8.1: eligibility is registered, not decided by outcome.
ELIGIBLE_FOR_ENGINE = (PERSISTENCE, RIDGE_AR)
NAIVE_CONTROLS = (SECTOR_MEAN, ZE_SECTOR_MEAN)

MIN_YEARLY_WINS = 6  # of 7 official evaluation years
SECTOR_REGRESSION_VETO = 0.10

CLAIM_STATUS = "sectoral_persistence_audit_engine_designation_only"


# --------------------------------------------------------------------------
# panel and features
# --------------------------------------------------------------------------


def load_panel(path: Path = PANEL_PATH) -> pd.DataFrame:
    panel = pd.read_csv(path, dtype={"ze2020": str})
    panel["year"] = panel["year"].astype(int)
    return panel.sort_values(["ze2020", "sector_code", "year"]).reset_index(drop=True)


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Derive lags and safe growths per ZE-sector series, from the target only."""
    out = panel.sort_values(["ze2020", "sector_code", "year"]).copy()
    grouped = out.groupby(["ze2020", "sector_code"])[TARGET]
    for k in (1, 2, 3):
        out[f"lag_{k}"] = grouped.shift(k)
    out["growth_1y_safe"] = (out["lag_1"] - out["lag_2"]) / out["lag_2"]
    out["growth_2y_safe"] = (out["lag_1"] - out["lag_3"]) / out["lag_3"]
    return out.reset_index(drop=True)


def completeness_mask(
    frame: pd.DataFrame, required: list[str] | None = None
) -> pd.Series:
    """Section 3: finite, not merely non-null.

    The single observed zero (5218/2016/JZ) makes a growth denominator +/-inf
    rather than NaN, so notna() would let two corrupted rows through.

    `required` defaults to the full feature set, which defines the **shared**
    population of the official window: every model there predicts exactly the
    same cells, as the integrity rules demand.  The persistence-only supplement
    passes the narrower set persistence actually consumes, so that it can cover
    the registered 2013-2025 window instead of being truncated by features no
    model in it uses.
    """
    columns = (FEATURES if required is None else list(required)) + [TARGET]
    values = frame[columns].to_numpy(dtype=float)
    return pd.Series(np.isfinite(values).all(axis=1), index=frame.index)


def assign_folds(zones: list[str]) -> dict[str, int]:
    """Section 6: deterministic, by position in the sorted zone list. No seed."""
    return {zone: index % N_FOLDS for index, zone in enumerate(sorted(zones))}


# --------------------------------------------------------------------------
# national ratio, fail-closed
# --------------------------------------------------------------------------


def national_totals(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.groupby(["sector_code", "year"])[TARGET].sum().rename("national_total").reset_index()


def national_ratio(totals: pd.DataFrame, sector: str, eval_year: int) -> float:
    """Section 5.2: r(s,t) = total(s,t-1) / total(s,t-2), reading nothing after t-1.

    Fails closed.  A zero, negative, missing or non-finite denominator aborts
    the audit; it may never yield an infinity, an imputation or a silent
    exclusion.
    """
    def lookup(year: int) -> float:
        rows = totals[(totals["sector_code"] == sector) & (totals["year"] == year)]
        assert len(rows) == 1, (
            f"national total for sector {sector} at {year} is not uniquely defined "
            f"({len(rows)} rows); aborting rather than guessing"
        )
        return float(rows["national_total"].iloc[0])

    numerator = lookup(eval_year - 1)
    denominator = lookup(eval_year - 2)
    assert np.isfinite(denominator) and denominator > 0, (
        f"national total for sector {sector} at {eval_year - 2} is "
        f"{denominator!r}; the ratio requires a finite, strictly positive "
        "denominator and the audit aborts rather than emitting an infinity"
    )
    ratio = numerator / denominator
    assert np.isfinite(ratio), (
        f"national ratio for sector {sector} at {eval_year} is {ratio!r}"
    )
    return ratio


# --------------------------------------------------------------------------
# per-year prediction
# --------------------------------------------------------------------------


def predict_year(
    featured: pd.DataFrame,
    totals: pd.DataFrame,
    eval_year: int,
    folds: dict[str, int],
    models: tuple[str, ...] = tuple(MODELS),
    required_features: list[str] | None = None,
) -> pd.DataFrame:
    """Predictions for one evaluation year, one row per eligible cell.

    Section 6, made concrete: `ridge_ar` and `sector_mean` use the remaining
    training-fold ZEs; `ze_sector_mean`, `persistence` and
    `national_scaled_persistence` use the test cell's causal history through
    t-1 and do not fit on folds.
    """
    complete = completeness_mask(featured, required_features)
    history = featured[featured["year"] < eval_year]
    test = featured[(featured["year"] == eval_year) & complete].copy()
    if test.empty:
        return pd.DataFrame()

    test["fold"] = test["ze2020"].map(folds)
    assert test["fold"].notna().all(), "a test zone has no fold assignment"

    complete_history = history[completeness_mask(history)]

    rows: list[pd.DataFrame] = []
    for fold in sorted(test["fold"].unique()):
        fold_test = test[test["fold"] == fold].copy()
        train_zones = {zone for zone, f in folds.items() if f != fold}
        assert not (set(fold_test["ze2020"]) & train_zones), "fold leakage: overlapping zones"

        block = fold_test[["ze2020", "sector_code", "year", TARGET, "fold"]].copy()
        block = block.rename(columns={TARGET: "y_true"})

        if PERSISTENCE in models:
            block[PERSISTENCE] = fold_test["lag_1"].to_numpy(dtype=float)

        if NATIONAL_SCALED in models:
            ratios = fold_test["sector_code"].map(
                lambda sector: national_ratio(totals, sector, eval_year)
            )
            block[NATIONAL_SCALED] = (
                fold_test["lag_1"].to_numpy(dtype=float) * ratios.to_numpy(dtype=float)
            )

        if ZE_SECTOR_MEAN in models:
            own = (
                history.groupby(["ze2020", "sector_code"])[TARGET]
                .mean()
                .rename(ZE_SECTOR_MEAN)
            )
            block = block.merge(own, on=["ze2020", "sector_code"], how="left")

        if SECTOR_MEAN in models:
            train_history = history[history["ze2020"].isin(train_zones)]
            sector_means = (
                train_history.groupby("sector_code")[TARGET].mean().rename(SECTOR_MEAN)
            )
            block = block.merge(sector_means, on="sector_code", how="left")

        if RIDGE_AR in models:
            train = complete_history[complete_history["ze2020"].isin(train_zones)]
            n_train_years = train["year"].nunique()
            assert n_train_years >= RIDGE_MIN_TRAIN_YEARS, (
                f"eval year {eval_year} fold {fold} has {n_train_years} complete "
                f"training years, below the registered minimum {RIDGE_MIN_TRAIN_YEARS}"
            )
            model = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("ridge", Ridge(alpha=RIDGE_ALPHA, fit_intercept=True)),
                ]
            )
            model.fit(
                train[FEATURES].to_numpy(dtype=float),
                train[TARGET].to_numpy(dtype=float),
            )
            # No clipping, no rounding: the ZE-total baseline convention.
            block[RIDGE_AR] = model.predict(fold_test[FEATURES].to_numpy(dtype=float))

        rows.append(block)

    out = pd.concat(rows, ignore_index=True)
    assert out[list(models)].notna().all().all(), (
        f"eval year {eval_year} produced a missing prediction; no imputation is permitted"
    )
    return out


def run_predictions(
    featured: pd.DataFrame,
    totals: pd.DataFrame,
    eval_years: list[int],
    folds: dict[str, int],
    models: tuple[str, ...] = tuple(MODELS),
    required_features: list[str] | None = None,
) -> pd.DataFrame:
    frames = [
        predict_year(featured, totals, year, folds, models, required_features)
        for year in eval_years
    ]
    frames = [frame for frame in frames if not frame.empty]
    assert frames, "no evaluation year produced predictions"
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denominator = np.abs(y_true).sum()
    if denominator == 0:
        return float("nan")
    return float(np.abs(y_true - y_pred).sum() / denominator)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.abs(y_true - y_pred).mean())


def metric_table(predictions: pd.DataFrame, models: tuple[str, ...]) -> dict[str, object]:
    y = predictions["y_true"].to_numpy(dtype=float)
    overall = {
        model: {
            "wmape": wmape(y, predictions[model].to_numpy(dtype=float)),
            "mae": mae(y, predictions[model].to_numpy(dtype=float)),
        }
        for model in models
    }

    by_year: dict[str, dict[str, float]] = {}
    for year, group in predictions.groupby("year"):
        yy = group["y_true"].to_numpy(dtype=float)
        by_year[str(int(year))] = {
            model: wmape(yy, group[model].to_numpy(dtype=float)) for model in models
        }

    by_sector: dict[str, dict[str, float]] = {}
    for sector, group in predictions.groupby("sector_code"):
        yy = group["y_true"].to_numpy(dtype=float)
        by_sector[str(sector)] = {
            model: wmape(yy, group[model].to_numpy(dtype=float)) for model in models
        }

    paired: dict[str, float] = {}
    for model in models:
        if model == PERSISTENCE:
            continue
        error_model = (predictions[model] - predictions["y_true"]).abs()
        error_persistence = (predictions[PERSISTENCE] - predictions["y_true"]).abs()
        paired[f"{model}_beats_persistence_cell_share"] = float(
            (error_model < error_persistence).mean()
        )

    return {
        "overall": overall,
        "wmape_by_year": by_year,
        "wmape_by_sector": by_sector,
        "paired_cell_win_rate_vs_persistence": paired,
    }


# --------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------


def _beats(challenger: float, reference: float) -> bool:
    """Section 8.2: strictly lower WMAPE. A tie is not a win."""
    return bool(challenger < reference)


def _yearly_wins(by_year: dict[str, dict[str, float]], challenger: str, reference: str) -> int:
    return sum(
        1 for year in by_year if _beats(by_year[year][challenger], by_year[year][reference])
    )


def sector_veto(by_sector: dict[str, dict[str, float]], candidate: str) -> dict[str, object]:
    """Section 8.5: a safety veto, never a promotional metric.

    It can only block a promotion clause 8.4 already granted on aggregate
    WMAPE; it can never create one.
    """
    offenders: dict[str, float] = {}
    for sector, values in by_sector.items():
        reference = values[PERSISTENCE]
        challenger = values[candidate]
        assert not (np.isnan(reference) or np.isnan(challenger)), (
            f"sector {sector} has a NaN WMAPE; the audit aborts rather than "
            "applying an uninterpretable veto"
        )
        if reference == 0:
            if challenger > 0:
                offenders[sector] = float("inf")
            continue
        regression = (challenger - reference) / reference
        if regression > SECTOR_REGRESSION_VETO:
            offenders[sector] = float(regression)
    return {"vetoed": bool(offenders), "offending_sectors": offenders}


def evaluate_gate(metrics: dict[str, object], n_eval_years: int) -> dict[str, object]:
    overall = metrics["overall"]
    by_year = metrics["wmape_by_year"]
    by_sector = metrics["wmape_by_sector"]

    qualification: dict[str, object] = {}
    for candidate in ELIGIBLE_FOR_ENGINE:
        entry: dict[str, object] = {}
        qualifies = True
        for control in NAIVE_CONTROLS:
            aggregate = _beats(overall[candidate]["wmape"], overall[control]["wmape"])
            wins = _yearly_wins(by_year, candidate, control)
            entry[control] = {
                "beats_aggregate": aggregate,
                "yearly_wins": wins,
                "yearly_wins_required": MIN_YEARLY_WINS,
                "passes": bool(aggregate and wins >= MIN_YEARLY_WINS),
            }
            qualifies = qualifies and aggregate and wins >= MIN_YEARLY_WINS
        entry["qualifies"] = bool(qualifies)
        qualification[candidate] = entry

    ridge_vs_persistence = {
        "beats_aggregate": _beats(overall[RIDGE_AR]["wmape"], overall[PERSISTENCE]["wmape"]),
        "yearly_wins": _yearly_wins(by_year, RIDGE_AR, PERSISTENCE),
        "yearly_wins_required": MIN_YEARLY_WINS,
    }
    veto = sector_veto(by_sector, RIDGE_AR)

    clause_1 = bool(
        qualification[RIDGE_AR]["qualifies"]
        and ridge_vs_persistence["beats_aggregate"]
        and ridge_vs_persistence["yearly_wins"] >= MIN_YEARLY_WINS
        and not veto["vetoed"]
    )
    clause_2 = bool(not clause_1 and qualification[PERSISTENCE]["qualifies"])

    if clause_1:
        verdict, engine = "ENGINE_DESIGNATED", RIDGE_AR
    elif clause_2:
        verdict, engine = "ENGINE_DESIGNATED", PERSISTENCE
    else:
        # Section 8.4 clause 3: the exhaustive complement of clauses 1 and 2.
        verdict, engine = "NO_ENGINE_DESIGNATED", None

    return {
        "n_eval_years": n_eval_years,
        "eligible_for_engine": list(ELIGIBLE_FOR_ENGINE),
        "never_eligible": [SECTOR_MEAN, ZE_SECTOR_MEAN, NATIONAL_SCALED],
        "naive_control_gate": qualification,
        "ridge_vs_persistence": ridge_vs_persistence,
        "ridge_sector_safety_veto": veto,
        "clause_1_ridge_designated": clause_1,
        "clause_2_persistence_designated": clause_2,
        "verdict": verdict,
        "engine": engine,
    }


# --------------------------------------------------------------------------
# integrity
# --------------------------------------------------------------------------


def check_target_mutation_invariance(
    panel: pd.DataFrame,
    eval_years: list[int],
    folds: dict[str, int],
    reference: pd.DataFrame,
) -> None:
    """Prove that no model reads the target at its own evaluation year.

    Truncating the panel at `t-1`, as the specification first phrased it, cannot
    be executed literally: the year-`t` rows would vanish and there would be
    nothing to predict.  The falsification implemented here is strictly
    stronger.  For each evaluation year `t` the panel is rebuilt with

      * every year after `t` removed, so no future information exists at all;
      * the target **at `t` itself** replaced by an arbitrary value.

    Features, national totals and folds are then recomputed from that mutated
    panel and year `t` is predicted again.  Only the prediction columns are
    compared -- `y_true` differs by construction.  If any model consulted the
    target at `t`, its prediction must move; identical predictions prove it did
    not.
    """
    for year in eval_years:
        mutated = panel[panel["year"] <= year].copy()
        target_rows = mutated["year"] == year
        assert target_rows.any(), f"no rows to mutate at {year}"
        mutated.loc[target_rows, TARGET] = (
            mutated.loc[target_rows, TARGET].to_numpy(dtype=float) * 7.0 + 1000.0
        )
        featured = build_features(mutated)
        totals = national_totals(mutated)
        again = predict_year(featured, totals, year, folds)

        keys = ["ze2020", "sector_code"]
        expected = reference[reference["year"] == year].sort_values(keys).reset_index(drop=True)
        again = again.sort_values(keys).reset_index(drop=True)
        assert list(again[keys[0]]) == list(expected[keys[0]]), (
            f"population changed under target mutation at {year}"
        )
        for model in MODELS:
            np.testing.assert_allclose(
                again[model].to_numpy(dtype=float),
                expected[model].to_numpy(dtype=float),
                rtol=0.0,
                atol=0.0,
                err_msg=(
                    f"{model} changed at {year} when the target at {year} was mutated: "
                    "it reads its own evaluation-year target"
                ),
            )


def assert_metrics_finite(metrics: dict[str, object]) -> None:
    """Blocking guard: a NaN or infinite metric invalidates the run.

    Section 9 requires every reported metric to be finite or an explicitly
    recorded NaN.  The gate must never be evaluated on a non-finite number,
    because comparisons against NaN silently return False and would be read as
    a lost comparison rather than a broken one.
    """
    def check(path: str, value: object) -> None:
        assert isinstance(value, (int, float)), f"{path} is not numeric: {value!r}"
        assert np.isfinite(float(value)), (
            f"{path} is {value!r}; the audit aborts rather than evaluating the gate "
            "on a non-finite metric"
        )

    for model, values in metrics["overall"].items():
        for name, value in values.items():
            check(f"overall.{model}.{name}", value)
    for year, values in metrics["wmape_by_year"].items():
        for model, value in values.items():
            check(f"wmape_by_year.{year}.{model}", value)
    for sector, values in metrics["wmape_by_sector"].items():
        for model, value in values.items():
            check(f"wmape_by_sector.{sector}.{model}", value)
    for name, value in metrics.get("paired_cell_win_rate_vs_persistence", {}).items():
        check(f"paired.{name}", value)


def integrity_report(
    predictions: pd.DataFrame, folds: dict[str, int], eval_years: list[int]
) -> dict[str, object]:
    duplicated = predictions.duplicated(["ze2020", "sector_code", "year"]).sum()
    assert duplicated == 0, f"{duplicated} duplicated ZE-sector-year rows"
    assert len(predictions) == OFFICIAL_CELL_COUNT, (
        f"official window holds {len(predictions)} rows, registered {OFFICIAL_CELL_COUNT}"
    )
    for model in MODELS:
        assert np.isfinite(predictions[model].to_numpy(dtype=float)).all(), (
            f"{model} produced a non-finite prediction"
        )
    negative = {model: int((predictions[model] < 0).sum()) for model in MODELS}
    negative_share = {
        model: float((predictions[model] < 0).mean()) for model in MODELS
    }
    negative_by_year = {
        str(int(year)): {
            model: {
                "count": int((group[model] < 0).sum()),
                "share": float((group[model] < 0).mean()),
            }
            for model in MODELS
        }
        for year, group in predictions.groupby("year")
    }
    return {
        "rows": int(len(predictions)),
        "registered_rows": OFFICIAL_CELL_COUNT,
        "duplicated_cells": int(duplicated),
        "eval_years": eval_years,
        "distinct_zones": int(predictions["ze2020"].nunique()),
        "distinct_sectors": int(predictions["sector_code"].nunique()),
        "negative_predictions": negative,
        "negative_prediction_share": negative_share,
        "negative_predictions_by_year": negative_by_year,
        "folds": N_FOLDS,
        "seeds_used": 0,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-path", type=Path, default=PANEL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--skip-truncation-check",
        action="store_true",
        help=(
            "skips the target-mutation invariance proof; diagnostic only, a real "
            "run must keep it enabled"
        ),
    )
    args = parser.parse_args()

    panel = load_panel(args.panel_path)
    featured = build_features(panel)
    totals = national_totals(panel)
    folds = assign_folds(sorted(panel["ze2020"].unique()))

    complete = completeness_mask(featured)
    first_complete_year = int(featured.loc[complete, "year"].min())
    assert first_complete_year == 2015, (
        f"feature completeness starts at {first_complete_year}, registered 2015"
    )

    official_years = list(range(OFFICIAL_FIRST_EVAL_YEAR, OFFICIAL_LAST_EVAL_YEAR + 1))
    predictions = run_predictions(featured, totals, official_years, folds)

    excluded = featured[
        (featured["year"].between(OFFICIAL_FIRST_EVAL_YEAR, OFFICIAL_LAST_EVAL_YEAR))
        & (~complete)
    ][["ze2020", "sector_code", "year"]]

    integrity = integrity_report(predictions, folds, official_years)
    integrity["excluded_cells"] = excluded.to_dict("records")
    integrity["excluded_cell_count"] = int(len(excluded))

    if not args.skip_truncation_check:
        check_target_mutation_invariance(panel, official_years, folds, predictions)
        integrity["target_mutation_invariance"] = "PASS"
    else:
        integrity["target_mutation_invariance"] = "SKIPPED"

    metrics = metric_table(predictions, tuple(MODELS))
    assert_metrics_finite(metrics)
    gate = evaluate_gate(metrics, len(official_years))

    # Persistence-only supplement.  NOT_COMPARABLE: no fitted model can be
    # evaluated over this window, so it never shares a ranking table.
    supplement_years = list(
        range(SUPPLEMENT_FIRST_EVAL_YEAR, SUPPLEMENT_LAST_EVAL_YEAR + 1)
    )
    # Persistence consumes lag_1 alone, so the supplement's eligibility requires
    # lag_1 and the target only.  Demanding the full feature set here would
    # silently truncate the registered 2013-2025 window to 2015-2025 on account
    # of features no model in this table uses.
    supplement = run_predictions(
        featured,
        totals,
        supplement_years,
        folds,
        models=(PERSISTENCE,),
        required_features=["lag_1"],
    )
    supplement_metrics = {
        "window": f"{SUPPLEMENT_FIRST_EVAL_YEAR}-{SUPPLEMENT_LAST_EVAL_YEAR}",
        "comparability": "NOT_COMPARABLE",
        "rows": int(len(supplement)),
        "wmape": wmape(
            supplement["y_true"].to_numpy(dtype=float),
            supplement[PERSISTENCE].to_numpy(dtype=float),
        ),
        "mae": mae(
            supplement["y_true"].to_numpy(dtype=float),
            supplement[PERSISTENCE].to_numpy(dtype=float),
        ),
        "wmape_by_year": {
            str(int(year)): wmape(
                group["y_true"].to_numpy(dtype=float),
                group[PERSISTENCE].to_numpy(dtype=float),
            )
            for year, group in supplement.groupby("year")
        },
        "note": (
            "Persistence over the full panel window. No fitted model can be evaluated "
            "here, so these numbers must never appear in the same ranking table as the "
            "official 2019-2025 comparison."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "fr_ze2020_sectoral_persistence_predictions_v1.csv"
    supplement_path = args.output_dir / "fr_ze2020_sectoral_persistence_supplement_v1.csv"
    manifest_path = args.output_dir / "fr_ze2020_sectoral_persistence_audit_v1.json"

    predictions.to_csv(predictions_path, index=False)
    supplement.to_csv(supplement_path, index=False)

    manifest = {
        "artifact": "fr_ze2020_sectoral_persistence_audit",
        "specification": "reports/canonical/HERALD_58_FR_ZE2020_SECTORAL_PERSISTENCE_AUDIT_SPEC.md",
        "decision": "DEC-083 (pre-registration); DEC-084 records this result",
        "claim_status": CLAIM_STATUS,
        "target": TARGET,
        "target_meaning": (
            "annual flow of newly created establishments; not stock growth, employment, "
            "output or survival"
        ),
        "official_window": f"{OFFICIAL_FIRST_EVAL_YEAR}-{OFFICIAL_LAST_EVAL_YEAR}",
        "models": MODELS,
        "integrity": integrity,
        "metrics": metrics,
        "gate": gate,
        "persistence_only_supplement": supplement_metrics,
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "input_sha256": sha256(args.panel_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {predictions_path} ({len(predictions)} rows)")
    print(f"Wrote {supplement_path} ({len(supplement)} rows, NOT_COMPARABLE)")
    print(f"Wrote {manifest_path}")
    print(f"Verdict: {gate['verdict']} | engine: {gate['engine']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
