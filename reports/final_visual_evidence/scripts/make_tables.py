"""The seven tables of the archive, each written as CSV and as Markdown.

Numeric tables are computed from artefacts. Descriptive tables (representations, candidate
relations, state of the art) are declarations, and are marked as such in their notes so that
nobody mistakes a design decision for a measurement.

Run: python reports/final_visual_evidence/scripts/make_tables.py
"""

from __future__ import annotations

import csv
from collections import defaultdict

from herald_evidence import (DATA, herald93_summary, herald94_tasks, herald95_tasks,
                             herald96_tasks, group, median, write_table)

REAL = "REAL_FRANCE"
SYN = "SYNTHETIC_KNOWN_TRUTH"
EXP = "EXPLORATORY"
FUT = "FUTURE_WORK"


# ── T01: sources and periods, measured on the French panel ───────────────────

def table_sources() -> None:
    path = DATA / "processed" / "france_ze2020" / "fr_ze2020_multisource_long_panel_v1.csv"
    wanted = {
        "urssaf_private_headcount_annual_mean": ("Effectifs salariés privés", "Urssaf", "A"),
        "urssaf_private_payroll_annual": ("Masse salariale privée", "Urssaf", "A"),
        "urssaf_employer_establishments": ("Établissements employeurs", "Urssaf", "A"),
        "local_unemployment_rate_annual_mean": ("Taux de chômage localisé", "Insee", "A"),
        "local_unemployment_rate_sa": ("Taux de chômage localisé (CVS)", "Insee", "T"),
        "urssaf_private_headcount_sa": ("Effectifs salariés privés (CVS)", "Urssaf", "T"),
        "establishment_creations": ("Créations d'établissements", "Sirene / SIDE", "A"),
        "flores_establishments": ("Établissements (Flores)", "Flores", "A"),
        "active_establishment_stock": ("Stock d'établissements actifs", "SIDE", "A"),
    }
    stats: dict[str, dict] = {k: {"years": set(), "zones": set(), "cells": set(),
                                  "sectors": set(), "n": 0, "observed": 0} for k in wanted}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            entry = stats.get(row["measure"])
            if entry is None:
                continue
            entry["years"].add(int(row["year"]))
            entry["zones"].add(row["ze2020"])
            entry["cells"].add((row["ze2020"], row["year"], row["quarter"]))
            entry["sectors"].add(row["sector"])
            entry["n"] += 1
            entry["observed"] += int(row["availability_mask"] == "1")

    rows = []
    for measure, (label, source, freq) in wanted.items():
        entry = stats[measure]
        if not entry["years"]:
            continue
        rows.append([label, source, {"A": "annuelle", "T": "trimestrielle"}[freq],
                     f"{min(entry['years'])}–{max(entry['years'])}",
                     len(entry["zones"]), len(entry["cells"]), len(entry["sectors"]),
                     f"{entry['observed'] / entry['n']:.3f}", REAL])
    write_table(
        "T01_sources_and_periods",
        ["signal", "source", "fréquence", "période", "zones", "cellules zone×période",
         "postes sectoriels", "part observée", "catégorie"],
        rows,
        "T01 — French sources, periods and coverage",
        "Measured on `data/processed/france_ze2020/fr_ze2020_multisource_long_panel_v1.csv`. "
        "'Cellules zone×période' counts distinct zone–period cells; sources published by "
        "sector contribute several rows per cell, which the 'postes sectoriels' column "
        "records. The study's own population is the 280 mainland ZE2020 of "
        "`fr_ze2020_clean_panel.csv`. 'Part observée' is the availability mask, not an "
        "imputation: absence is never a zero.")


# ── T02: the temporal representations ────────────────────────────────────────

