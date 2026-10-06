#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=3
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.84
export OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/train_contact_lora.py"
command="${python_command} ${python_file}"

# Data
command+=" --datasets /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/visible_surface_demonstrations"

# Training
command+=" --joint-position-expert --steps 3000 --batch-size 2 --seed 24"

# Output
command+=" --weights-dir /data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_visible_contact_expert"
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/contact_training/pi05_visible_contact_expert"

echo "$command"
eval "$command"
