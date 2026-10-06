#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=2
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.50
export OPENPI_DATA_HOME=/data1/sieniwgroup/sieniw/models/Physical-Intelligence/openpi-cache
export PYTHONPATH=src:.
export HF_HUB_OFFLINE=1

# Python
python_command=".venv-openpi/bin/python"
python_file="scripts/serve_openpi_droid.py"
command="${python_command} ${python_file}"

# Model
command+=" --checkpoint /data1/sieniwgroup/sieniw/models/HRC-Bench/pi05_visible_contact_expert/3000"
command+=" --contact-position"

# Runtime
command+=" --port 8765"

echo "$command"
eval "$command"
