"""面向真实模型的公开观测与动作适配器。"""
from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from typing import Any

from .protocol import Action, Observation, serialize


PRIVATE_OBSERVATION_KEYS = frozenset({
    "scenario", "robot_targets", "human_targets", "human_availability", "trust",
    "private_goal", "partner_state", "evaluator_label",
})


def public_observation_dict(observation: Observation) -> dict[str, Any]:
    """把协议观测编码为模型输入，RGB 保留实际像素数组。"""
    encoded = serialize(observation)
    encoded["rgb"] = observation.rgb.copy() if observation.rgb is not None else None
    leaked = PRIVATE_OBSERVATION_KEYS.intersection(encoded)
    if leaked:
        raise ValueError(f"公开观测包含私有字段: {sorted(leaked)}")
    return encoded


def decode_action(value: Action | Mapping[str, Any] | str) -> Action:
    """解码模型输出，并在进入仿真器前执行统一的动作边界检查。"""
    if isinstance(value, Action):
        action = value
    else:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, Mapping):
            raise TypeError("模型动作必须是 Action、JSON 对象或 JSON 字符串")
        allowed = {"kind", "object_id", "destination", "text", "joints", "duration_steps", "control_mode"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"模型动作包含未定义字段: {sorted(unknown)}")
        action = Action(**dict(value))
    if action.kind not in {"transfer", "request_help", "acknowledge", "wait", "joint_position", "finish"}:
        raise ValueError(f"未知动作类型: {action.kind}")
    if isinstance(action.duration_steps, bool) or not isinstance(action.duration_steps, int) or action.duration_steps < 1:
        raise ValueError("duration_steps 必须为正整数")
    if action.kind == "joint_position" and len(action.joints) != 9:
        raise ValueError("joint_position 必须包含 9 个关节目标")
    if action.kind == "joint_position" and not all(math.isfinite(value) for value in action.joints):
        raise ValueError("joint_position 必须包含有限关节目标")
    if action.kind == "transfer" and (not action.object_id or not action.destination):
        raise ValueError("transfer 必须同时给出 object_id 和 destination")
    return action


class ModelPolicy:
    """把任意同步模型函数接入 ContinuousBackend。

    `predict` 接收不含评测标签的字典，可以是 VLA 的图像加结构化输入，
    也可以是 WLA 的文本/状态输入；它返回 Action、JSON 字典或 JSON 字符串。
    """

    def __init__(self, predict: Callable[[dict[str, Any]], Any], *, continuous_control: bool = False):
        self.predict = predict
        self.continuous_control = continuous_control
        self.calls = 0

    def reset(self) -> None:
        self.calls = 0

    def act(self, observation: Observation) -> Action:
        self.calls += 1
        return decode_action(self.predict(public_observation_dict(observation)))


class FixedActionModel:
    """用于协议测试的最小模型，不参与 benchmark 结果解释。"""

    def __init__(self, action: Action):
        self.action = action

    def __call__(self, _: dict[str, Any]) -> Action:
        return self.action
