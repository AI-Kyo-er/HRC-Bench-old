#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/generate_human_contact_training.py"
command="${python_command} ${python_file}"

# Scene and entire episode split
command+=" --scene-cases food_into_bowl drawer_access"
command+=" --init-state-ids 0 1 2 3 --orders 0 1"
command+=" --steps 1200"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/human_contact_teacher_20261007"

echo "$command"
eval "$command"
