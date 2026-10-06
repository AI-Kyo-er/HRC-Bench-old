import json

import numpy as np
from PIL import Image

from experiments.continuous_v2.physical_frame_dataset import (PhysicalFrameDataset, export_physical_frames,
                                                            export_applied_position_frames)


def test_loader_matches_stems_and_never_crosses_episode_boundary(tmp_path):
    for name in ("episode_a", "episode_b"):
        directory = tmp_path / "train" / name
        directory.mkdir(parents=True)
        (directory / "public_task.txt").write_text("Pick up the blue block.")
        for step in (0, 4):
            stem = f"observation_{step:06d}_{step + 1:06d}"
            Image.fromarray(np.full((3, 4, 3), 10, dtype=np.uint8)).save(directory / (stem + ".png"))
            Image.fromarray(np.full((3, 4, 3), 20, dtype=np.uint8)).save(directory / (stem + "_wrist.png"))
            np.save(directory / (stem + ".state.npy"), np.arange(8, dtype=np.float32))
            np.save(directory / (stem + ".action.npy"), np.full(8, step / 10, dtype=np.float32))
    dataset = PhysicalFrameDataset(tmp_path, action_horizon=3)
    assert len(dataset) == 4
    first, last = dataset[0], dataset[1]
    assert first["observation/exterior_image_1_left"][0, 0, 0] == 10
    assert first["observation/wrist_image_left"][0, 0, 0] == 20
    np.testing.assert_array_equal(first["action_valid"], [True, True, False])
    np.testing.assert_array_equal(last["action_valid"], [True, False, False])
    assert not (tmp_path / "manifest.json").exists()


def test_export_uses_executed_motion_rather_than_requested_ik_jump(tmp_path):
    current = np.zeros(9)
    current[-2:] = 0.04
    next_pose = current.copy()
    next_pose[0] = 0.02
    requested = current.copy()
    requested[0] = 0.75
    requested[-2:] = 0
    stem = "observation_000000_000001"
    (tmp_path / "policy_io.jsonl").write_text(json.dumps({
        "observation": {"time_s": 0, "robot_qpos": current.tolist(), "rgb_artifact": stem + ".png"},
        "action": {"joints": requested.tolist()},
    }))
    np.savez(tmp_path / "trajectory.npz", step=np.array([0, 4]), qpos=np.stack([current, next_pose]))
    assert export_physical_frames(tmp_path, "Pick up the blue block.") == 1
    action = np.load(tmp_path / (stem + ".action.npy"))
    assert np.isclose(action[0], 0.1)
    assert action[-1] == 1
    assert np.load(tmp_path / (stem + ".state.npy"))[-1] == 0


def test_position_target_uses_last_applied_controller_request_and_preserves_original(tmp_path):
    stem = "observation_000000_000001"
    original = np.arange(8, dtype=np.float32)
    np.save(tmp_path / (stem + ".action.npy"), original)
    (tmp_path / "policy_io.jsonl").write_text(json.dumps({
        "observation": {"time_s": 0, "rgb_artifact": stem + ".png"},
    }))
    controls = [{"physics_step": step, "applied_target": [0.02 * (step + 1)] + [0] * 6 + [0.02, 0.02]}
                for step in range(4)]
    (tmp_path / "robot_control.jsonl").write_text("\n".join(json.dumps(row) for row in controls))
    assert export_applied_position_frames(tmp_path) == 1
    target = np.load(tmp_path / (stem + ".joint_position.npy"))
    np.testing.assert_allclose(target, [0.08] + [0] * 6 + [0.5])
    np.testing.assert_array_equal(np.load(tmp_path / (stem + ".action.npy")), original)
