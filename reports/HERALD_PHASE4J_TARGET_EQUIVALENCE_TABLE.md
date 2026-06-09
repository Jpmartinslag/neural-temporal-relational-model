# HERALD Phase 4J — Canonical Target Equivalence Table

Date: 2026-06-09
Status: official-source semantic gate (PT closed)
Scope: FR, NL, BE, PT — the four targets in `panel_ze2020.csv` / `european_panel`

This table is the canonical record of **what each country's target actually
measures**. It is built from official documentation, not from column names or
series correlation. It supersedes any prior claim that the four targets are a
single harmonized variable.

## Summary verdict

- **No two countries are `equivalent`.**
- **FR ↔ NL: partially comparable** (both local-unit creations; different
  restart/continuity rules).
- **PT: enterprise births, Eurostat-OECD aligned** — the only demographic,
  enterprise-unit target; maps to **Eurostat total enterprise births**.
- **BE: incompatible** — fiscal VAT registration, not a demographic birth.
- **PT gate: CLOSED.** FR/NL/BE remain documented but heterogeneous.

## Table

| country | source | indicator / table | target label | statistical unit | event counted | total/employer population | reactivation rule | mergers / splits / takeovers | continuity rule | known methodological breaks | territorial geometry | Eurostat mapping | evidence URL | confidence | compatibility verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **FR** | INSEE SIDE/SIRENE | répertoire SIRENE | `establishment_creation` (créations d'établissements) | **Établissement** (local production unit) | New local unit registered; includes some restarts after interruption and some takeovers **without** economic continuity | Total (all units, incl. without employees) | Includes some restarts | Includes some takeovers without economic continuity | Weaker than Eurostat (admin register) | Régime auto-entrepreneur 2009 inflated the series; SIRENE coverage changes | ZE2020 (zones d'emploi, ~280) | ≈ Eurostat *establishment/local-unit* concept, **not** enterprise births | https://www.insee.fr/fr/metadonnees/definition/c1754 ; https://www.insee.fr/fr/information/7682004 | High (unit) | **Incompatible with PT/BE; partially comparable with NL** |
| **NL** | CBS | 83631NED `OprichtingenVanVestigingen` | `local_unit_opening` | **Vestiging** (local unit / establishment) | Opening of an establishment belonging to a newly founded business; **excludes** continuation, merger, split, takeover, legal-form change, owner change, relocation preserving the market, reactivation | Total | Excludes reactivation | Excludes mergers/splits/takeovers | Stronger continuity rules than FR | NUTS/COROP layout stable; SBI changes minor | COROP (40) | Local-unit concept (like FR), **not** enterprise births | https://www.cbs.nl/nl-nl/cijfers/detail/83631NED ; https://opendata.cbs.nl/CBS/nl/dataset/81575ned | High (unit) | **Partially comparable with FR; incompatible with PT/BE** |
| **BE** | StatBel | assujettis à la TVA (primo-assujettissements) | `vat_first_registration` | **VAT-registered entity** (fiscal) | First appearance of an entity in the VAT register (administrative event), via monthly register snapshots | Total (VAT-liable) | Re-registrations identified separately (not strictly demographic) | Not a demographic birth event | Fiscal, not economic continuity | **Health-sector discontinuity Jan 2022** (VAT-exemption change) | arrondissements (42) | **Not** a Eurostat business-demography birth (BE is also absent from Eurostat BD) | https://statbel.fgov.be/fr/nouvelles/1110047-entreprises-assujetties-la-tva-en-janvier ; https://statbel.fgov.be/sites/default/files/files/metadata/T7.STAT_DTST_1.CTAC_ORG_1.DIFF_LVL_1.FR.pdf | High | **Incompatible with all (strongest mismatch)** |
| **PT** | INE | 0009702 (births total, NUTS2013) / 0014098 (NUTS2024) ; sectors 0009703 / 0014099 | `enterprise_birth` (nascimentos de empresas) | **Empresa** (enterprise) | Enterprise born "from scratch", **in economic — not administrative — terms** | **Total** enterprise population (includes enterprises without employees) | Eurostat-OECD 2-year rule | Excludes mergers/splits/takeovers (births "from scratch") | Eurostat-OECD economic continuity | **NUTS2013 → NUTS2024 break at 2023** (0014098 mapped back to 25 HERALD zones; PT_170 = Grande Lisboa + Península de Setúbal) | NUTS3 (25) | **Eurostat total enterprise births** (Eurostat-OECD Manual KS-RA-07-010); employer subset is a *different* indicator not used here | https://smi.ine.pt/VariavelFisica/Detalhes_TabObjectosRelacionados/17595 ; https://www.ine.pt (Demografia das Empresas) ; https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-ra-07-010 | High (total pop.); Medium (employer-subset correspondence, not needed) | **Closest to Eurostat; incompatible-as-unit with FR/NL, incompatible-in-nature with BE** |

## Pairwise compatibility matrix (verdict)

| | FR | NL | BE | PT |
|---|---|---|---|---|
| **FR** | — | partially comparable | incompatible | incompatible |
| **NL** | partially comparable | — | incompatible | incompatible |
| **BE** | incompatible | incompatible | — | incompatible |
| **PT** | incompatible | incompatible | incompatible | — |

## Portugal gate — closing evidence

- INE "Demografia das Empresas" states births/deaths are counted **in economic
  terms and not in administrative terms**, i.e. the demographic concept, and the
  series follows the **Eurostat-OECD Manual on Business Demography Statistics**
  (KS-RA-07-010 / OECD 9789264041882).
- Statistical unit = **enterprise** (smallest combination of legal units…),
  published by NUTS and economic activity.
- Population = **total enterprise births** (all enterprises, including those
  without employees). The employer-enterprise subset (≥1 employee), which Eurostat
  highlights as the most internationally comparable, is a **separate** indicator
  and is **not** what `0009702/0014098` provide.
- **Eurostat mapping (answer):** PT corresponds to **Eurostat total enterprise
  births**, with high confidence at the total-population level. Mapping to the
  *employer* population would require a different INE/Eurostat indicator and is
  not implied by the current target.
- Break: 2023 switches from NUTS2013 (`0009702/0009703/0009819`) to NUTS2024
  (`0014098/0014099/0014061`), remapped to the 25 historical HERALD zones.

## Open item (does not block the gate)

- The exact INE↔Eurostat *employer-subset* correspondence is unconfirmed, because
  the current target is the total population. If a future harmonized dataset
  (Path H) chooses the employer population, PT must be rebuilt from the employer
  indicator, not from `0009702/0014098`.
