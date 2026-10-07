#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_libero_native_reference.py"
command="${python_command} ${python_file}"

# Shared serving with a physically elevated receiver region
command+=" --suite libero_spatial --task-ids 2 --init-state-ids 0 --seed 0 --steps 1200"
command+=" --completion-criterion released_stable --autonomous-human-context shared_serving"
command+=" --human-workspace-layout raised_storage"

# Grounded neural human policy
command+=" --human-mode qwen --human-contact-model articulated_hand --human-policy-architecture grounded"
command+=" --human-persona independent --human-memory-scope episode"
command+=" --human-decision-interval-steps 40 --human-reflection-interval-s 6"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

# Learned robot and runtime cameras
command+=" --port 8766 --execution-horizon 10 --video-layout wide_and_policy"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/grounded_human_activity/shared_serving"

echo "$command"
eval "$command"
