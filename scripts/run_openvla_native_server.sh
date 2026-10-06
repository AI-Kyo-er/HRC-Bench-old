#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/openvla-transformers:src:.
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/hf-openvla

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/serve_openvla_native.py"
command="${python_command} ${python_file}"

# Model
command+=" --checkpoint /data1/sieniwgroup/sieniw/models/zixiaoBios/openvla-7b-finetuned-libero-spatial"

# Runtime
command+=" --port 8770"

echo "$command"
eval "$command"
