#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-hf
export TRITON_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-triton
export TORCHINDUCTOR_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-torchinductor
export TORCH_EXTENSIONS_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-extensions

# Python
python_command=".venv-human-awq-candidate/bin/python"
python_file="scripts/qualify_human_model_interface.py"
command="${python_command} ${python_file}"

# Model and pre-recorded conditions
command+=" --model models/qwen3-32b-awq-human-candidate"
command+=" --conditions experiments/human_candidate_interface_20261009/conditions.csv"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/human_candidate_interface_20261009"

echo "$command"
eval "$command"
