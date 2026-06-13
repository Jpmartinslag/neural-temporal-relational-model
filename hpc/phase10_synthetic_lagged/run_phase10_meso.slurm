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
CONDA_ENV="herald-v5"
N_EPOCHS=500

cd "${WORKDIR}"

# Activate conda
source "${HOME}/miniconda3/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

# Verify environment
python -c "import torch; print(f'torch={torch.__version__}')"
python -c "from src.modeles.synthetic.herald_graph_imputer_lagged import HERALDGraphImputerLagged; print('lagged OK')"

# Create output directories
mkdir -p "${OUTDIR}/logs"

# Run task
python -m src.modeles.synthetic.run_phase10_benchmark \
    --task-id "${SLURM_ARRAY_TASK_ID}" \
    --output-dir "${OUTDIR}" \
    --n-epochs "${N_EPOCHS}" \
    --verbose

echo "Task ${SLURM_ARRAY_TASK_ID} complete: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
