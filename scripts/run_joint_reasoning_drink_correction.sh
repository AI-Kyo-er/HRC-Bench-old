#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_reasoning_joint_activity.py"
command="${python_command} ${python_file}"

# Shared activity and human background
command+=" --activity drink_storage --profile particular --situation correction --activity-specific-context"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"
command+=" --human-decision-steps 80 --human-auto-buffer --initial-human-holding"

# Robot neural coordination and actual VLA
command+=" --coordinator-port 8782 --robot-skill-bank --coordinator-decision-steps 80"
command+=" --port 8766 --robot-language native_with_activity"

# Fixed development condition
command+=" --init-state-id 3 --seed 64 --steps 2400 --context-step 800"

# Output
command+=" --output-dir ./results/continuous_v2/joint_reasoning_drink_correction_20261008"

echo "$command"
eval "$command"
