#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_libero_native_reference.py"
command="${python_command} ${python_file}"

# Scene
command+=" --scene-case bowl_on_stove --init-state-ids 0 --seed 0 --steps 1200"
command+=" --completion-criterion released_stable --autonomous-human-context pantry_work"

# Neural human
command+=" --human-mode qwen --human-contact-model articulated_hand --human-policy-architecture grounded"
command+=" --human-persona independent --human-memory-scope episode"
command+=" --human-decision-interval-steps 40 --human-reflection-interval-s 6"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

# Neural robot and runtime cameras
command+=" --robot-planner-port 8780 --planner-interval-steps 40"
command+=" --port 8766 --execution-horizon 10 --video-layout wide_and_policy"

# Output
command+=" --output-dir ./results/continuous_v2/spatial_coordination_20261007/bowl_on_stove"

echo "$command"
eval "$command"
