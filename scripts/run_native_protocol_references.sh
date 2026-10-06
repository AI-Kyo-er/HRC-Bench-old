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

for model_name in pi05 openvla
do
    command="${python_command} ${python_file}"

    # Tasks
    command+=" --suite libero_spatial --task-ids 0 2 --init-state-ids 0 1"
    command+=" --seed 0 --steps 400 --human-mode none --completion-criterion released_stable"

    # Runtime
    if [[ "$model_name" == "pi05" ]]
    then
        command+=" --port 8766 --execution-horizon 10"
    else
        command+=" --port 8770 --execution-horizon 1"
    fi

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/native_protocol_references/${model_name}"

    echo "$command"
    eval "$command"
done
