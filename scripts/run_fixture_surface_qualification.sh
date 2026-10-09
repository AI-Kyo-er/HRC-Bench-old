#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=1
export PYTHONPATH=src:scripts
export LIBERO_CONFIG_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/libero-native
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-libero-native/bin/python"
python_file="scripts/run_fixture_surface_qualification.py"
command="${python_command} ${python_file}"

# Explicit fixed execution qualification
command+=" --activity drink_storage --human-source reference"
command+=" --workspace-method --human-area-placement --human-auto-buffer"
command+=" --initial-human-holding --init-state-id 2 --seed 115"

# Complete simulation and preserved evidence
command+=" --steps 800 --human-decision-steps 80 --context-step -1"
command+=" --port 8767"
command+=" --output-dir results/continuous_v2/fixture_surface_qualification_20261009"

echo "$command"
eval "$command"
