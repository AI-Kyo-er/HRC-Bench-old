#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=3
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_contribution_joint_activity.py"
command="${python_command} ${python_file}"

# Shared activity and human background
command+=" --activity drink_storage --profile particular --symbolic-coordinator --situation detour --activity-specific-context --robot-skill-bank --human-decision-steps 80 --coordinator-decision-steps 80 --human-reflection --human-auto-buffer --initial-human-holding --robot-language native_with_activity"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

# Development initialization and external context
command+=" --init-state-id 3 --seed 64 --steps 2400 --context-step 800"

# Actual VLA service
command+=" --port 8766"

# Output
command+=" --output-dir ./results/continuous_v2/joint_contribution_drink_detour_20261008"

echo "$command"
eval "$command"