def table_representations() -> None:
    rows = [
        ["niveau", "log(valeur)", "causal, t seulement", "état courant de la zone", "oui"],
        ["croissance", "log(v_t) − log(v_{t−4})", "causal", "variation sur un an", "oui"],
        ["accélération", "croissance_t − croissance_{t−4}", "causal",
         "la variation change-t-elle de rythme", "oui"],
        ["tendance", "pente OLS sur 12 périodes jusqu'à t", "causal, fenêtre fermée en t",
         "direction de moyen terme", "oui"],
        ["momentum", "moyenne des croissances sur 8 périodes", "causal", "persistance récente",
         "oui"],
        ["volatilité", "écart-type des croissances sur 8 périodes", "causal",
         "régularité de la trajectoire", "oui"],
        ["régime", "quatre indicatrices : expansion, décélération, contraction, reprise",
         "causal, dérivé de croissance et accélération", "état qualitatif", "oui"],
        ["composante nationale", "moyenne transversale de la croissance à t", "causal",
         "ce que toutes les zones subissent ensemble", "oui"],
        ["croissance relative", "croissance − composante nationale", "causal",
         "la part propre à la zone", "oui"],
        ["masque de disponibilité", "1 si publié à la date de décision, sinon 0",
         "par construction", "l'absence est un canal, jamais un zéro", "oui"],
    ]
    write_table(
        "T02_temporal_representations",
        ["représentation", "définition", "causalité", "ce qu'elle décrit", "utilisée"],
        rows,
        "T02 — The temporal representation of a zone's own trajectory",
        "A declaration, not a measurement: this is the feature table specified in "
        "`HERALD_94_COMPOSITE_SIGNAL_SPECIFICATION.md` before any result was seen. "
        "Eleven columns plus the availability channel, for each of five signals — 120 columns. "
        "Every one is computed from data released on or before the decision date.")


# ── T03: the candidate relations ─────────────────────────────────────────────

def table_relations() -> None:
    rows = [
        ["commuting", "flux domicile-travail observés (Insee mobilités professionnelles)",
         "observée", "40 destinations les plus fortes par zone",
         "prior de candidature ; jamais une étiquette, jamais dans une perte", REAL],
        ["similarité économique",
         "cosinus des profils temporels standardisés causalement, k plus proches",
         "construite", "k = 10 par zone, normalisation ajustée sur l'entraînement seul",
         "peut proposer des candidats ; n'entre jamais comme valeur dans le scorer", EXP],
        ["complémentarité", "association non linéaire conditionnée au régime",
         "construite", "définie dans le monde synthétique ; en France, exploratoire",
         "aucune arête apprise n'est appliquée à la France", EXP],
        ["union typée", "commuting ∪ similarité, le type servant au rapport seulement",
         "construite", "3127–3234 paires sur 80 zones synthétiques",
         "le type ne parvient pas au modèle comme variable", SYN],
        ["toutes les paires", "toutes les paires ordonnées distinctes",
         "construite", "6320 paires sur 80 zones synthétiques",
         "contient toutes les arêtes vraies ; sert à localiser le goulot", SYN],
    ]
    write_table(
        "T03_candidate_relations",
        ["famille", "définition", "nature", "portée", "règle d'usage", "catégorie"],
        rows,
        "T03 — Candidate relations, and the rule attached to each",
        "'Observée' means measured by a statistical body. 'Construite' means defined by this "
        "study from observed data. Neither is a discovered relation. No learned edge is "
        "applied to France at this stage.")


# ── T04 and T05: the models compared, on the HERALD 93 protocol ──────────────

_LABELS = {
    "persistence@0": ("Persistance", "classique", "aucun graphe"),
    "sparse_var@0": ("Granger graphique (Lasso)", "classique", "apprend le graphe"),
    "mtgnn@64": ("MTGNN", "grafo-temporel", "apprend le graphe"),
    "nri@64": ("NRI", "inférence relationnelle", "apprend le graphe"),
    "herald@32": ("HERALD @32", "proposition", "apprend le graphe"),
    "herald@64": ("HERALD @64", "proposition", "apprend le graphe"),
    "herald@128": ("HERALD @128", "proposition", "apprend le graphe"),
}


