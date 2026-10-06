import numpy as np
import pytest

from hrc_pilot.openvla_native_policy import libero_gripper


def test_openvla_gripper_matches_upstream_libero_sign_convention():
    close=libero_gripper([.1,.2,.3,.4,.5,.6,0])
    opened=libero_gripper([.1,.2,.3,.4,.5,.6,1])
    assert close[-1]==1 and opened[-1]==-1
    np.testing.assert_array_equal(close[:6],[.1,.2,.3,.4,.5,.6])


def test_openvla_invalid_native_action_is_rejected():
    with pytest.raises(ValueError):libero_gripper([0]*6)
    with pytest.raises(ValueError):libero_gripper([0]*6+[np.nan])
