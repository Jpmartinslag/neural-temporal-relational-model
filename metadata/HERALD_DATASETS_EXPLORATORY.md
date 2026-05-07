# HERALD — datasets exploratoires ou secondaires

Date: 2026-05-07

Ces datasets ont été collectés ou envisagés, mais ne structurent pas encore le modèle principal. Ils
doivent rester documentés pour éviter de les perdre, sans encombrer la narration scientifique.

## Candidats utiles mais non principaux

| Source | Fichier actuel | Potentiel | Risque / raison de prudence |
|---|---|---|---|
| BPE équipements | `data/interim/tables/bpe_commune_2024.csv`; `bpe_evolution_commune_2019_2024_geo2025.csv` | services, équipements, attractivité locale | plutôt structurel; risque de faible valeur prédictive annuelle |
| FILOSOFI revenus | `data/interim/tables/filosofi_commune_2020.csv`; `filosofi_commune_2021.csv` | contexte socio-économique | publication lente; signal peu dynamique |
| Population / RP | `rp_population_commune_2021.csv`; `rp_population_commune_2022.csv`; `population_history_annual_ze2020_v0.csv` | normalisation par taille, contexte démographique | peut dominer par effet taille si mal normalisé |
| Emploi lieu résidence / travail | `rp_emploi_*` | structure du marché du travail | recensement lent; pas conjoncturel |
| SITADEL construction | `sitadel_monthly_*`; `sitadel_surface_*` | signal avancé territorial, immobilier/construction | attention au cutoff mensuel; peut être très utile mais pas encore canonique |
| Énergie | `energy_consumption_ze2020_v0.csv` | activité productive indirecte | hétérogénéité de sources et délais |
| ZRR/QPV/ZAN/politiques publiques | `data/interim/policy/*` | lecture politique territoriale, app/recommandation | ne pas utiliser sans ablation; risque d'interprétation causale abusive |
| A17 sectoriel | `zone_sectoral_profile_a17_v0.csv`; `zone_sectoral_profile_history_v0.csv` | granularité sectorielle plus fine que A10 | complexifie la tête sectorielle; à tester après A10 robuste |
| REI / CFE historique | `rei_cfe_ze2020_v0.csv` | benchmark historique | rupture méthodologique avec SIDE; à garder en quarantaine |

## Règle d'intégration

Une source exploratoire ne devient principale que si:

1. sa date de publication est connue;
2. elle peut être alignée en geo2025/ZE2020;
3. elle améliore une métrique ou un indicateur interprétable dans une ablation dédiée;
4. elle ne transforme pas un forecast en nowcast caché;
5. elle apporte une lecture économique claire.

## Priorité future

Ordre recommandé:

1. SITADEL mensuel avec cutoff propre;
2. BPE/FILOSOFI/population comme contexte lent;
3. politiques publiques pour interprétation, pas prédiction principale;
4. A17/A20 seulement quand A10 est stabilisé.

