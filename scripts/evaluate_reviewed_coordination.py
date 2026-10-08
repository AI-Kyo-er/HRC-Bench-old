#!/usr/bin/env python3
"""核对案例审阅的源锚点并测量所标时间段，不修改原始实验记录。"""
import argparse
import json
from pathlib import Path

from hrc_pilot.reviewed_coordination_metrics import reviewed_metrics


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    root=parser.parse_args().input_dir
    result=reviewed_metrics(root)
    (root/'reviewed_coordination_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'status':result['status'],'reviewed_intervals':result['reviewed_intervals']},ensure_ascii=False))
