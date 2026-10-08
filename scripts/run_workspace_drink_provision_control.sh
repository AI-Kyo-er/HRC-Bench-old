#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_reasoning_constrained_joint_activity.py"
command="${python_command} ${python_file}"

# Task and reference
command+=" --activity drink_storage --human-source reference --workspace-method"
command+=" --init-state-id 2 --seed 92 --steps 2400 --initial-human-holding"
command+=" --human-auto-buffer --human-relational-targets --human-complete-observation"
command+=" --reference-drink-provision wine_bottle_1_personal --robot-language task_only"

# Runtime
command+=" --context-step 800 --human-decision-steps 80 --port 8766"

# Output
command+=" --output-dir results/continuous_v2/workspace_drink_provision_control_20261008"

echo "$command"
eval "$command"
