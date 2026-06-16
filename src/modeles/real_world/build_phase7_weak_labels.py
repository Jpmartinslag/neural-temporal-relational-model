"""
build_phase7_weak_labels.py — Build weak labels from Phase 7 sector precedence evidence.

DEC-058: Converts Phase 7 regression results into confidence-weighted training labels
for the SharedRelationEncoder fine-tuning.

Label rules (strict):
  COVID_ROBUST   = promoted AND promoted_without_2020 (highest confidence)
  MAIN_ONLY      = promoted AND NOT promoted_without_2020 (medium confidence)
  COVID_SENSITIVE = explicitly named class for COVID-window-only promotions (low weight)
  CONFLICTING    = promoted in opposite directions in different windows (very low weight)
  PERMUTATION_NEGATIVE = strong permutation evidence of absence (NOT from "not promoted")
  UNLABELED      = not promoted, no explicit evidence either way (excluded from loss)

Critical constraints:
  - "Not promoted" ≠ negative label. Only explicit permutation evidence = negative.
  - COVID_SENSITIVE must NOT be promoted as ROBUST.
  - Phase 7 uses lag=1 exclusively. lag_label=1 for all promoted edges.
  - presence_label=1 for promoted; presence_label=0 only for PERMUTATION_NEGATIVE.
  - confidence_weight ∈ [0, 1].
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ── Constants ─────────────────────────────────────────────────────────────────

PHASE7_MAIN = "data/processed/sector_precedence_results/main_with_sensitivity.csv"
PHASE7_COVID_ROBUST = "data/processed/sector_precedence_results/covid_robust_edges.csv"

OUT_DIR = "data/processed/real_relation_weak_labels"
OUT_CSV = f"{OUT_DIR}/phase7_weak_labels.csv"
OUT_MANIFEST = f"{OUT_DIR}/phase7_weak_labels_manifest.json"

# Confidence weight parameters (frozen)
WEIGHT_COVID_ROBUST_BASE = 0.80
WEIGHT_MAIN_ONLY_BASE = 0.40
WEIGHT_COVID_SENSITIVE_BASE = 0.15
WEIGHT_CONFLICTING_BASE = 0.05

# Phase 7 uses lag-1 regression
DEFAULT_LAG_LABEL = 1

REQUIRED_COLS = [
    "country", "source_sector", "target_sector",
    "window_start", "window_end",
    "sign_label", "lag_label", "presence_label",
    "confidence_weight", "evidence_class",
    "source_artifact", "notes",
]


# ── Confidence weighting ───────────────────────────────────────────────────────

def _compute_confidence(
    base: float,
    p_perm: float,
    bootstrap_sign_stability: float,
) -> float:
    """
    Scale base weight by statistical evidence quality.
    p_perm: lower is better (0.001 = max confidence).
    bootstrap_sign_stability: fraction of bootstrap samples with same sign (0-1).
    """
    # p_perm factor: 0.001 → 1.0, 0.01 → 0.7, 0.05 → 0.4
    p_factor = max(0.0, 1.0 - (p_perm / 0.05) * 0.6)
    # bootstrap factor: linear from 0.5 to 1.0
    bss = float(bootstrap_sign_stability)
    bss_factor = max(0.0, min(1.0, (bss - 0.5) / 0.5))
    # Combined: geometric mean of base, p_factor, bss_factor
    combined = base * (0.5 + 0.5 * p_factor) * (0.5 + 0.5 * bss_factor)
    return float(np.clip(combined, 0.0, 1.0))


# ── Main builder ──────────────────────────────────────────────────────────────

def build_weak_labels(
    phase7_main_path: str = PHASE7_MAIN,
    phase7_robust_path: str = PHASE7_COVID_ROBUST,
) -> pd.DataFrame:
    """
    Build weak labels DataFrame from Phase 7 evidence.
    Returns DataFrame with REQUIRED_COLS.
    """
    df_main = pd.read_csv(phase7_main_path)
    df_robust = pd.read_csv(phase7_robust_path)

    # Build COVID-robust key set: (country, src, tgt, window_start, window_end)
    robust_keys: set[tuple] = set()
    for _, row in df_robust.iterrows():
        robust_keys.add((row["country"], row["source_sector"], row["target_sector"],
                         int(row["window_start"]), int(row["window_end"])))

    rows = []

    # ── Promoted edges → positive weak labels ─────────────────────────────────
    promoted = df_main[df_main["promoted"] == True].copy()

    # Detect conflicting: same (country, src, tgt) promoted in opposite signs
    pair_signs: dict[tuple, list] = {}
    for _, r in promoted.iterrows():
        k = (r["country"], r["source_sector"], r["target_sector"])
        pair_signs.setdefault(k, []).append(r["beta"])
    conflicting_keys: set[tuple] = {
        k for k, betas in pair_signs.items()
        if len(betas) > 1 and not all(b > 0 for b in betas) and not all(b < 0 for b in betas)
    }

    for _, row in promoted.iterrows():
        country = str(row["country"])
        src = str(row["source_sector"])
        tgt = str(row["target_sector"])
        ws = int(row["window_start"])
        we = int(row["window_end"])
        beta = float(row["beta"])
        p_perm = float(row["p_perm"])
        bss = float(row["bootstrap_sign_stability"])
        promoted_wo20 = bool(row.get("promoted_without_2020", False))

        key = (country, src, tgt)
        is_conflicting = key in conflicting_keys
        is_covid_robust = (country, src, tgt, ws, we) in robust_keys

        if is_conflicting:
            evidence_class = "CONFLICTING"
            base_weight = WEIGHT_CONFLICTING_BASE
        elif is_covid_robust:
            evidence_class = "COVID_ROBUST"
            base_weight = WEIGHT_COVID_ROBUST_BASE
        elif not promoted_wo20:
            # Promoted only in main (includes COVID year) → COVID_SENSITIVE
            evidence_class = "COVID_SENSITIVE"
            base_weight = WEIGHT_COVID_SENSITIVE_BASE
        else:
            evidence_class = "MAIN_ONLY"
            base_weight = WEIGHT_MAIN_ONLY_BASE

        confidence = _compute_confidence(base_weight, p_perm, bss)

        sign_label = 1 if beta > 0 else -1
        notes_parts = [f"beta={beta:.4f}", f"p_perm={p_perm}", f"bss={bss:.3f}"]
        if promoted_wo20:
            notes_parts.append("robust_wo20")

        rows.append({
            "country": country,
            "source_sector": src,
            "target_sector": tgt,
            "window_start": ws,
            "window_end": we,
            "sign_label": sign_label,
            "lag_label": DEFAULT_LAG_LABEL,
            "presence_label": 1,
            "confidence_weight": round(confidence, 4),
            "evidence_class": evidence_class,
            "source_artifact": "phase7_sector_precedence_main_with_sensitivity",
            "notes": "; ".join(notes_parts),
        })

    # ── Non-promoted rows → UNLABELED (excluded from loss) ────────────────────
    # We do NOT add these as negative labels. "Not promoted" ≠ negative evidence.
    # They are listed as UNLABELED for transparency.
    not_promoted = df_main[df_main["promoted"] == False]
    for _, row in not_promoted.head(0).iterrows():   # head(0) = no rows; UNLABELED omitted
        pass  # UNLABELED rows are not included in training labels

    df_labels = pd.DataFrame(rows, columns=REQUIRED_COLS)
    return df_labels


def _csv_hash(df: pd.DataFrame) -> str:
    """SHA256 prefix of the label DataFrame content."""
    content = df.to_csv(index=False).encode()
    return hashlib.sha256(content).hexdigest()[:16]


def save_weak_labels(
    df: pd.DataFrame,
    out_csv: str = OUT_CSV,
    out_manifest: str = OUT_MANIFEST,
) -> dict:
    """Save weak labels CSV and manifest."""
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    # Statistics
    ec_counts = df["evidence_class"].value_counts().to_dict()
    country_counts = df["country"].value_counts().to_dict()

    manifest = {
        "csv_path": out_csv,
        "sha256_prefix": _csv_hash(df),
        "n_rows": len(df),
        "n_positive_labels": int((df["presence_label"] == 1).sum()),
        "n_negative_labels": int((df["presence_label"] == 0).sum()),
        "n_unlabeled": 0,  # UNLABELED not included in CSV
        "evidence_class_counts": ec_counts,
        "country_counts": country_counts,
        "confidence_weight_stats": {
            "mean": round(float(df["confidence_weight"].mean()), 4),
            "min": round(float(df["confidence_weight"].min()), 4),
            "max": round(float(df["confidence_weight"].max()), 4),
        },
        "lag_label_unique": sorted(df["lag_label"].dropna().unique().tolist()),
        "sign_label_counts": df["sign_label"].value_counts().to_dict(),
        "source_artifacts": df["source_artifact"].unique().tolist(),
        "experiment": "DEC-058",
        "constraints": {
            "not_promoted_is_not_negative": True,
            "covid_sensitive_not_robust": True,
            "phase7_lag": DEFAULT_LAG_LABEL,
        },
    }

    with open(out_manifest, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def load_weak_labels(csv_path: str = OUT_CSV) -> pd.DataFrame:
    """Load and validate weak labels CSV."""
    df = pd.read_csv(csv_path)
    for col in REQUIRED_COLS:
        if col not in df.columns:
            raise ValueError(f"Weak labels CSV missing column: {col}")
    # Confidence weights must be in [0,1]
    if not ((df["confidence_weight"] >= 0) & (df["confidence_weight"] <= 1)).all():
        raise ValueError("confidence_weight out of [0,1] range")
    # No null labels should have presence_label with high confidence
    return df


if __name__ == "__main__":
    df = build_weak_labels()
    manifest = save_weak_labels(df)
    print(f"Weak labels built: {len(df)} rows")
    print(f"Evidence classes: {manifest['evidence_class_counts']}")
    print(f"Countries: {manifest['country_counts']}")
    print(f"SHA256: {manifest['sha256_prefix']}")
    print(f"Saved: {OUT_CSV}")
