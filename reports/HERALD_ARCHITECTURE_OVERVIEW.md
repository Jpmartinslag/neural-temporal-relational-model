# HERALD Architecture Overview

**Created:** 2026-06-18 (consolidation/freeze pass).
**Status:** Documentation only — no scientific result, claim, or number in this file is new;
everything here is a restatement of what is already frozen in
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` and `reports/HERALD_PROJECT_CHARTER.md`.
If this document and the decision log ever disagree, the decision log wins.

---

## 1. Architecture diagram

```
                         ┌────────────────────────────┐
                         │   1. Données territoriales   │
                         │  pays × territoire × secteur │
                         │           × année             │
                         └──────────────┬────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
   ┌──────────────────┐      ┌──────────────────────┐   ┌──────────────────────┐
   │ 2. Prévision      │      │ 3. État économique     │   │ 4. Relations          │
   │    locale          │      │   (label descriptif)   │   │   sectorielles         │
   │ persistence/Ridge  │      │ growth/stability/      │   │ précédence temporelle  │
   │ AR(1), causal,      │      │ decline/recovery        │   │ signée, lag-1,         │
   │ rolling-origin      │      │ (+accel/decel/stagn.)   │   │ bootstrap/permutation  │
   └─────────┬───────────┘      └───────────┬─────────────┘   └───────────┬────────────┘
             │                              │                             │
             └──────────────┬───────────────┴──────────────┬──────────────┘
                             ▼                              ▼
                  ┌────────────────────┐         ┌─────────────────────────┐
                  │ 5. Niveau d'évidence │         │  [research track, not   │
                  │ observed/proxy/      │         │   wired to dashboard]   │
                  │ robust/supported/    │         │  SharedRelationEncoder  │
                  │ exploratory/blocked  │         │  (synthetic-validated,  │
                  └──────────┬────────────┘         │  real-data PARTIAL)     │
                             │                       └─────────────────────────┘
                             ▼
                  ┌────────────────────────┐
                  │ 6. Signaux pour la       │
                  │    décision (Observatory)│
                  │ — visualisation, jamais  │
                  │   causale, jamais une    │
                  │   recommandation          │
                  └──────────┬───────────────┘
                             │
                             ▼
                  ┌────────────────────────┐
                  │ FUTURE — Bloco 3:        │
                  │ Recommandation            │
                  │ NOT STARTED, requires     │
                  │ Bloco 1+2 complete         │
                  └────────────────────────┘
