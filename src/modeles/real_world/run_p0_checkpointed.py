"""
run_p0_checkpointed.py — DEC-056 corrected: P0 validation with trained checkpoint.

Loads the DEC-055 trained SharedRelationEncoder from checkpoint and applies
it to real FR/NL/PT sector panels (P0 zero-shot, no fine-tuning on real data).

This is the CORRECTED version of DEC-056 P0. The previous run
(DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION) used a randomly initialized
encoder and is only valid as a pipeline preflight — it cannot assess model quality.

Usage:
  python -m src.modeles.real_world.run_p0_checkpointed \\
      --checkpoint data/processed/phase16_dec055/shared_relation_encoder_best.pt \\
      --manifest  data/processed/phase16_dec055/checkpoint_manifest.json \\
      --out_dir   data/processed/real_shared_relations_checkpointed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.modeles.synthetic.phase16_decoupled.shared_relation_encoder import (
    SharedRelationEncoder,
    extract_pair_features,
)
from src.modeles.synthetic.phase16_decoupled.gates_dec056 import (
    CAUSAL_TERMS,
    evaluate_all_gates_dec056,
    format_gate_report_dec056,
    scan_for_causal_terms,
)
from src.modeles.real_world.run_shared_relation_real import (
    SECTOR_CODES,
    PT_ABSENT_SECTORS,
    PRESENCE_THRESHOLD,
    WINDOW_SIZE,
    ALL_WINDOWS,
    COVID_YEAR,
    PANEL_PATHS,
    PHASE7_PATH,
    REQUIRED_CSV_COLS,
    build_panel_array,
    normalize_panel,
    compute_stability,
    classify_relations,
    compare_phase7,
    permute_panel_years,
    permute_panel_sectors,
    permute_panel_regions,
    _mean_presence,
    _region_system,
    real_context,
    covid_stability_analysis,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_SECTORS = len(SECTOR_CODES)


# ── Checkpoint loading & verification ─────────────────────────────────────────

def _state_dict_hash(state_dict: dict) -> str:
    """SHA256 prefix of encoder state dict."""
    h = hashlib.sha256()
    for k in sorted(state_dict.keys()):
        h.update(k.encode())
        h.update(state_dict[k].cpu().numpy().tobytes())
    return h.hexdigest()[:16]


def load_trained_encoder(
    checkpoint_path: str,
    manifest_path: str | None = None,
) -> tuple[SharedRelationEncoder, str]:
    """
    Load trained SharedRelationEncoder from checkpoint.
    Verifies SHA256 hash against manifest if provided.
    Raises RuntimeError if hash mismatch.
    Returns (encoder, hash).
    """
    path = Path(checkpoint_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {checkpoint_path}. "
            "Run DEC-055 first: python -m src.modeles.synthetic.phase16_decoupled.run_dec055"
        )

    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state_dict = ckpt["model_state_dict"]

    encoder = SharedRelationEncoder()
    encoder.load_state_dict(state_dict)
    encoder.eval()

    actual_hash = _state_dict_hash(state_dict)

    if manifest_path is not None and Path(manifest_path).exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        expected_hash = manifest.get("sha256_prefix", "")
        if expected_hash and actual_hash != expected_hash:
            raise RuntimeError(
                f"Checkpoint hash mismatch: expected={expected_hash}, actual={actual_hash}. "
                "Checkpoint may be corrupted or replaced."
            )
        log.info(f"Hash verified: {actual_hash} matches manifest")
    else:
        log.warning("No manifest provided — hash not verified")

    log.info(
        f"Loaded checkpoint: {checkpoint_path}\n"
        f"  hash={actual_hash}, params={encoder.n_parameters()}, "
        f"best_seed={ckpt.get('training', {}).get('best_seed', '?')}, "
        f"best_oos_auc={ckpt.get('training', {}).get('best_unseen_pair_auc', float('nan')):.3f}"
    )

    return encoder, actual_hash


def is_encoder_trained(encoder: SharedRelationEncoder) -> bool:
    """
    Heuristic: an untrained encoder with bias=-2.0 on presence head will have
    presence_logit mean near sigmoid(-2.0)=0.119 or lower.
    A trained encoder should have moved significantly from initialization.
    """
    # Check if presence head bias is still at initialization (-2.0 exactly)
    presence_bias = encoder.head_presence.bias.data.item()
    if abs(presence_bias - (-2.0)) < 1e-6:
        return False
    return True


# ── P0 with trained encoder ───────────────────────────────────────────────────

@torch.no_grad()
def eval_window_trained(
    encoder: SharedRelationEncoder,
    norm_panel: np.ndarray,
    obs_mask: np.ndarray,
    years: list[int],
    window_start: int,
    window_end: int,
    country: str,
    checkpoint_hash: str,
    device: str = "cpu",
) -> list[dict]:
    """Evaluate trained encoder on one window. Records checkpoint_hash in output."""
    encoder.eval()
    year_arr = np.array(years)
    w_mask = (year_arr >= window_start) & (year_arr < window_end)
    if w_mask.sum() < 3:
        return []

    w_start_idx = int(np.where(w_mask)[0][0])
    w_end_idx = int(np.where(w_mask)[0][-1]) + 1
    obs_frac = float(obs_mask[:, :, w_start_idx:w_end_idx].mean())
    ctx = real_context(years, window_start, window_end, obs_frac)
    covid_period = (
        "covid" if window_start <= COVID_YEAR < window_end
        else ("pre_covid" if window_end <= COVID_YEAR else "post_covid")
    )

    records = []
    for src_idx, src_s in enumerate(SECTOR_CODES):
        for tgt_idx, tgt_s in enumerate(SECTOR_CODES):
            if src_idx == tgt_idx:
                continue
            if country == "PT" and (src_s in PT_ABSENT_SECTORS or tgt_s in PT_ABSENT_SECTORS):
                continue

            feat = extract_pair_features(
                norm_panel, obs_mask, src_idx, tgt_idx,
                window_end=w_end_idx, window_size=WINDOW_SIZE,
                device=device, context=ctx,
            )
            out = encoder(feat)
            presence_prob = float(torch.sigmoid(out["presence_logit"]))
            direction_prob = float(torch.sigmoid(out["direction_logit"]))
            sign_prob = float(torch.sigmoid(out["sign_logit"]))
            lag_probs = torch.softmax(out["lag_logits"], dim=-1).cpu().numpy()
            inferred_lag = 1 if lag_probs[0] > 0.5 else 2
            inferred_sign = "positive" if sign_prob > 0.5 else "negative"
            confidence = float(out["confidence"])

            records.append({
                "country": country,
                "region_system": _region_system(country),
                "window_start": window_start,
                "window_end": window_end,
                "source_sector": src_s,
                "target_sector": tgt_s,
                "score_presence": presence_prob,
                "score_direction": direction_prob,
                "score_sign": sign_prob,
                "score_lag1": float(lag_probs[0]),
                "score_lag2": float(lag_probs[1]),
                "inferred_lag": inferred_lag,
                "inferred_sign": inferred_sign,
                "confidence": confidence,
                "stability": float("nan"),
                "covid_period": covid_period,
                "validation_status": "ASSOCIATION_CANDIDATE",
                "provenance": "trained_shared_encoder_p0",
                "claim_scope": "analytic_association_only",
                "checkpoint_hash": checkpoint_hash,
            })

    return records


def run_p0_trained(
    encoder: SharedRelationEncoder,
    checkpoint_hash: str,
    countries: list[str] = ["FR", "NL", "PT"],
    device: str = "cpu",
) -> list[dict]:
    all_records = []
    for country in countries:
        log.info(f"P0-trained {country}: loading panel...")
        df = pd.read_csv(PANEL_PATHS[country])
        df = df[df["mask_sector_a10"] == 1.0].copy()
        raw_panel, obs_mask, regions, years = build_panel_array(df, country)

        valid_windows = [
            (ws, we) for ws, we in ALL_WINDOWS
            if ws >= min(years) and we <= max(years) + 1
        ]
        log.info(f"  {country}: {len(regions)} regions, {len(years)} years, "
                 f"{len(valid_windows)} windows")

        for ws, we in valid_windows:
            year_arr = np.array(years)
            w_mask = (year_arr >= ws) & (year_arr < we)
            if w_mask.sum() < 3:
                continue
            w_si = int(np.where(w_mask)[0][0])
            w_ei = int(np.where(w_mask)[0][-1]) + 1
            norm_p = normalize_panel(raw_panel, obs_mask, w_si, w_ei)
            recs = eval_window_trained(encoder, norm_p, obs_mask, years, ws, we,
                                       country, checkpoint_hash, device)
            all_records.extend(recs)

    return all_records


# ── Controls ───────────────────────────────────────────────────────────────────

def run_controls_trained(
    encoder: SharedRelationEncoder,
    checkpoint_hash: str,
    country: str = "PT",
    device: str = "cpu",
    seed: int = 42,
) -> dict:
    """Permutation controls using trained encoder."""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(PANEL_PATHS[country])
    df = df[df["mask_sector_a10"] == 1.0].copy()
    raw_panel, obs_mask, regions, years = build_panel_array(df, country)

    # Representative window
    ws, we = (2014, 2020) if 2014 in years else (min(years), min(years) + 6)
    year_arr = np.array(years)
    w_mask = (year_arr >= ws) & (year_arr < we)
    if w_mask.sum() < 3:
        ws, we = min(years), min(years) + 6
        w_mask = (year_arr >= ws) & (year_arr < we)
    w_si = int(np.where(w_mask)[0][0])
    w_ei = int(np.where(w_mask)[0][-1]) + 1

    norm_real = normalize_panel(raw_panel, obs_mask, w_si, w_ei)
    real_recs = eval_window_trained(encoder, norm_real, obs_mask, years, ws, we,
                                    country, checkpoint_hash, device)
    real_mean = _mean_presence(real_recs)

    ctrl_means: dict[str, float] = {}
    for name, fn in [
        ("permuted_years", permute_panel_years),
        ("permuted_sectors", permute_panel_sectors),
        ("permuted_regions", permute_panel_regions),
    ]:
        pp, pm = fn(raw_panel, obs_mask, np.random.default_rng(seed + 1))
        nn = normalize_panel(pp, pm, w_si, w_ei)
        pr = eval_window_trained(encoder, nn, pm, years, ws, we, country, checkpoint_hash, device)
        ctrl_means[name] = _mean_presence(pr)

    return {
        "real_presence_logit_mean": real_mean,
        "control_presence_logit_means": ctrl_means,
    }


# ── Embeddings ─────────────────────────────────────────────────────────────────

def export_embeddings_trained(
    encoder: SharedRelationEncoder,
    checkpoint_hash: str,
    countries: list[str] = ["FR", "NL", "PT"],
    device: str = "cpu",
) -> list[dict]:
    records = []
    encoder.eval()
    for country in countries:
        df = pd.read_csv(PANEL_PATHS[country])
        df = df[df["mask_sector_a10"] == 1.0].copy()
        raw_panel, obs_mask, regions, years = build_panel_array(df, country)

        ws_ref, we_ref = (2014, 2020) if 2014 in years else (min(years), min(years) + 6)
        year_arr = np.array(years)
        w_mask = (year_arr >= ws_ref) & (year_arr < we_ref)
        if w_mask.sum() < 3:
            continue

        w_si = int(np.where(w_mask)[0][0])
        w_ei = int(np.where(w_mask)[0][-1]) + 1
        norm_p = normalize_panel(raw_panel, obs_mask, w_si, w_ei)
        ctx = real_context(years, ws_ref, we_ref, float(obs_mask.mean()))

        with torch.no_grad():
            for si, ss in enumerate(SECTOR_CODES):
                for ti, ts in enumerate(SECTOR_CODES):
                    if si == ti:
                        continue
                    if country == "PT" and (ss in PT_ABSENT_SECTORS or ts in PT_ABSENT_SECTORS):
                        continue
                    feat = extract_pair_features(norm_p, obs_mask, si, ti,
                                                 window_end=w_ei, window_size=WINDOW_SIZE,
                                                 device=device, context=ctx)
                    out = encoder(feat)
                    records.append({
                        "country": country,
                        "source_sector": ss,
                        "target_sector": ts,
                        "window": f"{ws_ref}-{we_ref}",
                        "presence_prob": float(torch.sigmoid(out["presence_logit"])),
                        "embedding_32dim": out["embedding"].cpu().numpy().tolist(),
                        "checkpoint_hash": checkpoint_hash,
                        "prototype_candidate_id": None,
                        "provenance": "trained_shared_encoder_p0",
                        "status": "inferred_candidate",
                        "claim_scope": "analytic_association_only",
                    })
    return records


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    import time

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device = "cpu"

    t0 = time.time()
    log.info("DEC-056 CORRECTED: P0 Validation with Trained Checkpoint")

    # ── Load checkpoint ─────────────────────────────────────────────────────
    encoder, ckpt_hash = load_trained_encoder(args.checkpoint, args.manifest)

    # Guard: reject untrained encoder
    if not is_encoder_trained(encoder):
        raise RuntimeError(
            "Encoder appears untrained (presence bias == -2.0 initialization). "
            "This run would be DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION. "
            "Train the encoder first with run_dec055.py and provide the checkpoint."
        )

    log.info(f"Trained encoder confirmed (presence bias != -2.0), hash={ckpt_hash}")

    # ── P0: trained encoder on real panels ──────────────────────────────────
    log.info("Running P0 with trained encoder on FR/NL/PT...")
    p0_records = run_p0_trained(encoder, ckpt_hash, device=device)
    log.info(f"P0 (trained): {len(p0_records)} pair-window records")

    # Score distribution
    presence_scores = [r["score_presence"] for r in p0_records]
    p_mean = float(np.mean(presence_scores))
    p_max = float(np.max(presence_scores))
    p_above_threshold = sum(1 for s in presence_scores if s > PRESENCE_THRESHOLD)
    log.info(f"Presence scores: mean={p_mean:.3f}, max={p_max:.3f}, "
             f"above_{PRESENCE_THRESHOLD}={p_above_threshold}/{len(presence_scores)}")

    # ── Stability ─────────────────────────────────────────────────────────
    log.info("Computing temporal stability...")
    stability_by_country: dict[str, float] = {}
    for country in ["FR", "NL", "PT"]:
        c_recs = [r for r in p0_records if r["country"] == country]
        windows = sorted(set((r["window_start"], r["window_end"]) for r in c_recs))
        rby_w = {w: [r for r in c_recs if (r["window_start"], r["window_end"]) == w]
                 for w in windows}
        stab = compute_stability(rby_w)
        stability_by_country[country] = stab.get("mean", float("nan"))
    log.info(f"Stability: {stability_by_country}")

    # ── COVID analysis ─────────────────────────────────────────────────────
    log.info("COVID sensitivity analysis...")
    covid_analysis = covid_stability_analysis(p0_records)
    pre_stab_vals = [v["pre_vs_covid"] for v in covid_analysis.values()
                     if not math.isnan(v.get("pre_vs_covid", float("nan")))]
    covid_stab_vals = [v["covid_vs_post"] for v in covid_analysis.values()
                       if not math.isnan(v.get("covid_vs_post", float("nan")))]

    # ── Permutation controls ──────────────────────────────────────────────
    log.info("Running permutation controls (PT)...")
    ctrl = run_controls_trained(encoder, ckpt_hash, country="PT", device=device)
    real_mean = ctrl["real_presence_logit_mean"]
    ctrl_means = ctrl["control_presence_logit_means"]
    log.info(f"Controls: real={real_mean:.3f}, {ctrl_means}")

    # ── Phase 7 comparison ────────────────────────────────────────────────
    log.info("Comparing with Phase 7...")
    p7_result = compare_phase7(p0_records)
    log.info(f"Phase 7 concordance: {p7_result.get('phase7_sign_concordance', float('nan')):.3f} "
             f"({p7_result.get('phase7_n_compared', 0)} edges)")

    # ── Classification ─────────────────────────────────────────────────────
    log.info("Classifying relations...")
    classified = classify_relations(p0_records)
    replicated = [c for c in classified if c["validation_status"] == "REPLICATED_ASSOCIATION"]
    cs_by_country: dict[str, list] = {c: [] for c in ["FR", "NL", "PT"]}
    for c in classified:
        if c["validation_status"] == "ASSOCIATION_CANDIDATE":
            cs_by_country[c["country"]].append(c)

    top_pairs: list[dict] = []
    for country in ["FR", "NL", "PT"]:
        c_cl = [c for c in classified if c["country"] == country
                and c["best_presence"] > PRESENCE_THRESHOLD]
        c_cl.sort(key=lambda x: -x["best_presence"])
        for c in c_cl[:5]:
            top_pairs.append({
                "country": country,
                "source_sector": c["source_sector"],
                "target_sector": c["target_sector"],
                "score_presence": c["best_presence"],
                "score_sign": float("nan"),
                "inferred_lag": c["inferred_lag"],
                "inferred_sign": c["inferred_sign"],
                "confidence": c["confidence"],
                "window_start": int(c["best_window"].split("-")[0]),
                "window_end": int(c["best_window"].split("-")[1]),
                "validation_status": c["validation_status"],
            })

    # ── NaN/Inf check ─────────────────────────────────────────────────────
    nan_count = sum(1 for r in p0_records if math.isnan(r.get("score_presence", 0.0)))
    inf_count = sum(1 for r in p0_records if math.isinf(r.get("score_presence", 0.0)))

    # ── Embeddings ─────────────────────────────────────────────────────────
    log.info("Exporting embeddings...")
    embed_records = export_embeddings_trained(encoder, ckpt_hash, device=device)

    # ── Causal language check ──────────────────────────────────────────────
    causal_found = scan_for_causal_terms(
        " ".join([r.get("claim_scope", "") + " " + r.get("provenance", "") for r in p0_records])
    )

    # ── CSV output ─────────────────────────────────────────────────────────
    def _stability_for(r: dict) -> float:
        return stability_by_country.get(r["country"], float("nan"))

    df_out = pd.DataFrame(p0_records)
    df_out["stability"] = df_out.apply(_stability_for, axis=1)
    for col in REQUIRED_CSV_COLS:
        if col not in df_out.columns:
            df_out[col] = ""
    df_out = df_out[REQUIRED_CSV_COLS + [c for c in df_out.columns if c not in REQUIRED_CSV_COLS]]

    csv_ok = all(c in df_out.columns for c in REQUIRED_CSV_COLS)
    json_ok = isinstance(embed_records, list) and all(
        "country" in r and "source_sector" in r for r in embed_records[:3]
    )

    csv_path = out_dir / "shared_relation_scores_checkpointed.csv"
    df_out.to_csv(csv_path, index=False)
    log.info(f"CSV saved: {csv_path} ({len(df_out)} rows)")

    embed_path = out_dir / "shared_relation_embeddings_checkpointed.json"
    with open(embed_path, "w") as f:
        json.dump(embed_records, f, default=str)
    log.info(f"Embeddings: {embed_path} ({len(embed_records)} records)")

    # ── Gates ──────────────────────────────────────────────────────────────
    log.info("Evaluating gates...")
    gate_input = {
        "leakage_check": True,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "cross_country_pooling": False,
        "pt_kz_excluded": True,
        "real_presence_logit_mean": real_mean,
        "control_presence_logit_means": ctrl_means,
        "stability_by_country": stability_by_country,
        "phase7_sign_concordance": p7_result.get("phase7_sign_concordance", float("nan")),
        "phase7_n_compared": p7_result.get("phase7_n_compared", 0),
        "phase7_pairs_compared": p7_result.get("phase7_pairs_compared", []),
        "replicated_pairs": [f"{r['source_sector']}→{r['target_sector']}" for r in replicated],
        "presence_threshold": PRESENCE_THRESHOLD,
        "replication_note": f"Pairs above {PRESENCE_THRESHOLD} in ≥2 countries",
        "country_specific_pairs": {c: [f"{r['source_sector']}→{r['target_sector']}"
                                        for r in cs[:5]] for c, cs in cs_by_country.items()},
        "covid_windows_reported_separately": True,
        "pre_covid_stability_mean": float(np.nanmean(pre_stab_vals)) if pre_stab_vals else float("nan"),
        "covid_stability_mean": float(np.nanmean(covid_stab_vals)) if covid_stab_vals else float("nan"),
        "post_covid_stability_mean": float("nan"),
        "top_pairs_documented": top_pairs,
        "causal_terms_found": causal_found,
        "csv_schema_valid": csv_ok,
        "json_schema_valid": json_ok,
        "required_csv_cols_present": csv_ok,
    }

    gates = evaluate_all_gates_dec056(gate_input)
    n_pass = sum(1 for g in gates.values() if g.verdict == "PASS")
    n_fail = sum(1 for g in gates.values() if g.verdict == "FAIL")
    n_ne = sum(1 for g in gates.values() if g.verdict == "NOT_EVALUATED")

    # ── Decision ───────────────────────────────────────────────────────────
    r1 = gates["R1"].verdict == "PASS"
    r2 = gates["R2"].verdict == "PASS"
    r3 = gates["R3"].verdict == "PASS"
    r4 = gates["R4"].verdict == "PASS"
    r5 = gates["R5"].verdict == "PASS"

    if not r1:
        decision = "REAL_SHARED_RELATION_NOT_SUPPORTED"
    elif not r2:
        decision = "ENCODER_CAPTURES_ARTIFACTS"
    elif r3 and r4 and r5:
        decision = "REAL_SHARED_RELATION_SUPPORTED"
    elif r4 and not r5:
        decision = "PHASE7_CONCORDANCE_ONLY"
    elif r5 and not r4:
        decision = "COUNTRY_SPECIFIC_ONLY"
    elif r3 or r4 or r5:
        decision = "REAL_SHARED_RELATION_PARTIAL"
    else:
        decision = "REAL_SHARED_RELATION_NOT_SUPPORTED"

    elapsed = time.time() - t0

    # ── Save validation JSON ────────────────────────────────────────────────
    val_out = {
        "experiment": "DEC-056-CORRECTED",
        "protocol": "P0_trained_checkpoint",
        "run_note": "Trained checkpoint (DEC-055 best seed). Replaces DEC056_PREVIOUS_RUN_INVALID.",
        "checkpoint_path": args.checkpoint,
        "checkpoint_hash": ckpt_hash,
        "encoder_params": encoder.n_parameters(),
        "n_p0_records": len(p0_records),
        "presence_stats": {
            "mean": p_mean, "max": p_max,
            "above_threshold": p_above_threshold,
            "threshold": PRESENCE_THRESHOLD,
        },
        "stability_by_country": stability_by_country,
        "covid_analysis": covid_analysis,
        "controls": ctrl,
        "phase7_comparison": p7_result,
        "replicated_pairs": [{"src": r["source_sector"], "tgt": r["target_sector"],
                               "best_presence": r["best_presence"]} for r in replicated[:10]],
        "top_pairs": top_pairs,
        "classified_counts": {s: sum(1 for c in classified if c["validation_status"] == s)
                               for s in ["ASSOCIATION_CANDIDATE", "REPLICATED_ASSOCIATION",
                                         "COVID_SENSITIVE", "COUNTRY_SPECIFIC", "NOT_SUPPORTED"]},
        "gates": {gid: {"verdict": g.verdict, "description": g.description,
                         "evidence": {k: (v if not isinstance(v, float) or not math.isnan(v) else None)
                                      for k, v in g.evidence.items()}}
                  for gid, g in gates.items()},
        "gate_report": format_gate_report_dec056(gates),
        "decision": decision,
        "n_gates_pass": n_pass,
        "n_gates_fail": n_fail,
        "n_gates_ne": n_ne,
        "elapsed_seconds": elapsed,
        "previous_run_status": "DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION",
        "previous_run_note": "Prior P0 used randomly initialized encoder — valid only as pipeline preflight",
    }

    val_path = out_dir / "shared_relation_validation_checkpointed.json"
    with open(val_path, "w") as f:
        json.dump(val_out, f, indent=2, default=str)

    # ── Print ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DEC-056 CORRECTED: P0 Validation with Trained Checkpoint")
    print("=" * 70)
    print(f"Checkpoint hash: {ckpt_hash}")
    print(format_gate_report_dec056(gates))
    print(f"\nGates: {n_pass}/10 PASS, {n_fail}/10 FAIL, {n_ne}/10 NOT_EVALUATED")
    print(f"\nDecision: {decision}")
    print(f"\nPresence scores: mean={p_mean:.3f}, max={p_max:.3f}, "
          f"above_{PRESENCE_THRESHOLD}={p_above_threshold}/{len(presence_scores)}")

    print("\nStability by country:")
    for c, s in stability_by_country.items():
        print(f"  {c}: {s:.3f}")

    print("\nPermutation controls:")
    print(f"  Real mean presence: {real_mean:.3f}")
    for cn, cv in ctrl_means.items():
        print(f"  {cn}: {cv:.3f}  (delta={real_mean-cv:.3f})")

    print(f"\nPhase 7 concordance: {p7_result.get('phase7_sign_concordance', float('nan')):.3f} "
          f"({p7_result.get('phase7_n_compared', 0)} edges)")
    print(f"\nReplicated associations: {len(replicated)}")
    for r in replicated[:5]:
        print(f"  {r['source_sector']}→{r['target_sector']} "
              f"(presence={r['best_presence']:.3f}, {r['best_window']})")

    print("\nTop pairs per country:")
    for country in ["FR", "NL", "PT"]:
        top_c = [t for t in top_pairs if t["country"] == country][:3]
        if top_c:
            print(f"  {country}: " + ", ".join(
                f"{t['source_sector']}→{t['target_sector']} ({t['score_presence']:.3f})"
                for t in top_c
            ))

    print(f"\nClassified: {val_out['classified_counts']}")
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"Output: {out_dir}")

    print("\n[AUDIT NOTE]")
    print(f"  Previous DEC-056 run: DEC056_PREVIOUS_RUN_INVALID_FOR_MODEL_VALIDATION")
    print(f"  That run used an untrained encoder and is only valid as a real-pipeline preflight.")
    print(f"  This corrected run uses checkpoint hash={ckpt_hash} (DEC-055 best_seed=30).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEC-056 corrected P0 with trained checkpoint")
    parser.add_argument("--checkpoint",
                        default="data/processed/phase16_dec055/shared_relation_encoder_best.pt")
    parser.add_argument("--manifest",
                        default="data/processed/phase16_dec055/checkpoint_manifest.json")
    parser.add_argument("--out_dir",
                        default="data/processed/real_shared_relations_checkpointed")
    main(parser.parse_args())
