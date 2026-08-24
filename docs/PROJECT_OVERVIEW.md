# Project overview

**Public name:** Neural Temporal–Relational Model.
**Internal historical codename:** HERALD (*Heterogeneous Economic Relational Adaptive
Learning for territorial Dynamics*). The codename is kept only where it is needed to trace
an artefact back to its origin — see [`EXPERIMENT_PROVENANCE.md`](EXPERIMENT_PROVENANCE.md).
It is not the model's public/scientific name.

---

## Territorial object

The applied case is **France, 280 employment zones** (*zones d'emploi*, ZE2020 definition,
mainland France excluding Corsica in this phase). An employment zone is INSEE's standard
labour-market territorial unit — a group of communes where most residents both live and
work.

## Economic signals

Five economic signals are used, all published by an official statistical authority, all at
the employment-zone level, none fabricated for this study:

| Signal | Publisher | Frequency | Period |
|---|---|---|---|
| Private-sector employment | Urssaf | Annual | 1998–2024 |
| Private-sector payroll | Urssaf | Annual | 1998–2024 |
| Employing establishments | Urssaf | Annual | 1998–2024 |
| Local unemployment rate | Insee | Annual | 2003–2025 |
| New establishments | Sirene / SIDE | Annual | 2012–2025 |

Full sourcing, coverage and derived files: [`DATA_AND_PROVENANCE.md`](DATA_AND_PROVENANCE.md).

## What a node is

A node is **one territory** (a French employment zone, or — in the synthetic benchmark — one
of 280 artificial zones calibrated to reproduce French marginal statistics). A node's state
at year *t* is its own trajectory on the five signals above, summarised by the causal temporal
representation described below. Nodes do not represent sectors, establishments or people.

## What a candidate relation is

A candidate relation is a **proposed connection between two territories**, offered to the
model as an input, never as a label:

| Family | Nature | Definition |
|---|---|---|
| Commuting links | Observed | Home-to-work flows published by INSEE; the 40 strongest destinations per zone |
| Economic similarity links | Constructed | Similarity between standardized past trajectories; 10 nearest profiles per zone |
| Economic complementarity links | Constructed | Regime-dependent, nonlinear co-movement; known only in the synthetic benchmark |
| All candidate pairs | Constructed | Every ordered pair of distinct territories, used only as a diagnostic upper bound on the candidate set |

"Observed" means published by a statistical authority; "constructed" means derived by this
study from observed data. Neither word means the model discovered or validated the relation.
No candidate relation is presented as a proven economic dependency, an influence, or a
causal link. See [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md) for the exact
permitted and forbidden language.

## The causal temporal representation

Every territory's own trajectory is described using only information available on or before
the decision date: current level, annual growth, acceleration, a 12-period trend, 8-period
momentum, 8-period volatility, an economic regime label (expansion / slowdown / contraction /
recovery), a national component, the territory's growth relative to that national component,
and an availability indicator (a value that is not yet published is flagged, never replaced
by zero). This representation is the "local trajectory first" half of the architecture, and
it is the part of the model with a demonstrated effect (see Results).

## The relational learner

The "territorial context second" half of the architecture is a model that **learns a graph**
over the candidate relations above, rather than assuming a fixed adjacency. It is compared,
under one shared protocol, against a persistence baseline, a classical sparse method (graphical
Granger with Lasso), and two neural relational baselines (Neural Relational Inference, MTGNN),
at three widths (compact / medium / wide). The relational learner is evaluated on two separate
questions, kept structurally apart throughout the project:

1. **Forecasting** — does adding relational information improve one-step-ahead prediction of
   a territory's own signal, compared with a temporal-only baseline?
2. **Relation recovery / identification** — does the model's learned graph correspond to the
   true connections, in a setting where the true graph is known (the synthetic benchmark)?

These are answered separately because a model can do well on one and fail the other — which is
exactly what happened; see [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md).

Multirelational **attention-based fusion** across relation families, and **relation-family-specific
representations**, are proposed architecture extensions. Neither is implemented in the current
code, and neither should be read as a component of the evaluated model. They are future work.

## French application vs. synthetic known-truth benchmark

This is the single most important structural distinction in the project, and the one most
likely to be misread if skipped:

| | French application | Synthetic known-truth benchmark |
|---|---|---|
| Territories | 280 real employment zones | 280 artificial zones calibrated to French marginals |
| Signals | 5 real, observed | Generated to reproduce the real panel's statistical properties |
| True relational graph | **Not observed. Does not exist as ground truth.** | Known by construction (3 relation families) |
| What can be measured | Forecast accuracy, association, temporal precedence | Forecast accuracy **and** relation recovery against a known answer |
| Permitted conclusions | Descriptive / exploratory, never causal, never a validated relation | Recovery, ceiling, false-positive rate against controls |

Relation-recovery numbers (edge F1, AUPRC, oracle response) are **only ever measured on the
synthetic benchmark**, because only there is the true graph known. No French relation is ever
scored against a ground truth, because no such ground truth exists. Any French candidate
relation displayed by this project is a constructed hypothesis, never a discovered or measured
relation. See [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md) for the full boundary.

## How prediction and relation identification were evaluated separately

- **Forecasting** is scored as skill relative to a persistence baseline (repeat the latest
  observation), under causal rolling-origin evaluation (no information from after the decision
  date is ever used).
- **Relation identification** is scored by edge F1 and AUPRC **against the candidate set's own
  random baseline**, never as a raw number in isolation — because two candidate sets with
  different edge prevalence are not comparable on raw AUPRC. A **no-relation control** (a paired
  synthetic world with the propagation mechanism switched off) is run alongside every recovery
  result: if a model finds "structure" in the no-relation world, that structure is an artefact
  of the model, not evidence of a relation.
- An **oracle** (an estimator that receives the true relational term directly, instead of having
  to find it) is run at every relational-scale setting, to separate "is the mechanism present and
  measurable in the data" from "does the evaluated model find it." These are different questions,
  and the project's central finding is that the answer differs between them — see
  [`RESULTS_AND_LIMITATIONS.md`](RESULTS_AND_LIMITATIONS.md).

## Repository structure

See the root [`README.md`](../README.md#repository-structure) for the annotated directory
tree, and [`EXPERIMENT_PROVENANCE.md`](EXPERIMENT_PROVENANCE.md) for how the current state
relates to the project's experimental history.
