# European panel — architecture

## Motivation

The Neural Temporal–Relational Model was calibrated for France with country-specific
sources (SIDE, URSSAF, FLORES). Extending it to NL, BE, and PT initially produced a
"patch per country" pattern: each country got renamed columns, flags forced to zero, and
ad hoc adaptations inside `prepare_phase4_panel.py`.

This module replaces that approach with a **canonical data contract**: every country
implements an adapter that always exports the same schema. The model core never sees
source or regional-system differences — only the harmonized panel.

```
National sources     →  CountryAdapter  →  EuropeanPanel (schema.py)
Eurostat/ECB sources  →  EUSignalLoader  ↗
                                         ↓
                                      validation.py
                                         ↓
                                      model core
```

---

## File structure

```
src/data/european_panel/
├── README.md            ← this file
├── schema.py            ← canonical contract: FieldSpec, REQUIRED_FIELDS, …
├── validation.py        ← post-adapter checks: temporality, NaN, masks
├── adapters/
│   ├── __init__.py
│   ├── france_adapter.py    ← SIDE/A10/URSSAF into the canonical schema
│   ├── nl_adapter.py        ← CBS COROP into the canonical schema
│   ├── be_adapter.py        ← StatBel arrondissements into the canonical schema
│   └── pt_adapter.py        ← INE NUTS3 (target births) + Eurostat employment into the canonical schema
└── eu_signals/          (Phase 4E-C — integrated)
    ├── eurostat_client.py  ← REST JSON-stat client + cache under data/raw/
    ├── eurostat_gdp.py     ← nama_10_gdp (real GDP growth, national)
    ├── eurostat_lfs.py     ← lfsi_emp_a / une_rt_a (employment/unemployment, national)
    ├── ec_bcs.py           ← ei_bssi_m_r2 (ESI, monthly → annual average)
    ├── ecb_bls.py          ← ECB BLS SME credit standards, quarterly → annual average
    ├── assemble.py         ← lag-1 overlay + mask_eu_signals recomputation
    └── fetch_all.py        ← CLI: downloads raw data + writes eu_signals_annual.csv
```

> STS turnover and EEI remain NaN — the source-by-source missing-data search that
> established this was consolidated into the repository's documentation history
> before this delivery branch existed and is not part of the current file tree;
> it remains recoverable from git history (`git log --all -- reports/HERALD_PHASE4E_MISSING_DATA_SEARCH.md`).
> ECB BLS was integrated on 2026-06-02 as `eu_credit_standards_lag1`.

---

## Data contract (`schema.py`)

**Current schema state**:
- Fields catalogued in `FIELD_CATALOGUE`: **43**
- Columns exported by the current adapters: **43**
- Observability masks already exported:
  - `mask_target` — target observed
  - `mask_sector_a10` — A10 sector coverage observed
  - `mask_employment` — 1 = genuine employment tensor, 0 = absent
  - `mask_tensor` — operational tensor weight; `0.5` marks a proxy, `1.0` a genuine tensor
  - `mask_eu_signals` — share of non-NaN `eu_*` fields per row
- **Phase 4E-C (2026-06-02):** 5 of the 7 `eu_*` signals filled via Eurostat/ECB
  (`eu_gdp_growth_lag1`, `eu_employment_rate_lag1`, `eu_unemployment_rate_lag1`,
  `eu_esi_lag1`, `eu_credit_standards_lag1`), national, safely lagged by one year.
  `mask_eu_signals` ≈ 0.65–0.71 in covered years (FR/NL/BE/PT). STS turnover and EEI
  remain NaN. The overlay runs in `build_european_panel.py` after each adapter; the
  model core is unchanged. Disable with `--no-eu-signals`.
- **Netherlands sector births update (2026-06-02):** CBS 83631NED was integrated as
  `sector_*` by COROP × model A10 sector, lagged by one year in the NL adapter.
  `mask_sector_a10=1.0` in the NL panel.
