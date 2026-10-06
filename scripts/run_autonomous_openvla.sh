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

for autonomous_context in snack_host workspace_owner
do
    # Tasks
    command="${python_command} ${python_file}"
    command+=" --suite libero_spatial --task-ids 2 --init-state-ids 0"
    command+=" --seed 0 --steps 900 --completion-criterion released_stable"

    # Human
    command+=" --human-mode qwen --human-persona independent --human-memory-scope episode"
    command+=" --human-decision-interval-steps 40 --autonomous-human-context ${autonomous_context}"
    command+=" --human-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"

    # Robot
    command+=" --port 8770 --execution-horizon 1"

    # Output
    command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/autonomous_human/openvla/${autonomous_context}"

    echo "$command"
    eval "$command"
done
