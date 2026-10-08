#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_area_feedback_batch.py"
command="${python_command} ${python_file}"

# Resume only conditions already fully verified; never overwrite or retry failures.
command+=" --resume-verified"

echo "$command"
eval "$command"
