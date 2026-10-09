#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=3
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/openpi-torch-transformers:src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/serve_pi05_libero.py"
command="${python_command} ${python_file}"

# Local model and independent VLA service
command+=" --checkpoint /data1/sieniwgroup/sieniw/models/lerobot/pi05-libero"
command+=" --port 8768"

echo "$command"
eval "$command"
