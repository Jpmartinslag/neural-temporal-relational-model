# HERALD Phase 4J — Target-Aware Results (Path M)

Date: 2026-06-09
Source: existing predictions `hpc_results/herald_phase4j_a_20260609_local_r1/phase4j_a_predictions.csv`
Generator: `hpc/phase4/audit_phase4j_target_aware.py` (**reaggregation only — no model retrained**)

> **Semantic warning (mandatory).** Cross-country WMAPE below compares
> **heterogeneous administrative targets** — FR/NL local-unit creations, BE VAT
> first registrations, PT enterprise births. It measures transfer across related
> territorial tasks, **not** generalization of one harmonized target. See
> `HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`.

## 1. Primary result — per-country WMAPE, by target concept

| Country | Target concept | Persistence | Ridge | Fixed 50/50 | 50/50 vs persistence |
|---|---|---:|---:|---:|---:|
| FR | establishment_creation | 0.085149 | 0.091561 | **0.074465** | -12.55% |
| NL | local_unit_opening | 0.078982 | 0.069821 | **0.069799** | -11.63% (≈ tie vs Ridge) |
| BE | vat_first_registration | 0.087930 | 0.095380 | **0.084338** | -4.09% |
| PT | enterprise_birth | 0.123588 | 0.130927 | **0.119667** | -3.17% |

Per-country mean WMAPE is the **primary** result. The fixed 50/50 mean improves
the per-country mean in all four countries.

## 2. Worst-year and p90 (stability)

| Country | Config | Worst-year WMAPE | p90 yearly WMAPE |
|---|---|---:|---:|
| FR | persistence / 50/50 | 0.143169 / 0.123076 | 0.136409 / 0.121592 |
| NL | persistence / 50/50 | 0.113439 / 0.148117 | 0.112922 / 0.111492 |
| BE | persistence / 50/50 | 0.118230 / 0.159600 | 0.116412 / 0.126588 |
| PT | persistence / 50/50 | 0.271779 / 0.350076 | 0.231584 / 0.244481 |

The fixed 50/50 worsens the worst year in NL, BE, and PT. In specific good
years for persistence, adding Ridge damages the forecast.

## 3. Yearly wins (fixed 50/50)

| Country | Target concept | Wins vs persistence | Wins vs Ridge | Worst country-year regression vs persistence |
|---|---|---:|---:|---:|
| FR | establishment_creation | 5/7 | 6/7 | **+47.6%** (2023) |
| NL | local_unit_opening | 5/7 | 3/7 | +41.0% (2020) |
| BE | vat_first_registration | 4/7 | 4/7 | +37.5% (2024) |
| PT | enterprise_birth | 4/7 | 4/7 | +37.2% (2024) |

Aggregate: 18/28 country-years beat persistence (64%); 7/28 beat the best
isolated component.

## 4. Pooled WMAPE — sensitivity only

| Config | Pooled WMAPE |
|---|---:|
| Fixed 50/50 | 0.077447 |
| Persistence | 0.087468 |
| Ridge | 0.089400 |

Pooled is dominated by France (280 of 387 zones) and is reported **only as
sensitivity**, not as a primary or harmonized-target result.

## 5. Pre-specified tail-risk gate (fixed 50/50)

Thresholds fixed **before** inspecting results:

| # | Criterion | Threshold | Observed | Pass |
|---|---|---|---|:--:|
| C1 | Mean improves every country | all 4 | all 4 improve | ✅ |
| C2 | No country mean regresses | ≤ +1% | max -3.17% | ✅ |
| C3 | No country-year regresses vs persistence | ≤ +10% | **+47.6% (FR 2023)** | ❌ |
| C4 | Country-year wins vs persistence | ≥ 50% | 64% (18/28) | ✅ |
| — | p90 yearly WMAPE | report | pers 0.1505 / ridge 0.1813 / 50-50 0.1516 | — |

**Tail-risk verdict: FAIL (criterion C3).** The fixed 50/50 mean degrades the
worst country-year by up to +47.6% versus persistence, far above the +10% limit,
and its p90 yearly error (0.1516) is marginally worse than persistence (0.1505).

## 6. Decision

1. **Fixed 50/50 is not promoted.** It remains an exploratory candidate.
2. **No new weight search in this task** (the pre-specified stop rule applies).
3. Persistence remains the per-country safe baseline; Ridge is the trained
   reference.
4. **No retraining was needed**: this report only reaggregated existing
   predictions under the Path M protocol.

## Reproduction

```bash
python3 hpc/phase4/audit_phase4j_target_aware.py \
  --phase4j-root hpc_results/herald_phase4j_a_20260609_local_r1
```
