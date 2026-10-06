"""实际示范帧的 stem 配对加载器，不使用配对 manifest。

输入 observation_<physics_step>_<index>.png；腕部输入同 stem 加 _wrist，
本体状态同 stem 加 .state.npy；下一控制步目标同 stem 加 .action.npy。
动作块按同一 episode 内的物理时间排序拼接，终态用零速度/打开夹爪补齐。
"""
from pathlib import Path

import numpy as np
from PIL import Image


class PhysicalFrameDataset:
    def __init__(self, root, *, split="train", action_horizon=15, action_encoding="joint_velocity"):
        self.root = Path(root)
        self.action_horizon = action_horizon
        if action_horizon < 1:
            raise ValueError("action_horizon 必须为正整数")
        if action_encoding not in {"joint_velocity", "joint_position"}:
            raise ValueError("未知动作监督编码")
        self.action_suffix = ".action.npy" if action_encoding == "joint_velocity" else ".joint_position.npy"
        self.frames = sorted((self.root / split).rglob("*" + self.action_suffix))
        self.episode_frames = {}
        for path in self.frames:
            self.episode_frames.setdefault(path.parent, []).append(path)
        self.positions = {path: index for paths in self.episode_frames.values() for index, path in enumerate(paths)}

    def __len__(self):
        return len(self.frames)

    def stem(self, path):
        return path.name.removesuffix(self.action_suffix)

    def __getitem__(self, index):
        path = self.frames[index]
        stem = self.stem(path)
        state = np.load(path.with_name(stem + ".state.npy"))
        sequence = self.episode_frames[path.parent]
        cursor = self.positions[path]
        actions = np.zeros((self.action_horizon, 8), dtype=np.float32)
        valid = np.zeros(self.action_horizon, dtype=bool)
        for offset, target in enumerate(sequence[cursor:cursor + self.action_horizon]):
            if offset:
                previous_step = int(self.stem(sequence[cursor + offset - 1]).split("_")[1])
                current_step = int(self.stem(target).split("_")[1])
                if current_step - previous_step != 4:
                    break
            actions[offset] = np.load(target)
            valid[offset] = True
        return {
            "observation/exterior_image_1_left": np.asarray(Image.open(path.with_name(stem + ".png")).convert("RGB")),
            "observation/wrist_image_left": np.asarray(Image.open(path.with_name(stem + "_wrist.png")).convert("RGB")),
            "observation/joint_position": state[:7], "observation/gripper_position": state[7:8],
            "prompt": (path.parent / "public_task.txt").read_text(encoding="utf-8"),
            "actions": actions, "action_valid": valid,
        }


def export_physical_frames(directory: Path, instruction: str):
    """从真实下一步关节状态构造 DROID 速度标度监督，不使用 IK 目标跳变。"""
    import json
    directory = Path(directory)
    io = [json.loads(line) for line in (directory / "policy_io.jsonl").read_text().splitlines()]
    with np.load(directory / "trajectory.npz") as trajectory:
        poses = {int(step): qpos for step, qpos in zip(trajectory["step"], trajectory["qpos"])}
    exported = 0
    for record in io:
        observation = record["observation"]
        next_step = round(float(observation["time_s"]) * 60) + 4
        if next_step not in poses:
            continue
        current = np.asarray(observation["robot_qpos"], dtype=float)
        joint_velocity = (poses[next_step][:7] - current[:7]) / 0.2
        if abs(joint_velocity).max() > 1.0001:
            raise ValueError("示范实际关节速度超出 DROID 每步标度，不能生成失真的目标")
        action = np.r_[joint_velocity, float(sum(record["action"]["joints"][-2:]) < 0.04)].astype(np.float32)
        state = np.r_[current[:7], np.clip(1 - sum(current[-2:]) / 0.08, 0, 1)].astype(np.float32)
        stem = Path(observation["rgb_artifact"]).stem
        np.save(directory / (stem + ".action.npy"), action)
        np.save(directory / (stem + ".state.npy"), state)
        exported += 1
    (directory / "public_task.txt").write_text(instruction, encoding="utf-8")
    return exported


def export_applied_position_frames(directory: Path):
    """按输入stem保存下一控制tick内实际施加的最后一个PD位置目标。

    使用限速后的控制请求，不以测得位移代替动作，也不使用原始IK大跳变。
    原速度监督与图像保持原样；新目标以 .joint_position.npy 后缀独立匹配。
    """
    import json
    directory = Path(directory)
    controls = [json.loads(line) for line in (directory / "robot_control.jsonl").read_text().splitlines()]
    by_step = {int(row["physics_step"]): row for row in controls}
    records = [json.loads(line) for line in (directory / "policy_io.jsonl").read_text().splitlines()]
    count = 0
    for record in records:
        observation = record["observation"]
        stem = Path(observation["rgb_artifact"]).stem
        if not (directory / (stem + ".action.npy")).exists():
            continue
        end_step = round(float(observation["time_s"]) * 60) + 3
        if end_step not in by_step:
            raise ValueError(f"缺少该输入下一tick的实际控制目标：{stem}")
        applied = np.asarray(by_step[end_step]["applied_target"], dtype=np.float32)
        target = np.r_[applied[:7], np.clip(1 - sum(applied[-2:]) / 0.08, 0, 1)].astype(np.float32)
        np.save(directory / (stem + ".joint_position.npy"), target)
        count += 1
    return count
