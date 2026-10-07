#!/usr/bin/env python3
"""重建人接触手与机械臂的几何接触时段，不将接触记录当作伤害或唯一因果。"""
import argparse
import json
from pathlib import Path


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def audit(directory):
    trace=rows(directory/'trace.jsonl');decisions=rows(directory/'human_policy_io.jsonl')
    intervals=[];start=None;duration=0.;geoms=set();contact_samples=0
    for previous,row in zip(trace,trace[1:]):
        matches=[]
        for pair in row['contacts']:
            a,b=pair['geom1'] or '',pair['geom2'] or ''
            if b.startswith('human_'):a,b=b,a
            if a.startswith(('human_palm','human_left_finger','human_right_finger','human_fingertip')) and b.startswith(('robot','gripper')) and pair['distance_m']<=0:
                matches.append(b)
        if matches:
            if start is None:start=previous['time_s'];geoms=set()
            geoms.update(matches);duration+=row['time_s']-previous['time_s'];contact_samples+=1
        elif start is not None:
            intervals.append({'start_s':start,'end_s':previous['time_s'],'robot_geoms':sorted(geoms)});start=None
    if start is not None:intervals.append({'start_s':start,'end_s':trace[-1]['time_s'],'robot_geoms':sorted(geoms)})
    exposed=sum('hand_contact_geoms' in json.loads(d['public_input'].split('\n',1)[1])['your_measured_execution'] for d in decisions)
    return {'episode':str(directory),'hand_robot_contact_record_time_s':duration,'sample_count':contact_samples,
            'intervals':intervals,'decision_count_with_direct_hand_contact_feedback':exposed,
            'interpretation':'只计记录中的人手与robot/gripper几何接触且distance<=0；不推断接触力、伤害、人体完整碰撞或唯一阻挡原因。接触反馈可见性单列。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[audit(p.parent) for p in sorted(args.input_dir.rglob('human_policy_io.jsonl'))]
    assert episodes
    (args.input_dir/'hand_robot_contact_verification.json').write_text(json.dumps({'status':'audited','episodes':episodes},ensure_ascii=False,indent=2))
    print(json.dumps([{'episode':e['episode'],'contact_record_time_s':e['hand_robot_contact_record_time_s']} for e in episodes],ensure_ascii=False))


if __name__=='__main__':main()
