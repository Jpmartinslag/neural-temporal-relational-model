# HERALD Sector Precedence Graph — Execution Contract

**Status:** IMPLEMENTED, FULL RUN NOT YET EXECUTED

## Question

Does lagged growth in sector A add information about next-year growth in sector
B, within the same territory, beyond sector B's own recent growth?

## Method

- Directed edges `A(t-1) → B(t)`.
- Rolling six-year country windows.
- Regression: `B(t) ~ B(t-1) + A(t-1)`.
- Territory and year means removed before estimation.
- Standardized signed source coefficient (`beta`).
- Incremental explanatory value (`delta_r2`) beyond the target autoregression.
- Temporal null: source values permuted across territories within each year.
- Benjamini-Hochberg FDR within each country-window family.
- Territory bootstrap for sign stability.
- Main run and sensitivity excluding 2020.

## Promotion Gate

An exploratory edge requires all:

- `q_fdr ≤ 0.05`;
- `|beta| ≥ 0.10`;
- `delta_r2 ≥ 0.005`;
- bootstrap sign stability `≥ 0.70`;
- at least 60 aligned observations.

The prototype is ready only if at least two countries have a promoted edge
whose sign and promotion survive the 2020-excluded sensitivity.

Thresholds are project-specific pre-registered gates, not universal economic
constants.

## Interpretation

Allowed: predictive precedence, signed lagged association, exploratory sector
relationship.

Forbidden: structural causality, economic impact, intervention effect,
recommendation, cross-country pooling.

## Execution

Smoke:

```bash
python3 -m src.data.european_panel.build_sector_precedence_graph \
  --n-permutations 9 --n-bootstraps 9
```

Full run:

```bash
python3 -m src.data.european_panel.build_sector_precedence_graph \
  --n-permutations 999 --n-bootstraps 500 --confirm-full-run
```

The full run may be computationally expensive. Its outputs must be audited
before any edge is shown in the dashboard.