```

This mirrors the 6-stage / 4-component diagram already built into the v0.5.1
dashboard ("Méthode HERALD" — données territoriales → prévision locale → état
économique → relations sectorielles → niveau d'évidence → signaux pour la
décision; components: base statistique / couche relationnelle-candidats /
validation / sortie). The diagram above adds the explicit branch showing that
the neural relational-candidate research track exists but is **not wired
into** the current Observatory output.

---

## 2. Component-by-component explanation

### 2.1 Data
Country × territory × sector × year panels. Three observed sources (FR
ZE2020, PT Municipality continental, NL COROP) feed the relation graph and
training labels. One proxy source (NL Gemeente, disaggregated from COROP by
establishment-stock share) feeds territorial visualization context only —
explicitly excluded from relation labels per DEC-065. PT/IT/AT form a
separately harmonized Path H panel for LOCO forecasting only (no sector
graph). See `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` for the full
evidence-source boundary rules.

### 2.2 Forecast
Causal rolling-origin persistence and Ridge/AR(1). This is **plain
statistics**, not a learned/neural model: `forecast[t] = value[t-1]` for
persistence, or a ridge-regularized linear regression on lagged features for
Ridge. Validated as the best LOCO baseline for PT/IT/AT (DEC-006); PT
municipal-grain forecast closed the same way, with an explicit leakage
assertion that every forecast value equals the prior year's observed value
(DEC-068). France's HERALD Q7 (a richer regime-learner architecture,
WMAPE 0.0204) is PENDING_REAUDIT and not part of this causal-baseline family
for headline claims.

### 2.3 Economic states
Deterministic, rule-based labels computed directly from the observed series
(no model, no prediction): growth / acceleration / deceleration / stagnation
/ decline / recovery / possible sectoral emergence (per Charter §2.2). These
are descriptive facts about the past, not forecasts, unless explicitly paired
with an uncertainty interval and labelled as such.

### 2.4 Sector→sector relations
Phase 7 sector-precedence method: signed lag-1 regression, bootstrap/
permutation-validated, BH/FDR-corrected, pre-registered thresholds
(`|β|≥0.10` original; `|β|≥0.09` fine-grain-supported with extra evidence;
`0.07-0.09` exploratory-only per DEC-066). This is **simple statistics**
(linear regression + resampling), not a neural model. 20 observed edges
total (FR=9, NL COROP=8, PT Municipal=3) feed the relation graph in all
Observatory dashboards. Language is restricted to "association" / "predictive
precedence" — never "causes" or "structural causality" (Charter §2.4,
re-verified by automated test in every dashboard's test suite).

### 2.5 Validation
Every promoted relation passes: bootstrap stability (bss), permutation
p-value, BH/FDR correction across all tested pairs, and (for fine-grain
tiers) an additional COVID-robustness or cross-window/cross-country
replication check. The NL gemeente proxy's apparent 121 promoted edges were
**rejected on validation grounds** (DEC-065) after a structural diagnostic
found the proxy method itself injects a spurious cross-sector correlation —
this negative result is itself a validated methodological finding, not a
gap.

### 2.6 Dashboard ("Observatory")
Self-contained HTML files (Plotly embedded locally, no CDN dependency except
GSAP for timeline animation) built by deterministic Python builder scripts
from the validated exports above. v0.4/v0.4.1 are the stable, scientifically
complete, historical baseline. v0.5 added a layperson narrative layer but was
rejected as a polished MVP. v0.5.1 (current) is the same v0.4 evidence,
re-shaped into French, with the architecture diagram first, real geographic
heatmap, and the relation graph wired to filter the map. No dashboard
recomputes a scientific number — they all consume the already-validated
exports.

### 2.7 Recommendation (future)
Not implemented. Requires Bloco 1 (forecasting) + Bloco 2 (graph/relations)
complete per the Charter. An old `HERALD_INTELLIGENCE_LAYER_SPEC.md` exists
as a structural reference only (ARCHIVED status in the artifact registry) —
its rankings, if ever reused, are opportunity hypotheses, not validated
recommendations, and its old fixed weights must not be promoted.

---

## 3. What the neural/relational layer has actually demonstrated (verified against the decision log, not overstated or understated)

- **Useful on synthetic data:** the `SharedRelationEncoder` (DEC-055) achieves
  in-sample AUC=0.960 and unseen-pair AUC=0.690 on a controlled synthetic
  benchmark with known ground-truth relations — better than the earlier
  per-pair `GraphRelationHead`, which only memorized (OOS AUC=0.529).
- **Partial on real data:** validated against real FR/NL/PT data (DEC-056),
  then fine-tuned with Phase 7 weak labels (DEC-058/059). Sign concordance
  ranges 0.438 (zero-shot) to ~0.667 (best fine-tuned variant, valid folds
  only) — better than chance but not strongly above several negative
  controls (DEC-059 found 4 of 7 controls within 0.05 of the best variant).
  No robust cross-country replication; COVID/window sensitivity unresolved;
  0 abstentions in any run (every pair gets a score, none flagged
  `INSUFFICIENT_EVIDENCE` even where evidence is thin).
- **NOT a final claim.** DEC-059's own verdict is `REAL_WEAK_LABEL_TUNING_PARTIAL`.
  This research track is informative and worth continuing, but it does not
  feed any current Observatory dashboard — the v0.5.1 dashboard explicitly
  and correctly states, in its own UI text, that no neural candidate-relation
  dataset exists in this repository for real data today.
- **Closed branches under this same broad "graph" umbrella, for clarity:**
  the *geographic* graph (queen-contiguity spatial lag, Phase 4P/4Q) and the
  *dynamic dual* graph (P6_DDEG_S1) both failed their respective gates and
  are unrelated architecturally to the SharedRelationEncoder line above —
  they tested whether graph structure improves the **forecast**, not whether
  it can detect **relations**, and are closed for different reasons.

---

## 4. What is simple statistics (no learned/neural component)

- Persistence baseline: `value[t] = value[t-1]`.
- Ridge/AR(1): linear regression with L2 regularization on lagged features,
  fit per country (and now per PT municipality forecast run), rolling-origin
  validated.
- Phase 7 sector precedence: linear lag-1 regression + bootstrap/permutation
  + BH/FDR. No neural network anywhere in this pipeline.
- Phase 8 territorial influence decomposition: leave-one-territory-out (LOTO)
  beta decomposition — still linear regression arithmetic, not a model.
- Economic state labels: rule-based thresholds on observed growth rates.

All currently-promoted, currently-cited scientific results in this repository
are produced by one of the methods above. The only place a trained neural
model appears is the synthetic/real relation-learning research track in §3,
which is explicitly not part of any current dashboard or headline claim.

---

## 5. What feeds the dashboard

```
granular_territory_state_panel.csv  ─┐
granular_relation_edges.csv          ├─→ build_observatory_v04_dashboard.py ──→ v0.4/v0.4.1 dashboard
blocked_proxy_edges.csv             ─┘

(v0.4 exports above) + herald_observatory_v03_panel.csv (FR/NL forecast)
  ─→ build_observatory_v05_narrative_exports.py ──→ build_observatory_v05_narrative_dashboard.py ──→ v0.5 dashboard (superseded)

(v0.4 exports) + v0.3 forecast + pt_municipal_phase7_panel.csv (new PT forecast, DEC-068)
  ─→ build_pt_municipal_prediction_layer.py
  ─→ build_observatory_v051_narrative_exports.py
  ─→ build_observatory_v051_narrative_dashboard.py (+ _template.py)
  ──→ v0.5.1 dashboard (current)
```

No dashboard builder recomputes a scientific number from raw data directly —
every builder consumes already-validated, already-tested exports from an
earlier stage. This chain is enforced by fail-closed asserts in each builder
(e.g. "GEMEENTE_PROXY never appears in relation_edges") and re-verified by
the corresponding test suite on every run.

---

## 6. What's still missing

- **Recommendation layer:** 0% — not started, by design (requires Bloco 1+2 complete).
- **Visual (Playwright) validation:** never performed in this environment for
  any Observatory dashboard (v0.3 through v0.5.1) — all validation has been
  structural (DOM id / embedded JSON / handler cross-reference), not a real
  screenshot. This is an honest, repeated limitation, not unique to v0.5.1.
- **Modular, map-first dashboard architecture:** signalled by the product
  owner as the next direction, not yet started (see `CODEX_MEMORY.md` entry point).
- **Cross-country pooled relation training:** explicitly forbidden until a
  corrected NL gemeente proxy specification is validated (DEC-065) and until
  a concept-harmonisation DEC resolves the FR/NL/BE/PT target heterogeneity
  (Charter §5, "FR/NL/BE/PT targets are semantically heterogeneous").
  immediate.
- **Article/thesis writing:** no outline, no draft sections exist yet (see
  `reports/HERALD_CURRENT_STATE.md`, "Writing/article" row, ~5%).
- **Figures/tables for the article:** no figure-export pass has happened
  since Phase 8 — this is new work, not a re-run of an existing script.
