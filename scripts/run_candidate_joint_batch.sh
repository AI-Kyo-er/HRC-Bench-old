#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-hf
export TRITON_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-triton
export TORCHINDUCTOR_CACHE_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-torchinductor
export TORCH_EXTENSIONS_DIR=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/human-awq-extensions

# Python
python_command=".venv-human-awq-candidate/bin/python"
python_file="scripts/run_area_feedback_batch.py"
command="${python_command} ${python_file}"

# Method and pre-recorded conditions
command+=" --conditions experiments/candidate_joint_20261009/conditions.csv"
command+=" --human-model models/qwen3-32b-awq-human-candidate"
command+=" --human-carried-observation"

# Report
command+=" --report-script scripts/build_candidate_joint_report.py"

echo "$command"
eval "$command"
