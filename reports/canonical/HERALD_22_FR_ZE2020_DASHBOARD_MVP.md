# HERALD 22 — France ZE2020 Territorial Dashboard

**Created:** 2026-06-24. **Status:** `DASHBOARD_READY`.

Dashboard exploratoire France/ZE2020 pour présenter, en français, la chaîne
auditée: prévision contrôlée, structure sectorielle, relations territoriales et
signaux appris par les modèles. Le dashboard ne crée pas de recommandation, ne
revendique pas de causalité, et ne présente pas la prévision comme supérieure.

## Files

- **Builder:** `src/data/france_ze2020/build_fr_ze2020_dashboard_mvp.py`
- **HTML:** `reports/dashboards/fr_ze2020_dashboard_mvp.html`

## Inputs

All inputs are read-only and already audited in the France ZE2020 track:

```text
data/processed/france_ze2020/fr_ze2020_clean_panel.csv
data/processed/france_ze2020/fr_ze2020_baseline_predictions_v1.csv
data/processed/france_ze2020/fr_ze2020_sector_panel.csv
data/processed/france_ze2020/fr_ze2020_sector_relational_features.csv
data/processed/france_ze2020/fr_ze2020_sector_graph_predictions_v1.csv
data/processed/france_ze2020/fr_ze2020_exploratory_relation_signals.csv
data/processed/france_ze2020/fr_ze2020_neural_relational_feature_signals_v1.csv
data/external/ze2020_geometry.geojson
```

The builder never reads `dynamic_stgnn_feature_panel*`,
`graph_adjacency_core_v0.csv`, `graph_adjacency_mobility_v0.csv`, or legacy
training scripts.

## Geometry

`data/external/ze2020_geometry.geojson` is used for the France map. Coverage is
verified against the canonical France ZE2020 panel: **280/280 zones covered**.
The source file has 306 features; the extra 26 correspond to Corsica/DOM zones
excluded by the canonical scope.

The choropleth uses the real ZE2020 geometries. Centroids are computed only to
draw exploratory relation edges on top of the map.

## Visual Blocks

1. **Architecture du pipeline**  
   Six filled cards in French summarize the audited chain: observed inputs,
   clean panel, causal temporal memory, ZE x sector nodes, exploratory
   relations, and integrated visual reading. This block is descriptive only:
   it does not create a new model claim and does not promote a neural result.

2. **Carte territoriale ZE2020 et graphe relationnel**  
   Dark theme aligned with the reference France dashboard. The map is clickable,
   filtered by year, and displays ZE names rather than only numeric codes. The
   relation-focused time window starts in 2017 because no stable relation graph is
   available before that year. The year control includes a play/pause button for
   dynamic reading. It overlays the active territorial relation graph for the
   selected year.

   The primary control is four named buttons -- *Vue claire*, *Relations
   fortes*, *Relations moyennes*, *Réseau complet* -- so a non-technical user
   never has to touch a slider to get a readable graph. Each button sets,
   internally, the top-k connection count, the minimum signal/stability
   thresholds, the relation intensity mode, and the path depth (1 step for the
   two simpler views, up to 6 for the full network). The underlying technical
   controls (spatial family, top-k, signal/stability sliders, intensity mode,
   path depth) remain available inside a collapsed "Mode avancé" disclosure for
   users who want to fine-tune after picking a base mode.

   A permanent legend under the controls explains the encoding without relying
   on the user opening anything: orange = direct relation, violet dotted =
   indirect path (origin -> bridge zone -> reached zone), yellow = bridge zone,
   line thickness = signal strength, line opacity = stability. Indirect
   connections are always drawn through their intermediate bridge zones rather
   than as a straight origin-to-target line -- they are exploratory graph
   paths, not direct influence claims. Hover tooltips on every edge show the
   full path (for indirect links), step count, signal, stability, and an
   explicit "non causal" caveat.

   Relation family codes (`ze_to_ze_similarity`, etc.) are translated to short
   French labels for display (table cells, hover text) via a client-side
   lookup; the underlying family code is never altered.

3. **Prévision globale contrôlée**  
   Observed series plus audited persistence/ridge predictions when available.
   This is a control panel, not the methodological claim.

4. **Structure sectorielle**  
   Sector composition by year, dominant sector, diversity, and optional
   sector-level prediction comparison from the graph smoke output.

5. **Graphe des relations détectées**  
   Displays the active relation families:
   `ze_to_ze_similarity`, `ze_to_ze_same_sector_signal`,
   `intra_ze_sector_interaction`, and `ze_sector_specialization`. The dashboard
   can rank stable relations, strongest signals, medium recurrent signals,
   strong but unstable signals, or all detected signals. It also lists indirect
   paths, path depth, bridge zones, signal intensity, and stability.

6. **Signaux appris par les modèles**  
   Separates the two model outputs:
   - neural relational MLP: permutation-importance feature signals;
  - sector graph: ZE/sector relation signals shown as graph/table relations.

7. **Structure sectorielle A10**  
   The A10 panel is filtered by the selected year and uses compact horizontal
   bars with both sector code and full sector label, rather than a static
   all-year stacked chart. Bars are colored from a single sector-code -> color
   index computed once from the canonical sector panel, with a matching legend
   chip row underneath; the same index colors the map's "Secteur dominant"
   mode, so a given sector keeps the same color everywhere in the dashboard
   instead of being re-derived (and re-colored) per year.

8. **Painel latéral de zone**  
   Selecting a ZE shows, in one place: name, selected year, observed value,
   Ridge control prediction, dominant sector, and the dominant neural-model
   signal for that year (if available), followed by the top direct relations
   and top indirect paths for the current filters.

9. **Tableau comparatif intégré**  
   The previous France comparison dashboard
   `reports/dashboards/herald_france_final_dashboard.html` is embedded inside
   this dashboard as an isolated `iframe srcdoc` payload. This keeps the older
   article-style architecture/comparison view available for presentation while
   preventing its JavaScript state from mixing with the ZE2020 relational
   panel. The embedded copy is renamed in visible text from HERALD to "Modèle
   territorial" so the France ZE2020 MVP page itself does not present HERALD as
   its display name.

## Methodological Boundaries

- Relation signals are exploratory associations, not causal effects.
- The neural feature signals are feature-importance summaries, not entity-to-entity
  labels created by the model.
- The sector graph signals provide the explicit ZE/sector relations currently
  available.
- Recommendation or policy-action language is intentionally absent.
- Missing relation families (`sector_to_sector_comovement`,
  `temporal_precedence_signal`) remain documented gaps.

## Verification

Structural dashboard tests verify:

- no recommendation/policy-action columns or language;
- no causal-effect/causal-impact language;
- no visible draft wording such as "MVP", "smoke", "debug", "prototype";
- French dashboard labels are present;
- the architecture block is filled, not a placeholder;
- the integrated comparison dashboard is embedded and renamed;
- annual slider and spatial graph layer exist;
- the simple network-mode buttons (Vue claire / Relations fortes / Relations
  moyennes / Réseau complet) and the collapsed advanced-controls disclosure
  are present;
- the permanent edge legend and the sector color legend/index are present;
- ZE2020 geometry covers all 280 canonical zones;
- no forbidden legacy inputs are read.

Latest relevant test command:

```bash
python3 -m pytest -q tests/test_fr_ze2020_dashboard_mvp.py \
  tests/test_herald_artifact_registry.py \
  tests/test_herald_france_lineage_consistency.py
```

Result: `30 passed` for the dashboard test file in the latest dashboard-only
validation pass.
