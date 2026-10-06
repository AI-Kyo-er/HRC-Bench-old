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

for activity_profile in receiver_changes priority_changes interruption_return
do
    # Tasks
    command="${python_command} ${python_file}"
    command+=" --suite libero_spatial --task-ids 2 --init-state-ids 0"
    command+=" --seed 0 --steps 900 --activity-profile ${activity_profile}"
    command+=" --task-family moving_receptacle --completion-criterion released_stable"

    # Human
    command+=" --human-mode qwen --human-persona cooperative --human-memory-scope episode"
    command+=" --human-decision-interval-steps 40"
    command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

    # Robot
    command+=" --port 8766 --execution-horizon 10"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/native_dynamic_activity/${activity_profile}"

    echo "$command"
    eval "$command"
done
