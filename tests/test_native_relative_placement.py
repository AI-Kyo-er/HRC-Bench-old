from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json

import numpy as np

from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.native_hand_policy import ArticulatedAutonomousHuman
from hrc_pilot.native_relative_placement import box_vertical_surface, central_support, object_bottom
from hrc_pilot.protocol import Observation


def test_vertical_ray_uses_rotated_box_surface_and_misses_empty_space():
    angle=np.pi/6
    axes=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
    z=box_vertical_surface(np.array([0.,0.,1.]),axes,np.array([.1,.1,.01]),[0.,0.])
    assert np.isclose(z,1.+.01/np.cos(angle))
    assert box_vertical_surface(np.zeros(3),np.eye(3),np.ones(3),[2.,0.]) is None


def test_receiver_support_follows_real_motion_and_payload_origin_is_not_bottom():
    data=SimpleNamespace(body_xpos=np.array([[0.,0.,1.]]),geom_xpos=np.array([[0.,0.,1.02]]),
                         geom_xmat=np.eye(3).reshape(1,9))
    model=SimpleNamespace(geom_name2id=lambda _:0,geom_type=np.array([6]),geom_size=np.array([[.1,.1,.01]]))
    env=SimpleNamespace(env=SimpleNamespace(objects_dict={'bowl':SimpleNamespace(contact_geoms=['base'])},obj_body_id={'bowl':0}),
                        sim=SimpleNamespace(data=data,model=model))
    np.testing.assert_allclose(central_support(env,'bowl'),[0.,0.,1.03])
    assert np.isclose(object_bottom(env,'bowl'),1.01)
    data.body_xpos+=np.array([.2,.3,.1]);data.geom_xpos+=np.array([.2,.3,.1])
    np.testing.assert_allclose(central_support(env,'bowl'),[.2,.3,1.13])
    assert central_support(env,'unknown') is None


def policy(destination):
    p=ArticulatedAutonomousHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='pantry_work',model_path=Path('/unused'),
        generator=lambda _:json.dumps({'intent':'place','object_id':'food','destination':destination,'personal_targets':[],'long_term_intention':'共同用餐'}))
    p.reset(0)
    return p


def observation():
    return Observation(objects={'food':(0.,0.,1.),'bowl':(.2,.1,.9)},regions={'home':(0.,0.,.9)},messages=(),
        robot_ee=(0.,0.,1.),human_position=(0.,.6,0.),held_by_human=(),completed_skills=(),
        human_execution={'object_measured_in_hand':'food','relative_placement_destinations':{'on:bowl':{'support_xyz':[.2,.1,.91]},'on:food':{}}})


def test_relative_place_is_available_only_when_public_geometry_and_holding_exist():
    p=policy('on:bowl');o=observation()
    command=p.step(o).command
    assert command.intent=='place' and command.destination=='on:bowl'
    assert p.last_command_feedback['status']=='accepted'
    assert json.loads(p.policy_io[0]['public_input'].split('\n',1)[1])['action_interface']['relative_placement_destinations']['on:bowl']
    missing=policy('on:missing')
    assert missing.step(o).command.intent=='observe'
    assert missing.last_command_feedback['status']=='rejected'
    self_place=policy('on:food')
    assert self_place.step(o).command.intent=='observe'
    assert 'cannot_place_object_on_itself' in self_place.last_command_feedback['errors']
