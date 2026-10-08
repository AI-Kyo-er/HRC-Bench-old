#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_reasoning_constrained_joint_activity.py"
command="${python_command} ${python_file}"

# Task and explicitly fixed reference
command+=" --activity drawer_access --human-source reference --workspace-method"
command+=" --init-state-id 2 --seed 113 --steps 800 --initial-human-holding"
command+=" --human-auto-buffer --human-relational-targets --human-complete-observation"
command+=" --robot-language task_only"

# Runtime
command+=" --context-step 800 --human-decision-steps 80 --port 8766"

# Output
command+=" --output-dir results/continuous_v2/drawer_operation_floor_init2_seed113_20261009"

echo "$command"
eval "$command"
