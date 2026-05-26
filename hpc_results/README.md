# Résultats HPC HERALD

Ce dossier est une archive de calcul. Il peut contenir beaucoup de fichiers lourds, logs, CSV de
prédiction et `.npz` internes. Il ne doit pas être la structure principale du projet.

## Runs récents importants

- `herald_regime_phase2r_confirmatory_20260526_2r_confirm_r1_r1/` — Phase 2R confirmatoire,
  260 runs, audit strict passé. Résultat principal exporté vers `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md`
  et `reports/metrics/herald_phase2r_*.csv`.
- `herald_regime_phase2o_residual_shrinkage_20260525_2o_shrink_r1_r1/` — calibration du résidu.
- `herald_regime_phase2p_hc_auditor_interaction_20260525_2p_hc_aud_r1_r1/` — interaction HC/auditeur.
- `herald_regime_phase2q_input_arch_robustness_20260525_2q_input_arch_r1_r1/` — robustesse input/architecture.
- `herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1/` — Phase 2I SIDE5 ablations, 90 runs, audit strict passé.
- `herald_regime_phase2h_macro_real_20260515_1205_macro_real_r3_r1/` — Phase 2H macro réel, 100 runs.
- `herald_regime_phase2h_macro_permute_20260515_1206_macro_permute_r3_r1/` — falsification macro permutée, 40 runs.
- `herald_regime_phase2h_macro_extra_20260515_1218_macro_extra_minimal_r1/` — variantes minimales + macro Banque de France, 40 runs.
- `phase2h_combined_audit/` — audit combiné Phase 2H, CSV vs JSON vérifié, 180/180 runs.
- `herald_strict_exante_20260506_night_final/` — audit strict ex-ante, 120 runs.
- `herald_leak_stress_20260507_target_shuffle/` — target-shuffle leak stress.
- `herald_forecast_20260506_forecast_after_strict/` — forecast 2026/2027.
- `herald_semi_v2_final_20260504/` — dashboard Semi V2 stable.
- `herald_semi_total_253_geo2025/` — ancienne batterie complète geo2025.

## Décision Phase 2I

Le meilleur compromis actuel est `lag1_growth1y`, avec seulement `side_lag_1` et `growth_1y`.
Résultat: WMAPE moyen 2021-2025 = 0.021323, WMAPE 2021 = 0.034885, WMAPE 2025 = 0.013004 et A10
WMAPE = 0.156384. Il bat `side5_full` sur tous les folds 2021-2025 et gagne 9/10 seeds en test pairé.

Voir:

```text
hpc_results/herald_regime_phase2i_side5_20260518_1122_side5_audit_r1_r1/reports/audit_phase2i_side5/PHASE2I_SIDE5_AUDIT.md
reports/HERALD_PHASE2I_SIDE2_FEATURE_AUDIT.md
reports/figures/herald_phase2i_side5_audit_dashboard.html
```

La Phase 2H reste utile comme référence historique:

```text
hpc_results/phase2h_combined_audit/PHASE2H_COMBINED_AUDIT.md
reports/HERALD_PHASE2H_FEATURE_MINIMALITY_AUDIT.md
```

## Décision Phase 2R

Phase 2R remplace les anciennes lectures exploratoires comme point d'entrée principal. Le candidat
de travail est `L5_trainopt`: HERALD no flags, SIDE2, résidu neural calibré sur les années de train.

Lecture courte:

- `L5_trainopt` vs `L5_gate_no_auditor`: WMAPE moyen -0.000375, 17/20 wins, p=0.002818;
- `HC5_trainopt`: meilleure moyenne brute, mais plus coûteux en 2021;
- les variantes avec flags servent de contrôles méthodologiques, pas de modèle final;
- la piste suivante est un module d'état économique pour les mouvements rares, pas une nouvelle
  grille large de variantes internes.

Les fichiers lourds de cette phase restent régénérables et ne doivent pas être versionnés. Les
synthèses versionnées sont dans:

```text
reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md
reports/metrics/herald_phase2r_summary.csv
reports/metrics/herald_phase2r_paired_vs_l5_gate.csv
reports/dashboards/herald_france_dashboard.html
```

## Règle

À conserver dans Git seulement si léger et utile:

- README;
- JSON de métriques agrégées;
- dashboard HTML offline final;
- petits fichiers de synthèse.

À éviter dans Git:

- CSV de prédictions par seed;
- `.npz` internals;
- logs `.out` / `.err`;
- archives brutes de transfert.

Les sorties nécessaires au dashboard final doivent être exportées vers `reports/metrics/` et
`reports/dashboards/`.
