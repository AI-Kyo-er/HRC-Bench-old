#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=3
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/openpi-torch-transformers:src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/serve_pi05_libero.py"
command="${python_command} ${python_file}"

# Model
command+=" --checkpoint /data1/sieniwgroup/sieniw/models/lerobot/pi05-libero"

# Runtime
command+=" --port 8766"

echo "$command"
eval "$command"