- **Belgium tensor update (2026-06-02):** ONSS Q4 2021–2024 was integrated into
  `belgium_qtensor_jobs_panel.csv`; the BE tensor now covers 2008–2024.
- **Portugal tensor update (2026-06-02):** `nama_10r_3empers` was integrated as the
  regional employment-by-sector tensor (`EMP`, NUTS3 × NACE, 2000–2023) and completed
  for 2024 with ARDECO SNETZ (`Employment by industry`, NUTS3, A10). The PT panel keeps
  sector births as `sector_*`, but `mask_employment=1` and `mask_tensor=1` when the
  Eurostat/ARDECO tensor is present.
- **Portugal births extension 2023–2024 (2026-06-02):** the PT panel extended from
  2008–2022 to 2008–2024. Years 2008–2022 use the older INE indicators (`0009702`
  total births, `0009703` births by CAE, `0009819` stock, NUTS 2013); years 2023–2024
  use the new INE NUTS 2024 indicators (`0014098` total births, `0014099` births by
  CAE, `0014061` stock), remapped onto the 25 historical model zones. Critical case:
  `PT_170` = sum of Grande Lisboa (`1A0`) + Península de Setúbal (`1B0`), preserving
  the former Lisbon Metropolitan Area. Mapping in
  `src/data/ingest_portugal_panel_nuts3.py` (`NUTS2024_TO_HERALD_NUTS3`) — the
  constant name is a legacy identifier from before the public rename; the mapping
  logic itself is unaffected.

Required fields across all adapters:

| Field | Type | Role |
|---|---|---|
| `country` | str | ISO 3166-1 alpha-2 |
| `region_id` | str | NUTS3-2021 or documented national ID |
| `region_name` | str | Human-readable label |
| `region_level` | str | NUTS3 / COROP / arrondissement / ZE2020 / … |
| `year` | int | Target year t |
| `node_idx` | int | Stable integer index (0-based), consistent with the adjacency |
| `target_births` | float | Business/establishment births in t |
| `lag1_births` | float | `target_births` at t-1 |
| `growth_1y` | float | Causal percentage change: `(t-1 - t-2) / t-2` |
| `mask_target` | float | 1 = observed, 0 = absent (scales the loss) |
| `flag_target_concept` | str | 'establishment_creation' / 'enterprise_birth' / … |
| `flag_is_covid_year` | int | 1 for 2020 |
| `flag_is_rebound_year` | int | 1 for 2021 |
| `flag_forecast_safe` | int | 1 if every required lag is available |
| `meta_region_system` | str | Regional system used |
| `meta_source_label` | str | SIDE / CBS / StatBel / INE / Eurostat-BD |

Relevant optional fields: `lag2_births`, `lag3_births`, `growth_2y`, `stock_lag1`,
`sector_BE…RU` (A10), `eu_employment_rate_lag1`, `eu_esi_lag1`, `eu_credit_standards_lag1`,
`eu_gdp_growth_lag1`, `mask_sector_a10`, `mask_employment`, `mask_tensor`,
`mask_eu_signals`, `flag_has_national_employment`.

See `schema.py` for the full catalog with a `source_hint` per field.

---

## Adapter — minimal interface

```python
class CountryAdapter:
    country: str = "XX"

    def build(self, year_min: int, year_max: int) -> pd.DataFrame:
        """
        Produce a panel in the canonical European schema.
        Must contain every field in REQUIRED_FIELDS.
        Missing optional fields must be present as NaN (never omitted).
        """
        ...

    def validate(self, df: pd.DataFrame) -> dict:
        from src.data.european_panel.validation import validate_panel
        return validate_panel(df, country=self.country)
```

---

## Methodological rules

### Temporal causality
- Never use year-t data to predict t.
- `lag1_*` = value at t-1; `eu_*_lag1` = annual average for t-1, published before t.
- `flag_forecast_safe=0` excludes the row from training and evaluation.
- Nowcast ≠ forecast. Never call an ex-ante forecast a nowcast.

