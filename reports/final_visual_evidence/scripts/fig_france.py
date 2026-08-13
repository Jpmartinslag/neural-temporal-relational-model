"""French data and geography figures — F01 to F07.

Every map here shows something *observed* (a published commuting flow) or something
*constructed* (a candidate support this study defines from published series). None of them
shows a learned score, because no learned relational structure is authorised for France at
this stage. The stamp on each panel says which.

Run: python reports/final_visual_evidence/scripts/fig_france.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection, PolyCollection

from herald_evidence import (PALETTE, commuting_edges, footnote, mainland_zones,
                             multisource_series, save, stamp, use_style, write_provenance,
                             ze2020_geometry)

SOURCE_NOTE = ("Source : Insee (géographie ZE2020, mobilités professionnelles, chômage "
               "localisé), Urssaf, Flores, Sirene/SIDE. Population : 280 zones d'emploi de "
               "France métropolitaine, Corse exclue.")

PROVENANCE: dict[str, dict] = {}


# ── shared map machinery ─────────────────────────────────────────────────────

def draw_zones(ax, geometry, zones, *, facecolor=None, linewidth=0.25) -> None:
    polygons = []
    for code in zones:
        polygons.extend(geometry[code]["rings"])
    ax.add_collection(PolyCollection(
        polygons, facecolors=facecolor or PALETTE["land"], edgecolors=PALETTE["land_edge"],
        linewidths=linewidth))
    ax.set_aspect(1 / math.cos(math.radians(46.5)))
    ax.autoscale_view()
    ax.set_axis_off()


def draw_edges(ax, geometry, edges, colour, *, widths=None, alpha=0.55, zorder=3):
    segments = [[geometry[s]["centroid"], geometry[t]["centroid"]] for s, t, *_ in edges]
    ax.add_collection(LineCollection(
        segments, colors=colour, linewidths=widths if widths is not None else 0.6,
        alpha=alpha, zorder=zorder))


def blank_map(ax, geometry, zones) -> None:
    draw_zones(ax, geometry, zones)


# ── constructed candidate supports ───────────────────────────────────────────

def causal_growth_profiles(last_year: int = 2019) -> tuple[list[str], np.ndarray, list[int]]:
    """Annual log-growth of private headcount per zone, up to `last_year` only.

    The window stops before COVID so that the constructed supports are not defined by a single
    shared shock. Standardisation is per zone, so the profile carries the *shape* of a
    trajectory and not its level or its amplitude.
    """
    series = multisource_series()["headcount"]["series"]
    zones = sorted(z for z in series if z in set(mainland_zones()))
    years = sorted({y for z in zones for y in series[z] if y <= last_year})
    years = [y for y in years if all(y in series[z] and series[z][y] > 0 for z in zones)]
    levels = np.array([[math.log(series[z][y]) for y in years] for z in zones])
    growth = np.diff(levels, axis=1)
    centred = growth - growth.mean(axis=1, keepdims=True)
    scale = centred.std(axis=1, keepdims=True)
    scale[scale == 0] = 1.0
    return zones, centred / scale, years[1:]


def top_k_pairs(matrix: np.ndarray, k: int, *, largest: bool) -> list[tuple[int, int, float]]:
    work = matrix.copy()
    np.fill_diagonal(work, -np.inf if largest else np.inf)
    order = np.argsort(-work if largest else work, axis=1)[:, :k]
    return [(i, int(j), float(matrix[i, j])) for i in range(matrix.shape[0]) for j in order[i]]


def constructed_supports(k: int = 5):
    zones, profiles, years = causal_growth_profiles()
    correlation = (profiles @ profiles.T) / profiles.shape[1]
    similarity = top_k_pairs(correlation, k, largest=True)
    complementarity = top_k_pairs(correlation, k, largest=False)
    return zones, correlation, similarity, complementarity, years


def geodesic_km(a: np.ndarray, b: np.ndarray) -> float:
    lon = (a[0] - b[0]) * math.cos(math.radians(46.5)) * 111.32
    lat = (a[1] - b[1]) * 110.57
    return math.hypot(lon, lat)


# ── F01 ──────────────────────────────────────────────────────────────────────

def f01_zones(geometry, zones) -> None:
    use_style()
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    draw_zones(ax, geometry, zones, linewidth=0.35)
    ax.set_title("Les 280 zones d'emploi (ZE2020) de France métropolitaine")
    stamp(ax, "REAL_FRANCE — observé", PALETTE["commuting"])
    footnote(fig, SOURCE_NOTE + "\nDécoupage ZE2020 en vigueur ; les DOM et la Corse ne "
                                "font pas partie de la population d'étude.")
    save(fig, "F01_ze2020_zones")
    PROVENANCE["F01"] = {"zones": len(zones), "geometry": "data/external/ze2020_geometry.geojson"}


# ── F02 ──────────────────────────────────────────────────────────────────────

def f02_commuting(geometry, zones) -> None:
    edges = commuting_edges(2012)
    strongest: dict[str, list] = defaultdict(list)
    for source, target, weight in edges:
        strongest[source].append((weight, target))
    sample = []
    for source, items in strongest.items():
        for weight, target in sorted(items, reverse=True)[:3]:
            sample.append((source, target, weight))
    widths = np.array([w for *_, w in sample])
    widths = 0.25 + 2.4 * (widths / widths.max()) ** 0.45

    use_style()
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    draw_zones(ax, geometry, zones)
    draw_edges(ax, geometry, sample, PALETTE["commuting"], widths=widths, alpha=0.6)
    ax.set_title("Navettes domicile-travail : les trois destinations les plus fortes\n"
                 "de chaque zone")
    stamp(ax, "REAL_FRANCE — observé", PALETTE["commuting"])
    footnote(fig, SOURCE_NOTE + f"\nÉchantillon déclaré : {len(sample)} arêtes sur "
                                f"{len(edges)} flux inter-zones observés en 2012 ; l'épaisseur "
                                f"suit le nombre de navetteurs. Ce graphe est un prior de "
                                f"candidature, jamais une étiquette : aucune méthode n'est "
                                f"notée contre lui.")
    save(fig, "F02_commuting_network")
    PROVENANCE["F02"] = {"edges_total": len(edges), "edges_drawn": len(sample),
                         "vintage": 2012, "rule": "top-3 destinations per zone"}


# ── F03 and F04 ──────────────────────────────────────────────────────────────

ZOOM_REGION = {"name": "Auvergne-Rhône-Alpes et Bourgogne-Franche-Comté",
               "lon": (3.0, 7.4), "lat": (44.2, 48.0)}


def _relation_map(geometry, zones, zone_codes, pairs, colour, title, subtitle, stem,
                  key, *, far_quantile=0.60, sample=180, seed=20260813):
    """Two panels, because one national panel with 1400 chords is unreadable.

    Left: a declared random sample of the constructed pairs, the strongest quartile drawn
    heavier so that distant pairs are visible. Right: every pair touching one region, at full
    density, so the reader can see what an individual zone's candidate set looks like.
    """
    centroids = {z: geometry[z]["centroid"] for z in zone_codes}
    distances = np.array([geodesic_km(centroids[zone_codes[i]], centroids[zone_codes[j]])
                          for i, j, _ in pairs])
    threshold = float(np.quantile(distances, far_quantile))

    rng = np.random.default_rng(seed)
    picked = rng.choice(len(pairs), size=min(sample, len(pairs)), replace=False)
    near = [(zone_codes[pairs[p][0]], zone_codes[pairs[p][1]]) for p in picked
            if distances[p] < threshold]
    far = [(zone_codes[pairs[p][0]], zone_codes[pairs[p][1]]) for p in picked
           if distances[p] >= threshold]

    lon, lat = ZOOM_REGION["lon"], ZOOM_REGION["lat"]
    inside = {z for z in zone_codes
              if lon[0] <= centroids[z][0] <= lon[1] and lat[0] <= centroids[z][1] <= lat[1]}
    regional = [(zone_codes[i], zone_codes[j]) for i, j, _ in pairs
                if zone_codes[i] in inside]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 7.4))
    draw_zones(axes[0], geometry, zones)
    draw_edges(axes[0], geometry, near, colour, widths=0.55, alpha=0.30)
    draw_edges(axes[0], geometry, far, colour, widths=1.3, alpha=0.80, zorder=4)
    axes[0].plot([], [], color=colour, alpha=0.35, lw=1.4,
                 label=f"paires proches (< {threshold:.0f} km) — {len(near)} tracées")
    axes[0].plot([], [], color=colour, alpha=0.85, lw=2.4,
                 label=f"paires éloignées (≥ {threshold:.0f} km) — {len(far)} tracées")
    axes[0].legend(loc="lower left", fontsize=9)
    axes[0].set_title(f"Échantillon déclaré : {len(picked)} paires sur {len(pairs)}",
                      fontsize=13)

    draw_zones(axes[1], geometry, zones, linewidth=0.2)
    draw_zones(axes[1], geometry, sorted(inside), facecolor="#E4E4E4", linewidth=0.5)
    draw_edges(axes[1], geometry, regional, colour, widths=0.9, alpha=0.55, zorder=4)
    axes[1].set_title(f"Toutes les paires partant de {len(inside)} zones\n"
                      f"{ZOOM_REGION['name']} — {len(regional)} paires", fontsize=13)

    fig.suptitle(title, y=1.02)
    stamp(fig, "EXPLORATORY — construit, non découvert", PALETTE["warning"])
    footnote(fig, SOURCE_NOTE + "\n" + subtitle)
    save(fig, stem)
    PROVENANCE[key] = {"pairs": len(pairs), "pairs_drawn_left": int(len(picked)),
                       "far_pairs_drawn": len(far), "zoom_zones": len(inside),
                       "zoom_pairs": len(regional), "sample_seed": seed,
                       "distance_threshold_km": threshold,
                       "definition": subtitle}


def f03_similarity(geometry, zones, zone_codes, similarity, years) -> None:
    _relation_map(
        geometry, zones, zone_codes, similarity, PALETTE["similarity"],
        "Similarité économique construite : trajectoires de forme voisine",
        f"Définition : corrélation des croissances annuelles standardisées des effectifs "
        f"salariés privés, {years[0]}–{years[-1]}, cinq voisins les plus proches par zone. "
        f"Support candidat construit, pas une relation découverte : rien ici n'a été appris "
        f"par un modèle et aucune arête ne porte de sens économique établi.",
        "F03_similarity_map", "F03")


def f04_complementarity(geometry, zones, zone_codes, complementarity, years) -> None:
    _relation_map(
        geometry, zones, zone_codes, complementarity, PALETTE["complementarity"],
        "Complémentarité économique construite : trajectoires de forme opposée",
        f"Définition : mêmes profils que la similarité, mais les cinq corrélations les plus "
        f"négatives par zone, {years[0]}–{years[-1]}. Support candidat construit. Une "
        f"corrélation négative entre deux trajectoires n'est pas une complémentarité "
        f"économique : c'est une hypothèse à tester, pas un résultat.",
        "F04_complementarity_map", "F04")


# ── F05 ──────────────────────────────────────────────────────────────────────

def f05_side_by_side(geometry, zones, zone_codes, similarity, complementarity) -> None:
    commuting = commuting_edges(2012)
    strongest: dict[str, list] = defaultdict(list)
    for source, target, weight in commuting:
        strongest[source].append((weight, target))
    commuting_sample = [(s, t) for s, items in strongest.items()
                        for _, t in sorted(items, reverse=True)[:3]]
    similarity_pairs = [(zone_codes[i], zone_codes[j]) for i, j, _ in similarity]
    complementarity_pairs = [(zone_codes[i], zone_codes[j]) for i, j, _ in complementarity]
    union = sorted(set(commuting_sample) | set(similarity_pairs) | set(complementarity_pairs))

    panels = [("Navettes (observé)", commuting_sample, PALETTE["commuting"]),
              ("Similarité (construit)", similarity_pairs, PALETTE["similarity"]),
              ("Complémentarité (construit)", complementarity_pairs,
               PALETTE["complementarity"]),
              ("Union multirelationnelle", union, PALETTE["union"])]

    draw_count = 200
    rng = np.random.default_rng(20260813)

    use_style()
    fig, axes = plt.subplots(1, 4, figsize=(19.5, 6.0))
    for ax, (title, pairs, colour) in zip(axes, panels):
        picked = [pairs[p] for p in rng.choice(len(pairs), size=min(draw_count, len(pairs)),
                                               replace=False)]
        draw_zones(ax, geometry, zones, linewidth=0.15)
        draw_edges(ax, geometry, picked, colour, widths=0.8, alpha=0.5)
        ax.set_title(f"{title}\n{len(pairs)} paires — {len(picked)} tracées", fontsize=13)
    fig.suptitle("Quatre supports candidats sur la même géographie", y=1.02)
    stamp(fig, "REAL_FRANCE / EXPLORATORY", PALETTE["warning"])
    overlap = len(set(commuting_sample) & set(similarity_pairs))
    footnote(fig, SOURCE_NOTE + f"\nChaque panneau montre un échantillon aléatoire déclaré de "
                                f"{draw_count} paires, tiré avec une graine fixe : la densité "
                                f"tracée est comparable entre panneaux, les effectifs réels "
                                f"figurent dans les titres. Les familles se recouvrent peu — "
                                f"{overlap} paires communes entre navettes et similarité sur "
                                f"{len(similarity_pairs)}. Aucun de ces supports n'est un "
                                f"résultat ; ce sont des ensembles de candidats qu'un modèle "
                                f"aurait le droit d'examiner.", width=150)
    save(fig, "F05_support_comparison")
    PROVENANCE["F05"] = {"commuting": len(commuting_sample),
                         "similarity": len(similarity_pairs),
                         "complementarity": len(complementarity_pairs),
                         "union": len(union),
                         "commuting_similarity_overlap": overlap}


# ── F06 ──────────────────────────────────────────────────────────────────────

def f06_series() -> None:
    signals = multisource_series()
    order = ["headcount", "payroll", "establishments", "unemployment", "creations"]
    zones = mainland_zones()

    use_style()
    fig, axes = plt.subplots(1, 5, figsize=(21, 4.2))
    for ax, key in zip(axes, order):
        entry = signals[key]
        series = {z: v for z, v in entry["series"].items() if z in set(zones) and v}
        totals = {z: sum(v.values()) / len(v) for z, v in series.items()}
        ranked = sorted(totals, key=totals.get)
        picked = [ranked[int(q * (len(ranked) - 1))] for q in (0.10, 0.50, 0.90)]
        for zone, shade in zip(picked, ("#9A9A9A", PALETTE["commuting"], PALETTE["herald"])):
            values = series[zone]
            years = sorted(values)
            ax.plot(years, [values[y] for y in years], color=shade, lw=2.0,
                    label=f"{zone}")
        ax.set_title(f"{entry['label']}\n{entry['source']}", fontsize=12)
        ax.set_xlabel("année")
        ax.set_ylabel(entry["unit"])
        ax.legend(fontsize=8.5, title="ZE2020", title_fontsize=8.5)
    fig.suptitle("Cinq signaux économiques, trois zones représentatives "
                 "(décile 10, médiane, décile 90 de taille)", y=1.06)
    stamp(fig, "REAL_FRANCE — observé", PALETTE["commuting"])
    footnote(fig, SOURCE_NOTE + "\nLes fenêtres diffèrent d'une source à l'autre : c'est la "
                                "disponibilité réelle des publications, pas un choix de "
                                "cadrage. Une cellule absente reste absente.")
    save(fig, "F06_representative_series")
    PROVENANCE["F06"] = {"signals": order,
                         "rule": "zones at the 10th, 50th and 90th percentile of mean level"}


# ── F07 ──────────────────────────────────────────────────────────────────────

def f07_temporal_representation() -> None:
    series = multisource_series()["headcount"]["series"]
    zones = sorted(z for z in series if z in set(mainland_zones()))
    years = sorted(set.intersection(*[set(series[z]) for z in zones]))
    matrix = np.array([[series[z][y] for y in years] for z in zones])
    logs = np.log(matrix)
    growth = np.full_like(logs, np.nan)
    growth[:, 1:] = np.diff(logs, axis=1)
    acceleration = np.full_like(growth, np.nan)
    acceleration[:, 1:] = np.diff(growth, axis=1)

    window = 5
    trend = np.full_like(logs, np.nan)
    momentum = np.full_like(logs, np.nan)
    volatility = np.full_like(logs, np.nan)
    x = np.arange(window)
    for t in range(window - 1, logs.shape[1]):
        block = logs[:, t - window + 1:t + 1]
        centred = x - x.mean()
        trend[:, t] = ((block - block.mean(1, keepdims=True)) * centred).sum(1) / (
            centred ** 2).sum()
        gblock = growth[:, t - window + 1:t + 1]
        momentum[:, t] = np.nanmean(gblock, axis=1)
        volatility[:, t] = np.nanstd(gblock, axis=1)
    national = np.nanmean(growth, axis=0)
    relative = growth - national

    zone = zones[np.argsort(matrix.mean(1))[len(zones) // 2]]
    index = zones.index(zone)

    use_style()
    fig, axes = plt.subplots(3, 3, figsize=(16.5, 10.5), sharex=True)
    panels = [
        ("niveau  log(effectifs)", logs[index], PALETTE["commuting"], None),
        ("croissance  Δ log sur un an", growth[index], PALETTE["herald"], 0.0),
        ("accélération  Δ croissance", acceleration[index], PALETTE["other_neural"], 0.0),
        ("tendance  pente sur 5 ans", trend[index], PALETTE["similarity"], 0.0),
        ("momentum  croissance moyenne 5 ans", momentum[index], PALETTE["complementarity"],
         0.0),
        ("volatilité  écart-type 5 ans", volatility[index], PALETTE["learned_graph"], None),
        ("composante nationale", national, PALETTE["null"], 0.0),
        ("croissance relative  = croissance − national", relative[index], PALETTE["herald"],
         0.0),
    ]
    for ax, (title, values, colour, zero) in zip(axes.ravel(), panels):
        ax.plot(years, values, color=colour, lw=2.2)
        if zero is not None:
            ax.axhline(zero, color="#999999", lw=0.9, ls="--")
        ax.set_title(title, fontsize=12)

    ax = axes.ravel()[8]
    regimes = np.select(
        [(growth[index] > 0) & (acceleration[index] >= 0),
         (growth[index] > 0) & (acceleration[index] < 0),
         (growth[index] <= 0) & (acceleration[index] < 0),
         (growth[index] <= 0) & (acceleration[index] >= 0)],
        [0, 1, 2, 3], default=-1)
    names = ["expansion", "décélération", "contraction", "reprise"]
    colours = [PALETTE["complementarity"], PALETTE["similarity"], PALETTE["warning"],
               PALETTE["commuting"]]
    for code, (name, colour) in enumerate(zip(names, colours)):
        hits = [y for y, r in zip(years, regimes) if r == code]
        ax.bar(hits, [1] * len(hits), color=colour, width=0.9, label=name)
    ax.set_yticks([])
    ax.set_ylim(0, 1.05)
    ax.set_title("régime  quatre indicatrices exclusives", fontsize=12)
    ax.legend(fontsize=8.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16))

    for ax in axes[-1]:
        ax.set_xlabel("année")
    fig.suptitle(f"La représentation temporelle causale d'une zone — ZE2020 {zone}", y=1.01)
    stamp(fig, "REAL_FRANCE — dérivé d'observations", PALETTE["commuting"])
    footnote(fig, SOURCE_NOTE + "\nEffectifs salariés privés (Urssaf), moyenne annuelle. "
                                "Chaque colonne n'utilise que des données disponibles à la "
                                "date de décision. La fenêtre est réduite à cinq ans pour "
                                "l'illustration ; le modèle utilise douze périodes pour la "
                                "tendance et huit pour le momentum et la volatilité.")
    save(fig, "F07_temporal_representation")
    PROVENANCE["F07"] = {"zone": zone, "years": [years[0], years[-1]],
                         "illustration_window": window,
                         "model_windows": {"trend": 12, "momentum": 8, "volatility": 8}}


def main() -> None:
    geometry = ze2020_geometry()
    zones = mainland_zones()
    zone_codes, _, similarity, complementarity, years = constructed_supports()

    f01_zones(geometry, zones)
    f02_commuting(geometry, zones)
    f03_similarity(geometry, zones, zone_codes, similarity, years)
    f04_complementarity(geometry, zones, zone_codes, complementarity, years)
    f05_side_by_side(geometry, zones, zone_codes, similarity, complementarity)
    f06_series()
    f07_temporal_representation()

    write_provenance("figures_france.json", {
        "kind": "herald_visual_evidence_provenance",
        "category": "REAL_FRANCE and EXPLORATORY",
        "rule": "no learned relational score is drawn for France at this stage",
        "figures": PROVENANCE})
    print(f"{len(PROVENANCE)} French figures written")


if __name__ == "__main__":
    main()
