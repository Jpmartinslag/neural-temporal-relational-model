#!/bin/bash
set -euo pipefail

# Run locally from the repository root:
#   bash hpc/rsync_minimal_to_hpc.sh

DEST="${1:-meso-direct:~/project_recomm_dataset}"

rsync -avP \
  --include='/.gitignore' \
  --include='/requirements.txt' \
  --include='/run_herald_v5.sh' \
  --include='/run_herald_v6.sh' \
  --include='/hpc/***' \
  --include='/src/***' \
  --include='/metadata/***' \
  --include='/data/' \
  --include='/data/processed/' \
  --include='/data/processed/dynamic_stgnn_feature_panel_v1.csv' \
  --include='/data/processed/graph_adjacency_core_v0.csv' \
  --include='/data/processed/graph_adjacency_mobility_v0.csv' \
  --include='/data/processed/graph_node_index_core_v0.csv' \
  --include='/data/processed/side_creations_a10_ze2020_v1.csv' \
  --include='/data/raw/' \
  --include='/data/raw/employment/' \
  --include='/data/raw/employment/urssaf/' \
  --include='/data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv' \
  --exclude='*' \
  ./ "${DEST}/"
