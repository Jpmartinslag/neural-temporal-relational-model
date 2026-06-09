# HERALD Phase 4J - Semantic Target Audit

Date: 2026-06-09  
Status: preliminary official-source audit  
Decision: **FAIL for a single harmonized target; usable as a heterogeneous-task benchmark**

## Question

Do FR, NL, BE, and PT measure the same territorial event when the pipeline
labels the target as business creation?

## Findings

| Country | Pipeline source | Statistical unit/event | Preliminary equivalence |
|---|---|---|---|
| FR | INSEE SIDE/SIRENE | Creation of an **establishment** (local unit) | Local-unit target |
| NL | CBS 83631NED | Opened **establishments** belonging to a newly founded business | Close to FR unit, different event rules |
| BE | StatBel VAT register | First VAT registration (`primo-assujettissement`) | Fiscal registration, not demographic birth |
| PT | INE 0009702/0014098 | **Enterprise births** by NUTS3 | Enterprise-level target |

The current panel therefore does not contain one harmonized dependent
variable. It mixes local-unit creation, fiscal registration, and enterprise
birth.

## Country Evidence

### France

INSEE defines an establishment creation as a new local production unit. It
includes some restarts after interruption and some takeovers without economic
continuity. SIDE explicitly distinguishes enterprise and establishment
creations.

Official sources:

- https://www.insee.fr/fr/metadonnees/definition/c1754
- https://www.insee.fr/fr/information/7682004

### Netherlands

CBS 83631NED counts every establishment opened by a newly founded business.
The table excludes continuation, merger, split, takeover, legal-form change,
owner change, relocation preserving the market, and reactivation.

This confirms the local-unit interpretation, but it is not exactly equivalent
to France because France and CBS do not apply identical restart/continuity
rules.

Official source:

- https://www.cbs.nl/nl-nl/cijfers/detail/83631NED

### Belgium

The target is the first appearance of an enterprise in the VAT register.
StatBel separately identifies first registrations and re-registrations by
comparing monthly register snapshots. This is a fiscal-administrative event.

The population can change when VAT law changes. StatBel documents a large
health-sector discontinuity in January 2022 caused by a change in VAT
exemption rules. This is direct evidence that the target is not a stable
demographic birth concept.

Official sources:

- https://statbel.fgov.be/fr/nouvelles/assujettis-la-tva-mensuels-maintenant-disponibles-selon-la-nace
- https://statbel.fgov.be/fr/nouvelles/1110047-entreprises-assujetties-la-tva-en-janvier
- https://statbel.fgov.be/sites/default/files/files/metadata/T7.STAT_DTST_1.CTAC_ORG_1.DIFF_LVL_1.FR.pdf

### Portugal

Code inspection corrects an earlier documentation error: the target does
**not** come from GEP Quadros de Pessoal. `ingest_portugal_panel.py` downloads
INE indicators `0009702/0014098`; sector births use `0009703/0014099`.
GEP was investigated as a possible employment source, not as the target.

INE identifies the physical variable as enterprise births and publishes it by
NUTS and economic activity. The exact correspondence to Eurostat total
enterprise births versus employer enterprise births must still be confirmed
from the complete methodological metadata.

Official source:

- https://smi.ine.pt/VariavelFisica/Detalhes_TabObjectosRelacionados/17595?clear=True

## Consequences

1. Cross-country WMAPE remains useful for testing transfer across related
   territorial tasks, but not as proof of generalization for one identical
   economic target.
2. The current LOCO claim must say **heterogeneous-target transfer**.
3. A harmonized European dataset requires choosing one population and rebuilding
   every country from compatible official data.
4. Re-aggregating territories to NUTS3 does not solve target semantics and
   introduces MAUP.
5. Belgium is the strongest semantic incompatibility and requires either a
   separate output task or replacement by harmonized business-demography data.

## Gate Decision

**Semantic Gate 1: FAIL for direct target equivalence.**

Two valid paths remain:

- **Path H:** create a new harmonized Eurostat/official business-birth dataset,
  with one statistical unit and one event definition;
- **Path M:** retain the current panel as multi-task learning with explicit
  country/target concepts and restrict claims to heterogeneous-task transfer.

No architecture change can repair this semantic mismatch.

## Recommendation (independent, Path H vs Path M)

**Primary recommendation: Path M now; Path H later as a scoped confirmatory
dataset, not a replacement.**

| Criterion | Path H (harmonized target) | Path M (multi-task, heterogeneous targets) |
|---|---|---|
| Scientific rigor | Highest: enables a single-target generalization claim | High **if** claims are restricted to heterogeneous-task transfer |
| Data availability | Costly: FR is ZE2020, not NUTS3 (re-aggregation + MAUP); **BE is absent from Eurostat BD**, confirmed empirically (`bd_hgnace_r`, `bd_size_r3`) | Uses existing panel; no new ingestion |
| Timeline | Weeks–months (rebuild every country from compatible official data) | Days (add concept metadata/heads, restrict claims) |
| Cost | High data engineering; introduces a new experimental variable | Low |
| "Apprentissage frugal" fit | In tension (large data effort) | Strong fit (work with available data, small models) |
| Economic recommendation use | Cleaner single deployable target | Realistic: each country has its own administrative target; per-country concept conditioning is deployable |

**Rationale.** Path M is frugal, immediate, and honest: it matches the real
deployment scenario where each country exposes a different administrative target,
and it lets the science proceed now with claims explicitly restricted to
heterogeneous-task transfer. Path H's data cost is high and itself introduces a
new experimental variable (re-aggregating FR to NUTS3 triggers MAUP; Belgium is
not covered by Eurostat business demography, so a single Eurostat definition
would either drop BE or force an incompatible source). Path H should therefore be
pursued **later and scoped** — a separate confirmatory dataset on the subset of
countries where Eurostat/official business-demography births are clean and
NUTS3-native (e.g. PT, NL, plus a candidate such as ES), to test whether a
single-target claim holds — rather than as a rebuild that blocks current work.

This recommendation is conditional on one open check: confirming, from the
complete INE methodological metadata, the exact correspondence of the PT target
to Eurostat total vs employer enterprise births (Section "Portugal").
