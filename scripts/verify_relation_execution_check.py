#!/usr/bin/env python3
"""核对固定关系执行检查：原始控制、几何、释放支撑与完整真实视频。"""
import argparse
import json
from pathlib import Path

import numpy as np

from audit_joint_activity import audit
from hrc_pilot.geometry_frame_replay import replay_recorded_geometry
from hrc_pilot.human_relation_targets import relation_placement_targets
from hrc_pilot.video_verification import verify_episode


def read_rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify(root):
    p=json.loads((root/'provenance.json').read_text());ep=root/'episode'
    assert p['role']=='fixed_execution_qualification_not_dynamic_collaboration'
    assert p['human_source']=='reference' and p['reference_vla_instruction']
    audit(root)
    from robosuite.utils.binding_utils import MjSim
    sim=MjSim.from_xml_file(str((ep/'scene.xml').resolve()))
    trace=read_rows(ep/'trace.jsonl');human=read_rows(ep/'human_policy_io.jsonl')
    controls=read_rows(ep/'robot_control.jsonl');calls=read_rows(ep/'model_calls.jsonl')
    assert all(row['source']=='actual_vla_reference_instruction' for row in controls)
    assert all(row['action_source']=='actual_vla_reference_instruction' for row in calls)
    geometry=[]
    for row in human:
        record=trace[round(row['time_s']*20)]
        replay_recorded_geometry(sim.model._model,sim.data._data,record)
        targets=relation_placement_targets(sim.model,sim.data,list(record['objects']))
        saved=row['private_input']['scene']['relation_targets']
        assert set(targets)==set(saved)
        for name,target in targets.items():
            actual=saved[name]
            for key in ['object_id','relation','reference_object_id','support_collision_geom']:
                assert target[key]==actual[key]
            error=float(np.max(np.abs(np.asarray(target['target_xyz'])-actual['target_xyz'])))
            assert error<=.0002
            geometry.append({'time_s':row['time_s'],'target':name,'max_axis_error_m':error})
    witnesses={name:[] for name in ['cream_cheese_1__in__akita_black_bowl_1','akita_black_bowl_1__on__plate_1']}
    for record in trace:
        replay_recorded_geometry(sim.model._model,sim.data._data,record)
        targets=relation_placement_targets(sim.model,sim.data,list(record['objects']))
        owned=set(record['human_execution'].get('carried_objects',[]))
        if record['human_execution']['held_object']:owned.add(record['human_execution']['held_object'])
        for name,series in witnesses.items():
            target=targets.get(name)
            if target is None:
                series.append({'time_s':record['time_s'],'measured_supported_relation':False,'reference_surface_available':False});continue
            obj=target['object_id'];reference=target['reference_object_id'];support=target['support_collision_geom']
            pairs=[c for c in record['contacts'] if any((c[g] or '').startswith(obj+'_') for g in ['geom1','geom2'])]
            actual_support=any(support in [c['geom1'],c['geom2']] for c in pairs)
            reference_contact=any(any((c[g] or '').startswith(reference+'_') for g in ['geom1','geom2']) for c in pairs)
            robot_contact=any(any((c[g] or '').startswith(('robot','gripper')) for g in ['geom1','geom2']) for c in pairs)
            delta=np.asarray(record['objects'][obj])-target['target_xyz']
            released=obj not in owned and not robot_contact
            near=bool(np.linalg.norm(delta[:2])<.025 and abs(delta[2])<.025)
            relative=np.asarray(record['objects'][obj])-record['objects'][reference]
            native_ontop=bool(relative[2]>=0 and np.linalg.norm(relative[:2])<.03 and reference_contact)
            series.append({'time_s':record['time_s'],'source_object':obj,'reference_object':reference,
                'source_released_from_human_and_robot':released,'reference_support_collision_geom':support,
                'actual_support_contact':actual_support,'xy_distance_m':float(np.linalg.norm(delta[:2])),
                'any_reference_collision_contact':reference_contact,
                'native_ontop_equivalent':native_ontop,
                'released_reference_support_observed':bool(released and native_ontop),
                'signed_height_error_m':float(delta[2]),'near_computed_support_center':near,
                'measured_supported_relation':bool(released and near and actual_support)})
    terminal={}
    for name,series in witnesses.items():
        last=[w for w in series if w['time_s']>=trace[-1]['time_s']-1]
        terminal[name]={'first_measured_supported_relation_s':next((w['time_s'] for w in series if w['measured_supported_relation']),None),
                       'last_second_consistent':all(w['measured_supported_relation'] for w in last),
                       'last_second_released_reference_support':all(w.get('released_reference_support_observed',False) for w in last),
                       'terminal':series[-1]}
    video=verify_episode(ep,root,require_timeline=True)
    (root/'independent_video_verification.json').write_text(json.dumps(video,ensure_ascii=False,indent=2))
    assert video['status']=='verified'
    eef_delta=np.asarray(trace[-1]['robot_ee'])-trace[0]['robot_ee']
    report={'status':'records_geometry_and_video_verified','formal_benchmark_score':None,
        'human_neural_calls':0,'actual_vla_calls':len(calls),'actual_robot_controls':len(controls),
        'relation_geometry_max_axis_error_m':max(g['max_axis_error_m'] for g in geometry),
        'measured_relation_results':terminal,'robot_eef_displacement_m':eef_delta.tolist(),
        'robot_reference_instruction':p['reference_vla_instruction'],
        'robot_withdrawal_success':None,
        'relation_criteria_note':'原中心底面接触判据保留不变；另列参考物任一碰撞面支撑与LIBERO ObjectState.check_ontop的等价几何条件，不把它升级为完整包含。',
        'scope':'接触＋释放＋中心位置的保守物理见证，不是完整容器包含、工作链成功或动态人物效度。末端位移不等于全机械臂清场；退让能力尚需从实际占位审阅。'}
    (root/'relation_execution_evidence.json').write_text(json.dumps({'summary':report,'geometry':geometry,'relation_samples':witnesses},ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    verify(parser.parse_args().input_dir)
