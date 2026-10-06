#!/usr/bin/env python3
"""事后重建多主体放置；不以另一只空手的开口否定物体已释放。原始分数不覆盖。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def audit(directory):
    metrics=json.loads((directory/'metrics.json').read_text())
    spec=metrics['robot_goal_spec']
    if spec['kind'] not in {'on','in'}:raise ValueError('只审计物体放置，关节目标不适用')
    trace=rows(directory/'trace.jsonl');raw=rows(directory/'placement_evidence.jsonl')
    assert len(trace)==len(raw)+1
    obj,receiver=spec['object_id'],spec['receiver_id'];duration=0.;first=None;records=[]
    for previous,current,old in zip(trace,trace[1:],raw):
        assert old['time_s']==current['time_s']
        support=touch=False
        for c in current['contacts']:
            a,b=c['geom1'] or '',c['geom2'] or ''
            if b.startswith(obj+'_'):a,b=b,a
            if a.startswith(obj+'_'):
                support|=b.startswith(receiver+'_')
                touch|=b.startswith(('gripper','human_left_finger','human_right_finger','human_palm','human_fingertip'))
        dt=current['time_s']-previous['time_s'];assert dt>0
        speed=max(float(np.linalg.norm(np.array(current['objects'][name])-previous['objects'][name])/dt) for name in [obj,receiver])
        eligible=old['native_geometry_satisfied'] and support and not touch and speed<.08
        duration=duration+dt if eligible else 0.
        stable=bool(duration>=.2-1e-9)
        if stable and first is None:first=current['time_s']
        records.append({'time_s':current['time_s'],'geometry_satisfied':old['native_geometry_satisfied'],
                        'receiver_contact':support,'any_actor_hand_contact':touch,'pair_peak_speed_m_s':speed,
                        'stable_duration_s':duration,'all_actor_released_stable':stable,
                        'raw_aperture_dependent_success':old['released_stable_placement']})
    return {'episode':str(directory),'first_all_actor_released_stable_s':first,
            'final_all_actor_released_stable':records[-1]['all_actor_released_stable'],
            'raw_final_aperture_dependent_success':raw[-1]['released_stable_placement'],
            'disagreement_record_count':sum(r['all_actor_released_stable']!=r['raw_aperture_dependent_success'] for r in records),
            'records':records,'criterion_version':'all_actor_contact_release_v1',
            'interpretation':'事后物理关系审计：原生几何判据、实际支撑、双方手部无接触、两物体速度低于0.08m/s稳定0.2秒。原始分数保留；不证明策略因果、容器完全包含或人体安全。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    episodes=[audit(p.parent) for p in sorted(args.input_dir.rglob('placement_evidence.jsonl'))]
    assert episodes
    value={'status':'audited','criterion_version':'all_actor_contact_release_v1','episodes':episodes}
    (args.input_dir/'multi_actor_release_verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps({'episodes':len(episodes),'final_relations_satisfied':sum(e['final_all_actor_released_stable'] for e in episodes)},ensure_ascii=False))


if __name__=='__main__':main()
