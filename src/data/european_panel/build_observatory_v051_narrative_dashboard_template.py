"""
HTML/CSS/JS template for the HERALD Observatory v0.5.1 dashboard.

Kept in its own module purely to keep build_observatory_v051_narrative_dashboard.py
readable — this is still part of the v0.5.1 builder, not a shared/v0.4 file.
"""
from __future__ import annotations

import json


def render_template(sector_labels_fr: dict, sectors_order: list, gsap_tag: str, **kw) -> str:
    plotly_tag = kw["plotly_tag"]
    sector_options_html = "".join(
        f'<option value="{s}">{sector_labels_fr[s]} ({s})</option>' for s in sectors_order
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HERALD — Observatoire économique territorial</title>
{plotly_tag}
{gsap_tag}
<style>
{_CSS}
</style>
</head>
<body>
<div class="wrap">

{_html_header()}
{_html_method_section()}
{_html_evidence_summary(kw['n_fr'], kw['n_nl'], kw['n_pt'], kw['n_valid_relations'], kw['n_blocked_relations'])}
{_html_prediction_section()}
{_html_map_section(sector_options_html)}
{_html_relational_layer_section()}
{_html_graph_section()}
{_html_basins_legend_section()}
{_html_technical_details_section()}

</div>

<script>
{_js_constants(**kw)}
{_JS_BODY}
</script>
</body>
</html>
"""


def _html_header() -> str:
    return """
<header class="hero">
  <h1>HERALD — observatoire économique territorial</h1>
  <div class="subtitle">
    Prévoir l'activité, suivre les territoires et identifier les relations sectorielles
    dans le temps.
  </div>
</header>
"""


def _html_method_section() -> str:
    return """
<!-- ── PART C: ARCHITECTURE / MÉTHODE — opens the experience, before the map ── -->
<div class="section method-section">
  <div class="section-title">Méthode HERALD</div>
  <div class="section-note">
    HERALD combine une prévision statistique simple, une recherche de relations entre secteurs,
    une étape de validation stricte, et une restitution sur carte et sur graphe. Chaque étape ci-dessous
    correspond à une transformation auditable des données, pas à une boîte noire.
  </div>
  <div class="method-diagram">
    <div class="method-step">
      <div class="step-num">1</div>
      <div class="step-title">Données territoriales</div>
      <div class="step-desc">pays × territoire × secteur × année</div>
    </div>
    <div class="method-arrow">&#8594;</div>
    <div class="method-step">
      <div class="step-num">2</div>
      <div class="step-title">Prévision locale</div>
      <div class="step-desc">observé vs attendu (persistance / Ridge)</div>
    </div>
    <div class="method-arrow">&#8594;</div>
    <div class="method-step">
      <div class="step-num">3</div>
      <div class="step-title">État économique</div>
      <div class="step-desc">croissance, stabilité, recul</div>
    </div>
    <div class="method-arrow">&#8594;</div>
    <div class="method-step">
      <div class="step-num">4</div>
      <div class="step-title">Relations sectorielles</div>
      <div class="step-desc">précédence temporelle entre secteurs</div>
    </div>
    <div class="method-arrow">&#8594;</div>
    <div class="method-step">
      <div class="step-num">5</div>
      <div class="step-title">Niveau d'évidence</div>
      <div class="step-desc">observé, supporté, exploratoire, rejeté</div>
    </div>
    <div class="method-arrow">&#8594;</div>
    <div class="method-step step-final">
      <div class="step-num">6</div>
      <div class="step-title">Signaux pour la décision</div>
      <div class="step-desc">carte, graphe, résumé d'évidence</div>
    </div>
  </div>

  <div class="method-components">
    <div class="component-card">
      <div class="component-title">Base statistique</div>
      <div class="component-desc">Persistance (dernière valeur observée) et régression Ridge AR(1)
      (utilisant uniquement les données jusqu'à l'année précédente, jamais l'année à prévoir).
      C'est la couche de prévision principale,
      validée pour la France (ZE2020), les Pays-Bas (COROP) et désormais le Portugal (municipalités).</div>
    </div>
    <div class="component-card">
      <div class="component-title">Couche relationnelle / candidats</div>
      <div class="component-desc">Recherche de motifs de précédence temporelle entre secteurs
      (un secteur dont l'évolution précède celle d'un autre). Les candidats neuronaux/relationnels
      restent en validation — voir la section « Couche relationnelle » ci-dessous.</div>
    </div>
    <div class="component-card">
      <div class="component-title">Validation</div>
      <div class="component-desc">Contrôles temporels (fenêtres glissantes), tests de permutation,
      robustesse à la COVID, réplication entre fenêtres et pays. Seules les relations qui passent
      ces contrôles deviennent une évidence affichée.</div>
    </div>
    <div class="component-card">
      <div class="component-title">Sortie</div>
      <div class="component-desc">Carte territoriale (état, écart à l'attendu, bassins économiques),
      graphe des relations sectorielles, résumé d'évidence en langage clair.</div>
    </div>
  </div>
</div>
"""


def _html_evidence_summary(n_fr: int, n_nl: int, n_pt: int, n_valid: int, n_blocked: int) -> str:
    return f"""
<!-- ── PART H: résumé d'évidence (remplace les cartes KPI génériques) ── -->
<div class="section">
  <div class="section-title">Résumé d'évidence</div>
  <div class="section-note">Ce que cet observatoire couvre aujourd'hui, en une phrase par élément — pas un tableau de bord générique.</div>
  <div class="evidence-summary" id="evidence-summary">
    <div class="evidence-chip">3 pays comparés (France, Pays-Bas, Portugal)</div>
    <div class="evidence-chip">France et Portugal à granularité fine ({n_fr} zones d'emploi / {n_pt} communes)</div>
    <div class="evidence-chip">Pays-Bas : relations observées au niveau COROP ({n_nl} régions)</div>
    <div class="evidence-chip">{n_valid} relations sectorielles validées</div>
    <div class="evidence-chip evidence-chip-muted">{n_blocked} relations proxy rejetées (Pays-Bas, niveau gemeente)</div>
    <div class="evidence-chip">Prévision intégrée pour les 3 pays, y compris le Portugal au niveau municipal</div>
  </div>
</div>
"""


def _html_prediction_section() -> str:
    return """
<!-- ── PART D: PRÉVISION LOCALE — couche centrale ── -->
<div class="section">
  <div class="section-title">Prévision locale</div>
  <div class="section-note">
    Pour chaque territoire et secteur, l'observatoire compare la valeur observée à une valeur
    attendue calculée par une méthode simple sans anticipation (persistance ou régression Ridge AR(1),
    utilisant uniquement les données jusqu'à l'année précédente). Cette comparaison indique si un
    territoire est au-dessus, à, ou en dessous de sa tendance récente — ce n'est pas une garantie
    sur l'avenir.
  </div>
  <div id="prediction-gap-banner" class="info-banner"></div>
  <div class="card scroll-table">
    <table class="dense" id="prediction-table">
      <thead><tr><th>Territoire</th><th>Secteur</th><th>Année</th><th>Observé</th><th>Attendu</th><th>Écart</th><th>État</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>
"""


def _html_map_section(sector_options_html: str) -> str:
    return f"""
<!-- ── CARTE — visualisation principale ── -->
<div class="section">
  <div class="section-title">Carte territoriale</div>
  <div class="section-note">
    Choisissez un pays, un secteur et une année. La carte change directement de couleur pour montrer
    l'état économique, l'écart à l'attendu, ou les bassins de dynamique similaire — il n'y a pas de
    graphique séparé, la carte <em>est</em> la visualisation. Utilisez la ligne de temps pour faire défiler
    les années comme un film.
  </div>
  <div class="controls">
    <label>Pays
      <select id="map-country" onchange="handleCountryChange()">
        <option value="FR">France</option>
        <option value="NL">Pays-Bas</option>
        <option value="PT">Portugal</option>
      </select>
    </label>
    <label>Secteur
      <select id="map-sector" onchange="handleMapSectorChange()">
        <option value="ALL">Tous les secteurs (le plus marqué)</option>
        {sector_options_html}
      </select>
    </label>
    <label>Mode d'affichage
      <select id="map-view" onchange="renderTerritoryView()">
        <option value="state">État économique</option>
        <option value="velocity">Vitesse de variation</option>
        <option value="prediction">Écart à l'attendu</option>
        <option value="basins">Bassins économiques</option>
      </select>
    </label>
    <span id="map-evidence-badge"></span>
  </div>
  <div class="legend-row" id="map-legend"></div>
  <div class="map-layout">
    <div class="card" id="map-card" style="min-height:520px"><div id="map-plot" style="height:520px"></div></div>
    <div class="side-panel" id="map-side">
      <h3>Détail du territoire</h3>
      <div class="side-empty" id="map-side-empty">Cliquez sur un territoire pour voir ses secteurs, sa tendance, sa prévision et son évidence.</div>
      <div id="map-side-content" style="display:none"></div>
    </div>
  </div>
  <div class="controls" style="margin-top:12px">
    <button id="play-pause-btn" onclick="togglePlay()">&#9654; Lecture</button>
    <span style="display:flex;align-items:center;gap:8px;flex:1;min-width:240px;">
      <input type="range" id="year-slider" min="0" max="0" value="0" step="1" style="flex:1" oninput="onYearSliderInput()">
      <span id="year-label" style="font-size:13px;color:var(--muted);min-width:50px;text-align:right"></span>
    </span>
  </div>
  <div id="basins-note" class="basins-note" style="display:none">
    <strong>Bassins économiques</strong> — zones de concentration économique calculées à partir de la
    vitesse moyenne de variation observée par territoire et par année (quantile au sein de chaque pays-année).
    Ce n'est pas un regroupement structurel : c'est une simple description de territoires aux dynamiques proches.
  </div>
</div>
"""


def _html_relational_layer_section() -> str:
    return """
<!-- ── PART G: COUCHE RELATIONNELLE (honnête, séparée des relations validées) ── -->
<div class="section">
  <div class="section-title">Couche relationnelle</div>
  <div class="section-note">
    La couche statistique prévoit la valeur attendue d'un territoire. La couche relationnelle
    recherche des motifs entre secteurs : un secteur dont l'évolution semble précéder celle d'un
    autre. Une couche neuronale/relationnelle peut proposer des relations candidates ; seules les
    relations qui passent la validation (fenêtres temporelles, permutations, robustesse) deviennent
    une évidence affichée dans le graphe ci-dessous. Les relations proxy bloquées sont conservées
    uniquement à des fins d'audit.
  </div>
  <div class="relational-diagram">
    <div class="rel-step">Séries sectorielles</div>
    <div class="method-arrow">&#8594;</div>
    <div class="rel-step">Représentation relationnelle</div>
    <div class="method-arrow">&#8594;</div>
    <div class="rel-step">Candidats</div>
    <div class="method-arrow">&#8594;</div>
    <div class="rel-step">Validation</div>
    <div class="method-arrow">&#8594;</div>
    <div class="rel-step rel-step-final">Relations affichées</div>
  </div>
  <div class="relational-counts" id="relational-counts"></div>
  <div class="info-banner-neutral">
    La couche relationnelle est représentée ici par les relations validées (Phase 7) ; les candidats
    neuronaux restent en validation et ne sont pas mélangés avec les relations validées.
  </div>
</div>
"""


def _html_graph_section() -> str:
    return """
<!-- ── GRAPHE DES RELATIONS SECTORIELLES (connecté à la carte) ── -->
<div class="section">
  <div class="section-title">Relations sectorielles</div>
  <div class="section-note">
    Chaque flèche relie deux secteurs observés évoluant de façon liée dans le temps — l'un semble
    précéder l'autre. Il s'agit d'une <strong>association temporelle observée</strong>, jamais d'une
    recommandation automatique. Cliquer sur une relation filtre la carte sur le pays et la fenêtre
    correspondants.
  </div>
  <div class="controls">
    <label>Pays <select id="graph-country" onchange="renderGraph();syncMapFromGraph()">
      <option value="ALL">Tous les pays</option>
      <option value="FR">France</option>
      <option value="NL">Pays-Bas</option>
      <option value="PT">Portugal</option>
    </select></label>
    <label>Niveau d'évidence <select id="graph-evidence" onchange="renderGraph()">
      <option value="ALL">Tous les niveaux</option>
      <option value="Validé">Validé</option>
      <option value="Supporté">Supporté</option>
      <option value="Exploratoire">Exploratoire</option>
    </select></label>
    <label>Mode
      <select id="graph-mode" onchange="updateWindowLabel();renderGraph()">
        <option value="persistent">Toutes les relations (estompées) + fenêtre active</option>
        <option value="current">Fenêtre active uniquement</option>
      </select>
    </label>
    <span id="edge-count-label" style="color:var(--muted);font-size:12.5px;"></span>
  </div>
  <div class="controls">
    <button id="graph-play-btn" onclick="toggleGraphPlay()">&#9654; Lecture de la ligne de temps</button>
    <span style="display:flex;align-items:center;gap:8px;flex:1;min-width:240px;">
      <input type="range" id="window-slider" min="0" max="0" value="0" step="1" style="flex:1" oninput="onWindowSliderInput()">
      <span id="window-label" style="font-size:13px;color:var(--muted);min-width:110px;text-align:right"></span>
    </span>
  </div>
  <div class="legend-row">
    <div class="legend-item"><div class="legend-dot" style="background:var(--pos)"></div>Même direction</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--neg)"></div>Direction opposée</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--robust)"></div>Validé</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--supported);opacity:.8"></div>Supporté</div>
    <div class="legend-item"><div class="legend-line" style="background:var(--exploratory);opacity:.55"></div>Exploratoire</div>
  </div>
  <div class="graph-layout">
    <div class="card"><div id="sector-graph" style="height:480px"></div></div>
    <div class="side-panel" id="edge-panel">
      <h3>Détail de la relation</h3>
      <div class="side-empty" id="edge-panel-empty">Cliquez sur une flèche pour voir l'explication en langage clair et le contexte territorial.</div>
      <div id="edge-panel-content" style="display:none"></div>
    </div>
  </div>
  <div class="section-note" style="margin-top:14px">Vue d'appui : les mêmes relations selon les fenêtres temporelles (visuel secondaire).</div>
  <div class="card"><div id="relation-heatmap" style="height:280px"></div></div>
</div>
"""


def _html_basins_legend_section() -> str:
    return """
<!-- ── BADGES D'ÉVIDENCE ── -->
<div class="section">
  <div class="section-title">Badges d'évidence</div>
  <div class="section-note">Chaque donnée affichée porte un badge indiquant son niveau d'évidence.</div>
  <div class="legend-row">
    <div class="legend-item"><span class="badge badge-observed">Observé</span> mesuré directement</div>
    <div class="legend-item"><span class="badge badge-proxy">Proxy territorial</span> estimé, affiché pour contexte uniquement — jamais utilisé pour les relations</div>
    <div class="legend-item"><span class="badge badge-robust">Validé</span> évidence la plus solide</div>
    <div class="legend-item"><span class="badge badge-supported">Supporté</span> observé, avec contrôles de robustesse supplémentaires</div>
    <div class="legend-item"><span class="badge badge-exploratory">Exploratoire</span> observé, signal plus faible, non utilisable pour décider</div>
    <div class="legend-item"><span class="badge badge-blocked">Rejeté</span> détecté par un filtrage automatique mais méthodologiquement invalide — conservé pour audit</div>
    <div class="legend-item"><span class="badge badge-absent">Non disponible</span> secteur structurellement absent pour ce pays</div>
  </div>
</div>
"""


def _html_technical_details_section() -> str:
    return """
<!-- ── PART K: DÉTAILS MÉTHODOLOGIQUES (collapsible, technique) ── -->
<div class="section">
  <div class="section-title">Détails méthodologiques</div>
  <details class="tech">
    <summary>Relations proxy rejetées (audit uniquement, jamais une découverte)</summary>
    <div class="section-note" style="margin-top:8px">
      121 relations proxy au niveau gemeente (Pays-Bas) avaient été repérées par un filtrage
      automatique, mais un contrôle structurel a montré que la méthode d'estimation sous-jacente
      injecte un bruit sans rapport avec une précédence réelle entre secteurs. Elles sont conservées
      ici uniquement à des fins d'audit, ne sont jamais utilisées pour l'entraînement, et n'apparaissent
      jamais dans le graphe des relations ci-dessus.
    </div>
    <div class="card scroll-table">
      <table class="dense" id="blocked-table">
        <thead><tr><th>De</th><th>Vers</th><th>beta</th><th>Fenêtre</th><th>Motif</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </details>
  <details class="tech">
    <summary>Détail statistique (beta, q_fdr, bss, type d'évidence, sources, sommes de contrôle)</summary>
    <div class="kpis" id="evidence-kpis" style="margin-top:10px"></div>
    <div class="card" style="margin-top:10px">
      <div class="side-field"><span class="lbl">Références DEC</span><span id="dec-refs"></span></div>
      <div class="side-field"><span class="lbl">Somme de contrôle territory_view.csv (16)</span><span id="chk-territory"></span></div>
      <div class="side-field"><span class="lbl">Somme de contrôle relation_view.csv (16)</span><span id="chk-relation"></span></div>
      <div class="side-field"><span class="lbl">Somme de contrôle blocked_proxy_edges (16)</span><span id="chk-blocked"></span></div>
    </div>
    <table class="dense" style="margin-top:10px">
      <thead><tr><th>De&#8594;Vers</th><th>Pays</th><th>beta</th><th>q_fdr</th><th>bss</th><th>Fenêtre</th><th>label_class</th><th>evidence_type</th><th>allowed_for_training_label</th></tr></thead>
      <tbody id="tech-relation-tbody"></tbody>
    </table>
    <div class="footnote">
      Une relation orientée indique une précédence prédictive (la croissance décalée d'un secteur
      s'associe statistiquement à celle d'un autre), jamais une preuve causale structurelle.
      Ces relations n'établissent pas de lien de causalité structurelle.
    </div>
  </details>
  <details class="tech">
    <summary>Fichiers source / export</summary>
    <div class="links-row" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">
      <a href="../../data/processed/herald_observatory_v051_narrative/territory_view.csv" class="src-link">territory_view.csv</a>
      <a href="../../data/processed/herald_observatory_v051_narrative/relation_view.csv" class="src-link">relation_view.csv</a>
      <a href="../../data/processed/herald_observatory_v051_narrative/prediction_view.csv" class="src-link">prediction_view.csv</a>
      <a href="../../data/processed/herald_observatory_v051_narrative/pt_municipal_prediction_view.csv" class="src-link">pt_municipal_prediction_view.csv</a>
      <a href="../../data/processed/herald_observatory_v051_narrative/manifest.json" class="src-link">manifest.json</a>
    </div>
    <div style="color:var(--muted);font-size:11px;margin-top:8px;">
      Dépendance Plotly : {plotly_dep_placeholder}.
      Les transitions animées utilisent GSAP (chargé depuis un CDN, utilisé uniquement pour la lecture
      de la ligne de temps et les transitions de couleur de la carte — jamais une animation décorative).
    </div>
  </details>
</div>
""".replace("{plotly_dep_placeholder}", "{plotly_dep}")


_CSS = """
:root {
  --bg:#0f1220; --panel:#171b2d; --panel2:#20253a; --line:#30364f;
  --text:#eef2ff; --muted:#9aa4bf; --good:#26a69a; --bad:#ef5350;
  --stag:#9aa4bf; --pos:#26a69a; --neg:#ef5350;
  --robust:#4aa3ff; --supported:#4aa3ff; --exploratory:#ffd180;
  --observed:#26a69a; --proxy:#b39ddb; --blocked:#5a5f78;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;font-size:14px;}
.wrap{max-width:1600px;margin:0 auto;padding:20px;}
.hero{padding:10px 0 18px;border-bottom:1px solid var(--line);margin-bottom:18px;}
h1{font-size:28px;font-weight:780;margin-bottom:8px;}
h2{font-size:18px;font-weight:740;}
.subtitle{color:var(--muted);font-size:15px;line-height:1.6;max-width:920px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin:0 0 18px;}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;}
.kpi .v{font-size:22px;font-weight:760;}
.kpi .l{color:var(--muted);font-size:12px;margin-top:2px;}
.section{margin-top:34px;}
.section-title{font-size:20px;font-weight:740;margin-bottom:6px;}
.section-note{color:var(--muted);font-size:13.5px;line-height:1.55;max-width:980px;margin-bottom:12px;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px;}
select,button,input{background:var(--panel2);color:var(--text);border:1px solid var(--line);
  border-radius:6px;padding:7px 11px;font-size:13px;cursor:pointer;}
button.primary{background:var(--robust);border-color:var(--robust);color:#0f1220;font-weight:700;}
.map-layout{display:grid;grid-template-columns:1fr 380px;gap:14px;align-items:start;}
.side-panel{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:16px;}
.side-panel h3{font-size:15px;font-weight:730;margin-bottom:10px;}
.side-field{display:flex;justify-content:space-between;margin-bottom:7px;font-size:13px;gap:10px;}
.side-field .lbl{color:var(--muted);flex-shrink:0;}
.side-empty{color:var(--muted);font-size:13px;padding:20px 0;text-align:center;}
.badge{display:inline-block;border-radius:999px;padding:3px 10px;font-size:11.5px;font-weight:700;border:1px solid;}
.badge-observed{color:var(--observed);border-color:var(--observed);background:#0a1e1a;}
.badge-proxy{color:var(--proxy);border-color:var(--proxy);background:#1c1530;}
.badge-robust{color:var(--robust);border-color:var(--robust);background:#0a1a2e;}
.badge-supported{color:var(--supported);border-color:var(--supported);background:#0a1a2e;}
.badge-exploratory{color:var(--exploratory);border-color:var(--exploratory);background:#1e1a0a;}
.badge-blocked{color:var(--blocked);border-color:var(--blocked);background:#1a1a22;}
.badge-pos{color:var(--pos);border-color:var(--pos);background:#0a1e1a;}
.badge-neg{color:var(--neg);border-color:var(--neg);background:#1e0a0a;}
.badge-absent{color:#8a8fa8;border-color:#4a4f6a;background:#181a26;}
.legend-row{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;font-size:12.5px;}
.legend-item{display:flex;align-items:center;gap:5px;color:var(--muted);}
.legend-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0;}
.legend-line{width:24px;height:3px;flex-shrink:0;}
.narrative-sentence{background:var(--panel2);border-left:3px solid var(--robust);border-radius:6px;
  padding:12px 14px;font-size:14px;line-height:1.5;margin:10px 0;}
.footnote{color:#6a7090;font-size:11px;margin-top:6px;font-style:italic;}
.method-section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;}
.method-diagram{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0;}
.method-step{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:14px 16px;
  font-size:13px;text-align:center;flex:1;min-width:150px;}
.method-step.step-final{border-color:var(--robust);}
.step-num{color:var(--robust);font-weight:760;font-size:13px;margin-bottom:6px;}
.step-title{font-weight:700;margin-bottom:4px;}
.step-desc{color:var(--muted);font-size:11.5px;}
.method-arrow{color:var(--muted);font-size:18px;}
.method-components{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:18px;}
.component-card{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:14px;}
.component-title{font-weight:730;font-size:13.5px;margin-bottom:6px;color:var(--robust);}
.component-desc{color:var(--muted);font-size:12.5px;line-height:1.5;}
.evidence-summary{display:flex;flex-wrap:wrap;gap:10px;}
.evidence-chip{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:9px 16px;
  font-size:13px;}
.evidence-chip-muted{color:var(--muted);}
.relational-diagram{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0;}
.rel-step{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 14px;
  font-size:12.5px;text-align:center;flex:1;min-width:130px;}
.rel-step-final{border-color:var(--robust);}
.relational-counts{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px;}
.info-banner{background:#10243a;border:1px solid #1d4068;border-radius:8px;padding:10px 14px;
  font-size:13px;color:#bcdcff;margin-bottom:10px;}
.info-banner-neutral{background:#16182a;border:1px dashed var(--line);border-radius:8px;padding:12px 14px;
  color:var(--muted);font-size:13px;margin-top:6px;}
details.tech{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin-top:10px;}
details.tech summary{cursor:pointer;font-weight:700;font-size:13px;color:var(--muted);}
details.tech table.dense{margin-top:10px;}
table.dense{width:100%;border-collapse:collapse;font-size:12.5px;}
table.dense th{text-align:left;color:var(--muted);font-weight:600;padding:6px 8px;
  border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);}
table.dense td{padding:5px 8px;border-bottom:1px solid #232842;}
.scroll-table{max-height:380px;overflow-y:auto;}
.state-growth{color:var(--good);}
.state-falling{color:var(--bad);}
.state-stable{color:var(--stag);}
.state-noevidence{color:#4a4f6a;}
.basins-note{background:#16182a;border:1px dashed var(--line);border-radius:8px;padding:12px 14px;
  color:var(--muted);font-size:13px;margin-top:10px;}
.graph-layout{display:grid;grid-template-columns:1fr 340px;gap:14px;}
.src-link{color:var(--robust);text-decoration:none;font-size:12px;border:1px solid var(--line);
  border-radius:5px;padding:6px 10px;background:var(--panel2);}
select:disabled{opacity:.4;cursor:not-allowed;}
@media(max-width:950px){
  .map-layout,.graph-layout{grid-template-columns:1fr;}
  .kpis{grid-template-columns:repeat(2,1fr);}
  .method-diagram,.relational-diagram{flex-direction:column;}
  .method-arrow{transform:rotate(90deg);}
}
"""


def _js_constants(**kw) -> str:
    return f"""
const REGION_META = {kw['region_meta_js']};
const MAP_STATE = {kw['map_state_js']};
const NODE_POS = {kw['node_pos_js']};
const SECTOR_LABELS = {kw['sector_labels_js']};
const GEO_FR = {kw['geo_fr_js']};
const GEO_NL = {kw['geo_nl_js']};
const GEO_PT = {kw['geo_pt_js']};
const GEO = {{FR: GEO_FR, NL: GEO_NL, PT: GEO_PT}};
const RELATION_EDGES = {kw['relation_edges_js']};
const RELATION_TIMELINE = {kw['relation_timeline_js']};
const BLOCKED_EDGES = {kw['blocked_edges_js']};
const PREDICTION_LOOKUP = {kw['prediction_lookup_js']};
const ECONOMIC_BASINS = {kw['economic_basins_js']};
const SECTOR_VIEW_ROWS = {kw['sector_view_js']};
const MANIFEST = {kw['manifest_js']};
const MAP_CONFIG = {kw['map_config_js']};
const CSV_CHECKSUMS = {kw['csv_checksums_js']};
const N_TERRITORIES = {kw['n_territories_js']};
const N_VALID_RELATIONS = {kw['n_valid_relations']};
const N_BLOCKED_RELATIONS = {kw['n_blocked_relations']};
const N_SECTORS_TRACKED = {kw['n_sectors_tracked']};
const PT_KZ_STRUCTURAL_ABSENT = {kw['pt_kz_structural_absent']};
const PREDICTION_COUNTRIES = {kw['prediction_countries_js']};
const PT_MAP_STATUS = {json.dumps(kw['pt_map_status'])};
const PT_MUNICIPAL_PREDICTION_ROWS = {kw['pt_municipal_rows']};
"""


_JS_BODY = r"""
const SECTORS = Object.keys(SECTOR_LABELS);
const STATE_COLORS = {'Croissance':'#26a69a','Stable':'#9aa4bf','Recul':'#ef5350',
  'Donnée insuffisante':'#3a3f56','Secteur non disponible pour le Portugal':'#2a2c3a'};
const STATE_NUM = {'Croissance':1,'Stable':0,'Recul':-1,'Donnée insuffisante':null,
  'Secteur non disponible pour le Portugal':null};
const BASE_LAYOUT = {
  paper_bgcolor:'#171b2d', plot_bgcolor:'#171b2d',
  font:{color:'#eef2ff',family:'Inter,Segoe UI,Arial,sans-serif',size:12},
  margin:{l:50,r:20,t:30,b:40},
  hoverlabel:{bgcolor:'#20253a',bordercolor:'#30364f',font:{color:'#eef2ff'}},
};

let PLAY_INTERVAL = null;
let GRAPH_PLAY_INTERVAL = null;
let HIGHLIGHT_SECTOR = null;
let YEARS_BY_COUNTRY = {};
let GRAPH_MAP_FILTER = null; // {country, window} set when a relation is clicked

// ── Évidence relationnelle (Part G counts) ─────────────────────────
function renderRelationalCounts() {
  const nValidated = N_VALID_RELATIONS;
  const nBlocked = N_BLOCKED_RELATIONS;
  const el = document.getElementById('relational-counts');
  el.innerHTML = [
    ['Relations candidates (couche neuronale)', 'aucun jeu de données candidat neuronal disponible dans ce dépôt'],
    ['Relations validées (Phase 7)', nValidated],
    ['Relations proxy rejetées (audit uniquement)', nBlocked],
  ].map(([l,v]) => `<div class="evidence-chip">${l} : ${v}</div>`).join('');
}

// ── Bandeau prévision (Part B/D) ────────────────────────────────────
function renderPredictionBanner() {
  const banner = document.getElementById('prediction-gap-banner');
  banner.textContent = 'Prévision validée pour : ' + PREDICTION_COUNTRIES.join(', ') +
    '. Le Portugal est désormais intégré au niveau communal (' + PT_MUNICIPAL_PREDICTION_ROWS +
    ' lignes), via persistance/Ridge sans anticipation sur le panel observé — sans proxy, sans calcul HPC.';
}

// ── PT/KZ handling ──────────────────────────────────────────────────
function refreshSectorOptionsForCountry(country) {
  const sel = document.getElementById('map-sector');
  Array.from(sel.options).forEach(opt => {
    if (opt.value === 'KZ') {
      const disable = country === 'PT' && PT_KZ_STRUCTURAL_ABSENT;
      opt.disabled = disable;
      opt.title = disable ? 'Non disponible pour le Portugal (secteur structurellement absent)' : '';
      opt.textContent = disable
        ? SECTOR_LABELS['KZ'] + ' (KZ) — non disponible pour le Portugal'
        : SECTOR_LABELS['KZ'] + ' (KZ)';
      if (disable && sel.value === 'KZ') sel.value = 'ALL';
    }
  });
}

// ── Map / territory view ────────────────────────────────────────────
function populateYearOptions(country) {
  const years = new Set();
  const regions = MAP_STATE[country] || {};
  Object.values(regions).forEach(secMap => Object.values(secMap).forEach(yearMap =>
    Object.keys(yearMap).forEach(y => years.add(parseInt(y)))));
  YEARS_BY_COUNTRY[country] = [...years].sort((a,b)=>a-b);
  const slider = document.getElementById('year-slider');
  slider.min = 0; slider.max = Math.max(0, YEARS_BY_COUNTRY[country].length-1);
  slider.value = slider.max;
  updateYearLabel();
}

function currentYear() {
  const country = document.getElementById('map-country').value;
  const idx = parseInt(document.getElementById('year-slider').value);
  const years = YEARS_BY_COUNTRY[country] || [];
  return years[idx] || years[years.length-1];
}

function updateYearLabel() {
  document.getElementById('year-label').textContent = currentYear() || 'n/a';
}

function onYearSliderInput() { updateYearLabel(); renderTerritoryView(); }

function togglePlay() {
  const btn = document.getElementById('play-pause-btn');
  if (PLAY_INTERVAL) { clearInterval(PLAY_INTERVAL); PLAY_INTERVAL=null; btn.innerHTML='&#9654; Lecture'; return; }
  btn.innerHTML = '&#10074;&#10074; Pause';
  PLAY_INTERVAL = setInterval(() => {
    const slider = document.getElementById('year-slider');
    let idx = parseInt(slider.value) + 1;
    if (idx > parseInt(slider.max)) idx = 0;
    slider.value = idx;
    onYearSliderInput();
  }, 1000);
}

function handleCountryChange() {
  const country = document.getElementById('map-country').value;
  refreshSectorOptionsForCountry(country);
  populateYearOptions(country);
  renderTerritoryView();
  document.getElementById('graph-country').value = country;
  renderGraph();
}

function handleMapSectorChange() {
  const sector = document.getElementById('map-sector').value;
  HIGHLIGHT_SECTOR = sector === 'ALL' ? null : sector;
  renderTerritoryView();
  renderGraph();
}

function renderTerritoryView() {
  const country = document.getElementById('map-country').value;
  const view = document.getElementById('map-view').value;
  document.getElementById('basins-note').style.display = view === 'basins' ? 'block' : 'none';
  const isMapped = ['FR','NL','PT'].includes(country) && GEO[country] && GEO[country].features
    && GEO[country].features.length > 0;
  document.getElementById('map-card').innerHTML = isMapped
    ? '<div id="map-plot" style="height:520px"></div>'
    : '<div class="scroll-table"><table class="dense" id="territory-table"><thead><tr>'
      + '<th>Territoire</th><th>Secteur</th><th>État</th><th>Vitesse</th><th>Évidence</th></tr></thead><tbody></tbody></table></div>';
  if (['FR','NL','PT'].includes(country) && !isMapped) {
    document.getElementById('map-card').insertAdjacentHTML('afterbegin',
      '<div class="info-banner">Géométrie de la carte indisponible pour cette vue — tableau affiché plutôt qu\'une carte fabriquée.</div>');
  }
  const badgeClass = 'badge-observed';
  document.getElementById('map-evidence-badge').innerHTML = `<span class="badge ${badgeClass}">Observé</span>`;
  if (isMapped) renderMap(country, view); else renderTerritoryTable(country, view);
}

// MAP_STATE cell array layout: [state_human, velocity, value, evidence_badge]
const CELL_STATE=0, CELL_VEL=1, CELL_VALUE=2, CELL_BADGE=3;
// PREDICTION_LOOKUP cell array layout: [observed, expected, difference, trend_state]
const PRED_OBS=0, PRED_EXP=1, PRED_DIFF=2, PRED_TREND=3;

function cellForRegionSectorYear(country, rid, sector, year) {
  const regions = MAP_STATE[country] || {};
  const secMap = regions[rid] || {};
  return (secMap[sector]||{})[year] || null;
}

function bestSectorForRegion(country, rid, year) {
  const regions = MAP_STATE[country] || {};
  const secMap = regions[rid] || {};
  let best=null, bestAbs=-1, bestCell=null;
  Object.keys(secMap).forEach(s => {
    const cell = (secMap[s]||{})[year];
    if (cell && cell[CELL_VEL] != null && Math.abs(cell[CELL_VEL]) > bestAbs) { bestAbs=Math.abs(cell[CELL_VEL]); best=s; bestCell=cell; }
  });
  return [best, bestCell];
}

function predictionLookup(country, rid, sector, year) {
  const cell = (((PREDICTION_LOOKUP[country]||{})[String(rid)]||{})[sector]||{})[year];
  return cell || null;
}

function basinScore(country, rid, year) {
  const yearMap = (ECONOMIC_BASINS[country]||{})[String(year)] || {};
  return yearMap[String(rid)] || null; // [score, quantile]
}

function renderMap(country, view) {
  const year = currentYear();
  const sector = document.getElementById('map-sector').value;
  const regions = MAP_STATE[country] || {};
  const meta = REGION_META[country] || {};
  const geo = GEO[country];

  const locations=[], z=[], text=[], customdata=[];
  Object.keys(regions).forEach(rid => {
    let shownSector = sector, cell = null;
    if (sector === 'ALL') { const [b,c] = bestSectorForRegion(country, rid, year); shownSector=b; cell=c; }
    else { cell = cellForRegionSectorYear(country, rid, sector, year); }
    const name = (meta[rid]||{}).name || rid;
    locations.push(rid);

    if (view === 'basins') {
      const b = basinScore(country, rid, year);
      if (!b) { z.push(null); customdata.push({rid, name, sector: shownSector, year, value:null, state:'Donnée insuffisante', vel:null}); text.push(name + ': donnée insuffisante'); return; }
      z.push(b[1]);
      customdata.push({rid, name, sector: shownSector, year, value:b[0], state:cell?cell[CELL_STATE]:'Donnée insuffisante', vel:b[0]});
      text.push(name + '<br>bassin (quantile)=' + b[1].toFixed(2) + '<br>intensité=' + b[0].toFixed(3));
      return;
    }
    if (!cell) {
      z.push(null);
      customdata.push({rid, name, sector: shownSector, year, value:null, state:'Donnée insuffisante', vel:null});
      text.push(name + ': donnée insuffisante');
      return;
    }
    let zval, label;
    if (view === 'velocity') { zval = cell[CELL_VEL]; label='vitesse='+(cell[CELL_VEL]!=null?cell[CELL_VEL].toFixed(3):'n/a'); }
    else if (view === 'prediction') {
      const pr = predictionLookup(country, rid, shownSector, year);
      zval = pr ? pr[PRED_DIFF] : null;
      label = pr ? ('écart='+pr[PRED_DIFF].toFixed(1)) : 'sans prévision';
    } else { zval = STATE_NUM[cell[CELL_STATE]]; label = cell[CELL_STATE]; }
    z.push(zval);
    customdata.push({rid, name, sector: shownSector, year, value:cell[CELL_VALUE], state:cell[CELL_STATE], vel:cell[CELL_VEL]});
    text.push(name + '<br>secteur=' + (shownSector||'') + '<br>' + label);
  });

  const colorscale = (view==='state')
    ? [[0,'#ef5350'],[0.5,'#9aa4bf'],[1,'#26a69a']]
    : (view==='basins')
    ? [[0,'#171b2d'],[0.5,'#4aa3ff'],[1,'#ffd180']]
    : [[0,'#ef5350'],[0.5,'#171b2d'],[1,'#26a69a']];
  const trace = {
    type:'choropleth', geojson: geo, featureidkey:'properties.panel_id',
    locations, z, text, customdata, colorscale,
    zmin: view==='state' ? -1 : (view==='basins' ? 0 : undefined),
    zmax: view==='state' ? 1 : (view==='basins' ? 1 : undefined),
    zmid: (view!=='state' && view!=='basins') ? 0 : undefined,
    colorbar:{title: view==='state'?'État':(view==='velocity'?'Vitesse':(view==='basins'?'Bassin (quantile)':'Écart')), tickfont:{color:'#eef2ff',size:10}, thickness:14, len:0.8},
    hovertemplate:'%{text}<extra></extra>',
    marker:{line:{width:0.5, color:'#30364f'}}, showscale:true,
  };
  const layout = Object.assign({}, BASE_LAYOUT, {
    geo:{fitbounds:'geojson', visible:false, bgcolor:'#0f1220', showframe:false, showcoastlines:false},
    margin:{l:0,r:0,t:30,b:0},
    title:{text: (MAP_CONFIG[country]||{}).label + ' — ' + year + ' — ' + (sector==='ALL'?'tous secteurs':sector),
      font:{size:13,color:'#eef2ff'}},
  });
  Plotly.newPlot('map-plot', [trace], layout, {responsive:true, displayModeBar:false});
  document.getElementById('map-plot').on('plotly_click', function(data) {
    const pt = data.points[0];
    if (pt && pt.customdata) showTerritorySidePanel(country, pt.customdata);
  });
  renderMapLegend(view);
}

function renderTerritoryTable(country, view) {
  const year = currentYear();
  const sector = document.getElementById('map-sector').value;
  const regions = MAP_STATE[country] || {};
  const meta = REGION_META[country] || {};
  const rows = [];
  Object.keys(regions).forEach(rid => {
    const secMap = regions[rid];
    const m = meta[rid] || {};
    const sectorsToShow = sector === 'ALL' ? Object.keys(secMap) : [sector];
    sectorsToShow.forEach(s => {
      const cell = (secMap[s]||{})[year];
      if (!cell) return;
      rows.push([m.name||rid, s, cell[CELL_STATE], cell[CELL_VEL], cell[CELL_BADGE]]);
    });
  });
  const tbody = document.querySelector('#territory-table tbody');
  tbody.innerHTML = rows.slice(0,500).map(r => {
    const stCls = r[2]==='Croissance'?'state-growth':r[2]==='Recul'?'state-falling':r[2]==='Stable'?'state-stable':'state-noevidence';
    const badgeCls = r[4]==='Proxy territorial (contexte uniquement)' ? 'badge-proxy' : 'badge-observed';
    return `<tr><td>${r[0]}</td><td>${SECTOR_LABELS[r[1]]||r[1]} (${r[1]})</td>`
      + `<td class="${stCls}">${r[2]}</td><td>${r[3]!=null?r[3].toFixed(3):'Donnée insuffisante'}</td>`
      + `<td><span class="badge ${badgeCls}">${r[4]}</span></td></tr>`;
  }).join('');
  renderMapLegend(view);
}

function renderMapLegend(view) {
  const el = document.getElementById('map-legend');
  if (view === 'state') {
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Croissance</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>Stable</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>Recul</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#3a3f56"></div>Donnée insuffisante</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#b39ddb"></div>Proxy territorial</div>`;
  } else if (view === 'basins') {
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#171b2d;border:1px solid #4a4f6a"></div>Bassin faible</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#4aa3ff"></div>Bassin médian</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#ffd180"></div>Bassin fort (dynamique élevée)</div>`;
  } else {
    el.innerHTML = `<div class="legend-item"><div class="legend-dot" style="background:#ef5350"></div>En dessous de l'attendu</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#9aa4bf"></div>~ à l'attendu</div>`
      + `<div class="legend-item"><div class="legend-dot" style="background:#26a69a"></div>Au-dessus de l'attendu</div>`;
  }
}

function showTerritorySidePanel(country, cd) {
  const meta = (REGION_META[country]||{})[cd.rid] || {};
  const badge = meta.is_proxy_context
    ? '<span class="badge badge-proxy">Proxy territorial</span>' : '<span class="badge badge-observed">Observé</span>';
  const allSectors = (MAP_STATE[country]||{})[cd.rid] || {};
  const sector = cd.sector || Object.keys(allSectors)[0];
  const yearMap = allSectors[sector] || {};
  const seriesY = Object.keys(yearMap).map(Number).sort((a,b)=>a-b);
  const seriesV = seriesY.map(y => yearMap[y][CELL_VEL]);

  const ranking = Object.keys(allSectors).map(s => {
    const row = (allSectors[s]||{})[cd.year];
    return row ? {sector:s, vel:row[CELL_VEL], state:row[CELL_STATE]} : null;
  }).filter(Boolean).sort((a,b)=>(b.vel||0)-(a.vel||0));

  const pred = predictionLookup(country, cd.rid, sector, cd.year);

  document.getElementById('map-side-empty').style.display = 'none';
  const content = document.getElementById('map-side-content');
  content.style.display = 'block';
  const kzNote = (country==='PT' && sector==='KZ' && PT_KZ_STRUCTURAL_ABSENT)
    ? '<div class="footnote">Finance et assurance (KZ) est structurellement absente pour le Portugal — pas une donnée manquante.</div>' : '';
  const predBlock = pred
    ? `<div class="side-field"><span class="lbl">Observé</span><span>${pred[PRED_OBS]!=null?pred[PRED_OBS].toFixed(1):'Donnée insuffisante'}</span></div>
       <div class="side-field"><span class="lbl">Attendu</span><span>${pred[PRED_EXP]!=null?pred[PRED_EXP].toFixed(1):'Donnée insuffisante'}</span></div>
       <div class="side-field"><span class="lbl">Écart</span><span>${pred[PRED_DIFF]!=null?pred[PRED_DIFF].toFixed(1):'Donnée insuffisante'}</span></div>`
    : `<div class="side-field"><span class="lbl">Prévision</span><span>sans prévision</span></div>`;
  content.innerHTML = `
    <div style="margin-bottom:8px">${badge}</div>
    <div class="side-field"><span class="lbl">Territoire</span><span>${cd.name}</span></div>
    <div class="side-field"><span class="lbl">Type de territoire</span><span>${meta.region_system||''}</span></div>
    <div class="side-field"><span class="lbl">Secteur</span><span>${SECTOR_LABELS[sector]||sector} (${sector})</span></div>
    <div class="side-field"><span class="lbl">Année</span><span>${cd.year}</span></div>
    <div class="side-field"><span class="lbl">État</span><span>${cd.state||'Donnée insuffisante'}</span></div>
    ${predBlock}
    ${kzNote}
    <div id="ts-plot" style="height:140px;margin-top:8px"></div>
    <h3 style="margin-top:10px">Principaux secteurs ici (${cd.year})</h3>
    <table class="dense">${ranking.slice(0,9).map(r=>`<tr><td>${SECTOR_LABELS[r.sector]||r.sector} (${r.sector})</td><td class="${r.state==='Croissance'?'state-growth':r.state==='Recul'?'state-falling':'state-stable'}">${r.state}</td></tr>`).join('')}</table>
  `;
  Plotly.newPlot('ts-plot', [{x:seriesY, y:seriesV, type:'scatter', mode:'lines+markers',
    line:{color:'#4aa3ff'}, marker:{size:4}}],
    Object.assign({}, BASE_LAYOUT, {margin:{l:30,r:10,t:10,b:20},
      xaxis:{tickfont:{size:9}}, yaxis:{title:'vitesse de variation',tickfont:{size:9},titlefont:{size:9}}}),
    {responsive:true, displayModeBar:false});
}

// ── Prediction table ─────────────────────────────────────────────────
function renderPredictionTable() {
  renderPredictionBanner();
  const rows = [];
  Object.keys(PREDICTION_LOOKUP).forEach(country => {
    const regions = PREDICTION_LOOKUP[country];
    Object.keys(regions).forEach(rid => {
      const sectors = regions[rid];
      Object.keys(sectors).forEach(sector => {
        const years = sectors[sector];
        Object.keys(years).forEach(year => {
          if (rows.length >= 300) return;
          const cell = years[year];
          rows.push({country, rid, sector, year: parseInt(year), obs: cell[PRED_OBS],
            exp: cell[PRED_EXP], diff: cell[PRED_DIFF], trend: cell[PRED_TREND]});
        });
      });
    });
  });
  const meta = REGION_META;
  document.querySelector('#prediction-table tbody').innerHTML = rows.slice(0,300).map(r => {
    const name = (meta[r.country]?.[String(r.rid)]||{}).name || r.rid;
    const diffCls = r.diff > 0 ? 'state-growth' : r.diff < 0 ? 'state-falling' : 'state-stable';
    return `<tr><td>${name} (${r.country})</td><td>${SECTOR_LABELS[r.sector]||r.sector}</td>`
      + `<td>${r.year}</td><td>${r.obs!=null?r.obs.toFixed(0):'Donnée insuffisante'}</td>`
      + `<td>${r.exp!=null?r.exp.toFixed(0):'Donnée insuffisante'}</td>`
      + `<td class="${diffCls}">${r.diff!=null?r.diff.toFixed(0):'Donnée insuffisante'}</td>`
      + `<td>${r.trend}</td></tr>`;
  }).join('');
}

// ── Sector graph ────────────────────────────────────────────────────
function populateWindowOptions() {
  const slider = document.getElementById('window-slider');
  slider.min = 0; slider.max = Math.max(0, RELATION_TIMELINE.windows.length-1);
  slider.value = slider.max;
  updateWindowLabel();
}
function currentWindow() {
  const idx = parseInt(document.getElementById('window-slider').value);
  return RELATION_TIMELINE.windows[idx] || RELATION_TIMELINE.windows[RELATION_TIMELINE.windows.length-1];
}
function updateWindowLabel() { document.getElementById('window-label').textContent = currentWindow() || 'n/a'; }
function onWindowSliderInput() { updateWindowLabel(); renderGraph(); }
function toggleGraphPlay() {
  const btn = document.getElementById('graph-play-btn');
  if (GRAPH_PLAY_INTERVAL) { clearInterval(GRAPH_PLAY_INTERVAL); GRAPH_PLAY_INTERVAL=null; btn.innerHTML='&#9654; Lecture de la ligne de temps'; return; }
  btn.innerHTML = '&#10074;&#10074; Pause';
  GRAPH_PLAY_INTERVAL = setInterval(() => {
    const slider = document.getElementById('window-slider');
    let idx = parseInt(slider.value) + 1;
    if (idx > parseInt(slider.max)) idx = 0;
    slider.value = idx;
    onWindowSliderInput();
  }, 1300);
}
function syncMapFromGraph() {
  const c = document.getElementById('graph-country').value;
  if (['FR','NL','PT'].includes(c)) { document.getElementById('map-country').value = c; handleCountryChange(); }
}

// PART F: clicking a relation filters the map to that country/window (the
// map<->graph wiring required by Part F/N12). We move the map's country
// selector and the map's year to the edge's window_end year, then re-render.
function applyGraphFilterToMap(edge) {
  GRAPH_MAP_FILTER = {country: edge.country, window: edge.window};
  const mapCountrySel = document.getElementById('map-country');
  if (['FR','NL','PT'].includes(edge.country)) {
    mapCountrySel.value = edge.country;
    refreshSectorOptionsForCountry(edge.country);
    populateYearOptions(edge.country);
    const years = YEARS_BY_COUNTRY[edge.country] || [];
    const idx = years.indexOf(edge.window_end);
    if (idx >= 0) document.getElementById('year-slider').value = idx;
    updateYearLabel();
    renderTerritoryView();
  }
}

function renderGraph() {
  const country = document.getElementById('graph-country').value;
  const evidence = document.getElementById('graph-evidence').value;
  const mode = document.getElementById('graph-mode').value;
  const w = currentWindow();

  const baseFiltered = RELATION_EDGES.filter(e => {
    if (country !== 'ALL' && e.country !== country) return false;
    if (evidence !== 'ALL' && e.evidence_badge !== evidence) return false;
    return true;
  });
  const activeEdges = baseFiltered.filter(e => e.window === w);
  const faintEdges = mode === 'persistent' ? baseFiltered.filter(e => e.window !== w) : [];

  const annotations = [], edgeTraces = [];
  function drawSet(edges, faint) {
    const pairIdx = {};
    edges.forEach((e) => {
      const sp = NODE_POS[e.source_sector], tp = NODE_POS[e.target_sector];
      if (!sp || !tp) return;
      const key = e.source_sector+'->'+e.target_sector;
      pairIdx[key] = (pairIdx[key]||0)+1;
      const hasRev = edges.some(e2=>e2.source_sector===e.target_sector&&e2.target_sector===e.source_sector);
      const off = hasRev ? (pairIdx[key]%2===0?1:-1)*0.06 : 0;
      const dx=tp.x-sp.x, dy=tp.y-sp.y, dist=Math.sqrt(dx*dx+dy*dy)||1;
      const ux=dx/dist, uy=dy/dist, r=0.15;
      const px=-uy*off, py=ux*off;
      const ax=sp.x+ux*r+px, ay=sp.y+uy*r+py, x=tp.x-ux*r+px, y=tp.y-uy*r+py;
      const col = e.sign==='+' ? '#26a69a' : '#ef5350';
      const isHighlighted = !HIGHLIGHT_SECTOR || e.source_sector===HIGHLIGHT_SECTOR || e.target_sector===HIGHLIGHT_SECTOR;
      const w2 = (1+Math.abs(e.beta||0)*10) * (isHighlighted ? 1 : 0.6);
      const dash = e.evidence_badge==='Validé' ? 'solid' : e.evidence_badge==='Supporté' ? 'dash' : 'dot';
      let opacity = faint ? 0.12 : (e.evidence_badge==='Validé' ? 0.95 : e.evidence_badge==='Supporté' ? 0.8 : 0.45);
      if (!isHighlighted) opacity *= 0.3;
      edgeTraces.push({
        x:[ax,x,null], y:[ay,y,null], mode:'lines', type:'scatter',
        line:{color:col,width:w2,dash}, opacity, hoverinfo: faint ? 'skip' : 'text',
        text:`${e.source_sector}→${e.target_sector} (${e.country}) ${e.direction_human}`,
        customdata:[RELATION_EDGES.indexOf(e)], showlegend:false, name:key,
      });
      if (!faint) annotations.push({x,y,ax,ay,xref:'x',yref:'y',axref:'x',ayref:'y',
        showarrow:true,arrowhead:2,arrowsize:1.1,arrowwidth:Math.max(1.3,w2*0.6),arrowcolor:col,opacity});
    });
  }
  drawSet(faintEdges, true);
  drawSet(activeEdges, false);

  const nodeTrace = {
    x:SECTORS.map(s=>NODE_POS[s].x), y:SECTORS.map(s=>NODE_POS[s].y),
    mode:'markers+text', type:'scatter',
    marker:{size:30,color:SECTORS.map(s=>s===HIGHLIGHT_SECTOR?'#2d3a5c':'#20253a'),
      line:{color:'#4aa3ff',width:1.5}},
    text:SECTORS, textfont:{size:10,color:'#eef2ff'}, textposition:'middle center',
    hovertext:SECTORS.map(s=>'<b>'+(SECTOR_LABELS[s]||s)+'</b> ('+s+')'),
    hovertemplate:'%{hovertext}<extra></extra>', name:'secteurs',
  };
  document.getElementById('edge-count-label').textContent = activeEdges.length + ' relation(s) active(s) en ' + (w||'n/a') +
    (mode==='persistent' ? (' · ' + faintEdges.length + ' autres relations valides estompées') : '');
  const layout = Object.assign({}, BASE_LAYOUT, {
    xaxis:{range:[-1.6,1.6],showgrid:false,zeroline:false,showticklabels:false},
    yaxis:{range:[-1.45,1.45],showgrid:false,zeroline:false,showticklabels:false,scaleanchor:'x'},
    annotations, showlegend:false, hovermode:'closest',
    margin:{l:10,r:10,t:10,b:10},
  });
  Plotly.newPlot('sector-graph', [...edgeTraces, nodeTrace], layout, {responsive:true, displayModeBar:false});
  document.getElementById('sector-graph').on('plotly_click', function(data) {
    const pt = data.points[0];
    if (pt.data.customdata) {
      const edge = RELATION_EDGES[pt.data.customdata[0]];
      showEdgeDetail(edge);
      applyGraphFilterToMap(edge);
    }
  });
  renderRelationHeatmap(baseFiltered);
}

function showEdgeDetail(e) {
  if (!e) return;
  const badgeCls = e.evidence_badge==='Validé'?'badge-robust':e.evidence_badge==='Supporté'?'badge-supported':'badge-exploratory';
  const signBadge = e.sign==='+' ? '<span class="badge badge-pos">Même direction</span>' : '<span class="badge badge-neg">Direction opposée</span>';
  document.getElementById('edge-panel-empty').style.display = 'none';
  const content = document.getElementById('edge-panel-content');
  content.style.display = 'block';
  content.innerHTML = `
    <div style="margin:0 0 8px">${SECTOR_LABELS[e.source_sector]} (${e.source_sector}) &#8594; ${SECTOR_LABELS[e.target_sector]} (${e.target_sector})</div>
    <div style="margin-bottom:10px"><span class="badge ${badgeCls}">${e.evidence_badge}</span> ${signBadge}</div>
    <div class="narrative-sentence">${e.plain_sentence}</div>
    <div class="side-field"><span class="lbl">Pays</span><span>${e.country}</span></div>
    <div class="side-field"><span class="lbl">Fenêtre</span><span>${e.window}</span></div>
    <div class="footnote">Contexte territorial agrégé pour cette relation — aucune attribution au niveau d'un territoire individuel n'est faite.</div>
    <h3 style="margin-top:10px">Contexte territorial (${e.country}, ${e.window_end})</h3>
    ${territoryContextTable(e)}
  `;
}

function territoryContextTable(e) {
  const sectors = [e.source_sector, e.target_sector];
  const regions = MAP_STATE[e.country] || {};
  const rows = sectors.map(s => {
    const counts = {Croissance:0, Stable:0, Recul:0, 'Donnée insuffisante':0};
    Object.keys(regions).forEach(rid => {
      const cell = (regions[rid][s]||{})[e.window_end];
      const label = cell ? cell[CELL_STATE] : 'Donnée insuffisante';
      counts[label] = (counts[label]||0)+1;
    });
    return `<tr><td>${SECTOR_LABELS[s]} (${s})</td><td class="state-growth">${counts.Croissance}</td>`+
      `<td class="state-falling">${counts.Recul}</td><td class="state-stable">${counts.Stable}</td>`+
      `<td class="state-noevidence">${counts['Donnée insuffisante']}</td></tr>`;
  }).join('');
  return `<table class="dense"><thead><tr><th>Secteur</th><th>Croissance</th><th>Recul</th><th>Stable</th><th>Donnée insuffisante</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderRelationHeatmap(filtered) {
  const pairs = [...new Set(filtered.map(e=>e.country+': '+e.source_sector+'→'+e.target_sector))].sort();
  const windows = RELATION_TIMELINE.windows;
  const z = pairs.map(p => windows.map(w => {
    const [c, st] = p.split(': '); const [s,t] = st.split('→');
    const match = filtered.find(e=>e.country===c && e.source_sector===s && e.target_sector===t && e.window===w);
    return match ? match.beta : null;
  }));
  const trace = { type:'heatmap', x: windows, y: pairs, z,
    colorscale:[[0,'#ef5350'],[0.5,'#171b2d'],[1,'#26a69a']], zmid:0,
    colorbar:{title:'intensité', tickfont:{color:'#eef2ff',size:10}, thickness:12}, hoverinfo:'x+y+z' };
  const layout = Object.assign({}, BASE_LAYOUT, {margin:{l:140,r:20,t:10,b:50},
    xaxis:{tickangle:-45, tickfont:{size:9}}, yaxis:{tickfont:{size:9}, automargin:true}});
  Plotly.newPlot('relation-heatmap', [trace], layout, {responsive:true, displayModeBar:false});
}

function renderBlockedTable() {
  document.querySelector('#blocked-table tbody').innerHTML = BLOCKED_EDGES.map(e => `<tr>
    <td>${SECTOR_LABELS[e.source_sector]||e.source_sector} (${e.source_sector})</td>
    <td>${SECTOR_LABELS[e.target_sector]||e.target_sector} (${e.target_sector})</td>
    <td>${e.beta.toFixed(4)}</td><td>${e.window}</td><td>${e.reason}</td></tr>`).join('');
}

function renderEvidenceKpis() {
  const evItems = [
    ['Relations validées', N_VALID_RELATIONS],
    ['Relations rejetées (audit uniquement)', N_BLOCKED_RELATIONS],
    ['Pays couverts par la prévision', PREDICTION_COUNTRIES.join(', ') || 'aucun'],
  ];
  document.getElementById('evidence-kpis').innerHTML = evItems.map(([l,v])=>
    `<div class="kpi"><div class="v" style="font-size:15px">${v}</div><div class="l">${l}</div></div>`).join('');
  document.getElementById('dec-refs').textContent = (MANIFEST.dec_references||[]).join(', ');
  document.getElementById('chk-territory').textContent = CSV_CHECKSUMS['territory_view.csv'];
  document.getElementById('chk-relation').textContent = CSV_CHECKSUMS['relation_view.csv'];
  document.getElementById('chk-blocked').textContent = CSV_CHECKSUMS['blocked_proxy_edges_v04_copy.csv'];

  const tbody = document.getElementById('tech-relation-tbody');
  tbody.innerHTML = RELATION_EDGES.map(e => `<tr>
    <td>${e.source_sector}&#8594;${e.target_sector}</td><td>${e.country}</td>
    <td>${e.beta.toFixed(4)}</td><td>${e.q_fdr.toFixed(3)}</td><td>${e.bss.toFixed(3)}</td>
    <td>${e.window}</td><td>${e.label_class}</td><td style="font-size:10px">${e.evidence_type}</td>
    <td>${e.allowed_for_training_label}</td></tr>`).join('');
}

// ── Init ────────────────────────────────────────────────────────────
renderRelationalCounts();
renderEvidenceKpis();
refreshSectorOptionsForCountry('FR');
populateYearOptions('FR');
renderTerritoryView();
populateWindowOptions();
renderGraph();
renderPredictionTable();
renderBlockedTable();
"""
