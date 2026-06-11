# HERALD G2 Aggregate Dynamics Audit

**Date:** 2026-06-11
**Status:** `G2_DESCRIPTIVE_DYNAMICS_COMPLETE`
**Builder:** `src/data/european_panel/build_g2_aggregate_dynamics.py`
**Tests:** `tests/test_g2_aggregate_dynamics.py` — 45 pass, 0 skip, 0 fail
**Artifacts:** `data/processed/economic_graph/g2_dynamics/`

---

## 1. Scientific Question

How does the aggregate structure of the validated L2 co-growth graph vary over
time by country and sector?  This is a descriptive question within Bloco 2.  It
does not test causal hypotheses, does not name individual territorial edges as
stable relationships, and does not pool counts across countries.

**Language:** "observed aggregate variation in density and weights" — not
"structural evolution" or "causal dynamics".

---

## 2. Data and Coverage

**Source:** `data/processed/economic_graph/sector_panel_fr_nl_pt.csv`
**Source checksum (SHA-256, 16-char):** see `g2_dynamics_manifest.json`

| Country | Sectors | Regions | Observation years | Eval years | Eval range |
|---------|---------|---------|-------------------|------------|------------|
| FR | 9 (BE,FZ,GI,JZ,KZ,LZ,MN,OQ,RU) | 280 ZE2020 | 2012–2025 | 10 | 2017–2026 |
| NL | 9 (BE,FZ,GI,JZ,KZ,LZ,MN,OQ,RU) | 40 COROP | 2007–2025 | 15 | 2012–2026 |
| PT | 8 (BE,FZ,GI,JZ,LZ,MN,OQ,RU) | 25 NUTS3 | 2008–2024 | 13 | 2013–2025 |

**PT KZ:** structurally absent (DEC-018); never imputed, never converted to
zero.  PT participates with 8 sectors.

The 321 annual rows split into FR 90, NL 127 and PT 104. NL has fewer than
9×15 rows because OQ lacks sufficient early observations for every rolling
window; no missing graph-year is converted to zero.

**No cross-country pooling.** Counts, densities and weights are never aggregated
across countries.

---

## 3. Method

1. Read `sector_panel_fr_nl_pt.csv`.
2. For each country × sector, build rolling growth matrices (window=5,
   min_periods=4).
3. Compute pairwise Pearson correlations per eval_year.
4. Build top-k=5 symmetric binary adjacency (positive correlations only).
5. Compute per-year metrics: density, weight distribution (mean, median, std,
   p10, p25, p75, p90), and mean absolute weight. The top-k constructor keeps
   positive correlations only, so sign fractions are structural diagnostics
   (`frac_positive=1`) rather than substantive results.
6. Compute consecutive turnover (1 − Jaccard) and consecutive Jaccard.
7. Compute year-over-year changes (absolute and relative).
8. Compute pair-resampling sensitivity intervals for mean weight and density
   (200 resamples, 80% pairs, seed=42). These are not confidence intervals:
   territory pairs share nodes and are statistically dependent.
9. Summarize by period (pre-2020, 2020, post-2020) using the last observation
   year in each rolling window (`observation_year_last = eval_year − 1`).
   Therefore the row labelled period `2020` is the five-year rolling graph
   ending in 2020 and available at `eval_year=2021`; it is not a graph built
   only from observations collected during 2020.
10. Compare periods (post − pre, 2020 − pre).
11. Top-k sensitivity at k=3,5,10.
12. COVID sensitivity: repeat with and without observation_year=2020.
13. All parameters, checksums and commit recorded in manifest.

---

## 4. Metrics

### Per country × sector × eval_year (321 rows)

| Metric | Description |
|--------|-------------|
| n_regions | Number of territories |
| n_possible_pairs | N×(N−1)/2 |
| n_edges_valid | Edges in top-k adjacency |
| density | n_edges_valid / n_possible_pairs |
| mean/median/std_weight | Statistics of edge weights (Pearson correlations) |
| p10/p25/p75/p90_weight | Quantiles of edge weight distribution |
| frac_positive/negative/near_zero | Structural diagnostics; top-k retains positive edges only |
| mean_abs_weight | Mean |weight| |
| turnover | 1 − Jaccard vs previous year |
| jaccard_consecutive | Jaccard vs previous year |
| pair_resample_mean_weight_p{025,975} | Descriptive pair-resampling interval |
| pair_resample_density_p{025,975} | Descriptive pair-resampling interval |

### Per country × sector × period (78 rows)

Mean, min and max of annual metrics within each period.

### Per country × sector × comparison (52 rows)

Absolute and relative differences between periods (post−pre, 2020−pre).

---

## 5. Results: France (FR)

| Metric | Pre-2020 | 2020 | Post-2020 |
|--------|----------|------|-----------|
| Mean density | 0.0224 | 0.0226 | 0.0230 |
| Mean weight | 0.9501 | 0.9395 | 0.9453 |
| Mean turnover | 0.79 | — | 0.79 |
| N (sector-years) | 36 | 9 | 45 |

