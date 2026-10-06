"""核查 DROID 标度、双相机边界和几何抓取范围。"""
from dataclasses import replace

import numpy as np
import pytest

from hrc_pilot.continuous import ContinuousWorld, CONTINUOUS_SCENARIOS
from hrc_pilot.openpi_adapter import DroidVLAAdapter
from hrc_pilot.protocol import Message
from hrc_pilot.robot_control import droid_action_to_joint_target, hand_rotation, select_grasp_candidate


def test_droid_normalized_velocity_is_not_an_absolute_joint_target():
    qpos = np.array([0, -0.5, 0, -2.1, 0, 1.6, 0.8, 0.04, 0.04])
    target = droid_action_to_joint_target([0.5] * 7 + [1], qpos)
    np.testing.assert_allclose(target[:7], qpos[:7] + 0.1)
    assert target[-2:] == (0, 0)
    opened = droid_action_to_joint_target([0] * 8, qpos)
    np.testing.assert_allclose(opened, qpos)


def test_grasp_selection_requires_nearness_and_excludes_human_holding():
    positions = {"near": [0.01, 0, 0], "far": [0.3, 0, 0]}
    assert select_grasp_candidate(np.zeros(3), positions) == "near"
    assert select_grasp_candidate(np.zeros(3), positions, excluded=("near",)) is None
    np.testing.assert_allclose(hand_rotation([0, 1, 0, 0]) @ [0, 0, 0.1], [0, 0, -0.1])


def test_native_vla_receives_only_two_images_proprioception_and_public_language():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    observation = replace(observation, rgb=np.full((4, 5, 3), 123, dtype=np.uint8),
                          wrist_rgb=np.full((4, 5, 3), 65, dtype=np.uint8),
                          robot_qpos=(0, -0.5, 0, -2.1, 0, 1.6, 0.8, 0.04, 0.04))
    calls = []

    def infer(request):
        calls.append(request)
        return {"actions": np.zeros((15, 8))}

    policy = DroidVLAAdapter(infer, execution_horizon=2)
    for tick in range(3):
        policy.act(replace(observation, time_s=tick / 15))
    assert len(calls) == 2
    assert set(calls[0]) == {"observation/exterior_image_1_left", "observation/wrist_image_left",
                             "observation/joint_position", "observation/gripper_position", "prompt"}
    np.testing.assert_array_equal(calls[0]["observation/wrist_image_left"], observation.wrist_rgb)
    calls[0]["observation/exterior_image_1_left"][0, 0, 0] = 0
    assert observation.rgb[0, 0, 0] == 123
    with pytest.raises(ValueError, match="15"):
        policy.act(replace(observation, time_s=0.5))


def test_public_correction_discards_cached_action_chunk():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    observation = replace(observation, rgb=np.zeros((4, 4, 3), dtype=np.uint8),
                          wrist_rgb=np.zeros((4, 4, 3), dtype=np.uint8), robot_qpos=(0,) * 9)
    calls = []
    policy = DroidVLAAdapter(lambda request: calls.append(request) or {"actions": np.zeros((15, 8))})
    policy.act(observation)
    policy.act(replace(observation, time_s=1/15, messages=(Message("human", "correction", "不要拿蓝杯"),)))
    assert len(calls) == 2
    assert "不要拿蓝杯" in calls[-1]["prompt"]


def test_single_camera_cannot_be_silently_substituted_for_wrist_view():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    observation = replace(observation, rgb=np.zeros((4, 4, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="双相机"):
        DroidVLAAdapter(lambda _: None).act(observation)


def test_initial_assignment_is_deduplicated_but_later_assignment_remains_public():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    initial = Message("human", "assignment", "请你处理 blue，目标是 tray_blue。", "blue", "robot", "tray_blue")
    later = Message("human", "assignment", "现在请处理绿色", "green", "robot", "tray_green")
    observation = replace(observation, rgb=np.zeros((4, 4, 3), dtype=np.uint8),
                          wrist_rgb=np.zeros((4, 4, 3), dtype=np.uint8), robot_qpos=(0,) * 9,
                          messages=(initial,))
    calls = []
    policy = DroidVLAAdapter(lambda request: calls.append(request) or {"actions": np.zeros((15, 8))},
                            instruction="Pick up the blue block.")
    policy.act(observation)
    assert calls[0]["prompt"] == "Pick up the blue block."
    policy.act(replace(observation, time_s=1/15, messages=(initial, later)))
    assert "现在请处理绿色" in calls[1]["prompt"]


def test_initial_assignment_with_extra_public_constraint_is_retained():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    constraint = "请你处理 blue，目标是 tray_blue。 前置贡献完成后再接手（human:red:tray_red）。"
    observation = replace(observation, rgb=np.zeros((4, 4, 3), dtype=np.uint8),
                          wrist_rgb=np.zeros((4, 4, 3), dtype=np.uint8), robot_qpos=(0,) * 9,
                          messages=(Message("human", "assignment", constraint, "blue", "robot", "tray_blue"),))
    calls = []
    policy = DroidVLAAdapter(lambda request: calls.append(request) or {"actions": np.zeros((15, 8))},
                            instruction="Pick up the blue block.")
    policy.act(observation)
    assert constraint in calls[0]["prompt"]


def test_position_model_output_is_absolute_and_uses_continuous_gripper():
    observation = ContinuousWorld(CONTINUOUS_SCENARIOS["relay"]).observe()
    observation = replace(observation, rgb=np.zeros((4, 4, 3), dtype=np.uint8),
                          wrist_rgb=np.zeros((4, 4, 3), dtype=np.uint8), robot_qpos=(1,) * 9)
    raw = np.array([[0.3] * 7 + [0.75]])
    policy = DroidVLAAdapter(lambda _: {"actions": raw}, action_encoding="joint_position")
    action = policy.act(observation)
    np.testing.assert_allclose(action.joints, [0.3] * 7 + [0.01, 0.01])
    assert action.control_mode == "learned_absolute_joint_position"
    assert policy.audit_record()['action_scale_rad_per_step'] is None
