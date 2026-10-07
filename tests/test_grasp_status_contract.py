from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

from hrc_pilot.native_contact_human import NativeContactHuman
from hrc_pilot.native_articulated_hand import NativeArticulatedHuman


def test_secured_grasp_is_not_reported_as_unfinished_grasp_request():
    hand=object.__new__(NativeArticulatedHuman)
    hand.env=SimpleNamespace(sim=SimpleNamespace(data=SimpleNamespace(qpos=np.zeros(3))),
                             env=SimpleNamespace(objects_dict={'plate':None}))
    hand.finger_q=[0,1];hand.yaw_q=2;hand.carry_object='plate';hand.motor_failure=None
    hand.object_id=None;hand.accepted_intent='grasp';hand.finger_contacts=lambda name=None:[True,True]
    with patch.object(NativeContactHuman,'public_feedback',return_value={'status':'running'}):
        feedback=hand.public_feedback()
    assert feedback['status']=='grasp_secured' and feedback['object_measured_in_hand']=='plate'
    assert 'next_action' not in feedback and 'task_success' not in feedback
