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
