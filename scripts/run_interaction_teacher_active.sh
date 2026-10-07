#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/generate_interaction_contact_training.py"
command="${python_command} ${python_file}"

# Actual moving robot and human data teacher
command+=" --robot-mode pi05 --port 8766"
command+=" --scene-cases food_into_bowl bowl_on_stove"
command+=" --init-state-ids 0 3 --orders 0 1 --steps 1600"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/interaction_contact_20261007/moving"

echo "$command"
eval "$command"
