#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_libero_native_reference.py"
command="${python_command} ${python_file}"

# Task
command+=" --suite libero_spatial --task-ids 2 --init-state-ids 0 --seed 0 --steps 800"
command+=" --completion-criterion released_stable --human-workspace-layout raised_storage"

# Human
command+=" --human-mode qwen --human-contact-model articulated_hand"
command+=" --autonomous-human-context snack_storage --human-persona independent"
command+=" --human-memory-scope episode --human-decision-interval-steps 40"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

# Robot
command+=" --port 8766 --execution-horizon 10"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/articulated_hrc/snack_storage"

echo "$command"
eval "$command"
