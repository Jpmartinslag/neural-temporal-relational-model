# Résultats HPC HERALD

Ce dossier est une archive de calcul. Il peut contenir beaucoup de fichiers lourds, logs, CSV de
prédiction et `.npz` internes. Il ne doit pas être la structure principale du projet.

## Runs récents importants

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
