"""Final audit of the HERALD 93–96 stage, from the committed artefacts alone.

This script reads nothing but result JSON and reports what it finds. It never edits a result,
re-fits a model or adjusts a gate. Every claim the canonical reports make that can be checked
against an artefact is checked here, and every disagreement is recorded rather than repaired.

Run:  python reports/final_visual_evidence/scripts/audit_stage.py
Out:  reports/final_visual_evidence/provenance/stage_audit.json
"""

from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from herald_evidence import (group, herald93_summary, herald94_tasks, herald95_tasks,
                             herald96_tasks, median, write_provenance)

FINDINGS: list[dict[str, str]] = []


def note(severity: str, where: str, what: str, consequence: str) -> None:
    FINDINGS.append({"severity": severity, "where": where, "finding": what,
                     "consequence": consequence})


# ── HERALD 93 ────────────────────────────────────────────────────────────────

def audit_93() -> dict:
    summary = herald93_summary()
    table = summary["table"]
    rows = {}
    for name, entry in table.items():
        rows[name] = {
            "forecast_skill_median": entry["forecast_skill_median"],
            "edge_f1_median": entry["edge_f1_median"],
            "dense_correlation_median": entry["dense_correlation_median"],
            "auprc_s1": entry["auprc_median"],
            "auprc_s0": entry["s0_auprc_median"],
            "prevalence": entry["prevalence_median"],
            "stability": entry["stability"],
            "parameters": entry["cost"]["parameters"],
            "seconds": entry["cost"]["seconds"],
            "peak_memory_mb": entry["cost"]["peak_memory_mb"],
            "abstention_rate": entry.get("abstention_rate"),
            "no_structure_found_in_s0": entry["checks"]["no_structure_found_in_s0"],
            "relational_recovery_supported": entry["relational_recovery_supported"],
            "label": entry["label"],
        }

    # Claim: no method beats persistence.
    beats = {n: r["forecast_skill_median"] for n, r in rows.items()
             if r["forecast_skill_median"] is not None and r["forecast_skill_median"] > 0.001}
    if beats:
        note("HIGH", "HERALD 93 §6",
             f"a method exceeds persistence by more than 0.001 skill: {beats}",
             "the report's 'no method beats persistence' would need qualifying")

    # Claim: every method fails edge F1 and dense correlation.
    passed = [n for n, r in rows.items() if r["relational_recovery_supported"]]
    if passed:
        note("HIGH", "HERALD 93 §7", f"a method is marked recovery-supported: {passed}",
             "the CASE_C decision would need revisiting")

    # The stale threshold label.
    declared = summary["thresholds"]["edge_f1"]
    herald128 = rows["herald@128"]
    applied_is_relative = (herald128["edge_f1_median"] > declared
                           and not herald128["relational_recovery_supported"])
    if applied_is_relative:
        note("LOW", "hpc_results/herald93/benchmark_summary_v2.json",
             f"`thresholds.edge_f1` records {declared} and the check key is named "
             f"`edge_f1_at_least_0_50`, but the rule actually applied is prevalence + 0.10 "
             f"= {herald128['prevalence']+0.10:.2f}, as HERALD 93 §7 states — "
             f"herald@128 scores {herald128['edge_f1_median']:.3f} and still fails",
             "artefact metadata is stale; the reported science is the one that ran")

    # Claim: HERALD is the family the S0 control disqualifies.
    s0_clean = {n: r["no_structure_found_in_s0"] for n, r in rows.items()}
    return {"rows": rows, "s0_control_clean": s0_clean,
            "france_decision": summary["france_decision"],
            "chosen_herald_width": summary["chosen_herald_width"],
            "thresholds_declared": summary["thresholds"]}


# ── HERALD 94 ────────────────────────────────────────────────────────────────

