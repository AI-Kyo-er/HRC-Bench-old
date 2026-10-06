"""原生 π0.5-DROID 的双相机 / 本体状态 / 关节动作块适配。"""
from __future__ import annotations

from hashlib import sha256
from time import perf_counter

import numpy as np

from .protocol import Action, Observation
from .robot_control import droid_action_to_joint_target, position_action_to_joint_target


class DroidVLAAdapter:
    """模型只接收真实图像、本体状态和公开任务语言，不接收语义物体坐标。

    15 Hz 控制，使用官方 DROID 的 7 维归一化关节速度 + 夹爪闭合比例。
    目前只能输出底层动作，不替模型生成求助或其他公开沟通动作。
    """

    continuous_control = True

    def __init__(self, infer, *, instruction: str | None = None, execution_horizon: int = 8,
                 action_encoding: str = "joint_velocity"):
        if execution_horizon < 1:
            raise ValueError("execution_horizon 必须为正整数")
        self.infer = infer
        self.instruction = instruction
        self.execution_horizon = execution_horizon
        if action_encoding not in {"joint_velocity", "joint_position"}:
            raise ValueError("未知模型动作编码")
        self.action_encoding = action_encoding
        self.reset()

    def reset(self):
        self.chunk = []
        self.cursor = 0
        self.seen_messages = 0
        self.calls = 0
        self.last_time = None
        self.last_call = None
        self.initial_message_count = None

    def act(self, observation: Observation) -> Action:
        if observation.rgb is None or observation.wrist_rgb is None:
            raise ValueError("DROID 需要真实外部相机与腕部相机；不能复制同一图像冒充双相机")
        if self.last_time is not None and not np.isclose(observation.time_s - self.last_time, 1 / 15, atol=1e-7):
            raise ValueError("DROID 动作标度要求每 1/15 秒调用一次，请使用 tick_hz=15")
        self.last_time = observation.time_s
        if self.initial_message_count is None:
            self.initial_message_count = len(observation.messages)
        if len(observation.robot_qpos) != 9:
            raise ValueError("需要 7 个 Franka 臂关节与 2 个指关节状态")
        new_messages = observation.messages[self.seen_messages:]
        invalidate = any(message.kind in {"assignment", "correction", "reassignment", "help_reply",
                                          "temporarily_away", "returned", "action_failed", "action_blocked",
                                          "activity_change"}
                         for message in new_messages)
        self.seen_messages = len(observation.messages)
        if invalidate or self.cursor >= min(len(self.chunk), self.execution_horizon):
            request = {
                "observation/exterior_image_1_left": observation.rgb.copy(),
                "observation/wrist_image_left": observation.wrist_rgb.copy(),
                "observation/joint_position": np.asarray(observation.robot_qpos[:7], dtype=np.float32),
                "observation/gripper_position": np.array([
                    np.clip(1 - sum(observation.robot_qpos[-2:]) / 0.08, 0, 1)], dtype=np.float32),
                "prompt": self.instruction or observation.task_description,
            }
            activity_start = max((index for index, message in enumerate(observation.messages)
                                  if message.kind == "activity_change"), default=0)
            if observation.messages and observation.messages[activity_start].kind == "activity_change":
                request["prompt"] += "\nCurrent public activity: " + observation.messages[activity_start].text
            human_messages = [message.text for index, message in enumerate(observation.messages) if index >= activity_start and (message.speaker == "human"
                              or (message.speaker == "environment" and message.kind in {"action_blocked", "action_failed"}))
                              and not (index < self.initial_message_count
                                       and message.kind == "assignment" and message.value == "robot"
                                       and message.text == f"请你处理 {message.object_id}，目标是 {message.destination}。")]
            if human_messages:
                request["prompt"] += "\n" + "\n".join(human_messages[-8:])
            started = perf_counter()
            output = self.infer(request)
            chunk = np.asarray(output["actions"], dtype=float)
            if chunk.ndim != 2 or chunk.shape[1] != 8 or len(chunk) < 1 or not np.isfinite(chunk).all():
                raise ValueError("OpenPI 必须输出非空有限 N×8 动作块")
            self.chunk = chunk
            self.cursor = 0
            self.calls += 1
            self.last_call = {
                "adapter": "pi05_droid", "model_call": self.calls, "status": "ok",
                "elapsed_ms": (perf_counter() - started) * 1000,
                "raw_action_chunk": chunk.tolist(), "prompt": request["prompt"],
                "exterior_rgb_sha256": sha256(observation.rgb.tobytes()).hexdigest(),
                "wrist_rgb_sha256": sha256(observation.wrist_rgb.tobytes()).hexdigest(),
                "model_input_keys": list(request), "control_hz": 15,
                "action_scale_rad_per_step": 0.2 if self.action_encoding == "joint_velocity" else None,
                "action_encoding": self.action_encoding,
            }
        raw_action = self.chunk[self.cursor]
        self.cursor += 1
        self.last_call["executed_chunk_index"] = self.cursor - 1
        joints = (position_action_to_joint_target(raw_action) if self.action_encoding == "joint_position"
                  else droid_action_to_joint_target(raw_action, observation.robot_qpos))
        return Action("joint_position", joints=joints, duration_steps=1,
                      control_mode="learned_absolute_joint_position" if self.action_encoding == "joint_position"
                      else "droid_velocity_to_joint_position")

    def audit_record(self):
        return dict(self.last_call) if self.last_call is not None else None


def make_openpi_droid():
    import os
    from openpi_client.websocket_client_policy import WebsocketClientPolicy
    client = WebsocketClientPolicy(host=os.environ.get("HRC_OPENPI_HOST", "localhost"),
                                   port=int(os.environ.get("HRC_OPENPI_PORT", "8765")))
    return DroidVLAAdapter(client.infer)