**Key finding:** FR graph structure is extremely stable across periods.
Density changes are negligible (Δ < 0.001).  Mean weight fluctuations are
small (< 0.01 between periods).  All 9 sectors show minimal post−pre
differences.  FR turnover is high (79%) — consistent with the G2 preflight
finding that individual top-5 edges are volatile even though aggregate
statistics are stable.

**Largest FR sector change (post−pre):** MN Δweight = −0.011; RU Δweight =
+0.003. The pair-resampling intervals are narrow, but they are not
inferential confidence intervals.

**Interpretation status:** FR aggregate temporal signal was validated as
COVID-robust (DEC-024d, 9/9 sectors in both scenarios).  Limited inferential
claim permitted: aggregate density and weight distributions are temporally
consistent for all 9 sectors.

---

## 6. Results: Netherlands (NL)

| Metric | Pre-2020 | 2020 | Post-2020 |
|--------|----------|------|-----------|
| Mean density | 0.1653 | 0.1605 | 0.1714 |
| Mean weight | 0.8386 | 0.8120 | 0.8496 |
| Mean turnover | 0.59 | — | 0.59 |
| N (sector-years) | 73 | 9 | 45 |

**Key finding:** NL shows slight density increase post-2020 (+0.006 vs pre)
and weight increase (+0.011). The rolling graph whose window ends in 2020
shows a dip in mean weight (0.812 vs 0.839 pre). These are modest absolute
changes.

**Notable NL sector (post−pre):** GI Δweight = +0.089; BE Δdensity = +0.014.

**Interpretation status:** NL is `COVID_SENSITIVE` (DEC-024d, 4/9 with 2020
vs 5/9 without).  Results are descriptive only.  The observed period
differences may be driven by 2020 sensitivity.

---

## 7. Results: Portugal (PT)

| Metric | Pre-2020 | 2020 | Post-2020 |
|--------|----------|------|-----------|
| Mean density | 0.2762 | 0.2733 | 0.2775 |
| Mean weight | 0.7984 | 0.7963 | 0.8463 |
| Mean turnover | 0.51 | — | 0.51 |
| N (sector-years) | 64 | 8 | 32 |

**Key finding:** PT shows a post-2020 weight increase (+0.048 vs pre).  The
rolling-window-ending-2020 weight (0.796) is essentially identical to the
pre-2020 average (0.798).
Density changes are negligible across all periods.

**Notable PT sector (post−pre):** RU Δweight = +0.144; MN Δweight = +0.131.
These are the largest weight changes observed in any country.

**Interpretation status:** PT is `COVID_SENSITIVE` (DEC-024d, 4/8 with 2020
vs 0/8 without).  Results are purely descriptive.  The post-2020 weight
increase cannot be attributed to any specific cause.

---

## 8. Comparison Pre/2020/Post

### Across countries (descriptive, no pooling)

| Country | Δ density (post−pre) | Δ mean weight (post−pre) | Δ mean weight (2020−pre) |
|---------|---------------------|--------------------------|--------------------------|
| FR | +0.0006 | −0.0048 | −0.0106 |
| NL | +0.0061 | +0.0110 | −0.0266 |
| PT | +0.0013 | +0.0479 | −0.0021 |

**Interpretation:** All three countries show negligible density changes.
Weight changes are modest for FR, moderate for NL, and larger for PT
(driven by MN, RU, OQ sectors). The rolling graph ending in 2020 shows
slight weight dips for FR and NL but not PT. No causal attribution. These are
observed temporal differences in overlapping rolling windows, not COVID
effects.

---

## 9. Sensitivities

### Top-k sensitivity (k=3, 5, 10)

Higher k increases density mechanically (more edges per node).

| Country | Mean density k=3 | k=5 | k=10 |
|---------|------------------|-----|------|
| FR | ~0.014 | ~0.023 | ~0.046 |
| NL | ~0.120 | ~0.167 | ~0.282 |
| PT | ~0.177 | ~0.276 | ~0.503 |

Weight statistics change minimally with k because the top-k filter selects
the strongest correlations.

### COVID sensitivity (observation_year=2020 included vs excluded)

| Country | Mean density Δ | Mean weight Δ | Classification |
|---------|----------------|---------------|----------------|
| FR | < 0.001 | < 0.005 | `COVID_ROBUST` |
| NL | < 0.005 | < 0.01 | `COVID_SENSITIVE` |
| PT | < 0.005 | < 0.02 | `COVID_SENSITIVE` |

Detailed per-sector-year deltas in `g2_covid_sensitivity.csv`.

---

## 10. Uncertainty

- Pair-resampling sensitivity intervals computed per country × sector × year
  (200 resamples, 80% pair fraction, seed=42).
- Interval width is small for density (typically < 0.002 for FR) and mean
  weight (typically < 0.01), showing limited sensitivity to which observed
  pairs are sampled.
- These are not population confidence intervals. Territory pairs share nodes,
  so the resampled units are dependent and the intervals may be too narrow.
- Small number of years per period (e.g. 4 pre-2020 years for FR) limits
  period summary reliability.  These are descriptive intervals, not
  frequentist confidence intervals from a population model.
