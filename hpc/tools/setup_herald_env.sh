#!/bin/bash
set -euo pipefail

# Run on hpclogin01 once before submitting HERALD jobs:
#   bash hpc/setup_herald_env.sh

module purge
module load gcc/8.1.0
module load cuda/12.0.1
module load conda/23.3.1

ENV_NAME="herald-v5"

eval "$(conda shell.bash hook)"

if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  conda create -y -n "${ENV_NAME}" -c conda-forge python=3.10 numpy pandas scikit-learn
fi

conda activate "${ENV_NAME}"
python -m pip install --upgrade pip wheel setuptools
python -m pip install torch

python - <<'PY'
import numpy
import pandas
import sklearn
import torch

print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("sklearn", sklearn.__version__)
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
PY

ENV_DIR="$(python - <<'PY'
import os
print(os.environ["CONDA_PREFIX"])
PY
)"

cat > "${ENV_DIR}/env.sh" <<'EOF'
module purge
module load gcc/8.1.0
module load cuda/12.0.1
module load conda/23.3.1
eval "$(conda shell.bash hook)"
conda activate herald-v5
EOF

mkdir -p "${HOME}/venvs"
cp "${ENV_DIR}/env.sh" "${HOME}/venvs/herald-v5-env.sh"

echo "Environment ready: ${ENV_NAME} (${ENV_DIR})"
echo "Env loader: ${HOME}/venvs/herald-v5-env.sh"
