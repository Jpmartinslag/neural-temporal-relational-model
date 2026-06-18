# HERALD 11 — HPC and Results Map

**Created:** 2026-06-18 (post-consolidation structural mapping).
**Method:** audited by directory/job naming only. No log or result file was deleted.
**Authoritative machine-readable source:** `hpc/hpc_phase_registry.json` — this map is a
human-readable companion, not a replacement.
**Rule:** A result existing in `hpc_results/` is not citable on its own — it must be
traced to the DEC-* entry that interprets it (this map gives that trace).

---

## 1. HPC scripts — active

| Path | Phase | DEC |
|---|---|---|
| `hpc/phase7_sector_precedence/` | Phase 7 sector precedence (original, PT municipal, NL gemeente proxy) | DEC-033/034/064/065 |
| `hpc/phase9_synthetic_generalization/` | Synthetic benchmark Phase 9-11 | DEC-039/040/042/045 |
| `hpc/phase10_synthetic_lagged/` | Phase 10 lagged-graph architecture | DEC-043/044 |
| `hpc/forecast/` | Forecast baseline jobs | DEC-006 |
| `hpc/validation/`, `hpc/audit/`, `hpc/tools/` | Cross-phase validation/audit helper scripts | Utility, not phase-specific |

## 2. HPC scripts — historical (folder active for new jobs, but most scripts inside are CLOSED)

| Path | Phase | DEC | Status |
|---|---|---|---|
| `hpc/phase4/` | International generalization (4A→4Q sub-phases) | DEC-001→DEC-011 | Mixed: 4N/4E-B causal baselines ACTIVE; 4A/4D LEAKAGE-AFFECTED; 4P/4Q CLOSED FAIL |
| `hpc/phase5/` | Fixed-L2 residual corrector | DEC-023 | CLOSED, `NOT_SUPPORTED` |
| `hpc/phase6_dynamic_dual_graph/` | P6 dual graph | DEC-029 | CLOSED, `DUAL_GRAPH_S1_FAIL` |
| `hpc/regime/` | Pre-Q7 France regime/V6/V7 architecture search | predates DEC log | HISTORICAL, superseded by Q7 (Phase 3E) |
| `hpc/archive/`, `hpc/research/` | Older/exploratory scripts | Mixed | HISTORICAL — check phase name against decision log before reuse |

**Note (graph-temporal):** no dedicated `hpc/phase8_graph_temporal/` folder exists; the
S1-FR graph-temporal job ran via `src/modeles/run_s1_fr_local.py` (local, not a Slurm
HPC submission) — `S1_FR_FAIL` (DEC-031) closed the branch before any HPC array was
authorized.

## 3. HPC results — valid, cited in current canonicals

| Path | Job | Result |
|---|---|---|
| `hpc_results/herald_regime_phase3e_qtensor_arch_20260527_173259_r1` | Slurm 7398380 | Q7 selection (Phase 3E) |
| `hpc_results/herald_regime_phase2r_confirmatory_20260526_2r_confirm_r1_r1` | — | Phase 2R confirmatory (L5_trainopt vs reference, p=0.0028) |
| `hpc_results/herald_phase4n_a_local_r1` | local | Phase 4N persistence LOCO baseline (DEC-006) |
| `hpc_results/herald_phase4e_b_{fr,nl,be,pt}_20260603_131640_r1` | local | Phase 4E-B per-country causal baseline (DEC-002; FR 0.1031/NL 0.1017/BE 0.1488/PT 0.2286) |
| `hpc_results/herald_phase4o_b_spatial_r1`, `herald_phase4o_c_spatial_r1` | — | Italy residual spatial autocorrelation, `SUPPORTED` (DEC-007) |
| `hpc_results/phase7_pt_municipal/` | 7472757 | PT Municipal Phase 7, `PT_MUNICIPAL_PHASE7_COMPLETE` (DEC-064) |
| `hpc_results/phase7_nl_gemeente_proxy/` | 7475756 | NL gemeente proxy run — outputs exist but are **BLOCKED** (DEC-065), not a valid relation-label source |
| `data/processed/sector_precedence_results/` (Phase 7 HPC outputs land in `data/processed/`, not `hpc_results/`) | 7455266 | Original Phase 7 (DEC-034) |

## 4. HPC results — rejected (closed branches, do not use as input to anything new)

| Path | Job | Verdict |
|---|---|---|
| `hpc_results/herald_phase4p_it_spatial_lag_r1`, `_r2` | — | `REFUTED_UNDER_CURRENT_PROTOCOL`, p=0.19 (DEC-008) |
| `hpc_results/herald_phase4q_it_spatial_durbin_r1` | — | `REFUTED_UNDER_CURRENT_PROTOCOL`, p=0.32 (DEC-009) |
| `hpc_results/herald_phase4h_b_20260608_223045_r1` | 7434844 | `NOT_SUPPORTED` (graph-transfer hypothesis rejected) |
| `hpc_results/herald_phase4i_a_20260609_113632_r1` | 7439835 | Both admission gates FAIL — Phase 4I-B never launched |
| `hpc_results/dual_graph_s1/` | 7453691 | `DUAL_GRAPH_S1_FAIL`, all 7 criteria fail (DEC-029) |

## 5. HPC results — historical/superseded (predate causal-leakage fix or Q7 selection)

| Path | Notes |
|---|---|
| `hpc_results/herald_phase4_{be,nl,pt}_*` (2026-05-28/29) | Pre-leakage-fix Phase 4A/4B/4C runs — **WMAPE invalid as scientific baseline** (DEC-001) |
| `hpc_results/herald_phase4c_*`, `herald_phase4d_*` | Phase 4C/4D graph experiments — superseded, "adding graph complexity is not the path forward" finding |
| `hpc_results/herald_phase4e_a_*` (pre-4E-B) | Intermediate Phase 4E-A/A2, superseded by Phase 4E-B as the per-country baseline |
| `hpc_results/herald_phase3c_*`, `herald_phase3d_*` | Pre-Q7 labor-tutor/q_tensor search, superseded by Phase 3E |
| `hpc_results/herald_regime_discovery_20260527_115507`, `herald_regime_phase2j_fair_flag_*` | Pre-Q7 regime-discovery battery (Phase 2) |
| `hpc_results/herald_v6_observed2025_20260430_142920`, `herald_semi_total_253_geo2025` | Pre-Q7 V6/Semi training runs |
| `hpc_results/final_model_comparison_20260429` | Pre-Q7 model comparison, partial/failed per its own folder name |
| `hpc_results/imported_from_vm_20260501` | Raw imported artefacts, provenance not independently re-verified in this pass |
| `hpc_results/smoke_phase4*` (all `smoke_*` folders) | Smoke-test-only runs, liveness checks not scientific results |

## 6. Logs / raw outputs (regenerable, not a primary source)

Per-job `.out`/`.err`/raw `.npz`/`.csv` files inside any `hpc_results/*/` folder are
gitignored except small tracked JSON/manifest/README files (per `.gitignore`). These
are evidence of execution, not a substitute for the DEC-* entry that interprets them.

---

## Cross-reference

- Machine-readable phase registry: `hpc/hpc_phase_registry.json`
- Code that produced these results: `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
- Decision-level interpretation: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
