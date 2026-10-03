#!/usr/bin/env bash
export PYTHONPYCACHEPREFIX=/data1/sieniwgroup/sieniw/projects/HRC-Bench/cache/pycache

# Python
python_command="/usr/bin/python3.11"
python_file=" ./scripts/setup_vc_pilot.py"
command="${python_command} ${python_file}"

echo "$command"
eval "$command"
