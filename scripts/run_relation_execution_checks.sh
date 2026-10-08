#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=src
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_relation_execution_check.py"
command="${python_command} ${python_file}"

# Task and reference qualification
command+=" --activity snack_service --human-source reference --human-auto-buffer"
command+=" --reference-vla-instruction 'move the gripper up and away from the objects and the open drawer'"

# Runtime
command+=" --steps 1200 --human-decision-steps 40 --context-step 2000 --port 8766"

# Initialization and output
command_init2="${command} --init-state-id 2 --seed 82"
command_init2+=" --output-dir results/continuous_v2/relation_execution_init2_20261008"
echo "$command_init2"
eval "$command_init2"

command_init3="${command} --init-state-id 3 --seed 83"
command_init3+=" --output-dir results/continuous_v2/relation_execution_init3_20261008"
echo "$command_init3"
eval "$command_init3"