def table_models_and_recovery() -> None:
    summary = herald93_summary()
    table = summary["table"]
    order = ["persistence@0", "sparse_var@0", "herald@128", "herald@32", "herald@64",
             "nri@64", "mtgnn@64"]

    models = []
    recovery = []
    for key in order:
        entry = table[key]
        label, family, graph = _LABELS[key]
        cost = entry["cost"]
        models.append([label, family, graph, entry["capabilities"]["objective"],
                       cost["parameters"], cost["epochs"], f"{cost['seconds']:.1f}",
                       f"{cost['peak_memory_mb']:.0f}",
                       "—" if entry.get("abstention_rate") is None
                       or entry["abstention_rate"] != entry["abstention_rate"]
                       else f"{entry['abstention_rate']:.3f}"])
        f1 = entry["edge_f1_median"]
        recovery.append([
            label,
            f"{entry['forecast_skill_median']:+.4f}",
            "—" if f1 != f1 else f"{f1:.3f}",
            "—" if entry["dense_correlation_median"] != entry["dense_correlation_median"]
            else f"{entry['dense_correlation_median']:+.4f}",
            "—" if entry["auprc_median"] != entry["auprc_median"]
            else f"{entry['auprc_median']:.4f}",
            "—" if entry["s0_auprc_median"] != entry["s0_auprc_median"]
            else f"{entry['s0_auprc_median']:.4f}",
            "—" if entry["prevalence_median"] != entry["prevalence_median"]
            else f"{entry['prevalence_median']:.2f}",
            "non" if not entry["checks"]["no_structure_found_in_s0"] else "oui",
            "non" if not entry["relational_recovery_supported"] else "oui"])

    write_table(
        "T04_models_compared",
        ["méthode", "famille", "graphe", "objectif", "paramètres", "époques", "secondes",
         "mémoire (Mo)", "abstention"],
        models,
        "T04 — The models compared under the HERALD 93 protocol",
        "One protocol only: 280 synthetic zones calibrated on French marginals, log-growth at "
        "horizon 1, twelve rolling origins, five seeds, scenarios S0_NULL and S1_SHARED, the "
        "same commuting support for every method. HERALD 96's Neural Granger arm is NOT in "
        "this table: it ran on 80 zones against a residual target, and the two numbers are "
        "not comparable.")

    write_table(
        "T05_prediction_versus_recovery",
        ["méthode", "skill vs persistance", "edge F1", "corr. dense", "AUPRC S1", "AUPRC S0",
         "prévalence", "S0 propre", "récupération soutenue"],
        recovery,
        "T05 — Prediction and relational recovery are separate questions",
        "The two halves of this table answer different questions and a method may do well at "
        "one and nothing at the other. The decisive column is 'AUPRC S0': a method scoring in "
        "the scenario built with no mechanism has reproduced something it was given. Required "
        "for recovery: edge F1 ≥ prevalence + 0.10, dense correlation ≥ 0.30, stability ≥ "
        "0.90, AUPRC above prevalence in S1 and no structure in S0. No method passes.")


# ── T06: demonstrated / not demonstrated / future work ───────────────────────

