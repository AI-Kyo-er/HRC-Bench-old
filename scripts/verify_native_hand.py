#!/usr/bin/env python3
"""核查双指接触、物体真实抬升、支撑释放和控制时钟，不读取策略完成声明。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def verify(directory):
    trace=rows(directory/'trace.jsonl');control=rows(directory/'human_control.jsonl')
    metrics=json.loads((directory/'metrics.json').read_text());obj=metrics.get('object_id','cookies_1')
    initial=np.asarray(trace[0]['objects'][obj]);bilateral=[];released=[]
    for r in trace:
        contacts=r['contacts'];finger=[False,False];support=False
        for c in contacts:
            a,b=c['geom1'] or '',c['geom2'] or ''
            if b.startswith(obj+'_'):a,b=b,a
            if a.startswith(obj+'_'):
                for i,side in enumerate(['left','right']):finger[i]|=b=='human_'+side+'_finger_contact'
                support|=b=='human_storage_support'
        lift=r['objects'][obj][2]-initial[2]
        if all(finger) and lift>.04:bilateral.append(r['time_s'])
        if support and not any(finger):released.append(r['time_s'])
    speed=max(float(np.linalg.norm(c['actual_velocity'])) for c in control)
    positions=[np.asarray(r['objects'][obj]) for r in trace]
    object_speed=max(float(np.linalg.norm(b-a)/.05) for a,b in zip(positions,positions[1:]))
    assert all(c['human_object_pose_writes']==0 for c in control)
    np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],np.arange(len(trace))*.05,atol=1e-7)
    result={'episode':str(directory),'first_bilateral_contact_lift_s':bilateral[0] if bilateral else None,
            'first_released_support_contact_s':released[0] if released else None,
            'maximum_object_lift_m':float(max(p[2]-initial[2] for p in positions)),
            'human_peak_speed_m_s':speed,'object_peak_sampled_speed_m_s':object_speed,
            'friction_grasp_and_release_observed':bool(bilateral and released),
            'motion_qualified':bool(speed<=.65 and object_speed<=1.5),
            'object_pose_writes':0,'interpretation':'从接触和物理位置重建，不以grasp命令或生成式确认替代实际抓持。'}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[verify(p.parent) for p in sorted(args.input_dir.rglob('human_control.jsonl'))]
    assert episodes
    result={'status':'audited','episodes':episodes,'friction_grasp_release_count':sum(e['friction_grasp_and_release_observed'] for e in episodes),
            'motion_qualified_count':sum(e['motion_qualified'] for e in episodes)}
    (args.input_dir/'hand_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
