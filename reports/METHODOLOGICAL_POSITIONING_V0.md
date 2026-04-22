# Methodological Positioning v0

Date: 2026-04-22

## Canonical Framing

This project must be interpreted as a territorial multi-agent recommendation system for territorial economic recommendation, with an `STGNN` as the central backbone architecture.

The core scientific objective is not merely to find the best simple predictive model. The objective is to model territorial economic dynamics at `ZE2020` level, learn useful spatio-temporal territorial representations, and later use those representations inside a territorial recommendation pipeline orchestrated by multiple agents.

## Role of Prediction

Forecasting establishment creations is an intermediate supervised task of the backbone, not the final product of the project.

In practice:

- `SIDE` establishment-creation forecasting is the current supervised learning interface;
- the learned temporal and relational representations are the real backbone target;
- the downstream destination is territorial multi-agent recommendation, not standalone forecasting.

## Baseline Policy

The current baseline must always be treated as a benchmark, not as the final project outcome.

Official benchmark bundle:

- `side_creations_lag_1`
- `nb_com`
- `rei_cfe_microentrepreneurs_created_n_1_lag_1`

Best validated baseline at this stage:

- `Ridge + REI`
- mean `WMAPE ~= 6.699`

Interpretation rule:

- the baseline is the comparison floor for the backbone;
- the project must not be reframed as a search for the best simple model;
- winning on a tabular benchmark alone does not close the scientific objective.

## Experimental Interpretation

Several simple graph variants failed against the current REI benchmark:

- geographic linear spatial signals
- mobility linear spatial signals
- minimal `GCN` variants
- residual `GCN` variants
- first minimal residual `STGNN`

This does not show that `STGNN` is methodologically wrong for the project.

It only shows that the first low-capacity graph prototypes did not yet extract enough value from the available spatio-temporal structure.

## Current Project State

The project is currently in the correct next phase if it does the following:

- keep the REI baseline consolidated as the official benchmark;
- use the new tensor package with REI already included;
- develop a small but methodologically serious `STGNN` as the backbone;
- evaluate all graph-temporal progress against the benchmark bundle above.

## Precedence Rule

If an older report conflicts with this framing, this document prevails.

Historical reports remain useful as traceability of what was tried, but they must not be read as the current canonical methodological position.
