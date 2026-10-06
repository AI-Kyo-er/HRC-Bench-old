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

for activity in food_into_bowl shared_serving_pi
do
    command="${python_command} ${python_file}"

    # Scene and sustained activity
    command+=" --init-state-ids 0 --seed 0 --steps 1200 --completion-criterion released_stable"
    if [ "$activity" = "food_into_bowl" ]; then
        command+=" --scene-case food_into_bowl --autonomous-human-context pantry_work"
        command+=" --human-persona independent"
    else
        command+=" --suite libero_spatial --task-ids 2 --autonomous-human-context shared_serving"
        command+=" --human-workspace-layout raised_storage --human-persona assertive"
    fi

    # Neural human cognition and physical hand
    command+=" --human-mode qwen --human-contact-model articulated_hand --human-policy-architecture reflective"
    command+=" --human-memory-scope episode --human-decision-interval-steps 40 --human-reflection-interval-s 6"
    command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

    # Learned robot and simultaneous runtime cameras
    command+=" --port 8766 --execution-horizon 10 --video-layout wide_and_policy"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/reflective_hrc/${activity}"

    echo "$command"
    eval "$command"
done
