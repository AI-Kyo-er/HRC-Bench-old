#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_reasoning_constrained_joint_activity.py"
command="${python_command} ${python_file}"

# Shared activity and human background
command+=" --activity snack_service --situation detour --profile participating"
command+=" --activity-specific-context --initial-human-holding --human-auto-buffer"

# Explicit capability contract; withdrawal remains an unqualified VLA operation
command+=" --human-relational-targets --robot-skill-bank --robot-withdraw-operation"
command+=" --symbolic-coordinator --robot-language native_with_activity"

# Initialization and runtime
command+=" --init-state-id 3 --seed 71 --steps 2400 --context-step 800"
command+=" --human-decision-steps 80 --coordinator-decision-steps 80 --port 8766"

# Output
command+=" --output-dir results/continuous_v2/relational_snack_detour_symbolic_20261008"
echo "$command"
eval "$command"
