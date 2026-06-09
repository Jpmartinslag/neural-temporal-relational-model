# HERALD Phase 4J — Path M Protocol (Heterogeneous-Target Transfer)

Date: 2026-06-09
Decision context: semantic gate FAIL for a single harmonized target
(`reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md`,
`reports/HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`). Path M chosen now;
Path H later and scoped.

## 1. Problem definition

HERALD Phase 4 is, **by documented evidence, a transfer problem across related
but heterogeneous territorial tasks**, not a single-target generalization
problem. Each country keeps its own administrative target:

| Country | `flag_target_concept` | Unit |
|---|---|---|
| FR | `establishment_creation` | local unit (établissement) |
| NL | `local_unit_opening` | local unit (vestiging) |
| BE | `vat_first_registration` | fiscal VAT entity |
| PT | `enterprise_birth` | enterprise (Eurostat-OECD) |

The shared structure is **territorial business dynamics measured annually under a
causal `t-1` protocol**, not an identical dependent variable.

## 2. Metadata contract (mandatory)

- `flag_target_concept` is **mandatory metadata** on every row and must use the
  unit-precise values above. It is passthrough metadata: **no model consumes its
  string value**, so correcting it required no retraining (only a panel rebuild).
- `meta_source_label`, `meta_region_system`, `country`, `year`, `region_level`
  must be present and correct (audited in §5).
- Any results table that aggregates across countries must print
  `flag_target_concept` next to each country.

## 3. Reporting rules (binding)

1. **Primary result = per-country WMAPE** (mean yearly territorial WMAPE), each
   labelled with its target concept.
2. **Country-balanced mean = performance summary only**, explicitly *not* proof
   of a common target.
3. **Pooled WMAPE = sensitivity only.**
4. Every cross-country table carries the mandatory semantic warning (§6).
5. Yearly wins / worst-year / p90 reported alongside means (no mean-only claims).

## 4. Claims policy

**Forbidden claims:**
- "HERALD generalizes European business creation."
- "The model transfers a single enterprise-birth target across countries."
- Any statement implying FR/NL/BE/PT measure the same event.

**Permitted claim:**
- "HERALD transfers across **related but heterogeneous** territorial domains whose
  targets are administratively different (local-unit creations, VAT registrations,
  enterprise births), under a causal parameter-zero-shot LOCO protocol."

## 5. Metadata audit status (2026-06-09)

Adapters corrected this phase (see migration notes in code):

| Field | FR | NL | BE | PT |
|---|---|---|---|---|
| `flag_target_concept` | establishment_creation ✓ | local_unit_opening ✓ (was enterprise_birth) | vat_first_registration ✓ (was enterprise_birth) | enterprise_birth ✓ |
| `meta_source_label` | SIDE ✓ | CBS ✓ | StatBel ✓ | INE ✓ (was INE-GEP) |
| `meta_region_system` | ZE2020 ✓ | COROP ✓ | arrondissement ✓ | NUTS3 ✓ |

**Migration:** value changes are in passthrough metadata only. The canonical
`data/processed/european_panel/*.csv` are build artifacts (not versioned) and
carry the old strings until rebuilt; rebuilding the panel propagates the
corrected values. **No model retraining is required** (the 4J predictions do not
depend on `flag_target_concept`; the `panel_ze2020.csv` used by 4J does not even
contain the field). Legacy values are recorded in the adapter comments.

## 6. Mandatory semantic warning (paste into every cross-country table)

> Cross-country WMAPE here compares **heterogeneous administrative targets**
> (FR/NL local-unit creations, BE VAT first registrations, PT enterprise births).
> It measures transfer across related territorial tasks, **not** generalization of
> one harmonized target. See `HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`.

## 7. Relationship to Path H

Path H (one harmonized Eurostat/official definition for all countries) remains a
**later, scoped** option — a separate confirmatory dataset on countries where
official business-demography births are clean and NUTS3-native (PT, NL, candidate
ES), not a rebuild that blocks current work. Belgium is absent from Eurostat
business demography and is the hardest case. Re-aggregating FR to NUTS3 triggers
MAUP. Path H is therefore future validation, not the current track.
