#!/usr/bin/env python3
"""核查双指接触、物体真实抬升、支撑释放和控制时钟，不读取策略完成声明。"""
import argparse
import json
from pathlib import Path

import numpy as np


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def verify(directory,obj=None,destination=None):
    trace=rows(directory/'trace.jsonl');control=rows(directory/'human_control.jsonl')
    metrics=json.loads((directory/'metrics.json').read_text());obj=obj or metrics.get('object_id','cookies_1')
    destination=destination or metrics.get('destination')
    relative_receiver=destination.split(':',1)[1] if destination and destination.startswith('on:') else None
    initial=np.asarray(trace[0]['objects'][obj]);bilateral=[];released=[]
    for r in trace:
        contacts=r['contacts'];finger=[False,False];support=False
        for c in contacts:
            a,b=c['geom1'] or '',c['geom2'] or ''
            if b.startswith(obj+'_'):a,b=b,a
            if a.startswith(obj+'_'):
                for i,side in enumerate(['left','right']):finger[i]|=b=='human_'+side+'_finger_contact'
                support|=(b.startswith(relative_receiver+'_') if relative_receiver else
                          b=='table_collision' if destination and destination.endswith(('_personal','_home')) else
                          b=='human_storage_support' if destination and destination.endswith('_shelf') else
                          b in {'table_collision','human_storage_support'})
        lift=r['objects'][obj][2]-initial[2]
        if all(finger) and lift>.04:bilateral.append(r['time_s'])
        if support and not any(finger) and bilateral and r['time_s']>bilateral[0]:released.append(r['time_s'])
    speed=max(float(np.linalg.norm(c['actual_velocity'])) for c in control)
    positions=[np.asarray(r['objects'][obj]) for r in trace]
    object_speed=max(float(np.linalg.norm(b-a)/.05) for a,b in zip(positions,positions[1:]))
    assert all(c['human_object_pose_writes']==0 for c in control)
    np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],np.arange(len(trace))*.05,atol=1e-7)
    result={'episode':str(directory),'object_id':obj,'destination':destination,'first_bilateral_contact_lift_s':bilateral[0] if bilateral else None,
            'first_released_support_contact_s':released[0] if released else None,'relative_receiver':relative_receiver,
            'maximum_object_lift_m':float(max(p[2]-initial[2] for p in positions)),
            'human_peak_speed_m_s':speed,'object_peak_sampled_speed_m_s':object_speed,
            'friction_grasp_and_release_observed':bool(bilateral and released),
            'motion_qualified':bool(speed<=.65 and object_speed<=1.5),
            'object_pose_writes':0,'interpretation':'从接触和物理位置重建，不以grasp命令或生成式确认替代实际抓持。'}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[]
    for p in sorted(args.input_dir.rglob('human_control.jsonl')):
        metrics=json.loads((p.parent/'metrics.json').read_text())
        objects=[metrics['object_id']] if 'object_id' in metrics else sorted({r['object_id'] for r in rows(p) if r['object_id'] is not None})
        if not objects:
            initial=json.loads((p.parent/'trace.jsonl').open().readline())
            objects=initial['human_execution'].get('manipulable_object_ids',[])
            assert objects,'记录没有可审计的实际物品库存'
        decisions=rows(p.parent/'human_policy_io.jsonl') if (p.parent/'human_policy_io.jsonl').exists() else []
        for obj in objects:
            destinations=sorted({r['parsed_decision']['destination'] for r in decisions
                if r['parsed_decision']['intent']=='place' and r['parsed_decision']['object_id']==obj
                and r['parsed_decision'].get('destination')})
            if 'destination' in metrics:destinations=[metrics['destination']]
            episodes.extend(verify(p.parent,obj,d) for d in destinations or [None])
    assert episodes
    result={'status':'audited','episodes':episodes,'friction_grasp_release_count':sum(e['friction_grasp_and_release_observed'] for e in episodes),
            'motion_qualified_count':sum(e['motion_qualified'] for e in episodes)}
    (args.input_dir/'hand_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
