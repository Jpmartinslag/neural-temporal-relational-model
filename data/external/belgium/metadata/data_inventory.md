# Belgium — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready

---

## Panels produits

| Fichier | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/belgium_births_panel.csv` | 588 | 42 | 2007–2020 | Births (TVA primo-assujetissements) × arrondissement × year |
| `processed/belgium_stock_panel.csv` | 588 | 42 | 2007–2020 | Stock (TVA entreprises actives) × arrondissement × year |
| `processed/belgium_qtensor_jobs_panel.csv` | 5460 | 42 | 2008–2020 | ONSS employee jobs × A10 × arrondissement × year |

Zone IDs: `BE_<arrondissement>` (e.g. `BE_bruxelles`, `BE_anvers`, `BE_tournai_mouscron`).

---

## Sources

| Composant | Source | Indicateur | Licence |
|-----------|--------|-----------|---------|
| Births | Statbel — beSTAT API | TVA primo-assujetissements par arrondissement | CC BY 4.0 |
| Stock | Statbel — beSTAT API | TVA entreprises actives par arrondissement | CC BY 4.0 |
| Q-tensor | ONSS — archives localunit | Postes de travail par lieu de travail × NACE-BEL × arrondissement (Q4) | Open |

---

## Notes méthodologiques critiques

### Concept births
- **TVA primo-assujetissements** = premier enregistrement TVA (entreprise légale).
- Différent de France SIRENE = établissement physique (unité locale).
- Documenter explicitement dans le papier.

### Fenêtre Q-tensor
- 2007 NACE Rev.1 (40 colonnes) incompatible avec NACE Rev.2 (42 colonnes, A10-mappable).
- Q-tensor commence en **2008**; 2007 absent par design.
- Ne pas interpoler 2007 dans le pipeline principal.

### Géographie
- **42 arrondissements** (pas 43): Tournai et Mouscron fusionnés en `BE_tournai_mouscron`
  dans les fichiers ONSS 2019+; séparés dans 2008–2018 → mergés lors de l'ingestion.
- La Louvière (ancien arrondissement pré-2002) présent dans ONSS → mappé à `BE_soignies`.

### Brisure méthodologique 2018
- Statbel a révisé la série TVA en 2018 (concept groupe d'entreprises).
- Flagger dans les résultats; ne bloque pas Phase 4A.

### Fenêtre de modélisation effective
- Births + stock: 2007–2020 (2007 conservé pour lag)
- Q-tensor: 2008–2020
- **Première évaluation: 2009** (lag-1 sur births 2008 disponible)

---

## Ingestion

Script: `src/data/ingest_belgium_panel.py`

- Télécharge automatiquement les archives ONSS via attributs `data-spreadsheet` HTML
- Cache local dans `raw/statbel/` et `raw/onss/`
- Preflight: `python3 src/data/phase4_preflight.py`
