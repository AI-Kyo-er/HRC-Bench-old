#!/usr/bin/env python3
"""保留旧位置判据，额外核查高台实际释放/支撑和双方同时满足的时间。"""
import argparse
import json
from pathlib import Path

import numpy as np

from hrc_pilot.native_personal_evidence import evaluate_personal_goals,signature


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    result=[]
    for path in sorted(args.input_dir.rglob('personal_context.json')):
        directory=path.parent;context=json.loads(path.read_text());trace=rows(directory/'trace.jsonl')
        human=rows(directory/'human_policy_io.jsonl');controls=rows(directory/'human_control.jsonl');placement=rows(directory/'placement_evidence.jsonl')
        physical=evaluate_personal_goals(context['regions'],trace,controls,human,placement,require_shelf_release=True)
        first_joint=None;previous=None;dwell={};chosen=human[0]['personal_goal_state']['personal_targets'];which=0
        for i,r in enumerate(trace[1:]):
            while which+1<len(human) and human[which+1]['time_s']<=r['time_s']:
                which+=1;chosen=human[which]['personal_goal_state']['personal_targets']
            sig=signature(chosen,context['regions'])
            if sig!=previous:dwell={};previous=sig
            stable=True
            for t in chosen:
                obj=t['object_id'];point=np.asarray(context['regions'][t['destination']]);position=np.asarray(r['objects'][obj])
                speed=np.linalg.norm(position-np.asarray(trace[i]['objects'][obj]))/.05
                ok=np.linalg.norm(position[:2]-point[:2])<.025 and abs(position[2]-point[2])<.025 and speed<.08
                if t['destination'].endswith('_shelf'):
                    support=touch=False
                    for c in r['contacts']:
                        a,b=c['geom1'] or '',c['geom2'] or ''
                        if b.startswith(obj+'_'):a,b=b,a
                        if a.startswith(obj+'_'):
                            support|=b=='human_storage_support'
                            touch|=b.startswith(('human_left_finger','human_right_finger','gripper'))
                    ok=ok and support and not touch
                dwell[obj]=dwell.get(obj,0)+.05 if ok else 0
                stable&=dwell[obj]>=.2-1e-9
            if chosen and stable and placement[i]['released_stable_placement'] and first_joint is None:first_joint=r['time_s']
        original=json.loads((directory/'metrics.json').read_text())
        result.append({'episode':str(directory),'raw_position_joint_predicate':original['task_success'],
                       'released_goal_evidence':physical,'first_joint_released_stable_s':first_joint,
                       'final_joint_released_stable':physical['joint_observable_goals_satisfied'],
                       'interpretation':'事后更严格的高台放置审计，原始位置评分/输入/轨迹不覆盖；释放和物理支撑不由生成式声明代替。'})
    assert result
    (args.input_dir/'storage_verification.json').write_text(json.dumps({'status':'audited','episodes':result},ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
