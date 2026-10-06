#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=src:.

# Python
python_command=".venv-vc-pilot/bin/python"
python_file="scripts/run_openpi_benchmark.py"
command="${python_command} ${python_file}"

# Tasks
command+=" --scenario-dir experiments/continuous_v2/visible_contact_atomic_tasks"
command+=" --visible-surfaces --seeds 24 25 --ticks 450 --partner-mode observing"

# Physics and policy execution
command+=" --backend genesis --important --robot-grasp-model friction_contact"
command+=" --human-manipulation-model articulated_contact_hand"
command+=" --execution-horizon 4 --resolution 640 --render-stride 4"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/continuous_v2/pi05_visible_contact_atomic"

echo "$command"
eval "$command"
