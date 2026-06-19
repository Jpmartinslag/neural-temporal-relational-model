# Phase 7 Sector Precedence — Audit Report

**Result: PASS**  
Generated: 2026-06-12T14:35:20.850558+00:00

| Metric | Value |
|--------|-------|
| Total edges | 5456 |
| Manifest tasks | 710 |
| Promoted (main) | 25 |
| Promoted (without_2020) | 34 |

## Findings

- **INFO** `SCHEMA_OK`: All required columns present (18 total)
- **INFO** `TASKS_COMPLETE`: All 710 tasks represented
- **INFO** `NAN_PRESENT`: 368/5456 edges have NaN (expected for low-sample edges)
- **INFO** `NO_INF`: No Inf values in numeric columns
- **INFO** `P_RANGE_OK`: p_perm in (0, 1] for all 5088 non-NaN edges
- **INFO** `FDR_VERIFIED`: BH/FDR recomputed matches merged (max diff=1.11e-16)
- **INFO** `PROMOTION_MAIN`: Promoted edges (main): 25
- **INFO** `PROMOTION_WO20`: Promoted edges (without_2020): 34
- **INFO** `COVID_ROBUST`: COVID-robust edges: 12 (2 countries)
- **INFO** `SUMMARY`: Audit result: PASS — 9 findings
