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

for scene_case in bottle_on_rack bowl_on_stove drawer_access
do
    command="${python_command} ${python_file}"

    # Task
    command+=" --scene-case ${scene_case} --init-state-ids 0 --seed 0 --steps 500"
    command+=" --completion-criterion released_stable"

    # Human
    command+=" --human-mode none"

    # Robot
    command+=" --port 8766 --execution-horizon 10"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/scene_catalog_reference/${scene_case}"

    echo "$command"
    eval "$command"
done
