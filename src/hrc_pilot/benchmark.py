"""面向真实模型的公开观测与动作适配器。"""
from __future__ import annotations

import json
import math
from time import perf_counter
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

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


def _json_safe(value: Any) -> Any:
    """将外部模型的输入输出转换为可审计的 JSON 值。"""
    if isinstance(value, np.ndarray):
        return {"type": "ndarray", "shape": list(value.shape), "dtype": str(value.dtype)}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _json_safe(serialize(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


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

    def __init__(self, predict: Callable[[dict[str, Any]], Any], *, continuous_control: bool = False,
                 adapter_name: str = "python_callable"):
        self.predict = predict
        self.continuous_control = continuous_control
        self.adapter_name = adapter_name
        self.calls = 0
        self.last_call: dict[str, Any] | None = None

    def reset(self) -> None:
        self.calls = 0
        self.last_call = None

    def act(self, observation: Observation) -> Action:
        self.calls += 1
        request = public_observation_dict(observation)
        started = perf_counter()
        try:
            raw_output = self.predict(request)
            action = decode_action(raw_output)
        except Exception as error:
            self.last_call = {
                "adapter": self.adapter_name,
                "call_index": self.calls,
                "elapsed_ms": round((perf_counter() - started) * 1000.0, 3),
                "status": "error",
                "error_type": type(error).__name__,
                "error": str(error),
            }
            raise
        self.last_call = {
            "adapter": self.adapter_name,
            "call_index": self.calls,
            "elapsed_ms": round((perf_counter() - started) * 1000.0, 3),
            "status": "ok",
            "raw_output": _json_safe(raw_output),
            "action": _json_safe(action),
        }
        return action

    def audit_record(self) -> dict[str, Any] | None:
        """返回最近一次调用的轻量审计记录，不包含 RGB 像素。"""
        return self.last_call


class ExternalPolicyAdapter(ModelPolicy):
    """现有 VLA/WLA 的稳定 Python 适配契约。

    外部模型只需要实现 ``predict(public_observation)``。输入是公开观测字典，
    输出是 ``Action``、动作 JSON 字典或 JSON 字符串；适配器负责动作校验、
    推理耗时和原始输出审计。HTTP、subprocess 或模型仓库调用可以封装在
    ``predict`` 内，而不需要修改 benchmark 运行时。
    """

    def __init__(self, predict: Callable[[dict[str, Any]], Any], *,
                 continuous_control: bool = False, adapter_name: str = "external"):
        super().__init__(predict, continuous_control=continuous_control,
                         adapter_name=adapter_name)


class FixedActionModel:
    """用于协议测试的最小模型，不参与 benchmark 结果解释。"""

    def __init__(self, action: Action):
        self.action = action

    def __call__(self, _: dict[str, Any]) -> Action:
        return self.action
