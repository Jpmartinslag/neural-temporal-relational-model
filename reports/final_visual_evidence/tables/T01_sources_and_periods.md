# T01 — French sources, periods and coverage

Measured on `data/processed/france_ze2020/fr_ze2020_multisource_long_panel_v1.csv`. 'Cellules zone×période' counts distinct zone–period cells; sources published by sector contribute several rows per cell, which the 'postes sectoriels' column records. The study's own population is the 280 mainland ZE2020 of `fr_ze2020_clean_panel.csv`. 'Part observée' is the availability mask, not an imputation: absence is never a zero.

| signal | source | fréquence | période | zones | cellules zone×période | postes sectoriels | part observée | catégorie |
|---|---|---|---|---|---|---|---|---|
| Effectifs salariés privés | Urssaf | annuelle | 1998–2024 | 280 | 7560 | 1 | 1.000 | REAL_FRANCE |
| Masse salariale privée | Urssaf | annuelle | 1998–2024 | 280 | 7560 | 1 | 1.000 | REAL_FRANCE |
| Établissements employeurs | Urssaf | annuelle | 1998–2024 | 280 | 7560 | 1 | 1.000 | REAL_FRANCE |
| Taux de chômage localisé | Insee | annuelle | 2003–2025 | 280 | 6440 | 1 | 1.000 | REAL_FRANCE |
| Taux de chômage localisé (CVS) | Insee | trimestrielle | 2003–2026 | 280 | 26040 | 1 | 1.000 | REAL_FRANCE |
| Effectifs salariés privés (CVS) | Urssaf | trimestrielle | 1998–2026 | 280 | 31080 | 1 | 1.000 | REAL_FRANCE |
| Créations d'établissements | Sirene / SIDE | annuelle | 2012–2025 | 280 | 3920 | 10 | 1.000 | REAL_FRANCE |
| Établissements (Flores) | Flores | annuelle | 2017–2024 | 280 | 2240 | 18 | 0.993 | REAL_FRANCE |
| Stock d'établissements actifs | SIDE | annuelle | 2014–2024 | 280 | 3080 | 10 | 1.000 | REAL_FRANCE |
