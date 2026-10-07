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

for init_state in 4 5; do
    for activity in snack_service drink_storage drawer_access; do
        command="${python_command} ${python_file}"

        # 固定参考，只验证测试初态的原生操作与共同活动可执行性
        command+=" --activity ${activity} --human-source reference --robot-language task_only --initial-human-holding"

        # 预先固定的初始化，不用测试结果调节动态人策略
        command+=" --init-state-id ${init_state} --seed 65 --steps 2400 --context-step -1"

        # 原生操作来自真实VLA；人参考调度与末端清场来源分别记录
        command+=" --port 8766"

        # 保留完整真实Sim视频，不覆盖旧开发轨迹
        command+=" --output-dir ./results/continuous_v2/joint_reference_${activity}_init${init_state}_20261008"

        echo "$command"
        eval "$command"
    done
done
