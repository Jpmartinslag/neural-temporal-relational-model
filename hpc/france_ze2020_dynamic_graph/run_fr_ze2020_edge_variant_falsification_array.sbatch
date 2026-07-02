#!/bin/bash
#SBATCH --job-name=fr_ze2020_edge
#SBATCH --partition=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=03:00:00
#SBATCH --array=0-79
#SBATCH --output=hpc_results/fr_ze2020_dynamic_edge_variants_default/logs/task_%a.out
#SBATCH --error=hpc_results/fr_ze2020_dynamic_edge_variants_default/logs/task_%a.err

set -euo pipefail

SEEDS=(42 43 44 45 46)
VARIANT_NAMES=(
  expanding_memory
  pruned_stable
  stateful
  stateful_sector_only
  stateful_topk
  stateful_sector_topk
  feature_compatible
  feature_compatible_topk
  learned_stateful
  learned_stateful_topk
  learned_sector_only
  learned_sector_topk
  precision_stateful
  precision_stateful_topk
  precision_sector_only
  precision_sector_topk
)
VARIANT_PATHS=(
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_expanding.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_pruned_stable.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_only.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_stateful_sector_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_feature_compatible.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_feature_compatible_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_stateful.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_stateful_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_sector_only.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_learned_sector_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_precision_stateful.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_precision_stateful_topk.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_precision_sector_only.csv.gz
  data/processed/france_ze2020/fr_ze2020_dynamic_graph_edges_precision_sector_topk.csv.gz
)

VARIANT_INDEX=$((SLURM_ARRAY_TASK_ID / ${#SEEDS[@]}))
SEED_INDEX=$((SLURM_ARRAY_TASK_ID % ${#SEEDS[@]}))

export SEED="${SEEDS[${SEED_INDEX}]}"
export EDGE_VARIANT_NAME="${VARIANT_NAMES[${VARIANT_INDEX}]}"
export EDGE_VARIANT_PATH="${VARIANT_PATHS[${VARIANT_INDEX}]}"

bash hpc/france_ze2020_dynamic_graph/run_fr_ze2020_edge_variant_falsification_task.sh
