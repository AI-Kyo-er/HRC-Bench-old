#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/run_neural_human_qualification.py"
command="${python_command} ${python_file}"

# Output
command+=" --output-dir ./results/continuous_v2/joint_request_delivery_20261007"

# Scene
command+=" --scene-case food_into_bowl"
command+=" --human-policy-architecture deliberative --autonomous-human-context shared_meal"
command+=" --steps 1200 --human-command-delivery neural_request"

echo "$command"
eval "$command"
