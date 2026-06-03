# HERALD Phase 4 — International Generalisation Plan

**Date:** 2026-05-27  
**Statut:** protocole congelé avant lancement  
**Objectif:** Répliquer HERALD sur 3 pays européens (Belgique, Pays-Bas, Portugal) comme répliques indépendantes, protocole figé avant résultats.

---

## Déclaration de protocole

> *"Les pays ont été traités en parallèle pour l'efficacité computationnelle, mais chaque expérience a été évaluée comme une réplique indépendante, avec un protocole congelé avant les résultats."*

**Q7_effectifs_lag1 entre congelé depuis la France.** Aucune sélection d'hyperparamètre sur les données des autres pays. Les autres pays sont des répliques de validation, pas des terrains d'optimisation.

---

## Configs par pays (identiques, congelés)

| Config | Description | Rôle |
|--------|-------------|------|
| `naive_lag1` | prévision naïve = valeur année précédente | baseline triviale |
| `Ridge AR` | Ridge avec lags temporels | baseline externe standard |
| `Q1_zero` | HERALD sans q_tensor | mesure la valeur du signal URSSAF local |
| `Q0_real` | HERALD q_tensor contemporain complet | référence avec signal local |
| `Q7_effectifs_lag1` | candidat France, congelé | réplique principale |

**Seeds:** identiques à la France (0, 1, 7, 13, 17, 42, 77, 99, 123, 2025, ...).  
**Walk-forward:** même fenêtre, même règle d'exclusion.  
**Pas de tuning sur les pays cibles.**

---

## Preflight obligatoire par pays

**Aucune batterie ne se lance sans que les 6 points suivants soient validés.**  
Un seul point échoué = suspendre et documenter avant de continuer.

### Checklist preflight

```
[ ] 1. TARGET — Mesure entreprise ou établissement ?
        France: créations d'établissements (SIDE/SIRENE)
        → Pays cible doit mesurer le même concept.
        Si "entreprise juridique" ≠ "établissement physique": documenter l'écart,
        choisir explicitement, ne pas mélanger.

[ ] 2. TERRITOIRE — Unité comparable aux ZE françaises ?
        France: 306 zones d'emploi (50-500k hab., marché du travail cohérent)
        → Arrondissement BE, COROP NL, município PT: vérifier que l'unité
        reflète un bassin d'emploi, pas une unité administrative arbitraire.
        Si trop fin (commune) ou trop large (région): agréger ou documenter.

[ ] 3. SECTEUR — Mapping vers A10/NACE Rev.2 ?
        France: NAF Rev.2 → A10 (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU)
        → NACE-BEL, SBI 2008, CAE Rev.3 sont tous NACE-compatibles.
        Produire table de correspondance explicite avant toute agrégation.
        Vérifier qu'aucune section NACE n'est silencieusement abandonnée.

[ ] 4. COUVERTURE TEMPORELLE — Crise + post-crise couverts ?
        Minimum requis: 2008-2024 (crise financière + COVID + rebond).
        Si données depuis 2010 seulement: documenter l'absence de 2008.
        Si lacunes internes: interpoler ou exclure les années manquantes
        avec règle explicite, pas ad hoc.

[ ] 5. Q_TENSOR — Effectifs dans le même format ?
        France: effectifs URSSAF par ZE × secteur A10 × trimestre → lag1 annuel
        → Pays cible: vérifier que l'équivalent (ONSS, CBS, GEP QP) donne:
           - granularité territoriale au niveau de l'unité choisie
           - désagrégation sectorielle NACE
           - historique annuel (au moins 2010+)
           - aucun seuil de suppression qui viderait des secteurs entiers
        Si manque: utiliser Q1_zero pour ce pays, documenter.

[ ] 6. ÉTANCHÉITÉ TEMPORELLE — Pas de fuite ?
        Vérifier que toutes les features utilisées pour prédire l'année T
        sont disponibles avant l'année T dans la réalité.
        effectifs_lag1 = effectifs de l'année T-1 → OK si T-1 est publié avant T.
        Vérifier les dates de publication officielles de chaque source.
```

