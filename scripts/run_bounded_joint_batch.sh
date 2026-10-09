#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-hf
export TRITON_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-joint-triton
export TORCHINDUCTOR_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-joint-torchinductor
export TORCH_EXTENSIONS_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-joint-extensions

# Python
python_command=".venv-human-awq-candidate/bin/python"
python_file="scripts/run_bounded_joint_batch.py"
command="${python_command} ${python_file}"

# Frozen development conditions and method
command+=" --conditions experiments/bounded_joint_20261009/conditions.csv"
command+=" --human-model models/qwen3-32b-awq-human-candidate"

# Independent actual VLA service
command+=" --port 8767"

echo "$command"
eval "$command"
