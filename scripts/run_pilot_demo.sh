#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYOPENGL_PLATFORM=egl
export GS_CACHE_FILE_PATH=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/genesis-vico
export PYTHONPYCACHEPREFIX=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/pycache

# Python
python_command="./.venv-vc-pilot/bin/python"
python_file=" -m hrc_pilot.run"
command="${python_command} ${python_file}"

# Output
command+=" --output-dir ./results/pilot_v1/demo"

# Study
command+=" --scenarios history_keep history_pack information_update partner_available partner_unavailable"
command+=" --policies memory static reactive"
command+=" --seeds 0"

# Runtime
command+=" --backend gpu --resolution 800 --render-stride 3 --max-decisions 12"

echo "$command"
eval "$command"
