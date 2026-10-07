#!/usr/bin/env python3
"""按预定条件运行跨活动开发批，并在每条终态后独立核查。"""
import argparse
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from hrc_pilot.video_verification import verify_episode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system',choices=['visual','symbolic'],required=True)
    args=parser.parse_args()
    table=Path('experiments/coherent_joint_20261008/conditions.csv')
    rows=[r for r in csv.DictReader(table.open()) if r['system']==args.system]
    table_hash=sha256(table.read_bytes()).hexdigest()
    for row in rows:
        if sha256(table.read_bytes()).hexdigest()!=table_hash:raise RuntimeError('运行期间条件表变化')
        root=Path('results/continuous_v2')/row['run']
        if root.exists():raise RuntimeError('结果已存在，不能覆盖或因观察过期重启：'+str(root))
        command=[sys.executable,'scripts/run_reasoning_constrained_joint_activity.py',
            '--activity',row['activity'],'--situation',row['situation'],'--profile',row['profile'],
            '--init-state-id',row['init_state_id'],'--seed',row['seed'],'--steps',row['steps'],
            '--human-decision-steps','80','--coordinator-decision-steps','80','--context-step','800',
            '--activity-specific-context','--human-auto-buffer','--robot-skill-bank',
            '--robot-language','native_with_activity','--port','8766','--output-dir',str(root)]
        command+=(['--coordinator-port','8782'] if args.system=='visual' else ['--symbolic-coordinator'])
        if row['initial_human_holding']=='1':command+=['--initial-human-holding']
        log=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results')/(row['run']+'.log')
        with log.open('x') as stream:
            process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=os.environ.copy())
        if process.returncode:raise RuntimeError(f'{row["run"]} exit {process.returncode}; 保留失败和日志，停止批次')
        for script in ['audit_joint_activity.py','evaluate_joint_process.py']:
            subprocess.run([sys.executable,'scripts/'+script,'--input-dir',str(root)],check=True)
        video=verify_episode(root/'episode',root,require_timeline=True)
        (root/'independent_video_verification.json').write_text(json.dumps(video,ensure_ascii=False,indent=2))
        if video['status']!='verified':raise RuntimeError(str(video))
        (root/'batch_condition.json').write_text(json.dumps({'condition':row,'condition_table_sha256':table_hash,
            'role':'development_qualification_not_formal_benchmark'},ensure_ascii=False,indent=2))
        print(json.dumps({'completed_and_audited':row['run']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
