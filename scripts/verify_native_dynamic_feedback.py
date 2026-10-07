#!/usr/bin/env python3
"""重建生成式伙伴可见的反馈，核对模型决定与实际执行命令的时间关系。"""
import argparse
import json
from pathlib import Path

import numpy as np
from hrc_pilot.libero_native import perceived_object_contacts
from hrc_pilot.native_contact_observation import own_contact_observation


def rows(path):return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_episode(directory):
    trace=rows(directory/'trace.jsonl');decisions=rows(directory/'human_policy_io.jsonl')
    by_step={row['step']:row for row in trace}
    prohibited={'task_success','human_goal_success','task_contract','premature_placements','robot_placement_credit'}
    for decision in decisions:
        if decision['parse_error'] is not None:
            assert decision['parsed_decision']['intent']=='observe'
        public=json.loads(decision['public_input'].split('\n',1)[1])
        assert not prohibited.intersection(public)
        if 'robot_action' in public:assert public['robot_action']=='native_joint_control'
        else:assert public.get('observation_projection')=='compact_measured_world_v1'
        actual=by_step[decision['step']]
        measured=public['your_measured_execution']
        if 'hand_contact_report' in measured:
            expected_contacts=own_contact_observation(actual['contacts'],'human')
            assert measured['hand_contact_report']==expected_contacts
            assert measured['hand_contact_geoms']==expected_contacts['contact_geoms']
        if public.get('observation_projection')=='compact_measured_world_v1':
            np.testing.assert_allclose(public['human_position_xyz'],actual['human_position'],atol=.00051)
        else:np.testing.assert_allclose(measured['body_xy'],actual['human_position'][:2],atol=1e-9)
        np.testing.assert_allclose(measured['fingertip_xyz'],actual['human_hand_position'],atol=1e-9)
        if 'body_remaining_distance_m' in measured:
            np.testing.assert_allclose(measured['body_remaining_distance_m'],
                                       np.linalg.norm(np.asarray(measured['body_xy'])-measured['body_target_xy']))
        motion=public['robot_measured_motion']
        if 'perceived_object_contacts' in motion:assert motion['perceived_object_contacts']==perceived_object_contacts(actual)
        previous=by_step.get(actual['step']-1)
        expected_speed=(np.linalg.norm(np.asarray(actual['robot_ee'])-previous['robot_ee'])/
                        (actual['time_s']-previous['time_s']) if previous is not None else 0.)
        np.testing.assert_allclose(motion['eef_speed_m_s'],expected_speed,atol=1e-9)
        if 'object_id' in measured:
            np.testing.assert_allclose(measured['object_xyz'],actual['objects'][measured['object_id']])
            np.testing.assert_allclose(measured['object_remaining_xy_distance_m'],
                np.linalg.norm(np.asarray(measured['object_xyz'])[:2]-np.asarray(measured['destination_xyz'])[:2]))
    for actual in trace[1:]:
        previous=[row for row in decisions if row['time_s']<actual['time_s']-1e-9]
        assert previous
        assert actual['human_execution']['accepted_intent']==previous[-1]['parsed_decision']['intent']
    return {'episode':str(directory),'feedback_records':len(decisions),'status':'verified',
            'model_output_parse_error_count':sum(row['parse_error'] is not None for row in decisions),
            'public_geometry_reconstructed':True,'actual_robot_speed_reconstructed':True,
            'model_commands_followed_without_plan_routing':True,
            'interpretation':'核对记录的模型命令、反馈和物理测量一致；不证明模型理解或真人效度。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',required=True,type=Path)
    args=parser.parse_args()
    episodes=[verify_episode(path.parent) for path in sorted(args.input_dir.rglob('metrics.json'))]
    assert episodes
    result={'status':'verified','episodes':episodes,'episode_count':len(episodes)}
    (args.input_dir/'human_feedback_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'{len(episodes)}条生成式伙伴反馈和命令时间链路核查通过')


if __name__=='__main__':main()
