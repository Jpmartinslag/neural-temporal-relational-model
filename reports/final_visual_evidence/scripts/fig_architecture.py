"""Architecture diagrams — A01 global flow, A02 what exists, A03 what does not.

A03 is the one that needs care. It draws a proposal, and a proposal drawn in the same visual
language as a result is read as a result. It is therefore stamped, banded and captioned as not
implemented, and every box in it is hatched.

Run: python reports/final_visual_evidence/scripts/fig_architecture.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from herald_evidence import PALETTE, footnote, save, stamp, use_style, write_provenance

PROVENANCE: dict[str, dict] = {}


def canvas(width, height, title):
    use_style()
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_axis_off()
    ax.grid(False)
    ax.set_title(title, pad=18)
    return fig, ax


def box(ax, x, y, w, h, text, *, colour, facecolour=None, fontsize=11, hatch=None,
        text_colour=None, lw=1.6):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.6",
        linewidth=lw, edgecolor=colour, facecolor=facecolour or "#FFFFFF",
        hatch=hatch, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            zorder=4, color=text_colour or PALETTE["text"], linespacing=1.35)


def arrow(ax, start, end, *, colour="#777777", style="-|>", lw=1.6, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=16, linewidth=lw, color=colour,
        linestyle=ls, zorder=2,
        connectionstyle=f"arc3,rad={rad}"))


def label(ax, x, y, text, *, fontsize=9.5, colour="#777777", style="italic", ha="center"):
    ax.text(x, y, text, fontsize=fontsize, color=colour, style=style, ha=ha, va="center",
            zorder=5)


# ── A01 ──────────────────────────────────────────────────────────────────────

def a01_global_flow() -> None:
    fig, ax = canvas(16.5, 8.2, "Le flux global du projet")

    steps = [
        ("Données\néconomiques", PALETTE["commuting"],
         "Urssaf, Insee, Flores,\nSirene/SIDE"),
        ("Préparation et\ndisponibilité", PALETTE["commuting"],
         "masques de publication,\nretards, ruptures"),
        ("Représentation\ntemporelle", PALETTE["herald"],
         "niveau, croissance, régime,\ncomposante nationale"),
        ("Relations\ncandidates", PALETTE["similarity"],
         "navettes, similarité,\ncomplémentarité"),
        ("Modèles classiques\net neuronaux", PALETTE["other_neural"],
         "persistance, Granger,\nMTGNN, NRI, HERALD"),
        ("Validation\nsynthétique", PALETTE["true_graph"],
         "vérité connue,\noracle, scénario nul"),
        ("Analyse française\nexploratoire", PALETTE["complementarity"],
         "résultats temporels et\ndonnées observées"),
        ("Appui territorial\nfutur", PALETTE["null"],
         "non atteint\nà cette étape"),
    ]
    width, gap = 10.4, 1.6
    x = 2.0
    for index, (name, colour, caption) in enumerate(steps):
        y = 56
        dashed = index == len(steps) - 1
        box(ax, x, y, width, 20, name, colour=colour,
            facecolour="#FFFFFF" if not dashed else "#F6F6F6",
            fontsize=11.5, lw=1.4 if not dashed else 1.2)
        ax.text(x + width / 2, y - 4, caption, ha="center", va="top", fontsize=9,
                color="#777777", linespacing=1.3)
        if index:
            arrow(ax, (x - gap + 0.2, y + 10), (x - 0.4, y + 10))
        x += width + gap

    ax.axvspan(0, 0, 0, 0)
    band_y = 20
    box(ax, 2.0, band_y, 43.2, 12,
        "Ce qui a été démontré\nreprésentation temporelle, oracle, contrôle nul",
        colour=PALETTE["complementarity"], facecolour="#F1F8F4", fontsize=11)
    box(ax, 48.4, band_y, 43.2, 12,
        "Ce qui n'a PAS été démontré\nrécupération fiable des arêtes, application à la France",
        colour=PALETTE["warning"], facecolour="#FBF1F1", fontsize=11)

    stamp(fig, "REAL_FRANCE + SYNTHETIC_KNOWN_TRUTH", PALETTE["commuting"])
    footnote(fig, "La flèche va de gauche à droite, mais la validation synthétique est ce qui "
                  "AUTORISE l'étape suivante et non ce qui la suit : l'analyse française n'est "
                  "ouverte qu'aux résultats que le monde à vérité connue a soutenus. "
                  "L'« appui territorial futur » est tracé en gris parce que rien à cette "
                  "étape ne l'a atteint.", width=170)
    save(fig, "A01_project_flow")
    PROVENANCE["A01"] = {"steps": [name.replace("\n", " ") for name, _, _ in steps]}


# ── A02 ──────────────────────────────────────────────────────────────────────

def a02_current_architecture() -> None:
    fig, ax = canvas(13.0, 12.0, "L'architecture actuelle")

    box(ax, 30, 88, 40, 9, "Panel multisignal\ncinq signaux, masques de disponibilité",
        colour=PALETTE["commuting"], fontsize=11)
    box(ax, 30, 75, 40, 9, "Attributs temporels\n11 colonnes + masque, par signal",
        colour=PALETTE["herald"], fontsize=11)
    box(ax, 30, 62, 40, 9, "Baseline temporel local\nGELÉ pendant l'entraînement relationnel",
        colour=PALETTE["true_graph"], facecolour="#F4F4F4", fontsize=11)
    box(ax, 30, 49, 40, 9, "Résidu non expliqué\ny[t+1] − baseline[t+1]",
        colour=PALETTE["true_graph"], fontsize=11)

    supports = [("Navettes", PALETTE["commuting"], 3),
                ("Similarité", PALETTE["similarity"], 36),
                ("Complémentarité", PALETTE["complementarity"], 69)]
    for name, colour, x in supports:
        box(ax, x, 34, 28, 8, f"Support {name.lower()}", colour=colour, fontsize=10.5)
        arrow(ax, (x + 14, 34), (x + 14, 29.4), colour=colour, ls="--")

    box(ax, 8, 20, 84, 9,
        "Contribution des AUTRES zones\nune fonction partagée, pas de paramètre par paire, "
        "pas de chemin local, pas de boucle sur soi",
        colour=PALETTE["learned_graph"], fontsize=10.5)
    box(ax, 30, 7, 40, 8, "Prévision finale\nbaseline + contributions", colour=PALETTE["herald"],
        fontsize=11)

    for y0, y1 in ((88, 84.6), (75, 71.6), (62, 58.6)):
        arrow(ax, (50, y0), (50, y1 + 0.4))
    # The residual is the target the contributions must explain. It is routed down the left,
    # because the middle of the diagram belongs to the three supports.
    arrow(ax, (30, 53.5), (4, 53.5), style="-", colour="#777777")
    arrow(ax, (4, 53.5), (4, 24.5), style="-", colour="#777777")
    arrow(ax, (4, 24.5), (7.4, 24.5), colour="#777777")
    label(ax, 4, 40, "cible", fontsize=9.5, ha="center")
    arrow(ax, (50, 20), (50, 15.6))

    box(ax, 74, 44, 24, 14,
        "Évaluation séparée\n① prévision\n② récupération des arêtes",
        colour=PALETTE["warning"], facecolour="#FBF1F1", fontsize=10)
    arrow(ax, (70, 11), (86, 43.4), colour=PALETTE["warning"], ls=":", rad=0.2)

    label(ax, 15, 65, "le baseline ne bouge plus :\nun checksum le prouve\n"
                      "dans les 120 tâches", fontsize=9)
    label(ax, 86, 68, "les poids de navettes et de\nsimilarité PROPOSENT des\ncandidats ; "
                      "ils n'entrent\njamais comme valeur", fontsize=9)

    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — implémenté et exécuté", PALETTE["true_graph"])
    footnote(fig, "Le bras relationnel n'a le droit d'expliquer que ce que la trajectoire "
                  "locale n'expliquait pas. C'est ce qui rend son gain interprétable : il ne "
                  "peut pas gagner en apprenant mieux l'histoire d'une zone, seulement en "
                  "apprenant quelque chose sur ses voisines. La séparation entre l'évaluation "
                  "prédictive et l'évaluation relationnelle est la seconde protection : une "
                  "méthode peut prévoir mieux sans rien retrouver, et c'est exactement ce qui "
                  "est observé.", width=135)
    save(fig, "A02_current_architecture")
    PROVENANCE["A02"] = {"status": "implemented and executed in HERALD 96",
                         "guards": "baseline checksum identical before and after relational "
                                   "training in all 120 tasks"}


# ── A03 ──────────────────────────────────────────────────────────────────────

def a03_future_architecture() -> None:
    fig, ax = canvas(13.0, 12.0, "PROPOSED FUTURE ARCHITECTURE — NOT IMPLEMENTED")
    ax.set_title(ax.get_title(), color=PALETTE["warning"])

    ax.add_patch(FancyBboxPatch(
        (1, 1), 98, 92, boxstyle="round,pad=0.8,rounding_size=2",
        linewidth=2.4, edgecolor=PALETTE["warning"], facecolor="#FFFCFC",
        linestyle="--", zorder=1))
    ax.text(50, 96.5, "Aucun résultat de ce schéma n'existe. "
                      "Rien ici n'a été entraîné, mesuré ni validé.",
            ha="center", va="center", fontsize=11, color=PALETTE["warning"],
            fontweight="bold", zorder=5)

    hatch, grey = "///", "#F6F6F6"
    encoders = [("Encodeur\neffectifs", 4), ("Encodeur\nmasse salariale", 23),
                ("Encodeur\nétablissements", 42), ("Encodeur\nchômage", 61),
                ("Encodeur\ncréations", 80)]
    for name, x in encoders:
        box(ax, x, 76, 16, 9, name, colour=PALETTE["herald"], facecolour=grey,
            hatch=hatch, fontsize=9.5)

    modules = [("Module\nnavettes", PALETTE["commuting"], 8),
               ("Module\nsimilarité", PALETTE["similarity"], 37),
               ("Module\ncomplémentarité", PALETTE["complementarity"], 66)]
    for name, colour, x in modules:
        box(ax, x, 60, 26, 9, name, colour=colour, facecolour=grey, hatch=hatch,
            fontsize=10)
        arrow(ax, (x + 13, 76), (x + 13, 69.4), colour="#CCCCCC", ls="--")

    box(ax, 22, 45, 56, 9, "Fusion multirelationnelle PAR ATTENTION",
        colour=PALETTE["learned_graph"], facecolour=grey, hatch=hatch, fontsize=11.5)
    for _, _, x in modules:
        arrow(ax, (x + 13, 60), (50, 54.4), colour="#CCCCCC", ls="--")

    box(ax, 30, 32, 40, 8, "Graphe dynamique", colour=PALETTE["learned_graph"],
        facecolour=grey, hatch=hatch, fontsize=11)
    box(ax, 6, 18, 26, 8, "Prévision", colour=PALETTE["herald"], facecolour=grey,
        hatch=hatch, fontsize=11)
    box(ax, 37, 18, 26, 8, "Interprétation", colour=PALETTE["true_graph"], facecolour=grey,
        hatch=hatch, fontsize=11)
    box(ax, 68, 18, 26, 8, "Appui possible à la\nrecommandation",
        colour=PALETTE["null"], facecolour=grey, hatch=hatch, fontsize=10)
    arrow(ax, (50, 45), (50, 40.4), colour="#CCCCCC", ls="--")
    for x in (19, 50, 81):
        arrow(ax, (50, 32), (x, 26.4), colour="#CCCCCC", ls="--")

    ax.text(50, 10, "Condition d'entrée : cette direction ne devient testable que si "
                    "l'étape\nd'IDENTIFICATION est traitée. HERALD 96 a montré qu'élargir "
                    "les candidats\nne suffit pas — « toutes les paires » contient toutes les "
                    "arêtes vraies\net n'en retrouve aucune.",
            ha="center", va="center", fontsize=10, color="#666666", linespacing=1.5)

    stamp(fig, "FUTURE_WORK — NOT IMPLEMENTED", PALETTE["warning"])
    footnote(fig, "Ce schéma est une proposition d'architecture, au même statut qu'un "
                  "paragraphe de « travaux futurs ». Il ne doit jamais être présenté à côté "
                  "d'un tableau de résultats sans cette bannière, parce qu'un diagramme "
                  "dessiné dans le même langage visuel qu'un résultat se lit comme un "
                  "résultat.", width=135)
    save(fig, "A03_future_architecture")
    PROVENANCE["A03"] = {"status": "NOT IMPLEMENTED, NOT VALIDATED",
                         "rule": "never displayed without the banner"}


def main() -> None:
    a01_global_flow()
    a02_current_architecture()
    a03_future_architecture()
    write_provenance("figures_architecture.json", {
        "kind": "herald_visual_evidence_provenance",
        "category": "diagram",
        "rule": "A03 is a proposal and is marked as such in the title, a banner, a stamp, "
                "hatched boxes and its caption",
        "figures": PROVENANCE})
    print(f"{len(PROVENANCE)} architecture diagrams written")


if __name__ == "__main__":
    main()
