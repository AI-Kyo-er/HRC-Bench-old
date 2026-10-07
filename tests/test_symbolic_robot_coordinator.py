import json
from types import SimpleNamespace

import pytest

from hrc_pilot.symbolic_robot_coordinator import SymbolicRobotCoordinator,PUBLIC_FIELDS


def test_ideal_perception_is_explicit_and_private_fields_cannot_leak():
    seen=[]
    def generate(system,prompt):
        seen.append(json.loads(prompt));return '{"mode":"execute","instruction":"open the middle drawer","message":"I will open it."}'
    robot=SymbolicRobotCoordinator(SimpleNamespace(model_path='/local/model'),generator=generate)
    request={k:{} for k in PUBLIC_FIELDS};request['observed_world']={'drawer':{'opening_m':0}}
    assert robot.infer(request)['decision']['mode']=='execute'
    assert seen[0]['observed_world']['drawer']['opening_m']==0
    assert robot.metadata['perception']=='ideal_observable_geometry'
    with pytest.raises(ValueError):robot.infer({**request,'private_human_intention':'store'})


def test_moving_without_vla_is_not_silently_treated_as_manipulation():
    robot=SymbolicRobotCoordinator(SimpleNamespace(model_path='/unused'),
        generator=lambda s,p:'{"mode":"move_ee","delta_xyz_m":[0,0,0.1]}')
    result=robot.infer({k:{} for k in PUBLIC_FIELDS})
    assert result['parse_error']=='unsupported_direct_motion' and result['decision']['mode']=='hold'
