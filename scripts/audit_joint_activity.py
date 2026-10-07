#!/usr/bin/env python3
"""独立核对公开渠道、实际命令、连续人动作和真实机器人动作；不冒充语义效度。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.joint_human_policy import parse_choice


def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
def read(p):return json.loads(p.read_text())


def audit(root):
    ep=root/'episode';p=read(root/'provenance.json');activity=ACTIVITIES[p['activity']]
    assert not p['source_files_changed_during_run']
    assert p['human_executor']=='human_only_continuous_kinematic_attachment'
    trace=rows(ep/'trace.jsonl');human=rows(ep/'human_policy_io.jsonl');controls=rows(ep/'robot_control.jsonl')
    calls=rows(ep/'model_calls.jsonl');dialogue=rows(ep/'public_dialogue.jsonl');receipts=rows(ep/'human_command_receipts.jsonl')
    raw_human=rows(ep/'human_control.jsonl');contexts=rows(ep/'private_context.jsonl')
    assert len(trace)==len(controls)+1 and len(human)==len(receipts)
    np.testing.assert_allclose([r['physics_time_s']-trace[0]['physics_time_s'] for r in trace],
                               np.arange(len(trace))/20,atol=1e-7)
    for d,receipt in zip(human,receipts):
        assert d['decision_id']==receipt['request_id'] and d['choice']==receipt['choice']
        source=d['private_input'];scene=source['scene'];actual=trace[round(d['time_s']*20)]
        assert source['activity']==json.loads(json.dumps(activity.public(),ensure_ascii=False))
        assert 'private_background' not in source['activity']
        assert not {'task_success','score','future_context'}.intersection(scene)
        for obj,xyz in scene['objects_xyz'].items():np.testing.assert_allclose(xyz,actual['objects'][obj])
        np.testing.assert_allclose(scene['robot_eef_xyz'],actual['robot_ee'])
        assert all(m in dialogue and m['time_s']<=d['time_s'] for m in scene['public_dialogue'])
        assert all(c in contexts and c['time_s']<=d['time_s'] for c in scene['private_context'])
        if d['parse_error'] is None:
            assert parse_choice(d['raw_output'],scene['objects_xyz'],scene['regions_xyz'])==d['choice']
    emitted=[(d['time_s'],d['choice']['message'],d['decision_id']) for d in human if d['choice'].get('message')]
    assert emitted==[(m['time_s'],m['text'],m['human_decision_id']) for m in dialogue if m['speaker']=='human']
    received=0
    for c in calls:
        visible=dialogue[:c['visible_dialogue_count']]
        assert all(m['time_s']<=c['time_s'] for m in visible)
        if p['robot_system']=='direct_vla_public_dialogue':
            # 依据保存的设置兼容旧开发记录，不能倒改旧输入。
            recent=([m for m in visible if m['speaker'] in {'human','robot'}][-2:]
                    if p['robot_model_metadata'].get('language_token_limit') else visible[-12:])
            spoken='\n'.join(f'{m["speaker"]}: {m["text"]}' for m in recent)
            expected=activity.public_description+'\nActual public conversation:\n'+spoken
            assert c['prompt']==expected
            received+=sum(m['speaker']=='human' for m in visible[-12:])
        if 'language_input_evidence' in c:
            evidence=c['language_input_evidence']
            assert not evidence['truncated'] and evidence['token_count']<=evidence['token_limit']
            assert sum(evidence['token_mask'])==evidence['token_count']
        np.testing.assert_allclose(np.load(ep/f'observation_{c["step"]:06d}_state.npy'),c['state'])
        from PIL import Image
        for suffix,field in [('', 'exterior_rgb_sha256'),('_wrist','wrist_rgb_sha256')]:
            pixels=np.asarray(Image.open(ep/f'observation_{c["step"]:06d}{suffix}.png').convert('RGB'))
            assert sha256(pixels.tobytes()).hexdigest()==c[field]
        actions=np.load(ep/f'observation_{c["step"]:06d}_actions.npy')
        np.testing.assert_allclose(actions,np.asarray(c['raw_action_chunk'])[:c['executed_action_count']])
    for control,actual,next_actual in zip(controls,trace,trace[1:]):
        c=calls[control['model_call_id']]
        chunk_index=control['step']-c['step']
        np.testing.assert_allclose(control['action'],c['raw_action_chunk'][chunk_index])
        np.testing.assert_allclose([control['pre_physics_time_s'],control['post_physics_time_s']],
                                  [actual['physics_time_s'],next_actual['physics_time_s']],atol=1e-7)
        assert control['source']==c['action_source']
    velocities=np.asarray([r['hand_velocity'] for r in raw_human])
    speed=float(np.linalg.norm(velocities,axis=1).max())
    assert speed<=.200001 and all(r['robot_pose_writes']==0 for r in raw_human)
    assert all(r['human_attached_object_pose_write'] is None or r['human_attached_object_pose_write']==r['held_object'] for r in raw_human)
    times=np.asarray([r['physics_time_s'] for r in raw_human]);positions=np.asarray([r['hand_xyz'] for r in raw_human])
    assert np.all(np.diff(times)>0)
    sampled=float((np.linalg.norm(np.diff(positions,axis=0),axis=1)/np.diff(times)).max())
    assert sampled<=.200001
    robot_received_human_calls=sum('human:' in c['prompt'] for c in calls)
    review=[{'time_s':d['time_s'],'private_intention':d['choice'].get('intention'),
             'public_message':d['choice'].get('message'),'actual_action':d['choice']['action'],
             'execution_accepted':receipts[i]['accepted'],'execution_error':receipts[i]['error']}
            for i,d in enumerate(human)]
    result={'status':'verified','world_initializations':1,'human_neural_calls':len(human),
        'robot_action_blocks':len(calls),'actual_robot_control_steps':len(controls),
        'robot_calls_with_actual_human_speech':robot_received_human_calls,
        'human_calls_with_actual_robot_measurement':len(human),'human_peak_reference_speed_m_s':speed,
        'human_peak_sampled_kinematic_speed_m_s':sampled,'human_executor_rejection_count':sum(not r['accepted'] for r in receipts),
        'human_attached_object_pose_write_samples':sum(r['human_attached_object_pose_write'] is not None for r in raw_human),
        'private_context_notifications':contexts,'behavior_review':review,
        'interpretation':'验证实际观测、公开渠道和执行一致；不证明真人策略、共同任务完成、语义变化或cobalance。'}
    write_path=root/'interaction_verification.json';write_path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return {k:v for k,v in result.items() if k not in {'behavior_review','private_context_notifications'}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-dir',type=Path,required=True)
    print(json.dumps(audit(parser.parse_args().input_dir),ensure_ascii=False))
