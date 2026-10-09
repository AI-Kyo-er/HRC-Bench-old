#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-hf
export TRITON_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-visual-joint-triton
export TORCHINDUCTOR_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-visual-joint-torchinductor
export TORCH_EXTENSIONS_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/bounded-visual-joint-extensions

# Python
python_command=".venv-human-awq-candidate/bin/python"
python_file="scripts/run_bounded_visual_joint_batch.py"
command="${python_command} ${python_file}"

# Frozen task conditions and the same human method
command+=" --conditions experiments/bounded_visual_joint_20261009/conditions.csv"
command+=" --human-model models/qwen3-32b-awq-human-candidate"

# Independent visual coordinator and actual VLA services
command+=" --coordinator-port 8783 --port 8768"

echo "$command"
eval "$command"
