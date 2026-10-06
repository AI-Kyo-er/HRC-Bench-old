#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_EGL_DEVICE_ID=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export PYTHONPATH=src:.

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_libero_native_reference.py"
command="${python_command} ${python_file}"

# Tasks
command+=" --suite libero_spatial --task-ids 0 1 2 --init-state-ids 0"
command+=" --seed 30 --steps 280 --execution-horizon 10"

# Runtime
command+=" --port 8766"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/pi05_libero_native_reference"

echo "$command"
eval "$command"