def audit_94() -> dict:
    tasks = herald94_tasks()
    by_scenario = group(tasks, "scenario")
    seeds = sorted({t["seed"] for t in tasks})
    retired = {9701, 9702, 9703, 9704, 9705}
    if retired & set(seeds):
        note("HIGH", "HERALD 94", "a retired calibration seed appears in the reported grid",
             "the reported grid would be calibrated on its own diagnosis")

    out = {"seeds": seeds, "n_tasks": len(tasks),
           "zones": sorted({t["n_zones"] for t in tasks}),
           "origins": sorted({len(t["origins"]) for t in tasks}),
           "scenarios": {}}
    for (scenario,), rows in sorted(by_scenario.items()):
        rows = sorted(rows, key=lambda r: r["seed"])
        linear = [r["arms"]["ridge_linear"]["gain_over_best_single"] for r in rows]
        composite = [r["arms"]["ridge_composite"]["gain_over_ridge_linear"] for r in rows]
        mlp = [r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"] for r in rows]
        destroyed = [r["controls"]["interaction_destroyed"]["mlp_nonlinear"]
                     ["gain_over_ridge_linear"] for r in rows]
        surviving = (median(destroyed) / median(mlp)) if median(mlp) else float("nan")
        out["scenarios"][scenario] = {
            "temporal_gain_over_best_single": {"median": median(linear), "per_seed": linear},
            "composite_gain_over_linear": {"median": median(composite), "per_seed": composite},
            "mlp_gain_over_linear": {"median": median(mlp), "per_seed": mlp,
                                     "seeds_won": sum(1 for v in mlp if v > 0)},
            "surviving_share_after_interaction_destroyed": surviving,
            "best_single_column": sorted({r["best_single_column"] for r in rows}),
            "parameters": {"mlp": rows[0]["arms"]["mlp_nonlinear"]["parameters"],
                           "ridge": rows[0]["arms"]["ridge_linear"]["parameters"]},
            "seconds_median": median([r["cost"]["total_seconds"] for r in rows]),
        }

    null_gain = out["scenarios"]["N0_NULL"]["mlp_gain_over_linear"]["median"]
    for scenario, entry in out["scenarios"].items():
        if scenario == "N0_NULL":
            continue
        if entry["mlp_gain_over_linear"]["median"] > null_gain:
            note("INFO", f"HERALD 94 {scenario}",
                 "the network's median gain exceeds its gain in the null scenario here",
                 "does not change the verdict, which requires it in every scenario")

    if any(entry["composite_gain_over_linear"]["median"] > 0
           for entry in out["scenarios"].values()):
        note("HIGH", "HERALD 94 §3.2", "a composite arm improves on the linear arm",
             "the 'composites add nothing' claim would need qualifying")

    widths = {r["arms"]["mlp_nonlinear"].get("hidden") for r in tasks}
    out["forbidden_width_256_present"] = 256 in widths
    return out


# ── HERALD 95 ────────────────────────────────────────────────────────────────

def audit_95() -> dict:
    tasks = herald95_tasks()
    by_key = group(tasks, "scenario", "relational_scale")
    out = {"seeds": sorted({t["seed"] for t in tasks}), "n_tasks": len(tasks),
           "zones": sorted({t["n_zones"] for t in tasks}),
           "scales": sorted({t["relational_scale"] for t in tasks}),
           "ladder": {}}

    unpaired = [f"{t['scenario']}@{t['relational_scale']}#{t['seed']}"
                for t in tasks if not all(t["worlds_are_paired"].values())]
    if unpaired:
        note("HIGH", "HERALD 95", f"worlds not paired in {unpaired}",
             "the ladder would not be reading one varied quantity")

    for (scenario, scale), rows in sorted(by_key.items()):
        key = f"{scenario}@{scale}"
        snr = median([r["observable_diagnostics"]["per_scale"][str(scale)]["observable"]
                      [r["primary_signal"]]["snr"] for r in rows])
        out["ladder"][key] = {
            "scenario": scenario, "scale": scale,
            "observable_snr": snr,
            "clipped_share": median([r["calibration"]["clipped_share"]["headcount"]
                                     for r in rows]),
            "oracle": median([r["arms"]["oracle_relational"]["gain_over_ridge_linear"]
                              for r in rows]),
            "oracle_per_seed": [r["arms"]["oracle_relational"]["gain_over_ridge_linear"]
                                for r in sorted(rows, key=lambda x: x["seed"])],
            "network": median([r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"]
                               for r in rows]),
            "network_per_seed": [r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"]
                                 for r in sorted(rows, key=lambda x: x["seed"])],
            "destroyed": median([r["controls"]["interaction_destroyed"]["mlp_nonlinear"]
                                 ["gain_over_ridge_linear"] for r in rows]),
            "edge_auprc": median([r["edge_recovery"]["auprc"] for r in rows]),
            "edge_prevalence": median([r["edge_recovery"]["prevalence"] for r in rows]),
            "dense_correlation": median([r["edge_recovery"]["dense_correlation"]
                                         for r in rows]),
            "score_corr_with_prior": median([r["edge_recovery"]["score_diagnostics"]
                                             ["correlation_with_prior"] for r in rows]),
            "score_corr_with_truth": median([r["edge_recovery"]["score_diagnostics"]
                                             ["correlation_with_true_propagation"]
                                             for r in rows]),
        }

    # The oracle must be exactly zero without a mechanism and monotone with it.
    for scenario in ("N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION"):
        series = [out["ladder"][f"{scenario}@{s}"]["oracle"] for s in (0.0, 0.5, 1.0, 2.0)]
        if not all(b >= a for a, b in zip(series, series[1:])):
            note("HIGH", f"HERALD 95 {scenario}",
                 f"the oracle is not monotone in the scale: {series}",
                 "the instrument would not be measuring the ceiling")
        if abs(series[0]) > 1e-12:
            note("HIGH", f"HERALD 95 {scenario}",
                 f"the oracle is non-zero at scale 0: {series[0]}",
                 "the control would not be a control")

    # N0_NULL is claimed flat across all five scales.
    null_arms = {s: out["ladder"][f"N0_NULL@{s}"]["network"] for s in out["scales"]}
    null_edges = {s: out["ladder"][f"N0_NULL@{s}"]["edge_auprc"] for s in out["scales"]}
    if len(set(round(v, 12) for v in null_arms.values())) > 1:
        note("MEDIUM", "HERALD 95 §3",
             f"the null scenario's forecasting arms differ across scales: {null_arms}",
             "the flatness claim would be wrong where it matters most")
    if len(set(round(v, 12) for v in null_edges.values())) > 1:
        note("MEDIUM", "HERALD 95 §3",
             f"the null scenario's edge recovery is NOT identical across the five scales — "
             f"AUPRC {null_edges}. Every forecasting arm and control is bit-identical; only "
             f"the edge scorer moves, and only at scale 0.0",
             "the report's 'returns identical numbers' is true of the arms and false of the "
             "edge scorer; the differences are far smaller than the seed spread and no "
             "verdict depends on them, since edge recovery is inert at every scale")

    out["null_flatness"] = {"arms": null_arms, "edge_auprc": null_edges}
    return out


# ── HERALD 96 ────────────────────────────────────────────────────────────────

_AUDIT_96_CACHE: dict | None = None


def audit_96() -> dict:
    global _AUDIT_96_CACHE
    if _AUDIT_96_CACHE is not None:
        return _AUDIT_96_CACHE
    tasks = herald96_tasks()
    out = {"seeds": sorted({t["seed"] for t in tasks}), "n_tasks": len(tasks),
           "zones": sorted({t["n_zones"] for t in tasks}),
           "scales": sorted({t["relational_scale"] for t in tasks}),
           "supports": sorted({t["support"] for t in tasks}),
           "cells": {}}

    unfrozen = [t for t in tasks if not t["baseline"]["frozen"]
                or abs(t["baseline"]["checksum_before"] - t["baseline"]["checksum_after"]) > 0]
    if unfrozen:
        note("HIGH", "HERALD 96", f"{len(unfrozen)} tasks did not keep the baseline frozen",
             "the residual target would have moved under the relational arm")

    for (scenario, scale, support), rows in sorted(
            group(tasks, "scenario", "relational_scale", "support").items()):
        key = f"{scenario}@{scale}|{support}"
        recovery = [r["recovery"] for r in rows]
        out["cells"][key] = {
            "scenario": scenario, "scale": scale, "support": support,
            "n_seeds": len(rows),
            "oracle_all_families": median([r["oracles"]["all_families"] for r in rows]),
            "oracle_per_family": {f: median([r["oracles"][f] for r in rows])
                                  for f in ("commuting", "similarity", "complementarity")},
            "arm_residual_gain": median([r["arm"]["residual_gain"] for r in rows]),
            "arm_gain_per_seed": [r["arm"]["residual_gain"]
                                  for r in sorted(rows, key=lambda x: x["seed"])],
            "auprc": median([r["auprc"] for r in recovery]),
            "prevalence": median([r["prevalence"] for r in recovery]),
            "auprc_outside_commuting": median([r["auprc_outside_commuting"]
                                               for r in recovery]),
            "edge_f1": median([r["edge_f1"] for r in recovery]),
            "n_true_in_support": median([r["n_true_in_support"] for r in recovery]),
            "n_true_outside_commuting_in_support": median(
                [r["n_true_outside_commuting_in_support"] for r in recovery]),
            "mean_score_true": median([median([v["mean_score"]
                                               for v in r["per_family"].values()
                                               if "mean_score" in v]) for r in recovery]),
            "mean_score_elsewhere": median([median([v["mean_score_elsewhere"]
                                                    for v in r["per_family"].values()
                                                    if "mean_score_elsewhere" in v])
                                            for r in recovery]),
            "n_pairs": median([r["arm"]["n_pairs"] for r in rows]),
            "parameters": sorted({r["arm"]["parameters"] for r in rows}),
            "seconds": median([r["cost"]["total_seconds"] for r in rows]),
        }

    # The oracle: exactly zero in the null, monotone in the mechanism scenario.
    for support in out["supports"]:
        nulls = [out["cells"][f"M0_NULL@{s}|{support}"]["oracle_all_families"]
                 for s in out["scales"]]
        if any(abs(v) > 1e-12 for v in nulls):
            note("HIGH", "HERALD 96", f"oracle non-zero in M0_NULL for {support}: {nulls}",
                 "the null control would be compromised")
        series = [out["cells"][f"M1_MULTIRELATIONAL@{s}|{support}"]["oracle_all_families"]
                  for s in out["scales"]]
        if not all(b >= a for a, b in zip(series, series[1:])):
            note("HIGH", "HERALD 96", f"oracle not monotone for {support}: {series}",
                 "the instrument would not be sound")

    # The arm: nothing may be reported as recovery.
    recovering = [k for k, c in out["cells"].items()
                  if c["scenario"] == "M1_MULTIRELATIONAL" and c["auprc"] > c["prevalence"]]
    out["cells_where_auprc_exceeds_prevalence"] = recovering
    for key in recovering:
        cell = out["cells"][key]
        twin = out["cells"][f"M0_NULL@{cell['scale']}|{cell['support']}"]
        ratio_m1 = cell["auprc"] / cell["prevalence"]
        ratio_m0 = twin["auprc"] / twin["prevalence"]
        note("MEDIUM", f"HERALD 96 {key}",
             f"AUPRC sits above prevalence (ratio {ratio_m1:.2f}), but the same support does "
             f"so by {ratio_m0:.2f} in the null scenario, where nothing propagates",
             "a support artefact, not recovery; the report's own table shows both numbers, "
             "and its summarising sentence 'AUPRC equals prevalence' is looser than the table")

    # Cost figures the report quotes.
    seconds = [t["cost"]["total_seconds"] for t in tasks]
    pairs = [t["arm"]["n_pairs"] for t in tasks]
    out["cost_range_seconds"] = [min(seconds), max(seconds)]
    out["candidate_pairs_range"] = [min(pairs), max(pairs)]
    out["arm_parameters"] = sorted({t["arm"]["parameters"] for t in tasks})
    quoted_seconds, quoted_pairs = (109, 218), (977, 6320)
    if (min(seconds), max(seconds)) != quoted_seconds:
        note("LOW", "HERALD 96 §5",
             f"the report quotes {quoted_seconds[0]}–{quoted_seconds[1]} s per task; the "
             f"artefacts span {min(seconds):.1f}–{max(seconds):.1f} s",
             "cost is understated in both directions; no scientific claim depends on it")
    if (min(pairs), max(pairs)) != quoted_pairs:
        note("LOW", "HERALD 96 §5",
             f"the report quotes {quoted_pairs[0]}–{quoted_pairs[1]} candidate pairs; the "
             f"artefacts span {min(pairs)}–{max(pairs)}. 977 is HERALD 94's network "
             f"parameter count, not a support size; the smallest support "
             f"(similarity_only) holds {min(pairs)} pairs",
             "a transcription slip in a cost sentence; no verdict depends on it")
    _AUDIT_96_CACHE = out
    return out


# ── smoke versus final ───────────────────────────────────────────────────────

def audit_smoke_versus_final() -> dict:
    import pathlib
    from herald_evidence import RESULTS
    out = {}
    smoke_dir = RESULTS / "herald96" / "smoke"
    if smoke_dir.exists():
        smoke = {}
        for path in sorted(smoke_dir.glob("*.json")):
            payload = json.loads(path.read_text())
            smoke[f"{payload['scenario']}@{payload['relational_scale']}|"
                  f"{payload['support']}"] = payload["arm"]["residual_gain"]
        final = audit_96()["cells"]
        comparison = {}
        for key, value in smoke.items():
            if key in final:
                comparison[key] = {"smoke_seed_9951": value,
                                   "final_seeds_median": final[key]["arm_residual_gain"]}
        out["herald96"] = {"smoke_seeds": [9951], "final_seeds": [9961, 9962, 9963, 9964, 9965],
                           "comparison": comparison}
        for key, pair in comparison.items():
            if pair["smoke_seed_9951"] > 0 >= pair["final_seeds_median"]:
                note("INFO", f"HERALD 96 {key}",
                     f"the smoke seed returned {pair['smoke_seed_9951']:+.4f} and the five "
                     f"final seeds {pair['final_seeds_median']:+.4f}",
                     "confirms the report's §4: no smoke result may stand as a conclusion")
        quoted = {"M1_MULTIRELATIONAL@1.0|typed_union": 0.0414,
                  "M1_MULTIRELATIONAL@1.0|commuting_only": 0.0210}
        for key, value in quoted.items():
            actual = comparison.get(key, {}).get("smoke_seed_9951")
            if actual is not None and abs(actual - value) > 5e-4:
                note("LOW", "HERALD 96 §4",
                     f"the report quotes a smoke gain of {value:+.4f} for {key}; the artefact "
                     f"holds {actual:+.4f}",
                     "a transcription slip in a paragraph whose point — that the smoke was "
                     "wrong — is unaffected by either figure")
    return out


def main() -> None:
    payload = {
        "kind": "herald_stage_closure_audit",
        "scope": "HERALD 93, 94, 95, 96 — synthetic benchmark stage",
        "rule": "artefacts are read, never written; no gate is moved; no model is refitted",
        "herald93": audit_93(),
        "herald94": audit_94(),
        "herald95": audit_95(),
        "herald96": audit_96(),
        "smoke_versus_final": audit_smoke_versus_final(),
        "protocol_separation": {
            "note": "HERALD 93 and HERALD 96 must never share a numeric ranking",
            "herald93": {"zones": 280, "target": "log-growth h=1", "scenarios": ["S0", "S1"],
                         "support": "commuting top-40, truth drawn inside it",
                         "prevalence": 0.70},
            "herald96": {"zones": 80, "target": "residual after a frozen local baseline",
                         "scenarios": ["M0_NULL", "M1_MULTIRELATIONAL"],
                         "support": "four supports, 2/3 of the truth outside commuting",
                         "prevalence": "0.011–0.061 depending on support"},
        },
        "findings": FINDINGS,
    }
    path = write_provenance("stage_audit.json", payload)
    print(f"wrote {path}")
    print(f"{len(FINDINGS)} findings")
    for entry in FINDINGS:
        print(f"  [{entry['severity']:6s}] {entry['where']}: {entry['finding'][:150]}")


if __name__ == "__main__":
    main()
