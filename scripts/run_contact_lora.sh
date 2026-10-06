#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=3
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.65
export OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/train_contact_lora.py"
command="${python_command} ${python_file}"

# Data
command+=" --datasets /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/contact_demonstrations_v1 /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/contact_feedback_demonstrations"

# Training
command+=" --steps 400 --batch-size 2 --seed 20"

# Output
command+=" --weights-dir /data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_droid_contact_lora_v1"
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/contact_training/pi05_lora_v1"

echo "$command"
eval "$command"
