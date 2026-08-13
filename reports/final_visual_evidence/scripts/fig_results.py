"""Result figures — R01 to R06.

Four experiments are kept apart on purpose, because their targets, populations and supports
differ and a single chart mixing them would be false:

    HERALD 94  temporal prediction, 280 zones, log-growth, six scenarios
    HERALD 93  main synthetic benchmark, 280 zones, log-growth, six methods
    HERALD 95  scale diagnostic, 280 zones, one quantity varied
    HERALD 96  residual diagnostic, 80 zones, residual target, four supports

No figure here ranks a HERALD 93 number against a HERALD 96 number.

Run: python reports/final_visual_evidence/scripts/fig_results.py
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from herald_evidence import (PALETTE, footnote, group, herald93_summary, herald94_tasks,
                             herald95_tasks, herald96_tasks, median, method_colour, save,
                             stamp, use_style, write_provenance)

PROVENANCE: dict[str, dict] = {}

LABEL93 = {"persistence@0": "Persistance", "sparse_var@0": "Granger (Lasso)",
           "mtgnn@64": "MTGNN @64", "nri@64": "NRI @64", "herald@32": "HERALD @32",
           "herald@64": "HERALD @64", "herald@128": "HERALD @128"}
COLOUR93 = {"persistence@0": PALETTE["null"], "sparse_var@0": PALETTE["classical"],
            "mtgnn@64": PALETTE["other_neural"], "nri@64": PALETTE["other_neural"],
            "herald@32": PALETTE["herald"], "herald@64": PALETTE["herald"],
            "herald@128": PALETTE["herald"]}


# ── R01 ──────────────────────────────────────────────────────────────────────

def r01_temporal_performance() -> None:
    by_scenario = group(herald94_tasks(), "scenario")
    scenarios = ["N0_NULL", "N1_LINEAR", "N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION",
                 "N5_REDUNDANT"]

    use_style()
    fig, ax = plt.subplots(figsize=(11.6, 6.4))
    x = np.arange(len(scenarios))
    medians, spreads = [], []
    for scenario in scenarios:
        rows = by_scenario[(scenario,)]
        values = [r["arms"]["ridge_linear"]["gain_over_best_single"] for r in rows]
        medians.append(median(values))
        spreads.append(values)
    ax.bar(x, medians, width=0.6, color=PALETTE["herald"], label="médiane sur cinq graines")
    for index, values in enumerate(spreads):
        ax.scatter([index] * len(values), values, s=44, color="#333333", zorder=5,
                   label="graine individuelle" if index == 0 else None)
    ax.axhline(0, color="#777777", lw=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], fontsize=10.5)
    ax.set_ylabel("part de l'erreur quadratique retirée")
    ax.set_title("La représentation temporelle, contre le meilleur signal isolé")
    ax.legend(fontsize=10)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — HERALD 94", PALETTE["herald"])
    footnote(fig, "280 zones synthétiques, douze origines glissantes, cinq graines finales "
                  "(9801–9805), modèle linéaire régularisé sur 120 colonnes contre la "
                  "meilleure colonne unique — `headcount.relative` dans les six scénarios et "
                  "les trente tâches. Le gain est aussi grand dans le scénario SANS mécanisme "
                  "relationnel : c'est une propriété de la représentation d'une trajectoire, "
                  "pas un indice de relation territoriale.", width=125)
    save(fig, "R01_temporal_performance")
    PROVENANCE["R01"] = {"scenarios": scenarios, "medians": medians}


# ── R02 ──────────────────────────────────────────────────────────────────────

def r02_skill_versus_persistence() -> None:
    table = herald93_summary()["table"]
    order = sorted(table, key=lambda k: -table[k]["forecast_skill_median"])

    use_style()
    fig, ax = plt.subplots(figsize=(10.6, 6.2))
    values = [table[k]["forecast_skill_median"] for k in order]
    colours = [COLOUR93[k] for k in order]
    ax.barh(np.arange(len(order)), values, color=colours, height=0.62)
    ax.set_yticks(np.arange(len(order)))
    ax.set_yticklabels([LABEL93[k] for k in order])
    ax.invert_yaxis()
    ax.axvline(0, color="#333333", lw=1.6)
    ax.set_xlabel("skill contre la persistance  (positif = mieux que la persistance)")
    ax.set_title("Aucune méthode ne bat la persistance")
    for index, value in enumerate(values):
        ax.text(value + (0.006 if value >= 0 else -0.006), index, f"{value:+.4f}",
                va="center", ha="left" if value >= 0 else "right", fontsize=10)
    ax.set_xlim(min(values) - 0.05, max(0.02, max(values) + 0.05))
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — HERALD 93", PALETTE["herald"])
    footnote(fig, "280 zones synthétiques, croissance logarithmique à l'horizon 1, douze "
                  "origines, cinq graines, scénario S1_SHARED. Le meilleur résultat, +0,0001, "
                  "est la persistance à quatre décimales. C'est une propriété de la CIBLE — "
                  "l'autocorrélation vit dans le niveau, et la différencier laisse peu à "
                  "prévoir — et elle s'applique identiquement aux six méthodes.", width=125)
    save(fig, "R02_forecast_skill")
    PROVENANCE["R02"] = {"skill": {LABEL93[k]: table[k]["forecast_skill_median"]
                                   for k in order}}


# ── R03 ──────────────────────────────────────────────────────────────────────

def r03_auprc_versus_prevalence() -> None:
    table = herald93_summary()["table"]
    order = [k for k in ["herald@128", "herald@32", "herald@64", "mtgnn@64", "sparse_var@0",
                         "nri@64"]]
    cells = group(herald96_tasks(), "scenario", "relational_scale", "support")
    supports = ["commuting_only", "similarity_only", "typed_union", "all_pairs"]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(16.0, 6.2))

    ax = axes[0]
    x = np.arange(len(order))
    s1 = [table[k]["auprc_median"] for k in order]
    s0 = [table[k]["s0_auprc_median"] for k in order]
    prevalence = table[order[0]]["prevalence_median"]
    ax.bar(x - 0.19, s1, width=0.36, color=PALETTE["herald"], label="AUPRC — S1 (mécanisme)")
    ax.bar(x + 0.19, s0, width=0.36, color=PALETTE["null"], label="AUPRC — S0 (sans mécanisme)")
    ax.axhline(prevalence, color=PALETTE["true_graph"], lw=2.0, ls="--",
               label=f"prévalence = {prevalence:.2f}")
    ax.set_xticks(x)
    ax.set_xticklabels([LABEL93[k].replace(" ", "\n") for k in order], fontsize=10)
    ax.set_ylim(0.6, 0.78)
    ax.set_ylabel("AUPRC")
    ax.set_title("HERALD 93 — 280 zones, support navettes\nprévalence 0,70", fontsize=13)
    ax.legend(fontsize=9.5, loc="upper right")

    ax = axes[1]
    x = np.arange(len(supports))
    m1 = [median([r["recovery"]["auprc"]
                  for r in cells[("M1_MULTIRELATIONAL", 1.0, s)]]) for s in supports]
    m0 = [median([r["recovery"]["auprc"] for r in cells[("M0_NULL", 1.0, s)]])
          for s in supports]
    prev = [median([r["recovery"]["prevalence"]
                    for r in cells[("M1_MULTIRELATIONAL", 1.0, s)]]) for s in supports]
    ax.bar(x - 0.19, m1, width=0.36, color=PALETTE["learned_graph"],
           label="AUPRC — M1 (mécanisme)")
    ax.bar(x + 0.19, m0, width=0.36, color=PALETTE["null"],
           label="AUPRC — M0 (sans mécanisme)")
    ax.scatter(x, prev, marker="_", s=1500, color=PALETTE["true_graph"], linewidths=3,
               label="prévalence du support", zorder=6)
    ax.set_xticks(x)
    ax.set_xticklabels(["navettes\nseules", "similarité\nseule", "union\ntypée",
                        "toutes les\npaires"], fontsize=10)
    ax.set_title("HERALD 96 — 80 zones, cible résiduelle\nprévalence variable selon le support",
                 fontsize=13)
    ax.legend(fontsize=9.5)

    fig.suptitle("AUPRC contre prévalence, dans deux protocoles qui ne se comparent pas",
                 y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — mesuré", PALETTE["learned_graph"])
    footnote(fig, "Les deux panneaux ont des ORDONNÉES DIFFÉRENTES et des prévalences "
                  "différentes : à gauche la vérité est tirée à l'intérieur du support, donc "
                  "0,70 des paires candidates sont vraies ; à droite deux tiers des arêtes "
                  "vraies sont hors navettes et la prévalence tombe entre 0,011 et 0,061. "
                  "Comparer 0,73 à 0,02 n'aurait aucun sens. Ce qui se compare est la "
                  "DISTANCE de chaque barre à sa propre prévalence, et cette distance est "
                  "nulle des deux côtés — y compris dans le scénario sans mécanisme, où elle "
                  "devrait l'être.", width=155)
    save(fig, "R03_auprc_versus_prevalence")
    PROVENANCE["R03"] = {"herald93_prevalence": prevalence,
                         "herald96_prevalence": dict(zip(supports, prev)),
                         "rule": "the two panels are never merged into one ranking"}


# ── R04 ──────────────────────────────────────────────────────────────────────

def r04_scale_diagnostic() -> None:
    ladder = group(herald95_tasks(), "scenario", "relational_scale")
    scales = (0.0, 0.5, 1.0, 2.0, 4.0)
    interpretive = (0.0, 0.5, 1.0, 2.0)

    use_style()
    fig, axes = plt.subplots(1, 3, figsize=(18.0, 5.8))

    ax = axes[0]
    for scenario, marker in [("N2_NONLINEAR", "o"), ("N3_REGIME", "s"),
                             ("N4_INTERACTION", "^")]:
        snr = [median([r["observable_diagnostics"]["per_scale"][str(s)]["observable"]
                       [r["primary_signal"]]["snr"] for r in ladder[(scenario, s)]])
               for s in scales]
        ax.plot(scales, snr, marker=marker, lw=2.0, ms=8, color=PALETTE["commuting"],
                label=scenario)
    ax.axvspan(2.0, 4.2, color="#F3F3F3", zorder=0)
    ax.text(3.0, 0.08, "test de\nsaturation", ha="center", fontsize=9.5, color="#888888")
    ax.set_xlabel("intensité relationnelle")
    ax.set_ylabel("rapport signal/bruit observable")
    ax.set_title("Le mécanisme EST visible\ndans les données publiées", fontsize=13)
    ax.legend(fontsize=9.5)

    ax = axes[1]
    for scenario, marker in [("N2_NONLINEAR", "o"), ("N3_REGIME", "s"),
                             ("N4_INTERACTION", "^")]:
        oracle = [median([r["arms"]["oracle_relational"]["gain_over_ridge_linear"]
                          for r in ladder[(scenario, s)]]) for s in interpretive]
        ax.plot(interpretive, oracle, marker=marker, lw=2.0, ms=8, color=PALETTE["oracle"],
                label=f"oracle — {scenario}")
    ax.axhline(0, color="#999999", lw=1.0)
    ax.set_xlabel("intensité relationnelle")
    ax.set_ylabel("part de l'erreur retirée")
    ax.set_title("Le plafond est RÉEL mais BAS\n≈ 2 % à l'intensité nominale", fontsize=13)
    ax.legend(fontsize=9.5)

    ax = axes[2]
    for scenario, marker in [("N0_NULL", "x"), ("N2_NONLINEAR", "o"), ("N3_REGIME", "s"),
                             ("N4_INTERACTION", "^")]:
        auprc = [median([r["edge_recovery"]["auprc"] for r in ladder[(scenario, s)]])
                 for s in scales]
        colour = PALETTE["null"] if scenario == "N0_NULL" else PALETTE["learned_graph"]
        ax.plot(scales, auprc, marker=marker, lw=2.0, ms=8, color=colour, label=scenario)
    prevalence = median([r["edge_recovery"]["prevalence"]
                         for r in ladder[("N4_INTERACTION", 1.0)]])
    ax.axhline(prevalence, color=PALETTE["true_graph"], lw=2.0, ls="--",
               label=f"prévalence = {prevalence:.2f}")
    ax.set_ylim(0.66, 0.78)
    ax.set_xlabel("intensité relationnelle")
    ax.set_ylabel("AUPRC des arêtes")
    ax.set_title("La récupération des arêtes\nne bouge PAS", fontsize=13)
    ax.legend(fontsize=9)

    fig.suptitle("Diagnostic d'échelle : « trop petit pour être vu » ou « modèle incapable » ?",
                 y=1.04)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — HERALD 95", PALETTE["oracle"])
    footnote(fig, "280 zones, trois graines (9901–9903), une seule quantité variée — "
                  "`relational_scale` — avec un appariement cellule par cellule du bruit "
                  "vérifié par une garde dans les 60 tâches. Réponse : le modèle. Le "
                  "mécanisme est visible (panneau 1) et exploitable (panneau 2), et le "
                  "scorer d'arêtes n'y répond pas du tout (panneau 3) — multiplier le "
                  "mécanisme par quatre déplace le graphe appris d'environ 1e−8. La "
                  "qualification qui compte : le plafond lui-même vaut environ 2 % de "
                  "l'erreur quadratique.", width=155)
    save(fig, "R04_scale_diagnostic")
    PROVENANCE["R04"] = {"scales": list(scales), "interpretive_scales": list(interpretive),
                         "stress_scale": 4.0}


# ── R05 ──────────────────────────────────────────────────────────────────────

def r05_cost() -> None:
    table = herald93_summary()["table"]
    order = ["persistence@0", "sparse_var@0", "mtgnn@64", "nri@64", "herald@32", "herald@64",
             "herald@128"]

    use_style()
    fig, axes = plt.subplots(1, 2, figsize=(16.0, 6.2))

    ax = axes[0]
    for key in order:
        entry = table[key]
        params = max(entry["cost"]["parameters"], 1)
        ax.scatter(params, entry["forecast_skill_median"], s=260, color=COLOUR93[key],
                   edgecolors="white", linewidths=1.5, zorder=5)
        ax.annotate(LABEL93[key], (params, entry["forecast_skill_median"]),
                    textcoords="offset points", xytext=(10, 8), fontsize=10)
    ax.set_xscale("log")
    ax.axhline(0, color="#333333", lw=1.4)
    ax.set_xlabel("paramètres (échelle logarithmique ; la persistance en compte 0, portée à 1)")
    ax.set_ylabel("skill contre la persistance")
    ax.set_title("Plus de paramètres n'achète pas de prévision", fontsize=13)

    ax = axes[1]
    x = np.arange(len(order))
    seconds = [table[k]["cost"]["seconds"] for k in order]
    ax.bar(x, seconds, color=[COLOUR93[k] for k in order], width=0.62)
    for index, value in enumerate(seconds):
        ax.text(index, value * 1.06, f"{value:.0f} s", ha="center", fontsize=9.5)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([LABEL93[k].replace(" ", "\n") for k in order], fontsize=9.5)
    ax.set_ylabel("secondes par tâche (échelle logarithmique)")
    ax.set_title("Le bras classique est deux ordres de grandeur\nmoins cher", fontsize=13)

    fig.suptitle("Coût, paramètres et performance", y=1.03)
    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — HERALD 93", PALETTE["herald"])
    footnote(fig, "C'est le résultat de frugalité, et il n'est pas favorable à la "
                  "proposition : Granger graphique par Lasso coûte 5,5 s et 50 400 "
                  "paramètres, prévoit aussi bien que le meilleur bras neuronal, et son "
                  "contrôle S0 est propre. HERALD @128 coûte 1 367 s et 368 660 paramètres "
                  "pour la même récupération, c'est-à-dire aucune.", width=155)
    save(fig, "R05_cost_and_parameters")
    PROVENANCE["R05"] = {"parameters": {LABEL93[k]: table[k]["cost"]["parameters"]
                                        for k in order},
                         "seconds": {LABEL93[k]: table[k]["cost"]["seconds"] for k in order}}


# ── R06 ──────────────────────────────────────────────────────────────────────

def r06_scientific_evolution() -> None:
    steps = [
        ("HERALD 91", "Tournoi des signaux",
         "aucun signal français ne porte\nd'information relationnelle stable",
         PALETTE["null"]),
        ("HERALD 93", "Banc à vérité connue",
         "six méthodes, aucune ne récupère ;\nle contrôle S0 est décisif",
         PALETTE["herald"]),
        ("HERALD 94", "Représentation temporelle",
         "elle retire 11–24 % de l'erreur ;\naucun composite n'ajoute rien",
         PALETTE["complementarity"]),
        ("HERALD 95", "Échelle relationnelle",
         "le mécanisme EST observable ;\nl'échec venait du modèle",
         PALETTE["oracle"]),
        ("HERALD 96", "Granger neuronal résiduel",
         "l'oracle vaut 10 % du résidu ;\nle goulot est l'identification",
         PALETTE["learned_graph"]),
        ("HERALD 97", "Gel de l'étape",
         "acquis, non acquis et travaux futurs\nséparés ; comparaison finale spécifiée",
         PALETTE["commuting"]),
    ]

    use_style()
    fig, ax = plt.subplots(figsize=(17.5, 7.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_axis_off()
    ax.grid(False)
    ax.plot([4, 96], [55, 55], color="#CCCCCC", lw=3, zorder=1)

    positions = np.linspace(9, 91, len(steps))
    for x, (code, title, finding, colour) in zip(positions, steps):
        ax.scatter([x], [55], s=420, color=colour, edgecolors="white", linewidths=2.4,
                   zorder=4)
        ax.text(x, 63, code, ha="center", fontsize=12, fontweight="bold", color=colour)
        ax.text(x, 69, title, ha="center", fontsize=10.5, color="#444444")
        ax.text(x, 47, finding, ha="center", va="top", fontsize=9.8, color="#555555",
                linespacing=1.45)

    ax.text(50, 92, "Chaque étape a été ouverte par ce que la précédente n'avait PAS montré",
            ha="center", fontsize=13, fontweight="bold")
    ax.text(50, 18, "La question s'est déplacée trois fois : « le modèle récupère-t-il ? » → "
                    "« y a-t-il quelque chose à récupérer ? » → « où est le goulot ? »\n"
                    "Aucune de ces réponses n'a exigé de changer un seuil après coup.",
            ha="center", fontsize=11, color="#666666", linespacing=1.6)

    stamp(fig, "SYNTHETIC_KNOWN_TRUTH — trajectoire", PALETTE["commuting"])
    footnote(fig, "Les seuils de chaque étape ont été déclarés avant soumission. Deux "
                  "critères ont été remplacés AVANT interprétation, tous deux parce qu'ils "
                  "étaient insatisfaisables par construction, et tous deux consignés avec "
                  "leur raisonnement (DEC-136, DEC-138). Les graines dont l'erreur hors "
                  "échantillon avait été lue ont été retirées et remplacées par des graines "
                  "jamais générées.", width=170)
    save(fig, "R06_scientific_evolution")
    PROVENANCE["R06"] = {"steps": [code for code, *_ in steps]}


def main() -> None:
    r01_temporal_performance()
    r02_skill_versus_persistence()
    r03_auprc_versus_prevalence()
    r04_scale_diagnostic()
    r05_cost()
    r06_scientific_evolution()
    write_provenance("figures_results.json", {
        "kind": "herald_visual_evidence_provenance",
        "category": "SYNTHETIC_KNOWN_TRUTH",
        "rule": "four experiments, four protocols, never merged into one ranking",
        "figures": PROVENANCE})
    print(f"{len(PROVENANCE)} result figures written")


if __name__ == "__main__":
    main()
