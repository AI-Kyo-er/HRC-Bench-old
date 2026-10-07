#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export MUJOCO_GL=egl
export PYNPUT_BACKEND=dummy
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_joint_activity.py"

for activity in snack_service drink_storage drawer_access; do
    command="${python_command} ${python_file}"

    # 固定人仅用于匹配初态的可执行性参考
    command+=" --activity ${activity} --human-source reference --robot-language task_only --initial-human-holding"

    # 与技能库开发批匹配的初始化与持续时间
    command+=" --init-state-id 2 --seed 63 --steps 2400 --context-step -1"

    # 真实VLA服务
    command+=" --port 8766"

    # 输出，不覆盖原结果
    command+=" --output-dir ./results/continuous_v2/joint_matched_reference_${activity}_init2_20261008"

    echo "$command"
    eval "$command"
done
