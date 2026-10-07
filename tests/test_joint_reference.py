from types import SimpleNamespace
import json

import numpy as np

from hrc_pilot.joint_activity import ACTIVITIES
from hrc_pilot.joint_reference import JointReference
from hrc_pilot.joint_human_policy import JointHumanPolicy
from hrc_pilot.joint_world import observable_world,actual_robot_execution,drawer_support
from hrc_pilot.kinematic_human import KinematicHuman


def test_reference_waits_for_real_human_completion_and_robot_contribution():
    r=JointReference(ACTIVITIES['snack_service'])
    scene={'time_s':0,'own_execution':{'completed_requests':[]}}
    first=r.decide(scene,False)
    assert first['choice']['action']=='relocate' and not r.robot_permission
    assert r.decide({**scene,'time_s':2},False)['choice']['action']=='wait'
    scene={'time_s':12,'own_execution':{'completed_requests':[0]}}
    assert r.decide(scene,False)['reference_stage']=='robot' and r.robot_permission
    after=r.decide({**scene,'time_s':20},True)
    assert after['choice']['destination']=='snack_delivery' and after['neural_inferences']==0


def test_reflection_is_actual_second_generation_bound_to_measurement():
    prompts=[]
    def generate(prompt):
        prompts.append(json.loads(prompt))
        return '{"action":"message","message":"Please wait.","reason":"No manipulation observed"}'
    h=JointHumanPolicy(ACTIVITIES['snack_service'],model_path='/unused',generator=generate,reflection=True)
    scene={'time_s':0.,'objects_xyz':{},'regions_xyz':{},'measured_world':{'object_contacts':{}}}
    result=h.decide(scene)
    assert len(prompts)==2 and result['neural_inferences']==2
    assert prompts[1]['scene']==scene and prompts[1]['candidate_choice_to_review']==result['candidate_raw_output']
    assert result['reflection_input']==prompts[1]


def test_observations_do_not_invent_robot_manipulation_or_read_scores():
    record={'objects':{'cream_cheese_1':[0,0,1],'akita_black_bowl_1':[.3,0,1]},
            'robot_qpos':[0]*7+[.03,-.03],'robot_ee':[0,0,1],'contacts':[],'task_success':True}
    world=observable_world(record,{'serving_ready':(.3,0,1)})
    assert world['relative_object_positions']['cream_cheese_1_to_akita_black_bowl_1']['xy_distance_m']==.3
    assert 'task_success' not in world
    execution=actual_robot_execution(record,[{'action_source':'coordinator_selected_hold'}],[])
    assert execution['actual_vla_blocks']==0 and execution['gripper_contact_objects']==[]


def test_drawer_support_requires_real_bottom_contact_and_release_not_merely_proximity():
    record={'objects':{'cream_cheese_1':[.03,-.10,1.003], 'wooden_cabinet_1':[.03,-.25,.905]},
        'robot_qpos':[0]*9,'contacts':[{'geom1':'cream_cheese_1_g1','geom2':'wooden_cabinet_1_g27'}],
        'human_execution':{'held_object':None}}
    drawer={'support_xyz':[.03,-.10,.994], 'geometry_source':'wooden_cabinet_1_g27',
            'opening_m':.16,'placement_accessible':True}
    regions={'drawer_storage':(.03,-.10,1.021)}
    def measured():return observable_world(record,regions,drawer)['released_object_support_contacts']['cream_cheese_1']
    assert measured()==['middle_drawer_bottom']
    legacy=observable_world(record,regions,drawer,measurement_version=1)
    assert legacy['released_object_support_contacts']['cream_cheese_1']==[] and 'measurement_version' not in legacy
    record['human_execution']['held_object']='cream_cheese_1'
    assert measured()==[]
    record['human_execution']['held_object']=None
    record['contacts'][0]['geom2']='wooden_cabinet_1_side'
    assert measured()==[]
    record['contacts']=[]
    assert measured()==[]


def test_relocate_finishes_one_selected_contribution_and_keeps_robot_positions():
    actor=object.__new__(KinematicHuman)
    data=SimpleNamespace(time=0.,qpos=np.zeros(24),qvel=np.zeros(24),ctrl=np.zeros(3),ncon=0)
    data.qpos[:3]=[0,0,1.06];data.qpos[6:9]=[0,0,1.];data.qpos[9]=1
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=data),env=SimpleNamespace(object_states_dict={}))
    actor.qidx=[0,1,2];actor.didx=[0,1,2];actor.actuators=[0,1,2]
    actor.body_base=np.array([.25,.6]);actor.body_target=actor.body_base.copy();actor.body_velocity=np.zeros(2)
    actor.reference=data.qpos[:3].copy();actor.velocity=np.zeros(3);actor.dt=.002;actor.motion_speed=.2
    actor.target=actor.reference.copy();actor.phase='idle';actor.object_id=None;actor.held=None
    actor.offset=None;actor.object_q={'bowl':(6,6)};actor.avatar=None;actor.physics_steps=0;actor.last_request=None
    actor.records=[];actor.receipts=[];actor.completed_requests=[];actor.active_request=None
    actor.regions={'ready':(.1,.1,1.)};actor.carried_offsets={};actor.carried_quaternions={}
    actor.object_position=lambda n:data.qpos[6:9].copy();actor._display=lambda p:None
    robot=data.qpos[13:].copy()
    actor.accept_choice({'action':'relocate','object_id':'bowl','destination':'ready'},0)
    for _ in range(12000):
        actor.physics_step();data.time+=actor.dt
        if actor.phase=='idle':break
    assert actor.completed_requests==[0] and actor.held is None
    np.testing.assert_allclose(data.qpos[6:9],[.1,.1,1.],atol=.0041)
    np.testing.assert_array_equal(data.qpos[13:],robot)
    assert all(np.linalg.norm(r['hand_velocity'])<=.200001 for r in actor.records)
