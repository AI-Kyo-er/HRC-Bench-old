import json
from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.joint_human_policy import JointHumanPolicy,parse_choice
from hrc_pilot.kinematic_human import KinematicHuman


def test_private_need_is_not_in_public_activity_but_actual_feedback_changes_input():
    activity=ACTIVITIES['snack_service']
    assert 'private_background' not in activity.public() and 'external_context' not in activity.public()
    inputs=[]
    def generate(prompt):
        inputs.append(json.loads(prompt))
        return json.dumps({'action':'wait','intention':'prepare snack','message':'Can you wait?',
                          'reason':'partner still moving','memory':'observed motion'})
    p=JointHumanPolicy(activity,model_path='/unused',generator=generate)
    scene={'time_s':0.,'objects_xyz':{'bowl':[0,0,1]},'regions_xyz':{},'robot_motion':{'eef_speed':.1}}
    p.decide(scene)
    p.decide({**scene,'time_s':2.,'robot_motion':{'eef_speed':0.},'public_dialogue':[{'speaker':'robot','text':'Ready.'}]})
    assert inputs[1]['scene']['public_dialogue'][0]['text']=='Ready.'
    assert inputs[1]['scene']['robot_motion']['eef_speed']==0.
    assert inputs[1]['own_memory'][0]['text']=='observed motion'
    with pytest.raises(ValueError):parse_choice('{"action":"pick","object_id":"hidden"}',{'bowl':[]},{})
    structured=parse_choice('{"action":"pick","object_id":"bowl","memory":[]}',{'bowl':[]},{})
    assert structured['action']=='pick' and structured['memory']=='[]'
    assert parse_choice('{"action":"message","message":"Please wait."}',{}, {})['message']=='Please wait.'
    chosen=parse_choice('{"action":"message","presence_choice":"step_aside","message":"I will take the call aside."}',{}, {})
    assert chosen['action']=='away' and chosen['declared_action']=='message'


def test_explicit_participation_operation_is_executed_without_reading_speech():
    raw=json.dumps({'action':'message','participation':'step_aside','message':'Taking the call.'})
    # 旧运行按保存的schema重建，不倒改其失败行为。
    assert parse_choice(raw,{}, {})['action']=='message'
    choice=parse_choice(raw,{}, {},schema_version=2)
    assert choice['action']=='away' and choice['declared_action']=='message'
    assert choice['presence_choice']=='step_aside'
    return_choice=parse_choice('{"action":"wait","participation":"return_to_work"}',{}, {},schema_version=2)
    assert return_choice['action']=='return'
    # 不能根据一句话替人决定离开，也不能静默解决相反的明确操作。
    text_only=parse_choice('{"action":"message","participation":"busy","message":"I left."}',{}, {},schema_version=2)
    assert text_only['action']=='message'
    with pytest.raises(ValueError,match='冲突'):
        parse_choice('{"action":"message","participation":"step_aside","presence_choice":"keep"}',{}, {},schema_version=2)
    with pytest.raises(ValueError,match='冲突'):
        parse_choice('{"action":"relocate","object_id":"bowl","destination":"ready","participation":"step_aside"}',
                     {'bowl':[]},{'ready':[]},schema_version=2)


def test_pick_is_continuous_and_writes_only_human_held_object():
    actor=object.__new__(KinematicHuman)
    data=SimpleNamespace(time=0.,qpos=np.zeros(20),qvel=np.zeros(20),ctrl=np.zeros(3))
    data.qpos[:3]=[0,0,1.06];data.qpos[6:9]=[0,0,1.]
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=data),env=SimpleNamespace(object_states_dict={}))
    actor.qidx=[0,1,2];actor.didx=[0,1,2];actor.actuators=[0,1,2]
    actor.body_base=np.array([.25,.6]);actor.body_target=actor.body_base.copy();actor.body_velocity=np.zeros(2)
    actor.reference=data.qpos[:3].copy();actor.velocity=np.zeros(3);actor.dt=.002;actor.motion_speed=.2
    actor.target=actor.reference.copy();actor.phase='pick_approach';actor.object_id='bowl';actor.held=None
    actor.offset=None;actor.object_q={'bowl':(6,6)};actor.avatar=None;actor.physics_steps=0
    actor.records=[];actor.completed_requests=[];actor.active_request=0
    actor.object_position=lambda n:data.qpos[6:9].copy();actor._display=lambda p:None
    robot_before=data.qpos[13:].copy()
    actor.physics_step()
    assert actor.held=='bowl'
    np.testing.assert_allclose(data.qpos[6:9],[0,0,1.])
    for _ in range(100):actor.physics_step();data.time+=actor.dt
    assert 1.<data.qpos[8]<1.04
    np.testing.assert_array_equal(data.qpos[13:],robot_before)
    assert all(r['human_attached_object_pose_write']=='bowl' and r['robot_pose_writes']==0 for r in actor.records)
