#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
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
command+=" --scene-case food_into_bowl --init-state-ids 4 --seed 4 --steps 1200"
command+=" --completion-criterion released_stable --autonomous-human-context shared_meal"

# Neural human
command+=" --human-mode qwen --human-contact-model articulated_hand --human-policy-architecture interactive"
command+=" --human-persona independent --human-memory-scope episode"
command+=" --human-decision-interval-steps 40"
command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"
command+=" --human-adapter /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B-HRC-interaction-lora-20261007"

# Learned VLA and runtime cameras
command+=" --port 8766 --execution-horizon 10 --video-layout wide_and_policy"
command+=" --vla-language-interface task_only --human-command-delivery neural_request"

# Output
command+=" --output-dir ./results/continuous_v2/interactive_hrc_food_20261007"

echo "$command"
eval "$command"
