import json
import copy
import numpy as np
from pathlib import Path
from dataclasses import replace

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_grounded_human import GroundedReflectiveHuman
from hrc_pilot.protocol import Observation,Message
from hrc_pilot.reflective_human_verification import verify_reflective_records


def observation():
    return Observation(objects={'plate':(0.,0.,.9),'bowl':(.1,0.,.9)},regions={'personal':(0.,.3,.9)},
        messages=(Message('environment','assignment','Robot handles bowl',None,'robot'),),
        robot_ee=(0.,0.,1.),human_position=(0.,.6,0.),held_by_human=(),completed_skills=(),
        human_execution={'manipulable_object_ids':['plate','bowl'],'object_measured_in_hand':None})


def test_grounded_state_does_not_promote_old_generated_claims_to_evidence():
    outputs=iter(['I should consider the measured plate, not assume a grasp. </think>'+json.dumps({
        'decision_kind':'continue','long_term_intention':'整理餐盘','personal_targets':[['plate','personal']],
        'plan':['grasp plate','place plate personal']}),json.dumps({'intent':'grasp','object_id':'plate'})])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused'),
        autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0);p.experience_memory=[{'memory_id':'old','text':'I already placed everything.'}]
    output=p.step(observation());public=json.loads(p.policy_io[0]['public_input'].split('\n',1)[1])
    assert output.command.intent=='grasp' and output.command.object_id=='plate'
    assert 'your_personal_experience_memory' not in public and 'your_recent_public_decisions' not in public
    assert public['robot_current_assignments'][0]['assigned_role']=='robot'
    assert p.planning_io[0]['raw_model_output'].startswith('I should consider')
    assert p.planning_io[0]['thinking_enabled'] and not p.policy_io[0]['thinking_enabled']
    assert verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'


def test_truncated_thinking_retains_intention_and_is_not_parsed_as_final_decision():
    outputs=iter(['I am still reasoning and might consider {"personal_targets":[]} ',json.dumps({'intent':'observe'})])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused'),
        autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0);p.step(observation())
    assert p.planning_io[0]['validation_error'] and p.planning_io[0]['raw_output']==''
    assert p.personal_targets==[] and verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'


def test_new_and_revised_targets_get_current_geometry_before_motor_inference():
    outputs=iter([
        'Reasoning </think>'+json.dumps({'decision_kind':'continue','long_term_intention':'整理餐盘',
            'personal_targets':[['plate','personal']],'observed_changes':'Everything already placed!',
            'assumption_corrections':['Wrong past belief'],'plan':['Move plate']}),
        '{"intent":"grasp","object_id":"plate"}',
        'Reasoning </think>'+json.dumps({'decision_kind':'revise','long_term_intention':'先整理碗',
            'personal_targets':[['bowl','personal']],'plan':['Move bowl']}),
        '{"intent":"grasp","object_id":"bowl"}'])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path=Path('/unused'),
        autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0);p.step(observation());p.step(replace(observation(),time_s=6))
    for row,obj in zip(p.policy_io,['plate','bowl']):
        v=json.loads(row['public_input'].split('\n',1)[1])
        assert v['your_current_personal_targets']==[{'object_id':obj,'destination':'personal'}]
        assert [g['object_id'] for g in v['your_target_geometry']]==[obj]
        assert v['your_target_geometry'][0]['measurement_time_s']==row['time_s']
        assert 'observed_changes' not in v['active_intention_plan']
        assert 'Everything already placed!' not in row['public_input']
    assert p.planning_io[0]['active_intention_plan']['observed_changes']=='Everything already placed!'
    assert verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'


def test_relative_goal_uses_current_collision_support_height_and_tracks_receiver():
    outputs=iter([
        'Reasoning </think>'+json.dumps({'decision_kind':'continue',
            'long_term_intention':'把餐盘放到碗上','personal_targets':[['plate','on:bowl']],
            'plan':['Move plate onto bowl']}),
        '{"intent":"grasp","object_id":"plate"}',
        '{"intent":"observe"}'])
    p=GroundedReflectiveHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),
        model_path=Path('/unused'),autonomous_context='pantry_work',generator=lambda _:next(outputs))
    p.reset(0)
    o=observation()
    interface={'receiver_object_id':'bowl','support_xyz':[.1,0.,.96]}
    p.step(replace(o,human_execution={**o.human_execution,
        'relative_placement_destinations':{'on:bowl':interface}}))
    moved=replace(o,time_s=2,objects={**o.objects,'bowl':(.3,.1,.92)},
        human_execution={**o.human_execution,'relative_placement_destinations':{
            'on:bowl':{**interface,'support_xyz':[.3,.1,.98]}}})
    p.step(moved)
    for row,point in zip(p.policy_io,[[.1,0.,.96],[.3,.1,.98]]):
        public=json.loads(row['public_input'].split('\n',1)[1])
        assert public['human_input_contract']=='current_intentions_and_support_geometry_v3'
        np.testing.assert_allclose(public['your_target_geometry'][0]['destination_xyz'],point)
        assert public['your_target_geometry'][0]['measurement_time_s']==row['time_s']
    assert verify_reflective_records(p.planning_io,p.policy_io)['status']=='verified'
    # 已保存的v2记录仍按原body位置语义审计，不回写历史输入。
    legacy=copy.deepcopy(p.policy_io)
    for row in legacy:
        public=json.loads(row['public_input'].split('\n',1)[1])
        public['human_input_contract']='current_intentions_and_measured_geometry_v2'
        public['your_target_geometry'][0]['destination_xyz']=public['objects_xyz']['bowl']
        row['public_input']='阶段：当前动作\n'+json.dumps(public)
    assert verify_reflective_records(p.planning_io,legacy)['status']=='verified'
