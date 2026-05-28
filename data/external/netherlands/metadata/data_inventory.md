# Netherlands — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready

---

## Panels produits

| Fichier | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/netherlands_births_panel.csv` | 440 | 40 | 2015–2025 | Births (CBS 83631NED oprichtingen) × COROP × year |
| `processed/netherlands_stock_panel.csv` | 440 | 40 | 2015–2025 | Stock (CBS 81578NED vestigingen) × COROP × year |
| `processed/netherlands_qtensor_jobs_panel.csv` | 6000 | 40 | 2010–2024 | CBS 83582NED employee jobs × SBI-A10 × COROP × year |

Zone IDs: `CR01`–`CR40` (COROP zones). CR98/CR99 (aggregates) excluded.

---

## Sources

| Composant | Source | Table CBS | Licence |
|-----------|--------|-----------|---------|
| Births | CBS StatLine | 83631NED — oprichtingen vestigingen × SBI × regio | Open data CBS |
| Stock | CBS StatLine | 81578NED — vestigingen × SBI × regio | Open data CBS |
| Q-tensor | CBS StatLine | 83582NED — banen werknemers × SBI-A10 × COROP | Open data CBS |

API: `https://opendata.cbs.nl/ODataFeed/odata/{table}/TypedDataSet?$filter=startswith(RegioS,'CR')`

---

## Notes méthodologiques critiques

### Fenêtres
- Births et stock: CBS publie les totaux COROP (T001081) depuis **2015** seulement.
  Avant 2015: NaN par design (pas de proxy).
- Q-tensor: disponible depuis **2010** (SBI-A10 agrégats COROP).
- **Fenêtre de modélisation effective: 2016–2024** (intersection births/stock/qtensor avec lag-1).

### NaN supprimés dans le Q-tensor
- **48 cellules (0.8%)** supprimées par CBS (contrôle de divulgation statistique).
- Politique: `jobs_suppressed=1`, valeur remplie à 0. Flag `jobs_suppressed` présent dans le fichier.
- Ces cellules sont concentrées sur les secteurs rares dans les petites zones COROP.

### Concept births
- CBS 83631NED = **oprichtingen vestigingen** (nouvelles unités locales = établissements).
- Concept identique à France SIRENE (établissement physique) ✅.

### Ingestion
Script: `src/data/ingest_netherlands_panel.py`
