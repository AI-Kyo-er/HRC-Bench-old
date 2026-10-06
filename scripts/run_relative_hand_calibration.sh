#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_native_hand_validation.py"

for object_id in cream_cheese_1 plate_1 wine_bottle_1 akita_black_bowl_1
do
    command="${python_command} ${python_file}"

    # Scene and executor calibration; these are teacher commands, not benchmark policies.
    command+=" --scene-case food_into_bowl --object-id ${object_id} --steps 500"
    destination="${object_id}_personal"
    if [ "$object_id" = "cream_cheese_1" ]; then
        destination="on:akita_black_bowl_1"
    fi
    command+=" --destination ${destination}"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/relative_hand_calibration/${object_id}"

    echo "$command"
    eval "$command"
done
