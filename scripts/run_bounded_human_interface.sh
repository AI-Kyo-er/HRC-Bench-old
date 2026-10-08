#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src:scripts
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/hf-human-awq-candidate

# Python
python_command=".venv-human-awq-candidate/bin/python"
python_file="scripts/run_bounded_human_interface.py"
command="${python_command} ${python_file}"

# Saved actual input and frozen model
command+=" --input-dir results/continuous_v2/candidate_drink_correction_symbolic_20261009"
command+=" --time-s 36 --seed 14136"
command+=" --model models/qwen3-32b-awq-human-candidate"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/bounded_human_interface_20261009"

echo "$command"
eval "$command"
