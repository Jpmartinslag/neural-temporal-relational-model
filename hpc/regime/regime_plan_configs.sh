# regime_plan_configs.sh — plan_configs() function only.
#
# Sourced by run_herald_regime_seed.sh (execution) and
# submit_herald_phase2d_stability.sh (preflight listing only).
# Contains NO training code — safe to source without executing training.
#
# Column layout:
#   mode variant source_policy label sector_lambda alpha_smooth_lambda
#   smooth_lambda smooth_regime_source latent_train_mode latent_inference_mode
#   regime_seq_transform single_target_year
#   [collapse_lambda latent_smooth_lambda alpha_balance_lambda
#    zone_dro_boost swa_start_frac window_years
#    latent_max_step_lambda latent_step_threshold]

plan_configs() {
  case "${REGIME_PLAN:-discovery}" in
    discovery)
      echo "manual_flags full with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime full with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "change_point full with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_both with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      ;;
    latent_gate_phase2a)
      echo "manual_flags full with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "manual_flags full no_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime full with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime full no_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "change_point learned_regime_gate with_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      echo "change_point learned_regime_gate no_source_flags base 0.1 0.001 0.01 explicit normal match_train none all"
      ;;
    phase2b_a10_guard)
      echo "manual_flags full no_source_flags ctrl 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags candidate 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags sec02 0.2 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags sec03 0.3 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags sec05 0.5 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags secenh 0.2 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags alpha005 0.2 0.005 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate no_source_flags smooth003 0.2 0.001 0.03 explicit normal match_train none all"
      echo "change_point learned_regime_gate no_source_flags cp_sec02 0.2 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_both no_source_flags both_sec02 0.2 0.001 0.01 explicit normal match_train none all"
      ;;
    phase2c_critical)
      echo "manual_flags full no_source_flags ctrl_manual 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime full no_source_flags ctrl_noregime 0.1 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags cand_baseline 0.2 0.001 0.01 explicit normal match_train none all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags cand_sym_smooth 0.2 0.001 0.01 none normal match_train none all"
      echo "change_point learned_regime_gate_sector_enhanced no_source_flags falsify_regime_permute 0.2 0.001 0.01 none normal match_train permute_random all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags falsify_latent_inf_zero 0.2 0.001 0.01 none normal zero none all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags falsify_latent_frozen 0.2 0.001 0.01 none frozen_first match_train none all"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags fold2021_probe 0.2 0.001 0.01 none normal match_train none 2021"
      ;;
    phase2d_stability)
      # Phase 2D — 12 configs × 10 seeds = 120 runs.
      # Columns 1-12: mode variant source_policy label sector_lambda alpha_smooth
      #               smooth smooth_src latent_train latent_inf regime_transform fold
      # Columns 13-18: collapse_lambda latent_smooth_lambda alpha_balance_lambda
      #                zone_dro_boost swa_start_frac window_years
      #
      # Baselines
      echo "manual_flags full no_source_flags ctrl_manual 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0"
      echo "no_regime full no_source_flags ctrl_noregime 0.1 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags cand_2c 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0"
      # H1 — anti-collapse + latent smooth (two strengths)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D1a_col01 0.2 0.001 0.01 none normal match_train none all 0.01 0.005 0.0 1.0 0.0 0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D1b_col05 0.2 0.001 0.01 none normal match_train none all 0.05 0.01 0.0 1.0 0.0 0"
      # H2 — PELT causal change-point (pen=3 conservative; pen=5 stricter)
      echo "pelt_regime_pen3 learned_regime_gate_sector_enhanced no_source_flags D2a_pelt3 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0"
      echo "pelt_regime_pen5 learned_regime_gate_sector_enhanced no_source_flags D2b_pelt5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0"
      # H4 — alpha balance
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D3_aba 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.005 1.0 0.0 0"
      # H5 — zone DRO Q4/Q5 boost ×1.5 (causal: training-period zone_weight only)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D4_dro15 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.5 0.0 0"
      # H6 — SWA stabiliser (last 20% of epochs)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D5_swa 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.2 0"
      # H7 — rolling window (causal: only years <= train_max)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D6_roll9 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 9"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags D7_roll7 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 7"
      ;;
    phase2e_residual_rebound)
      # Phase 2E — 11 configs × 10 seeds = 110 runs.
      # Focus: ridge-residual breakpoints, causal recovery velocity, and
      # excessive latent-step regularisation.  No manual/source flags except
      # the explicit manual upper-bound control.
      echo "manual_flags full no_source_flags ctrl_manual 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags cand_2c 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6"
      echo "resid_pelt learned_regime_gate_sector_enhanced no_source_flags E1_resid_pelt_real 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6"
      echo "recovery_velocity learned_regime_gate_sector_enhanced no_source_flags E2_velocity_causal 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6"
      echo "recovery_velocity_permute learned_regime_gate_sector_enhanced no_source_flags E2_velocity_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags E4_step_thr05 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.5"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags E4_step_thr06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags E4_step_thr07 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.7"
      echo "resid_pelt learned_regime_gate_sector_enhanced no_source_flags E1_E4_resid_pelt_thr06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6"
      echo "recovery_velocity learned_regime_gate_sector_enhanced no_source_flags E2_E4_velocity_thr06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6"
      echo "resid_pelt_recovery_velocity learned_regime_gate_sector_enhanced no_source_flags E1_E2_E4_combo_light 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6"
      ;;
    phase2g_feature_noise)
      # Phase 2G anti-noise — 8 configs × 10 seeds = 80 runs.
      # Same clean regime architecture; only input blocks change.
      # feature_policy controls annual FLORES/SIDE-stock filtering and
      # URSSAF quarterly zeroing in train_herald_regime_experiment.py.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags current_clean 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 current_clean"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_flores 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_side_stock_a10 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_side_stock_a10"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_flores_no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_urssaf"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_flores_no_side_stock_a10 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_urssaf_no_side_stock_a10 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf_no_side_stock_a10"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_side_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only"
      ;;
    phase2h_macro_real)
      # Phase 2H macro — 10 configs × 10 seeds = 100 runs.
      # Requires PANEL_PATH with:
      #   fr_climat_affaires_t_minus_1
      #   fr_climat_emploi_t_minus_1
      #   fr_bdf_conj_services_climate_t_minus_1
      #   fr_bdf_gstix_comp_t_minus_1
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_simplified 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_side_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_climat_affaires 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_affaires"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_climat_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_emploi"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_climat_affaires_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_affaires_emploi"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_climat_affaires_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only climat_affaires_emploi"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_bdf_conj_services 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 bdf_conj_services"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_bdf_gstix 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 bdf_gstix"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_bdf_conj_gstix 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 bdf_conj_gstix"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags best_insee_bdf_core 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 insee_bdf_core"
      ;;
    phase2h_macro_permute)
      # Phase 2H falsification — 4 configs × 10 seeds = 40 runs.
      # Use PANEL_PATH pointing to a panel where macro columns are temporally
      # permuted by year.  If macro is real signal, these should degrade.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags perm_best_climat_affaires 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_affaires"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags perm_best_climat_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_emploi"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags perm_best_climat_affaires_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 climat_affaires_emploi"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags perm_best_insee_bdf_core 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 insee_bdf_core"
      ;;
    phase2h_macro_extra)
      # Phase 2H extra — 4 configs × 10 seeds = 40 runs.
      # Completes the audit by testing BDF macro signals on the minimal
      # SIDE-only feature policy, not only on the best_simplified policy.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_bdf_conj_services 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only bdf_conj_services"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_bdf_gstix 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only bdf_gstix"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_bdf_conj_gstix 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only bdf_conj_gstix"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_insee_bdf_core 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only insee_bdf_core"
      ;;
    phase2i_side5_audit)
      # Phase 2I SIDE5 audit — 9 configs × seeds.
      # Same architecture and hyperparameters as best_simplified.
      # Only the feature_policy changes to isolate each SIDE5 contribution.
      # No manual flags, no source flags, no macro features.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags side5_full 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_full none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags drop_lag1 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_drop_lag1 none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags drop_lag2 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_drop_lag2 none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags drop_lag3 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_drop_lag3 none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags drop_growth1y 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_drop_growth1y none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags drop_growth2y 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_drop_growth2y none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags lags_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lags_only none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags growth_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_growth_only none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags lag1_growth1y 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none"
      ;;
    phase2j_fair_flag)
      # Phase 2J fair flag comparison — 2 configs × 10 seeds = 20 runs.
      #
      # Hypothesis: HERALD no-flags can match or beat HERALD with manual flags
      # when BOTH use the same clean input set (side_lag_1 + growth_1y only).
      #
      # Both variants use:
      #   feature_policy = side5_lag1_growth1y (drops flores, side_stock,
      #     side_lag_2, side_lag_3, growth_2y from annual features)
      #   no_source_flags (drops has_flores_source, has_side_stock_source,
      #     has_urssaf_source from annual features)
      #   no macro features
      #
      # Variant 1 — HERALD no flags clean (SIDE2 candidate from Phase 2I):
      #   regime_mode = no_regime (no is_covid_year, no is_post_covid_rebound)
      #   v7_variant  = learned_regime_gate_sector_enhanced (latent gate)
      #   label suffix: _nf to distinguish from Phase 2I lag1_growth1y
      #
      # Variant 2 — HERALD flags clean (NEW: same inputs + manual flags):
      #   regime_mode = manual_flags (keeps is_covid_year, is_post_covid_rebound
      #     in annual features and regime vector)
      #   v7_variant  = full (explicit regime, no latent gate)
      #   sector_lambda = 0.1 (consistent with all prior manual_flags controls)
      #
      # The only difference between the two variants is the presence of
      # is_covid_year and is_post_covid_rebound. All other inputs are identical.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags lag1_growth1y_nf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none"
      echo "manual_flags full no_source_flags lag1_growth1y_flags 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none"
      ;;
    phase2k_latent_dim)
      # Phase 2K latent-regime dimension audit — 13 configs × 10 seeds = 130 runs.
      #
      # Columns 1-22: same schema as Phase 2J.
      # Columns 23-25: latent_regime_dim  latent_dim_l1_lambda  latent_dim_auto_mask
      #
      # Block A — fixed latent dim, gate only (5 configs):
      #   variant = learned_regime_gate_sector_enhanced
      #   tests: H1 (dim 3 not necessary?), H2 (dim 4/5 = instability?)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L1_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 1 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L2_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 2 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed"
      # Block B — fixed latent dim, gate + graph (5 configs):
      #   variant = learned_regime_both_sector_enhanced
      #   tests: H3 (latent affects graph connections?), paired vs gate at same dim
      echo "no_regime learned_regime_both_sector_enhanced no_source_flags L1_both 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 1 0.0 fixed"
      echo "no_regime learned_regime_both_sector_enhanced no_source_flags L2_both 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 2 0.0 fixed"
      echo "no_regime learned_regime_both_sector_enhanced no_source_flags L3_both 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed"
      echo "no_regime learned_regime_both_sector_enhanced no_source_flags L4_both 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed"
      echo "no_regime learned_regime_both_sector_enhanced no_source_flags L5_both 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed"
      # Block C — auto-regularized dim=5 with L1 mask (3 configs):
      #   tests: H4 (model can deactivate unused dims?), H5 (AUTO5 → 1-2 active dims?)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_l1_001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.001 auto"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_l1_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.005 auto"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_l1_010 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.010 auto"
      ;;
    phase2l_latent_dim_wide)
      # Phase 2L latent-regime wide audit — 20 configs × 10 seeds = 200 runs.
      #
      # Methodological goal:
      #   Test whether the fixed 3D latent regime is a useful inductive bias or
      #   an arbitrary constraint, while keeping the same clean input policy
      #   used in Phase 2K (side_lag_1 + growth_1y, no source flags, no manual
      #   COVID/rebound flags).
      #
      # Columns 1-22: same schema as Phase 2J.
      # Columns 23-25: latent_regime_dim  latent_dim_l1_lambda  latent_dim_auto_mask
      #
      # Block A — fixed gate-only dimensions (7 configs):
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L1_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 1 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L2_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 2 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L6_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 6 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L8_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 8 0.0 fixed"
      # Block B — stronger auto-mask L1 and hard-concrete L0-style masks.
      # Phase 2K showed weak sigmoid L1 kept all dims active.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_l1_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.005 auto"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_l1_020 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.020 auto"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO6_l1_020 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 6 0.020 auto"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.005 hard_concrete"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC6_l0_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 6 0.005 hard_concrete"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC8_l0_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 8 0.005 hard_concrete"
      # Block C — temporal step cap. Tests temporal coherence without manual flags.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_step06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6 side5_lag1_growth1y none 3 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_step06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6 side5_lag1_growth1y none 4 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_step06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6 side5_lag1_growth1y none 5 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_step06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6 side5_lag1_growth1y none 5 0.005 auto"
      # Block D — A10 guard through stronger sector loss. Tests total/A10 trade-off.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUTO5_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.005 auto"
      ;;
    phase2m_latent_autoreg_strong)
      # Phase 2M latent auto-regulation audit — 11 configs × 10 seeds = 110 runs.
      #
      # Goal:
      #   Test whether Phase 2L failed because the auto-regulation mechanism was
      #   too weak/misplaced. Keep the clean no-flags, SIDE2 input setting.
      #
      # Columns 1-26: Phase 2L schema.
      # Columns 27-29: latent_dim_beta_start latent_dim_beta_end latent_group_lasso_lambda.
      #
      # References rerun in-battery for paired comparisons:
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.005 hard_concrete hard_concrete none none 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed sigmoid none none 0.0"
      # Stronger hard-concrete L0-style penalties:
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_020 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.020 hard_concrete hard_concrete none none 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_100 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.100 hard_concrete hard_concrete none none 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_050_anneal 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete 0.6666667 0.3333333 0.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC8_l0_050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 8 0.050 hard_concrete hard_concrete none none 0.0"
      # Source-level dimension penalties and concrete dropout:
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags GL5_005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.005"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags GL5_020 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.020"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags CD5_kl_001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.001 auto concrete_dropout 0.6666667 0.3333333 0.0"
      ;;
    phase2n_internal_auditor)
      # Phase 2N internal auditor — 11 configs × 10 seeds = 110 runs.
      #
      # Goal:
      #   Test input-conditioned self-regulation. Unlike Phase 2M, this is not a
      #   global latent-dimension mask. The auditor emits a confidence per year
      #   and can down-weight the learned latent regime and/or neutralize alpha.
      #
      # References rerun in-battery:
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate_no_auditor 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      # Auditor acts only on latent vector before gate/graph consumers.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_lat_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 latent_scale 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_lat_b005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 latent_scale 0.005 0.0 2.0"
      # Auditor neutralizes alpha toward 0.5 when confidence drops.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_alpha_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 alpha_neutral 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_alpha_b005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 alpha_neutral 0.005 0.0 2.0"
      # Auditor controls both latent intensity and alpha neutrality.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_both_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_both_b005 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.005 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_both_b001_s010 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.010 2.0"
      ;;
    phase2o_residual_shrinkage)
      # Phase 2O — residual shrinkage/selector audit, 9 configs × seeds.
      #
      # Goal:
      #   Test whether HERALD should always apply its full neural residual.
      #   `fixed` shrinkage is a direct ablation; `train_opt` picks lambda from
      #   training years only inside each fold (causal fallback toward Ridge).
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate_no_auditor 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_shrink050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 fixed 0.5 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_shrink075 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 fixed 0.75 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_alpha_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 alpha_neutral 0.001 0.0 2.0 train_opt 1.0 0.0 1.25"
      ;;
    phase2p_hc_auditor_interaction)
      # Phase 2P — HC5 + auditor interaction, 8 configs × seeds.
      #
      # Goal:
      #   Test whether HC5's mean/2025 advantage combines with the 2N auditor's
      #   2021/A10 advantage. This is an interaction battery, not another L0 grid.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate_no_auditor 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_l0_050 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_alpha_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 alpha_neutral 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_both_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_alpha_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 alpha_neutral 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_both_b001 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 both 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_both_b001_s010 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 both 0.001 0.010 2.0"
      ;;
    phase2q_input_arch_robustness)
      # Phase 2Q — input policy × architecture robustness, 9 configs × seeds.
      #
      # Goal:
      #   Separate "SIDE2 is strong" from "architecture is strong" by crossing
      #   three clean input policies with three no-flag architectures.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags side2_L5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags side2_HC5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags side2_AUDboth 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_L5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_HC5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags minimal_AUDboth 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 minimal_side_only none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_noise_L5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_noise_HC5 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags no_noise_AUDboth 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_flores_no_side_stock_a10 none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0"
      ;;
    phase2r_confirmatory)
      # Phase 2R — confirmatory HERALD battery.
      #
      # Goal:
      #   Freeze the post-2O/2P/2Q candidate set and compare it against fair
      #   controls in one run, instead of continuing exploratory grids.
      #
      # Reads:
      #   - no manual flags candidate family;
      #   - clean manual-flags control on the same SIDE2 input;
      #   - extended manual-flags control with the historical broader inputs;
      #   - Ridge-only fallback inside the same training/evaluation pipeline.
      #
      # Main claim candidate:
      #   L5_trainopt = HERALD no-flags, SIDE2, residual correction calibrated
      #   from training years only.
      echo "no_regime ridge_only no_source_flags ridge_side2 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L3_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_gate_no_auditor 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags HC5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.050 hard_concrete hard_concrete none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_alpha_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 alpha_neutral 0.001 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags AUD_both_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags L4_a10g 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 4 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags side2_AUDboth 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 both 0.001 0.0 2.0 none 1.0 0.0 1.25"
      echo "manual_flags full no_source_flags clean_flags_side2 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "manual_flags full no_source_flags clean_flags_side2_trainopt 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      echo "manual_flags full with_source_flags extended_flags_current 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 current_clean none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 none 1.0 0.0 1.25"
      echo "manual_flags full with_source_flags extended_flags_current_trainopt 0.1 0.001 0.01 explicit normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 current_clean none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25"
      ;;
    phase3_tutor_gate_block_a)
      # Phase 3 Tutor Block A — 5 configs × 10 seeds = 50 runs.
      #
      # Question:
      #   Does a forecast-safe macro state help HERALD no-flags react to rare
      #   economic states, and does local heterogeneous gating beat global action?
      #
      # Tutor state:
      #   climat_affaires_emploi = INSEE business climate + employment climate,
      #   lagged as t_minus_1 in the macro panel.
      #
      # Controls:
      #   T0 = current no-flags L5 calibrated baseline.
      #   T1 = same model, macro as ordinary annual feature.
      #   T2 = macro drives one global alpha gate shared by all ZE.
      #   T5 = macro enters local alpha gate with ZE state.
      #   T6 = T5 with tutor state temporally permuted.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags T0_l5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none"
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags T1_macro_feature 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y climat_affaires_emploi 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none"
      echo "no_regime tutor_global_gate no_source_flags T2_tutor_global_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_affaires_emploi none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags T5_tutor_hetero_gate 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_affaires_emploi none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags T6_tutor_hetero_permute 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_affaires_emploi permute_random"
      ;;
    phase3b_tutor_signal_screen)
      # Phase 3B — tutor signal screen, 11 configs × 10 seeds = 110 runs.
      #
      # Goal:
      #   Keep architecture fixed (heterogeneous tutor gate), isolate which
      #   macro signal helps or harms.  Every real signal has a temporal
      #   permutation falsification.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags T0_l5_trainopt 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B1_affaires 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_affaires none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B1p_affaires_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_affaires permute_random"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B2_emploi 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_emploi none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B2p_emploi_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 climat_emploi permute_random"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B3_bdf_conj 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 bdf_conj_services none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B3p_bdf_conj_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 bdf_conj_services permute_random"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B4_gstix 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 bdf_gstix none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B4p_gstix_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 bdf_gstix permute_random"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B5_core 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 insee_bdf_core none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags B5p_core_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 insee_bdf_core permute_random"
      ;;
    phase3c_labor_tutor)
      # Phase 3C — labor-market tutor gate battery.
      #
      # Hypothesis:
      #   Labor-market signals (URSSAF employer counts, DEFM) contain causal local
      #   information about which ZEs are in recovery vs choc, and can help the
      #   residual gate distinguish choc from rebond without manual flags.
      #
      # Architecture: same as Phase 3A/3B (tutor_heterogeneous_gate, L5_trainopt).
      # Key change: ZE-level per-ZE tutor signal via --labor-tutor-feature-set.
      #
      # Column layout (same as all other plans):
      #   mode variant source_policy label sector_lambda alpha_smooth_lambda
      #   smooth_lambda smooth_regime_source latent_train_mode latent_inference_mode
      #   regime_seq_transform single_target_year
      #   collapse_lambda latent_smooth_lambda alpha_balance_lambda zone_dro_boost
      #   swa_start_frac window_years latent_max_step_lambda latent_step_threshold
      #   feature_policy macro_feature_set latent_regime_dim latent_dim_l1_lambda
      #   latent_dim_auto_mask latent_dim_mask_type latent_dim_beta_start latent_dim_beta_end
      #   latent_group_lasso_lambda auditor_mode auditor_budget_lambda auditor_smooth_lambda
      #   auditor_bias_init residual_shrinkage_mode residual_shrinkage_value
      #   residual_shrinkage_min residual_shrinkage_max
      #   tutor_feature_set tutor_state_transform
      #   labor_tutor_feature_set          ← NEW col 40
      #
      # C0: baseline L5_trainopt (no labor tutor, no global tutor)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags C0_baseline 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none"
      # C1: DEFM cat-A ZE recovery Q4(t-1)/Q2(t-1) — unlocked 2026-05-26
      echo "no_regime tutor_heterogeneous_gate no_source_flags C1_defm_ze_recovery 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_recovery"
      # C2: DEFM permuted — falsification
      echo "no_regime tutor_heterogeneous_gate no_source_flags C2_defm_ze_recovery_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_recovery_perm"
      # C3: URSSAF cotisants delta ZE — available
      echo "no_regime tutor_heterogeneous_gate no_source_flags C3_urssaf_employer_estab_growth 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth"
      # C4: URSSAF cotisants delta permuted — available
      echo "no_regime tutor_heterogeneous_gate no_source_flags C4_urssaf_employer_estab_growth_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_perm"
      # C5/C6: combined local labor tutor and temporal falsification.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C5_combo_defm_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_urssaf_combo"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C6_combo_defm_urssaf_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_urssaf_combo_perm"
      # C7/C8: lag controls.  If lag2 beats lag1, the tutor may be capturing slow inertia, not rebound state.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C7_defm_lag2 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_recovery_lag2"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C8_urssaf_lag2 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_lag2"
      # C9/C10: spatial falsification.  Keeps year signal, destroys ZE-specific assignment.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C9_defm_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_recovery_spatial_perm"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C10_urssaf_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_spatial_perm"
      # C11/C12: DEFM alternative transforms.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C11_defm_signed_recovery 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_recovery_signed"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C12_defm_yoy 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_yoy"
      # C13/C14: split URSSAF contraction vs expansion.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C13_urssaf_negative_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_neg"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C14_urssaf_positive_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_pos"
      # C15/C16/C17: combined signal under regularization and latent-size controls.
      echo "no_regime tutor_heterogeneous_gate no_source_flags C15_combo_step06 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.005 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_urssaf_combo"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C16_combo_a10_guard 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_urssaf_combo"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C17_combo_l3dim 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 3 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none defm_urssaf_combo"
      # Activité partielle remains blocked: no clean pre-2020 ZE-level open data.
      ;;
    phase3c_urssaf_isolation)
      # Isolation battery: all configs use no_urssaf policy (q_tensor zeroed).
      # Purpose: isolate whether urssaf_employer_estab_growth adds value beyond
      # the quarterly URSSAF tensor (effectifs_salaries_cvs + masse_salariale_cvs).
      # Compare C3_no_urssaf vs C0_no_urssaf (value), C4_no_urssaf (temporal falsif),
      # C10_no_urssaf (spatial falsif). 4 configs × 10 seeds = 40 runs.
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags C0_no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C3_no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C4_no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_perm"
      echo "no_regime tutor_heterogeneous_gate no_source_flags C10_no_urssaf 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 no_urssaf none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none urssaf_employer_estab_growth_spatial_perm"
      ;;
    phase3d_qtensor)
      # Phase 3D — quarterly URSSAF tensor ablation battery.
      #
      # Hypothesis:
      #   The q_tensor (effectifs_salaries_cvs + masse_salariale_cvs, quarterly ZE)
      #   is a causal/local source of information. We falsify:
      #   - temporal content (temporal_perm destroys year ordering)
      #   - spatial content  (spatial_perm destroys ZE identity)
      #   - channel split    (effectifs_only vs masse_only)
      #   - temporal recency (lag1 shifts tensor 1 year back)
      #
      # Architecture: same strong config as Phase 3C baseline (L5_trainopt).
      # feature_policy=side5_lag1_growth1y throughout (no FLORES, clean SIDE).
      # No annual labor tutor (labor_tutor_feature_set=none).
      #
      # Column layout (cols 1-40 same as all other plans, col 41 = quarterly_tensor_policy):
      #   ... residual_shrinkage_min residual_shrinkage_max
      #   tutor_feature_set tutor_state_transform labor_tutor_feature_set
      #   quarterly_tensor_policy          ← NEW col 41
      #
      # 7 configs × 10 seeds = 70 runs.
      #
      # Q0: baseline — real q_tensor
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q0_real 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none real"
      # Q1: zero q_tensor — measures total q_tensor contribution
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q1_zero 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none zero"
      # Q2 (temporal_perm) removed: global year permutation is not fold-safe and cannot
      # serve as a causal falsification. A fold-safe version would require permuting only
      # within years <= train_max per fold, which is not implemented in the current
      # build_quarterly_tensor + make_sequences contract.
      # Q3: spatial permutation — shuffles ZE identity, preserves temporal distribution
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q3_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none spatial_perm"
      # Q4: effectifs only — zeros masse_salariale channel
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q4_effectifs_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none effectifs_only"
      # Q5: masse_salariale only — zeros effectifs channel
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q5_masse_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none masse_only"
      # Q6: lag1 — shifts q_tensor 1 year back (t gets t-1 data), tests temporal recency
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q6_lag1 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none lag1"
      ;;
    phase3e_qtensor_arch)
      # Phase 3E — q_tensor architecture selection battery.
      #
      # Hypothesis:
      #   Select the optimal form of the quarterly URSSAF tensor for HERALD:
      #   complete vs zero, effectifs vs masse, contemporaneous vs lagged,
      #   real ZE vs spatial perm, with/without A10 guard.
      #
      # 12 configs × 20 seeds = 240 runs.
      # Architecture: no_regime + learned_regime_gate_sector_enhanced, L5_trainopt.
      # feature_policy=side5_lag1_growth1y throughout. No external tutor signals.
      #
      # Phase 3D findings:
      #   Q6_lag1 best mean WMAPE, Q4_effectifs_only ≈ Q0_real, Q1_zero competitive on 2021.
      #   Hypothesis: effectifs_lag1 may be the best single form.
      #
      # col 41 = quarterly_tensor_policy (new in Phase 3D)
      # Note: temporal_perm (global) is NOT included — not fold-safe.
      #
      # Q0: baseline — real q_tensor (both channels, contemporaneous)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q0_real 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none real"
      # Q1: zero q_tensor — no q_tensor contribution
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q1_zero 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none zero"
      # Q3: spatial perm of full q_tensor — destroys ZE identity
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q3_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none spatial_perm"
      # Q4: effectifs only (contemporaneous)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q4_effectifs_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none effectifs_only"
      # Q5: masse_salariale only (contemporaneous)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q5_masse_only 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none masse_only"
      # Q6: full q_tensor lag1
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q6_lag1 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none lag1"
      # Q7: effectifs lag1 — primary candidate from Phase 3D
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q7_effectifs_lag1 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none effectifs_lag1"
      # Q8: masse_salariale lag1
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q8_masse_lag1 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none masse_lag1"
      # Q9: full q_tensor lag2
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q9_lag2 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none lag2"
      # Q10: effectifs + spatial perm — falsification of Q4/Q7 ZE-local claim
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q10_effectifs_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none effectifs_spatial_perm"
      # Q11: lag1 + spatial perm — falsification of Q6/Q7 ZE-local claim
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q11_lag1_spatial_perm 0.2 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none lag1_spatial_perm"
      # Q12: effectifs_lag1 + A10 guard (sector_lambda=0.3)
      echo "no_regime learned_regime_gate_sector_enhanced no_source_flags Q12_effectifs_lag1_a10guard 0.3 0.001 0.01 none normal match_train none all 0.0 0.0 0.0 1.0 0.0 0 0.0 0.6 side5_lag1_growth1y none 5 0.0 fixed sigmoid none none 0.0 none 0.0 0.0 2.0 train_opt 1.0 0.0 1.25 none none none effectifs_lag1"
      ;;
    *)
      echo "Unknown REGIME_PLAN=${REGIME_PLAN}" >&2
      return 1
      ;;
  esac
}
