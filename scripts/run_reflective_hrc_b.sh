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

for activity in drawer_access shared_serving_openvla
do
    command="${python_command} ${python_file}"

    # Scene and sustained activity
    command+=" --init-state-ids 0 --seed 0 --steps 1200 --completion-criterion released_stable"
    if [ "$activity" = "drawer_access" ]; then
        command+=" --scene-case drawer_access --autonomous-human-context pantry_work"
        command+=" --human-persona cautious --port 8766 --execution-horizon 10"
    else
        command+=" --suite libero_spatial --task-ids 2 --autonomous-human-context shared_serving"
        command+=" --human-workspace-layout raised_storage --human-persona assertive"
        command+=" --port 8770 --execution-horizon 1"
    fi

    # Neural human cognition and physical hand
    command+=" --human-mode qwen --human-contact-model articulated_hand --human-policy-architecture reflective"
    command+=" --human-memory-scope episode --human-decision-interval-steps 40 --human-reflection-interval-s 6"
    command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

    # Simultaneous runtime cameras
    command+=" --video-layout wide_and_policy"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/reflective_hrc/${activity}"

    echo "$command"
    eval "$command"
done
