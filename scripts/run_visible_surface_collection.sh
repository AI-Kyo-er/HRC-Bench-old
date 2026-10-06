#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=src:.

# Python
python_command=".venv-vc-pilot/bin/python"
python_file="scripts/collect_contact_demonstrations.py"
command="${python_command} ${python_file}"

# Scene
command+=" --visible-surfaces --objects green blue red"
command+=" --seeds 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131"

# Rendering
command+=" --resolution 480 --render-stride 4"

# Output
command+=" --output-dir /data1/sieniwgroup/sieniw/projects/HRC-Bench/datasets/visible_surface_demonstrations"

echo "$command"
eval "$command"
