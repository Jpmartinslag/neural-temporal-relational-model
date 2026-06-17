# HERALD Granular Evidence Policy

**Status:** ACTIVE
**Date:** 2026-06-17
**Follows:** DEC-063 (proxy panel construction), DEC-064 (PT Municipal Phase 7), DEC-065
(NL gemeente proxy BLOCKED), DEC-066 (fine-grain threshold policy)
**Purpose:** Define, once and for all, which territorial evidence sources may feed
sector→sector relation labels/training and which may only feed territorial context/
visualization, after the DEC-065 structural validity finding.

---

## 1. Observed Relation Labels (may feed training / Observatory relation graph)

| Source | Region system | Evidence type | DEC | Status |
|--------|---------------|----------------|-----|--------|
| FR ZE2020 | ZE2020 (280 zones) | `observed_births` (establishment_creation, SIDE/SIRENE) | DEC-034/060 | VALID_OBSERVED |
| PT Municipal | MUNICIPALITY (278 municipalities) | `observed_births` (enterprise_birth, INE) | DEC-064 | VALID_OBSERVED |
| NL COROP | COROP (40 regions) | `observed_births` (local_unit_opening, CBS 83631NED) | DEC-034 | VALID_OBSERVED |

These three sources are **directly observed** (not disaggregated by proxy weighting).
Edges derived from them, once classified under the DEC-066 fine-grain taxonomy
(`ROBUST_ORIGINAL`, `FINE_GRAIN_SUPPORTED`, `EXPLORATORY_FINE_GRAIN`), may feed:
- the Observatory relation graph (Layer 2)
- supervised training labels — subject to the `use_in_training` flag per tier
  in `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json`
- claims of statistical association / temporal precedence (never causal claims)

PT NUTS3 (25 territories, DEC-034 scale) remains a separate, coarser observed source;
it is not part of the granular (municipal/ZE2020-scale) evidence set defined here, but
remains valid at its own scale per DEC-034/066.

---

## 2. Proxy Territorial Estimates (visualization/context ONLY)

| Source | Region system | Evidence type | DEC | Status |
|--------|---------------|----------------|-----|--------|
| NL gemeente proxy | GEMEENTE_PROXY (355 gemeenten) | `proxy_disaggregated_by_stock_share` | DEC-063/065 | **BLOCKED_FOR_RELATION_LABELS** |

**Root cause (DEC-065):** the proxy disaggregation method
(`estimated_births_gemeente = observed_births_COROP × stock_share_gemeente`) injects
cross-sector-correlated noise into gemeente-level velocity that is unrelated to any
births-precedence relationship. Decomposition regression
`gm_velocity ~ corop_velocity + share_velocity` found the `share_velocity` coefficient
(≈13.0) roughly 10× larger than `corop_velocity` (≈1.33), and `share_velocity` itself
has cross-sector correlation of 0.34–0.82 — a structural property of local
establishment-stock co-movement (e.g. gentrification, development), not a births
precedence mechanism. Full diagnostic:
`data/processed/phase7_nl_gemeente_proxy/results/structural_validity_diagnostic.json`.

**NL gemeente proxy MAY feed:**
- territorial context map (Layer 1 territory state)
- local stock/structure visual estimate (which sectors are locally concentrated)
- visual distribution estimate of where COROP-level activity is spatially allocated

**NL gemeente proxy MUST NOT feed:**
- sector→sector relation labels (Layer 2 relation graph)
- claims of municipal-level temporal precedence between sectors
- supervised training as a positive label under any DEC-066 tier
  (`ROBUST_ORIGINAL`, `FINE_GRAIN_SUPPORTED`, `EXPLORATORY_FINE_GRAIN`)

All 121 NL gemeente proxy edges nominally promoted by the automated Phase 7 gates
are preserved as evidence (not deleted) but are permanently labelled
`BLOCKED_PROXY_ARTIFACT` with `allowed_for_training_label=false` and
`reason=stock_share_induced_artifact`. See
`data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv`.

---

## 3. Label Classes

| Label class | Meaning | `use_in_training` |
|---|---|---|
| `ROBUST_ORIGINAL` | \|β\|≥0.10, q_fdr<0.05, bss≥0.70, observed source | `true` (full weight) |
| `FINE_GRAIN_SUPPORTED` | \|β\|≥0.09, bss≥0.80, + COVID-robust/cross-window/cross-country, observed source | `with_caveat` (downweighted) |
| `EXPLORATORY_FINE_GRAIN` | \|β\|≥0.07, bss≥0.90, observed source, no extra robustness condition | `false` (hypothesis only) |
| `BLOCKED_PROXY_ARTIFACT` | Promoted by gate-counts but sourced from a proxy method with a documented structural validity defect (DEC-065) | `false` (never; structurally invalid, not merely weak) |
| `INSUFFICIENT_EVIDENCE` | Fails minimum gates (q_fdr, β, Δr², bss, or n_samples) on an observed source | `false` |

`BLOCKED_PROXY_ARTIFACT` is distinct from `INSUFFICIENT_EVIDENCE`: the former means the
statistical machinery is invalid for this source (clustering/induced correlation), not
that the underlying effect is weak. It must never be silently merged into
`EXPLORATORY_FINE_GRAIN` or any other tier, even if its raw |β|/bss numbers would
otherwise qualify.

---

## 4. Language Rules

**Permitted:**
- "proxy territorial" / "territorial proxy estimate"
- "estimativa desagregada" / "disaggregated estimate"
- "contexto municipal" / "municipal context"
- "não válido para relações" / "not valid for relation labels"
- "associação estatística" / "statistical association"
- "precedência temporal" / "temporal precedence"
- "impacto preditivo" / "predictive impact" (in the sense of explaining variance, not causing)
- "evidência observada" / "observed evidence"
- "artefato metodológico" / "methodological artifact"

**Prohibited:**
- "nascimento observado municipal NL" / "NL municipal observed births" (NL gemeente
  data is never observed births — it is a proxy)
- "relação robusta municipal NL" / "robust NL municipal relation" (no NL municipal-scale
  relation is robust; only NL COROP-scale relations are observed/valid)
- any wording asserting that one sector is structurally responsible for growth in
  another sector, or any other structural-causal claim, at any scale, for any country

These rules apply to all new reports, dashboards, and code comments touching granular
evidence (FR ZE2020, PT Municipal, NL COROP, NL gemeente proxy).

---

## 5. Summary Table

| Evidence | Relation labels | Territory context | Training | Status |
|---|---|---|---|---|
| FR ZE2020 observed | YES | YES | per DEC-066 tier | VALID_OBSERVED |
| PT Municipal observed | YES | YES | per DEC-066 tier | VALID_OBSERVED |
| NL COROP observed | YES | YES | per DEC-066 tier | VALID_OBSERVED |
| NL gemeente proxy | **NO** | YES (tagged proxy) | **NO** | BLOCKED_FOR_RELATION_LABELS |

---

*HERALD Granular Evidence Policy | ACTIVE | follows DEC-063/064/065/066 | 2026-06-17*
