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
command+=" --output-dir ./results/continuous_v2/neural_human_qualification_20261007"

# Scene
command+=" --scene-case bowl_on_stove"
command+=" --steps 1200"

echo "$command"
eval "$command"
