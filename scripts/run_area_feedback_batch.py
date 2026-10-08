"""预定三活动：区域内放置与自身事实反馈，失败保留不自动重试。"""
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    table=Path('experiments/area_feedback_20261009/conditions.csv');digest=sha256(table.read_bytes()).hexdigest()
    for row in csv.DictReader(table.open()):
        root=Path('results/continuous_v2')/row['run']
        if root.exists():raise RuntimeError('禁止覆盖：'+str(root))
        if sha256(table.read_bytes()).hexdigest()!=digest:raise RuntimeError('条件表变化')
        command=[sys.executable,'scripts/run_workspace_joint_activity.py',
            '--activity',row['activity'],'--situation',row['situation'],'--profile',row['profile'],
            '--init-state-id',row['init_state_id'],'--seed',row['seed'],'--steps',row['steps'],
            '--context-step','800','--human-decision-steps','80','--coordinator-decision-steps','80',
            '--workspace-method','--activity-specific-context','--human-auto-buffer',
            '--human-relational-targets','--human-complete-observation','--symbolic-coordinator',
            '--robot-skill-bank','--interaction-contract','--human-area-placement',
            '--human-contribution-observations','--port','8766','--output-dir',str(root)]
        if row['initial_human_holding']=='1':command.append('--initial-human-holding')
        log=Path('/data1/sieniwgroup/sieniw/projects/HRC-Bench/results')/(row['run']+'.log')
        with log.open('x') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=os.environ.copy())
        if result.returncode:raise RuntimeError('保留失败：'+row['run'])
        (root/'batch_condition.json').write_text(json.dumps({'condition':row,'condition_table_sha256':digest,
            'role':'area_and_feedback_development_not_formal'},ensure_ascii=False,indent=2))
        for script in ['audit_joint_activity.py','evaluate_joint_process.py']:
            subprocess.run([sys.executable,'scripts/'+script,'--input-dir',str(root)],check=True)
        from hrc_pilot.video_verification import verify_episode
        video=verify_episode(root/'episode',root,require_timeline=True)
        (root/'independent_video_verification.json').write_text(json.dumps(video,ensure_ascii=False,indent=2))
        if video['status']!='verified':raise RuntimeError('视频核查失败')
        subprocess.run([sys.executable,'scripts/build_area_feedback_report.py'],check=True)
        print(json.dumps({'condition_verified':row['run']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
