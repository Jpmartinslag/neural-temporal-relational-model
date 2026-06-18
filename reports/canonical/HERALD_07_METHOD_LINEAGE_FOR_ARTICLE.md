# HERALD 07 — Method Lineage for the Article

**Created:** 2026-06-18 (canonical consolidation, second-level traceability map).
**Status:** Documentation only — narrative synthesis of `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
and canonicals #1-#4. No new claim is made here that isn't already in those documents.
If this narrative disagrees with the decision log, the decision log wins.
**Purpose:** explain the scientific line of reasoning behind HERALD's evolution, in
prose, as raw material for the article's introduction/discussion — not a new result.

**Language rules followed throughout:** "temporal precedence," "association," "evidence
tier," never "structural causality." The recommendation layer is referred to as a
*future decision layer* — planned, not implemented.

---

## Why did we start with territorial prediction?

Enterprise birth (new establishment creation) is a measurable, internationally
comparable proxy for territorial economic dynamism. It is not the only thing of
interest — the Project Charter is explicit that it is "one indicator," chosen because it
is harmonisable across countries, not because it is the sole objective. Starting with a
prediction layer also gave the project a falsifiable first question: can we forecast this
indicator better than a naive baseline, for a single country, before attempting anything
more ambitious (graphs, multi-country pooling, recommendation)?

## Why France / ZE2020?

France had the richest available institutional data (SIDE/SIRENE establishment-creation
records, URSSAF employment data) and a territorial grain — ZE2020 "Zones d'Emploi," 280
employment zones — that is economically meaningful (labour-market catchment areas) rather
than purely administrative. This let an architecture search (Phase 2/3) run against a
single, well-understood domain before generalizing. The result, HERALD Q7, reached WMAPE
0.0204 — but that number carries a standing caveat (`PENDING_REAUDIT`) because the causal
audit of its `growth_1y/2y` and `effectifs_lag1` features was not yet formally complete
when this consolidation was written. The lesson generalizes beyond France: **a strong
result is not citable as a headline claim until its feature pipeline has been causally
audited** — which is exactly what the next section is about.

## Why did we test European generalization?

A single-country result cannot support a claim about a "European territorial
intelligence system." Generalizing required two separable questions: (1) does the same
*target concept* exist elsewhere, and (2) does the same *model* transfer. Internationalizing
to PT/IT/AT/NL/BE answered both, and the answers diverged: target concepts turned out to
be **semantically heterogeneous** (France's établissement creation, NL's local-unit
opening, Belgium's first VAT registration, Portugal's enterprise birth are not the same
thing), while a much simpler model — persistence — turned out to transfer better than
anything more sophisticated, once leakage was fixed (see next section).

## What did the leakage finding teach us?

Early cross-country baselines (Phase 4A/4D) used a `growth_1y` feature computed with the
forecast target itself — a textbook information leak. Finding and fixing this (DEC-001)
did more than invalidate a set of numbers: it established a standing methodological
discipline for the rest of the project — every subsequent baseline had to be rebuilt
under a strictly causal, rolling-origin protocol, and every later architecture
(graph-temporal, dual-graph, SharedRelationEncoder) was held to the same standard before
any of its numbers could be trusted. The France Q7 PENDING_REAUDIT caveat exists precisely
because that same discipline had not yet been fully re-applied to the French pipeline.

## Why were several neural/spatial graphs rejected?

Three structurally different graph hypotheses were tested, each under a pre-registered,
fail-closed gate, and each failed on its own terms:

- **Geographic queen-contiguity** (Italy, Phase 4P/4Q): a spatial lag and a Spatial-Durbin
  block both failed to beat persistence, and neither beat topology-randomized controls
  (p=0.19, p=0.32). The geographic *hypothesis* — that adjacency alone carries predictive
  signal — was not supported, even though Italian residuals do show real spatial
  autocorrelation (a genuine finding, just not an exploitable one with this method).
- **P6 dynamic dual graph** (France): a learned, low-parameter (≤10k) dual graph failed
  all 7 of its pre-registered gate criteria, including underperforming a no-graph
  baseline. Its learned sector labels were additionally found to contain a mapping bug
  (`INVALID_FOR_INTERPRETATION`), an unrelated but compounding problem.
- **Graph-temporal architectures** (GConvGRU, EvolveGCN-H): both were statistically
  indistinguishable from temporal/territory permutation nulls under the A1 fail-closed
  contract. The architecture itself was not the demonstrated problem — the limited
  3-feature tensor available at the time may have been — but under the protocol in force,
  neither model earned promotion.

Each rejection is a finding, not a gap: per the Project Charter (§8), none of these
branches can be reopened on performance grounds alone — only new evidence under a new
pre-registered decision can do that.

## Why did we end up with robust statistical prediction instead?

After three independent graph hypotheses failed their gates, the project had accumulated
strong negative evidence that *the specific graph structures tested* did not help
forecasting — not that no structure could ever help, but that none tested so far cleared
a fair bar against randomized controls. Persistence and Ridge/AR(1) — plain, transparent
statistics with no learned component — remained the only forecasting methods that
consistently passed their validation gates across multiple countries. Choosing them as
the production baseline was therefore not a default or a fallback; it was the
best-supported choice given everything tested up to that point.

## Why did we add sector precedence?

Once the prediction layer was stable, the next falsifiable question was about
*structure between sectors*, not just within a single territory's own history: does
growth in one sector tend to precede growth or decline in another, at a one-year lag? A
simple, auditable method — signed lag-1 regression with bootstrap/permutation validation
and BH/FDR correction — was deliberately chosen over a neural alternative, because it is
directly interpretable and because the project's graph-hypothesis track record up to that
point favoured simple, falsifiable methods over complex ones. This produced the Phase 7
sector-precedence layer: a small number of validated temporal-precedence associations
(never described as causal) across FR/NL/PT.

## Why did granularity become a central question?

Once Phase 7 was running, an asymmetry appeared: France, with by far the most territorial
units (280 ZE2020 zones), produced almost no promoted sector pairs, while NL (40 COROP
regions) and PT (23-25 NUTS3 regions) produced several. The natural reaction — "France's
data must be weaker" — was tested explicitly (DEC-060) and rejected: the effect is
**ecological fragmentation**, a structural property of the statistical method itself.
Splitting a fixed total relationship across more, smaller territorial units mechanically
shrinks the per-unit effect size, regardless of whether the underlying relationship is
real or strong. This reframed "granularity" from a side detail into a first-class
methodological variable: any cross-country comparison of promoted-edge counts that
ignores territorial grain is comparing apples to oranges. It directly motivated raising
PT and NL to finer grains (municipal/gemeente) to test whether the same relationships
would appear at a comparable scale to France's — which is exactly the next question.

## Why was the NL gemeente proxy blocked?

Raising the Netherlands to municipal (gemeente) grain required a proxy, because the
Dutch national statistics office (CBS) does not publish a gemeente × sector × births
table — only a COROP-level births table and a separate, different gemeente-level stock
table. The proxy disaggregated COROP births by each gemeente's share of establishment
stock. Applied naively, the automated promotion-gate count would have called this method
`SUPPORTED` (121 promoted edges — a suspiciously large jump from COROP's 8). A deeper
structural diagnostic found why: the disaggregation method itself injects a
cross-sector-correlated artefact (general local stock co-movement — e.g. gentrification —
not births dynamics) that the regression mistakes for a relation. This is a textbook case
of a derived feature creating its own spurious signal, and it was caught only because the
121-edge jump contradicted the granularity finding above (finer grain should produce
*fewer* detectable effects, not fifteen times more). The proxy was manually overridden
to `BLOCKED` for relation labels — a deliberate human correction of an automated metric,
preserved as a methodological finding in its own right, not hidden as an embarrassment.

## What is the current HERALD architecture?

Six pieces, in order: (1) territorial data (country × territory × sector × year), feeding
(2) a causal, rolling-origin local prediction (persistence/Ridge/AR(1) — never a learned
graph model, given the rejections above), (3) a purely descriptive economic-state label
derived from the observed series (growth/decline/recovery, no model involved), and (4) a
validated sector-to-sector temporal-precedence layer (Phase 7, lag-1 regression). All
three feed (5) an explicit evidence tier (observed/proxy/robust/supported/exploratory/
blocked) before reaching (6) the Observatory dashboard, which visualizes but never
recomputes a scientific number and never claims causality or a recommendation. A
parallel, explicitly unwired research track (the neural SharedRelationEncoder) exists
alongside this architecture: strong on synthetic data, only partially validated on real
data, and not part of the production pipeline.

## What is still missing before a recommendation layer?

Nothing about recommendation has been built. The Project Charter requires both the
forecasting layer (Bloco 1) and the relation/graph layer (Bloco 2) to be complete before
any decision-support layer is attempted, and even then, any output would be an
"opportunity hypothesis," not a validated recommendation — old fixed weights from a prior
intelligence-layer spec are explicitly not to be reused. As of this writing: the
prediction layer is conservative but stable, the relation layer has real but
granularity-limited evidence, and the recommendation layer is **0% — not started**. This
is stated plainly and repeatedly across the canonical documents precisely so that no
reader mistakes a future plan for a current capability.

---

## How this becomes the article storyline

A plausible methods/results narrative arc, built directly from the sections above:

1. **Motivation** — territorial economic dynamism is hard to forecast and harder to
   explain structurally; enterprise birth is a harmonisable first indicator.
2. **Single-country foundation** — France/ZE2020 establishes a forecasting baseline and a
   discipline (causal, rolling-origin evaluation) that the rest of the project inherits.
3. **The leakage lesson** — a concrete methodological failure (and its fix) sets the
   evidentiary bar for everything that follows; this is worth its own short subsection as
   a demonstration of scientific self-correction, not just a footnote.
4. **Three failed graph hypotheses** — presented together as a coherent negative result:
   geographic adjacency, a learned dual graph, and graph-temporal neural architectures
   were each tested under a pre-registered gate and each failed, narrowing the field to
   simple statistics.
5. **The surviving method** — persistence/Ridge plus a simple, auditable sector-precedence
   layer, framed as the best-supported choice given the negative evidence above, not a
   default.
6. **Granularity as a first-class variable** — the France/NL/PT asymmetry, its resolution
   (ecological fragmentation, not weak data), and how it motivated finer-grain testing.
7. **The proxy-blocking finding** — a self-contained cautionary methods vignette: an
   automated metric said "supported," a structural diagnostic said "artifact," and the
   discrepancy itself is the result worth reporting.
8. **Current state and honest limitations** — the architecture as it stands, the
   conservative prediction layer, the partial real-data neural research track, and the
   explicit absence of a recommendation layer.
9. **Future work** — the modular, map-first dashboard redesign and what Bloco 1+2
   completion would need to look like before recommendation work could even start.

---

## Cross-reference

- Phase-by-phase narrative: `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
- Phase/technique matrix: `reports/canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md`
- Full claim/evidence table: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
- Architecture detail: `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
