#!/usr/bin/env python3
"""CPU重建保存的MuJoCo场景，独立核对人模型可见的相对支撑坐标。"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np

from hrc_pilot.native_relative_placement import relative_destinations


def verify(directory):
    model=mujoco.MjModel.from_xml_path(str((directory/'scene.xml').resolve()))
    data=mujoco.MjData(model)
    first=json.loads((directory/'trace.jsonl').open().readline())
    names=first['human_execution']['manipulable_object_ids']
    body_ids={n:mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,n+'_main') for n in names}
    assert all(i>=0 for i in body_ids.values())
    objects={}
    for name in names:
        geoms=[mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,i) for i in range(model.ngeom)
               if model.geom_bodyid[i]==body_ids[name] and (model.geom_contype[i] or model.geom_conaffinity[i])]
        assert geoms;objects[name]=SimpleNamespace(contact_geoms=geoms)
    adapter=SimpleNamespace(geom_type=model.geom_type,geom_size=model.geom_size,
                            geom_name2id=lambda n:mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,n))
    observed_data=SimpleNamespace(body_xpos=data.xpos,geom_xpos=data.geom_xpos,geom_xmat=data.geom_xmat)
    env=SimpleNamespace(env=SimpleNamespace(objects_dict=objects,obj_body_id=body_ids),sim=SimpleNamespace(model=adapter,data=observed_data))
    records=0;maximum=0.;receiver_motion=0.;selected_motion=0.;initial_by_key={};destination_counts=set()
    with (directory/'trace.jsonl').open() as stream:
        for line in stream:
            row=json.loads(line);data.qpos[:]=row['qpos'];data.qvel[:]=row['qvel']
            # mj_step caches geom poses before its final integration. Reconstruct that phase
            # rather than comparing cached feedback to positions advanced by one physics tick.
            if records:mujoco.mj_integratePos(model,data.qpos,data.qvel,-model.opt.timestep)
            mujoco.mj_forward(model,data)
            actual=relative_destinations(env);saved=row['human_execution']['relative_placement_destinations']
            assert set(actual)==set(saved)
            destination_counts.add(len(actual))
            for key in actual:
                a=np.asarray(actual[key]['support_xyz']);b=np.asarray(saved[key]['support_xyz'])
                error=float(np.linalg.norm(a-b));maximum=max(maximum,error)
                # XML serialization rounds the static layout and collision dimensions.
                np.testing.assert_allclose(a,b,atol=3e-6,rtol=0)
                initial_by_key.setdefault(key,a.copy())
                receiver_motion=max(receiver_motion,float(np.linalg.norm(a-initial_by_key[key])))
            feedback=row['human_execution']
            if feedback.get('destination','') in actual:
                np.testing.assert_allclose(feedback['destination_xyz'],actual[feedback['destination']]['support_xyz'],atol=3e-6,rtol=0)
                selected_motion=max(selected_motion,float(np.linalg.norm(np.asarray(actual[feedback['destination']]['support_xyz'])-initial_by_key[feedback['destination']])))
            records+=1
    return {'episode':str(directory),'status':'verified','reconstructed_frames':records,
            'maximum_support_coordinate_error_m':maximum,'maximum_potential_receiver_support_motion_m':receiver_motion,
            'maximum_selected_receiver_support_motion_m':selected_motion,
            'visible_relative_destination_counts':sorted(destination_counts),
            'source':'saved scene.xml + measured qpos/qvel; reconstruct mj_step pre-integration geometry cache on CPU, no render',
            'interpretation':'核对真实状态下的接收支撑几何，未用任务分数选择工具或把接触放置称作完整包含。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    args=parser.parse_args();episodes=[verify(p.parent) for p in sorted(args.input_dir.rglob('trace.jsonl'))]
    assert episodes
    value={'status':'verified','episodes':episodes}
    (args.input_dir/'relative_geometry_verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps(value,ensure_ascii=False))


if __name__=='__main__':main()
