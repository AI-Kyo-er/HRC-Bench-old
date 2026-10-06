import numpy as np
from types import SimpleNamespace

from hrc_pilot.human_contact import bounded_motion, HumanContactExecutor
from hrc_pilot.continuous import HumanCommand


def test_approach_respects_speed_and_acceleration_to_the_endpoint():
    position = np.zeros(3)
    velocity = np.zeros(3)
    target = np.array([0.5, 0.2, 0.1])
    for _ in range(600):
        previous_velocity = velocity.copy()
        previous_position = position.copy()
        position, velocity = bounded_motion(position, velocity, target, dt=1/60, speed=0.4, acceleration=0.9)
        assert np.linalg.norm(position - previous_position) <= 0.4/60 + 1e-9
        assert np.linalg.norm(velocity - previous_velocity) <= 0.9/60 + 1e-9
    assert np.linalg.norm(position - target) < 0.001


def test_retargeting_does_not_move_the_hand_in_one_step():
    position = np.array([0.3, 0.1, 1.0])
    velocity = np.array([0.25, 0, 0])
    target = np.array([-0.5, 0.8, 0.9])
    updated, next_velocity = bounded_motion(position, velocity, target, dt=1/60, speed=0.4, acceleration=0.9)
    assert np.linalg.norm(updated - position) <= 0.4/60
    assert np.linalg.norm(next_velocity - velocity) <= 0.9/60 + 1e-9
    np.testing.assert_array_equal(target, [-0.5, 0.8, 0.9])


class ArrayTensor:
    def __init__(self, array):
        self.array = np.asarray(array)

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array.copy()


def active_executor():
    executor = HumanContactExecutor.__new__(HumanContactExecutor)
    executor.phase = "carry"
    executor.fingers = 0.0
    executor.object_id = "blue"
    executor.destination = "tray_blue"
    executor.hand = SimpleNamespace(get_qpos=lambda: ArrayTensor([0.4, 0.2, 1.0, 0.02, 0.02]))
    executor.workspace = SimpleNamespace(held_by_human=lambda: ("blue",), step_count=12, monitor_active=False,
                                         objects={"blue": object()},
                                         avatar=SimpleNamespace(robot=SimpleNamespace(global_trans=np.array([0.5, 0.8, 0]))))
    return executor


def test_generated_observe_interrupts_active_manipulation():
    executor = active_executor()
    executor.accept(HumanCommand("observe"))
    assert executor.phase == "paused"
    assert executor.suspended_phase == "carry"
    np.testing.assert_array_equal(executor.target, [0.4, 0.2, 1.0])
    assert executor.fingers == 0.0


def test_generated_away_navigates_with_physically_held_object():
    executor = active_executor()
    executor.accept(HumanCommand("away", target=(0.5, 0.9, 0)))
    assert executor.phase == "navigate_holding"
    assert executor.fingers == 0.0
    np.testing.assert_array_equal(executor.body_target, [0.5, 0.9])
    executor.accept(HumanCommand("carry", "blue", "tray_blue"))
    assert executor.phase == "carry"


def test_new_intent_waits_for_physical_release_clearance():
    executor = active_executor()
    executor.phase = "release"
    executor.command = HumanCommand("carry", "blue", "tray_blue")
    next_intent = HumanCommand("approach", "red", "tray_red")
    executor.accept(next_intent)
    assert executor.phase == "release"
    assert executor.object_id == "blue"
    assert executor.destination == "tray_blue"
    assert executor.pending_command is next_intent
    assert executor.command.object_id == "blue"
