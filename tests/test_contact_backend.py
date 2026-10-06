from types import SimpleNamespace

import numpy as np
import pytest

from hrc_pilot.backend import VCWorkspace
from hrc_pilot.contact_backend import ContactWorkspace
from hrc_pilot.continuous import CONTINUOUS_SCENARIOS
from hrc_pilot.protocol import Action, EventLog


class ObjectBody:
    def __init__(self):
        self.position = np.array([0.35, -0.08, 0.81])
        self.velocity = np.zeros(3)
        self.links = [4]

    def get_contacts(self):
        return {"link_a": np.array([30] * len(self.links)), "link_b": np.array(self.links),
                "force_a": np.array([[0, 0, 1.0]] * len(self.links)).reshape(-1, 3)}

    def get_pos(self):
        return self.position

    def get_vel(self):
        return self.velocity

    def set_pos(self, _):
        raise AssertionError("监测器不得移动物体")


def make_workspace():
    workspace = ContactWorkspace.__new__(ContactWorkspace)
    workspace.monitor_active = True
    workspace.objects = {"blue": ObjectBody()}
    workspace.finger_links = {20, 21}
    workspace.support_links = {4, 5}
    workspace.initial_physical_positions = {"blue": [0.35, -0.08, 0.81]}
    workspace.held_by_human = lambda: ()
    workspace.contact_records = []
    workspace.control_records = []
    workspace.contact_grasps = set()
    workspace.stable_placements = {}
    workspace.last_placement = {}
    workspace.completed_skills = []
    workspace.regions = {"tray_blue": [0.42, -0.30, 0.82]}
    workspace.scenario = CONTINUOUS_SCENARIOS["concurrent_overlay"]
    workspace.step_count = 0
    workspace.log = EventLog()
    workspace.messages = []
    return workspace


def step(workspace, count=1):
    for _ in range(count):
        workspace._after_physics_step()
        workspace.step_count += 1


def test_contacts_and_lift_required_before_physical_placement():
    workspace = make_workspace()
    body = workspace.objects["blue"]
    body.position = np.array([0.42, -0.30, 0.81])
    step(workspace, 30)
    assert not workspace.completed_skills
    body.links = [20, 21]
    body.position = np.array([0.35, -0.08, 0.95])
    step(workspace)
    assert workspace.contact_grasps == {"blue"}
    body.links = [4]
    body.position = np.array([0.42, -0.30, 0.81])
    step(workspace, 23)
    assert not workspace.completed_skills
    step(workspace)
    assert workspace.completed_skills == ["robot:blue:tray_blue"]
    assert workspace.log.events[-1]["source"] == "friction_contact"


@pytest.mark.parametrize("invalid", ["one_finger", "no_lift", "still_held", "moving", "unsupported"])
def test_invalid_contact_states_cannot_commit(invalid):
    workspace = make_workspace()
    body = workspace.objects["blue"]
    body.position[2] = 0.81 if invalid == "no_lift" else 0.95
    body.links = [20] if invalid == "one_finger" else [20, 21]
    step(workspace)
    body.position = np.array([0.42, -0.30, 0.81])
    body.links = [20, 21] if invalid == "still_held" else [] if invalid == "unsupported" else [4]
    body.velocity = np.array([0.1, 0, 0]) if invalid == "moving" else np.zeros(3)
    step(workspace, 30)
    assert not workspace.completed_skills


def test_contact_control_records_requested_and_speed_limited_targets():
    workspace = make_workspace()
    applied = []
    workspace.previous_control = np.zeros(9)
    workspace.robot = SimpleNamespace(control_dofs_position=lambda q: applied.append(q.copy()))
    workspace._control_robot_position(np.ones(9))
    np.testing.assert_allclose(applied[0][:7], 1.2 / 60)
    np.testing.assert_allclose(applied[0][-2:], 0.04 / 60)
    assert workspace.control_records[0]["requested_target"] == [1.0] * 9
    assert workspace.control_records[0]["rate_limited"]


def test_semantic_transfer_and_geometric_attachment_are_disabled():
    workspace = make_workspace()
    with pytest.raises(ValueError, match="只接受关节动作"):
        workspace.continuous_start_action(Action("transfer", "blue", "tray_blue"))
    workspace._continuous_joint_grasp()
    assert not hasattr(workspace, "attachment")


def test_blocked_placement_cannot_be_retroactively_credited_after_prerequisite():
    workspace = make_workspace()
    workspace.scenario = CONTINUOUS_SCENARIOS["relay"]
    body = workspace.objects["blue"]
    body.links = [20, 21]
    body.position[2] = 0.95
    step(workspace)
    body.links = [4]
    body.position = np.array([0.42, -0.30, 0.81])
    step(workspace, 24)
    assert "robot:blue:tray_blue" not in workspace.completed_skills
    assert workspace.messages[-1].speaker == "environment"
    workspace.completed_skills.append("human:red:tray_red")
    step(workspace, 30)
    assert "robot:blue:tray_blue" not in workspace.completed_skills
    body.links = [20, 21]
    body.position[2] = 0.95
    step(workspace)
    body.links = [4]
    body.position[2] = 0.81
    step(workspace, 24)
    assert "robot:blue:tray_blue" in workspace.completed_skills
