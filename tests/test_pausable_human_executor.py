import numpy as np

from hrc_pilot.pausable_human_executor import PausableHumanExecutor
from hrc_pilot.tool_joint_human import execution_tool_result
from test_human_owned_buffer import make_actor


def test_explicit_pause_cancels_own_transfer_without_release_or_robot_pose_change():
    actor,data=make_actor(True);actor.__class__=PausableHumanExecutor;actor.cancelled_requests=[]
    actor.phase='transfer_raise';actor.active_request=2;actor.transfer_destination='drawer';robot=data.qpos[20:].copy()
    actor.accept_choice({'action':'pause_current','message':'I will stop.'},3)
    assert actor.phase=='idle' and actor.held=='plate' and actor.cancelled_requests==[2]
    assert actor.completed_requests==[3] and actor.transfer_destination is None
    np.testing.assert_array_equal(data.qpos[20:],robot)
    feedback=actor.public_feedback()
    reply=execution_tool_result(3,{'time_s':4.,'own_execution':feedback,'measured_world':{}})
    assert reply['cancelled_request_ids']==[2] and reply['held_object']=='plate'
    assert 2 not in reply['completed_request_ids']
