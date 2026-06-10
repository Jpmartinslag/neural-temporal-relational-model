# HERALD Codex Memory
Updated 2026-06-10 (Phase 4Q + strategic reorientation). Read first; verify drift with `rtk git status --short`.

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
PT 0.778 (8 sectors); temporal q=0.005, territory q=0.005, LOYO pass, COVID-robust.
3/3 countries pass, 2 required. Edges are Granger-predictive associations, not
structural economic causality. L4 mobility and L5 geography remain unvalidated.
Next: community detection baseline (task 2.8).
Artifacts: `data/processed/economic_graph/g1_l2_cogrowth/`; `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`.
See `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md`.

### Bloco 3 — Economic Recommendation (NOT STARTED)
Terminal use case. Requires Bloco 1 + Bloco 2 complete.
Cannot be claimed as a current capability.

## Documents créés/révisés 2026-06-10
- `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — DEC-001 to DEC-019 (DEC-018: PT KZ exclusion; DEC-019: L2 PASS)
- `reports/HERALD_EVIDENCE_MATRIX.md` — 24 claims (G-10 added: L2 SUPPORTED), all classified
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` — G0→G6→Bloco 3; dashboard section added
- `reports/HERALD_RESEARCH_GANTT.md` — Gantt with DATE_LIMITE_A_CONFIRMER; task 4.4 updated
- `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md` — ≥30 works
- `reports/bibliography/HERALD_REFERENCES_MASTER.md` — 25 refs, 9 axes
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

## HPC
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
