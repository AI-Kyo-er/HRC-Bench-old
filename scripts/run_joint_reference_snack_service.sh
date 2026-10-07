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

# Feasibility reference only
command+=" --activity snack_service --human-source reference --robot-language task_only"

# Initial state and complete simulated time
command+=" --init-state-id 0 --seed 60 --steps 2400 --context-step -1"

# Actual VLA
command+=" --port 8766"

# Output
command+=" --output-dir ./results/continuous_v2/joint_feasibility_snack_service_20261007"

echo "$command"
eval "$command"
