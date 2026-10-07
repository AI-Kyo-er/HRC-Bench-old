#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/generate_interaction_contact_training.py"
command="${python_command} ${python_file}"

# Additional object combination with physical recovery
command+=" --robot-mode parked --scene-cases drawer_access"
command+=" --target-pair wine_bottle_1 plate_1"
command+=" --init-state-ids 0 3 --orders 0 1 --steps 1600"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/interaction_contact_20261007/plate"

echo "$command"
eval "$command"
