#!/usr/bin/env python3
"""终态核验修复后续跑原表：重验已有结果，只启动不存在的条件，不重跑episode。"""
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
    args=parser.parse_args();table=Path('experiments/coherent_joint_20261008/conditions.csv')
    digest=sha256(table.read_bytes()).hexdigest()
    conditions=[row for row in csv.DictReader(table.open()) if row['system']==args.system]
    for row in conditions:
        if sha256(table.read_bytes()).hexdigest()!=digest:raise RuntimeError('原条件表已变化')
        root=Path('results/continuous_v2')/row['run']
        if root.exists():
            if not (root/'summary.json').exists():raise RuntimeError('已有非终态结果，禁止覆盖或重跑：'+str(root))
            provenance=json.loads((root/'provenance.json').read_text())
            for key in ['activity','situation','profile']:
                if provenance[key]!=row[key]:raise RuntimeError('已有条件与原表不同')
            for key in ['seed','init_state_id','steps']:
                if provenance[key]!=int(row[key]):raise RuntimeError('已有初始化或预算与原表不同')
            prior=root/'batch_condition.json'
            if prior.exists() and json.loads(prior.read_text())['condition_table_sha256']!=digest:
                raise RuntimeError('已有结果不属于此固定表')
        else:
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
                result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=os.environ.copy())
            if result.returncode:raise RuntimeError('新条件运行失败，保留并停止：'+row['run'])
        for script in ['audit_joint_activity.py','evaluate_joint_process.py']:
            subprocess.run([sys.executable,'scripts/'+script,'--input-dir',str(root)],check=True)
        video=verify_episode(root/'episode',root,require_timeline=True)
        (root/'independent_video_verification.json').write_text(json.dumps(video,ensure_ascii=False,indent=2))
        if video['status']!='verified':raise RuntimeError('视频核验失败，保留并停止')
        (root/'batch_condition.json').write_text(json.dumps({'condition':row,'condition_table_sha256':digest,
            'role':'development_qualification_not_formal_benchmark'},ensure_ascii=False,indent=2))
        print(json.dumps({'existing_or_new_condition_verified':row['run']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