- Years are not independent draws — they are consecutive observations from
  a correlated time series.  Do not treat N years as N independent samples.

---

## 11. Limitations

1. **Individual edges are NOT stable** (G2_EDGE_STABILITY_NOT_SUPPORTED;
   M2 0.06–0.26; persistence 0.4%).
2. **Communities are NOT validated** (DEC-021: NOT_SUPPORTED).
3. **Graph does NOT improve forecasting** (DEC-023: NOT_SUPPORTED).
4. **Pearson rolling correlation conflates co-movement with shared trends.**
5. **MAUP applies** — territorial units are administrative boundaries.
6. **No causal attribution.** Period differences are observed, not explained.
7. **Small number of years limits period comparison power.** FR has only 4
   pre-2020 eval years.
8. **NL and PT are COVID-sensitive** — their period conclusions change when
   observation_year=2020 is removed.
9. **Cross-country replication of temporal signal is NOT supported** — the
   2/3 gate passes with different countries in different scenarios.
10. **No economic recommendation.** The graph describes statistical
    co-movement, not productive opportunities.
11. **Period labels summarize overlapping five-year windows.** The `2020`
    period is the graph ending in 2020, not a pure single-year graph or an
    estimate of a COVID effect.
12. **Positive-edge selection is structural.** Sign fractions cannot be used
    to claim that negative economic relationships are absent.

---

## 12. Claims Permitted and Prohibited

### Permitted

- The positive top-k L2 co-growth graph's aggregate density and weight
  distributions vary modestly across rolling windows ending before, during,
  and after 2020 for all three countries.
- FR aggregate temporal structure is COVID-robust: metrics are consistent
  with or without observation_year=2020.
- Edge-level turnover is high (~79% for FR, ~59% for NL, ~51% for PT);
  aggregate statistics are more interpretable than individual edge tracking.
- PT shows the largest post-2020 weight increase (+0.048), concentrated in
  RU, MN and OQ sectors; this is a descriptive observation.
- Use `FR_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED`.
- Use `G2_CROSS_COUNTRY_REPLICATION_NOT_SUPPORTED`.

### Prohibited

- "The L2 graph shows structural evolution" (use: observed aggregate
  variation).
- "COVID caused graph weakening/strengthening."
- "Territory A and B have a stable co-growth relationship."
- "The graph predicts enterprise births" (DEC-023: NOT_SUPPORTED).
- "Communities of territories are validated" (DEC-021: NOT_SUPPORTED).
- "NL/PT temporal signal is generally validated" (COVID-sensitive).
- `G2_AGGREGATE_TEMPORAL_SIGNAL_SUPPORTED` as a global conclusion.
- Any economic recommendation based on these results.

---

## 13. Methodological Decision

**DEC-025 — G2 aggregate dynamics characterization complete.**

The descriptive analysis records that the L2 graph's aggregate structure
(density, weight distribution, turnover) varies modestly over time for all
three countries.  FR is the only country with a COVID-robust temporal signal.
NL and PT provide sensitivity results only.  Individual edges remain
unstable; communities remain unvalidated; forecast utility remains
unsupported.

---

## 14. Dashboard Adaptation Plan

The following G2 statistics could be added to `herald_france_final_dashboard.html`
in a future iteration (after explicit authorization per DEC-014):

1. **Density panel:** Line chart of edge density over time, per sector.
2. **Weight distribution:** Box/violin plot of weight distribution per year.
3. **Turnover indicator:** Annual turnover rate by sector.
4. **Period summary table:** Pre/2020/post comparison for selected sectors.
5. **Country selector:** Extend to NL and PT with explicit COVID-sensitivity
   warning.

**No dashboard modification in this task** (DEC-014).  This plan is
documentation only.

---

## Artifacts

| File | Size | Description |
|------|------|-------------|
| `g2_annual_metrics.csv` | 161 KB | 321 rows: country × sector × eval_year |
| `g2_period_metrics.csv` | 29 KB | 78 rows: country × sector × period |
| `g2_period_comparisons.csv` | 13 KB | 52 rows: country × sector × comparison |
| `g2_topk_sensitivity.csv` | 43 KB | Per-year metrics at k=3,5,10 |
| `g2_covid_sensitivity.csv` | 50 KB | Per-year with/without 2020 comparison |
| `g2_dynamics_summary.json` | 3 KB | Parameters, checksums, country summaries |
| `g2_dynamics_manifest.json` | 1 KB | Artifact checksums and metadata |
| `figures/g2_density_temporal_{FR,NL,PT}.png` | — | Density over time |
| `figures/g2_weight_temporal_{FR,NL,PT}.png` | — | Mean/median weight over time |
| `figures/g2_heatmap_{FR,NL,PT}.png` | — | Sector × year heatmap |
| `figures/g2_post_minus_pre_{FR,NL,PT}.png` | — | Post−pre weight change |
| `figures/g2_turnover_jaccard_{FR,NL,PT}.png` | — | Turnover and Jaccard temporal |
| `figures/g2_comparative_panel.png` | — | 3-country comparative panel |
