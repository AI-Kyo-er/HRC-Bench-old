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

for model_name in pi05 openvla
do
    for task_family in moving_receptacle prepare_receptacle shared_workspace
    do
        command="${python_command} ${python_file}"

        # Tasks
        command+=" --suite libero_spatial --task-ids 2 --init-state-ids 0"
        command+=" --seed 0 --steps 400 --task-family ${task_family} --completion-criterion released_stable"

        # Human
        command+=" --human-mode qwen --human-persona cooperative --human-memory-scope episode"
        command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

        # Runtime
        if [[ "$model_name" == "pi05" ]]
        then
            command+=" --port 8766 --execution-horizon 10"
        else
            command+=" --port 8770 --execution-horizon 1"
        fi

        # Output
        command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/native_model_hrc/${model_name}_${task_family}"

        echo "$command"
        eval "$command"
    done
done
