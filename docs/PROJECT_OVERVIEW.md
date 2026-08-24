# Project overview

**Public name:** Neural Temporal–Relational Model.

## Territorial object

The applied case is **France, 280 employment zones** (*zones d'emploi*, ZE2020 definition,
mainland France excluding Corsica in this phase). An employment zone is INSEE's standard
labour-market territorial unit — a group of communes where most residents both live and
work.

## Economic signals

Five economic signals are used, all published by an official statistical authority, all at
the employment-zone level, none fabricated for this study. Frequency below is each signal's
**native publication frequency**, verified against the report's data-construction section —
not the frequency of any single downstream analysis grid:

| Signal | Publisher | Native frequency |
|---|---|---|
| Private salaried employment | Urssaf | Quarterly |
| Gross payroll | Urssaf | Quarterly |
| Employer establishments | Urssaf | Annual |
| Localised unemployment | Insee | Quarterly |
| Establishment creations | Insee / SIDE | Annual |

Full sourcing, periods, and how the two annual and three quarterly series are aligned onto one
time axis: [`DATA_AND_PROVENANCE.md`](DATA_AND_PROVENANCE.md).

## What a node is

A node is **one territory** (a French employment zone, or — in the synthetic protocols — one of
the calibrated artificial zones). A node's state at a given period is its own trajectory on the
five signals above, summarised by the causal temporal representation described below. Nodes do
not represent sectors, establishments or people.

## What a candidate relation is

A candidate relation is a **proposed connection between two territories**, offered to the
model as an input, never as a label:

| Family | Nature | Definition |
|---|---|---|
| Commuting links | Observed | Home-to-work flows published by Insee; the 40 strongest destinations per source zone (main benchmark) or the 40 strongest incoming sources per target zone (residual diagnostic) |
| Economic similarity links | Constructed | The 10 sources whose past growth history correlates most with the target's, using only information available by the decision period |
| Economic complementarity links | Constructed | Regime-dependent, nonlinear co-movement; a relation family known only in the synthetic protocols |
| All ordered pairs | Constructed | Every ordered pair of distinct territories in the **80-territory residual diagnostic only** (6,320 pairs) — used there to test whether limited candidate coverage explains that diagnostic's failure to recover connections. **Not evaluated at this scale in the 280-territory main benchmark.** |

"Observed" means published by a statistical authority; "constructed" means derived by this
study from observed data. Neither word means the model discovered or validated the relation.
No candidate relation is presented as a proven economic dependency, an influence, or a
causal link. See [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md) for the exact
permitted and forbidden language.

## The causal temporal representation

Every territory's own trajectory is described using only information available on or before
the decision date: current level, growth over the signal's own native lag, acceleration, a
medium-term trend, recent momentum, volatility, an economic regime label, a national component,
the territory's growth relative to that national component, and an availability indicator (a
value that is not yet published is flagged, never replaced by zero). This representation is the
"local trajectory first" half of the architecture, and it is the part of the model with a
demonstrated effect (see Results).

## The relational learner

The "territorial context second" half of the architecture is a model that **learns a graph**
over the candidate relations above, rather than assuming a fixed adjacency. It is evaluated
under **two separate, non-comparable synthetic protocols** — never a single shared setting —
described fully in [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md):

- A **280-territory main benchmark**, where the proposed model (at three widths) is compared
  against persistence, a classical sparse method (graphical Granger with Lasso), and two neural
  relational baselines (Neural Relational Inference, MTGNN) — all five under one shared protocol
  (same observed values, masks, candidate support, training window, scoring origins, and seeds).
- An **80-territory residual diagnostic**, where a single additive relational arm is tested
  alone, after a frozen local temporal baseline, across four candidate supports — this diagnostic
  does not include persistence/Granger/NRI/MTGNN as comparators.

The relational learner is evaluated on two separate questions, kept structurally apart
throughout the project:

1. **Forecasting** — does adding relational information improve prediction of a territory's own
   signal, compared with a temporal-only baseline?
2. **Relation recovery / identification** — does the model's learned graph correspond to the
   true connections, in a setting where the true graph is known?

These are answered separately because a model can do well on one and fail the other — which is
exactly what happened; see [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md).

Multirelational **attention-based fusion** across relation families, and **relation-family-specific
representations**, are proposed architecture extensions. Neither is implemented in the current
code, and neither should be read as a component of the evaluated model. They are future work.

## French application vs. synthetic known-truth protocols

This is the single most important structural distinction in the project, and the one most
likely to be misread if skipped. There are **three** distinct settings, not two — the two
synthetic protocols are themselves not comparable to each other (different territory counts,
targets, and candidate supports; see [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md)
for the full separation table):

| | French application | 280-territory main benchmark | 80-territory residual diagnostic |
|---|---|---|---|
| Territories | 280 real employment zones | 280 artificial zones calibrated to French marginals | 80 artificial zones (same calibration) |
| Target | Observed signals; no single fixed prediction target | Growth of the 5 signals at the next period | Residual left after a frozen local temporal baseline, at 3 horizons |
| True relational graph | **Not observed. Does not exist as ground truth.** | Known by construction, drawn inside the commuting support | Known by construction, 3 relation families, most outside the commuting support |
| What can be measured | Forecast accuracy, association, temporal precedence | Forecast skill **and** relation recovery against a known answer | Out-of-sample residual gain **and** relation recovery against a known answer |
| Permitted conclusions | Descriptive / exploratory, never causal, never a validated relation | Recovery, ceiling, false-positive rate against controls, for this protocol only | Recovery, ceiling, false-positive rate against controls, for this protocol only |

Relation-recovery numbers (edge F1, AUPRC, oracle response) are **only ever measured on the two
synthetic protocols**, because only there is the true graph known. No French relation is ever
scored against a ground truth, because no such ground truth exists. Any French candidate
relation displayed by this project is a constructed hypothesis, never a discovered or measured
relation. A number from one synthetic protocol is also never compared with a number from the
other. See [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md) for the full boundary.

## How prediction and relation identification were evaluated separately

- **Forecasting** is scored as skill relative to a persistence baseline (repeat the latest
  observation) in the main benchmark, or as out-of-sample residual gain in the diagnostic, under
  causal rolling-origin evaluation (no information from after the decision date is ever used).
- **Relation identification** is scored by edge F1 and AUPRC **against the candidate set's own
  random baseline**, never as a raw number in isolation, and never across protocols — because
  candidate sets with different edge prevalence, in different protocols, are not comparable on
  raw AUPRC. A **no-relation control** (a paired synthetic world with the propagation mechanism
  switched off) is run alongside every recovery result: if a model finds "structure" in the
  no-relation world, that structure is an artefact of the model, not evidence of a relation.
- An **oracle** (an estimator that receives the true relational term directly, instead of having
  to find it) is run in both protocols, to separate "is the mechanism present and measurable in
  the data" from "does the evaluated model find it." These are different questions, and the
  project's central finding is that the answer differs between them — see
  [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md).

## Repository structure

See the root [`README.md`](../README.md#repository-structure) for the annotated directory
tree, and [`EXPERIMENT_PROVENANCE.md`](EXPERIMENT_PROVENANCE.md) for how the current state
relates to the project's experimental history.
