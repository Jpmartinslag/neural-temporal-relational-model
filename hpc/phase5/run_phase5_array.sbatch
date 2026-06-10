#!/bin/bash
#SBATCH --job-name=herald_phase5
#SBATCH --output=hpc_results/phase5/logs/%A_%a.out
#SBATCH --error=hpc_results/phase5/logs/%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --constraint="mpi"
# Array index = flat index over (country × hypothesis × seed)
# Set N before submit: sbatch --array=0-<N-1> run_phase5_array.sbatch
#SBATCH --array=0-0

# ---- Environment ----
source ~/.bashrc
cd ~/project_recomm_herald_v6_2025_20260430/dataset

# ---- Config grid (must match run_phase5_job.py CONFIG) ----
COUNTRIES=(NL PT FR)
HYPOTHESES=(H0 H0b H1-linear H2-linear PC-temporal-linear PC-territory-linear H1-neural H2-neural PC-temporal-neural PC-territory-neural)
SEEDS=(42 43 44 0 1)

N_COUNTRIES=${#COUNTRIES[@]}
N_HYPS=${#HYPOTHESES[@]}
N_SEEDS=${#SEEDS[@]}

ARRAY_IDX=${SLURM_ARRAY_TASK_ID}
SEED_IDX=$(( ARRAY_IDX % N_SEEDS ))
HYP_IDX=$(( (ARRAY_IDX / N_SEEDS) % N_HYPS ))
COUNTRY_IDX=$(( ARRAY_IDX / (N_SEEDS * N_HYPS) ))

COUNTRY=${COUNTRIES[$COUNTRY_IDX]}
HYPOTHESIS=${HYPOTHESES[$HYP_IDX]}
SEED=${SEEDS[$SEED_IDX]}

echo "Job $SLURM_JOB_ID array=$ARRAY_IDX: country=$COUNTRY hyp=$HYPOTHESIS seed=$SEED"

python3 hpc/phase5/run_phase5_job.py \
    --country "$COUNTRY" \
    --hypothesis "$HYPOTHESIS" \
    --seed "$SEED" \
    --eval-years 2015 2016 2017 2018 2019 2020 2021 2022 2023 \
    --out-dir hpc_results/phase5/raw
