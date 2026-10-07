#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export PYTHONPATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/schema-decoding/python:src:.

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_coherent_joint_batch.py"
command="${python_command} ${python_file}"

# Predefined strategy system and six life situations
command+=" --system symbolic"

echo "$command"
eval "$command"
