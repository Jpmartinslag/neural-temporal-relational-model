#!/bin/bash
#SBATCH --job-name=herald_p10_lagged
#SBATCH --partition=fast
#SBATCH --qos=fast
#SBATCH --array=0-19
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=hpc_results/phase10_synthetic_lagged/logs/task_%a.out
#SBATCH --error=hpc_results/phase10_synthetic_lagged/logs/task_%a.err

# HERALD Phase 10 — Lagged Graph Architecture Benchmark
# Array: 0-19 (4 scenarios × 5 seeds)
# Partition: fast, QOS: fast (meso cluster)
# Conda env: herald-v5
# Working dir: ~/project_recomm_herald_v6_2025_20260430/dataset

set -euo pipefail

echo "=========================================="
echo "HERALD Phase 10 — task ${SLURM_ARRAY_TASK_ID}"
echo "Node: $(hostname)"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=========================================="

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
OUTDIR="${WORKDIR}/hpc_results/phase10_synthetic_lagged"
PYTHON="${HOME}/.conda/envs/herald-v5/bin/python"
N_EPOCHS=500

cd "${WORKDIR}"

# Verify environment
"${PYTHON}" -c "import torch; print(f'torch={torch.__version__}')"
"${PYTHON}" -c "from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged; print('lagged OK')"

# Create output directories
mkdir -p "${OUTDIR}/logs"

# Run task
"${PYTHON}" -m src.modeles.synthetic.run_phase10_benchmark \
    --task-id "${SLURM_ARRAY_TASK_ID}" \
    --output-dir "${OUTDIR}" \
    --n-epochs "${N_EPOCHS}" \
    --verbose

echo "Task ${SLURM_ARRAY_TASK_ID} complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