def table_status() -> None:
    tasks94 = group(herald94_tasks(), "scenario")
    temporal = {s: median([r["arms"]["ridge_linear"]["gain_over_best_single"] for r in rows])
                for (s,), rows in tasks94.items()}
    lo, hi = min(temporal.values()), max(temporal.values())

    tasks95 = group(herald95_tasks(), "scenario", "relational_scale")
    oracle95 = median([r["arms"]["oracle_relational"]["gain_over_ridge_linear"]
                       for r in tasks95[("N4_INTERACTION", 1.0)]])

    tasks96 = group(herald96_tasks(), "scenario", "relational_scale", "support")
    oracle96 = median([r["oracles"]["all_families"]
                       for r in tasks96[("M1_MULTIRELATIONAL", 1.0, "typed_union")]])

    rows = [
        ["La représentation temporelle causale réduit l'erreur",
         "DÉMONTRÉ", SYN,
         f"gain médian de {lo:.3f} à {hi:.3f} de l'erreur quadratique hors échantillon "
         f"contre le meilleur signal isolé, dans les six scénarios",
         "HERALD 94 §3.1"],
        ["Les six composites déclarés ajoutent de l'information",
         "RÉFUTÉ", SYN,
         "l'effet médian est négatif dans les six scénarios (−0,003 à −0,008)",
         "HERALD 94 §3.2"],
        ["Le gain non linéaire du réseau est relationnel",
         "RÉFUTÉ", SYN,
         "le gain est aussi grand dans le scénario sans mécanisme et survit à la destruction "
         "de sa propre interaction",
         "HERALD 94 §3.3–3.4, HERALD 95 §4"],
        ["Le mécanisme relationnel est observable dans les données publiées",
         "DÉMONTRÉ", SYN,
         f"l'oracle vaut exactement 0 sans mécanisme et croît de façon monotone ; "
         f"+{oracle95:.4f} de l'erreur à l'échelle nominale sur la croissance brute, "
         f"+{oracle96:.4f} du résidu après un baseline local gelé",
         "HERALD 95 §4, HERALD 96 §2"],
        ["Un modèle récupère les arêtes vraies au-dessus du hasard",
         "NON DÉMONTRÉ", SYN,
         "aucune des six méthodes de HERALD 93, ni le bras Neural Granger de HERALD 96, dans "
         "aucun des quatre supports ni aucune des trois intensités",
         "HERALD 93 §7, HERALD 96 §3"],
        ["Le goulot est la génération de candidats",
         "RÉFUTÉ", SYN,
         "le support « toutes les paires » contient toutes les arêtes vraies et ne récupère "
         "rien ; le goulot est l'identification",
         "HERALD 96 §6"],
        ["Une méthode bat la persistance en prévision",
         "NON DÉMONTRÉ", SYN,
         "le meilleur skill est +0,0001 (Granger), c'est-à-dire la persistance à quatre "
         "décimales ; la croissance logarithmique à l'horizon 1 est proche du bruit de mesure",
         "HERALD 93 §6"],
        ["Les arêtes apprises décrivent des relations économiques françaises",
         "NON AUTORISÉ", EXP,
         "aucune arête apprise n'est appliquée, visualisée ou interprétée pour la France ; "
         "décision CASE_C_DO_NOT_APPLY_RELATIONS",
         "HERALD 93 §9, HERALD 96 §7"],
        ["La fusion multirelationnelle par attention améliore l'identification",
         "TRAVAIL FUTUR", FUT,
         "ni implémentée ni validée à cette étape ; aucune donnée ne la soutient ni ne la "
         "réfute",
         "HERALD 97"],
        ["Un objectif d'entraînement qui note les arêtes plutôt que de seulement prévoir",
         "TRAVAIL FUTUR", FUT,
         "proposé par HERALD 96 §8 comme la cible directe du goulot identifié",
         "HERALD 96 §8"],
    ]
    write_table(
        "T06_demonstrated_not_demonstrated_future",
        ["affirmation", "statut", "catégorie", "sur quoi le statut repose", "source"],
        rows,
        "T06 — Demonstrated, not demonstrated, future work",
        "'DÉMONTRÉ' and 'RÉFUTÉ' are claims about synthetic worlds whose truth is known. "
        "None of them is a claim about the French economy. 'NON DÉMONTRÉ' means the "
        "experiment was run and did not support the claim; it does not mean the claim is "
        "false.")


# ── T07: state of the art against what was actually run ──────────────────────