### Formulaire de validation preflight (à remplir par pays)

```markdown
## Preflight — [PAYS] — [DATE]

1. TARGET: [ ] OK — [entreprise / établissement / autre: ___]
   Écart vs France: ___

2. TERRITOIRE: [ ] OK — [unité: ___] [N unités: ___]
   Comparable ZE: [ ] oui [ ] non, agrégé en: ___

3. SECTEUR: [ ] OK — [classification: ___]
   Table mapping produite: [ ] oui, fichier: ___

4. COUVERTURE: [ ] OK — [années: ___ à ___]
   Lacunes: ___

5. Q_TENSOR: [ ] OK [ ] manquant → Q1_zero uniquement
   Source: ___ Granularité: ___ Secteurs: ___

6. ÉTANCHÉITÉ: [ ] OK
   Date publication source principale: ___

DÉCISION: [ ] LANCER  [ ] SUSPENDRE — raison: ___
```

---

## Structure des rapports

### Par pays (obligatoire, indépendant)

```
reports/HERALD_PHASE4_BE_AUDIT.md
reports/HERALD_PHASE4_NL_AUDIT.md
reports/HERALD_PHASE4_PT_AUDIT.md
```

Chaque rapport contient:
- résultat preflight (6 points)
- tableau par config (mean WMAPE, std, 2021, 2025, sector WMAPE)
- comparaisons pairées vs Ridge AR (Wilcoxon, wins, p-value)
- verdict pays isolé — HERALD bat-il Ridge AR dans CE pays?

**Ne pas déclarer victoire sur moyenne globale.**  
Montrer pays par pays. Un pays où HERALD ne bat pas Ridge = résultat à analyser, pas à cacher.

### Agrégé 4 pays (après les 3 rapports individuels)

```
reports/HERALD_PHASE4_AGGREGATE_AUDIT.md
```

Contient:
- tableau récapitulatif France + BE + NL + PT
- cohérence des résultats (Q7 gagne-t-il systématiquement?)
- hétérogénéité entre pays (variance inter-pays)
- analyse des écarts (si Q7 perd dans un pays, pourquoi?)

---

## Sources de données par pays

### Belgique

| Composant | Source | URL | Accès |
|-----------|--------|-----|-------|
| Créations entreprises | Statbel démographie | https://statbel.fgov.be/en/themes/enterprises/demography-enterprises/ | CC BY 4.0 |
| Effectifs (ONSS) | Federal Planning Bureau | https://www.plan.be/en/data/qualitative-employment-data-belgium-1999-2024 | Open data |
| Masse salariale | FPB wage costs | idem | Open data |
| Géométries | Statbel secteurs statistiques | https://statbel.fgov.be/en/open-data/statistical-sectors-2022 | CC BY 4.0 |

