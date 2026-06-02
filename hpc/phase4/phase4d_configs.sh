#!/bin/bash
# Phase 4D config registry — functional graphs (commuting + sector similarity).
#
# 4-field output per config (tab-separated):
#   label  feature_policy  qtensor_policy  graph_file
#
# graph_file: path relative to dataset root (data/processed/phase4d/{country}/...)
#   Special value "geo_default" → use country default adj_geo.csv (Phase 4C real contiguity)
#
# feature_policy:
#   side5_lag1_growth1y   → lag_1 + growth_1y  (winning France / Phase 4A baseline)
#   current_clean         → full side features  (Phase 4A best for NL)
#
# qtensor_policy:
#   zero          → tensor disabled
#   effectifs_lag1 → employment/births tensor lag-1 (Q7 equiv for NL/BE; births proxy for PT)
#
# Permutation controls use seed=42 (documented in build_phase4d_commuting_graph.py)
#
# Usage:
#   COUNTRY=nl source hpc/phase4/phase4d_configs.sh && phase4d_configs
#   COUNTRY=be source hpc/phase4/phase4d_configs.sh && phase4d_configs
#   COUNTRY=pt source hpc/phase4/phase4d_configs.sh && phase4d_configs

phase4d_configs() {
  local country="${COUNTRY:?COUNTRY env var required (nl|be|pt)}"
  local d4="data/processed/phase4d/${country}"

  case "$country" in
    nl)
      # ── Controls ────────────────────────────────────────────────────────────
      # Replicate Phase 4A best: no_qtensor_control (current_clean + zero + identity)
      echo "best_4a                  current_clean        zero            ${d4}/adj_identity.csv"
      # Replicate Phase 4C best: baseline_side2 (side5_lag1_growth1y + zero + real geo)
      echo "geo_4c                   side5_lag1_growth1y  zero            geo_default"
      # ── Commuting graph ─────────────────────────────────────────────────────
      echo "commuting_dense_no_tensor side5_lag1_growth1y zero            ${d4}/adj_commuting.csv"
      echo "commuting_top5_no_tensor  side5_lag1_growth1y zero            ${d4}/adj_commuting_top5.csv"
      echo "commuting_top8_no_tensor  side5_lag1_growth1y zero            ${d4}/adj_commuting_top8.csv"
      echo "commuting_top5_tensor     side5_lag1_growth1y effectifs_lag1  ${d4}/adj_commuting_top5.csv"
      # ── Sector similarity graph ──────────────────────────────────────────────
      echo "sector_top5_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top5.csv"
      echo "sector_top8_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top8.csv"
      echo "sector_top5_tensor       side5_lag1_growth1y  effectifs_lag1  ${d4}/adj_sector_similarity_top5.csv"
      # ── Permutation control (null model) ────────────────────────────────────
      echo "graph_perm_control       side5_lag1_growth1y  zero            ${d4}/adj_commuting_top5_perm.csv"
      ;;
    be)
      # ── Controls ────────────────────────────────────────────────────────────
      # Replicate Phase 4A best: baseline_side2 (side5_lag1_growth1y + zero + identity)
      echo "best_4a                  side5_lag1_growth1y  zero            ${d4}/adj_identity.csv"
      # Replicate Phase 4C best: baseline_side2 (side5_lag1_growth1y + zero + real geo)
      echo "geo_4c                   side5_lag1_growth1y  zero            geo_default"
      # ── Commuting graph ─────────────────────────────────────────────────────
      echo "commuting_dense_no_tensor side5_lag1_growth1y zero            ${d4}/adj_commuting.csv"
      echo "commuting_top5_no_tensor  side5_lag1_growth1y zero            ${d4}/adj_commuting_top5.csv"
      echo "commuting_top8_no_tensor  side5_lag1_growth1y zero            ${d4}/adj_commuting_top8.csv"
      echo "commuting_top5_tensor     side5_lag1_growth1y effectifs_lag1  ${d4}/adj_commuting_top5.csv"
      # ── Sector similarity graph ──────────────────────────────────────────────
      echo "sector_top5_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top5.csv"
      echo "sector_top8_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top8.csv"
      echo "sector_top5_tensor       side5_lag1_growth1y  effectifs_lag1  ${d4}/adj_sector_similarity_top5.csv"
      # ── Permutation control (null model) ────────────────────────────────────
      echo "graph_perm_control       side5_lag1_growth1y  zero            ${d4}/adj_commuting_top5_perm.csv"
      ;;
    pt)
      # ── Controls ────────────────────────────────────────────────────────────
      # Replicate Phase 4A best: sector_births_lag1 (side5_lag1_growth1y + effectifs_lag1 + identity)
      # NOTE: effectifs_lag1 uses births proxy for PT — NOT Q7 effectifs
      echo "best_4a                  side5_lag1_growth1y  effectifs_lag1  ${d4}/adj_identity.csv"
      # Replicate Phase 4C best: same config + real geographic contiguity
      echo "geo_4c                   side5_lag1_growth1y  effectifs_lag1  geo_default"
      # ── Sector similarity graph (no commuting for PT — blocked) ─────────────
      echo "sector_top5_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top5.csv"
      echo "sector_top8_no_tensor    side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top8.csv"
      echo "sector_top5_births       side5_lag1_growth1y  effectifs_lag1  ${d4}/adj_sector_similarity_top5.csv"
      echo "sector_top8_births       side5_lag1_growth1y  effectifs_lag1  ${d4}/adj_sector_similarity_top8.csv"
      # ── Permutation control ──────────────────────────────────────────────────
      echo "graph_perm_control       side5_lag1_growth1y  zero            ${d4}/adj_sector_similarity_top5_perm.csv"
      ;;
    *)
      echo "ERROR: unknown country: $country (expected nl|be|pt)" >&2
      return 1
      ;;
  esac
}

phase4d_n_configs() {
  local country="${COUNTRY:?}"
  case "$country" in
    nl|be) echo 10 ;;
    pt)    echo 7  ;;
    *)     echo 0  ;;
  esac
}
