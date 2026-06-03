# HERALD Phase 4 — Coverage Mask Experimental Plan

## Hypothesis

> "Can HERALD learn from international panels with heterogeneous observability,
> using coverage masks to avoid penalising the model for data that a country does not publish?"

This does not promise it works. It defines a testable hypothesis.

## Motivation

Cross-country training panels have structural data gaps:
- **Netherlands 2007–2014**: OPQ sectors not reported (~16% of total births)
- **Belgium**: different birth concept (Primo-assujetissements ≠ créations SIDE)
- **Portugal**: sector coverage varies with INE methodological reforms
- **Any future country**: missing years, unreported sectors, classification changes

Ad-hoc per-country preprocessing introduces researcher degrees of freedom and
breaks reproducibility. A general mechanism is more defensible scientifically.

## Experimental Design

> **⚠️ NOTA RETROACTIVA (2026-06-03): Phase 4A affectée par leakage temporel.**
> La feature `growth_1y` dans les panels Phase 4A/4D était calculée comme
> `(y[t] − y[t-1]) / y[t-1]`, utilisant l'objectif courant `y[t]` (fuite temporelle).
> Les WMAPE Phase 4A sont **invalides comme baseline scientifique**.
> Baseline causal: Phase 4E-A. Voir `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md`.

### Phase 4A — ~~Clean~~ **Legacy baseline (leakage-affected)** (no mask)
- Train only on years/sectors that are **fully comparable across all countries**
- Netherlands: 2015–2024 births (T001081 available, OPQ included)
- Belgium: 2006–2020 (homogeneous series)
- Portugal: 2008–2022 (homogeneous series)
- **Purpose (original)**: establish a clean floor with no methodological confound
- **Status**: `growth_1y` was leaky — WMAPEs inflated. Use Phase 4E-A as baseline instead.

### Phase 4B — Coverage mask
- Extend training to partially-observed years/sectors
- Netherlands: add 2007–2014 with `coverage_mask[OPQ]=0`
- Loss is masked: only penalise on observed sectors/totals
- OPQ head trained only where OPQ is observed (2015+), extrapolated silently elsewhere
- **Purpose**: test if partial observability helps without introducing bias

### Phase 4C — Comparison
Evaluate 4B vs 4A on:
1. WMAPE on 2021–2025 evaluation folds (primary metric)
2. Seed stability (std across seeds)
3. Sector-level WMAPE — does OPQ prediction quality degrade?
4. Bias check — does any country benefit at the expense of another?

## Success Criterion

| Outcome | Interpretation |
|---------|---------------|
| 4B WMAPE < 4A AND seed std ≤ 4A | Coverage mask is a methodological contribution |
| 4B WMAPE ≈ 4A | Neutral — masking neither helps nor hurts |
| 4B WMAPE > 4A OR seed std > 4A | Negative result — partial observability adds noise even when masked |

All three outcomes are publishable.
The negative result: *"coverage masking was insufficient to recover signal from partially-observed panels"*.

## Technical Implementation (Phase 4B)

Three components:

### 1. Panel builder — `coverage_mask` column
```python
# Per row in the panel:
coverage_mask: dict[str, bool]  # A10 sector → observed (True/False)
y_partial: float                # sum of observed sectors (NaN if none)
y_total: float                  # full total (NaN if not published)
```

### 2. Loss function — masked WMAPE
```python
def masked_wmape(y_pred_sectors, y_true_sectors, coverage_mask, y_partial):
    # Case 1: full total observed → standard WMAPE on total
    # Case 2: partial total only → WMAPE on sum(ŷ_s for s in mask)
    # Case 3: nothing observed → skip row (no gradient)
    # Sector loss: only for s where mask[s]=True
```

### 3. Dataloader — pass mask as tensor
```python
batch["coverage_mask"]  # shape [B, n_sectors], dtype float (0.0 / 1.0)
batch["y_partial"]      # shape [B], float (NaN where not applicable)
```

## Netherlands Data Status

| Table | Coverage | Status |
|-------|----------|--------|
| 83631NED births | 2015–2025 COROP (T001081) | Downloaded ✓ |
| 83631NED births | 2007–2014 COROP (sum non-OPQ) | Needs download ✓ |
| 83582NED jobs A10 | 2010–2024 COROP | Downloaded ✓ |
| 81578NED stock | 2007–2026 COROP | Downloaded ✓ |

OPQ share per zone: median 16%, std 1.4 pp across years — stable enough for masking.
Spatial correlation r(total, private) = 0.9997 — masking does not distort ranking.

## Paper Framing

> "We introduce a coverage-aware training objective for HERALD that accommodates
> heterogeneous sector observability across countries and time periods. Training
> on partially-observed panels without masking introduces systematic bias equal
> to the missing sector share (~16% for Netherlands pre-2015). The mask
> eliminates this bias while preserving the usable signal. We evaluate whether
> the additional training years from previously unusable data improve
> out-of-sample WMAPE on the 2021–2025 evaluation window."

---
*Created: 2026-05-28 — Phase 4 experimental design*
