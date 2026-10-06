import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import replace
import json

from hrc_pilot.native_articulated_hand import install_articulated_hand
from hrc_pilot.native_hand_policy import ArticulatedAutonomousHuman
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.protocol import Observation


def test_hand_uses_joint_motors_and_contact_geoms_without_object_binding():
    root=ET.fromstring('<mujoco><worldbody><body name="human_slide_x"><joint/><inertial/><body name="human_slide_y"><joint/><inertial/><body name="human_slide_z"><joint/><inertial/><body name="human_fingertip"><geom type="sphere" size=".015"/></body></body></body></body></worldbody><actuator/></mujoco>')
    install_articulated_hand(root)
    assert len(root.findall('.//joint'))==6
    assert len(root.findall('.//motor'))==3
    assert not root.findall('.//weld') and not root.findall('.//equality')
    assert root.find(".//joint[@name='human_left_finger']").get('range')=='0 .095'


def test_place_requires_measured_holding_not_generated_claim():
    p=ArticulatedAutonomousHuman(replace(CONTINUOUS_SCENARIOS['relay'],tick_hz=20),autonomous_context='snack_storage',model_path=Path('/unused'),
        generator=lambda _:json.dumps({'intent':'place','object_id':'cookie','destination':'shelf','current_goal':'我已拿着cookie','personal_targets':[],'long_term_intention':'收纳'}))
    p.reset(0);o=Observation(objects={'cookie':(0,0,.9)},regions={'shelf':(.1,.1,1.)},messages=(),robot_ee=(0,0,1.),human_position=(0,.6,0),held_by_human=(),completed_skills=(),human_execution={'object_measured_in_hand':None})
    output=p.step(o)
    assert output.command.intent=='observe'
    assert p.last_command_feedback['errors']==['requested_object_not_in_measured_hand']


def test_holding_feedback_does_not_turn_past_grasp_into_current_contact():
    from types import SimpleNamespace
    from unittest.mock import patch
    import numpy as np
    from hrc_pilot.native_contact_human import NativeContactHuman
    from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
    hand=object.__new__(NativeArticulatedHuman)
    hand.env=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(qpos=np.zeros(3))))
    hand.finger_q=[0,1];hand.yaw_q=2;hand.carry_object='cookies_1';hand.motor_failure=None;hand.object_id=None
    hand.finger_contacts=lambda name=None:[False,False]
    with patch.object(NativeContactHuman,'public_feedback',return_value={}):feedback=hand.public_feedback()
    assert feedback['object_measured_in_hand'] is None
    assert feedback['last_confirmed_grasp_object']=='cookies_1'


def test_repeated_grasp_retargets_moved_object_during_approach():
    from types import SimpleNamespace
    import numpy as np
    from hrc_pilot.continuous import HumanCommand
    from hrc_pilot.native_articulated_hand import NativeArticulatedHuman
    hand=object.__new__(NativeArticulatedHuman)
    hand.signature=('grasp','cookie',None);hand.phase='grasp_approach';hand.grasp_initial_object=np.array([0,0,.91])
    hand.object_position=lambda _:np.array([.10,0,.91]);hand.carry_object=None;hand.surface_z=.9;hand.geom=0
    hand.position=lambda:np.array([0,0,1.1])
    model=SimpleNamespace(geom_contype=np.ones(1),geom_conaffinity=np.ones(1),geom_name2id=lambda _:0,
                          geom_type=np.array([6]),geom_size=np.array([[.02,.03,.01]]))
    data=SimpleNamespace(time=1.,body_xmat=np.eye(3).reshape(1,9),geom_xmat=np.eye(3).reshape(1,9),geom_xpos=np.array([[.10,0,.91]]))
    hand.env=SimpleNamespace(sim=SimpleNamespace(model=model,data=data),env=SimpleNamespace(obj_body_id={'cookie':0},objects_dict={'cookie':SimpleNamespace(contact_geoms=['cookie_geom'])}))
    hand.accept(HumanCommand('grasp','cookie'))
    np.testing.assert_allclose(hand.target[:2],[.10,0])
    np.testing.assert_allclose(hand.grasp_initial_object,[.10,0,.91])
    assert hand.phase=='grasp_approach'
