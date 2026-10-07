from types import SimpleNamespace
import numpy as np

from hrc_pilot.kinematic_human import KinematicHuman


def make_actor(auto_buffer):
    actor=object.__new__(KinematicHuman)
    data=SimpleNamespace(time=0.,qpos=np.zeros(32),qvel=np.zeros(32),ctrl=np.zeros(3),ncon=0)
    data.qpos[:3]=[0,0,1.12];data.qpos[6:9]=[0,0,1.06];data.qpos[9]=1
    data.qpos[13:16]=[.12,.1,1.];data.qpos[16]=1;data.qpos[20:]=.7
    actor.env=SimpleNamespace(sim=SimpleNamespace(data=data),env=SimpleNamespace(object_states_dict={}))
    actor.qidx=[0,1,2];actor.didx=[0,1,2];actor.actuators=[0,1,2]
    actor.body_base=np.array([.25,.6]);actor.body_target=actor.body_base.copy();actor.body_velocity=np.zeros(2)
    actor.reference=data.qpos[:3].copy();actor.velocity=np.zeros(3);actor.dt=.002;actor.motion_speed=.2
    actor.target=actor.reference.copy();actor.phase='idle';actor.object_id='plate';actor.held='plate'
    actor.offset=np.array([0.,0.,-.06]);actor.object_q={'plate':(6,6),'cream':(13,13)}
    actor.avatar=None;actor.physics_steps=0;actor.last_request=None;actor.auto_buffer=auto_buffer
    actor.records=[];actor.receipts=[];actor.completed_requests=[];actor.active_request=None
    actor.regions={'plate_personal':(.2,.3,1.),'drawer':(.05,-.1,1.)}
    actor.carried_offsets={'plate':actor.offset.copy()};actor.carried_quaternions={'plate':np.array([1,0,0,0])}
    actor.object_position=lambda n:data.qpos[actor.object_q[n][0]:actor.object_q[n][0]+3].copy()
    actor._display=lambda p:None;actor.transfer_destination=None
    return actor,data


def test_single_selected_contribution_buffers_owned_item_continuously_without_selecting_next_task():
    actor,data=make_actor(True);robot=data.qpos[20:].copy()
    choice={'action':'relocate','object_id':'cream','destination':'drawer'}
    actor.accept_choice(choice,1)
    assert actor.phase=='buffer_owned_object' and actor.object_id=='cream'
    assert actor.receipts[-1]['automatic_buffer']['owned_object']=='plate'
    first_plate=data.qpos[6:9].copy();actor.physics_step();data.time+=actor.dt
    assert np.linalg.norm(data.qpos[6:9]-first_plate)<.001
    for i in range(20000):
        if i==100:actor.accept_choice(choice,2)
        actor.physics_step();data.time+=actor.dt
        if actor.phase=='idle':break
    assert actor.completed_requests==[1] and actor.held is None
    np.testing.assert_allclose(data.qpos[6:9],[.2,.3,1.],atol=.0041)
    np.testing.assert_allclose(data.qpos[13:16],[.05,-.1,1.],atol=.0041)
    np.testing.assert_array_equal(data.qpos[20:],robot)
    assert all(np.linalg.norm(r['hand_velocity'])<=.200001 and r['robot_pose_writes']==0 for r in actor.records)
    assert set(x for r in actor.records for x in r['human_carried_object_pose_writes'])=={'plate','cream'}


def test_buffer_is_explicitly_optional_and_requires_a_known_public_location():
    actor,_=make_actor(False)
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer'},1)
    assert actor.receipts[-1]['error']=='holding_a_different_object'
    actor,_=make_actor(True);actor.regions.pop('plate_personal')
    actor.accept_choice({'action':'relocate','object_id':'cream','destination':'drawer'},1)
    assert actor.receipts[-1]['error']=='no_public_buffer_for_owned_object'
