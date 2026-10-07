#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1
export HF_HOME=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/hf-coordinator

# Python
python_command=".venv-qwen3-v14/bin/python"
python_file="scripts/serve_robot_coordinator.py"
command="${python_command} ${python_file}"

# Model
command+=" --model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-VL-8B-Instruct"

# Runtime
command+=" --port 8782 --skill-bank"

echo "$command"
eval "$command"
