#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export HF_HUB_OFFLINE=1
export PYTHONPATH=src:.
export TOKENIZERS_PARALLELISM=false

# Python
python_command="./.venv-libero-native/bin/python"
python_file="./scripts/train_human_contact_lora.py"
command="${python_command} ${python_file}"

# Model and actual contact samples
command+=" --base-model /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B"
command+=" --dataset /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/human_contact_teacher_20261007"
command+=" --weights-dir /data1/sieniwgroup/sieniw/models/Qwen/Qwen3-14B-HRC-contact-lora-20261007"

# Training
command+=" --steps 160 --gradient-accumulation 4 --max-sequence-length 4096 --seed 31"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/results/human_contact_lora_train_20261007"

echo "$command"
eval "$command"
