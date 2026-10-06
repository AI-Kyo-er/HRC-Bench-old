from dataclasses import replace
import json

import numpy as np
import torch

from hrc_pilot.cartesian_vla_adapter import CartesianVLAAdapter
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS, ContinuousWorld
from hrc_pilot.protocol import serialize


def test_cartesian_model_rotation_and_translation_are_preserved_without_object_query():
    class Link:
        def get_quat(self):return torch.tensor([1.,0,0,0])
    class Robot:
        def get_link(self,_):return Link()
        def inverse_kinematics(self,**kwargs):self.target=kwargs;return torch.zeros(9)
    robot=Robot();requests=[]
    def infer(value):requests.append(value);return {'actions':np.array([[1,0,0,0,0,1,1]],np.float32)}
    obs=ContinuousWorld(CONTINUOUS_SCENARIOS['relay']).observe()
    obs=replace(obs,robot_ee=(.4,0,.9),robot_qpos=(0,)*7+(.04,.04),
                rgb=np.zeros((4,4,3),np.uint8),wrist_rgb=np.zeros((4,4,3),np.uint8))
    policy=CartesianVLAAdapter(infer,lambda:robot,instruction='Public operation')
    action=policy.act(obs)
    np.testing.assert_allclose(robot.target['pos'],[.45,0,.9])
    np.testing.assert_allclose(robot.target['quat'],[np.cos(.25),0,0,np.sin(.25)])
    np.testing.assert_allclose(requests[0]['observation/state'],[-.16,0,1.0034,0,0,0,.04,-.04])
    assert set(requests[0])=={'observation/image','observation/wrist_image','observation/state','prompt'}
    assert action.joints[-2:]==(0,0)
    json.dumps(serialize(action))