def table_state_of_the_art() -> None:
    rows = [
        ["Baselines temporels", "Persistance ; AR-Ridge",
         "fixer le plancher : ce qu'on obtient sans rien apprendre",
         "OUI", "Persistance (HERALD 93)",
         "sans plancher, tout gain est illisible ; c'est la référence du skill"],
        ["Dépendance temporelle classique", "Granger ; Granger graphique par Lasso ; PCMCI+",
         "tester la précédence temporelle de façon frugale et lisible",
         "OUI (Lasso) ; NON (PCMCI+)", "Granger graphique par Lasso (HERALD 93)",
         "`tigramite` est absent de l'environnement du cluster ; ajouter une dépendance non "
         "auditée pour obtenir une deuxième méthode classique est pire qu'en exécuter une "
         "qui se lit de bout en bout"],
        ["Propagation sur graphe", "GCN ; GraphSAGE",
         "fondements de l'agrégation de voisinage",
         "NON", "— (fondement, pas représentant)",
         "ce sont les briques dont MTGNN et NRI héritent ; les tester seuls répondrait à une "
         "question que le protocole ne pose pas, puisqu'ils supposent le graphe donné et "
         "n'apprennent pas de structure"],
        ["Prévision spatio-temporelle", "STGCN ; DCRNN",
         "prévoir avec un graphe généralement fourni",
         "NON", "— (fondement, pas représentant)",
         "le graphe y est une entrée, pas une sortie ; la question centrale de cette étude "
         "est précisément de savoir si le graphe peut être retrouvé"],
        ["Graphes dynamiques", "EvolveGCN ; TGN",
         "faire évoluer la structure dans le temps",
         "NON", "— (hors protocole actuel)",
         "le graphe vrai du benchmark ne bouge pas à l'intérieur des douze origines de "
         "notation, donc le critère typé n'est pas exercé ; les tester ici mesurerait une "
         "capacité que le banc ne sollicite pas"],
        ["Prévision grafo-temporelle avec apprentissage de structure", "MTGNN",
         "un graphe aide-t-il la prévision, et celui qu'il apprend est-il le vrai",
         "OUI", "MTGNN @64 (HERALD 93)",
         "il apprend son adjacence à partir d'un objectif de prévision seul, ce qui est "
         "exactement la confusion que l'étude doit éviter"],
        ["Inférence relationnelle neuronale", "NRI",
         "une architecture conçue pour retrouver les relations les retrouve-t-elle",
         "OUI", "NRI @64 (HERALD 93)",
         "postérieure statique, stable, et restreinte au même support, pour que la "
         "comparaison porte sur les méthodes et non sur les supports"],
        ["Proposition", "HERALD",
         "temporalité, signaux multiples, prior territorial, abstention, frugalité",
         "OUI", "HERALD @32/@64/@128 (HERALD 93)",
         "la proposition de l'étude ; évaluée sous les mêmes folds, origines, graines, "
         "masques et vraisemblance que les autres bras neuronaux"],
        ["Diagnostic relationnel résiduel", "Neural Granger ; NAVAR",
         "attribuer une contribution par source après un baseline local gelé",
         "OUI", "Bras additif par source (HERALD 96)",
         "diagnostic postérieur, sur un protocole différent : 80 zones, cible résiduelle, "
         "quatre supports ; ses chiffres ne se classent pas avec ceux de HERALD 93"],
    ]
    write_table(
        "T07_state_of_the_art_coherence",
        ["famille", "exemple cité", "fonction scientifique", "testé ?", "représentant choisi",
         "justification"],
        rows,
        "T07 — Why some methods are foundations and others are experimental representatives",
        "Not every method cited in a literature review needs to be run. What needs justifying "
        "is which one stands for its family and why the others do not. A method whose "
        "premise is that the graph is given cannot answer a question about whether the graph "
        "can be recovered.")


def main() -> None:
    table_sources()
    table_representations()
    table_relations()
    table_models_and_recovery()
    table_status()
    table_state_of_the_art()
    print("tables written to reports/final_visual_evidence/tables/")


if __name__ == "__main__":
    main()