### Non-predictive fields (`NON_PREDICTIVE_FIELDS`)
`flag_is_covid_year` and `flag_is_rebound_year` are **audit metadata**, not predictive
features. They live in `schema.NON_PREDICTIVE_FIELDS` and must be excluded from
`x_ann`, `q_tensor`, the regime vector, and any model input.

Reason: they encode explicit knowledge of specific calendar dates (2020, 2021), which
is implicit lookahead in a temporal-generalization setting. The Phase 4 training
pipeline does not use them as features — this rule formalizes and protects that
behavior.

The legacy `train_dynamic_stgnn_models_v1.py` trainer used them via `feature_columns()`.
That trainer is not used in the Phase 4D/4E batteries and must not be referenced for
new experiments.

### Targets and comparability
- `flag_target_concept` documents the exact concept.
- Do not compare WMAPE across countries when the underlying concepts differ.
- Do not impute a missing sector as zero without `mask_sector_a10`.
- **Phase 4J status (semantic gate executed — FAILS for a single shared target):**
  the official semantic audit confirmed the 4 targets are **not** the same statistical
  event: FR établissement creations (local unit), NL `oprichtingen van vestigingen`
  (local unit, different continuity rules), BE first VAT registration (fiscal
  registration, methodological break Jan/2022), PT enterprise births per INE
  `0009702`/`0014098` (enterprise unit). The panel is, for now, a **heterogeneous
  multi-task benchmark**, not proof of generalization across an identical target.
  Do not compare the four as if they were equivalent. `flag_target_concept` is
  **mandatory metadata** with unit-precise values: FR `establishment_creation`, NL
  `local_unit_opening`, BE `vat_first_registration`, PT `enterprise_birth`
  (Eurostat-OECD definition, total population). The full target-equivalence table and
  path-M protocol write-up were consolidated into the repository's documentation
  history before this delivery branch existed and are not part of the current file
  tree; the finding above is the operative summary, and the underlying documents
  remain recoverable from git history
  (`git log --all -- reports/HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`).

### Macro signals
- Add `eu_*` signals one at a time, with a per-country ablation.
- Do not add 20 macro features at once without a clean baseline.
- Report when a feature helps only one country — do not generalize from that.

### Common European signals
- Eurostat BD, LFS, STS, BCS/ESI, ECB BLS: common coverage across FR/NL/BE/PT.
- BE is absent from Eurostat BD (confirmed empirically for `bd_hgnace_r` and
  `bd_size_r3`). For BE, StatBel is the primary source; Eurostat BD is used only for
  cross-validation.
- ECB BLS: euro-area members only. FR/NL/BE/PT are covered since 2003.

### Graphs and tensors
- Graphs and tensors are **secondary ablations**, not part of the base contract.
- The European contract defines the features; graphs are training configuration.
- Phase 4D showed that functional graphs do not robustly beat an identity control
  (the permutation control won in BE; the NL/PT margin was below σ).

---

## Phase 4E — experimental plan

The full experimental-plan document was consolidated into the repository's
documentation history before this delivery branch existed and is not part of the
current file tree; it remains recoverable from git history
(`git log --all -- reports/HERALD_EUROPEAN_PANEL_STANDARD_PLAN.md`). The battery
sequence and win criteria below are the operative summary.

Battery sequence:
1. `phase4e_baseline` — standardized panel, no EU signals, no embedding
2. `phase4e_country_embed` — + country embedding (16-dim, learned)
3. `phase4e_eu_signals` — + Eurostat/LFS/ESI/ECB-BLS by ablation
4. `phase4e_tensor_masks` — use `mask_tensor`/`mask_employment` in the loss and configs

Win criteria:
- WMAPE improves over the Phase 4E-A/A2 causal baseline in ≥2 countries
- No country regresses by >1% vs. its own clean causal baseline
- France is analyzed separately because the canonical model uses a distinct national
  pipeline
- Stability: σ_seed < 0.005
