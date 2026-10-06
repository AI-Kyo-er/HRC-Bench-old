import json
from dataclasses import replace
from types import SimpleNamespace

import numpy as np

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_contact_human import NativeContactHuman, NativeQwenHuman
from hrc_pilot.native_execution import NativeMotionObserver, interaction_metrics
from hrc_pilot.protocol import Observation


def public_observation(time_s=0):
    return Observation(objects={'plate_1':(0,.2,.9)},regions={'near_human':(0,.32,.9)},messages=(),
                       robot_ee=(0,0,1),human_position=(.25,.70,0),held_by_human=(),completed_skills=(),
                       time_s=time_s,human_execution={'status':'running','body_remaining_distance_m':.10},
                       robot_motion={'eef_speed_m_s':0.,'motion_observed':False})


def test_generated_plan_is_reconsidered_by_model_and_never_routes_actions():
    outputs=iter([
        {'intent':'return','plan':['回到工作位','推盘子'],'memory_note':'已返回'},
        {'intent':'observe','plan':['暂停核对实际位置'],'wait_condition':'机械臂离开盘子'}])
    prompts=[]
    policy=NativeQwenHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path='/tmp/no-model',
                          generator=lambda prompt:prompts.append(prompt) or json.dumps(next(outputs)),
                          decision_interval_steps=20)
    assert policy.step(public_observation()).command.intent=='return'
    assert policy.step(public_observation(1)).command.intent=='observe'
    visible=json.loads(prompts[-1].split('\n',1)[1])
    assert visible['your_measured_execution']['body_remaining_distance_m']==.10
    assert visible['your_previous_generated_plan']==['回到工作位','推盘子']
    assert visible['robot_measured_motion']['motion_observed'] is False
    assert len(policy.audit_state()['measured_execution_history'])==2
    assert 'task_success' not in prompts[-1]


def test_invalid_command_reaches_next_model_input_with_reason_and_no_automatic_repair():
    prompts=[]
    policy=NativeQwenHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),model_path='/tmp/no-model',
                          generator=lambda prompt:prompts.append(prompt) or
                          '{"intent":"push","object_id":"plate_1","destination":"plate_1"}',
                          decision_interval_steps=20)
    assert policy.step(public_observation()).command.intent=='observe'
    assert policy.step(public_observation(1)).command.intent=='observe'
    visible=json.loads(prompts[-1].split('\n',1)[1])
    assert visible['your_last_command_validation']['errors']==['unknown_destination_region']
    assert visible['action_interface']['push_destination_values']==['near_human']


def test_motor_finished_does_not_claim_object_goal_completed():
    actor=NativeContactHuman.__new__(NativeContactHuman)
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(time=4.)))
    actor.body_base=np.array([.25,.6]);actor.body_target=actor.body_base.copy()
    actor.position=lambda:np.array([0,.2,1.1]);actor.target=actor.position()
    actor.phase='idle';actor.accepted_intent='push';actor.command_started_at=1.
    actor.object_id='plate_1';actor.destination='near_human';actor.regions={'near_human':(0,.32,.9)}
    actor.object_position=lambda name:np.array([0,.2,.9])
    feedback=actor.public_feedback()
    assert feedback['status']=='motor_finished'
    assert np.isclose(feedback['object_remaining_xy_distance_m'],.12)
    actor.accepted_intent='return';actor.body_target=np.array([.25,.7])
    assert actor.public_feedback()['status']=='running'


def test_robot_motion_feedback_reports_stopping_without_fictional_task_label():
    observer=NativeMotionObserver()
    row={'time_s':0.,'robot_ee':[0,0,1.],'robot_qpos':[0,0], 'objects':{'bowl':[0,0,.9]}}
    observer.update(row)
    moving={**row,'time_s':1.,'robot_ee':[.2,0,1.]}
    assert observer.update(moving)['motion_observed']
    stopped={**moving,'time_s':2.}
    assert not observer.update(stopped)['motion_observed']
    assert 'placing_bowl' not in str(observer.update({**stopped,'time_s':3.}))


def test_interaction_durations_use_actual_motion_and_decision_intervals():
    row={'time_s':0.,'robot_ee':[0,0,1.],'human_hand_position':[1,0,1.],'human_position':[1,0,0]}
    trace=[row,{**row,'time_s':1.,'robot_ee':[.1,0,1.]},{**row,'time_s':2.,'robot_ee':[.1,0,1.]}]
    metrics=interaction_metrics(trace,[{'contact_geoms':[]},{'contact_geoms':['plate']}],
                                [{'time_s':0.,'parsed_decision':{'intent':'observe'}}])
    assert metrics['robot_ee_motion_time_s']==1.
    assert metrics['both_stationary_time_s']==1.
    assert metrics['human_observe_command_time_s']==2.
