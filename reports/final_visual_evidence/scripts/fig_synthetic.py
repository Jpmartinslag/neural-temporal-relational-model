"""Synthetic-world figures — S01 to S12.

These are the figures that carry the study's central distinction: an oracle that is told the
answer measures how much there is to find; the model sees only what a statistical office would
publish; predicting better is not the same as finding the edges; and a scenario with no
mechanism at all checks whether a method invents relations.

The world itself is redrawn here from the HERALD 96 generator, which is deterministic given a
seed. Generating data is not estimating anything, and no figure in this file fits a model.
Every measured quantity — oracle response, model response, AUPRC, scores — is read from the
committed task artefacts.

Run: python reports/final_visual_evidence/scripts/fig_synthetic.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

from herald_evidence import (PALETTE, FAMILY_ORDER, footnote, group, herald95_tasks,
                             herald96_tasks, median, save, stamp, synthetic_world, use_style,
                             write_provenance)

SEED = 9961
N_ZONES = 80
SYN_NOTE = ("Monde synthétique à vérité connue (HERALD 96), 80 territoires artificiels, "
            "graine 9961. Marginales, autocorrélations, dispersions, masques de publication "
            "et retards calibrés sur le panel français ; ce n'est pas la France.")

PROVENANCE: dict[str, dict] = {}
FAMILY_LABEL = {"commuting": "navettes", "similarity": "similarité",
                "complementarity": "complémentarité"}


def world(scenario="M1_MULTIRELATIONAL", scale=1.0):
    return synthetic_world(n_zones=N_ZONES, seed=SEED, scenario=scenario,
                           relational_scale=scale)


def draw_territory(ax, coords, *, sizes=None, colour="#DEDEDE", edge="#9A9A9A", zorder=2):
    ax.scatter(coords[:, 0], coords[:, 1], s=sizes if sizes is not None else 46,
               c=colour, edgecolors=edge, linewidths=0.7, zorder=zorder)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_pairs(ax, coords, pairs, colour, *, width=1.0, alpha=0.7, zorder=3):
    segments = [[coords[i], coords[j]] for i, j in pairs]
    ax.add_collection(LineCollection(segments, colors=colour, linewidths=width,
                                     alpha=alpha, zorder=zorder))


# ── S01 ──────────────────────────────────────────────────────────────────────

def s01_territories() -> None:
    data = world()
    coords = data["truth"]["coordinates"]
    low = data["metadata"]["low_information"]

    use_style()
    fig = plt.figure(figsize=(15.5, 6.4))
    grid = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.5, 1.5], wspace=0.28)

    ax = fig.add_subplot(grid[0])
    sizes = 30 + 120 * (~low)
    draw_territory(ax, coords, sizes=sizes, colour=np.where(low, "#CFCFCF", PALETTE["union"]))
    for index in (0, 1, 2):
        ax.annotate(f"Z{index:04d}", coords[index], textcoords="offset points",
                    xytext=(7, 6), fontsize=10)
    ax.set_title("80 territoires artificiels\net leurs volumes", fontsize=13)
    ax.plot([], [], "o", color=PALETTE["union"], label="zone ordinaire")
    ax.plot([], [], "o", color="#CFCFCF", label="zone à faible information")
    ax.legend(fontsize=9, loc="lower left")

    axes = [fig.add_subplot(grid[1]), fig.add_subplot(grid[2])]
    names = ["headcount", "unemployment"]
    labels = ["effectifs (log)", "taux de chômage (logit)"]
    years = data["metadata"]["years"]
    for ax, name, label in zip(axes, names, labels):
        values = data["signals"][name]["values"]
        for index, colour in zip((0, 1, 2), (PALETTE["commuting"], PALETTE["herald"],
                                             PALETTE["complementarity"])):
            series = values[:, index]
            observed = ~np.isnan(series)
            ax.plot(years[observed], series[observed], color=colour, lw=1.4,
                    label=f"Z{index:04d}")
        ax.set_title(f"{label}\npublié seulement quand la source publie", fontsize=13)
        ax.set_xlabel("année")
        ax.legend(fontsize=9)

    fig.suptitle("Le monde synthétique : des territoires, des volumes, des signaux publiés",
                 y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH", PALETTE["true_graph"])
    footnote(fig, SYN_NOTE + " Une cellule non publiée reste absente : l'absence est un canal "
                             "de masque, jamais un zéro.", width=140)
    save(fig, "S01_synthetic_territories")
    PROVENANCE["S01"] = {"zones": N_ZONES, "seed": SEED,
                         "low_information_zones": int(low.sum())}


# ── S02, S03, S04, S10 ───────────────────────────────────────────────────────

def s02_true_graph() -> None:
    data = world()
    coords = data["truth"]["coordinates"]
    edges = data["truth"]["relations"]["edges"]
    commuting = data["truth"]["commuting"]
    outside = data["truth"]["diagnostics"]["true_edges_outside_commuting"]

    use_style()
    fig, ax = plt.subplots(figsize=(8.4, 8.0))
    draw_territory(ax, coords)
    for family in FAMILY_ORDER:
        draw_pairs(ax, coords, edges[family], PALETTE[family], width=1.5, alpha=0.8)
    handles = [Line2D([], [], color=PALETTE[f], lw=2.4,
                      label=f"{FAMILY_LABEL[f]} — {len(edges[f])} arêtes, "
                            f"{outside[f]} hors navettes")
               for f in FAMILY_ORDER]
    ax.legend(handles=handles, fontsize=10, loc="lower left")
    ax.set_title("Le graphe VRAI : trois familles de relations")
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — connu du seul évaluateur", PALETTE["true_graph"])
    total = sum(len(edges[f]) for f in FAMILY_ORDER)
    footnote(fig, SYN_NOTE + f" {sum(outside.values())} des {total} arêtes vraies relient des "
                             f"zones sans navettes entre elles : c'est précisément ce que "
                             f"l'étape précédente ne pouvait pas tester. Ce graphe n'atteint "
                             f"jamais le modèle : ni comme entrée, ni comme étiquette, ni "
                             f"dans une perte.", width=120)
    save(fig, "S02_true_graph")
    PROVENANCE["S02"] = {"edges_per_family": {f: len(edges[f]) for f in FAMILY_ORDER},
                         "outside_commuting": outside,
                         "commuting_density": float((commuting > 0).mean())}


def s03_candidate_support() -> None:
    data = world()
    coords = data["truth"]["coordinates"]
    commuting = data["truth"]["commuting"]
    edges = data["truth"]["relations"]["edges"]

    tasks = {t["support"]: t for t in herald96_tasks()
             if t["scenario"] == "M1_MULTIRELATIONAL" and t["relational_scale"] == 1.0
             and t["seed"] == SEED}
    commuting_pairs = [(i, j) for i in range(N_ZONES) for j in range(N_ZONES)
                       if i != j and commuting[i, j] > 0]
    rng = np.random.default_rng(20260813)
    drawn = [commuting_pairs[p] for p in rng.choice(len(commuting_pairs), size=400,
                                                    replace=False)]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 7.2))
    draw_territory(axes[0], coords)
    draw_pairs(axes[0], coords, drawn, PALETTE["commuting"], width=0.4, alpha=0.22)
    axes[0].set_title(f"Support candidat « navettes »\n"
                      f"{tasks['commuting_only']['arm']['n_pairs']} paires "
                      f"({len(drawn)} tracées)", fontsize=13)

    draw_territory(axes[1], coords)
    inside, missed = [], []
    for family in FAMILY_ORDER:
        for i, j in edges[family]:
            (inside if commuting[i, j] > 0 else missed).append((i, j))
    draw_pairs(axes[1], coords, drawn, PALETTE["commuting"], width=0.35, alpha=0.12)
    draw_pairs(axes[1], coords, inside, PALETTE["true_graph"], width=1.6, alpha=0.9, zorder=5)
    draw_pairs(axes[1], coords, missed, PALETTE["warning"], width=1.6, alpha=0.9, zorder=5)
    handles = [Line2D([], [], color=PALETTE["true_graph"], lw=2.4,
                      label=f"arête vraie DANS le support navettes — {len(inside)}"),
               Line2D([], [], color=PALETTE["warning"], lw=2.4,
                      label=f"arête vraie HORS du support navettes — {len(missed)}")]
    axes[1].legend(handles=handles, fontsize=10, loc="lower left")
    axes[1].set_title("Ce que le support des navettes ne peut pas contenir", fontsize=13)

    fig.suptitle("Le support candidat, et son plafond", y=1.02)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH", PALETTE["true_graph"])
    footnote(fig, SYN_NOTE + f" Un modèle restreint aux navettes ne peut pas retrouver les "
                             f"{len(missed)} arêtes rouges, quelle que soit sa qualité. C'est "
                             f"pourquoi HERALD 96 compare quatre supports, dont « toutes les "
                             f"paires », qui les contient toutes.", width=140)
    save(fig, "S03_candidate_support")
    PROVENANCE["S03"] = {"support_sizes": {k: v["arm"]["n_pairs"] for k, v in tasks.items()},
                         "true_edges_inside_commuting": len(inside),
                         "true_edges_outside_commuting": len(missed)}


def s04_learned_scores() -> None:
    """What the arm actually assigned. There is no per-edge dump, but the artefacts hold the
    mean score on true edges and on everything else, per family — which is the comparison the
    figure needs."""
    tasks = herald96_tasks()
    cells = group(tasks, "scenario", "relational_scale", "support")

    use_style()
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.6), sharey=True)
    scales = (0.0, 1.0, 2.0)
    for ax, family in zip(axes, FAMILY_ORDER):
        on_edge, elsewhere = [], []
        for scale in scales:
            rows = cells[("M1_MULTIRELATIONAL", scale, "typed_union")]
            on_edge.append(median([r["recovery"]["per_family"][family]["mean_score"]
                                   for r in rows]))
            elsewhere.append(median([r["recovery"]["per_family"][family]
                                     ["mean_score_elsewhere"] for r in rows]))
        x = np.arange(len(scales))
        ax.bar(x - 0.19, on_edge, width=0.36, color=PALETTE[family],
               label="paires qui SONT des arêtes vraies")
        ax.bar(x + 0.19, elsewhere, width=0.36, color="#CFCFCF",
               label="toutes les autres paires")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{s:g}×" for s in scales])
        ax.set_xlabel("intensité relationnelle")
        ax.set_title(FAMILY_LABEL[family], fontsize=13)
    axes[0].set_ylabel("contribution moyenne attribuée")
    axes[0].legend(fontsize=9.5, loc="lower left")
    fig.suptitle("Les scores appris ne séparent pas les arêtes vraies du reste", y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — mesuré", PALETTE["learned_graph"])
    footnote(fig, SYN_NOTE + " Union typée, médiane sur cinq graines finales (9961–9965). "
                             "Un séparateur utile donnerait des barres colorées nettement "
                             "plus hautes que les grises. Elles sont au même niveau, et à "
                             "l'intensité nominale elles sont très légèrement plus basses.",
             width=140)
    save(fig, "S04_learned_scores")
    PROVENANCE["S04"] = {"support": "typed_union", "scales": list(scales),
                         "seeds": [9961, 9962, 9963, 9964, 9965]}


def s10_true_versus_learned() -> None:
    data = world()
    coords = data["truth"]["coordinates"]
    edges = data["truth"]["relations"]["edges"]
    rows = group(herald96_tasks(), "scenario", "relational_scale", "support")[
        ("M1_MULTIRELATIONAL", 1.0, "typed_union")]
    budget = int(median([r["recovery"]["budget"] for r in rows]))
    in_support = int(median([r["recovery"]["n_true_in_support"] for r in rows]))
    recall = median([r["recovery"]["recall"] for r in rows])
    recovered = int(round(recall * in_support))

    all_true = [(i, j) for f in FAMILY_ORDER for i, j in edges[f]]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 7.2))
    draw_territory(axes[0], coords)
    for family in FAMILY_ORDER:
        draw_pairs(axes[0], coords, edges[family], PALETTE[family], width=1.4, alpha=0.85)
    axes[0].set_title(f"Graphe VRAI — {len(all_true)} arêtes", fontsize=13)

    draw_territory(axes[1], coords)
    draw_pairs(axes[1], coords, all_true, "#DCDCDC", width=1.2, alpha=0.9)
    rng = np.random.default_rng(SEED)
    picked = [all_true[p] for p in rng.choice(len(all_true), size=max(recovered, 1),
                                              replace=False)]
    draw_pairs(axes[1], coords, picked, PALETTE["learned_graph"], width=2.6, alpha=1.0,
               zorder=6)
    axes[1].set_title(f"Ce que le bras retrouve dans ses {budget} meilleures paires\n"
                      f"{recovered} sur les {in_support} arêtes vraies du support",
                      fontsize=13)
    handles = [Line2D([], [], color="#DCDCDC", lw=2.4, label="arête vraie non retrouvée"),
               Line2D([], [], color=PALETTE["learned_graph"], lw=3.0,
                      label="arête vraie retrouvée")]
    axes[1].legend(handles=handles, fontsize=10, loc="lower left")

    fig.suptitle("Graphe vrai contre graphe appris", y=1.02)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — schéma quantitatif", PALETTE["learned_graph"])
    footnote(fig, SYN_NOTE + f" Le monde compte {len(all_true)} arêtes vraies, dont "
                             f"{in_support} tombent dans l'union typée. Le rappel mesuré au "
                             f"budget est {recall:.4f} : {recovered} d'entre elles figure "
                             f"parmi les {budget} paires les mieux notées. LAQUELLE n'est pas "
                             f"reconstituable — les scores par arête ne sont pas conservés — "
                             f"donc l'arête surlignée à droite est tirée au hasard parmi les "
                             f"arêtes vraies : c'est le NOMBRE qui est mesuré, pas la "
                             f"position.", width=125)
    save(fig, "S10_true_versus_learned_graph")
    PROVENANCE["S10"] = {"true_edges": len(all_true), "budget": budget,
                         "true_edges_in_support": in_support,
                         "recall_at_budget": recall, "recovered": recovered,
                         "caveat": "the highlighted edge is illustrative; only the count "
                                   "is measured"}


# ── S05, S06, S07 ────────────────────────────────────────────────────────────

def _relational_field(scenario, scale):
    data = world(scenario=scenario, scale=scale)
    # `truth["relational"][signal]` is the relational term that actually reaches a zone's
    # latent path for that signal: the arriving quantity after the signal's loading, which is
    # what `relational_scale` multiplies. `total_arriving` is the same quantity *before* the
    # loading, so it does not move with the scale and is the wrong array to draw here.
    arriving = np.asarray(data["truth"]["relational"]["headcount"])
    return data, arriving


def s05_s06_mechanism() -> None:
    for stem, scenario, title, key in [
            ("S05_no_mechanism", "M0_NULL",
             "Scénario SANS mécanisme : les arêtes existent, rien n'y circule", "S05"),
            ("S06_with_mechanism", "M1_MULTIRELATIONAL",
             "Scénario AVEC mécanisme : la même géographie, la même graine", "S06")]:
        data, arriving = _relational_field(scenario, 1.0)
        coords = data["truth"]["coordinates"]
        edges = data["truth"]["relations"]["edges"]
        strength = np.sqrt((arriving ** 2).mean(axis=0))

        use_style()
        fig, axes = plt.subplots(1, 2, figsize=(15.0, 6.8))
        # A common reference across both scenarios, so that the empty panel reads as empty
        # rather than being rescaled until it looks full.
        reference = 0.075
        draw_territory(axes[0], coords, sizes=22 + 300 * strength / reference,
                       colour=PALETTE["herald"] if strength.max() > 0 else "#DEDEDE")
        for family in FAMILY_ORDER:
            draw_pairs(axes[0], coords, edges[family], PALETTE[family], width=1.0, alpha=0.45)
        axes[0].set_title("Intensité de ce qui ARRIVE dans chaque zone\n"
                          f"RMS max = {strength.max():.4f}", fontsize=13)

        years = data["metadata"]["years"]
        for index, colour in zip((0, 1, 2), (PALETTE["commuting"], PALETTE["herald"],
                                             PALETTE["complementarity"])):
            axes[1].plot(years, arriving[:, index], color=colour, lw=1.5,
                         label=f"Z{index:04d}")
        axes[1].axhline(0, color="#999999", lw=0.9, ls="--")
        axes[1].set_ylim(-0.11, 0.11)
        axes[1].set_xlabel("année")
        axes[1].set_ylabel("composante relationnelle reçue")
        axes[1].set_title("La même quantité, dans le temps", fontsize=13)
        axes[1].legend(fontsize=9.5)

        fig.suptitle(title, y=1.02)
        stamp(fig, "SYNTHETIC_KNOWN_TRUTH", PALETTE["true_graph"])
        footnote(fig, SYN_NOTE + " Les deux scénarios tirent les MÊMES paires depuis le même "
                                 "flux aléatoire : ils ne diffèrent que par le fait que "
                                 "quelque chose voyage, ou non, le long des arêtes. C'est ce "
                                 "qui rend le scénario nul interprétable — une méthode qui y "
                                 "trouve une structure a reproduit ce qu'on lui a donné.",
                 width=140)
        save(fig, stem)
        PROVENANCE[key] = {"scenario": scenario, "max_arriving_rms": float(strength.max())}


def s07_scales() -> None:
    scales = (0.0, 0.5, 1.0, 2.0)
    fields = {s: _relational_field("M1_MULTIRELATIONAL", s) for s in scales}
    reference = max(np.sqrt((a ** 2).mean(axis=0)).max() for _, a in fields.values())

    use_style()
    fig, axes = plt.subplots(1, 4, figsize=(19.5, 5.6))
    peaks = {}
    for ax, scale in zip(axes, scales):
        data, arriving = fields[scale]
        coords = data["truth"]["coordinates"]
        strength = np.sqrt((arriving ** 2).mean(axis=0))
        peaks[scale] = float(strength.max())
        draw_territory(ax, coords, sizes=22 + 300 * strength / reference,
                       colour=PALETTE["herald"] if strength.max() > 0 else "#DEDEDE")
        for family in FAMILY_ORDER:
            draw_pairs(ax, coords, data["truth"]["relations"]["edges"][family],
                       PALETTE[family], width=0.8, alpha=0.35)
        ax.set_title(f"{scale:g}×   RMS max {strength.max():.4f}", fontsize=13)
    fig.suptitle("La même échelle relationnelle, montée du silence au double du nominal",
                 y=1.04)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH", PALETTE["true_graph"])
    footnote(fig, SYN_NOTE + " Une seule quantité varie entre ces quatre mondes : "
                             "`relational_scale`. Territoires, graphe, états latents, bruit "
                             "et masques sont identiques cellule par cellule — une garde le "
                             "vérifie, et l'appariement a dû être réparé avant que l'échelle "
                             "ne veuille dire quelque chose. Le rayon est à échelle commune.",
             width=140)
    save(fig, "S07_relational_scales")
    PROVENANCE["S07"] = {"peak_arriving_rms_by_scale": peaks}


# ── S08, S09, S11, S12 ───────────────────────────────────────────────────────

def s08_s09_oracle_versus_model() -> None:
    ladder = group(herald95_tasks(), "scenario", "relational_scale")
    cells = group(herald96_tasks(), "scenario", "relational_scale", "support")
    scales95 = (0.0, 0.5, 1.0, 2.0)
    scales96 = (0.0, 1.0, 2.0)

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(15.6, 6.2))

    ax = axes[0]
    for scenario, marker in [("N2_NONLINEAR", "o"), ("N3_REGIME", "s"),
                             ("N4_INTERACTION", "^")]:
        values = [median([r["arms"]["oracle_relational"]["gain_over_ridge_linear"]
                          for r in ladder[(scenario, s)]]) for s in scales95]
        ax.plot(scales95, values, marker=marker, color=PALETTE["oracle"], lw=2.0, ms=8,
                label=f"oracle — {scenario}")
    oracle96 = [median([r["oracles"]["all_families"]
                        for r in cells[("M1_MULTIRELATIONAL", s, "typed_union")]])
                for s in scales96]
    ax.plot(scales96, oracle96, marker="D", color=PALETTE["complementarity"], lw=2.0, ms=8,
            ls="--", label="oracle — HERALD 96 (cible résiduelle)")
    ax.axhline(0, color="#999999", lw=1.0)
    ax.set_xlabel("intensité relationnelle")
    ax.set_ylabel("part de l'erreur retirée")
    ax.set_title("L'ORACLE répond à l'intensité", fontsize=14)
    ax.legend(fontsize=9.5)

    ax = axes[1]
    for scenario, marker in [("N2_NONLINEAR", "o"), ("N3_REGIME", "s"),
                             ("N4_INTERACTION", "^")]:
        values = [median([r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"]
                          for r in ladder[(scenario, s)]]) for s in scales95]
        ax.plot(scales95, values, marker=marker, color=PALETTE["herald"], lw=2.0, ms=8,
                label=f"réseau HERALD — {scenario}")
    null = median([r["arms"]["mlp_nonlinear"]["gain_over_ridge_linear"]
                   for r in ladder[("N0_NULL", 1.0)]])
    ax.axhline(null, color=PALETTE["null"], lw=2.0, ls=":",
               label=f"gain dans le scénario SANS mécanisme ({null:+.3f})")
    arm = [median([r["arm"]["residual_gain"]
                   for r in cells[("M1_MULTIRELATIONAL", s, "typed_union")]])
           for s in scales96]
    ax.plot(scales96, arm, marker="D", color=PALETTE["learned_graph"], lw=2.0, ms=8, ls="--",
            label="bras Neural Granger — HERALD 96")
    ax.axhline(0, color="#999999", lw=1.0)
    ax.set_xlabel("intensité relationnelle")
    ax.set_title("LES MODÈLES n'y répondent pas", fontsize=14)
    ax.legend(fontsize=9.5)

    fig.suptitle("Répondre à l'intensité : la seule preuve qu'un gain est relationnel", y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — mesuré", PALETTE["oracle"])
    footnote(fig, "HERALD 95 : 280 zones, cible croissance logarithmique, trois graines "
                  "(9901–9903). HERALD 96 : 80 zones, cible résiduelle après un baseline "
                  "local gelé, cinq graines (9961–9965). Les deux protocoles sont tracés "
                  "ensemble parce qu'ils partagent la question — répondre à l'intensité — et "
                  "PAS parce que leurs niveaux se comparent : les cibles diffèrent, et un "
                  "classement numérique commun serait faux. L'échelle 4× est un test de "
                  "saturation et n'est interprétée nulle part.", width=140)
    save(fig, "S08_S09_oracle_and_models_over_scale")
    PROVENANCE["S08_S09"] = {"herald95_scales": list(scales95),
                             "herald96_scales": list(scales96),
                             "network_gain_in_null": null}


def s11_auprc_versus_prevalence() -> None:
    cells = group(herald96_tasks(), "scenario", "relational_scale", "support")
    supports = ["commuting_only", "similarity_only", "typed_union", "all_pairs"]
    labels = ["navettes\nseules", "similarité\nseule", "union\ntypée", "toutes\nles paires"]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(15.6, 6.0), sharey=False)
    for ax, scenario, title in [
            (axes[0], "M1_MULTIRELATIONAL", "AVEC mécanisme (1×)"),
            (axes[1], "M0_NULL", "SANS mécanisme")]:
        scale = 1.0
        auprc = [median([r["recovery"]["auprc"] for r in cells[(scenario, scale, s)]])
                 for s in supports]
        prevalence = [median([r["recovery"]["prevalence"]
                              for r in cells[(scenario, scale, s)]]) for s in supports]
        x = np.arange(len(supports))
        ax.bar(x - 0.19, auprc, width=0.36, color=PALETTE["learned_graph"],
               label="AUPRC du modèle")
        ax.bar(x + 0.19, prevalence, width=0.36, color=PALETTE["prevalence"],
               label="prévalence (ce que le hasard obtient)")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_title(title, fontsize=14)
        ax.set_ylabel("AUPRC")
        ax.legend(fontsize=9.5)
    fig.suptitle("AUPRC contre prévalence : le hasard obtient déjà ce score", y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — mesuré", PALETTE["learned_graph"])
    footnote(fig, SYN_NOTE + " Médiane sur cinq graines finales. La prévalence est la part "
                             "d'arêtes vraies dans le support, donc la valeur qu'obtient un "
                             "classement aléatoire. Le support « similarité seule » dépasse "
                             "sa prévalence d'environ un quart — mais il le fait AUTANT dans "
                             "le scénario sans mécanisme, ce qui en fait une propriété du "
                             "support et non une récupération.", width=140)
    save(fig, "S11_auprc_versus_prevalence")
    PROVENANCE["S11"] = {"supports": supports, "scale": 1.0,
                         "reading_rule": "a bar above prevalence counts only if the same bar "
                                         "does not rise in M0_NULL"}


def s12_prediction_versus_recovery() -> None:
    cells = group(herald96_tasks(), "scenario", "relational_scale", "support")
    supports = ["commuting_only", "similarity_only", "typed_union", "all_pairs"]
    labels = ["navettes seules", "similarité seule", "union typée", "toutes les paires"]

    use_style()
    fig, ax = plt.subplots(figsize=(9.6, 7.2))
    for support, label in zip(supports, labels):
        rows = cells[("M1_MULTIRELATIONAL", 1.0, support)]
        gain = median([r["arm"]["residual_gain"] for r in rows])
        lift = median([r["recovery"]["auprc"] - r["recovery"]["prevalence"] for r in rows])
        oracle = median([r["oracles"]["all_families"] for r in rows])
        ax.scatter(gain, lift, s=260, color=PALETTE["learned_graph"], zorder=5,
                   edgecolors="white", linewidths=1.4)
        ax.annotate(f"{label}\noracle {oracle:+.3f}", (gain, lift),
                    textcoords="offset points", xytext=(12, 10), fontsize=10)
    ax.axhline(0, color="#999999", lw=1.2)
    ax.axvline(0, color="#999999", lw=1.2)
    ax.set_xlabel("prévision  →  gain sur le résidu (médiane)")
    ax.set_ylabel("récupération  →  AUPRC moins prévalence")
    ax.set_title("Prévoir mieux et retrouver les arêtes\nsont deux questions distinctes")
    ax.text(0.02, 0.97, "quadrant utile :\nprévoit ET retrouve", transform=ax.transAxes,
            va="top", fontsize=10, color="#777777")
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — mesuré", PALETTE["learned_graph"])
    footnote(fig, SYN_NOTE + " Aucun support n'atteint le quadrant supérieur droit. Le seul "
                             "point dont le lift est positif — similarité seule — l'est "
                             "autant sans mécanisme. L'oracle indiqué à côté de chaque point "
                             "est ce qui restait à gagner.", width=125)
    save(fig, "S12_prediction_versus_recovery")
    PROVENANCE["S12"] = {"scale": 1.0, "supports": supports}


def main() -> None:
    s01_territories()
    s02_true_graph()
    s03_candidate_support()
    s04_learned_scores()
    s05_s06_mechanism()
    s07_scales()
    s08_s09_oracle_versus_model()
    s10_true_versus_learned()
    s11_auprc_versus_prevalence()
    s12_prediction_versus_recovery()
    write_provenance("figures_synthetic.json", {
        "kind": "herald_visual_evidence_provenance",
        "category": "SYNTHETIC_KNOWN_TRUTH",
        "world": {"generator": "src/data/synthetic/generate_multirelational_v96.py",
                  "seed": SEED, "n_zones": N_ZONES},
        "rule": "the world is regenerated deterministically; every measured quantity is read "
                "from hpc_results, never recomputed by fitting anything",
        "figures": PROVENANCE})
    print(f"{len(PROVENANCE)} synthetic figures written")


if __name__ == "__main__":
    main()
