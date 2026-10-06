#!/usr/bin/env python3
"""检查完整场景的物品脱离桌面，保留任务完成和附带损失两个独立结果。"""
import argparse
import json
from pathlib import Path

import numpy as np


def audit(trace,movable_names,tabletop_z):
    objects=[]
    for name in movable_names:
        positions=np.asarray([r['objects'][name] for r in trace])
        times=np.asarray([r['time_s'] for r in trace]);dt=np.diff(times)
        assert (dt>0).all()
        speeds=np.linalg.norm(np.diff(positions,axis=0),axis=1)/dt
        dwell=0.;first=None;stable=None
        for i,r in enumerate(trace):
            below=r['objects'][name][2]<tabletop_z-.1
            if below and first is None:first=r['time_s']
            dwell=dwell+(times[i]-times[i-1]) if below and i else 0.
            if dwell>=.2-1e-9 and stable is None:stable=r['time_s']
        witnesses=[]
        if first is not None:
            for r in trace:
                if first-1<=r['time_s']<=first:
                    for c in r['contacts']:
                        a,b=c['geom1'] or '',c['geom2'] or ''
                        if b.startswith(name+'_'):a,b=b,a
                        if a.startswith(name+'_') and b.startswith(('robot','gripper','human')):
                            witnesses.append({'time_s':r['time_s'],'actor_geom':b})
        objects.append({'object_id':name,'maximum_displacement_m':float(np.linalg.norm(positions-positions[0],axis=1).max()),
                        'minimum_body_origin_z_m':float(positions[:,2].min()),'peak_sampled_speed_m_s':float(speeds.max()),
                        'first_below_table_clearance_s':first,'first_sustained_below_table_clearance_s':stable,
                        'terminal_below_table_clearance':bool(positions[-1,2]<tabletop_z-.1),
                        'actor_contact_witnesses_in_preceding_second':witnesses})
    return {'tabletop_z_m':tabletop_z,'clearance_below_table_m':.1,'stable_seconds':.2,'objects':objects,
            'sustained_below_table_object_count':sum(o['first_sustained_below_table_clearance_s'] is not None for o in objects),
            'interpretation':'完整物品库存的空间损失描述；物体body原点低于桌面10cm并持续0.2秒。接触见证不单独证明因果；自由落体速度不是瞬移，附带损失也不能被目标任务成功掩盖。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args()
    import mujoco
    episodes=[]
    for path in sorted(args.input_dir.rglob('trace.jsonl')):
        trace=[json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        model=mujoco.MjModel.from_xml_path(str((path.parent/'scene.xml').resolve()));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
        geom=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'table_collision');assert geom>=0
        tabletop_z=float(data.geom_xpos[geom,2]+model.geom_size[geom,2])
        names=trace[0]['human_execution']['manipulable_object_ids']
        episodes.append({'episode':str(path.parent),**audit(trace,names,tabletop_z)})
    assert episodes
    (args.input_dir/'scene_integrity_verification.json').write_text(json.dumps({'status':'audited','episodes':episodes},ensure_ascii=False,indent=2))
    print(json.dumps({'episodes':len(episodes),'sustained_below_table_objects':sum(e['sustained_below_table_object_count'] for e in episodes)},ensure_ascii=False))


if __name__=='__main__':main()
