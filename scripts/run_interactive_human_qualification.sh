#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/run_neural_human_qualification.py"
command="${python_command} ${python_file}"

# Learned neural policy
command+=" --human-policy-architecture interactive --autonomous-human-context shared_meal"
command+=" --adapter-path /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B-HRC-interaction-lora-20261007"
command+=" --human-command-delivery neural_request"

# Unseen initialization
command+=" --scene-case food_into_bowl --init-state-id 4 --seed 4 --steps 1200"

# Output
command+=" --output-dir ./results/continuous_v2/interactive_human_qualification_20261007"

echo "$command"
eval "$command"
