#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_joint_activity.py"
command="${python_command} ${python_file}"

# Shared activity and human background
command+=" --activity snack_service --profile busy"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

# Development initialization and external context
command+=" --init-state-id 0 --seed 50 --steps 1600 --context-step 800"

# Actual VLA service
command+=" --port 8766"

# Output
command+=" --output-dir ./results/continuous_v2/joint_activity_snack_service_dev_20261007"

echo "$command"
eval "$command"