Territoire cible: **43 arrondissements** (niveau intermédiaire commune/province, cohérent avec bassin d'emploi).

### Pays-Bas

| Composant | Source | URL | Accès |
|-----------|--------|-----|-------|
| Créations entreprises | CBS 81575NED | https://opendata.cbs.nl/#/CBS/nl/dataset/81575NED/table | API ouverte |
| Effectifs | CBS 81464ned | https://opendata.cbs.nl/#/CBS/nl/dataset/81464ned/table | API ouverte |
| Loonsom | CBS StatLine | https://opendata.cbs.nl/ | API ouverte |
| Géométries | CBS COROP | https://www.cbs.nl/werkgelegenheid | Open data |

Territoire cible: **40 régions COROP** (bassins d'emploi officiels NL, échelle comparable ZE).

### Portugal

| Composant | Source | URL | Accès |
|-----------|--------|-----|-------|
| Créations entreprises | INE + dados.gov | https://dados.gov.pt/en/datasets/numero-de-empresas/ | Open data |
| Effectifs + masse sal. | GEP Quadros de Pessoal | https://www.gep.mtsss.gov.pt/quadros-de-pessoal | Download + possible pedido |
| Géométries | INE CAOP | https://www.ine.pt/ | Open data |

Territoire cible: **308 municípios** (ou 23 zonas de emprego INE si disponíveis — verificar no preflight).  
**Atenção:** Quadros de Pessoal podem exigir pedido formal para anos recentes → verificar antes de comprometer o calendário.

---

## Pipeline technique par pays

### Étape 1 — Ingestion (~4h)

```python
# src/data/ingest_<pays>_panel.py
# Produit: data/processed/<pays>_feature_panel_through_2024_v1.csv
# Schéma obligatoire (identique France):
df.columns = [
    "zone_id",      # arrondissement / COROP / município
    "target_year",  # années couvertes
    "y",            # créations établissements/entreprises (avec note si écart)
    "side_lag_1",   # y(t-1), dérivé
    "growth_1y",    # (y(t-1)-y(t-2))/y(t-2) — CAUSAL (lags seulement)
                    # ⚠️ ANCIEN calcul (y(t)-y(t-1))/y(t-1) = LEAKAGE — invalide en Phase 4E
    "effectifs",    # employés par zone × secteur (ou NaN si Q_TENSOR absent)
    "masse_sal",    # masse salariale (ou NaN si absent)
]
```

### Étape 2 — Graphe d'adjacence (~2h)

```python
# src/data/build_<pays>_graph.py
# Géométries officielles → geopandas.sjoin → matrice d'adjacence
# Format identique: metadata/<pays>_adjacency_v1.csv
```

### Étape 3 — Preflight (~1h)

```bash
python3 hpc/regime/preflight_herald_phase4_<pays>.py
# Vérifie les 6 points, génère le formulaire, bloque si échec
```

### Étape 4 — Smoke test (~30min)

```bash
bash hpc/regime/smoke_test_phase4_<pays>.sh
# 2 seeds, 50 epochs, vérifier pipeline end-to-end
```

### Étape 5 — Batterie complète HPC

```bash
bash hpc/regime/submit_herald_phase4_<pays>.sh
# 5 configs × 20 seeds = 100 runs par pays
# 3 pays en parallèle = 300 runs simultanés
```

### Étape 6 — Agrégation + audit

```bash
python3 hpc/regime/aggregate_herald_regime_results.py \
  --root hpc_results/herald_phase4_<pays>_*/
python3 hpc/regime/audit_herald_phase4_<pays>_results.py \
  --root hpc_results/herald_phase4_<pays>_*/
```

---

## Calendrier

| Jour | Tâche | Livrable |
|------|-------|---------|
| J1 | Ingest BE + build graph BE + preflight BE | `preflight_BE.md` validé |
| J2 | Ingest NL + build graph NL + preflight NL | `preflight_NL.md` validé |
| J3 | Ingest PT + build graph PT + preflight PT | `preflight_PT.md` validé |
| J4 | Smoke tests 3 pays + fix bugs | 3 smoke tests OK |
| J5 | **Lancer 3 batteries en parallèle** | 300 runs en cours |
| J6 | Agrégation + audit BE + NL | `HERALD_PHASE4_BE_AUDIT.md`, `_NL_AUDIT.md` |
| J7 | Audit PT + rapport agrégé 4 pays | `HERALD_PHASE4_PT_AUDIT.md`, `_AGGREGATE_AUDIT.md` |

---

## Critères de succès

- [ ] Preflight 6/6 validé pour chaque pays (ou écart documenté)
- [ ] 3 pipelines d'ingestion opérationnels avec schéma identique France
- [ ] 3 graphes d'adjacence construits
- [ ] 300 runs complétés (5 configs × 20 seeds × 3 pays)
- [ ] 3 rapports pays indépendants rédigés
- [ ] 1 rapport agrégé 4 pays
- [ ] Q7 bat Ridge AR dans au moins 2/3 pays (critère paper)
- [ ] Résultat négatif (si existe) documenté et analysé, pas dissimulé
