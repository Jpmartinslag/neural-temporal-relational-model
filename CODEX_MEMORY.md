# HERALD Codex Memory
**LEIA PRIMEIRO.** Updated 2026-06-12 (DEC-036: geographic dashboard, derived windows, France ZE documentation).
Read this file, then verify drift with `rtk git status --short`.

## Quick orientation (start here)
- **Direction:** `reports/HERALD_PROJECT_CHARTER.md` — official scope, permitted/forbidden claims, frozen decisions.
- **Current state by component:** `reports/HERALD_CURRENT_STATE.md` — completion %, blockers, next step.
- **All decisions:** `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-036).
- **Claims classification:** `reports/HERALD_EVIDENCE_MATRIX.md`.
- **Active document list:** `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`.
- **Artefact manifest:** `reports/herald_artifact_registry.json`.
- **S1_FR_FAIL (DEC-031):** GConvGRU and EvolveGCN-H fail all 5 frozen gate criteria on France (GConvGRU WMAPE 0.064922 vs Ridge 0.064856; p_temporal=1.0). Graph-temporal prediction branch CLOSED. No HPC authorized.
- **Observatory exports:** aggregate PT/IT/AT v0.1.1 (1,963 rows); sector FR/NL/PT v0.2 (45,945 rows) via `build_observatory_export.py`; Observatory v0.3 (45,945 rows + sector relations) via `src/data/european_panel/build_observatory_v03.py`.
- **Phase 7 result (DEC-034):** SECTOR_PRECEDENCE_PROTOTYPE_READY — 12 COVID-robust edges (NL=3, PT=9); 25 total promoted main edges. Slurm 7455266, meso. Audit PASS.
- **Observatory v0.3 (DEC-035):** Sector precedence layer integrated. ROBUST/MAIN_ONLY_EXPLORATORY classification. Dashboard: `reports/dashboards/herald_observatory_v03_dashboard.html`. Tests: 649 pass.
- **Immediate next step:** extend sector panel to AT/BE (pre-register hypothesis first); report writing (Phase 6).

## DO NOT change direction without a new DEC-* entry
No new GNN architecture search. No geographic graph reopen. No P6 relaunch.
P6 sector-edge CSV (`data/processed/dual_graph_s1/learned_sector_edges.csv`) is **INVALID_FOR_INTERPRETATION** — wrong sector names, see Charter §6 and DEC-030.

## Rules
- Repo `/home/jpdark/Downloads/project_recomm/dataset`.
- Prefix shell commands `rtk`; raw Python/SSH/rsync: `rtk proxy <command>`.
- Dirty worktree: never reset/revert unrelated changes. Exclude raws, `hpc_results/`, large generated artifacts from commits.
- Branch `main`; use `rtk git rev-parse HEAD` and `rtk git rev-parse origin/main`
  to verify the current revision instead of storing a commit hash here.
- Forecast `t` uses data available through `t-1` only.
- Phase 4A/4D metrics are legacy/leaky (`growth_1y[t]` used `target[t]`). Scientific baseline starts at causal Phase 4E.

## Scientific state
Goal: frugal territorial enterprise-birth forecasting. Design: strong
persistence/AR-Ridge base + low-capacity residual correction + graph only if it
adds out-of-sample value. Forecasting now; recommendation/policy claims later.

Original targets differ: FR `establishment_creation`; NL `local_unit_opening`;
BE `vat_first_registration`; PT `enterprise_birth`. Their cross-country mean
does not prove European generalization. Path M = heterogeneous multitask,
primary metrics per country. Path H = harmonized target.

Harmonized Path H: PT 23 + IT 93 + AT 35 stable mainland NUTS3, 2008-2020,
151 regions, total demographic `enterprise_birth`.
Panel: `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv`.

## Results
Phase 4N LOCO: persistence balanced WMAPE ~0.0939; Ridge ~0.0969.
Residual/mix not promoted. Direct Ridge has cross-country target-scale mismatch.
See `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`.

Phase 4O-C: Moran's I + BH/FDR q=.05 + 999 permutations + 999 graph controls
`P W P^T` + leave-one-region-out.

Critical correction: causal years qualify only when every region has its own
past-residual scale (`region_mad`/`region_std`). Country fallback is descriptive
only: one common scalar leaves Moran's I unchanged from absolute residuals.

Final gate:
- IT PASS: robust relative + causal spatial residual signal.
- PT FAIL: relative signal fails strict LOO; early causal years use fallback.
- AT FAIL: signal mainly absolute, possibly heteroscedasticity.
- Multi-country Phase 4P NOT authorized: 1/3; threshold 2/3.
- Italy-only linear spatial-lag diagnostic was authorized; no
  GNN/generalization claim.

Phase 4P Italy-only rolling-origin result (`r2`, canonical):
- Persistence mean yearly WMAPE 0.054946.
- Residual Ridge 0.056204.
- Real queen-neighbour lag 0.056185.
- Permuted-graph median 0.056242; 18/99 controls tie/beat real, empirical p=.19.
- Real graph wins vs persistence 4/9 years and vs residual Ridge 4/9.
- Mean residual Moran does not fall: absolute 0.116848 -> 0.121740; relative
  0.264240 -> 0.269176.
- Phase 4P FAIL. Reject tested `W × births[t-1]` feature. Keep persistence.
- Post-run audit gate now explicitly requires >=1% gain vs persistence and
  no-graph Ridge, graph-control p<=.05, >=5/9 yearly wins, and worst-year
  regression <=10%. Do not call these thresholds pre-registered for 4P; use
  prospectively. Current FAIL is unchanged under the original weaker gate.
- Do not launch Italy graph training, multi-country Phase 4P, STGNN, or HERALD
  from this result.

Validation: 46 repo tests pass (`python3 -m pytest -q tests`); causal audit
passes; deterministic; Phase 4P `git diff --check` clean. Root-wide pytest
collects vendored `tools/external/graphify/tests` and fails on 26 unrelated
package-import collisions.

Key files:
- `hpc/phase4/run_phase4n_harmonized_loco.py`
- `hpc/phase4/run_phase4o_c_residual_spatial_diagnostic.py`
- `hpc/phase4/audit_phase4o_b_results.py`
- `hpc/phase4/run_phase4p_italy_spatial_lag.py`
- `tests/test_phase4o_spatial.py`
- `tests/test_phase4p_italy_spatial_lag.py`
- `reports/HERALD_PHASE4M_COMMON_FEATURE_CONTRACT.md`
- `reports/HERALD_PHASE4M_PT_IT_AT_PANEL_AUDIT.md`
- `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`
- `reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md`
- `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md`

## State as of 2026-06-10 (Phase 4Q complete)

Phase 4Q fixed Italy Spatial-Durbin block: gate FAIL (p=.32, −5.95% vs persistence).
Geographic queen-contiguity branch CLOSED under 2008-2020 data.
Do NOT launch STGNN/HERALD graph training or multi-country Phase 4P.
Reopen only with: new harmonized country, justified functional/mobility network, or revised data window.

## New strategic direction (2026-06-10)

Three scientific tracks, in priority order:

### Bloco 1 — Temporal Forecasting (active, no architecture restart)
- Persistence is best LOCO baseline. No model promoted for PT/IT/AT LOCO.
- Permitted: non-graph frugal country-specific improvements; conformal intervals.
- Forbidden: STGNN, neural graph, multi-country Phase 4P.

### Bloco 2 — Dynamic Economic Graph (L3 FR/NL PASS; L1 FAIL; L2 FR/NL/PT PASS)
New scientific question: what sector-territory economic relations exist and evolve?
NOT about improving forecast accuracy (that question was answered: geographic graph FAIL).
Role: represent relations, track evolution, detect growth/crisis/stagnation, explain dynamics.
The formal contract is `reports/HERALD_G0_FORMAL_CONTRACT.md` (10/10).
G1-L3 territory-structure projection passed for FR/NL with temporal and
territory-label nulls, FDR, leave-one-year-out and bootstrap stability. PT is
excluded from nine-sector gate because KZ has zero mass in every territory/year.
PT KZ audit (DEC-018): INE indicator 0009703 never includes section K; verified
definitional exclusion per Eurostat/OECD enterprise demography convention.
G1-L1 RCA co-specialization failed the common gate (NL pass, FR fail, PT ineligible).
G1-L2 same-sector cross-territory co-growth PASSED (DEC-019): FR 0.782, NL 0.789,
PT 0.778 (8 sectors); temporal q=0.005, territory q=0.005, LOYO pass.
COVID_ROBUST (DEC-020): all 3 pass full gate with 2020 excluded from windows
(eval_year=2020 retained; its window covers pre-COVID years 2015-2019).
COVID stability: FR 0.744, NL 0.762, PT 0.738 — all still pass.
3/3 countries pass, 2 required. Edges are statistical co-movement
associations, not Granger predictability or structural economic causality.
L2 builder corrected bugs: (1) eval_year exclusion removed; (2) bootstrap
propagates exclude_years; (3) full 4-criterion gate applied to COVID run.
27 tests pass. Second run confirms determinism.
Corrected community baseline (DEC-021): FAIL 0/3. Symmetric top-k=5 graphs,
valid temporal/territory series nulls, equal Louvain budget, modularity+AMI
BH/FDR. Some AMI signal survives, but modularity is reproduced by nulls.
L4 mobility and L5 geography remain unvalidated.
Artifacts: `data/processed/economic_graph/g1_l2_cogrowth/`; `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`.
HPC spec: `reports/HERALD_PHASE5_HPC_SPEC.md` (DEC-022). Community failure
does not invalidate L2.
**Phase 5 ablation v3 (NL, 2021-2023, 5 seeds, widths (2,)(4,)(8,)(16,8)): NOT_SUPPORTED.**
Two root-cause fixes before ablation:
  1. `message_pass_1hop` self-value fallback for isolated regions (OQ sector: zero edges
     t=2012-2019 → h=NaN for all 40 NL regions).
  2. Column-mean imputation in `predict_neural_corrector` for sectors with missing growth
     data (OQ t=2011-2016: all-NaN → imputed from t=2017-2020 means, training only).
     n_train: 39 → 440 for eval=2021.
Best H2-neural (width=(8,)): 5.53% vs H0b 3.41% (62% regression), vs H1=5.14% (H2 WORSE).
H2 beats permuted controls (6.34%, 5.94%) confirming graph specificity, but fails regression
gate (H2>H0b×1.1=3.75%) and fails to beat H1-neural. NOT_SUPPORTED all widths.
Linear correctors also fail: H2-linear=5.56% vs H0b=3.41%.
Conclusion: L2 co-growth graph does NOT improve territorial forecasting over AR-Ridge.
H0b remains best; all corrector branches closed.
65/65 tests pass. 15/65 tests updated (zero-edge semantics, self-value fallback).
See `reports/HERALD_PHASE5_HPC_SPEC.md` (status: NOT_SUPPORTED).
DEC-023 added to decision log.

**G2 Preflight (2026-06-10): descriptive findings valid.**
Script: `src/data/european_panel/build_g2_temporal_preflight.py`. 42+1 tests pass.
Artefacts: `data/processed/economic_graph/g2_preflight/` (compact, no raw edges).
Preflight findings (FR/NL/PT, top-k=5, criteria pre-registered per DEC-024):
- LOYO Pearson: 0.10-0.19; LOYO Jaccard: 0.07-0.26 — all FAIL ≥0.70 stability threshold
- Persistent edges (≥70% years): 0.4% — highly transient; turnover 59%/yr
- COVID: no measurable step-change in density or weight

**G2 Corrected controls (DEC-024c, 2026-06-11): COMPLETE.**
Module: `src/data/european_panel/build_g2_corrected_controls.py`. 25 tests pass.
Source: `sector_panel_fr_nl_pt.csv`. 199 perms N1 (temporal) + 199 perms N2 (row-wise territory).
Seeds: N1=42, N2=137. COVID: obs_year=2020 excluded from windows; eval_year=2020 retained.
N2 column permutation verified DEGENERATE for M1/M2 Jaccard (null std=0, p=1.0 always).
Metrics: M1 consecutive Jaccard · M2 mean pairwise Jaccard · M3 LOYO observed only (null BLOCKED).

Verdicts:
- Corrected COVID comparison (DEC-024d): FR 9/9 with and without obs-year
  2020 (`COVID_ROBUST`); NL 4/9→5/9 and PT 4/8→0/8
  (`COVID_SENSITIVE`). The 2/3 gate passes with different country pairs, so
  there is no robust two-country replication.
- G2_EDGE_STABILITY_NOT_SUPPORTED — M2 0.06-0.26, far below 0.70 threshold; 0/3 countries.
- PT: 0/8 sectors significant → temporal signal not validated for PT.
- M3 LOYO observed: FR 0.287 · NL 0.500 · PT 0.578. Null BLOCKED.
- G-13: PARTIALLY_SUPPORTED; inferential aggregate claim robust only for FR.

Prior control (commit cc48924) INVALID: permuted pre-computed edge weights — p=0.005/26/26 invalid.
Language: "associação estatística temporal observada", NOT causal attribution.
No individual edge claims. No cross-country pooling. No recommendation.

**G2 Aggregate Dynamics (DEC-025, 2026-06-11): COMPLETE.**
Module: `src/data/european_panel/build_g2_aggregate_dynamics.py`. 45 tests pass.
Source: `sector_panel_fr_nl_pt.csv`. 321 annual metric rows. Pair-resampling
sensitivity intervals use 200 draws; they are not confidence intervals because
territory pairs share nodes.
Artifacts: `data/processed/economic_graph/g2_dynamics/` (7 CSVs/JSONs + 16 figures).
Findings:
- FR: density Δ < 0.001, weight Δ < 0.01, turnover 79%. COVID_ROBUST.
- NL: density +0.006, weight +0.011, turnover 59%. COVID_SENSITIVE.
- PT: density +0.001, weight +0.048 (RU/MN sectors Δ > 0.13), turnover 51%. COVID_SENSITIVE.
- G-14 SUPPORTED as a descriptive computed statement.
  G2_CROSS_COUNTRY_REPLICATION_NOT_SUPPORTED.
- FR_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED.
Period `2020` means a five-year rolling graph ending in observation year 2020
(available at eval_year=2021), not a graph based only on 2020.
Next: G4-G5 explanation/visualization.
Reports written: HERALD_G2_REPORT_SECTION_FR.md, HERALD_G2_REPORT_FIGURE_SELECTION.md, HERALD_G2_DASHBOARD_INTEGRATION_SPEC.md
No dashboard modification (DEC-014). No HPC, GNN, recommendation.

**Graph-temporal tensor preflight and E0 smoke (DEC-027): E0_STATIC_SNAPSHOT_PASS (reclassified).**
**Graph-temporal schema 2.0 and E0-v2 smoke (DEC-028): E0_V2_PASS (2026-06-11). CLOSED.**
**FR adjacency audit (DEC-028): FR_ADJACENCY_READY (2026-06-11).**
**A1 implementation contract: FROZEN (DEC-028, 2026-06-11).**
- EconoGNN: `REFERENCE_ONLY`; dynamic observed trade graph, different task,
  scale and evaluation; public GitHub incomplete.
- A0 remains country-specific AR/Ridge.
- A1 candidates: low-capacity GConvGRU (A1a) and EvolveGCN-H (A1b) over per-year causal L2.
- A0-neural (GRU without message passing): equal-capacity control — mandatory for S1-FR.
- All candidates predict the same territorial total; sector births are graph
  features, not a separate target.
- NL is engineering smoke only (COVID-sensitive). FR is first scientific local
  test because only FR is robust under both G2 COVID scenarios.
- E0_V2_PASS: 13.92s runtime, 0.035 GB RSS delta, 57/57 tests, zero leakage,
  zero mask errors, deterministic outputs. Schema 2.0 corrects 5 schema 1.0 defects.
- Schema 2.0 tensors: `data/processed/graph_temporal_v2/` — 3 NL folds,
  features_seq (5,40,9,3), adjacency_seq (5,9,40,40). Canonical H0b Ridge
  (corrector.py port), per-feature masks, positive_topk adjacency.
- Schema 1.0 tensors: `data/processed/graph_temporal_preflight/` — SUPERSEDED
  by schema 2.0; kept for audit trail only.
- FR adjacency (5 eval years 2021–2025): 280 ZE, 9 sectors, 0 isolated nodes at k=3/5/10,
  1 connected component (all years), perfect symmetry, 26–39% raw negative correlations.
  All 8 fail-closed criteria pass. Tensors ready for GConvGRU/EvolveGCN-H.
- A1 contract: interface (B,T,R,S,F), bounded residual head (clamp_frac∈{0.10,0.15}),
  masked pooling, ≤5,000 params, shared weights across sectors, 11 mandatory tests in
  `tests/test_graph_temporal_a1.py`, 5 seeds {42–46}, rolling-origin folds, masked WMAPE loss.
- Evidence matrix: 33 claims; SUPPORTED=11, PARTIALLY_SUPPORTED=3, NOT_SUPPORTED=5,
  NOT_TESTED=4, REFUTED=8, PENDING_REAUDIT=1. G-17 added (S1_FR_FAIL). MET-05 updated REFUTED.
- **S1_FR_FAIL (DEC-031)**: FR scientific local test COMPLETED — GConvGRU and EvolveGCN-H
  fail all gate criteria. Graph-temporal prediction branch CLOSED. HPC NOT authorized.
- Adjacency audit (NL): 29–36% negative correlations; 0–1 isolated regions at
  k=5 (NL/2019 is sparse: 40 isolated across one sector). Primary repr: positive_topk.

**Branch CLOSED.** S1_FR_FAIL confirmed and committed (DEC-031). No A1 implementation outstanding.


### Bloco 3 — Economic Recommendation (NOT STARTED)
Terminal use case. Requires Bloco 1 + Bloco 2 complete.
Cannot be claimed as a current capability.

## Documents créés/révisés 2026-06-11 (DEC-027 tensor + E0)
- `src/data/european_panel/build_graph_temporal_preflight.py` — causal tensor builder
- `src/modeles/run_e0_smoke_nl.py` — E0 engineering smoke (NL, 3 eval years)
- `tests/test_graph_temporal_preflight.py` — 33 tests, 18 methodological invariants
- `data/processed/graph_temporal_preflight/` — 3 NL fold artifacts + manifest
- `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` — E0_STATIC_SNAPSHOT_PASS (reclassified)

## Documents créés/révisés 2026-06-11 (DEC-028 schema 2.0 + FR adjacency + A1 contract)
- `src/data/european_panel/build_graph_temporal_v2.py` — schema 2.0 tensor builder + CLI
- `src/modeles/run_e0_smoke_nl_v2.py` — E0-v2 smoke harness (RSS, 8 checks, E0_V2_PASS)
- `tests/test_graph_temporal_v2.py` — 24 schema 2.0 tests (T19–T42)
- `data/processed/graph_temporal_v2/` — 3 NL + 5 FR fold NPZs + manifest_v2.json
- `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md` — E0_V2_PASS audit
- `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md` — FR_ADJACENCY_READY (280 ZE, 5 eval years)
- `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md` — FROZEN A1 spec
- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — DEC-028 appended
- `reports/HERALD_EVIDENCE_MATRIX.md` — MET-06 added; 32 claims; SUPPORTED=12

## Documents créés/révisés 2026-06-10
- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — DEC-001 to DEC-027
- `reports/HERALD_EVIDENCE_MATRIX.md` — 31 claims (G-10: L2 SUPPORTED; G-11: community NOT_SUPPORTED), all classified
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` — G0→G6→Bloco 3; dashboard section added
- `reports/HERALD_RESEARCH_GANTT.md` — Gantt with DATE_LIMITE_A_CONFIRMER; task 4.4 updated
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md` — ≥30 works
- `reports/bibliography/HERALD_REFERENCES_MASTER.md` — 25 master refs, 9 axes; EconoGNN verified
- `reports/bibliography/herald_graph_temporal_references.bib` — 22 architecture/evaluation sources
- `reports/bibliography/herald_references.bib` — BibTeX; Friedman 2008 VERIFIED_PRIMARY
- `reports/bibliography/HERALD_REFERENCE_AUDIT.csv` — audit table; Friedman 2008 VERIFIED_PRIMARY

**Dashboard (DEC-014):**
`reports/dashboards/herald_france_final_dashboard.html` = base visuelle officielle.
Pas de nouveau dashboard from scratch. Adaptation incrémentale uniquement
après validation de L3, L2 (et L1 si récupéré). L3 PASS + L2 PASS sont maintenant validés.
Ne pas modifier ce fichier ni générer un nouveau HTML avant autorisation explicite.

## Claims gate
Permitted: persistence best baseline PT/IT/AT LOCO; Italian residual spatial autocorrelation robust; geographic lags rejected; FR/NL/BE/PT targets heterogeneous.
Prohibited: recommendation, geographic graph improves forecast, cold-start LOCO, universal generalization, attention = explanation, Granger = structural causality.

## HPC Taxonomy (2026-06-12)

Index: `hpc/HPC_PHASE_INDEX.md`. Registry: `hpc/hpc_phase_registry.json`.

| Phase | Dir | Status |
|---|---|---|
| P2P3_REGIME_FRANCE | `hpc/regime/` | frozen |
| P4_GEO_GRAPH (4P/4Q FAIL, closed) | `hpc/phase4/` | frozen |
| P5_FIXED_GRAPH_CORRECTOR | `hpc/phase5/` | NOT_SUPPORTED |
| **P6_DDEG_S1 (frozen/FAIL)** | **`hpc/phase6_dynamic_dual_graph/`** | **frozen/FAIL** |

**P6_DDEG_S1:** Dynamic dual economic graph, France NUTS3, 5 folds × 11 controls × 5 seeds = 275 HPC jobs.
Full study complete — job 7453691, 275/275 COMPLETED, 0 FAILED.
Gate: **DUAL_GRAPH_S1_FAIL** — all 7 criteria fail. Predictive dual-graph branch CLOSED. Do not relaunch.
C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%) and C2_no_graph 0.1329 (+7.2%). Seed Jaccard 0.3353 (threshold 0.50).
Descriptive: named-edge artefact INVALID_FOR_INTERPRETATION (sector label mapping unverifiable); index-based stability not predictively validated.
Key artifacts: `data/processed/dual_graph_s1/gate_result.json`, `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`,
`reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md`. Status in registry: frozen/FAIL (DEC-029).

## HPC Connection
SSH alias `meso`: host `hpc2.mesocentre.uca.fr`, user `jpmartinsd`, ProxyJump
`mesoext`. Remote:
`~/project_recomm_herald_v6_2025_20260430/dataset`.

Manual sync:
```bash
rtk proxy rsync -av hpc/phase4/ meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc/phase4/
rtk proxy ssh meso 'cd ~/project_recomm_herald_v6_2025_20260430/dataset && squeue -u jpmartinsd'
rtk proxy rsync -av meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/OUT_ROOT/ hpc_results/OUT_ROOT/
```

Parallel Slurm jobs require `#SBATCH --constraint="mpi"` to avoid affected
`nompi` nodes. Next Italy diagnostic is cheap: local smoke/audit first; HPC only
if justified.
