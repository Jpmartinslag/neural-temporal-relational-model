# HERALD Phase 4E-B — Causal Feature-Policy Ablation

**Goal:** choose clean per-country feature/tensor baselines after retiring Phase 4A/4D leakage-affected scores.

Phase 4E-B does **not** compare against Phase 4A as a valid performance baseline. It uses the canonical Phase 4E European panel, causal `growth_1y`, no manual COVID/rebound input flags, identity graph, and `no_regime`.

## Configs

Common to FR/NL/BE/PT:

| Config | Purpose |
|---|---|
| `b0_baseline_annual` | Phase 4E-A causal 5-feature baseline: lag1/2/3 + growth1/2 |
| `b1_side5_full_zero` | Trainer-native `side5_full`, zero tensor |
| `b2_side2_zero` | Only lag1 + causal growth1, zero tensor |
| `b3_current_clean_zero` | Current-clean annual inputs, zero tensor |

Portugal-only tensor controls:

| Config | Purpose |
|---|---|
| `b4_side2_births_lag1` | A2-style births proxy tensor control |
| `b5_side2_emp_lag1` | Harmonised Eurostat/ARDECO employment tensor |

## Runs

10 seeds:
`0 1 7 13 17 42 77 99 123 2025`

Expected total:
- FR/NL/BE: 4 configs x 10 seeds = 40 each
- PT: 6 configs x 10 seeds = 60
- Total = 180 runs

## Decision Rules

- If `b0_baseline_annual` remains best: keep Phase 4E-A as country baseline.
- If `b1_side5_full_zero` wins: trainer-native 5-feature policy is enough.
- If `b2_side2_zero` wins: simple lag1 + growth1 is sufficient under causal data.
- If `b3_current_clean_zero` wins: stock/source-compatible annual inputs matter.
- For PT, compare `b4` vs `b5`: if employment tensor beats births proxy, promote the harmonised European tensor.

BE is the key diagnostic country because Phase 4E-A2 worsened there after dropping lag2/lag3.

---

## Results (2026-06-03 — 180/180 runs complete)

| Country | Winner | WMAPE mean ± std | Delta vs b0 | Interpretation |
|---------|--------|-----------------|-------------|----------------|
| FR | `b2_side2_zero` | 0.1031 ± 0.0084 | −0.0121 (−10.5%) | lag1 + causal growth1 sufficient |
| NL | `b0_baseline_annual` | 0.1017 ± 0.0075 | 0.0000 | full history wins; side2 degrades +25% |
| BE | `b3_current_clean_zero` | 0.1488 ± 0.0063 | −0.0041 (−2.7%) | current_clean marginal win; side2 degrades |
| PT | `b5_side2_emp_lag1` | 0.2286 ± 0.0148 | −0.0187 (−7.6%) | Eurostat/ARDECO employment tensor wins |

Full audit: `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md`

### Conclusion

**Phase 4E-B is the clean causal baseline per country.** No single feature policy dominates across all countries.

- Phase 4E-C must compare against these per-country winners, not Phase 4E-A.
- Phase 4A/4D remain legacy leakage-affected results — not valid baselines.
- PT employment tensor (`b5`) is promoted as the canonical PT tensor for future batteries.
